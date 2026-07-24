"""OpenAI integration for generating ad copy.

This module is intentionally narrow: it assembles the prompt from the
owner-provided listing details, the loaded KB context, and the PLZ lookup
data, then calls the Responses API and returns the generated draft text.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from prompt_templates import (
    DEFAULT_BRAND_TONE_CHECKLIST,
    DEFAULT_OUTPUT_LANGUAGE,
    build_ad_generation_bundle,
)

# Default to a lower-cost model; override with IMMOADS_LLM_MODEL when needed.
DEFAULT_MODEL = os.getenv("IMMOADS_LLM_MODEL", "gpt-4o-mini")
DEFAULT_REASONING_EFFORT = os.getenv("IMMOADS_REASONING_EFFORT", "medium")


@dataclass(frozen=True)
class AdGenerationRequest:
    """Structured inputs for a single ad-generation run."""

    owner_info: Mapping[str, Any]
    primary_kb_context: Any
    secondary_kb_context: Any
    location_data: Any
    output_language: str = DEFAULT_OUTPUT_LANGUAGE
    tone_hint: Optional[str] = None
    additional_instructions: Optional[str] = None
    brand_tone_checklist: Sequence[str] = field(default_factory=lambda: tuple(DEFAULT_BRAND_TONE_CHECKLIST))
    model: str = DEFAULT_MODEL
    reasoning_effort: Optional[str] = DEFAULT_REASONING_EFFORT
    max_output_tokens: Optional[int] = 900


@dataclass(frozen=True)
class AdGenerationResult:
    """Normalized response returned from the LLM."""

    draft_text: str
    model: str
    raw_response: Any = None
    usage: Any = None
    messages: List[Dict[str, str]] = field(default_factory=list)


def create_openai_client(api_key: Optional[str] = None) -> Any:
    """Create an OpenAI client lazily so the module remains import-safe."""

    if api_key is None:
        # Read the API key from the environment unless a caller passes one in.
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise ImportError("The openai package is required to generate ad copy.") from exc

    return OpenAI(api_key=api_key)


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def extract_response_text(response: Any) -> str:
    """Extract assistant text from a Responses API result.

    The SDK exposes convenience properties on current response objects, but we
    also support a few fallback shapes so the module is tolerant of SDK
    variants.
    """

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        # Newer SDK responses often expose the full assistant text directly.
        return output_text.strip()

    output = getattr(response, "output", None)
    if not output:
        return ""

    parts: List[str] = []
    for item in output:
        item_type = getattr(item, "type", None) or getattr(item, "kind", None)
        if item_type == "message":
            # Walk message content blocks and collect any text fragments.
            content = getattr(item, "content", None) or []
            for content_item in content:
                content_type = getattr(content_item, "type", None)
                if content_type in {"output_text", "text"}:
                    text = getattr(content_item, "text", None)
                    if text is None and isinstance(content_item, Mapping):
                        text = content_item.get("text")
                    text = _coerce_text(text).strip()
                    if text:
                        parts.append(text)

    return "\n\n".join(parts).strip()


def build_generation_bundle(request: AdGenerationRequest) -> Any:
    # Keep prompt construction in one place so prompt changes stay easy to review.
    return build_ad_generation_bundle(
        owner_info=request.owner_info,
        primary_kb_context=request.primary_kb_context,
        secondary_kb_context=request.secondary_kb_context,
        location_data=request.location_data,
        output_language=request.output_language,
        tone_hint=request.tone_hint,
        additional_instructions=request.additional_instructions,
        brand_tone_checklist=request.brand_tone_checklist,
    )


def generate_ad_copy(
    request: AdGenerationRequest,
    *,
    api_key: Optional[str] = None,
) -> AdGenerationResult:
    """Generate a draft apartment ad via the OpenAI Responses API."""

    client = create_openai_client(api_key=api_key)
    # Build a single request bundle from owner data, KB context, and location facts.
    bundle = build_generation_bundle(request)
    request_payload = bundle.as_request_payload()

    # Send the assembled prompt to the Responses API.
    create_kwargs: Dict[str, Any] = {"model": request.model, **request_payload}
    if request.reasoning_effort:
        create_kwargs["reasoning"] = {"effort": request.reasoning_effort}
    if request.max_output_tokens is not None:
        create_kwargs["max_output_tokens"] = request.max_output_tokens

    response = client.responses.create(**create_kwargs)
    # Normalize the returned text so downstream code gets a plain draft string.
    draft_text = extract_response_text(response)
    if not draft_text:
        raise RuntimeError("The LLM response did not contain any text output.")

    return AdGenerationResult(
        draft_text=draft_text,
        model=request.model,
        raw_response=response,
        usage=getattr(response, "usage", None),
        messages=bundle.as_messages(),
    )
