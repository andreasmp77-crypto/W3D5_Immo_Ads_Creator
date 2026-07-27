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
