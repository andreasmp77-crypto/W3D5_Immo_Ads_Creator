# AGENTS.md — Niche Real Estate Pitch Engine

## Project Purpose
This repo builds ImmoAds, a listing-ad generator for Berlin apartments. It ingests owner-provided listing details, loads brand and market knowledge from markdown, looks up local amenities by PLZ, and generates publish-ready ad copy with a human review step. See `project_structure.md` for the full PM kickoff and Must-ID list; every change in this repo should trace back to one of the Must IDs there (`M1`-`M6`). Do not add features that are not tied to a Must ID or explicitly listed in the MVP / Won't sections of that file.

## Stack & How to Run
- Python 3.8+
- LLM API: use the free-tier provider selected for the build (never commit `.env`)
- Install: `pip install -r requirements.txt`
- Run: `python src/main.py`
- Env vars expected: the LLM `OPENAI_API_KEY` API key used by the implementation, plus any lookup key required by `location_data.py` if it uses an external service

## Repo Map
- `knowledge_base/primary/` — brand/tone guidelines, property listings, and past ads
- `knowledge_base/secondary/` — Berlin market context and other supporting summaries, written in our own words
- `src/document_processor.py` — owner input ingestion
- `src/knowledge_base.py` — KB loading and selection
- `src/prompt_templates.py` — ad-generation prompt templates
- `src/llm_integration.py` — LLM API wrapper
- `src/content_pipeline.py` — orchestration from input to draft/review/final output
- `src/main.py` — entry point for `python src/main.py`
- `templates/` — reusable prompt template files referenced by `prompt_templates.py`

## Conventions
- All knowledge base content is markdown, one topic per file, with a short frontmatter
  header (title, last updated).
- New source files go in `src/`; new content docs go under the matching `knowledge_base/`
  subfolder. Never mix code and content directories.
- PLZ / amenity lookup facts must be injected as explicit prompt variables and kept separate
  from KB context.
- Function and file names stay in `snake_case`; keep one responsibility per module.

## Definition of Done (agent-assisted changes)
- Code/docs are committed to the repo (not left uncommitted).
- The relevant Must's verify step from `project_structure.md` passes.
- The Trello card being worked is updated with what changed.
- No secrets, API keys, or `.env` contents are committed.
- No hallucinated facts in generated output — if a KB doc doesn't cover something, the
  prompt/template should omit it rather than let the model invent it.

## Never Do
- Never commit `.env` or any file containing API keys.
- Never invent APIs or services that aren't in the Stack section above — ask first.
- Never expand scope into anything in the Won't list from `project_structure.md` without an
  explicit decision logged there.
- Never add a vector database or embeddings pipeline by default unless `rag_decision.md`
  is explicitly updated to say otherwise.
- Never paste external source text verbatim into `knowledge_base/secondary/` — summarize
  in our own words.

## How the Team Uses Agents (Codex)
- Work one Trello card at a time. Before prompting Codex, paste the card description and
  its Must ID into the prompt along with a pointer to this file ("follow AGENTS.md").
- After Codex makes changes, check the diff against the Never Do list above before
  committing.
- If Codex proposes something outside the current Must ID or Won't list, treat it as a
  future card, not something to merge now.
