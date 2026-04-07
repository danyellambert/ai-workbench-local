# Executive Deck Generation — Benchmark/Eval Executive Review Contract v1

## Objective of this deliverable

Document and begin implementation of the first technical slice of the **Executive Deck Generation** capability between:

- **AI Workbench Local**
- **`ppt_creator_app`**

> For the complete product reading, deck catalog, and capability roadmap, also see: `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

> For the technical productization reading of the first slice in the current ecosystem, also see: `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`

The focus of this round remains the path:

**benchmark/eval -> structured contract -> payload compatible with `ppt_creator`**

This document should be read as:

- the **technical P1** of the Executive Deck Generation capability
- specifically the **benchmark/eval executive review** deck

The next deck families planned by the broader capability include:

- document review deck
- policy/contract comparison deck
- action plan deck
- candidate review deck
- evidence pack deck

## What we will do in this round

### Scope included now

1. create a **JSON contract v1** for the `benchmark/eval -> executive deck` slice
2. create a **builder** that converts aggregates from the current project into a stable contract
3. create an **adapter** that transforms this contract into a payload compatible with the schema expected by `ppt_creator`
4. add **focused unit tests** to guarantee foundation stability

### Scope explicitly out of this round

Still **not included** now:

- a real HTTP call to `ppt_creator_app`
- Docker / port / shared volume
- UI to export the deck from the main app
- asynchronous rendering queue
- real preview / remote review / artifact download

These points are left for the next slice, when the contract is already stable.

## Architectural reading

At this stage, the separation is as follows:

- **AI Workbench Local**
  - remains the source of truth for benchmarks/evals
  - consolidates the domain aggregates
  - generates the intermediate presentation contract
- **`ppt_creator_app`**
  - remains the specialized service/renderer
  - will later receive a pre-structured payload for `.pptx`

In other words: **the foundation lands in the domain first and only later moves up to API/Docker**.

## JSON contract v1

### Contract name

> Technical honesty note: the slice already implemented in code still uses the foundation naming `presentation_export.v1` / `benchmark_eval_executive_deck`. This remains valid as the current base, even with the broader capability now positioned as **Executive Deck Generation**.

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

### High-level structure

```json
{
  "contract_version": "presentation_export.v1",
  "export_kind": "benchmark_eval_executive_deck",
  "presentation": {
    "title": "AI Workbench Local — Benchmark & Eval Review",
    "subtitle": "Executive summary of the current round",
    "author": "AI Workbench Local",
    "date": "2026-04-04",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Benchmark & Eval Review"
  },
  "model_comparison_snapshot": {
    "total_runs": 4,
    "total_candidates": 12,
    "success_rate": 0.917,
    "avg_latency_s": 1.284,
    "avg_format_adherence": 0.944,
    "avg_use_case_fit_score": 0.902,
    "top_model": "qwen2.5:7b",
    "top_runtime_bucket": "local"
  },
  "eval_snapshot": {
    "total_runs": 18,
    "pass_rate": 0.778,
    "warn_rate": 0.167,
    "fail_rate": 0.056,
    "avg_score_ratio": 0.912,
    "avg_latency_s": 1.537,
    "needs_review_rate": 0.111,
    "top_suite_name": "structured_real_document_eval"
  },
  "executive_summary": "Top candidate and eval health in one executive package.",
  "key_highlights": [
    "Current top benchmark candidate: qwen2.5:7b.",
    "Eval PASS rate above 75% in the current round."
  ],
  "key_metrics": [
    {
      "label": "Benchmark candidates",
      "value": "12",
      "detail": "Top model: qwen2.5:7b"
    }
  ],
  "model_leaderboard": [
    {
      "rank": 1,
      "model": "qwen2.5:7b",
      "provider": "ollama",
      "runtime_bucket": "local",
      "comparison_score": 0.941,
      "avg_latency_s": 1.08,
      "format_adherence": 0.98,
      "use_case_fit_score": 0.93,
      "success_rate": 1.0
    }
  ],
  "eval_suite_leaderboard": [
    {
      "rank": 1,
      "suite_name": "structured_real_document_eval",
      "pass_rate": 1.0,
      "avg_score_ratio": 0.96,
      "avg_latency_s": 1.12,
      "total_runs": 6
    }
  ],
  "recommendation": "Promote the leading candidate to the next controlled round.",
  "watchouts": [
    "There are still suites in WARN/FAIL that require hardening."
  ],
  "next_steps": [
    "Review WARN/FAIL suites.",
    "Serialize this contract and call the deck service through the API."
  ],
  "data_sources": [
    "phase7_model_comparison_log",
    "phase8_eval_store"
  ]
}
```

## Mapping to `ppt_creator`

The adapter for this round will transform the contract above into a presentation payload with the following blocks:

1. `title`
2. `summary`
3. `metrics`
4. model leaderboard `table`
5. eval suite leaderboard `table`
6. `comparison` with recommendation vs. watchouts
7. `bullets` with next steps

## Why this design

This format is strong because:

- it preserves a clear domain contract in AI Workbench
- it avoids coupling the project too early to the raw `ppt_creator` schema
- it already leaves the payload close enough to the final renderer
- it makes the next HTTP API integration stage easier

## Next slice after this delivery

After this contract is stable and covered by tests, the recommended next step is:

1. create a `presentation_export_service`
2. call `ppt_creator_app` over HTTP
3. externalize URL/timeouts through configuration
4. decide the artifact strategy (`bytes` vs `volume/path`)
5. only then run `ppt_creator_app` in Docker as a separate service

## Complementary document

This document remains intentionally focused on the **first technical slice** (`benchmark/eval -> contract -> payload compatible with the renderer`).

For the complete capability process inside AI Workbench Local, including:

- product positioning
- deck family catalog
- P1/P2/P3 prioritization
- architectural boundary
- HTTP integration
- UX
- artifacts
- observability
- fit within Phase 10.25

see:

- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`
