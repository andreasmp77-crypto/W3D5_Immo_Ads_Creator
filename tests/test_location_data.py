from __future__ import annotations

from src.location_data import (
    PlzSpatialSummary,
    fetch_nearby_transit,
    get_location_summary,
    get_plz_spatial_summary,
    load_kita_data,
)


def test_plz_spatial_summary_for_known_plz():
    summary = get_plz_spatial_summary("10115")

    assert isinstance(summary, PlzSpatialSummary)
    assert summary.plz == "10115"
    assert summary.district == "Mitte"
    assert summary.record_count > 0
    assert summary.centroid_xy is not None


def test_location_summary_contains_counts_and_transit_fallback():
    summary = get_location_summary("10115")

    assert "ZIP CODE 10115" in summary
    assert "Daycares & Schools:" in summary
    assert "Public transport:" in summary


def test_load_kita_data_is_non_empty_for_known_plz():
    text = load_kita_data("10115")
    assert "Kita" in text
    assert "school" in text.lower()


def test_fetch_nearby_transit_uses_deterministic_fallback():
    text = fetch_nearby_transit("10115")
    assert "centroid-based lookup" in text
