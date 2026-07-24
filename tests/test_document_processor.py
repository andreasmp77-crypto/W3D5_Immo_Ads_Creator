from __future__ import annotations

from pathlib import Path

import pytest

from src.document_processor import content_pipeline_inputs_to_dict, normalize_owner_listing


def test_normalize_owner_listing_from_dict():
    raw = {
        "postal_code": "10115",
        "rooms": 3,
        "size": "84.3",
        "rent": "1415",
        "bathrooms": "1",
        "tone_of_ad": "warm and premium",
        "description": "Renovated old-building apartment.",
    }

    inputs = normalize_owner_listing(raw)

    assert inputs.plz == "10115"
    assert inputs.output_language == "English"
    assert inputs.tone_hint == "warm and premium"
    assert inputs.owner_info["size_sqm"] == "84.3"
    assert inputs.owner_info["rent_eur"] == "1415"
    assert inputs.owner_info["description"] == "Renovated old-building apartment."


def test_normalize_owner_listing_from_json_text():
    raw = (
        '{"plz":"10115","rooms":3,"size_sqm":84.3,"rent_eur":1415,'
        '"bathrooms":1,"description":"Text listing","output_language":"German"}'
    )

    inputs = normalize_owner_listing(raw)

    assert inputs.plz == "10115"
    assert inputs.output_language == "German"
    assert inputs.owner_info["rooms"] == 3
    assert inputs.owner_info["rent_eur"] == 1415


def test_normalize_owner_listing_from_txt_lines():
    raw = """
    headline: Westend apartment
    postal_code: 10115
    rooms: 3
    size: 84.3
    rent: 1415
    bathrooms: 1
    tone: premium
    description: Renovated old-building apartment.
    """

    inputs = normalize_owner_listing(raw)

    assert inputs.plz == "10115"
    assert inputs.tone_hint == "premium"
    assert inputs.owner_info["headline"] == "Westend apartment"


def test_normalize_owner_listing_requires_plz():
    with pytest.raises(ValueError, match="PLZ/postal code is required"):
        normalize_owner_listing({"rooms": 3, "rent": 1415})


def test_content_pipeline_inputs_to_dict_round_trip():
    inputs = normalize_owner_listing(
        {
            "plz": "10115",
            "rooms": 3,
            "rent": 1415,
            "tone": "warm",
        }
    )

    serialized = content_pipeline_inputs_to_dict(inputs)

    assert serialized["plz"] == "10115"
    assert serialized["tone_hint"] == "warm"
    assert serialized["owner_info"]["rooms"] == 3
