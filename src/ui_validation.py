"""Validation and normalization helpers for the ImmoAds UI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from src.document_processor import normalize_owner_listing
    from src.location_data import get_plz_spatial_summary, verify_address_with_geopy
except ImportError:  # pragma: no cover - script execution fallback
    from document_processor import normalize_owner_listing
    from location_data import get_plz_spatial_summary, verify_address_with_geopy


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    text = str(value).strip()
    return text or None


def _coerce_picture_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return Path(cleaned).name if cleaned else None

    for attr in ("orig_name", "name", "path", "filename"):
        candidate = getattr(value, attr, None)
        if candidate:
            return Path(str(candidate)).name

    cleaned = _clean_text(value)
    return Path(cleaned).name if cleaned else None


def _coerce_picture_list(uploaded_pictures: Optional[Sequence[Any]]) -> List[str]:
    if not uploaded_pictures:
        return []

    pictures: List[str] = []
    for item in uploaded_pictures:
        picture_name = _coerce_picture_value(item)
        if picture_name:
            pictures.append(picture_name)
    return pictures


def build_listing_payload(
    **form_values: Any,
) -> Dict[str, Any]:
    """Create the canonical intake payload for the parser."""

    if "plz" in form_values or "postal_code" in form_values:
        street_name = form_values.get("street_name")
        house_number = form_values.get("house_number")
        postal_code = form_values.get("postal_code") or form_values.get("plz") or ""
        city = form_values.get("city")
        full_name = form_values.get("full_name") or form_values.get("contact_name")
        phone_number = form_values.get("phone_number") or form_values.get("phone")
        living_area_sqm = form_values.get("living_area_sqm") or form_values.get("size_sqm")
        rooms = form_values.get("rooms")
        bedrooms = form_values.get("bedrooms")
        bathrooms = form_values.get("bathrooms")
        heating_type = form_values.get("heating_type")
        energy_efficiency = form_values.get("energy_efficiency")
        property_condition = form_values.get("property_condition")
        cold_rent_eur = form_values.get("cold_rent_eur")
        nebenkosten_eur = form_values.get("nebenkosten_eur")
        total_warm_rent_eur = form_values.get("total_warm_rent_eur") or form_values.get("rent_eur")
        property_type = form_values.get("property_type")
        property_description = form_values.get("property_description") or form_values.get("description")
        fixtures_and_fittings = form_values.get("fixtures_and_fittings")
        tone = form_values.get("tone")
        photos = form_values.get("photos") or form_values.get("pictures")
        location_note = form_values.get("location_note")
    else:
        street_name = form_values.get("street_name")
        house_number = form_values.get("house_number")
        postal_code = form_values.get("postal_code") or ""
        city = form_values.get("city")
        full_name = form_values.get("full_name")
        phone_number = form_values.get("phone_number")
        living_area_sqm = form_values.get("living_area_sqm")
        rooms = form_values.get("rooms")
        bedrooms = form_values.get("bedrooms")
        bathrooms = form_values.get("bathrooms")
        heating_type = form_values.get("heating_type")
        energy_efficiency = form_values.get("energy_efficiency")
        property_condition = form_values.get("property_condition")
        cold_rent_eur = form_values.get("cold_rent_eur")
        nebenkosten_eur = form_values.get("nebenkosten_eur")
        total_warm_rent_eur = form_values.get("total_warm_rent_eur")
        property_type = form_values.get("property_type")
        property_description = form_values.get("property_description")
        fixtures_and_fittings = form_values.get("fixtures_and_fittings")
        tone = form_values.get("tone")
        photos = form_values.get("photos") or form_values.get("pictures")
        location_note = form_values.get("location_note")

    description_bits = [
        _clean_text(property_description),
        _clean_text(fixtures_and_fittings),
        _clean_text(location_note),
    ]
    description = "\n\n".join(bit for bit in description_bits if bit)

    payload: Dict[str, Any] = {
        "street_name": _clean_text(street_name),
        "house_number": _clean_text(house_number),
        "plz": _clean_text(postal_code) or "",
        "postal_code": _clean_text(postal_code) or "",
        "city": _clean_text(city),
        "full_name": _clean_text(full_name),
        "phone_number": _clean_text(phone_number),
        "living_area_sqm": living_area_sqm,
        "size_sqm": living_area_sqm,
        "rooms": rooms,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "heating_type": _clean_text(heating_type),
        "energy_efficiency": _clean_text(energy_efficiency),
        "property_condition": _clean_text(property_condition),
        "cold_rent_eur": cold_rent_eur,
        "nebenkosten_eur": nebenkosten_eur,
        "total_warm_rent_eur": total_warm_rent_eur,
        "rent_eur": total_warm_rent_eur,
        "property_type": _clean_text(property_type),
        "description": description,
        "tone": _clean_text(tone),
        "headline": " ".join(
            part for part in [_clean_text(street_name), _clean_text(house_number), _clean_text(city)] if part
        ),
    }

    if isinstance(photos, str):
        photo_values: Sequence[Any] = [photos]
    elif isinstance(photos, Sequence):
        photo_values = photos
    elif photos is None:
        photo_values = []
    else:
        photo_values = [photos]

    picture_names = _coerce_picture_list(photo_values)
    if picture_names:
        payload["pictures"] = picture_names

    return {key: value for key, value in payload.items() if value not in (None, "")}


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
