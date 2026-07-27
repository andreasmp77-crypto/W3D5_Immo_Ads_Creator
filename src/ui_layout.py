"""Gradio landlord intake UI for ImmoAds.

This version mirrors the exported Claude/Organic layout as closely as Gradio
allows: a thin top bar, a narrow centered form, stacked cards, compact inputs,
segmented radios, photo drop slots, and a full-width CTA.
"""

from __future__ import annotations

import tempfile
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from src.document_processor import normalize_owner_listing
    from src.content_pipeline import ContentPipelineInputs, generate_content_draft
    from src.location_data import get_plz_spatial_summary, verify_address_with_geopy
    from src.pdf_export import render_structured_listing_pdf, strip_markdown_for_plain_text
except ImportError:  # pragma: no cover - script execution fallback
    from document_processor import normalize_owner_listing
    from content_pipeline import ContentPipelineInputs, generate_content_draft
    from location_data import get_plz_spatial_summary, verify_address_with_geopy
    from pdf_export import render_structured_listing_pdf, strip_markdown_for_plain_text


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

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Caprasimo:wght@400&family=Figtree:wght@400;600;700&display=swap');

:root {
  --color-bg: #f5ead8;
  --color-surface: #ebddc5;
  --color-text: #201e1d;
  --color-accent: #c67139;
  --color-accent-2: #7a8a5e;
  --color-divider: color-mix(in srgb, #201e1d 16%, transparent);
  --color-neutral-100: #f9f4ed;
  --color-neutral-200: #eee7db;
  --color-neutral-300: #dcd3c4;
  --color-neutral-400: #c0b6a5;
  --color-neutral-500: #a19786;
  --color-neutral-600: #82796a;
  --color-neutral-700: #645c50;
  --color-neutral-800: #474238;
  --color-neutral-900: #2e2b25;
  --color-accent-100: #fff2eb;
  --color-accent-200: #ffe1d0;
  --color-accent-300: #ffc6a5;
  --color-accent-400: #f6a06b;
  --color-accent-500: #d67f48;
  --color-accent-600: #b2622d;
  --color-accent-700: #8c491a;
  --color-accent-800: #643312;
  --color-accent-900: #402310;
  --color-accent-2-100: #f0fae1;
  --color-accent-2-200: #e1eecc;
  --color-accent-2-300: #ccdbb2;
  --color-accent-2-400: #aebf92;
  --color-accent-2-500: #8fa073;
  --color-accent-2-600: #728157;
  --color-accent-2-700: #56633f;
  --color-accent-2-800: #3d472b;
  --color-accent-2-900: #272e1b;
  --font-heading: "Caprasimo", system-ui, sans-serif;
  --font-heading-weight: 400;
  --font-body: "Figtree", system-ui, sans-serif;
  --space-1: 4.4px;
  --space-2: 8.8px;
  --space-3: 13.2px;
  --space-4: 17.6px;
  --space-6: 26.4px;
  --space-8: 35.2px;
  --radius-sm: 8px;
  --radius-md: 16px;
  --radius-lg: 28px;
  --shadow-sm: 0 1px 2px color-mix(in srgb, #2e2b25 14%, transparent);
  --shadow-md: 0 3px 10px color-mix(in srgb, #2e2b25 16%, transparent);
  --shadow-lg: 0 12px 32px color-mix(in srgb, #2e2b25 22%, transparent);
}

/* Gradio's own components (Textbox, Number, Dropdown, Radio, Button, ...)
   render with their own internal markup and read these Gradio-defined CSS
   variables directly, not the .card/.input/.btn classes above (those only
   style the raw HTML we inject via gr.HTML). Overriding them here is what
   actually recolors native component chrome to match the design tokens.
   Also applied under .dark so the palette stays fixed regardless of the
   viewer's OS color-scheme preference. */
:root,
.dark {
  --body-background-fill: var(--color-bg);
  --body-text-color: var(--color-text);
  --body-text-color-subdued: color-mix(in srgb, var(--color-text) 55%, transparent);
  --background-fill-primary: var(--color-bg);
  --background-fill-secondary: var(--color-surface);
  --background-fill-secondary-hover: var(--color-surface);
  --border-color-primary: var(--color-divider);
  --border-color-secondary: var(--color-divider);
  --border-color-accent: var(--color-accent);
  --border-color-accent-subdued: var(--color-accent-300);
  --color-accent-soft: var(--color-accent-100);
  --link-text-color: var(--color-accent);
  --link-text-color-hover: var(--color-accent-600);
  --link-text-color-active: var(--color-accent-700);
  --link-text-color-visited: var(--color-accent);

  --block-background-fill: transparent;
  --block-border-color: transparent;
  --block-border-width: 0px;
  --block-shadow: none;
  --block-label-background-fill: transparent;
  --block-label-border-width: 0px;
  --block-label-text-color: color-mix(in srgb, var(--color-text) 70%, transparent);
  --block-label-text-weight: 700;
  --block-title-text-color: var(--color-text);
  --block-info-text-color: color-mix(in srgb, var(--color-text) 55%, transparent);
  --panel-background-fill: transparent;
  --panel-border-width: 0px;
  --input-background-fill: var(--color-surface);
  --input-background-fill-focus: var(--color-surface);
  --input-border-color: var(--color-divider);
  --input-border-color-focus: var(--color-accent);
  --input-placeholder-color: var(--color-neutral-600);
  --input-shadow: none;
  --input-shadow-focus: none;
  --input-radius: 999px;
  --input-padding: 8px 14px;

  --button-primary-background-fill: var(--color-accent);
  --button-primary-background-fill-hover: var(--color-accent-600);
  --button-primary-border-color: var(--color-accent);
  --button-primary-border-color-hover: var(--color-accent-600);
  --button-primary-text-color: var(--color-bg);
  --button-primary-text-color-hover: var(--color-bg);
  --button-secondary-background-fill: transparent;
  --button-secondary-background-fill-hover: color-mix(in srgb, var(--color-text) 7%, transparent);
  --button-secondary-border-color: var(--color-divider);
  --button-secondary-text-color: var(--color-text);
  --button-secondary-text-color-hover: var(--color-text);
  --button-large-radius: 999px;
  --button-medium-radius: 999px;
  --button-small-radius: 999px;

  --checkbox-background-color: var(--color-surface);
  --checkbox-background-color-selected: var(--color-accent);
  --checkbox-background-color-hover: var(--color-surface);
  --checkbox-border-color: var(--color-divider);
  --checkbox-border-color-selected: var(--color-accent);
  --checkbox-border-color-hover: var(--color-accent);
  --checkbox-label-background-fill: var(--color-bg);
  --checkbox-label-background-fill-hover: color-mix(in srgb, var(--color-text) 7%, transparent);
  --checkbox-label-background-fill-selected: var(--color-accent);
  --checkbox-label-border-color: var(--color-divider);
  --checkbox-label-border-color-selected: var(--color-accent);
  --checkbox-label-text-color: var(--color-text);
  --checkbox-label-text-color-selected: var(--color-text);
  --checkbox-label-text-weight: 500;
}

/* Gradio's Radio component marks the checked pill with class="selected"
   (see label.selected in its compiled CSS) but only exposes one shared
   --checkbox-label-text-weight for both states. Bold just the selected
   pill directly so the active choice reads as selected without relying
   on a color change. */
.seg label.selected {
  font-weight: 700 !important;
}

body {
  margin: 0;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-body);
  text-wrap: pretty;
}

h1, h2, h3, h4 {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  letter-spacing: -0.015em;
}

.gradio-container {
  max-width: 100% !important;
  color: var(--color-text);
  background: var(--color-bg) !important;
}

.gradio-container .main,
.gradio-container .wrap,
.gradio-container .block,
.gradio-container .panel,
.gradio-container .gr-form,
.gradio-container .gr-box {
  background: var(--color-bg) !important;
}

.immo-shell {
  margin: 0 auto;
  /* Extra bottom padding leaves room for the fixed .cta-bar so it never
     covers the last card. */
  padding: var(--space-6) var(--space-4) 120px;
}

.form-shell {
  max-width: 880px;
  margin: 0 auto;
}

.nav {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-bottom: none !important;
}

.nav-brand {
  font-family: var(--font-heading);
  font-size: 18px;
  margin-right: auto;
  color: var(--color-text);
  letter-spacing: 0.01em;
}

/* Brand banner (icon + wordmark + tagline) shown at the top of every view.
   Recreated in the page's cream/accent palette rather than embedding the
   supplied dark-navy raster, which would clash with the theme. */
.brand-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-right: auto;
}

.brand-logo {
  display: inline-flex;
  width: 46px;
  height: 46px;
  flex: none;
}

.brand-logo svg {
  width: 100%;
  height: 100%;
  display: block;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.12;
}

.brand-name {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 26px;
  color: var(--color-text);
  letter-spacing: 0.01em;
}

.brand-tagline {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--color-accent);
  letter-spacing: 0.02em;
}

@media (max-width: 768px) {
  .brand-name {
    font-size: 21px;
  }
  .brand-tagline {
    font-size: 11.5px;
  }
  .brand-logo {
    width: 38px;
    height: 38px;
  }
}

.topbar-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--color-accent-100);
  color: var(--color-accent-700);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
}

