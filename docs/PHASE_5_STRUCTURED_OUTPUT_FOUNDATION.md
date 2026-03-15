# Phase 5 Structured Output Foundation

## Purpose

This document records the architecture decisions taken for the first implementation slice of Phase 5 (structured outputs). The goal of this slice is **not** to finish all Phase 5 business modes yet. The goal is to establish a reusable, validated, and repository-compatible foundation that can later support extraction, structured summaries, checklist generation, CV analysis, and code analysis.

## Architecture decisions

### 1. Separate payload schemas from execution metadata
Structured business content now lives in task payload schemas under `src/structured/base.py`. Execution metadata such as parsing failures, validation failures, raw model output, and render-mode selection lives in `src/structured/envelope.py`.

Why this was chosen:
- keeps task payloads reusable for future automations
- avoids mixing business data with transport/execution concerns
- makes error handling and UI rendering easier later

### 2. Use explicit nested Pydantic models
Loose dictionaries were replaced where practical with explicit nested models such as:
- `Relationship`
- `ExtractedField`
- `ChecklistItem`
- `ContactInfo`
- `CVSection`

Why this was chosen:
- stronger validation
- more predictable structure for UI/renderers
- easier future migration to tools/agents

### 3. Controlled-failure envelope instead of silent schema fabrication
The parser no longer fabricates semantic fields to force a payload through validation. It now:
1. extracts a JSON candidate
2. sanitizes only safe syntactic issues
3. validates against the requested schema
4. returns a controlled failure envelope when validation still fails

Why this was chosen:
- avoids false positives
- makes debugging easier
- keeps structured outputs trustworthy

### 4. Keep registry focused on task metadata
`src/structured/registry.py` now stores task definitions, schemas, RAG requirements, and preferred render modes. It no longer owns provider construction.

Why this was chosen:
- avoids mixing task catalog responsibilities with execution responsibilities
- keeps the foundation easier to extend later

### 5. Keep runtime task execution compatible with the existing app
Task handlers remain lightweight and use the project’s current provider registry and current RAG retrieval flow when `use_rag_context=True`.

Why this was chosen:
- prevents a second parallel document-analysis runtime path
- aligns Phase 5 with the existing chat/RAG architecture

### 6. Add explicit render-mode metadata now
The foundation already exposes render modes in the execution envelope (`json`, `friendly`, and `checklist` where appropriate), even though the UI renderer is not implemented yet.

Why this was chosen:
- keeps generation decoupled from presentation
- makes future UI integration cleaner

## Files created or modified in this slice

### New / updated structured-output foundation files
- `src/structured/__init__.py`
- `src/structured/base.py`
- `src/structured/envelope.py`
- `src/structured/parsers.py`
- `src/structured/registry.py`
- `src/structured/schemas.py`
- `src/structured/service.py`
- `src/structured/tasks.py`

### Supporting fix made while stabilizing imports
- `src/providers/registry.py`

### Documentation added
- `docs/PHASE_5_STRUCTURED_OUTPUT_FOUNDATION.md`

## What was corrected from the initial draft

- removed the most fragile JSON extraction approach based on unsupported recursive regex
- removed the risky strategy of inventing missing semantic fields just to make validation pass
- separated validated task payloads from execution-envelope metadata
- replaced zero-byte `schemas.py` with a compatibility re-export module
- fixed `ChecklistPayload.progress_percentage` to a 0..100 range
- made OpenAI provider loading optional so the structured package can be imported even when the `openai` package is not installed
- moved task registration to explicit payload classes instead of relying on union indexing
- kept render-mode metadata explicit in the foundation

## Deferred pieces

These items are intentionally **not finished** in this slice and should be treated as the next implementation steps rather than missing bugs in the foundation itself:

1. **UI integration**
   - no new controls in `main_qwen.py` yet
   - no user-facing renderer in `src/ui/` yet
   - no selection between JSON/friendly/checklist views yet

2. **Full task-specific polish**
   - prompts are still functional stubs
   - task instructions are not yet tuned for benchmark-quality reliability
   - code-analysis mode is not yet implemented

3. **Observability and logging polish**
   - no dedicated debug panel yet
   - no structured-output telemetry in the app UI yet

4. **Tests**
   - no formal unit tests yet for parser, schemas, registry, and service

5. **Documentation beyond the foundation**
   - no full Phase 5 usage guide yet
   - no example artifacts yet

## Recommended next step

The safest next step is **UI wiring + first real render layer**, not more schema expansion. In practice, the next slice should:
1. expose structured task selection in the app
2. add a renderer for JSON and friendly view
3. wire one real task end-to-end (recommended: extraction or summary)
4. only then add the remaining modes
