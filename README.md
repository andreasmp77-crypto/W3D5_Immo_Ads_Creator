# ImmoAds

ImmoAds is a Gradio-based property ad generator for Berlin listings. It normalizes owner input, loads brand and market knowledge from Markdown, enriches the listing with PLZ-based location facts, generates ad copy with OpenAI, and lets the user review the result before export.

## What It Does

- Accepts listing details from the UI, including address, property facts, tone, and photos.
- Normalizes the raw input into `ContentPipelineInputs`.
- Loads primary and secondary knowledge base markdown files.
- Looks up Kitas, schools, neighbor-PLZ fallbacks, centroids, and transit details from local data plus live BVG/geopy verification.
- Separates owner info, knowledge base context, and location facts before sending the prompt to the LLM.
- Generates draft copy with the OpenAI Responses API.
- Supports human review and PDF export from the UI; see `deliverables/` for sample exported listing PDFs.

## Setup

```bash
pip install -r requirements.txt
```

## Run

Start the app:

```bash
python src/main.py
```

`src/main.py` loads `.env` and launches the Gradio UI through the compatibility wrapper in `src/app.py`.

## Tests

Run the test suite:

```bash
pytest -q
```

The current tests cover:

- owner listing normalization
- address validation and warning handling
- knowledge base scanning and formatting
- PLZ location lookup, centroids, and neighbor fallback
- prompt and LLM integration helpers
- content pipeline orchestration
- UI callback behavior, including PDF export fallback

## Repository Layout

- `src/main.py` - entry point for `python src/main.py`
- `src/app.py` - compatibility wrapper for the UI surface
- `src/ui_layout.py` - Gradio layout and page structure
- `src/ui_callbacks.py` - generate/export callbacks
- `src/ui_validation.py` - form validation and normalization
- `src/ui_shared.py` - shared UI constants
- `src/document_processor.py` - raw listing normalization
- `src/document_parsing.py` - parsing helpers for owner intake
- `src/content_pipeline.py` - compatibility facade for the content flow
- `src/content_service.py` - pipeline orchestration service
- `src/knowledge_base.py` - Markdown KB loading and formatting
- `src/location_data.py` - compatibility facade for PLZ lookup
- `src/location_static.py` - static PLZ data, centroids, and summaries
- `src/location_live.py` - live geopy and BVG verification helpers
- `src/prompt_templates.py` - prompt assembly helpers
- `src/llm_integration.py` - OpenAI Responses API wrapper
- `src/pdf_export.py` - PDF rendering for reviewed listings
- `knowledge_base/primary/` - agency tone, listings, and examples
- `knowledge_base/secondary/` - Berlin context summaries written in the project’s own words
- `data/` - local lookup datasets used by the location layer
- `deliverables/` - sample listing PDFs exported from the app (per-tone Berlin listing exports plus the generic-ChatGPT baseline used for comparison) and the final project presentation deck
- `tests/` - pytest coverage for the implemented modules

## Environment

Expected environment variables:

- `OPENAI_API_KEY` - required for ad generation

Notes:

- `geopy` is used for external address verification when installed.
- PDF export uses a WeasyPrint-based path when available, and falls back to the built-in PDF renderer if WeasyPrint is missing.
- Exporting from the running app downloads the PDF through the browser; `deliverables/` holds example exports and the final presentation checked into the repo, not a live export destination.

## Workflow Notes

- The user’s postal code drives the location lookup.
- Owner input, KB context, and location facts stay separated in the prompt.
- If exact PLZ data is missing, the location layer falls back to the nearest neighbor PLZ and labels that fallback explicitly.
- `content_pipeline.py` keeps orchestration separate from lookup and prompt layers.

## Project Context

See `project_structure.md`, `architecture_diagram.md`, and `AGENTS.md` for the current scope, module map, and working rules.
