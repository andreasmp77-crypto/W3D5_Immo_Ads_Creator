from __future__ import annotations

import json

from src.location_data import (
    PlzSpatialSummary,
    fetch_nearby_transit,
    get_location_summary,
    get_neighboring_plz,
    get_plz_spatial_summary,
    load_kita_data,
)


def test_plz_spatial_summary_for_known_plz():
    summary = get_plz_spatial_summary("10115")

    assert isinstance(summary, PlzSpatialSummary)
    assert summary.plz == "10115"
    assert summary.district == "Mitte"
    assert summary.record_count > 0
    assert summary.centroid_latlon is not None


def test_plz_spatial_summary_for_unknown_plz_is_honest():
    summary = get_plz_spatial_summary("00000")

    assert summary.record_count == 0
    assert summary.centroid_latlon is None


def test_load_kita_data_returns_real_names_for_known_plz():
    text = load_kita_data("10115")
    assert "Kitas:" in text
    assert "registered" in text


def test_load_kita_data_is_honest_for_unknown_plz():
    text = load_kita_data("00000")
    assert "no data available" in text


def test_fetch_nearby_transit_uses_live_lookup(monkeypatch):
    monkeypatch.setattr("src.location_data._transit_cache", {})
    fake_response = json.dumps(
        [
            {"type": "stop", "name": "U Rosa-Luxemburg-Platz (Berlin)"},
            {"type": "stop", "name": "Mollstr./Prenzlauer Allee (Berlin)"},
        ]
    ).encode("utf-8")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return fake_response

    monkeypatch.setattr("src.location_data.urllib.request.urlopen", lambda url, timeout=5: FakeResponse())

    text = fetch_nearby_transit("10115")
    assert "U Rosa-Luxemburg-Platz" in text
    assert "Mollstr./Prenzlauer Allee" in text


def test_fetch_nearby_transit_fails_closed_on_api_error(monkeypatch):
    monkeypatch.setattr("src.location_data._transit_cache", {})

    def raise_error(url, timeout=5):
        raise OSError("network unavailable")

    monkeypatch.setattr("src.location_data.urllib.request.urlopen", raise_error)

    text = fetch_nearby_transit("10115")
    assert text == "Public transport: data unavailable for this PLZ."


def test_fetch_nearby_transit_unknown_plz_has_no_centroid(monkeypatch):
    monkeypatch.setattr("src.location_data._transit_cache", {})
    text = fetch_nearby_transit("00000")
    assert text == "Public transport: data unavailable for this PLZ."


def test_get_neighboring_plz_returns_real_adjacent_codes():
    neighbors = get_neighboring_plz("10115")
    assert isinstance(neighbors, list)
    assert len(neighbors) > 0
    assert "10115" not in neighbors  # a PLZ is never its own neighbor


def test_get_neighboring_plz_unknown_plz_returns_empty():
    assert get_neighboring_plz("00000") == []


def test_load_kita_data_falls_back_to_neighbor_when_plz_has_none(monkeypatch):
    monkeypatch.setattr("src.location_data._load_kitas", lambda: {
        "99999": [],
        "88888": [{"name": "Neighbor Kita", "district": "Test", "licensed_capacity": 50}],
    })
    monkeypatch.setattr("src.location_data._load_neighbors", lambda: {"99999": ["88888"]})
    monkeypatch.setattr(
        "src.location_data.get_plz_spatial_summary",
        lambda plz: PlzSpatialSummary(plz=plz, district="Test", record_count=0),
    )
    load_kita_data.cache_clear()

    text = load_kita_data("99999")
    assert "none registered directly in this PLZ" in text
    assert "88888" in text
    assert "Neighbor Kita" in text


def test_fetch_nearby_transit_caches_successful_result(monkeypatch):
    call_count = {"n": 0}
    fake_response = json.dumps([{"type": "stop", "name": "Cached Stop"}]).encode("utf-8")

    class FakeResponse:
        def __enter__(self):
            call_count["n"] += 1
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return fake_response

    monkeypatch.setattr("src.location_data.urllib.request.urlopen", lambda url, timeout=5: FakeResponse())
    monkeypatch.setattr("src.location_data._transit_cache", {})

    first = fetch_nearby_transit("10115")
    second = fetch_nearby_transit("10115")

    assert first == second
    assert call_count["n"] == 1  # second call served from cache, no new network call


def test_location_summary_omits_schools_until_sourced(monkeypatch):
    monkeypatch.setattr("src.location_data.fetch_nearby_transit", lambda plz: "Public transport: stub.")

    summary = get_location_summary("10115")

    assert "ZIP CODE 10115" in summary
    assert "Kitas:" in summary
    assert "Schools:" not in summary
