"""Deterministic PLZ-based location lookup for ImmoAds.

Loads the local amenity workbook, derives PLZ centroids from spatial points,
and memoizes the heavy reads so repeated prompt generation stays fast.
"""

from __future__ import annotations

import csv
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

try:
    import geopandas as gpd
except ImportError:  # pragma: no cover - optional dependency
    gpd = None

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
AMENITY_WORKBOOK = Path("knowledge_base/secondary/kitaliste-nov-2025.xlsx")
KITAS_FILE = DATA_DIR / "kitas_by_plz.csv"
PROJECT_CRS = "EPSG:25833"
WGS84_CRS = "EPSG:4326"


@dataclass(frozen=True)
class PlzSpatialSummary:
    """Cached spatial summary for one postal code."""

    plz: str
    district: str
    record_count: int
    centroid_xy: Optional[Tuple[float, float]] = None
    centroid_latlon: Optional[Tuple[float, float]] = None


def _normalize_plz(plz: str) -> str:
    return str(plz).strip()


def _standardize_amenity_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize workbook and CSV inputs to one shared schema."""
    column_map = {
        "Einrichtungsbezirk": "district_code",
        "Einrichtungsbezirk Name": "district",
        "Einrichtungsnummer": "entry_id",
        "Einrichtungsname": "name",
        "Straße": "street",
        "Hausnummer": "house_number",
        "PLZ": "plz",
        "Telefon": "phone",
        "Einrichtungstyp": "facility_type",
        "Trägernummer": "provider_id",
        "Trägername": "provider",
        "ETRS_YKOORDINATE": "etrs_y",
        "ETRS_XKOORDINATE": "etrs_x",
        "Erlaubte Plätze (BE)": "licensed_capacity",
    }

    frame = frame.rename(columns={key: value for key, value in column_map.items() if key in frame.columns}).copy()

    if "plz" in frame.columns:
        frame["plz"] = frame["plz"].astype(str).str.strip()
    if "district" in frame.columns:
        frame["district"] = frame["district"].astype(str).str.strip()
    if "name" in frame.columns:
        frame["name"] = frame["name"].astype(str).str.strip()
    if "etrs_x" in frame.columns:
        frame["etrs_x"] = pd.to_numeric(frame["etrs_x"], errors="coerce")
    if "etrs_y" in frame.columns:
        frame["etrs_y"] = pd.to_numeric(frame["etrs_y"], errors="coerce")

    return frame


@lru_cache(maxsize=1)
def _load_amenity_frame() -> pd.DataFrame:
    """Load the local amenity table once and keep it cached."""
    if AMENITY_WORKBOOK.exists():
        try:
            frame = pd.read_excel(AMENITY_WORKBOOK, sheet_name=0, header=1)
            return _standardize_amenity_frame(frame)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Could not read amenity workbook %s: %s", AMENITY_WORKBOOK, exc)

    if KITAS_FILE.exists():
        try:
            with open(KITAS_FILE, mode="r", encoding="utf-8") as handle:
                frame = pd.DataFrame(csv.DictReader(handle))
            return _standardize_amenity_frame(frame)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("Could not read amenity CSV %s: %s", KITAS_FILE, exc)

    logger.warning("No amenity source file found for PLZ lookup.")
    return pd.DataFrame()


@lru_cache(maxsize=1)
def _load_amenity_geodataframe():
    """Build a GeoDataFrame when GeoPandas is available and coordinates exist."""
    frame = _load_amenity_frame()
    if frame.empty or gpd is None:
        return None

    required_columns = {"etrs_x", "etrs_y"}
    if not required_columns.issubset(frame.columns):
        return None

    usable = frame.dropna(subset=["etrs_x", "etrs_y"]).copy()
    if usable.empty:
        return None

    geometry = gpd.points_from_xy(usable["etrs_x"], usable["etrs_y"])
    return gpd.GeoDataFrame(usable, geometry=geometry, crs=PROJECT_CRS)


@lru_cache(maxsize=256)
def _rows_for_plz(plz: str) -> List[Dict[str, str]]:
    frame = _load_amenity_frame()
    if frame.empty or "plz" not in frame.columns:
        return []

    normalized_plz = _normalize_plz(plz)
    subset = frame[frame["plz"] == normalized_plz]
    return subset.fillna("").to_dict(orient="records")


def _is_kita_entry(name: str) -> bool:
    lowered = name.lower()
    return any(token in lowered for token in ("kita", "kindergarten", "kinderladen", "kindertages", "daycare"))


def _is_school_entry(name: str) -> bool:
    lowered = name.lower()
    return bool(
        re.search(
            r"\b(school|schule|grundschule|gymnasium|oberschule|college|universit[aä]t)\b",
            lowered,
        )
    )


@lru_cache(maxsize=256)
def get_plz_spatial_summary(plz: str) -> PlzSpatialSummary:
    """Return cached spatial metadata for a single PLZ."""
    normalized_plz = _normalize_plz(plz)
    rows = _rows_for_plz(normalized_plz)
    if not rows:
        return PlzSpatialSummary(plz=normalized_plz, district="unknown", record_count=0)

    district_counts: Dict[str, int] = {}
    for row in rows:
        district = str(row.get("district", "")).strip() or "unknown"
        district_counts[district] = district_counts.get(district, 0) + 1
    district = max(district_counts, key=district_counts.get)

    centroid_xy: Optional[Tuple[float, float]] = None
    centroid_latlon: Optional[Tuple[float, float]] = None

    amenity_gdf = _load_amenity_geodataframe()
    if amenity_gdf is not None and "plz" in amenity_gdf.columns:
        subset = amenity_gdf[amenity_gdf["plz"] == normalized_plz]
        if not subset.empty:
            try:
                centroid_geometry = subset.geometry.unary_union.centroid
                centroid_xy = (float(centroid_geometry.x), float(centroid_geometry.y))

                if gpd is not None:
                    centroid_point = gpd.GeoSeries([centroid_geometry], crs=PROJECT_CRS).to_crs(WGS84_CRS).iloc[0]
                    centroid_latlon = (float(centroid_point.y), float(centroid_point.x))
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.warning("Could not compute centroid for PLZ %s: %s", normalized_plz, exc)
    else:
        x_values = [row.get("etrs_x") for row in rows if row.get("etrs_x") not in (None, "")]
        y_values = [row.get("etrs_y") for row in rows if row.get("etrs_y") not in (None, "")]
        try:
            centroid_xy = (
                float(sum(float(value) for value in x_values) / len(x_values)),
                float(sum(float(value) for value in y_values) / len(y_values)),
            )
        except Exception:
            centroid_xy = None

    return PlzSpatialSummary(
        plz=normalized_plz,
        district=district,
        record_count=len(rows),
        centroid_xy=centroid_xy,
        centroid_latlon=centroid_latlon,
    )


@lru_cache(maxsize=256)
def load_kita_data(plz: str) -> str:
    """Read daycare and school counts for the given PLZ from the local dataset."""
    rows = _rows_for_plz(plz)
    if not rows:
        return "Daycare/School infrastructure data unavailable."

    kitas = sum(1 for row in rows if _is_kita_entry(str(row.get("name", ""))))
    schools = sum(1 for row in rows if _is_school_entry(str(row.get("name", ""))))

    if kitas == 0 and schools == 0:
        return "Daycare/School infrastructure data unavailable for this PLZ."

    kita_label = "Kita" if kitas == 1 else "Kitas"
    school_label = "school" if schools == 1 else "schools"
    return f"Daycares & Schools: ~{kitas} {kita_label} and {schools} {school_label} in this PLZ area."


@lru_cache(maxsize=256)
def fetch_nearby_transit(plz: str) -> str:
    """Return a deterministic transit placeholder anchored on the PLZ centroid."""
    summary = get_plz_spatial_summary(plz)
    if summary.record_count == 0:
        return "- Public transport data unavailable for this PLZ."

    if summary.centroid_latlon:
        lat, lon = summary.centroid_latlon
        return (
            f"- Public transport: centroid-based lookup anchored at {summary.district} "
            f"(approx. {lat:.4f}, {lon:.4f}) from {summary.record_count} local amenity points; "
            "station-level dataset not bundled yet."
        )

    if summary.centroid_xy:
        x_coord, y_coord = summary.centroid_xy
        return (
            f"- Public transport: centroid-based lookup anchored at {summary.district} "
            f"(projected centroid {x_coord:.1f}, {y_coord:.1f}) from {summary.record_count} local amenity points; "
            "station-level dataset not bundled yet."
        )

    return (
        f"- Public transport: centroid-based lookup anchored at {summary.district} "
        f"from {summary.record_count} local amenity points; station-level dataset not bundled yet."
    )


@lru_cache(maxsize=256)
def get_location_summary(plz: str) -> str:
    """Build the final fact block injected into prompts."""
    normalized_plz = _normalize_plz(plz)
    summary = [f"=== FACTUAL LOCATION DATA (ZIP CODE {normalized_plz}) ==="]

    summary.append(load_kita_data(normalized_plz))
    summary.append(fetch_nearby_transit(normalized_plz))

    return "\n\n".join(summary)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_plz = "10115"
    print("\n--- TESTING LOCATION DATA RETRIEVAL ---")
    result = get_location_summary(test_plz)
    print(result)
