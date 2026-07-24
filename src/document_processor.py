"""Normalize raw owner property listings into pipeline-ready inputs.

This module accepts dicts, JSON strings, or plain-text listings and converts
them into ``ContentPipelineInputs`` for the content pipeline.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Union

try:
    from src.content_pipeline import ContentPipelineInputs
except ImportError:  # pragma: no cover - script execution fallback
    from content_pipeline import ContentPipelineInputs

RawListingInput = Union[Mapping[str, Any], str, Path]

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

DEFAULT_OUTPUT_LANGUAGE = "English"


def _normalize_key(key: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", key.strip().lower())
    return cleaned.strip("_")


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        return stripped
    return value


def _clean_owner_info(owner_info: Mapping[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in owner_info.items():
        cleaned_key = _normalize_key(str(key))
        if not cleaned_key:
            continue
        cleaned[cleaned_key] = _coerce_scalar(value)
    return cleaned


def _apply_aliases(owner_info: Mapping[str, Any]) -> Dict[str, Any]:
    mapped: Dict[str, Any] = {}
    for key, value in owner_info.items():
        target_key = FIELD_ALIASES.get(_normalize_key(key), _normalize_key(key))
        mapped[target_key] = value
    return mapped


def _parse_json_text(raw_text: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        return parsed
    return None


def _extract_key_value_pairs(raw_text: str) -> Dict[str, Any]:
    pairs: Dict[str, Any] = {}
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        normalized_key = _normalize_key(key)
        if not normalized_key:
            continue
        pairs[normalized_key] = value.strip()
    return pairs


def _infer_plz(text: str) -> Optional[str]:
    match = re.search(r"\b\d{5}\b", text)
    if match:
        return match.group(0)
    return None


def _infer_owner_info(raw_input: RawListingInput) -> Dict[str, Any]:
    if isinstance(raw_input, Mapping):
        return _clean_owner_info(_apply_aliases(raw_input))

    if isinstance(raw_input, Path):
        raw_text = raw_input.read_text(encoding="utf-8")
    else:
        raw_text = str(raw_input)

    raw_text = raw_text.strip()
    if not raw_text:
        return {}

    parsed_json = _parse_json_text(raw_text)
    if parsed_json is not None:
        return _clean_owner_info(_apply_aliases(parsed_json))

    extracted_pairs = _extract_key_value_pairs(raw_text)
    return _clean_owner_info(_apply_aliases(extracted_pairs))


def _build_pipeline_inputs(owner_info: Dict[str, Any]) -> ContentPipelineInputs:
    plz = str(owner_info.pop("plz", "")).strip()
    if not plz:
        inferred_plz = _infer_plz(json.dumps(owner_info, ensure_ascii=True))
        plz = inferred_plz or ""

    output_language = str(owner_info.pop("output_language", DEFAULT_OUTPUT_LANGUAGE) or DEFAULT_OUTPUT_LANGUAGE).strip()
    tone_hint = owner_info.pop("tone", None)
    additional_instructions = owner_info.pop("additional_instructions", None)

    if not plz:
        raise ValueError("A PLZ/postal code is required to build ContentPipelineInputs.")

    return ContentPipelineInputs(
        owner_info=owner_info,
        plz=plz,
        output_language=output_language or DEFAULT_OUTPUT_LANGUAGE,
        tone_hint=str(tone_hint).strip() if tone_hint else None,
        additional_instructions=str(additional_instructions).strip() if additional_instructions else None,
    )


def normalize_owner_listing(raw_input: RawListingInput) -> ContentPipelineInputs:
    """Convert dict, JSON, or TXT input into ``ContentPipelineInputs``."""
    owner_info = _infer_owner_info(raw_input)
    return _build_pipeline_inputs(owner_info)


def normalize_listing_file(path: Union[str, Path]) -> ContentPipelineInputs:
    """Load a local file and normalize it into pipeline inputs."""
    file_path = Path(path)
    return normalize_owner_listing(file_path)


def content_pipeline_inputs_to_dict(inputs: ContentPipelineInputs) -> Dict[str, Any]:
    """Serialize pipeline inputs for debugging or tests."""
    return {
        "owner_info": dict(inputs.owner_info),
        "plz": inputs.plz,
        "output_language": inputs.output_language,
        "tone_hint": inputs.tone_hint,
        "additional_instructions": inputs.additional_instructions,
    }


if __name__ == "__main__":
    sample_text = """
    headline: Westend 3-room apartment
    postal_code: 10115
    rooms: 3
    size: 84.3
    rent: 1415
    bathrooms: 1
    tone: warm and premium
    description: Renovated old-building apartment with balcony and fitted kitchen.
    """
    normalized = normalize_owner_listing(sample_text)
    print(json.dumps(content_pipeline_inputs_to_dict(normalized), indent=2, ensure_ascii=False))
