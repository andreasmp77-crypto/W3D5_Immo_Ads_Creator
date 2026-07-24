# Pipeline Workflow

┌──────────────────────────────────────┐
│ Raw Owner Input                      │
│ dict / JSON / TXT / file path        │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ document_processor.py                │  <-- Cleans aliases, infers PLZ, builds
│                                      │      ContentPipelineInputs (M1)
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ content_pipeline.py                  │  <-- Orchestrates context collection,
│                                      │      generation, review, and final payload (M5)
└───────┬───────────────────┬──────────┘
        │                   │
        │                   │
        ▼                   ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│ knowledge_base.py    │  │ location_data.py                      │
│                      │  │                                      │
│ Loads primary +      │  │ Loads local amenity workbook / CSV,   │
│ secondary markdown   │  │ derives cached PLZ spatial summaries, │
│ context (M2)         │  │ optional GeoPandas centroid path,     │
└──────────┬───────────┘  │ then returns deterministic facts (M3) │
           │              └──────────┬─────────────────────────────┘
           │                         │
           └──────────────┬──────────┘
                          ▼
┌──────────────────────────────────────┐
│ prompt_templates.py                  │  <-- Separates owner info, KB context,
│                                      │      and location facts into prompt blocks (M4)
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ llm_integration.py                  │  <-- Calls OpenAI Responses API and
│                                      │      normalizes draft text (M4)
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ Human Review / Edit                  │  <-- Reviewer can accept or edit draft (M5)
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ Reviewed / Publish-Ready Payload      │
│ build_publish_payload()               │
└──────────────────────────────────────┘

Notes:
- `document_processor.py` currently supports dict, JSON, TXT, and file-path input.
- `location_data.py` uses GeoPandas when available, but keeps a deterministic pandas
  fallback so PLZ facts still load without a spatial dependency.
- `M6` is not implemented yet in code; the current pipeline stops at a publish-ready
  payload rather than PDF/UI rendering.
