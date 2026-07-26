"""Entry point for launching the ImmoAds Gradio UI."""

from __future__ import annotations

from dotenv import load_dotenv

try:
    from src.app import launch
except ImportError:  # pragma: no cover - script execution fallback
    from app import launch


def main() -> None:
    load_dotenv()
    launch()


if __name__ == "__main__":
    main()
