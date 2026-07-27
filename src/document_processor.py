"""Normalize raw owner property listings into pipeline-ready inputs.

This module accepts dicts, JSON strings, or plain-text listings and converts
them into ``ContentPipelineInputs`` for the content pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Union

try:
    from src.content_pipeline import ContentPipelineInputs
    from src.document_parsing import infer_owner_info, infer_plz
except ImportError:  # pragma: no cover - script execution fallback
    from content_pipeline import ContentPipelineInputs
    from document_parsing import infer_owner_info, infer_plz

RawListingInput = Union[Mapping[str, Any], str, Path]

DEFAULT_OUTPUT_LANGUAGE = "English"


def _build_pipeline_inputs(owner_info: Dict[str, Any]) -> ContentPipelineInputs:
    plz = str(owner_info.pop("plz", "")).strip()
    if not plz:
        inferred_plz = infer_plz(json.dumps(owner_info, ensure_ascii=True))
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
    owner_info = infer_owner_info(raw_input)
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
