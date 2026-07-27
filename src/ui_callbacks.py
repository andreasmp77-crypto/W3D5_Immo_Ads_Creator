"""Gradio callback functions for the ImmoAds UI."""

from __future__ import annotations

import tempfile
from typing import Any, Dict, Sequence

try:
    from src.content_pipeline import ContentPipelineInputs
    from src.pdf_export import render_listing_webpage_pdf, strip_markdown_for_plain_text
    from src.ui_layout import FORM_FIELD_NAMES, INTRO_HTML, REVIEW_INTRO_HTML
    from src.ui_validation import normalize_listing_submission
except ImportError:  # pragma: no cover - script execution fallback
    from content_pipeline import ContentPipelineInputs
    from pdf_export import render_listing_webpage_pdf, strip_markdown_for_plain_text
    from ui_layout import FORM_FIELD_NAMES, INTRO_HTML, REVIEW_INTRO_HTML
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

    from src import app as app_module

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
    cleaned_copy = strip_markdown_for_plain_text(holder["result"].draft_text).strip()
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


def _save_and_export_pdf_callback(*form_values: Any) -> str:
    """Render the reviewed listing to a PDF that looks like the review page
    (browser-style "Print to PDF"), with all photos on one dedicated page."""

    field_values = form_values[:-3]
    photo_paths = [p for p in form_values[-3:] if p]
    values_map = dict(zip(SAVE_EXPORT_FIELD_NAMES, field_values))
    ad_copy = str(values_map.get("generated_ad_copy") or "").strip()

    pdf_bytes = render_listing_webpage_pdf(values_map, ad_copy, photo_paths)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp_file.write(pdf_bytes)
    tmp_file.close()
    return tmp_file.name
