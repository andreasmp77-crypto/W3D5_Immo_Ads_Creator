"""Deterministic PLZ-based location lookup for ImmoAds (M3).

Design notes (see rag_decision.md and knowledge_base/AGENTS.md):
- Kita data is static, sourced from Berlin's open-data Kitaliste, pre-processed into
  data/kitas_by_plz.json (grouped by PLZ, sorted by licensed capacity).
- PLZ -> centroid is a static, precomputed lookup (data/plz_centroids.json), sourced
  from WZBSocialScienceCenter/plz_geocoord.
- Public transport is fetched LIVE from v6.bvg.transport.rest at request time (no API
  key, 100 req/min free tier) using the PLZ centroid. This is a deterministic lookup,
  not a RAG/retrieval step.
- Schools are sourced from the official Senatsverwaltung fuer Bildung directory via
  scripts/fetch_schools.py into data/schools_by_plz.json, mirroring the Kita pattern.
  If that file hasn't been generated yet, get_schools()/load_school_data() return an
  "unavailable" result rather than a fabricated count.

All facts here are injected as explicit prompt variables, kept separate from
knowledge_base/ markdown context (never store PLZ facts inside knowledge_base/).
"""

from __future__ import annotations

import json
import os
import logging
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KITAS_FILE = DATA_DIR / "kitas_by_plz.json"
CENTROIDS_FILE = DATA_DIR / "plz_centroids.json"
NEIGHBORS_FILE = DATA_DIR / "plz_neighbors.json"
SCHOOLS_FILE = DATA_DIR / "schools_by_plz.json"
BVG_BASE_URL = "https://v6.bvg.transport.rest"
GEOPY_USER_AGENT = os.getenv("IMMOADS_GEOPY_USER_AGENT", "ImmoAdsAddressVerifier/1.0")
GEOPY_REQUEST_TIMEOUT_SECONDS = float(os.getenv("IMMOADS_GEOPY_REQUEST_TIMEOUT_SECONDS", "5"))
GEOPY_MIN_DELAY_SECONDS = float(os.getenv("IMMOADS_GEOPY_MIN_DELAY_SECONDS", "1.0"))

# Live transit lookups are cached in-memory for TRANSIT_CACHE_TTL_SECONDS so repeated
# ad-generation runs for the same PLZ (e.g. during testing/demo) don't hammer the
# free-tier BVG API (100 req/min)
# a shared/persistent cache later
TRANSIT_CACHE_TTL_SECONDS = 15 * 60
_transit_cache: Dict[str, Tuple[float, str]] = {}

@dataclass(frozen=True)
class PlzSpatialSummary:
    """Cached spatial summary for one postal code."""

    plz: str
    district: str
    record_count: int
    centroid_latlon: Optional[Tuple[float, float]] = None


@dataclass(frozen=True)
class AddressVerificationResult:
    """Outcome of an external geocoding verification lookup."""

    status: str
    query: str
    verified: bool
    message: str
    display_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


def _normalize_plz(plz: str) -> str:
    return str(plz).strip()


def _normalize_address_part(value: Any) -> str:
    return str(value or "").strip()


def _build_address_query(street_name: str, house_number: str, postal_code: str, city: str) -> str:
    street_line = " ".join(part for part in (street_name, house_number) if part).strip()
    locality_line = ", ".join(part for part in (postal_code, city, "Germany") if part)
    return ", ".join(part for part in (street_line, locality_line) if part)


@lru_cache(maxsize=1)
def _get_geopy_geocode() -> Optional[Callable[..., Any]]:
    """Build a rate-limited geopy geocoder if the dependency is installed."""

    try:
        from geopy.extra.rate_limiter import RateLimiter
        from geopy.geocoders import Nominatim
    except ImportError:
        logger.info("geopy is not installed; address verification will be skipped.")
        return None

    geocoder = Nominatim(
        user_agent=GEOPY_USER_AGENT,
        timeout=GEOPY_REQUEST_TIMEOUT_SECONDS,
    )
    return RateLimiter(
        geocoder.geocode,
        min_delay_seconds=GEOPY_MIN_DELAY_SECONDS,
        max_retries=0,
        swallow_exceptions=False,
    )


