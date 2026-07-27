"""Render a reviewed listing as a downloadable PDF (M6).

No PDF library is a project dependency (see project_structure.md M6, marked
nice-to-have), so this writes minimal-but-valid PDF bytes using only the
stdlib plus Pillow (already a hard dependency of gradio, so guaranteed
available): a two-style Helvetica layout for text, uploaded photos embedded
as JPEG XObjects, and a hand-built xref table.
"""

from __future__ import annotations

import base64
import html
import io
import re
import textwrap
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow ships with gradio
    Image = None  # type: ignore[assignment]


def _pdf_encode_text(text: str) -> bytes:
    """Escape PDF-reserved chars and encode for the WinAnsiEncoding font."""
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return escaped.encode("cp1252", errors="replace")


def _wrap_text_to_lines(text: str, width: int = 92) -> List[str]:
    lines: List[str] = []
    for paragraph in text.replace("\r\n", "\n").split("\n"):
        wrapped = textwrap.wrap(paragraph, width=width) if paragraph.strip() else [""]
        lines.extend(wrapped)
    return lines


def _paginate(items: List[object], per_page: int) -> List[List[object]]:
    if not items:
        return [[]]
    return [items[i : i + per_page] for i in range(0, len(items), per_page)]


def strip_markdown_for_plain_text(block: str) -> str:
    """Strip Markdown syntax (headers, bold, italic) for the plain-text PDF body.

    The LLM (via prompt_templates.py) returns Markdown-formatted ad copy, but
    this PDF writer only supports plain text, so callers should run each
    content block through this before handing it to the render functions.
    """
    text = re.sub(r"^#{1,4}\s*", "", block, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", text)
    return text


def _prepare_jpeg_for_pdf(
    path: str, max_dimension: int = 1000, quality: int = 82
) -> Optional[Tuple[bytes, int, int]]:
    """Load an uploaded image and re-encode it as JPEG bytes for PDF embedding.

    Returns None (skip that photo) rather than raising, so one unreadable
    upload doesn't break the whole export.
    """
    if not path or Image is None:
        return None
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((max_dimension, max_dimension))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue(), img.width, img.height
    except Exception:  # pragma: no cover - depends on arbitrary uploaded file contents
        return None


class _PdfBuilder:
    """Incremental PDF object writer: reserve an object number, fill it in later.

    This avoids hand-computed object-number arithmetic (a past source of a
    broken xref table) when the object count varies with page/photo count.
    """

    def __init__(self) -> None:
        self._objects: List[bytes] = []

    def reserve(self) -> int:
        self._objects.append(b"")
        return len(self._objects)

    def add(self, body: bytes) -> int:
        self._objects.append(body)
        return len(self._objects)

    def set(self, obj_num: int, body: bytes) -> None:
        self._objects[obj_num - 1] = body

    def build(self, root_num: int) -> bytes:
        buf = io.BytesIO()
        buf.write(b"%PDF-1.4\n")
        offsets: List[int] = []
        for i, body in enumerate(self._objects, start=1):
            offsets.append(buf.tell())
            buf.write(f"{i} 0 obj\n".encode("latin-1"))
            buf.write(body)
            buf.write(b"\nendobj\n")

        xref_offset = buf.tell()
        total_objs = len(self._objects) + 1
        buf.write(f"xref\n0 {total_objs}\n".encode("latin-1"))
        buf.write(b"0000000000 65535 f \n")
        for offset in offsets:
            buf.write(f"{offset:010d} 00000 n \n".encode("latin-1"))

        buf.write(
            f"trailer\n<< /Size {total_objs} /Root {root_num} 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode(
                "latin-1"
            )
        )
        return buf.getvalue()


_PAGE_WIDTH = 612.0
_PAGE_HEIGHT = 792.0
_MARGIN = 50.0


def _text_page_content(styled_lines: Sequence[Tuple[str, str]]) -> bytes:
    stream_lines: List[bytes] = [b"BT", b"14 TL", f"{_MARGIN:.0f} 740 Td".encode("latin-1")]
    current_style: Optional[str] = None
    for j, (text, style) in enumerate(styled_lines):
        if style != current_style:
            if style == "title":
                stream_lines.append(b"/F2 18 Tf")
            elif style == "header":
                stream_lines.append(b"/F2 12 Tf")
            else:
                stream_lines.append(b"/F1 11 Tf")
            current_style = style
        text_bytes = _pdf_encode_text(text)
        prefix = b"(" if j == 0 else b"T* ("
        stream_lines.append(prefix + text_bytes + b") Tj")
    stream_lines.append(b"ET")
    return b"\n".join(stream_lines)


