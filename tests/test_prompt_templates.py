from __future__ import annotations

from src.prompt_templates import (
    DEFAULT_BRAND_TONE_CHECKLIST,
    build_ad_generation_bundle,
)


def test_build_ad_generation_bundle_separates_prompt_sections():
    bundle = build_ad_generation_bundle(
        owner_info={"headline": "Westend apartment", "rooms": 3},
        primary_kb_context="PRIMARY KB TEXT",
        secondary_kb_context="SECONDARY KB TEXT",
        location_data="LOCATION TEXT",
        tone_hint="warm and premium",
        additional_instructions="Keep it concise.",
    )

    assert "You are writing a real-estate listing ad for a Berlin apartment." in bundle.system
    assert "Stay strictly within the facts provided below." in bundle.system
    assert "Owner info:" in bundle.user
    assert "Primary knowledge base:" in bundle.user
    assert "Secondary knowledge base:" in bundle.user
    assert "Location data:" in bundle.user
    assert "Brand tone checklist:" in bundle.user


def test_build_ad_generation_bundle_includes_brand_guardrails():
    bundle = build_ad_generation_bundle(
        owner_info={"headline": "Test"},
        primary_kb_context="PRIMARY KB TEXT",
        secondary_kb_context="SECONDARY KB TEXT",
        location_data="LOCATION TEXT",
    )

    for rule in DEFAULT_BRAND_TONE_CHECKLIST:
        assert rule in bundle.user


def test_build_ad_generation_bundle_uses_request_payload_shape():
    bundle = build_ad_generation_bundle(
        owner_info={"headline": "Test"},
        primary_kb_context="PRIMARY KB TEXT",
        secondary_kb_context="SECONDARY KB TEXT",
        location_data="LOCATION TEXT",
    )

    payload = bundle.as_request_payload()

    assert payload["instructions"] == bundle.system
    assert payload["input"] == bundle.user


def test_build_ad_generation_bundle_omits_missing_details_without_breaking_prompt():
    bundle = build_ad_generation_bundle(
        owner_info={"headline": "Test", "description": ""},
        primary_kb_context="PRIMARY KB TEXT",
        secondary_kb_context="SECONDARY KB TEXT",
        location_data=None,
    )

    assert "Not provided." in bundle.user
    assert "headline" in bundle.user
