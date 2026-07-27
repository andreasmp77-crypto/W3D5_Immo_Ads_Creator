"""Compatibility facade for the ImmoAds content flow."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

try:
    from src.content_service import (
        ContentPipelineInputs,
        ContentPipelineResult,
        ContentPipelineService,
        ReviewCallback,
    )
    from src.knowledge_base import get_primary_kb_context, get_secondary_kb_context
    from src.llm_integration import AdGenerationRequest, AdGenerationResult, generate_ad_copy
    from src.location_data import get_location_summary
except ImportError:  # pragma: no cover - script execution fallback
    from content_service import (
        ContentPipelineInputs,
        ContentPipelineResult,
        ContentPipelineService,
        ReviewCallback,
    )
    from knowledge_base import get_primary_kb_context, get_secondary_kb_context
    from llm_integration import AdGenerationRequest, AdGenerationResult, generate_ad_copy
    from location_data import get_location_summary


def _service() -> ContentPipelineService:
    """Build a service using the current module-level dependencies."""

    return ContentPipelineService(
        primary_kb_loader=get_primary_kb_context,
        secondary_kb_loader=get_secondary_kb_context,
        location_summary_loader=get_location_summary,
        generation_runner=generate_ad_copy,
    )


def collect_pipeline_context(inputs: ContentPipelineInputs) -> Dict[str, str]:
    return _service().collect_pipeline_context(inputs)


def build_generation_request(
    inputs: ContentPipelineInputs,
    *,
    primary_kb_context: str,
    secondary_kb_context: str,
    location_summary: str,
) -> AdGenerationRequest:
    return _service().build_generation_request(
        inputs,
        primary_kb_context=primary_kb_context,
        secondary_kb_context=secondary_kb_context,
        location_summary=location_summary,
    )


def generate_content_draft(
    inputs: ContentPipelineInputs,
    *,
    api_key: Optional[str] = None,
) -> ContentPipelineResult:
    return _service().generate_content_draft(inputs, api_key=api_key)


def review_draft_text(draft_text: str, reviewer: Optional[ReviewCallback] = None) -> str:
    return _service().review_draft_text(draft_text, reviewer=reviewer)


def run_content_pipeline(
    inputs: ContentPipelineInputs,
    *,
    api_key: Optional[str] = None,
    reviewer: Optional[ReviewCallback] = None,
) -> ContentPipelineResult:
    return _service().run_content_pipeline(inputs, api_key=api_key, reviewer=reviewer)


def build_publish_payload(result: ContentPipelineResult) -> Dict[str, Any]:
    return _service().build_publish_payload(result)

