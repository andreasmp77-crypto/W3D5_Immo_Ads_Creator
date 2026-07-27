"""Validation and normalization helpers for the ImmoAds UI."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from src.document_parsing import build_listing_payload
    from src.document_processor import normalize_owner_listing
    from src.location_data import get_plz_spatial_summary, verify_address_with_geopy
except ImportError:  # pragma: no cover - script execution fallback
    from document_parsing import build_listing_payload
    from document_processor import normalize_owner_listing
    from location_data import get_plz_spatial_summary, verify_address_with_geopy


_HOUSE_NUMBER_PATTERN = re.compile(r"^[0-9]+[a-zA-Z]?(?:\s*[/\-]\s*[0-9]+[a-zA-Z]?)?$")


def validate_address_payload(
    payload: Dict[str, Any],
    *,
    strict_address_validation: bool = False,
    verify_external_address: bool = False,
    address_verifier: Optional[Callable[[str, str, str, str], Any]] = None,
) -> Tuple[List[str], List[str]]:
    """Validate address fields before the listing is sent to the pipeline."""

    errors: List[str] = []
    warnings: List[str] = []

    street_name = str(payload.get("street_name") or "").strip()
    house_number = str(payload.get("house_number") or "").strip()
    postal_code = str(payload.get("postal_code") or payload.get("plz") or "").strip()
    city = str(payload.get("city") or "").strip()

    has_address_fields = any((street_name, house_number, postal_code, city))
    if not has_address_fields and not strict_address_validation:
        return errors, warnings

    if not street_name:
        errors.append("Street name is required.")

    if not house_number:
        errors.append("House number is required.")
    elif not _HOUSE_NUMBER_PATTERN.fullmatch(house_number):
        errors.append("House number must look like 12, 12A, 12/14, or 12-14.")

    if not postal_code:
        errors.append("Postal code is required.")
    elif not re.fullmatch(r"\d{5}", postal_code):
        errors.append("Postal code must be a 5-digit Berlin PLZ.")

    if not city:
        errors.append("City is required.")
    elif city.lower() != "berlin":
        errors.append("This MVP only supports Berlin listings.")

    if postal_code and re.fullmatch(r"\d{5}", postal_code):
        spatial_summary = get_plz_spatial_summary(postal_code)
        if spatial_summary.record_count == 0 and spatial_summary.centroid_latlon is None:
            warnings.append(
                f"Postal code {postal_code} is valid, but it is not present in the local Berlin lookup data."
            )

    if verify_external_address and not errors:
        verifier = address_verifier or verify_address_with_geopy
        verification = verifier(street_name, house_number, postal_code, city)
        if verification.status == "not_verified":
            errors.append(verification.message)
        elif verification.status == "unavailable":
            warnings.append(verification.message)

    return errors, warnings


def normalize_listing_submission(
    strict_address_validation: bool = False,
    verify_external_address: bool = False,
    address_verifier: Optional[Callable[[str, str, str, str], Any]] = None,
    **form_values: Any,
) -> Tuple[Dict[str, Any], str]:
    """Normalize the landlord form and return a short status message."""

    payload = build_listing_payload(**form_values)
    address_errors, address_warnings = validate_address_payload(
        payload,
        strict_address_validation=strict_address_validation,
        verify_external_address=verify_external_address,
        address_verifier=address_verifier,
    )
    if address_errors and strict_address_validation:
        raise ValueError("Address validation failed: " + " ".join(address_errors))

    inputs = normalize_owner_listing(payload)
    normalized = {
        "owner_info": dict(inputs.owner_info),
        "plz": inputs.plz,
        "output_language": inputs.output_language,
        "tone_hint": inputs.tone_hint,
        "additional_instructions": inputs.additional_instructions,
    }
    owner_info = normalized["owner_info"]
    tone = owner_info.get("tone") or "Warm & inviting"
    rooms = owner_info.get("rooms", "n/a")
    photos = owner_info.get("pictures") or []
    photo_note = f" with {len(photos)} photo(s)" if photos else ""
    summary_lines = [
        "### Parsed intake",
        f"- PLZ: `{normalized['plz']}`",
        f"- Rooms: `{rooms}`",
        f"- Tone: {tone}",
        f"- Pictures: {', '.join(f'`{photo}`' for photo in photos) if photos else 'No pictures uploaded.'}",
    ]
    if address_warnings:
        summary_lines.extend([f"- Warning: {warning}" for warning in address_warnings])
    if photo_note:
        summary_lines.append(photo_note.strip())
    summary = "\n".join(summary_lines)
    return normalized, summary