.hero-title {
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 34px;
  line-height: 1.08;
  margin: 0 0 8px;
  letter-spacing: -0.01em;
  color: var(--color-text);
}

.hero-copy {
  font-size: 15.5px;
  color: var(--color-neutral-700);
  margin: 0;
}

.card {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.elev-sm {
  box-shadow: var(--shadow-sm);
}

.form-card {
  margin-bottom: var(--space-4);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  border: 1px solid var(--color-divider);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 17px;
  line-height: 1.2;
  color: var(--color-text);
}

.card-kicker {
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-accent);
}

.section-rule {
  height: 1px;
  background: var(--color-divider);
  margin-top: var(--space-4);
  margin-bottom: var(--space-4);
}

.field > label {
  display: block;
  font-size: 14px;
  margin-bottom: 5px;
  color: var(--color-text);
}

.input {
  width: 100%;
  min-height: 36px;
  padding: 6px 10px;
  font: inherit;
  font-size: 14px;
  color: var(--color-text);
  caret-color: var(--color-accent);
  background: var(--color-surface);
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-md);
}

.input:hover {
  border-color: color-mix(in srgb, var(--color-text) 45%, transparent);
}

.input:focus-visible {
  border-color: var(--color-accent);
  outline-offset: 0;
}

textarea.input {
  min-height: 90px;
  resize: vertical;
}

