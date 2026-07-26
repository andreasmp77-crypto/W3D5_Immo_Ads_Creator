"""Render a reviewed listing as a downloadable PDF (M6).

No PDF library is a project dependency (see project_structure.md M6, marked
nice-to-have), so this writes minimal-but-valid PDF bytes using only the
stdlib plus Pillow (already a hard dependency of gradio, so guaranteed
available): a two-style Helvetica layout for text, uploaded photos embedded
as JPEG XObjects, and a hand-built xref table.
"""

from __future__ import annotations

import io
import re
import textwrap
from typing import Dict, List, Optional, Sequence, Tuple

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
