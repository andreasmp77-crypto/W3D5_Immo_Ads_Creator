# AGENTS.md — knowledge_base/

Scope: this file applies to anything under `knowledge_base/`. It supplements — does not
replace — the root `AGENTS.md`. The Never Do list, Definition of Done, and Must IDs
(`M1`-`M6`) from `project_structure.md` still apply here.

## What lives here
- `primary/` — brand/tone guidelines, property listings, and past ads (per root
  `AGENTS.md` Repo Map). Supports M2 and M4.
- `secondary/` — Berlin market context and other supporting summaries, written in our own
  words (per root `AGENTS.md` Repo Map). Supports M2 and M4.

## Sourcing
- `primary/` content (listings, past ads, brand tone) is original — this is a fictional
  agency, so there is no real company to source it from.
- `secondary/` content must be grounded in real, current research (per the root Never Do
  item: "never paste external source text verbatim into `knowledge_base/secondary/` —
  summarize in our own words"). Write a short original summary of the actual finding, not
  a copy of source wording.
- PLZ-based schools/transport/Kita facts do **not** belong in `knowledge_base/`. Per root
  `AGENTS.md` Conventions, those are looked up by `location_data.py` and injected as
  explicit prompt variables, kept separate from KB context.

## File conventions
- Markdown, one topic per file, with a short frontmatter header (title, last updated) —
  as specified in root `AGENTS.md` Conventions.
- New content docs go under the matching `primary/` or `secondary/` subfolder; never mix
  code and content directories (root `AGENTS.md` Conventions).

## Definition of Done (KB content changes)
- Follows the file conventions above.
- Loads without error via `knowledge_base.py` (M2 verify step: "Test loads sample `.md`
  files without error").
- No secrets committed (root DoD).
- Card notes which Must ID the change supports, per root `AGENTS.md` "How the Team Uses
  Agents."

## Never Do (in addition to root Never Do list)
- Never paste external source text verbatim in `secondary/` — already stated in root
  `AGENTS.md`, restated here since it's the rule most relevant to this folder.
- Never add PLZ/location lookup data into KB markdown files — that data flow is owned by
  `location_data.py`, not the knowledge base (see Sourcing above).
- Never scrape real listings, real agency names, or real individuals' data into
  `primary/` — the Won't list in `project_structure.md` rules out scraping live rental
  prices from external listing sites, and real personal/address data is out of scope for
  this fictional-agency MVP.