.input::placeholder,
textarea::placeholder {
  color: var(--color-neutral-600);
  opacity: 1;
}

.radio {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
}

.radio input,
.seg-opt input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.seg {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.seg-opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  font-size: 13px;
  cursor: pointer;
}

.seg-opt + .seg-opt {
  border-left: 1px solid var(--color-divider);
}

.seg-opt:has(input:checked) {
  background: var(--color-accent);
  color: var(--color-bg);
}

.seg-opt:not(:has(input:checked)):hover {
  background: color-mix(in srgb, var(--color-text) 7%, transparent);
}

.seg-opt:has(input:focus-visible) {
  outline: 2px solid var(--color-accent);
  outline-offset: -2px;
}

.radio-list {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
}

.radio-list label {
  border: 1px solid var(--color-divider);
  border-radius: 999px;
  padding: 7px 12px;
}

.radio-list label:hover {
  background: color-mix(in srgb, var(--color-text) 7%, transparent);
}

.radio-list label:has(input:checked) {
  background: var(--color-accent);
  color: var(--color-bg);
  border-color: var(--color-accent);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  text-decoration: none;
  font-family: var(--font-heading);
  font-weight: var(--font-heading-weight);
  font-size: 14px;
  line-height: 1.2;
  color: var(--color-text);
  background: transparent;
  border: 1px solid transparent;
  padding: var(--space-2) calc(var(--space-3) * 1.2);
  border-radius: var(--radius-md);
}

