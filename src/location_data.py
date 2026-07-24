"""Deterministic PLZ-based location lookup for ImmoAds.
Uses local CSV data for daycare and school counts.
Returns a safe transit fallback when station data is unavailable.
"""

import csv
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path("data")
KITAS_FILE = DATA_DIR / "kitas_by_plz.csv"

def _normalize_plz(plz: str) -> str:
    return str(plz).strip()


@lru_cache(maxsize=1)
def _load_rows() -> List[Dict[str, str]]:
    if not KITAS_FILE.exists():
        logger.warning("Kita CSV not found at %s", KITAS_FILE)
        return []

    with open(KITAS_FILE, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _rows_for_plz(plz: str) -> List[Dict[str, str]]:
    plz = _normalize_plz(plz)
    return [row for row in _load_rows() if _normalize_plz(row.get("plz", "")) == plz]


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


def load_kita_data(plz: str) -> str:
    """
    Reads daycare and school counts for the given PLZ from the local CSV file.
    """
    rows = _rows_for_plz(plz)
    if not rows:
        return "Daycare/School infrastructure data unavailable."

    kitas = sum(1 for row in rows if _is_kita_entry(row.get("name", "")))
    schools = sum(1 for row in rows if _is_school_entry(row.get("name", "")))

    if kitas == 0 and schools == 0:
        return "Daycare/School infrastructure data unavailable for this PLZ."

    kita_label = "Kita" if kitas == 1 else "Kitas"
    school_label = "school" if schools == 1 else "schools"
    return f"Daycares & Schools: ~{kitas} {kita_label} and {schools} {school_label} in this PLZ area."


def fetch_nearby_transit(plz: str) -> str:
    """
    Returns a local, deterministic transit summary for the PLZ.

    The repo does not currently ship a station-level dataset, so we avoid
    network lookups here and surface a clear, non-failing fallback instead.
    """
    rows = _rows_for_plz(plz)
    if not rows:
        return "- Public transport data unavailable for this PLZ."

    district = rows[0].get("district", "this district").strip() or "this district"
    station_note = (
        f"- Public transport: station-level data is not loaded yet for {district}; "
        "use the PLZ lookup as a deterministic placeholder until a local transit dataset is added."
    )
    return station_note


def get_location_summary(plz: str) -> str:
    """
    Main execution point called by prompt_templates.py / content_pipeline.py.
    Combines local daycare/school counts and a deterministic transit fallback.
    """
    plz = _normalize_plz(plz)
    summary = [f"=== FACTUAL LOCATION DATA (ZIP CODE {plz}) ==="]
    
    # 1. Daycare & School Data from the local CSV
    summary.append(load_kita_data(plz))
    
    # 2. Transit summary fallback without network/geocoding
    summary.append(fetch_nearby_transit(plz))
        
    return "\n\n".join(summary)
