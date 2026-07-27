"""Service layer for ImmoAds content generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

try:
    from src.knowledge_base import get_primary_kb_context, get_secondary_kb_context
    from src.llm_integration import AdGenerationRequest, AdGenerationResult, generate_ad_copy
    from src.location_data import get_location_summary
except ImportError:  # pragma: no cover - script execution fallback
    from knowledge_base import get_primary_kb_context, get_secondary_kb_context
    from llm_integration import AdGenerationRequest, AdGenerationResult, generate_ad_copy
    from location_data import get_location_summary

ReviewCallback = Callable[[str], str]


@dataclass(frozen=True)
class ContentPipelineInputs:
    """Inputs required to generate one ad draft."""

    owner_info: Mapping[str, Any]
    plz: str
    output_language: str = "English"
    tone_hint: Optional[str] = None
    additional_instructions: Optional[str] = None


@dataclass(frozen=True)
class ContentPipelineResult:
    """Output of the full content pipeline."""

    owner_info: Mapping[str, Any]
    location_summary: str
    primary_kb_context: str
    secondary_kb_context: str
    generation_request: AdGenerationRequest
    generation_result: AdGenerationResult
    reviewed_text: str
    review_notes: Optional[str] = None
    published_text: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "published_text", self.reviewed_text.strip())

    @property
    def draft_text(self) -> str:
        return self.generation_result.draft_text

    def as_dict(self) -> Dict[str, Any]:
        """Return a serializable snapshot for UI or API use."""
        return {
            "owner_info": dict(self.owner_info),
            "location_summary": self.location_summary,
            "primary_kb_context": self.primary_kb_context,
            "secondary_kb_context": self.secondary_kb_context,
            "draft_text": self.draft_text,
            "reviewed_text": self.reviewed_text,
            "published_text": self.published_text,
            "review_notes": self.review_notes,
            "model": self.generation_result.model,
        }


@dataclass(frozen=True)
class ContentPipelineService:
    """Dependency-injected service for building and running the pipeline."""

    primary_kb_loader: Callable[[], str] = get_primary_kb_context
    secondary_kb_loader: Callable[[], str] = get_secondary_kb_context
    location_summary_loader: Callable[[str], str] = get_location_summary
    generation_runner: Callable[..., AdGenerationResult] = generate_ad_copy

    def collect_pipeline_context(self, inputs: ContentPipelineInputs) -> Dict[str, str]:
        primary_kb_context = self.primary_kb_loader()
        secondary_kb_context = self.secondary_kb_loader()
        location_summary = self.location_summary_loader(inputs.plz)
        return {
            "primary_kb_context": primary_kb_context,
            "secondary_kb_context": secondary_kb_context,
            "location_summary": location_summary,
        }

    def build_generation_request(
        self,
        inputs: ContentPipelineInputs,
        *,
        primary_kb_context: str,
        secondary_kb_context: str,
        location_summary: str,
    ) -> AdGenerationRequest:
        return AdGenerationRequest(
            owner_info=inputs.owner_info,
            primary_kb_context=primary_kb_context,
            secondary_kb_context=secondary_kb_context,
            location_data=location_summary,
            output_language=inputs.output_language,
            tone_hint=inputs.tone_hint,
            additional_instructions=inputs.additional_instructions,
        )

    def generate_content_draft(
        self,
        inputs: ContentPipelineInputs,
        *,
        api_key: Optional[str] = None,
    ) -> ContentPipelineResult:
        context = self.collect_pipeline_context(inputs)
        request = self.build_generation_request(
            inputs,
            primary_kb_context=context["primary_kb_context"],
            secondary_kb_context=context["secondary_kb_context"],
            location_summary=context["location_summary"],
        )
        generation_result = self.generation_runner(request, api_key=api_key)
        reviewed_text = generation_result.draft_text

        return ContentPipelineResult(
            owner_info=inputs.owner_info,
            location_summary=context["location_summary"],
            primary_kb_context=context["primary_kb_context"],
            secondary_kb_context=context["secondary_kb_context"],
            generation_request=request,
            generation_result=generation_result,
            reviewed_text=reviewed_text,
        )

    def review_draft_text(self, draft_text: str, reviewer: Optional[ReviewCallback] = None) -> str:
        if reviewer is not None:
            edited_text = reviewer(draft_text)
            return edited_text.strip() or draft_text.strip()

        try:
            import sys

            if not sys.stdin.isatty():
                return draft_text.strip()

            print("\n--- REVIEW DRAFT ---")
            print("Press Enter on an empty line to keep the current version.")
            print("Paste an edited version below and end with EOF / Ctrl-D:")
            print("\nCurrent draft:\n")
            print(draft_text)
            print("\nEdited draft:")
            edited_lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                edited_lines.append(line)
            edited_text = "\n".join(edited_lines).strip()
            return edited_text or draft_text.strip()
        except Exception:
            return draft_text.strip()

    def run_content_pipeline(
        self,
        inputs: ContentPipelineInputs,
        *,
        api_key: Optional[str] = None,
        reviewer: Optional[ReviewCallback] = None,
    ) -> ContentPipelineResult:
        draft_result = self.generate_content_draft(inputs, api_key=api_key)
        reviewed_text = self.review_draft_text(draft_result.draft_text, reviewer=reviewer)

        return ContentPipelineResult(
            owner_info=draft_result.owner_info,
            location_summary=draft_result.location_summary,
            primary_kb_context=draft_result.primary_kb_context,
            secondary_kb_context=draft_result.secondary_kb_context,
            generation_request=draft_result.generation_request,
            generation_result=draft_result.generation_result,
            reviewed_text=reviewed_text,
            review_notes=None if reviewed_text == draft_result.draft_text.strip() else "Edited during human review.",
        )

    def build_publish_payload(self, result: ContentPipelineResult) -> Dict[str, Any]:
        return {
            "headline": result.owner_info.get("headline") or "Apartment Ad",
            "body": result.published_text,
            "location_summary": result.location_summary,
            "owner_info": dict(result.owner_info),
            "review_notes": result.review_notes,
        }


DEFAULT_SERVICE = ContentPipelineService()

