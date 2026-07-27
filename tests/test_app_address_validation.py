from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from src import app as app_module
from src.app import (
    FORM_FIELD_NAMES,
    _generate_listing_callback,
    build_listing_payload,
    normalize_listing_submission,
    validate_address_payload,
)
from src.location_data import verify_address_with_geopy


def test_validate_address_payload_accepts_valid_berlin_address():
    errors, warnings = validate_address_payload(
        {
            "street_name": "Reichsstraße",
            "house_number": "100",
            "postal_code": "14050",
            "city": "Berlin",
        }
    )

    assert errors == []
    assert warnings == []


def test_validate_address_payload_rejects_bad_house_number_and_postal_code():
    errors, warnings = validate_address_payload(
        {
            "street_name": "Reichsstraße",
            "house_number": "house",
            "postal_code": "1405",
            "city": "Berlin",
        }
    )

    assert "House number must look like" in " ".join(errors)
    assert "Postal code must be a 5-digit Berlin PLZ." in errors
    assert warnings == []


def test_validate_address_payload_rejects_non_berlin_city():
    errors, warnings = validate_address_payload(
        {
            "street_name": "Reichsstraße",
            "house_number": "100",
            "postal_code": "14050",
            "city": "Munich",
        }
    )

    assert "This MVP only supports Berlin listings." in errors
    assert warnings == []


def test_validate_address_payload_warns_for_unknown_plz():
    errors, warnings = validate_address_payload(
        {
            "street_name": "Example Street",
            "house_number": "1",
            "postal_code": "99999",
            "city": "Berlin",
        }
    )

    assert errors == []
    assert warnings
    assert "not present in the local Berlin lookup data" in warnings[0]


def test_validate_address_payload_requires_address_fields_in_strict_mode():
    errors, warnings = validate_address_payload({}, strict_address_validation=True)

    assert "Street name is required." in errors
    assert "Postal code is required." in errors
    assert warnings == []


def test_normalize_listing_submission_raises_on_invalid_address():
    with pytest.raises(ValueError, match="Address validation failed"):
        normalize_listing_submission(
            strict_address_validation=True,
            street_name="",
            house_number="100",
            postal_code="14050",
            city="Berlin",
        )


def test_build_listing_payload_keeps_address_fields():
    payload = build_listing_payload(
        street_name="Reichsstraße",
        house_number="100",
        postal_code="14050",
        city="Berlin",
    )

    assert payload["street_name"] == "Reichsstraße"
    assert payload["postal_code"] == "14050"
    assert payload["city"] == "Berlin"


def test_generate_listing_callback_hides_debug_summary(monkeypatch):
    # Non-fatal address warnings (e.g. PLZ not in the local lookup, geopy not
    # installed) are developer-facing and must NOT be dumped onto the review
    # page; the status box stays hidden and generation still succeeds.
    fake_gradio = SimpleNamespace(update=lambda **kwargs: kwargs)
    monkeypatch.setitem(sys.modules, "gradio", fake_gradio)
    monkeypatch.setattr(
        app_module,
        "generate_content_draft",
        lambda _inputs: SimpleNamespace(draft_text="Generated copy **here**"),
    )

    form_values = {
        "street_name": "Example Street",
        "house_number": "1",
        "postal_code": "99999",
        "city": "Berlin",
    }
    ordered_values = [form_values.get(field, "") for field in FORM_FIELD_NAMES]

    result = _generate_listing_callback(*ordered_values)

    # index 0 = intro (switched to the review heading), index 1 = generated copy,
    # last = generation_status (hidden, no parsed-intake / warning dump).
    assert "Review your listing" in result[0]["value"]
    assert result[1]["value"] == "Generated copy here"
    assert result[-1]["visible"] is False
    assert result[-1]["value"] == ""


def test_validate_address_payload_uses_cached_geopy_verification(monkeypatch):
    verify_address_with_geopy.cache_clear()

    call_count = {"n": 0}

    class FakeLocation:
        latitude = 52.5
        longitude = 13.4
        address = "Reichsstraße 100, 14050 Berlin, Germany"
        raw = {"address": {"postcode": "14050", "city": "Berlin"}}

    def fake_geocode(query, **kwargs):
        call_count["n"] += 1
        return FakeLocation()

    monkeypatch.setattr("src.location_data._get_geopy_geocode", lambda: fake_geocode)

    first = verify_address_with_geopy("Reichsstraße", "100", "14050", "Berlin")
    second = verify_address_with_geopy("Reichsstraße", "100", "14050", "Berlin")

    assert first.verified is True
    assert second.verified is True
    assert first.message == "Address verified by the external geocoding service."
    assert call_count["n"] == 1
