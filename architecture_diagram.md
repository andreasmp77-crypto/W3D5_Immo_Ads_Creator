# Pipeline Workflow

┌──────────────────────────────────────┐
│ src/main.py                          │
│ launches src.app.py (Gradio UI)      │
└──────────────────┬───────────────────┘
                   │
                   ▼
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
│ content_pipeline.py                  │  <-- Orchestrates context collection
└───────┬───────────────────┬──────────┘
        │                   │
        │                   │
        ▼                   ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│ knowledge_base.py    │  │ location_data.py                     │
│                      │  │                                      │
│ Loads primary +      │  │ Loads JSON PLZ data + centroids,     │
│ secondary markdown   │  │ uses live BVG lookup, and falls back │
│ context (M2)         │  │ to the nearest neighbor PLZ when     │
└──────────┬───────────┘  │ exact data is missing (M3)           │
           │              └──────────┬───────────────────────────┘
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
│ llm_integration.py                   │  <-- Calls OpenAI Responses API and
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
│ pdf_export.py                        │  <-- Optional PDF rendering branch used
│                                      │      by the Gradio app (M6 / nice-to-have)
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ Final PDF / UI Output                │
└──────────────────────────────────────┘

Notes:
- `document_processor.py` currently supports dict, JSON, TXT, and file-path input.
- `location_data.py` uses JSON-backed PLZ centroids plus live BVG lookup; if a PLZ
  is missing locally, it falls back to the nearest neighboring PLZ and labels that
  fallback explicitly.
- The Gradio app currently calls the draft-generation path and then renders PDF output.
- `M6` is implemented via `pdf_export.py` in the current UI path; the publish/UI
  branch remains the primary MVP target in `project_structure.md`.