.btn-primary {
  background: var(--color-accent);
  color: var(--color-bg);
}

.btn-primary:hover {
  background: var(--color-accent-600);
}

.btn-primary:active {
  background: var(--color-accent-700);
}

.btn-secondary {
  border-color: var(--color-divider);
}

.btn-secondary:hover {
  background: color-mix(in srgb, var(--color-text) 7%, transparent);
}

.btn-ghost {
  color: var(--color-accent);
  padding-inline: var(--space-1);
}

.btn-icon {
  width: 36px;
  height: 36px;
  padding: 0;
}

.btn-block {
  width: 100%;
  margin-top: var(--space-2);
}

.submit-btn {
  min-height: 52px;
  font-size: 16px;
}

/* Gradio locally redefines --color-accent to its own default orange
   (#f97316) on primary buttons, which would shadow the brand accent. Reset
   it here so var(--color-accent) below resolves to the design token
   (#c67139 from :root) and the CTA matches the rest of the accent UI.
   Covers both the Generate button (<button>) and the DownloadButton, which
   Gradio may render as a nested <button> or <a>. */
button.submit-btn,
.submit-btn button,
.submit-btn a {
  --color-accent: #c67139;
  min-height: 52px !important;
  width: 100% !important;
  font-size: 16px !important;
  font-family: var(--font-heading) !important;
  font-weight: var(--font-heading-weight) !important;
  background: var(--color-accent) !important;
  color: var(--color-bg) !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  box-shadow: none !important;
}

/* Keep the primary CTA pinned to the bottom of the viewport so it stays
   reachable no matter how far down the long form the user has scrolled.
   position: fixed (not sticky) because Gradio's nested column wrappers set
   overflow that would trap a sticky element. Centered to line up with the
   880px form column; the translucent blurred backdrop stops form content
   showing through as it scrolls behind the bar. */
.cta-bar {
  position: fixed;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  width: min(880px, calc(100vw - 24px));
  z-index: 50;
  padding: var(--space-3) 0 var(--space-4);
  background: color-mix(in srgb, var(--color-bg) 90%, transparent);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.field-grid-2 {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-4);
}

.field-grid-2-equal {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.field-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-4);
}

.field-grid-3-top {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-4);
}

/* Gradio wraps adjacent form fields in an internal .form grouping div;
   left as-is, that single wrapper becomes the only grid item and only
   fills the first grid-template-columns track. Unwrap it so the actual
   fields lay out directly on our grid. */
.field-grid-2 > .form,
.field-grid-2-equal > .form,
.field-grid-3 > .form,
.field-grid-3-top > .form {
  display: contents;
}

.photo-grid {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.photo-grid > * {
  width: 33.3333%;
  aspect-ratio: 4 / 3;
}

.photo-grid .gradio-container {
  height: 100%;
}

.photo-grid img {
  object-fit: cover;
}

.note-copy {
  font-size: 13.5px;
  color: var(--color-neutral-700);
  margin: 8px 0 var(--space-3);
}

.icon-accent {
  color: var(--color-accent-700);
}

.hidden-output {
  display: none !important;
}

/* Hide the native browser spin buttons on Number inputs (Living area, rent
   fields, ...) so they don't add extra visual bulk beyond the design. */
input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="number"] {
  -moz-appearance: textfield;
}

/* "Rounded frame" variant from the source design system: cards get a large
   soft radius, small controls (buttons/tags/segments/inputs) go full pill. */
.card,
.form-card,
.dialog {
  border-radius: calc(var(--radius-lg) * 1.15);
}

.btn,
.tag,
.seg,
.input {
  border-radius: 999px;
}

.input {
  padding-inline: 14px;
}

/* The pill radius (--input-radius: 999px) looks right on single-line inputs
   but rounds multi-line text areas so hard that the corners eat the text
   (notably the generated ad copy). Give text areas a gentle radius instead.
   Literal px (not var(--radius-md)) because Gradio shadows that token locally. */
