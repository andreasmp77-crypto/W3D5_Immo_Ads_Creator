"""
One-time build script: fetch the official Berlin schools directory and produce
data/schools_by_plz.json, in the same shape/convention as data/kitas_by_plz.json.

"""

import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "https://www.bildungsstatistik.berlin.de/statistik/ListGen/Schuldaten.aspx"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "schools_by_plz.json"

# BSN (school ID) format: 2 digits + letter + 2-3 digits, e.g. "01G01", "10K13"
BSN_PATTERN = re.compile(r"\d{2}[A-Z]\d{2,3}")
# Berlin PLZ range used in this dataset
PLZ_PATTERN = re.compile(r"(1[0-4]\d{3})")


def fetch_table_text() -> str:
    resp = requests.get(URL, timeout=30, verify=False)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # The school table is the main data table on the page; adjust selector if the
    # page structure changes.
    table = soup.find("table")
    return table.get_text(separator="") if table else soup.get_text(separator="")


def parse_schools(raw_text: str):
    """Split the concatenated table text into (bsn, name, plz, address) records."""
    matches = list(BSN_PATTERN.finditer(raw_text))
    schools = []
    for i, match in enumerate(matches):
        bsn = match.group()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        chunk = raw_text[start:end]

        plz_match = PLZ_PATTERN.search(chunk)
        if not plz_match:
            continue  # skip malformed rows rather than guessing a PLZ

        name = chunk[: plz_match.start()].strip()
        rest = chunk[plz_match.end() :]
        # Address is the text up to the first phone number (starts with "+49")
        phone_idx = rest.find("+49")
        address = rest[:phone_idx].strip() if phone_idx != -1 else rest.strip()

        schools.append(
            {
                "bsn": bsn,
                "name": name,
                "plz": plz_match.group(),
                "address": address,
            }
        )
    return schools


def group_by_plz(schools):
    grouped = {}
    for school in schools:
        plz = school.pop("plz")
        grouped.setdefault(plz, []).append(school)
    return grouped


def main():
    raw_text = fetch_table_text()
    schools = parse_schools(raw_text)
    grouped = group_by_plz(schools)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(grouped, f, ensure_ascii=False, indent=2)

    print(f"Parsed {len(schools)} schools across {len(grouped)} PLZ codes.")
    print(f"Wrote {OUTPUT_PATH}")
    print(
        "Sanity check: Berlin has ~927 schools per the page header. "
        "If this count is far off, inspect the table selector in fetch_table_text()."
    )


if __name__ == "__main__":
    main()
