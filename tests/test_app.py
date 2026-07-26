from __future__ import annotations

import json

from src.app import build_listing_payload, normalize_listing_submission


def test_build_listing_payload_keeps_only_expected_fields():
    payload = build_listing_payload(
        plz="14050",
        rooms=3,
        size_sqm=84.3,
        rent_eur=1415,
        bathrooms=1,
        description="Renovated old-building apartment.",
        tone="warm and premium",
        pictures=["/tmp/front-view.jpg", "living-room.png"],
    )

    assert payload["plz"] == "14050"
    assert payload["rooms"] == 3
    assert payload["size_sqm"] == 84.3
    assert payload["rent_eur"] == 1415
    assert payload["bathrooms"] == 1
    assert payload["pictures"] == ["front-view.jpg", "living-room.png"]


def test_normalize_listing_submission_returns_parsed_json():
    normalized, summary = normalize_listing_submission(
        plz="14050",
        rooms=3,
        size_sqm=84.3,
        rent_eur=1415,
        bathrooms=1,
        description="Renovated old-building apartment with balcony.",
        tone="warm and premium",
        pictures=["front-view.jpg"],
    )

    assert normalized["plz"] == "14050"
    assert normalized["owner_info"]["rooms"] == 3
    assert normalized["owner_info"]["rent_eur"] == 1415
    assert normalized["owner_info"]["pictures"] == ["front-view.jpg"]

    parsed = json.loads(json.dumps(normalized))
    assert parsed["owner_info"]["description"] == "Renovated old-building apartment with balcony."
    assert "- PLZ: `14050`" in summary
    assert "Pictures: `front-view.jpg`" in summary
