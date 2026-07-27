"""
Compare prompt variants for ad generation.

This script is for prompt engineering experiments. It can:
- print the assembled prompt for each variant, or
- optionally call the live OpenAI API and print the resulting draft copy.

Usage examples:
    python scripts/compare_prompts.py
    python scripts/compare_prompts.py --live
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from textwrap import indent

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"

for path in (ROOT, SRC_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from src.content_pipeline import ContentPipelineInputs, build_generation_request
from src.knowledge_base import get_primary_kb_context, get_secondary_kb_context
from src.llm_integration import AdGenerationRequest, generate_ad_copy
from src.prompt_templates import build_ad_generation_bundle


def build_sample_inputs() -> ContentPipelineInputs:
    """Create a small, reusable example input for prompt experiments."""

    return ContentPipelineInputs(
        owner_info={
            "headline": "Westend 3-room apartment",
            "rooms": 3,
            "size_sqm": 84.3,
            "rent_eur": 1415,
            "bathrooms": 1,
            "description": "Renovated old-building apartment with balcony and fitted kitchen.",
        },
        plz="14050",
        output_language="English",
        tone_hint="warm, premium, and trustworthy",
        additional_instructions="Highlight the renovated condition and quiet side-street setting.",
    )


def build_variants(base_request: AdGenerationRequest) -> list[tuple[str, AdGenerationRequest]]:
    """Return a few prompt variants to compare side by side."""

    return [
        ("baseline", base_request),
        (
            "more premium",
            replace(
                base_request,
                tone_hint="elevated, polished, and editorial",
                additional_instructions="Use more premium language, but stay factual and avoid hype.",
            ),
        ),
        (
            "more concise",
            replace(
                base_request,
                tone_hint="clear, concise, and practical",
                additional_instructions="Keep the copy shorter and focus on the strongest selling points.",
            ),
        ),
    ]


def print_prompt_preview(label: str, request: AdGenerationRequest) -> None:
    """Print the assembled prompt so you can inspect it without calling the API."""

    bundle = build_ad_generation_bundle(
        owner_info=request.owner_info,
        primary_kb_context=request.primary_kb_context,
        secondary_kb_context=request.secondary_kb_context,
        location_data=request.location_data,
        output_language=request.output_language,
        tone_hint=request.tone_hint,
        additional_instructions=request.additional_instructions,
        brand_tone_checklist=request.brand_tone_checklist,
    )

    print(f"\n=== {label.upper()} ===")
    print("SYSTEM:")
    print(indent(bundle.system, "  "))
    print("USER:")
    print(indent(bundle.user, "  "))


def run_live_generation(label: str, request: AdGenerationRequest) -> None:
    """Call the live API for a single prompt variant."""

    result = generate_ad_copy(request)
    print(f"\n=== {label.upper()} ===")
    print(result.draft_text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ad-generation prompt variants.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Send each prompt variant to the OpenAI API and print the draft output.",
    )
    args = parser.parse_args()

    inputs = build_sample_inputs()
    primary_kb_context = get_primary_kb_context()
    secondary_kb_context = get_secondary_kb_context()
    location_summary = (
        "PLZ 14050 sample location summary: nearby schools, transit, and Kita details "
        "should be inserted here from the location data layer."
    )
    base_request = build_generation_request(
        inputs,
        primary_kb_context=primary_kb_context,
        secondary_kb_context=secondary_kb_context,
        location_summary=location_summary,
    )

    variants = build_variants(base_request)

    for label, request in variants:
        if args.live:
            run_live_generation(label, request)
        else:
            print_prompt_preview(label, request)


if __name__ == "__main__":
    main()