def render_structured_listing_pdf(
    headline: str,
    sections: Sequence[Tuple[str, Sequence[str]]],
    image_paths: Sequence[str] = (),
) -> bytes:
    """Render a titled, sectioned listing (matching the on-screen card layout)
    as a multi-page PDF, followed by one full page per uploaded photo.
    """
    builder = _PdfBuilder()
    catalog_num = builder.reserve()
    pages_num = builder.reserve()
    font_regular_num = builder.add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold_num = builder.add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    resources = f"<< /Font << /F1 {font_regular_num} 0 R /F2 {font_bold_num} 0 R >> >>".encode("latin-1")

    styled_lines: List[Tuple[str, str]] = [
        (line, "title") for line in _wrap_text_to_lines(headline or "Apartment Listing", width=68)
    ]
    styled_lines.append(("", "body"))
    for title, content_lines in sections:
        clean_lines = [str(line) for line in content_lines if line not in (None, "")]
        if not clean_lines:
            continue
        if title:
            styled_lines.append((title.upper(), "header"))
        for raw_line in clean_lines:
            styled_lines.extend((wrapped, "body") for wrapped in _wrap_text_to_lines(raw_line, width=92))
        styled_lines.append(("", "body"))

    page_nums: List[int] = []
    for page_lines in _paginate(styled_lines, per_page=44):
        content_num = builder.reserve()
        page_num = builder.add(
            (
                f"<< /Type /Page /Parent {pages_num} 0 R /Resources "
            ).encode("latin-1")
            + resources
            + f" /MediaBox [0 0 {_PAGE_WIDTH:.0f} {_PAGE_HEIGHT:.0f}] /Contents {content_num} 0 R >>".encode("latin-1")
        )
        stream = _text_page_content(page_lines)
        builder.set(content_num, f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        page_nums.append(page_num)

    for image_index, path in enumerate(image_paths):
        embedded = _prepare_jpeg_for_pdf(path)
        if embedded is None:
            continue
        jpeg_bytes, px_w, px_h = embedded
        image_num = builder.add(
            (
                f"<< /Type /XObject /Subtype /Image /Width {px_w} /Height {px_h} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg_bytes)} >>\nstream\n"
            ).encode("latin-1")
            + jpeg_bytes
            + b"\nendstream"
        )

        max_w = _PAGE_WIDTH - 2 * _MARGIN
        max_h = _PAGE_HEIGHT - 2 * _MARGIN
        scale = min(max_w / px_w, max_h / px_h, 1.0)
        draw_w = px_w * scale
        draw_h = px_h * scale
        tx = (_PAGE_WIDTH - draw_w) / 2
        ty = (_PAGE_HEIGHT - draw_h) / 2

        content_num = builder.reserve()
        page_num = builder.add(
            (
                f"<< /Type /Page /Parent {pages_num} 0 R "
                f"/Resources << /XObject << /Im{image_index} {image_num} 0 R >> >> "
                f"/MediaBox [0 0 {_PAGE_WIDTH:.0f} {_PAGE_HEIGHT:.0f}] /Contents {content_num} 0 R >>"
            ).encode("latin-1")
        )
        stream = f"q {draw_w:.2f} 0 0 {draw_h:.2f} {tx:.2f} {ty:.2f} cm /Im{image_index} Do Q".encode("latin-1")
        builder.set(content_num, f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        page_nums.append(page_num)

    if not page_nums:
        content_num = builder.reserve()
        page_num = builder.add(
            (
                f"<< /Type /Page /Parent {pages_num} 0 R /Resources "
            ).encode("latin-1")
            + resources
            + f" /MediaBox [0 0 {_PAGE_WIDTH:.0f} {_PAGE_HEIGHT:.0f}] /Contents {content_num} 0 R >>".encode("latin-1")
        )
        builder.set(content_num, b"<< /Length 0 >>\nstream\n\nendstream")
        page_nums.append(page_num)

    kids = " ".join(f"{n} 0 R" for n in page_nums)
    builder.set(catalog_num, f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode("latin-1"))
    builder.set(pages_num, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_nums)} >>".encode("latin-1"))

    return builder.build(catalog_num)


def render_listing_pdf(headline: str, body_text: str) -> bytes:
    """Backward-compatible plain single-section PDF (no headers, no photos)."""
    return render_structured_listing_pdf(headline, [("", _wrap_text_to_lines(body_text or "", width=92))])


# ---------------------------------------------------------------------------
# WYSIWYG export: render the reviewed listing as an HTML document styled like
# the web page, then print it to PDF with WeasyPrint (a browser-style
# "Print to PDF"). Photos are grouped together on one dedicated final page.
# ---------------------------------------------------------------------------

# Design tokens mirrored from the web UI (see ui_layout.CUSTOM_CSS) so the PDF
# looks like the review page.
_BG = "#f5ead8"
_SURFACE = "#ebddc5"
_TEXT = "#201e1d"
_ACCENT = "#c67139"
_ACCENT_700 = "#8c491a"
_ACCENT_100 = "#fff2eb"
_DIVIDER = "rgba(32, 30, 29, 0.16)"
_MUTED = "rgba(32, 30, 29, 0.70)"

# SVG building mark from BANNER_HTML, with literal colours (WeasyPrint does not
# resolve CSS custom properties inside <svg>).
_LOGO_SVG = f"""
<svg viewBox="0 0 48 48" width="42" height="42" xmlns="http://www.w3.org/2000/svg">
  <rect x="9" y="5" width="30" height="39" rx="5" fill="{_ACCENT}"/>
  <g fill="{_BG}">
    <rect x="14" y="11" width="5" height="5" rx="1"/><rect x="21.5" y="11" width="5" height="5" rx="1"/>
    <rect x="29" y="11" width="5" height="5" rx="1"/><rect x="14" y="19" width="5" height="5" rx="1"/>
    <rect x="21.5" y="19" width="5" height="5" rx="1"/><rect x="29" y="19" width="5" height="5" rx="1"/>
    <rect x="14" y="27" width="5" height="5" rx="1"/><rect x="29" y="27" width="5" height="5" rx="1"/>
    <rect x="21" y="34" width="6" height="10" rx="1"/>
  </g>
</svg>
"""


def _photo_data_uri(path: str) -> Optional[str]:
    """Re-encode an uploaded photo as a base64 JPEG data URI so the HTML is
    fully self-contained (no external file references for WeasyPrint to load)."""
    embedded = _prepare_jpeg_for_pdf(path, max_dimension=1400, quality=85)
    if embedded is None:
        return None
    jpeg_bytes, _w, _h = embedded
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")


def _fmt(value: Any) -> str:
    """Format a field value for display, trimming trailing .0 on whole numbers."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return html.escape(str(value))


def _field_html(label: str, value: Any) -> str:
    if value in (None, "") or str(value).strip() == "":
        return ""
    return (
        f'<div class="field"><div class="f-label">{html.escape(label)}</div>'
        f'<div class="f-value">{_fmt(value)}</div></div>'
    )


def _card_html(number: str, title: str, fields_html: str, *, columns: int = 2) -> str:
    if not fields_html.strip():
        return ""
    return (
        f'<section class="card">'
        f'<div class="card-head"><span class="c-num">{number}</span>'
        f'<span class="c-title">{html.escape(title)}</span></div>'
        f'<div class="fields cols-{columns}">{fields_html}</div>'
        f"</section>"
    )


def build_listing_html(
    values: Dict[str, Any],
    ad_copy: str,
    photo_data_uris: Sequence[str] = (),
) -> str:
    """Build a self-contained HTML document that mirrors the review page."""

    street = values.get("street_name") or ""
    house_number = values.get("house_number") or ""
    city = values.get("city") or ""
    headline = " ".join(p for p in [street, house_number, city] if p) or "Apartment Listing"

    address_fields = (
        _field_html("Street name", street)
        + _field_html("House number", house_number)
        + _field_html("Pincode", values.get("postal_code"))
        + _field_html("City", city)
    )
    contact_fields = _field_html("Full name", values.get("full_name")) + _field_html(
        "Phone number", values.get("phone_number")
    )
    detail_fields = (
        _field_html("Living area (m²)", values.get("living_area_sqm"))
        + _field_html("Rooms", values.get("rooms"))
        + _field_html("Bedrooms", values.get("bedrooms"))
        + _field_html("Bathrooms", values.get("bathrooms"))
        + _field_html("Heating type", values.get("heating_type"))
        + _field_html("Energy efficiency", values.get("energy_efficiency"))
        + _field_html("Property condition", values.get("property_condition"))
        + _field_html("Property type", values.get("property_type"))
    )
    cost_fields = (
        _field_html("Cold rent (EUR)", values.get("cold_rent_eur"))
        + _field_html("Warm costs (EUR)", values.get("nebenkosten_eur"))
        + _field_html("Total rent (EUR)", values.get("total_warm_rent_eur"))
    )

    # Description card: the generated ad copy plus any extra notes.
    desc_parts = []
    if str(ad_copy or "").strip():
        desc_parts.append(f'<div class="ad-copy">{html.escape(ad_copy.strip())}</div>')
    desc_parts.append(_field_html("Fixtures & fittings", values.get("fixtures_and_fittings")))
    desc_parts.append(_field_html("Location notes", values.get("location_note")))
    desc_body = "".join(p for p in desc_parts if p)
    description_card = (
        f'<section class="card"><div class="card-head"><span class="c-num">05</span>'
        f'<span class="c-title">Description</span></div>'
        f'<div class="fields cols-1">{desc_body}</div></section>'
        if desc_body
        else ""
    )

    cards = "".join(
        [
            _card_html("01", "Address", address_fields, columns=2),
            _card_html("02", "Contact", contact_fields, columns=2),
            _card_html("03", "Property details", detail_fields, columns=3),
            _card_html("04", "Costs", cost_fields, columns=3),
            description_card,
        ]
    )

    photos_section = ""
    imgs = [uri for uri in photo_data_uris if uri]
    if imgs:
        photo_imgs = "".join(f'<img src="{uri}" alt="Property photo"/>' for uri in imgs)
        photos_section = (
            f'<section class="card photos-page"><div class="card-head">'
            f'<span class="c-num">06</span><span class="c-title">Photos</span></div>'
            f'<div class="photo-grid">{photo_imgs}</div></section>'
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Caprasimo&family=Figtree:wght@400;600;700&display=swap');
  @page {{ size: A4; margin: 1.4cm; }}
  html {{ background: {_BG}; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: "Figtree", "Helvetica Neue", Arial, sans-serif;
    color: {_TEXT};
    font-size: 12px;
    line-height: 1.45;
  }}
  .banner {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
  .banner .name {{ font-family: "Caprasimo", Georgia, serif; font-size: 26px; line-height: 1; }}
  .banner .tag {{ color: {_ACCENT}; font-size: 12px; margin-top: 2px; }}
  h1.doc-title {{
    font-family: "Caprasimo", Georgia, serif; font-weight: 400; font-size: 26px;
    margin: 0 0 4px;
  }}
  .kicker {{
    display: inline-block; background: {_ACCENT_100}; color: {_ACCENT_700};
    font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 999px; margin-bottom: 8px;
  }}
  .sub {{ color: {_MUTED}; margin: 0 0 18px; }}
  .card {{
    background: {_SURFACE}; border: 1px solid {_DIVIDER}; border-radius: 18px;
    padding: 16px 18px; margin-bottom: 14px;
  }}
  .card-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
  .c-num {{ font-family: "Caprasimo", Georgia, serif; font-size: 22px; color: {_TEXT}; }}
  .c-title {{
    text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; font-size: 12px;
  }}
  .card-head {{ border-bottom: 1px solid {_DIVIDER}; padding-bottom: 8px; }}
  .fields {{ display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 12px; }}
  .fields.cols-1 .field {{ width: 100%; }}
  .fields.cols-2 .field {{ width: calc(50% - 7px); }}
  .fields.cols-3 .field {{ width: calc(33.333% - 10px); }}
  .f-label {{ font-size: 10px; color: {_MUTED}; margin-bottom: 4px; }}
  .f-value {{
    background: {_BG}; border: 1px solid {_DIVIDER}; border-radius: 999px;
    padding: 7px 14px; font-size: 12px; min-height: 30px;
  }}
  .ad-copy {{
    white-space: pre-wrap; background: {_BG}; border: 1px solid {_DIVIDER};
    border-radius: 14px; padding: 14px 16px; font-size: 12px; line-height: 1.5;
  }}
  .photos-page {{ break-before: page; }}
  .photo-grid {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }}
  .photo-grid img {{
    width: calc(50% - 6px); height: 230px; object-fit: cover;
    border-radius: 14px; border: 1px solid {_DIVIDER};
  }}
</style>
</head>
<body>
  <div class="banner">
    {_LOGO_SVG}
    <div><div class="name">ImmoAds</div><div class="tag">A smarter way to write apartment ads.</div></div>
  </div>
  <div class="kicker">Listing</div>
  <h1 class="doc-title">{html.escape(headline)}</h1>
  <p class="sub">Generated with ImmoAds &mdash; ready to publish or share.</p>
  {cards}
  {photos_section}
</body>
</html>"""


def render_listing_webpage_pdf(
    values: Dict[str, Any],
    ad_copy: str,
    photo_paths: Sequence[str] = (),
) -> bytes:
    """Render the reviewed listing to a PDF that looks like the web page.

    Uses WeasyPrint to "print" a styled HTML document; all photos are placed
    together on one dedicated final page. Raises ImportError with install
    guidance if WeasyPrint (and its native libraries) are unavailable.
    """
    try:
        from weasyprint import HTML  # lazy: heavy import with native deps
    except Exception as exc:  # pragma: no cover - depends on local install
        raise ImportError(
            "WeasyPrint is required for the web-page-style PDF export. Install it with "
            "`pip install weasyprint` plus its native libraries (on macOS: "
            "`conda install -c conda-forge pango gdk-pixbuf`, or `brew install pango`)."
        ) from exc

    photo_data_uris = [uri for uri in (_photo_data_uri(p) for p in photo_paths) if uri]
    document_html = build_listing_html(values, ad_copy, photo_data_uris)
    return HTML(string=document_html).write_pdf()
