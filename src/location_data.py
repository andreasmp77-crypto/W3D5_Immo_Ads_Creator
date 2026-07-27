"""Compatibility facade for PLZ lookups and live verification.

Static lookup logic lives in ``src.location_static`` and live network helpers
live in ``src.location_live``. This module keeps the original import surface
stable for the UI, pipeline, and tests.
"""

from __future__ import annotations

import logging
import time
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.location_live import (
        AddressVerificationResult,
        BVG_BASE_URL,
        fetch_nearby_transit_for_centroid,
        get_geopy_geocode as _get_geopy_geocode_impl,
        verify_address as _verify_address_impl,
    )
    from src.location_static import (
        PlzSpatialSummary,
        build_plz_spatial_summary,
        format_kita_data,
        format_school_data,
        get_kitas as _get_kitas_impl,
        get_neighboring_plz as _get_neighboring_plz_impl,
        get_schools as _get_schools_impl,
        load_centroids_file,
        load_kitas_file,
        load_neighbors_file,
        load_schools_file,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from location_live import (
        AddressVerificationResult,
        BVG_BASE_URL,
        fetch_nearby_transit_for_centroid,
        get_geopy_geocode as _get_geopy_geocode_impl,
        verify_address as _verify_address_impl,
    )
    from location_static import (
        PlzSpatialSummary,
        build_plz_spatial_summary,
        format_kita_data,
        format_school_data,
        get_kitas as _get_kitas_impl,
        get_neighboring_plz as _get_neighboring_plz_impl,
        get_schools as _get_schools_impl,
        load_centroids_file,
        load_kitas_file,
        load_neighbors_file,
        load_schools_file,
    )

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KITAS_FILE = DATA_DIR / "kitas_by_plz.json"
CENTROIDS_FILE = DATA_DIR / "plz_centroids.json"
NEIGHBORS_FILE = DATA_DIR / "plz_neighbors.json"
SCHOOLS_FILE = DATA_DIR / "schools_by_plz.json"

# Cached live transit results. Tests monkeypatch this dict directly, so the
# wrapper keeps it local instead of hiding it behind the live helper module.
TRANSIT_CACHE_TTL_SECONDS = 15 * 60
_transit_cache: Dict[str, Tuple[float, str]] = {}

# Monkeypatch-friendly aliases for the static/live helpers.
_load_kitas = lru_cache(maxsize=1)(lambda: load_kitas_file(KITAS_FILE))
_load_centroids = lru_cache(maxsize=1)(lambda: load_centroids_file(CENTROIDS_FILE))
_load_neighbors = lru_cache(maxsize=1)(lambda: load_neighbors_file(NEIGHBORS_FILE))
_load_schools = lru_cache(maxsize=1)(lambda: load_schools_file(SCHOOLS_FILE))
_get_geopy_geocode = _get_geopy_geocode_impl


def _normalize_plz(plz: str) -> str:
    return str(plz).strip()


@lru_cache(maxsize=256)
def get_plz_spatial_summary(plz: str) -> PlzSpatialSummary:
    """Return cached spatial metadata for a single PLZ."""

    normalized_plz = _normalize_plz(plz)
    return build_plz_spatial_summary(
        normalized_plz,
        kitas_lookup=_load_kitas(),
        centroids_lookup=_load_centroids(),
    )


def get_neighboring_plz(plz: str) -> List[str]:
    """Return real bordering PLZ codes for a given PLZ."""

    return _get_neighboring_plz_impl(_normalize_plz(plz), _load_neighbors())


def get_kitas(plz: str, top_n: int = 3) -> List[Dict[str, object]]:
    """Return up to top_n Kitas for a PLZ, largest licensed capacity first."""

    return _get_kitas_impl(_normalize_plz(plz), _load_kitas(), top_n=top_n)


def get_schools(plz: str, top_n: int = 3) -> List[Dict[str, object]]:
    """Return up to top_n schools for a PLZ."""

    return _get_schools_impl(_normalize_plz(plz), _load_schools(), top_n=top_n)


@lru_cache(maxsize=256)
def load_school_data(plz: str) -> str:
    """Return a human-readable summary of real schools for the given PLZ."""

    if not SCHOOLS_FILE.exists():
        return "Schools: data not yet available (run scripts/fetch_schools.py)."

    normalized_plz = _normalize_plz(plz)
    schools_lookup = _load_schools()
    return format_school_data(
        normalized_plz,
        schools_lookup=schools_lookup,
        neighbors_lookup=_load_neighbors(),
    )


@lru_cache(maxsize=256)
def load_kita_data(plz: str) -> str:
    """Return a human-readable summary of real Kitas for the given PLZ."""

    normalized_plz = _normalize_plz(plz)
    spatial_summary = get_plz_spatial_summary(normalized_plz)
    return format_kita_data(
        normalized_plz,
        kitas_lookup=_load_kitas(),
        neighbors_lookup=_load_neighbors(),
        spatial_summary=spatial_summary,
    )


def fetch_nearby_transit(plz: str, max_results: int = 5, max_distance_m: int = 800) -> str:
    """Return a real nearby-transit summary via a live BVG API call."""

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
    result = fetch_nearby_transit_for_centroid(
        lat,
        lng,
        max_results=max_results,
        max_distance_m=max_distance_m,
        urlopen=urllib.request.urlopen,
    )
    _transit_cache[normalized_plz] = (time.monotonic(), result)
    return result


@lru_cache(maxsize=512)
def verify_address_with_geopy(
    street_name: str,
    house_number: str,
    postal_code: str,
    city: str,
) -> AddressVerificationResult:
    """Verify a submitted address through geopy/Nominatim."""

    return _verify_address_impl(
        street_name,
        house_number,
        postal_code,
        city,
        geocode=_get_geopy_geocode(),
    )


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
