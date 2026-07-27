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


def test_generate_listing_callback_uses_reviewed_text(monkeypatch):
    fake_gradio = type("FakeGradio", (), {"update": staticmethod(lambda **kwargs: kwargs)})
    monkeypatch.setitem(__import__("sys").modules, "gradio", fake_gradio)
    monkeypatch.setattr(
        "src.app.verify_address_with_geopy",
        lambda *args, **kwargs: type("Result", (), {"status": "verified", "message": "ok"})(),
    )
    monkeypatch.setattr(
        "src.app.generate_content_draft",
        lambda _inputs: type(
            "PipelineResult",
            (),
            {
                "draft_text": "Generic draft body",
                "reviewed_text": (
                    "Generic draft body\n\n"
                    "Location facts:\n"
                    "- Kitas: 1 registered in this PLZ, including Example Kita.\n"
                    "- Public transport: nearby stops include Example Stop (250m)."
                ),
            },
        )(),
    )

    form_values = [
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
    ]

    result = ui_callbacks._generate_listing_callback(*form_values)

    assert "Location facts:" in result[1]["value"]
    assert "Example Kita" in result[1]["value"]
