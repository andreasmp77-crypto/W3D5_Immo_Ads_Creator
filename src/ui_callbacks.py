"""Gradio callback functions for the ImmoAds UI."""

from __future__ import annotations

import os
import re
import tempfile
from typing import Any, Dict, Sequence

try:
    from src.content_pipeline import ContentPipelineInputs
    from src.pdf_export import (
        render_listing_pdf,
        render_listing_webpage_pdf,
        strip_markdown_for_plain_text,
    )
    from src.ui_shared import FORM_FIELD_NAMES, INTRO_HTML, REVIEW_INTRO_HTML
    from src.ui_validation import normalize_listing_submission
except ImportError:  # pragma: no cover - script execution fallback
    from content_pipeline import ContentPipelineInputs
    from pdf_export import render_listing_pdf, render_listing_webpage_pdf, strip_markdown_for_plain_text
    from ui_shared import FORM_FIELD_NAMES, INTRO_HTML, REVIEW_INTRO_HTML
    from ui_validation import normalize_listing_submission


try:  # Marker default so Gradio injects a live Progress; gradio is otherwise
    # imported lazily, so guard this for non-UI (test) environments.
    import gradio as _gr_progress_mod

    _PROGRESS_DEFAULT = _gr_progress_mod.Progress()
except Exception:  # pragma: no cover - gradio not installed
    _PROGRESS_DEFAULT = None


def _generate_listing_callback(*form_values: Any, progress=_PROGRESS_DEFAULT):
    """Run the content pipeline and switch the form into review mode."""

    import gradio as gr
    import threading
    import time

    # Resolve the app module (so tests can monkeypatch generate_content_draft /
    # verify_address_with_geopy on it) whether the package is imported as
    # `src.app` or, when src/ is on sys.path at runtime, as top-level `app`.
    try:
        from src import app as app_module
    except ModuleNotFoundError:  # pragma: no cover - depends on launch cwd
        import app as app_module

    def _tick(fraction: float, desc: str) -> None:
        if progress is not None:
            progress(fraction, desc=desc)

    _tick(0.05, "Validating address…")

    form_values_map = dict(zip(FORM_FIELD_NAMES, form_values))
    form_values_map["photos"] = [
        form_values_map.pop("photo_1", None),
        form_values_map.pop("photo_2", None),
        form_values_map.pop("photo_3", None),
    ]

    def _form_state(error_message: str, *, status_visible: bool = True):
        return (
            gr.update(value=INTRO_HTML),
            gr.update(value="", visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(value=error_message, visible=status_visible),
        )

    try:
        normalized, summary = normalize_listing_submission(
            strict_address_validation=True,
            verify_external_address=True,
            address_verifier=app_module.verify_address_with_geopy,
            **form_values_map,
        )
    except ValueError as exc:
        return _form_state(f"**Please complete the address fields before generating:** {exc}")

    owner_info = normalized["owner_info"]
    _tick(0.25, "Analyzing the neighborhood…")
    _tick(0.4, "Writing your listing with AI…")
    holder: Dict[str, Any] = {}

    def _run() -> None:
        try:
            inputs = ContentPipelineInputs(
                owner_info=owner_info,
                plz=normalized["plz"],
                output_language=normalized["output_language"],
                tone_hint=normalized["tone_hint"],
                additional_instructions=normalized["additional_instructions"],
            )
            holder["result"] = app_module.generate_content_draft(inputs)
        except Exception as exc:  # pragma: no cover - depends on external API availability
            holder["error"] = exc

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()
    pct = 0.4
    while worker.is_alive():
        time.sleep(0.4)
        pct = min(pct + 0.03, 0.9)
        _tick(pct, "Writing your listing with AI…")
    worker.join()

    if "error" in holder:
        return _form_state(f"**Could not generate the listing:** {holder['error']}")

    _tick(0.95, "Formatting your listing…")
    rendered_text = getattr(holder["result"], "reviewed_text", None) or holder["result"].draft_text
    cleaned_copy = strip_markdown_for_plain_text(rendered_text).strip()
    _tick(1.0, "Done")

    return (
        gr.update(value=REVIEW_INTRO_HTML),
        gr.update(value=cleaned_copy, visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(value="", visible=False),
    )


SAVE_EXPORT_FIELD_NAMES = FORM_FIELD_NAMES[:-3] + ["generated_ad_copy"]


def _slugify_filename(text: str, fallback: str = "listing") -> str:
    """Turn an address into a filesystem-safe filename stem (no extension)."""
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    slug = re.sub(r"[\s]+", "_", slug)
    return slug or fallback


def _save_and_export_pdf_callback(*form_values: Any) -> str:
    """Render the reviewed listing to a PDF that looks like the review page
    (browser-style "Print to PDF"), with all photos on one dedicated page.
    The downloaded filename is derived from the listing address, since
    Gradio's DownloadButton uses the returned path's basename as the file
    name it offers to the browser."""

    field_values = form_values[:-3]
    photo_paths = [p for p in form_values[-3:] if p]
    values_map = dict(zip(SAVE_EXPORT_FIELD_NAMES, field_values))
    ad_copy = str(values_map.get("generated_ad_copy") or "").strip()

    try:
        pdf_bytes = render_listing_webpage_pdf(values_map, ad_copy, photo_paths)
    except ImportError:
        fallback_sections = [
            ("Address", [
                f"{values_map.get('street_name') or ''} {values_map.get('house_number') or ''}".strip(),
                f"{values_map.get('postal_code') or ''} {values_map.get('city') or ''}".strip(),
            ]),
            ("Contact", [
                values_map.get("full_name"),
                values_map.get("phone_number"),
            ]),
            ("Property details", [
                values_map.get("living_area_sqm"),
                values_map.get("rooms"),
                values_map.get("bedrooms"),
                values_map.get("bathrooms"),
                values_map.get("heating_type"),
                values_map.get("energy_efficiency"),
                values_map.get("property_condition"),
                values_map.get("property_type"),
            ]),
            ("Costs", [
                values_map.get("cold_rent_eur"),
                values_map.get("nebenkosten_eur"),
                values_map.get("total_warm_rent_eur"),
            ]),
            ("Description", [
                ad_copy,
                values_map.get("fixtures_and_fittings"),
                values_map.get("location_note"),
            ]),
        ]
        pdf_bytes = render_listing_pdf(
            " ".join(
                str(part)
                for part in (
                    values_map.get("street_name"),
                    values_map.get("house_number"),
                    values_map.get("city"),
                )
                if part
            )
            or "Apartment Listing",
            "\n".join(
                str(line)
                for _section_title, section_lines in fallback_sections
                for line in section_lines
                if line not in (None, "")
            ),
        )

    address_parts = [
        values_map.get("street_name"),
        values_map.get("house_number"),
        values_map.get("postal_code"),
        values_map.get("city"),
    ]
    address = " ".join(str(p) for p in address_parts if p)
    filename = f"{_slugify_filename(address)}.pdf"

    # Write into a fresh temp directory (not tempfile.NamedTemporaryFile, whose
    # random name would otherwise become the download filename) so concurrent
    # exports don't collide on the same address-derived filename.
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, filename)
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)
    return tmp_path
