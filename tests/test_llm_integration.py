from __future__ import annotations

from types import SimpleNamespace

from src.llm_integration import (
    AdGenerationRequest,
    build_generation_bundle,
    extract_response_text,
    _model_supports_reasoning,
)


def test_extract_response_text_from_output_text():
    response = SimpleNamespace(output_text=" Draft text ")
    assert extract_response_text(response) == "Draft text"


def test_extract_response_text_from_message_blocks():
    response = SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                content=[
                    SimpleNamespace(type="text", text="Hello"),
                    SimpleNamespace(type="output_text", text=" world"),
                ],
            )
        ]
    )

    assert extract_response_text(response) == "Hello\n\nworld"


def test_model_supports_reasoning_guard():
    assert _model_supports_reasoning("gpt-5.1") is True
    assert _model_supports_reasoning("gpt-4o-mini") is False


def test_build_generation_bundle_keeps_separate_sections():
    request = AdGenerationRequest(
        owner_info={"headline": "Test"},
        primary_kb_context="PRIMARY",
        secondary_kb_context="SECONDARY",
        location_data="LOCATION",
    )

    bundle = build_generation_bundle(request)
    messages = bundle.as_messages()

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Owner info" in messages[1]["content"]
    assert "Primary knowledge base" in messages[1]["content"]
    assert "Location data" in messages[1]["content"]
