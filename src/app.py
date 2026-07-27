"""Compatibility wrapper for the ImmoAds Gradio UI."""

from __future__ import annotations

try:
    from src.content_pipeline import ContentPipelineInputs, generate_content_draft
    from src.location_data import verify_address_with_geopy
    from src.ui_callbacks import _generate_listing_callback, _save_and_export_pdf_callback
    from src.ui_layout import (
        BANNER_HTML,
        CUSTOM_CSS,
        DEFAULT_SAMPLE_LISTING,
        ENERGY_OPTIONS,
        FORM_FIELD_NAMES,
        HEATING_OPTIONS,
        INTRO_HTML,
        PROPERTY_CONDITIONS,
        PROPERTY_TYPES,
        REVIEW_INTRO_HTML,
        TONES,
        _section_header,
        create_app,
        launch,
    )
    from src.ui_validation import (
        build_listing_payload,
        normalize_listing_submission,
        validate_address_payload,
    )
except ImportError:  # pragma: no cover - script execution fallback
    from content_pipeline import ContentPipelineInputs, generate_content_draft
    from location_data import verify_address_with_geopy
    from ui_callbacks import _generate_listing_callback, _save_and_export_pdf_callback
    from ui_layout import (
        BANNER_HTML,
        CUSTOM_CSS,
        DEFAULT_SAMPLE_LISTING,
        ENERGY_OPTIONS,
        FORM_FIELD_NAMES,
        HEATING_OPTIONS,
        INTRO_HTML,
        PROPERTY_CONDITIONS,
        PROPERTY_TYPES,
        REVIEW_INTRO_HTML,
        TONES,
        _section_header,
        create_app,
        launch,
    )
    from ui_validation import (
        build_listing_payload,
        normalize_listing_submission,
        validate_address_payload,
    )


if __name__ == "__main__":
    launch()
