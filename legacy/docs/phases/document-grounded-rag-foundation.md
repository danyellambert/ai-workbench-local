# Phase 4 — Document-Grounded RAG Foundation

## Goal

Allow the application to answer with grounded context extracted from user-provided documents.

## What was implemented

- upload support for:
  - PDF
  - TXT
  - CSV
  - MD
  - PY
- text extraction by file type
- local chunking with size and overlap controls
- local embedding generation
- local RAG index persistence
- similarity-based retrieval
- prompt enrichment with retrieved context
- source display in the final answer

## Main modules introduced

- `src/rag/loaders.py`
- `src/rag/chunking.py`
- `src/rag/vector_store.py`
- `src/rag/prompting.py`
- `src/rag/service.py`
- `src/storage/rag_store.py`
- `src/services/rag_state.py`

## Strategy used

- local embeddings through the Ollama path
- a simple local vector persistence layer as the initial baseline
- cosine-similarity retrieval
- retrieved context injected before answer generation

## Important embedding direction at this stage

This phase explicitly treated multilingual embedding quality as an important retrieval concern and documented `bge-m3` as a strong early choice for Portuguese and multilingual workloads.

## Why this phase mattered

Phase 4 was the first milestone that made the project useful for real document analysis rather than only free-form chat.

It also established the manual RAG foundations that later phases benchmarked, tuned, instrumented, and evolved.

## Source notes retained from the original phase record

The original Portuguese phase notes were preserved in:

- `old/docs/PHASE_4_NOTES.md`

## Closure

Phase 4 is complete because the repository already had a working end-to-end document-grounded RAG flow before the later tuning and validation work of Phase 4.5.

## Transition to the next phase

Once RAG existed, the next step was not more features immediately, but better robustness, measurement, and tuning.