textarea,
textarea.input {
  border-radius: 14px !important;
}

@media (max-width: 768px) {
  .immo-shell {
    padding-inline: 12px;
  }

  .field-grid-2,
  .field-grid-2-equal,
  .field-grid-3,
  .field-grid-3-top {
    grid-template-columns: 1fr;
  }

  .photo-grid {
    flex-direction: column;
  }

  .photo-grid > * {
    width: 100%;
  }
}
"""

# Header banner: SVG building icon + wordmark + tagline, styled in the app's
# cream/accent palette so it fits the theme (the supplied image was dark navy).
BANNER_HTML = """
<div class="brand-banner">
  <span class="brand-logo">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="9" y="5" width="30" height="39" rx="5" fill="var(--color-accent)"/>
      <g fill="var(--color-bg)">
        <rect x="14" y="11" width="5" height="5" rx="1"/>
        <rect x="21.5" y="11" width="5" height="5" rx="1"/>
        <rect x="29" y="11" width="5" height="5" rx="1"/>
        <rect x="14" y="19" width="5" height="5" rx="1"/>
        <rect x="21.5" y="19" width="5" height="5" rx="1"/>
        <rect x="29" y="19" width="5" height="5" rx="1"/>
        <rect x="14" y="27" width="5" height="5" rx="1"/>
        <rect x="29" y="27" width="5" height="5" rx="1"/>
        <rect x="21" y="34" width="6" height="10" rx="1"/>
      </g>
    </svg>
  </span>
  <span class="brand-text">
    <span class="brand-name">ImmoAds</span>
    <span class="brand-tagline">A smarter way to write apartment ads.</span>
  </span>
</div>
"""


INTRO_HTML = """
<div style="margin-bottom:var(--space-6)">
  <div class="topbar-pill">New Listing</div>
  <h1 class="hero-title">List your property</h1>
  <p class="hero-copy">Fill in the details below. ImmoAds turns this into a polished listing with on-brand copy and neighborhood highlights - ready to publish or export as a PDF.</p>
</div>
"""

# Shown in place of INTRO_HTML once the draft has been generated, turning the
# page into a "review" step.
REVIEW_INTRO_HTML = """
<div style="margin-bottom:var(--space-6)">
  <div class="topbar-pill">Review</div>
  <h1 class="hero-title">Review your listing</h1>
  <p class="hero-copy">Your draft version of the AI-generated listing is ready for review. Edit it in the text boxes and click the "Save and export to PDF" button to generate the PDF.</p>