@lru_cache(maxsize=512)
def verify_address_with_geopy(
    street_name: str,
    house_number: str,
    postal_code: str,
    city: str,
) -> AddressVerificationResult:
    """Verify a submitted address through geopy/Nominatim.

    The result is cached per normalized address so repeated submits do not
    keep querying the external service. The geopy call itself is also
    rate-limited to avoid accidental bursts.
    """

    street_name = _normalize_address_part(street_name)
    house_number = _normalize_address_part(house_number)
    postal_code = _normalize_address_part(postal_code)
    city = _normalize_address_part(city)
    query = _build_address_query(street_name, house_number, postal_code, city)

    if not query:
        return AddressVerificationResult(
            status="skipped",
            query=query,
            verified=False,
            message="Address verification skipped because the address is incomplete.",
        )

    geocode = _get_geopy_geocode()
    if geocode is None:
        return AddressVerificationResult(
            status="unavailable",
            query=query,
            verified=False,
            message="Address verification unavailable because geopy is not installed.",
        )

    try:
        location = geocode(query, exactly_one=True, addressdetails=True, country_codes="de")
    except Exception as exc:  # network/API failure: fail closed, never fabricate
        logger.warning("Geopy address verification failed for %s: %s", query, exc)
        return AddressVerificationResult(
            status="unavailable",
            query=query,
            verified=False,
            message="Address verification unavailable right now.",
        )

    if location is None:
        return AddressVerificationResult(
            status="not_verified",
            query=query,
            verified=False,
            message="Address could not be verified by the external geocoding service.",
        )

    raw = getattr(location, "raw", {}) or {}
    address_details = raw.get("address", {}) if isinstance(raw, dict) else {}
    returned_postcode = _normalize_address_part(address_details.get("postcode"))
    returned_city = _normalize_address_part(
        address_details.get("city")
        or address_details.get("town")
        or address_details.get("village")
        or address_details.get("municipality")
    )

    if postal_code and returned_postcode and returned_postcode != postal_code:
        return AddressVerificationResult(
            status="not_verified",
            query=query,
            verified=False,
            message="Address could not be verified by the external geocoding service.",
        )

    if city and returned_city and returned_city.lower() != city.lower():
        return AddressVerificationResult(
            status="not_verified",
            query=query,
            verified=False,
            message="Address could not be verified by the external geocoding service.",
        )

    return AddressVerificationResult(
        status="verified",
        query=query,
        verified=True,
        message="Address verified by the external geocoding service.",
        display_name=getattr(location, "address", None) or raw.get("display_name"),
        latitude=getattr(location, "latitude", None),
        longitude=getattr(location, "longitude", None),
    )


