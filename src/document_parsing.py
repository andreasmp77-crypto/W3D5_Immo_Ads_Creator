"""Low-level parsing helpers for raw listing intake."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

FIELD_ALIASES = {
    "postal_code": "plz",
    "postcode": "plz",
    "zip": "plz",
    "zip_code": "plz",
    "rooms": "rooms",
    "room_count": "rooms",
    "size": "size_sqm",
    "size_sqm": "size_sqm",
    "living_area": "size_sqm",
    "rent": "rent_eur",
    "monthly_rent": "rent_eur",
    "rent_eur": "rent_eur",
    "bathrooms": "bathrooms",
    "bathroom_count": "bathrooms",
    "description": "description",
    "tone": "tone",
    "tone_of_ad": "tone",
    "headline": "headline",
    "language": "output_language",
    "output_language": "output_language",
    "additional_instructions": "additional_instructions",
}


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    text = str(value).strip()
    return text or None


def coerce_picture_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return Path(cleaned).name if cleaned else None

    for attr in ("orig_name", "name", "path", "filename"):
        candidate = getattr(value, attr, None)
        if candidate:
            return Path(str(candidate)).name

    cleaned = clean_text(value)
    return Path(cleaned).name if cleaned else None


def coerce_picture_list(uploaded_pictures: Optional[Sequence[Any]]) -> List[str]:
    if not uploaded_pictures:
        return []

    pictures: List[str] = []
    for item in uploaded_pictures:
        picture_name = coerce_picture_value(item)
        if picture_name:
            pictures.append(picture_name)
    return pictures


def normalize_key(key: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", key.strip().lower())
    return cleaned.strip("_")


def coerce_scalar(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        return stripped
    return value


def clean_owner_info(owner_info: Mapping[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in owner_info.items():
        cleaned_key = normalize_key(str(key))
        if not cleaned_key:
            continue
        cleaned[cleaned_key] = coerce_scalar(value)
    return cleaned


def apply_aliases(owner_info: Mapping[str, Any]) -> Dict[str, Any]:
    mapped: Dict[str, Any] = {}
    for key, value in owner_info.items():
        target_key = FIELD_ALIASES.get(normalize_key(key), normalize_key(key))
        mapped[target_key] = value
    return mapped


def parse_json_text(raw_text: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed
    return None


def extract_key_value_pairs(raw_text: str) -> Dict[str, Any]:
    pairs: Dict[str, Any] = {}
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        normalized_key = normalize_key(key)
        if not normalized_key:
            continue
        pairs[normalized_key] = value.strip()
    return pairs


def infer_plz(text: str) -> Optional[str]:
    match = re.search(r"\b\d{5}\b", text)
    if match:
        return match.group(0)
    return None


def infer_owner_info(raw_input: Any) -> Dict[str, Any]:
    if isinstance(raw_input, Mapping):
        return clean_owner_info(apply_aliases(raw_input))

    if isinstance(raw_input, Path):
        raw_text = raw_input.read_text(encoding="utf-8")
    else:
        raw_text = str(raw_input)

    raw_text = raw_text.strip()
    if not raw_text:
        return {}

    parsed_json = parse_json_text(raw_text)
    if parsed_json is not None:
        return clean_owner_info(apply_aliases(parsed_json))

    extracted_pairs = extract_key_value_pairs(raw_text)
    return clean_owner_info(apply_aliases(extracted_pairs))


def build_listing_payload(**form_values: Any) -> Dict[str, Any]:
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
        clean_text(property_description),
        clean_text(fixtures_and_fittings),
        clean_text(location_note),
    ]
    description = "\n\n".join(bit for bit in description_bits if bit)

    payload: Dict[str, Any] = {
        "street_name": clean_text(street_name),
        "house_number": clean_text(house_number),
        "plz": clean_text(postal_code) or "",
        "postal_code": clean_text(postal_code) or "",
        "city": clean_text(city),
        "full_name": clean_text(full_name),
        "phone_number": clean_text(phone_number),
        "living_area_sqm": living_area_sqm,
        "size_sqm": living_area_sqm,
        "rooms": rooms,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "heating_type": clean_text(heating_type),
        "energy_efficiency": clean_text(energy_efficiency),
        "property_condition": clean_text(property_condition),
        "cold_rent_eur": cold_rent_eur,
        "nebenkosten_eur": nebenkosten_eur,
        "total_warm_rent_eur": total_warm_rent_eur,
        "rent_eur": total_warm_rent_eur,
        "property_type": clean_text(property_type),
        "description": description,
        "tone": clean_text(tone),
        "headline": " ".join(
            part for part in [clean_text(street_name), clean_text(house_number), clean_text(city)] if part
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

    picture_names = coerce_picture_list(photo_values)
    if picture_names:
        payload["pictures"] = picture_names

    return {key: value for key, value in payload.items() if value not in (None, "")}
