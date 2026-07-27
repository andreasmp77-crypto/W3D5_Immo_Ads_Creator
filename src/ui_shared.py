"""Shared UI constants for ImmoAds."""

from __future__ import annotations

DEFAULT_SAMPLE_LISTING = {
    "street_name": "Reichsstraße",
    "house_number": "100",
    "postal_code": "14050",
    "city": "Berlin",
    "full_name": "Max Müller",
    "phone_number": "030 12345678",
    "living_area_sqm": 84.3,
    "rooms": 3,
    "bedrooms": 1,
    "bathrooms": 1,
    "heating_type": "Central heating / Gas heating",
    "energy_efficiency": "B",
    "property_condition": "Fully renovated",
    "cold_rent_eur": 1000,
    "nebenkosten_eur": 415,
    "total_warm_rent_eur": 1415,
    "property_type": "Apartment",
    "property_description": (
        "Renovated old-building apartment with parquet flooring, a fitted kitchen, "
        "and a quiet side-street location close to transit."
    ),
    "fixtures_and_fittings": "Balcony, cellar, elevator, fitted kitchen, parquet flooring.",
    "location_note": "",
    "tone": "Warm & inviting",
    "photos": [],
}

FORM_FIELD_NAMES = [
    "street_name",
    "house_number",
    "postal_code",
    "city",
    "full_name",
    "phone_number",
    "living_area_sqm",
    "rooms",
    "bedrooms",
    "bathrooms",
    "heating_type",
    "energy_efficiency",
    "property_condition",
    "cold_rent_eur",
    "nebenkosten_eur",
    "total_warm_rent_eur",
    "property_type",
    "property_description",
    "fixtures_and_fittings",
    "location_note",
    "tone",
    "photo_1",
    "photo_2",
    "photo_3",
]

TONES = ["Warm & inviting", "Professional", "Premium"]
PROPERTY_CONDITIONS = ["New", "Fully renovated", "Needs renovation"]
HEATING_OPTIONS = [
    "Central heating / Gas heating",
    "District heating",
    "Underfloor heating",
    "Night storage heating",
]
ENERGY_OPTIONS = ["A", "B", "C", "D", "E", "F", "G"]
PROPERTY_TYPES = [
    "Select type...",
    "Apartment",
    "Old building apartment",
    "New build",
    "Maisonette",
    "Penthouse",
]

INTRO_HTML = """
<div style="margin-bottom:var(--space-6)">
  <div class="topbar-pill">New Listing</div>
  <h1 class="hero-title">List your property</h1>
  <p class="hero-copy">Fill in the details below. ImmoAds turns this into a polished listing with on-brand copy and neighborhood highlights - ready to publish or export as a PDF.</p>
</div>
"""

REVIEW_INTRO_HTML = """
<div style="margin-bottom:var(--space-6)">
  <div class="topbar-pill">Review</div>
  <h1 class="hero-title">Review your listing</h1>
  <p class="hero-copy">Your draft version of the AI-generated listing is ready for review. Edit it in the text boxes and click the "Save and export to PDF" button to generate the PDF.</p>
</div>
"""

