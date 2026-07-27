"""Static PLZ-based lookup helpers for ImmoAds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class PlzSpatialSummary:
    """Cached spatial summary for one postal code."""

    plz: str
    district: str
    record_count: int
    centroid_latlon: Optional[Tuple[float, float]] = None


def _normalize_plz(plz: str) -> str:
    return str(plz).strip()


def load_lookup_file(file_path: Path, *, missing_message: Optional[str] = None) -> Dict[str, Any]:
    """Load a JSON lookup file and fail closed with an empty mapping."""

    if not file_path.exists():
        if missing_message:
            import logging

            logging.getLogger(__name__).warning(missing_message, file_path)
        return {}
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def load_kitas_file(file_path: Path) -> Dict[str, List[Dict[str, object]]]:
    return load_lookup_file(file_path, missing_message="Kita data file not found at %s")


def load_centroids_file(file_path: Path) -> Dict[str, Dict[str, float]]:
    return load_lookup_file(file_path, missing_message="PLZ centroid file not found at %s")


def load_neighbors_file(file_path: Path) -> Dict[str, List[str]]:
    return load_lookup_file(file_path, missing_message="PLZ neighbor file not found at %s")


def load_schools_file(file_path: Path) -> Dict[str, List[Dict[str, object]]]:
    return load_lookup_file(
        file_path,
        missing_message="Schools data file not found at %s -- run scripts/fetch_schools.py first",
    )


def build_plz_spatial_summary(
    plz: str,
    *,
    kitas_lookup: Mapping[str, List[Dict[str, object]]],
    centroids_lookup: Mapping[str, Dict[str, float]],
) -> PlzSpatialSummary:
    normalized_plz = _normalize_plz(plz)
    kitas = kitas_lookup.get(normalized_plz, [])
    centroid = centroids_lookup.get(normalized_plz)

    district = kitas[0]["district"] if kitas else "unknown"
    centroid_latlon = (centroid["lat"], centroid["lng"]) if centroid else None

    return PlzSpatialSummary(
        plz=normalized_plz,
        district=district,
        record_count=len(kitas),
        centroid_latlon=centroid_latlon,
    )


def get_neighboring_plz(plz: str, neighbors_lookup: Mapping[str, List[str]]) -> List[str]:
    return neighbors_lookup.get(_normalize_plz(plz), [])


def get_kitas(
    plz: str,
    kitas_lookup: Mapping[str, List[Dict[str, object]]],
    *,
    top_n: int = 3,
) -> List[Dict[str, object]]:
    return kitas_lookup.get(_normalize_plz(plz), [])[:top_n]


def get_schools(
    plz: str,
    schools_lookup: Mapping[str, List[Dict[str, object]]],
    *,
    top_n: int = 3,
) -> List[Dict[str, object]]:
    return schools_lookup.get(_normalize_plz(plz), [])[:top_n]


def format_school_data(
    plz: str,
    *,
    schools_lookup: Mapping[str, List[Dict[str, object]]],
    neighbors_lookup: Mapping[str, List[str]],
) -> str:
    normalized_plz = _normalize_plz(plz)
    if not schools_lookup:
        return "Schools: data not yet available (run scripts/fetch_schools.py)."

    schools = get_schools(normalized_plz, schools_lookup)
    if schools:
        names = ", ".join(s["name"] for s in schools)
        total = len(schools_lookup.get(normalized_plz, []))
        return f"Schools: {total} registered in this PLZ, including {names}."

    for neighbor_plz in get_neighboring_plz(normalized_plz, neighbors_lookup):
        neighbor_schools = get_schools(neighbor_plz, schools_lookup)
        if neighbor_schools:
            names = ", ".join(s["name"] for s in neighbor_schools)
            return (
                f"Schools: none registered directly in this PLZ; nearby PLZ "
                f"{neighbor_plz} has options including {names}."
            )

    return "Schools: no data available for this PLZ or its immediate neighbors."


def format_kita_data(
    plz: str,
    *,
    kitas_lookup: Mapping[str, List[Dict[str, object]]],
    neighbors_lookup: Mapping[str, List[str]],
    spatial_summary: PlzSpatialSummary,
) -> str:
    normalized_plz = _normalize_plz(plz)
    kitas = get_kitas(normalized_plz, kitas_lookup)
    if kitas:
        names = ", ".join(k["name"] for k in kitas)
        return f"Kitas: {spatial_summary.record_count} registered in this PLZ, including {names}."

    for neighbor_plz in get_neighboring_plz(normalized_plz, neighbors_lookup):
        neighbor_kitas = get_kitas(neighbor_plz, kitas_lookup)
        if neighbor_kitas:
            names = ", ".join(k["name"] for k in neighbor_kitas)
            return (
                f"Kitas: none registered directly in this PLZ; nearby PLZ {neighbor_plz} "
                f"has options including {names}."
            )

    return "Kitas: no data available for this PLZ or its immediate neighbors."

