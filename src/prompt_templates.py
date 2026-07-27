"""Prompt assembly helpers for ad generation.

The project keeps factual inputs separate from knowledge-base prose so the
LLM can use owner data, KB context, and PLZ lookup results without blending
them together.
"""

from __future__ import annotations

from dataclasses import dataclass
from json import dumps
from typing import Any, Dict, List, Mapping, Optional, Sequence

DEFAULT_BRAND_TONE_CHECKLIST: Sequence[str] = (
    "Keep the tone professional, warm, and publication-ready.",
    "Use only facts present in the provided owner info, KB context, and location data.",
    "Do not invent amenities, distances, certifications, or neighborhood claims.",
    "Highlight the strongest property benefits without sounding generic or exaggerated.",
    "Do not repeat the same information more than once.",
    "Omit any detail that is missing or uncertain instead of filling gaps."
)

DEFAULT_OUTPUT_LANGUAGE = "English"


@dataclass(frozen=True)
class PromptBundle:
    """Container for the messages sent to the LLM."""

    system: str
    user: str

    def as_messages(self) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]

    def as_request_payload(self) -> Dict[str, str]:
        return {"instructions": self.system, "input": self.user}


def _stringify_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return dumps(value, ensure_ascii=True, indent=2, sort_keys=True)
    if isinstance(value, (list, tuple, set)):
        return dumps(list(value), ensure_ascii=True, indent=2)
    return str(value).strip()


def format_section(title: str, value: Any) -> str:
    content = _stringify_value(value)
    if not content:
        content = "Not provided."
    return f"{title}:\n{content}"


def format_context_block(title: str, values: Any) -> str:
    if values is None:
        return f"{title}:\nNot provided."
    if isinstance(values, Mapping):
        body_lines = []
        for key, value in values.items():
            body_lines.append(f"- {key}: {_stringify_value(value) or 'Not provided.'}")
        body = "\n".join(body_lines) if body_lines else "Not provided."
        return f"{title}:\n{body}"
    if isinstance(values, (list, tuple, set)):
        body_lines = [f"- {_stringify_value(item)}" for item in values if _stringify_value(item)]
        body = "\n".join(body_lines) if body_lines else "Not provided."
        return f"{title}:\n{body}"
    content = _stringify_value(values)
    return f"{title}:\n{content or 'Not provided.'}"


def build_ad_generation_bundle(
    *,
    owner_info: Mapping[str, Any],
    primary_kb_context: Any,
    secondary_kb_context: Any,
    location_data: Any,
    output_language: str = DEFAULT_OUTPUT_LANGUAGE,
    tone_hint: Optional[str] = None,
    additional_instructions: Optional[str] = None,
    brand_tone_checklist: Optional[Sequence[str]] = None,
) -> PromptBundle:
    """Build a prompt bundle that keeps each input source separate."""

    checklist = brand_tone_checklist or DEFAULT_BRAND_TONE_CHECKLIST
    system_prompt = "\n".join(
        [
            "You are writing a real-estate listing ad for a Berlin apartment.",
            f"Write the final copy in {output_language}.",
            "Use a professional, trustworthy, and distinctive tone.",
            "Stay strictly within the facts provided below.",
        "If a fact is missing, omit it rather than inventing it.",
        "Always include the provided location facts when they exist, especially Kita and public transport facts.",
        "Do not repeat the same information more than once.",
        "Do not mention that you are an AI model or refer to internal prompting.",
        ]
    )

    user_sections = [
        format_section("Owner info", owner_info),
        format_context_block("Primary knowledge base", primary_kb_context),
        format_context_block("Secondary knowledge base", secondary_kb_context),
        format_context_block("Location data", location_data),
        format_context_block("Tone hint", tone_hint or "Use the strongest suitable brand-aligned tone."),
        format_context_block("Additional instructions", additional_instructions),
        format_context_block("Brand tone checklist", list(checklist)),
        "Output requirements:\n"
        "- Produce publish-ready ad copy.\n"
        "- Keep it concrete, natural, and non-generic.\n"
        "- Do not add unsupported claims.\n"
        "- Include the provided Kita and public transport facts if they are present in the location data.\n"
        "- If the public transport section says data unavailable, state that briefly rather than omitting it.\n"
        "- Do not repeat the same information more than once.\n"
        "- If useful, emphasize location and apartment strengths in a balanced way.",
    ]

    return PromptBundle(system=system_prompt, user="\n\n".join(user_sections))


def build_ad_generation_messages(
    *,
    owner_info: Mapping[str, Any],
    primary_kb_context: Any,
    secondary_kb_context: Any,
    location_data: Any,
    output_language: str = DEFAULT_OUTPUT_LANGUAGE,
    tone_hint: Optional[str] = None,
    additional_instructions: Optional[str] = None,
    brand_tone_checklist: Optional[Sequence[str]] = None,
) -> List[Dict[str, str]]:
    """Return the prompt as chat-style messages for the Responses API."""

    return build_ad_generation_bundle(
        owner_info=owner_info,
        primary_kb_context=primary_kb_context,
        secondary_kb_context=secondary_kb_context,
        location_data=location_data,
        output_language=output_language,
        tone_hint=tone_hint,
        additional_instructions=additional_instructions,
        brand_tone_checklist=brand_tone_checklist,
    ).as_messages()
