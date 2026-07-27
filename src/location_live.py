"""Live network helpers for ImmoAds location verification."""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Optional, Tuple

logger = logging.getLogger(__name__)

BVG_BASE_URL = "https://v6.bvg.transport.rest"
GEOPY_USER_AGENT = os.getenv("IMMOADS_GEOPY_USER_AGENT", "ImmoAdsAddressVerifier/1.0")
GEOPY_REQUEST_TIMEOUT_SECONDS = float(os.getenv("IMMOADS_GEOPY_REQUEST_TIMEOUT_SECONDS", "5"))
GEOPY_MIN_DELAY_SECONDS = float(os.getenv("IMMOADS_GEOPY_MIN_DELAY_SECONDS", "1.0"))


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


def _normalize_address_part(value: Any) -> str:
    return str(value or "").strip()


def _build_address_query(street_name: str, house_number: str, postal_code: str, city: str) -> str:
    street_line = " ".join(part for part in (street_name, house_number) if part).strip()
    locality_line = ", ".join(part for part in (postal_code, city, "Germany") if part)
    return ", ".join(part for part in (street_line, locality_line) if part)


@lru_cache(maxsize=1)
def get_geopy_geocode() -> Optional[Callable[..., Any]]:
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


def verify_address(
    street_name: str,
    house_number: str,
    postal_code: str,
    city: str,
    *,
    geocode: Optional[Callable[..., Any]] = None,
) -> AddressVerificationResult:
    """Verify a submitted address through geopy/Nominatim."""

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

    geocode = geocode or get_geopy_geocode()
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


def fetch_nearby_transit_for_centroid(
    lat: float,
    lng: float,
    *,
    max_results: int = 5,
    max_distance_m: int = 800,
    urlopen: Callable[..., Any] = urllib.request.urlopen,
) -> str:
    """Return a real nearby-transit summary via a live BVG API call."""

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
        with urlopen(url, timeout=5) as resp:
            stops = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network/API failure: fail closed, never fabricate
        logger.warning("BVG lookup failed: %s", exc)
        return "Public transport: data unavailable for this PLZ."

    named_stops = [f"{s['name']} ({s.get('distance')}m)" for s in stops if s.get("type") == "stop" and s.get("name")]
    if not named_stops:
        return "Public transport: no stops found within range for this PLZ."
    return "Public transport: nearby stops include " + ", ".join(named_stops[:max_results]) + "."

