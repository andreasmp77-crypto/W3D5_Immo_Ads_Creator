# AGENTS.md — Niche Real Estate Pitch Engine

## Project Purpose
This repo builds a content engine for a fictional luxury real estate agency. It generates
personalized property descriptions and neighborhood guides by combining an internal
knowledge base (listing details, brand voice, past sold-over-asking examples) with an
external knowledge base (mortgage rate trends, local return-to-office patterns, rent
regulation). See `project_structure.md` for the full PM kickoff and Must-ID list — every
change in this repo should trace back to a Must ID from that file. Do not add features that
aren't tied to a Must ID or explicitly listed as an MVP scope item below.

## MVP Scope (do not exceed without asking)
- NO real authentication/login system. Owner vs. tenant is a simple role flag passed into
  the CLI/UI, not a user account system.
- NO floor-plan/diagram image parsing. Property details (rooms, dimensions, features) are
  entered as structured text/form fields, not extracted from images.
- Address → nearby amenities (Kita, train station) is a SINGLE deterministic API/geocode
  lookup per listing, injected directly into the prompt as a fact. This is NOT a RAG
  retrieval step — do not add embeddings or similarity search for this.
- Comparable past listings (from the primary KB) MAY use lightweight retrieval (metadata
  filtering by price range/neighborhood is sufficient — no vector DB required) once the
  primary KB has more than ~5 listings.

## Stack & How to Run
- Python 3.8+
- LLM: OpenAI or Anthropic API (see `.env.example` for required keys — never commit `.env`)
- Install: `pip install -r requirements.txt`
- Run: `python src/main.py`
- Env vars expected: `OPENAI_API_KEY`, `GEOCODE_API_KEY` (if using a
  real amenities lookup service)

## Repo Map
- `knowledge_base/primary/` — agency branding, property listings, past sold-over-asking
  examples (markdown)
- `knowledge_base/secondary/` — mortgage rates, RTO trends, rent regulation summaries
  (markdown, written in our own words — never paste copyrighted text verbatim)
- `src/document_processor.py` — markdown ingestion for both KBs
- `src/knowledge_base.py` — KB loading + comparable-listing filtering
- `src/prompt_templates.py` — pitch/neighborhood-guide prompt templates
- `src/llm_integration.py` — LLM API wrapper
- `src/content_pipeline.py` — document → monitor → brief → publish → iterate
- `templates/` — reusable prompt template files referenced by `prompt_templates.py`

## Conventions
- All knowledge base content is markdown, one topic per file, with a short frontmatter
  header (title, last updated).
- New source files go in `src/`; new content docs go under the matching `knowledge_base/`
  subfolder — never mix code and content directories.
- Deterministic facts (amenities, geocode results) are injected as explicit prompt
  variables, clearly separated from retrieved/selected KB context, so it's obvious in code
  which facts are looked-up vs. generated.
- Function and file names in `snake_case`; one responsibility per module (matches the repo
  map above — don't collapse pipeline stages into one file).

## Definition of Done (agent-assisted changes)
- Code/docs are committed to the repo (not left uncommitted).
- The relevant Must's "verify" step (from `project_structure.md`) passes.
- The Trello card being worked is updated with what changed.
- No secrets, API keys, or `.env` contents are committed.
- No hallucinated facts in generated output — if a KB doc doesn't cover something, the
  prompt/template should omit it rather than let the model invent it.

## Never Do
- Never commit `.env` or any file containing API keys.
- Never invent APIs or services that aren't in the Stack section above — ask first.
- Never expand scope into anything listed under MVP Scope exclusions (auth system, image
  parsing) without an explicit decision logged in `project_structure.md`.
- Never add a vector database or embeddings pipeline "by default" — the RAG decision in
  `rag_decision.md` is deterministic-lookup + lightweight metadata filtering only, unless
  that file is explicitly updated to say otherwise.
- Never paste external source text verbatim into `knowledge_base/secondary/` — summarize
  in our own words.

## How the Team Uses Agents (Codex)
- Work one Trello card at a time. Before prompting Codex, paste the card description and
  its Must ID into the prompt along with a pointer to this file ("follow AGENTS.md").
- After Codex makes changes, check the diff against the Never Do list above before
  committing.
- If Codex proposes something outside MVP Scope, treat it as a suggestion for a future
  card, not something to merge now.