@lru_cache(maxsize=1)
def _load_kitas() -> Dict[str, List[Dict[str, object]]]:
    if not KITAS_FILE.exists():
        logger.warning("Kita data file not found at %s", KITAS_FILE)
        return {}
    with open(KITAS_FILE, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_centroids() -> Dict[str, Dict[str, float]]:
    if not CENTROIDS_FILE.exists():
        logger.warning("PLZ centroid file not found at %s", CENTROIDS_FILE)
        return {}
    with open(CENTROIDS_FILE, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=256)
def get_plz_spatial_summary(plz: str) -> PlzSpatialSummary:
    """Return cached spatial metadata for a single PLZ."""
    normalized_plz = _normalize_plz(plz)
    kitas = _load_kitas().get(normalized_plz, [])
    centroid = _load_centroids().get(normalized_plz)

    district = kitas[0]["district"] if kitas else "unknown"
    centroid_latlon = (centroid["lat"], centroid["lng"]) if centroid else None

    return PlzSpatialSummary(
        plz=normalized_plz,
        district=district,
        record_count=len(kitas),
        centroid_latlon=centroid_latlon,
    )


@lru_cache(maxsize=1)
def _load_neighbors() -> Dict[str, List[str]]:
    if not NEIGHBORS_FILE.exists():
        logger.warning("PLZ neighbor file not found at %s", NEIGHBORS_FILE)
        return {}
    with open(NEIGHBORS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_neighboring_plz(plz: str) -> List[str]:
    """Return real bordering PLZ codes for a given PLZ.

    Precomputed once via geopandas polygon adjacency (shapely `.touches()`) on the
    official 190 Berlin PLZ boundary polygons -- not a live geometric computation on
    every call. See project_structure.md roadmap: "if Kita/school/transport info is
    missing, pick up neighbouring pincode information."
    """
    return _load_neighbors().get(_normalize_plz(plz), [])


def get_kitas(plz: str, top_n: int = 3) -> List[Dict[str, object]]:
    """Return up to top_n Kitas for a PLZ, largest licensed capacity first."""
    return _load_kitas().get(_normalize_plz(plz), [])[:top_n]


@lru_cache(maxsize=1)
def _load_schools() -> Dict[str, List[Dict[str, object]]]:
    if not SCHOOLS_FILE.exists():
        logger.warning(
            "Schools data file not found at %s -- run scripts/fetch_schools.py first",
            SCHOOLS_FILE,
        )
        return {}
    with open(SCHOOLS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_schools(plz: str, top_n: int = 3) -> List[Dict[str, object]]:
    """Return up to top_n schools for a PLZ.

    Source: data/schools_by_plz.json, generated by scripts/fetch_schools.py from
    the official Senatsverwaltung fuer Bildung schools directory. Returns []
    if the PLZ is unknown or the data file hasn't been generated yet.
    """
    return _load_schools().get(_normalize_plz(plz), [])[:top_n]


@lru_cache(maxsize=256)
def load_school_data(plz: str) -> str:
    """Return a human-readable summary of real schools for the given PLZ.

    Falls back to a real neighboring PLZ (same pattern as load_kita_data) if this
    PLZ has none. Returns an "unavailable" string if scripts/fetch_schools.py
    hasn't been run yet -- never a fabricated count.
    """
    if not SCHOOLS_FILE.exists():
        return "Schools: data not yet available (run scripts/fetch_schools.py)."

    normalized_plz = _normalize_plz(plz)
    schools = get_schools(normalized_plz)
    if schools:
        names = ", ".join(s["name"] for s in schools)
        total = len(_load_schools().get(normalized_plz, []))
        return f"Schools: {total} registered in this PLZ, including {names}."

    for neighbor_plz in get_neighboring_plz(normalized_plz):
        neighbor_schools = get_schools(neighbor_plz)
        if neighbor_schools:
            names = ", ".join(s["name"] for s in neighbor_schools)
            return (
                f"Schools: none registered directly in this PLZ; nearby PLZ "
                f"{neighbor_plz} has options including {names}."
            )

    return "Schools: no data available for this PLZ or its immediate neighbors."


@lru_cache(maxsize=256)
def load_kita_data(plz: str) -> str:
    """Return a human-readable summary of real Kitas for the given PLZ.

    Falls back to a real neighboring PLZ (via geopandas-derived adjacency) if this
    PLZ has no Kita data, per the project roadmap. The fallback is always labeled
    explicitly -- never presented as if it were data for the requested PLZ itself.
    """
    normalized_plz = _normalize_plz(plz)
    kitas = get_kitas(normalized_plz)
    if kitas:
        names = ", ".join(k["name"] for k in kitas)
        total = get_plz_spatial_summary(normalized_plz).record_count
        return f"Kitas: {total} registered in this PLZ, including {names}."

    for neighbor_plz in get_neighboring_plz(normalized_plz):
        neighbor_kitas = get_kitas(neighbor_plz)
        if neighbor_kitas:
            names = ", ".join(k["name"] for k in neighbor_kitas)
            return (
                f"Kitas: none registered directly in this PLZ; nearby PLZ {neighbor_plz} "
                f"has options including {names}."
            )

    return "Kitas: no data available for this PLZ or its immediate neighbors."


def fetch_nearby_transit(plz: str, max_results: int = 5, max_distance_m: int = 800) -> str:
    """Return a real nearby-transit summary via a live BVG API call.

    Fails closed: on any lookup/network problem, returns an explicit
    "unavailable" string rather than a fabricated station name.
    """
    normalized_plz = _normalize_plz(plz)

    cached = _transit_cache.get(normalized_plz)
    if cached is not None:
        cached_at, cached_value = cached
        if time.monotonic() - cached_at < TRANSIT_CACHE_TTL_SECONDS:
            return cached_value

    summary = get_plz_spatial_summary(normalized_plz)
    if not summary.centroid_latlon:
        return "Public transport: data unavailable for this PLZ."

    lat, lng = summary.centroid_latlon
    params = {
        "latitude": lat,
        "longitude": lng,
        "results": max_results,
        "distance": max_distance_m,
        "poi": "false",
        "pretty": "false",
    }
    url = f"{BVG_BASE_URL}/locations/nearby?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            stops = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network/API failure: fail closed, never fabricate
        logger.warning("BVG lookup failed for PLZ %s: %s", normalized_plz, exc)
        return "Public transport: data unavailable for this PLZ."

    named_stops = [f"{s['name']} ({s.get('distance')}m)" for s in stops if s.get("type") == "stop" and s.get("name")]
    if not named_stops:
        result = "Public transport: no stops found within range for this PLZ."
    else:
        result = "Public transport: nearby stops include " + ", ".join(named_stops[:max_results]) + "."

    _transit_cache[normalized_plz] = (time.monotonic(), result)
    return result


@lru_cache(maxsize=256)
def get_location_summary(plz: str) -> str:
    """Build the final fact block injected into prompts."""
    normalized_plz = _normalize_plz(plz)
    lines = [f"=== FACTUAL LOCATION DATA (ZIP CODE {normalized_plz}) ==="]
    lines.append(load_kita_data(normalized_plz))
    lines.append(load_school_data(normalized_plz))
    lines.append(fetch_nearby_transit(normalized_plz))
    return "\n\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_plz = "10115"
    print("\n--- TESTING LOCATION DATA RETRIEVAL ---")
    print(get_location_summary(test_plz))
