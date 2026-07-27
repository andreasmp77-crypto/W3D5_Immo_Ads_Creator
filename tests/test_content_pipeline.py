from __future__ import annotations

from src.content_pipeline import (
    ContentPipelineInputs,
    build_generation_request,
    build_publish_payload,
    collect_pipeline_context,
    generate_content_draft,
    run_content_pipeline,
)
from src.llm_integration import AdGenerationResult


def test_collect_pipeline_context(monkeypatch):
    monkeypatch.setattr("src.content_pipeline.get_primary_kb_context", lambda: "PRIMARY CONTEXT")
    monkeypatch.setattr("src.content_pipeline.get_secondary_kb_context", lambda: "SECONDARY CONTEXT")
    monkeypatch.setattr("src.content_pipeline.get_location_summary", lambda plz: f"LOCATION {plz}")

    inputs = ContentPipelineInputs(owner_info={"headline": "Test"}, plz="10115")
    context = collect_pipeline_context(inputs)

    assert context["primary_kb_context"] == "PRIMARY CONTEXT"
    assert context["secondary_kb_context"] == "SECONDARY CONTEXT"
    assert context["location_summary"] == "LOCATION 10115"


def test_build_generation_request():
    inputs = ContentPipelineInputs(
        owner_info={"headline": "Test"},
        plz="10115",
        output_language="German",
        tone_hint="premium",
        additional_instructions="Keep it concise.",
    )
    request = build_generation_request(
        inputs,
        primary_kb_context="PRIMARY",
        secondary_kb_context="SECONDARY",
        location_summary="LOCATION",
    )

    assert request.owner_info["headline"] == "Test"
    assert request.output_language == "German"
    assert request.tone_hint == "premium"
    assert request.additional_instructions == "Keep it concise."


def test_generate_content_draft_uses_llm_stub(monkeypatch):
    monkeypatch.setattr("src.content_pipeline.get_primary_kb_context", lambda: "PRIMARY CONTEXT")
    monkeypatch.setattr("src.content_pipeline.get_secondary_kb_context", lambda: "SECONDARY CONTEXT")
    monkeypatch.setattr(
        "src.content_pipeline.get_location_summary",
        lambda plz: (
            "=== FACTUAL LOCATION DATA (ZIP CODE 10115) ===\n\n"
            "Kitas: 25 registered in this PLZ, including Example Kita.\n\n"
            "Schools: 10 registered in this PLZ, including Example School.\n\n"
            "Public transport: nearby stops include Example Stop (250m)."
        ),
    )

    def fake_generate_ad_copy(request, api_key=None):
        return AdGenerationResult(draft_text="Draft body", model="test-model")

    monkeypatch.setattr("src.content_pipeline.generate_ad_copy", fake_generate_ad_copy)

    result = generate_content_draft(ContentPipelineInputs(owner_info={"headline": "Test"}, plz="10115"))

    assert result.draft_text == "Draft body"
    assert "Kitas: 25 registered in this PLZ" in result.reviewed_text
    assert "Public transport: nearby stops include Example Stop (250m)." in result.reviewed_text
    assert "Location facts:" in result.reviewed_text
    assert "Kitas: 25 registered in this PLZ" in result.location_summary


def test_run_content_pipeline_allows_review_edit(monkeypatch):
    monkeypatch.setattr("src.content_pipeline.get_primary_kb_context", lambda: "PRIMARY CONTEXT")
    monkeypatch.setattr("src.content_pipeline.get_secondary_kb_context", lambda: "SECONDARY CONTEXT")
    monkeypatch.setattr("src.content_pipeline.get_location_summary", lambda plz: f"LOCATION {plz}")

    def fake_generate_ad_copy(request, api_key=None):
        return AdGenerationResult(draft_text="Draft body", model="test-model")

    monkeypatch.setattr("src.content_pipeline.generate_ad_copy", fake_generate_ad_copy)

    result = run_content_pipeline(
        ContentPipelineInputs(owner_info={"headline": "Test"}, plz="10115"),
        reviewer=lambda draft: draft.replace("Draft", "Reviewed"),
    )

    assert result.reviewed_text == "Reviewed body"
    payload = build_publish_payload(result)
    assert payload["headline"] == "Test"
    assert payload["body"] == "Reviewed body"
