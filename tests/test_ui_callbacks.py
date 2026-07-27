from __future__ import annotations

from src import ui_callbacks


def test_save_and_export_pdf_callback_falls_back_when_weasyprint_is_missing(monkeypatch):
    values = [
        "Reichsstraße",
        "100",
        "14050",
        "Berlin",
        "Max Müller",
        "030 12345678",
        84.3,
        3,
        1,
        1,
        "Central heating / Gas heating",
        "B",
        "Fully renovated",
        1000,
        415,
        1415,
        "Apartment",
        "Renovated old-building apartment with parquet flooring.",
        "Balcony, cellar, elevator.",
        "",
        "Warm & inviting",
        "",
        "",
        "",
        "Generated listing copy",
    ]

    monkeypatch.setattr(
        ui_callbacks,
        "render_listing_webpage_pdf",
        lambda *args, **kwargs: (_ for _ in ()).throw(ImportError("missing weasyprint")),
    )
    monkeypatch.setattr(ui_callbacks, "render_listing_pdf", lambda headline, body_text: b"%PDF-1.4\nfallback")

    output_path = ui_callbacks._save_and_export_pdf_callback(*values)

    assert output_path.endswith(".pdf")
    with open(output_path, "rb") as f:
        assert f.read().startswith(b"%PDF-1.4")