</div>
"""


def _section_header(number: str, title: str, icon: str) -> str:
    return f"""
    <div class="card-title">
      <span style="min-width:34px;color:var(--color-neutral-800);font-size:2rem;line-height:1;font-weight:800">{number}</span>
      <span class="icon-accent">{icon}</span>
      <span style="text-transform:uppercase;letter-spacing:0.08em;font-size:0.95rem">{title}</span>
    </div>
    <div class="section-rule"></div>
    """


def create_app():
    """Build the Gradio UI."""

    try:
        import gradio as gr
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise ImportError(
            "Gradio is required to launch the UI. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    try:
        from src.ui_callbacks import _generate_listing_callback, _save_and_export_pdf_callback
    except ImportError:  # pragma: no cover - script execution fallback
        from ui_callbacks import _generate_listing_callback, _save_and_export_pdf_callback

    with gr.Blocks(css=CUSTOM_CSS, title="ImmoAds") as demo:
        with gr.Row(elem_classes=["nav"]):
            gr.HTML(BANNER_HTML)

        with gr.Column(elem_classes=["immo-shell"]):
            with gr.Column(elem_classes=["form-shell"]):
                intro = gr.HTML(INTRO_HTML)
                with gr.Column(elem_classes=["card", "elev-sm", "form-card"]):
                    gr.HTML(_section_header("01", "Address", "📍"))
                    with gr.Row(elem_classes=["field-grid-2"]):
                        street_name = gr.Textbox(label="Street name", value=DEFAULT_SAMPLE_LISTING["street_name"])
                        house_number = gr.Textbox(label="House number", value=DEFAULT_SAMPLE_LISTING["house_number"])
                    with gr.Row(elem_classes=["field-grid-2"]):
                        postal_code = gr.Textbox(label="Pincode", value=DEFAULT_SAMPLE_LISTING["postal_code"])
                        city = gr.Textbox(label="City", value=DEFAULT_SAMPLE_LISTING["city"])

                with gr.Column(elem_classes=["card", "elev-sm", "form-card"]):
                    gr.HTML(_section_header("02", "Contact", "☎"))
                    with gr.Row(elem_classes=["field-grid-2"]):
                        full_name = gr.Textbox(label="Full name", value=DEFAULT_SAMPLE_LISTING["full_name"])
                        phone_number = gr.Textbox(label="Phone number", value=DEFAULT_SAMPLE_LISTING["phone_number"])

                with gr.Column(elem_classes=["card", "elev-sm", "form-card"]):
                    gr.HTML(_section_header("03", "Property details", "⌂"))
                    with gr.Row(elem_classes=["field-grid-3"]):
                        living_area_sqm = gr.Number(label="Living area (m²)", value=DEFAULT_SAMPLE_LISTING["living_area_sqm"], precision=1)
                        rooms = gr.Number(label="Number of rooms", value=DEFAULT_SAMPLE_LISTING["rooms"], precision=1)
                        bedrooms = gr.Number(label="Number of bedrooms", value=DEFAULT_SAMPLE_LISTING["bedrooms"], precision=1)
                    with gr.Row(elem_classes=["field-grid-3"]):
                        bathrooms = gr.Number(label="Number of bathrooms", value=DEFAULT_SAMPLE_LISTING["bathrooms"], precision=1)
                        heating_type = gr.Dropdown(label="Heating type", choices=HEATING_OPTIONS, value=DEFAULT_SAMPLE_LISTING["heating_type"])
                        energy_efficiency = gr.Dropdown(label="Energy efficiency", choices=ENERGY_OPTIONS, value=DEFAULT_SAMPLE_LISTING["energy_efficiency"])
                    gr.HTML('<div class="field"><label id="condition-label">Property condition</label></div>')
                    property_condition = gr.Radio(
                        choices=PROPERTY_CONDITIONS,
                        value=DEFAULT_SAMPLE_LISTING["property_condition"],
                        show_label=False,
                        elem_classes=["seg"],
                    )

                with gr.Column(elem_classes=["card", "elev-sm", "form-card"]):
                    gr.HTML(_section_header("04", "Costs", "€"))
                    with gr.Row(elem_classes=["field-grid-3"]):
                        cold_rent_eur = gr.Number(label="Cold rent (EUR)", value=DEFAULT_SAMPLE_LISTING["cold_rent_eur"], precision=1)
                        nebenkosten_eur = gr.Number(label="Warm costs (EUR)", value=DEFAULT_SAMPLE_LISTING["nebenkosten_eur"], precision=1)
                        total_warm_rent_eur = gr.Number(label="Total rent (EUR)", value=DEFAULT_SAMPLE_LISTING["total_warm_rent_eur"], precision=1)

                with gr.Column(elem_classes=["card", "elev-sm", "form-card"]):
                    gr.HTML(_section_header("05", "Description", "✎"))
                    property_type = gr.Dropdown(label="Property type", choices=PROPERTY_TYPES, value=DEFAULT_SAMPLE_LISTING["property_type"])
                    property_description = gr.Textbox(
                        label="Property description",
                        value=DEFAULT_SAMPLE_LISTING["property_description"],
                        placeholder="Describe the building, location, and surroundings...",
                    )
                    fixtures_and_fittings = gr.TextArea(
                        label="Fixtures & fittings",
                        value=DEFAULT_SAMPLE_LISTING["fixtures_and_fittings"],
                        lines=4,
                        placeholder="Parquet floors, fitted kitchen, balcony, cellar, elevator...",
                    )
                    location_note = gr.TextArea(
                        label="Location notes",
                        value=DEFAULT_SAMPLE_LISTING["location_note"],
                        lines=2,
                        placeholder="Optional extra location notes...",
                    )
                    generated_ad_copy = gr.TextArea(
                        label="Generated ad copy",
                        value="",
                        lines=12,
                        visible=False,
                    )

                with gr.Column(elem_classes=["card", "elev-sm", "form-card"]):
                    gr.HTML(_section_header("06", "Photos", "⬆"))
                    gr.Markdown("Upload up to 3 photos. High-resolution images increase viewing requests.")
                    with gr.Row(elem_classes=["photo-grid"]):
                        photo_1 = gr.Image(label="Photo 1", type="filepath", sources=["upload"], interactive=True)
                        photo_2 = gr.Image(label="Photo 2", type="filepath", sources=["upload"], interactive=True)
                        photo_3 = gr.Image(label="Photo 3", type="filepath", sources=["upload"], interactive=True)

                with gr.Column(elem_classes=["card", "elev-sm", "form-card"]) as tone_section:
                    gr.HTML(_section_header("07", "Tone of voice", "✦"))
                    gr.Markdown("Choose the voice for the generated ad copy.")
                    tone = gr.Radio(
                        choices=TONES,
                        value=DEFAULT_SAMPLE_LISTING["tone"],
                        show_label=False,
                        elem_classes=["seg"],
                    )

                with gr.Column(elem_classes=["cta-bar"]):
                    submit = gr.Button(
                        "Generate my listing ad",
                        elem_classes=["btn", "btn-primary", "btn-block", "submit-btn"],
                        variant="primary",
                    )
                    save_export_btn = gr.Button(
                        "💾 Save and export to PDF",
                        elem_classes=["btn", "btn-primary", "btn-block", "submit-btn"],
                        variant="primary",
                        visible=False,
                    )
                    # The actual file download is delivered through this hidden
                    # DownloadButton: save_export_btn builds the PDF into its value,
                    # then a follow-up JS click triggers the browser download. Doing
                    # it this way exports in a single click (a DownloadButton that
                    # generates its own value needs two). Hidden via CSS, not
                    # visible=False, so it still renders a clickable element.
                    pdf_download = gr.DownloadButton(
                        "download",
                        elem_id="pdf-download",
                        elem_classes=["hidden-output"],
                    )
                    generation_status = gr.Markdown(value="", visible=False)

            form_fields = [
                street_name,
                house_number,
                postal_code,
                city,
                full_name,
                phone_number,
                living_area_sqm,
                rooms,
                bedrooms,
                bathrooms,
                heating_type,
                energy_efficiency,
                property_condition,
                cold_rent_eur,
                nebenkosten_eur,
                total_warm_rent_eur,
                property_type,
                property_description,
                fixtures_and_fittings,
                location_note,
                tone,
                photo_1,
                photo_2,
                photo_3,
            ]

            submit.click(
                fn=_generate_listing_callback,
                inputs=form_fields,
                outputs=[
                    intro,
                    generated_ad_copy,
                    property_description,
                    fixtures_and_fittings,
                    location_note,
                    tone_section,
                    submit,
                    save_export_btn,
                    generation_status,
                ],
            )

            save_export_btn.click(
                fn=_save_and_export_pdf_callback,
                # non-photo fields + generated copy, then the 3 photo components last
                # (matches _save_and_export_pdf_callback's form_values[:-3] / [-3:] split)
                inputs=form_fields[:-3] + [generated_ad_copy] + form_fields[-3:],
                # Build the PDF into the hidden DownloadButton, then click it from
                # the browser so the file downloads in this same single click.
                outputs=[pdf_download],
            ).then(
                None,
                None,
                None,
                js="() => { document.querySelector('#pdf-download').click(); }",
            )

    return demo


def launch(**launch_kwargs: Any):
    """Launch the Gradio UI."""

    launch_kwargs.setdefault("share", True)
    demo = create_app()
    demo.queue()
    return demo.launch(**launch_kwargs)


if __name__ == "__main__":
    launch()
