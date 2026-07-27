# rag_decision.md - Niche Real Estate Pitch Engine

## RAG Decision

For our MVP, we chose **non-RAG context injection** rather than a full retrieval-augmented generation pipeline.

## Decision

We load and select relevant markdown content directly from the primary and secondary knowledge bases, then inject that context into the prompt along with structured listing inputs and PLZ-based location facts. We do **not** use embeddings, a vector database, or semantic similarity search in the MVP.

## Why this decision fits our project

Our current corpus is small and manageable: a limited set of markdown files for brand tone, past ad examples, and Berlin market context. Because these files are few in number and largely static during the 2-day build, direct loading and selection is simpler, faster, and easier to test than building a full RAG stack.

The most important factual enrichment in our system, such as nearby schools, public transport, and Kita information, is based on structured PLZ/location lookup rather than semantic retrieval from long unstructured documents. That means this part of the system is a deterministic data lookup problem, not a RAG problem.

Our main Quality objective is to generate apartment ads that are accurate, brand-consistent, and clearly different from generic ChatGPT output, regardless of whether we use retrieval or direct context injection. For this MVP, that quality need is better served by keeping the pipeline simple and reliable, so we can spend time on prompt quality, brand voice, and human review instead of building retrieval infrastructure.

The project is also constrained to a 2-day delivery window with free-tier tools and limited engineering capacity. Adding embeddings, chunking, indexing, and retrieval evaluation would increase complexity, cost, and debugging effort without clearly improving the MVP outcome for such a small corpus.

## What we implemented instead

Instead of full RAG, our MVP uses:
- direct markdown loading from the primary and secondary knowledge bases,
- explicit prompt sections for brand voice, market context, and listing details,
- deterministic PLZ-based lookup for amenities and neighborhood facts,
- optional lightweight filtering of comparable examples based on metadata such as neighborhood or price range, if needed.

This gives us most of the practical benefit we need in the MVP while keeping the codebase easier to understand, test, and present.

## When we would revisit this decision

We would revisit RAG if one or more of the following becomes true:
- the primary knowledge base grows to many past listing examples,
- the secondary research set expands across many longer market and regulation documents,
- prompt context becomes too large for efficient injection,
- users need flexible querying across a much broader document library,
- retrieval quality becomes more important than implementation simplicity.

In that future case, we would first try a minimal retrieval layer, such as chunk selection or metadata filtering, before moving to a full vector database approach.

## Final position

For this MVP, **non-RAG context injection is the better engineering choice** because it matches our small corpus, deterministic data needs, tight timeline, and quality goal of producing accurate, brand-aligned, non-generic apartment ads.