# Pipeline Workflow (current architecture)

┌────────────────────────────────────────────┐
│ Gradio UI (app.py)                         │
│ ui_layout.py   -- page/form layout         │
│ ui_shared.py   -- constants, sample listing│
│ ui_callbacks.py -- generate / export clicks│
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ ui_validation.py                           │  <-- Validates address fields, checks
│                                            │      PLZ against local lookup data,
│                                            │      and (if enabled) verifies the
│                                            │      address live via geopy/Nominatim
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ document_parsing.py                        │  <-- Low-level field aliasing / cleanup
│ document_processor.py                      │  <-- Builds ContentPipelineInputs (M1)
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ content_pipeline.py (facade)               │
│   -> content_service.py (real logic)       │  <-- Orchestrates context collection,
│                                            │      generation, review, publish (M5)
└───────┬───────────────────┬────────────────┘
        │                   │
        ▼                   ▼
┌───────────────────┐   ┌────────────────────────────────────────┐
│ knowledge_base.py │   │ location_data.py (facade)              │
│                   │   │   -> location_static.py                │
│ Loads primary +   │   │      Kitas, schools, PLZ neighbors,    │
│ secondary markdown│   │      centroids -- all precomputed,     │
│ context (M2)      │   │      static JSON files (real open data)│
└─────────┬─────────┘   │   -> location_live.py                  │
          │             │      Live BVG transit lookup (cached   │
          │             │      15 min) + live geopy/Nominatim    │
          │             │      address verification (M3)         │
          │             └──────────────┬─────────────────────────┘
          │                            │
          └──────────────┬─────────────┘
                         ▼
┌────────────────────────────────────────────┐
│ prompt_templates.py                        │  <-- Separates owner info, KB context,
│                                            │      and location facts into prompt
│                                            │      blocks; instructs the model to
│                                            │      surface Kita/transit facts and
│                                            │      never invent unsupported ones (M4)
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ llm_integration.py                         │  <-- Calls OpenAI Responses API and
│                                            │      normalizes draft text (M4)
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ Human Review                               │  <-- Reviewer edits draft inline (M5)
└───────────────────┬────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────┐
│ pdf_export.py                              │  <-- Renders the reviewed listing (with
│                                            │      photos) as a downloadable PDF (M6)
└────────────────────────────────────────────┘

Notes:
- `location_data.py`, `content_pipeline.py` are thin compatibility facades kept stable
  for the UI and tests; the real logic lives in `location_static.py` / `location_live.py`
  and `content_service.py` respectively.
- Static vs. live is a deliberate split, not an accident: Kitas/schools/neighbors/centroids
  are precomputed once (see `rag_decision.md` - non-RAG context injection, static corpus);
  transit and address verification are live lookups because they're either time-sensitive
  (transit) or need real-time external validation (address).
- If a PLZ has no local Kita/school data, the system falls back to a real neighboring PLZ
  (computed once via geopandas polygon adjacency) - never a fabricated result.
- Every location fact returned by `location_static.py` / `location_live.py` is either real
  data or an explicit "unavailable" string; nothing is guessed.
