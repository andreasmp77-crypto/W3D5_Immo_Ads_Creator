# Project Structure

## Project identity
- **Name:** ImmoAds - AI Apartment Ad Generator
- **Type:** R&D
- **Goal:** ImmoAds does the heavy lifting on your listing — generating compelling, on-brand ad copy and pulling in the neighborhood details (schools, transit, Kitas) that convince tenants to book a viewing

- **Project characteristics (ticked):**
  - [x] Defined goal
  - [x] Limited resources (2-day window, free-tier APIs)
  - [x] Complex (multi-source data integration + LLM pipeline)
  - [x] Defined start/end

## Objectives (Quality / Time / Cost)
- **Quality:** The system must produce apartment ads that are accurate (correct amenity data for the given postal code), brand-consistent in tone, and demonstrably different from generic ChatGPT output — regardless of the specific retrieval/injection mechanism used.
- **Time:** MVP (UI input - document ingestion(2D Floor plan), both knowledge bases, PLZ-based data lookup, ad generation, PDF/UI export) must be complete within the 2-day project window.
- **Cost:** Use free-tier LLM API access and free/open datasets for schools, transport, and Kita data; no paid data subscriptions.


## Requirements → implementation

**Use case:** An apartment owner enters listing details and a postal code; the system enriches the ad with nearby schools, public transport, and Kita information, then produces a publish-ready PDF/UI.

**Must**

| ID | Requirement | Maps to file/module | How verified |
|---|---|---|---|
| M1 | Ingest owner-provided listing details (rooms, size, rent,pictures(optional), #bathrooms, description, tone of the ad) | `document_processor.py` | Unit test: sample input on UI returns correctly parsed JSON |
| M2 | Load primary KB (brand/tone guidelines, past ads) and secondary KB (Berlin district and market-context markdown) from markdown | `knowledge_base.py` | Test loads sample `.md` files without error |
| M3 | Look up schools, public transport, and Kita info by PLZ — Kitas from real Berlin open data, transport via live lookup | `location_data.py` | Returns non-empty Kita + transit result for 5 test PLZs across different Berlin districts |
| M4 | Generate ad copy via LLM using owner info + KB context + location data | `llm_integration.py`, `prompt_templates.py` | Manual review of output against brand tone checklist |
| M5 | Human review/edit before finalizing PDF/UI Posting | `content_pipeline.py` | Manual test: reviewer can edit draft text before final PDF/UI is generated |
| M6 | Render final ad as a PDF/UI posting | `pdf_export.py` (nice-to-have) and/or `publish_UI.py` — UI posting is the required MVP path; PDF export may be dropped if time-constrained | Generated post appears correctly on the UI and contains all required fields; PDF export tested only if built |

**Won't**
- Won't support cities outside Berlin in the MVP
- Won't scrape live rental prices from external listing sites
- Won't build a full vector database / embeddings pipeline (see `rag_decision.md`)

## WBS (2 levels)

1. **Project setup**
   1.1 Initialize repo, venv, `requirements.txt`
   1.2 Write `agents.md`
   1.3 Set up `.env` for API keys
2. **Knowledge base & data**
   2.1 Create primary KB markdown files (brand tone, past ad examples)
   2.2 Create secondary KB markdown files (Berlin market context)
   2.3 Source/prepare PLZ-based schools/transport/Kita dataset
3. **Core pipeline**
   3.1 Build `document_processor.py` (owner input ingestion)
   3.2 Build 2D floor plan ingestion within `document_processor.py`
   3.3 Build `knowledge_base.py` (load/select KB content)
   3.4 Build `location_data.py` (PLZ lookup)
   3.5 Build `prompt_templates.py`
   3.6 Build `llm_integration.py`
   3.7 Build `content_pipeline.py` (orchestration)
4. **Output & review**
   4.1 Build `pdf_export.py`
   4.2 Implement human review/edit step
5. **Uniqueness & docs**
   5.1 Generate side-by-side comparison vs. generic ChatGPT
   5.2 Write README, `rag_decision.md`, finalize this file
6. **PM & demo**
   6.1 Maintain Trello board, capture Day 1/Day 2 screenshots
   6.2 Prepare presentation

## Risks

| Risk | Probability | Impact | Strategy | Concrete action |
|---|---|---|---|---|
| PLZ-based schools/transport/Kita dataset is unavailable or incomplete for some districts | M | M | Reduction | Do not display any such information; note in ad that full neighborhood data wasn't available for that PLZ |
| 2-day time constraint causes scope creep beyond MVP | M | M | Mitigation | Freeze WBS after Day 1 morning; defer extras (live APIs, multi-city support) to the Won't list |
| Generated ad content reads as generic/AI-like, failing the uniqueness requirement | M | H | Mitigation | Build 2+ prompt style variants and require human-in-the-loop review before PDF export |

## Bridge to RAG decision
Our knowledge bases (brand/tone guidelines and Berlin market context) are expected to be small — a handful of markdown files that are largely static over the 2-day build. The PLZ-based schools/transport/Kita data is structured factual lookup, not semantically retrieved prose, so it sits outside the RAG/non-RAG question entirely. Given the corpus size and low update frequency, our current lean is toward non-RAG context injection (load and select relevant markdown directly into the prompt), which keeps the pipeline simple and matches the owner's need for consistent, quickly-generated ads. We would revisit this if the primary KB grew to many past-ad examples or the secondary KB expanded to cover many industry sources, at which point retrieval would help manage context-window limits and cost. This decision and its full defense will be finalized in `rag_decision.md`.

## Product Roadmap/Enhancement:
- Incase the information (Kita,School or Transport) info is missing, pick up neighbouring pincode informaiton
- Check the rental cap information from the Govt websites/API and provide as an input for the owners
- A barometer of how asked rent compares to the area

