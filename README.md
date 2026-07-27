# ImmoAds

ImmoAds is a Gradio-based property ad generator for Berlin listings. It normalizes owner input, loads brand and market knowledge from Markdown, enriches the listing with PLZ-based truth location facts, generates ad copy with OpenAI, and can render a reviewed PDF export.

## What It Does

- Accepts landlord input from the UI, including listing details, tone, photos, and postal code.
- Normalizes that input into `ContentPipelineInputs`.
- Loads primary and secondary knowledge base markdown files.
- Looks up Kitas, schools, neighbor PLZ fallbacks, centroids, and transit details from local JSON data plus live BVG lookup.
- Builds an LLM prompt with separated owner info, KB context, and location facts.
- Generates draft copy with OpenAI Responses API.
- Lets the user review and edit the draft before export.
- Exports a PDF version of the listing through the UI.

## Setup

```bash
pip install -r requirements.txt
```

If you want to run the tests and `pytest` is not already available in your environment, install it separately in your dev setup.

## Run

Start the app:

```bash
python src/main.py
```

`src/main.py` loads `.env` and launches the Gradio UI in `src/app.py`.

## Tests

Run the test suite:

```bash
pytest -q
```

The current suite covers:

- owner listing normalization
- KB scanning and formatting
- PLZ location lookup and neighbor fallback
- prompt / LLM integration helpers
- content pipeline orchestration

## Repository Layout

- `src/app.py` - Gradio UI and PDF export wiring
- `src/main.py` - entry point that launches the UI
- `src/document_processor.py` - raw listing normalization
- `src/content_pipeline.py` - orchestration from context collection to reviewed output
- `src/knowledge_base.py` - markdown KB loading and formatting
- `src/location_data.py` - PLZ lookup, neighbor fallback, centroids, transit, and school/Kita summaries
- `src/prompt_templates.py` - prompt assembly helpers
- `src/llm_integration.py` - OpenAI Responses API wrapper
- `src/pdf_export.py` - PDF rendering for reviewed listings
- `knowledge_base/primary/` - agency tone, listings, and examples
- `knowledge_base/secondary/` - Berlin context summaries written in the project’s own words
- `data/` - local lookup datasets used by `location_data.py`
- `tests/` - pytest coverage for the implemented modules

## Workflow Notes

- The user’s postal code is the input that selects location facts.
- The ad generation prompt keeps owner info, KB context, and PLZ facts separate.
- Location facts are not taken from the UI text verbatim; they are looked up from the data layer.
- If exact PLZ data is missing, `location_data.py` falls back to the nearest neighboring PLZ and labels that fallback explicitly.
- `content_pipeline.py` keeps orchestration separate from the lookup and prompt layers.

## Project Context

The current implementation focuses on:

- owner intake and normalization
- KB loading from Markdown
- deterministic PLZ enrichment
- LLM copy generation
- human review
- PDF export

See `project_structure.md`, `architecture_diagram.md`, and `AGENTS.md` for the current scope and working constraints.
