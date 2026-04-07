# Phase 10.25 — Productization of the first slice of Executive Deck Generation

## Objective

This document should now be read as the **technical documentation for the first slice** of the broader **Executive Deck Generation** capability.

The official capability context and catalog are in:

- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

Here, the focus is narrower:

- how to turn `ppt_creator_app` into a specialized layer within the current ecosystem
- how to complete the first priority deck
- how to move from the contract to HTTP integration and minimum UX

At this moment, the prioritized technical slice remains:

- **benchmark/eval -> executive review deck**

`ppt_creator_app` enters as the **specialized executive rendering layer** within this broader capability.

> In short: `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md` defines the product capability; this document details the technical productization of the first slice.

Important complementary documents for fully implementing the capability:

- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENTATION_PLAN.md`
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG.md`
- `docs/EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE.md`
- `docs/EXECUTIVE_DECK_GENERATION_API_CONTRACT.md`
- `docs/EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE.md`
- `docs/EXECUTIVE_DECK_GENERATION_UX_SPEC.md`
- `docs/EXECUTIVE_DECK_GENERATION_TEST_STRATEGY.md`
- `docs/EXECUTIVE_DECK_GENERATION_QUALITY_AND_GOVERNANCE.md`

---

## Relationship to the broader capability

The project should now be read like this:

- **AI Workbench Local** = the main applied-AI product
- **Executive Deck Generation** = a recurring product capability
- **`ppt_creator_app`** = the specialized renderer that enables this capability

The priority deck families now become:

- summary / executive review decks
- document review decks
- comparison / decision decks
- action-plan decks
- candidate review decks
- evidence / audit decks

This document covers the productization layer of **P1**:

- **Benchmark & Eval Executive Review Deck**

---

## Why this strengthens the product capability

This feature significantly improves the repository's professional narrative because it closes a very strong loop:

1. the system measures quality with benchmark/evals
2. it consolidates results into a structured contract
3. it transforms that into an executive artifact consumable by the business
4. it preserves a clear separation between domain, orchestration, and rendering

This helps show that the project is not just:

- chat with an LLM
- document-grounded RAG
- structured outputs

It also shows:

- **product thinking**
- **versioned contract design**
- **integration between specialized services**
- **generation of business artifacts**
- **end-to-end QA and observability for a feature**

In practice, this strengthens the reading that you know how to bridge:

- the applied-AI layer
- the software/architecture layer
- the executive-delivery layer for stakeholders

---

## Official architectural decision

This is the decision that best preserves the strength of the project.

### What remains in AI Workbench Local

AI Workbench remains the **source of truth** for:

- benchmark
- evals
- EvidenceOps
- structured outputs
- metrics consolidation
- executive recommendation

### What stays in `ppt_creator_app`

`ppt_creator_app` remains the specialized service for:

- validating the presentation schema
- rendering `.pptx`
- reviewing visual quality
- generating previews
- comparing artifacts

### The correct boundary

The strongest boundary is:

**AI Workbench Local = domain intelligence + orchestration**  
**`ppt_creator_app` = specialized executive rendering**

### What not to do

To preserve this architecture, the recommended direction is **not** to:

- copy the `ppt_creator_app` code into AI Workbench
- couple AI Workbench to the renderer's raw schema too early
- use the `ppt_creator_ai/` layer for this benchmark/eval slice
- turn deck export into logic scattered across the UI

For this use case, the strongest interpretation is **deterministic**:

**benchmark/eval -> structured contract -> presentation payload -> `.pptx` render**

With no LLM in the middle of the final executive-deck export stage.

This matters because it conveys engineering discipline and reduces the risk of noise/hallucination in the last mile.

---

## Current state already in place

### In AI Workbench Local

There is already a concrete foundation for the first slice.

#### Base document for the current technical slice

- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

#### Contract and adapter service already implemented

- `src/services/presentation_export.py`

Today it already delivers:

- versioned contract `presentation_export.v1`
- `export_kind = "benchmark_eval_executive_deck"`
- builder from project aggregates/logs
- adapter to a `ppt_creator`-compatible payload

Functions already in place:

- `build_benchmark_eval_contract(...)`
- `build_benchmark_eval_contract_from_logs(...)`
- `build_ppt_creator_payload_from_benchmark_eval_contract(...)`

#### Existing tests

- `tests/test_presentation_export_unittest.py`

These tests already validate:

- creation of the concrete contract from logs
- presence of metrics/highlights/leaderboards
- expected slide sequence in the `ppt_creator` payload

### In `ppt_creator_app`

The sibling project is already mature enough to enter as a specialized service.

#### Main documentation

- `/Users/danyellambert/ppt_creator_app/README.md`
- `/Users/danyellambert/ppt_creator_app/NEXT_STEPS.md`

#### Capabilities already available

- `.pptx` renderer
- schema with `pydantic`
- local HTTP API
- quality review
- preview
- `.pptx` comparison
- artifact serving
- local playground/editor

#### Useful existing endpoints

According to `README.md` and `ppt_creator/api.py`, endpoints such as these already exist:

- `GET /health`
- `GET /artifact`
- `POST /validate`
- `POST /review`
- `POST /preview`
- `POST /render`

#### Relevant schema compatibility

`ppt_creator/schema.py` already supports the slide types used by the current slice:

- `title`
- `summary`
- `metrics`
- `table`
- `comparison`
- `bullets`

In other words: the main structural compatibility for the first slice already exists.

---

## The real gap between the current state and the product feature

Although the foundation already exists, important layers are still missing before this becomes a real AI Workbench feature.

### Gap 1 — HTTP integration does not exist yet

Today AI Workbench:

- generates the contract
- generates the payload

But it still **does not call** `ppt_creator_app` over HTTP.

### Gap 2 — configuration does not exist yet

There is still no explicit configuration in the current project for presentation export, for example:

- service base URL
- timeout
- remote output/preview directories
- artifact policy

### Gap 3 — UX does not exist yet

The main app still does not have:

- an explicit action to export an executive deck
- `.pptx` download
- export-status visualization
- fallback when the deck service is offline

### Gap 4 — artifact lifecycle does not exist yet

There is still no standard flow to persist:

- the JSON contract
- the payload sent to the renderer
- the renderer response
- the final `.pptx`
- related review/previews

### Gap 5 — feature-specific observability does not exist yet

Operational export signals are still missing, such as:

- success/failure per export
- renderer latency
- artifact size
- how many previews were generated
- service unavailability rate

### Gap 6 — product integration does not exist yet

The feature has still not been clearly fitted into the path across:

- the current Streamlit app
- the future Gradio UI
- the future Phase 10.25 web app / HTTP backend

---

## Official thesis of the feature

`ppt_creator_app` **must not** appear as a parallel product inside AI Workbench.

It should be positioned as a product capability:

> AI Workbench Local transforms benchmark, eval, EvidenceOps, and structured-output signals into reproducible executive artifacts.

In the first slice, that means:

> From benchmark/eval logs and aggregates, the system generates an executive `.pptx` deck ready for review, sharing, and demonstration.

This thesis is strong because it shows that the project knows how to:

- measure quality
- consolidate evidence
- translate technical signals into an executive narrative
- generate a reusable business deliverable

---

## Recommended implementation order

This is the strongest order for product, engineering, and portfolio value.

### Slice 0 — contract and adapter foundation

**Status:** already delivered.

- [x] versioned contract
- [x] builder in AI Workbench
- [x] adapter for a `ppt_creator`-compatible payload
- [x] foundation unit tests

### Slice 1 — synchronous HTTP integration

**Recommended next step.**

Objective: move from a “ready payload” to an “on-demand generated `.pptx` deck.”

Minimum delivery:

- [x] create `presentation_export_service` in AI Workbench
- [x] call `GET /health` on `ppt_creator_app` before rendering
- [x] call `POST /render` with the executive deck payload
- [x] download the `.pptx` through `GET /artifact`
- [x] save local export artifacts in AI Workbench
- [x] return a structured result to the UI

### Slice 2 — UX in the current app (Streamlit)

Objective: turn the integration into a visible product feature.

Minimum delivery:

- [x] **Export executive deck** button
- [x] `.pptx` download
- [x] contract JSON download
- [x] payload JSON download
- [x] friendly status/error display

### Slice 3 — artifact lifecycle hardening

Objective: make the feature auditable and reusable.

Minimum delivery:

- [ ] local directory/versioning per `export_id`
- [ ] persistence of export metadata
- [ ] retention/cleanup of old artifacts
- [ ] operational feature log

### Slice 4 — integration into Phase 10.25

Objective: fit the feature into the HTTP backend and into the Streamlit -> Gradio -> web app evolution.

Minimum delivery:

- [ ] export endpoint in the AI Workbench backend
- [ ] exposure of the capability in the intermediate UI
- [ ] explicit action in the future web app

### Slice 5 — `export_kind` expansion

After the benchmark/eval slice is solid, expand to new decks.

Suggested order:

1. `benchmark_eval_executive_deck`
2. `evidenceops_document_review_deck`
3. `phase_closure_or_project_review_deck`

### Slice 6 — operational hardening

Only after the feature is already useful and stable:

- [ ] Docker/compose for `ppt_creator_app`
- [ ] stronger timeouts and retries
- [ ] asynchronous queue for heavy renders
- [ ] hybrid deployment strategy

---

## The smallest demonstrable slice with the best cost/benefit

If the goal is to deliver the **best demonstrable MVP** of this feature without opening the scope too much, the recommendation is:

1. keep the current v1 contract
2. create `presentation_export_service`
3. perform synchronous export of the benchmark/eval deck
4. save locally:
   - contract
   - payload
   - render response
   - `.pptx`
5. expose a button in the current UI
6. add focused service tests

This slice is already enough to demonstrate:

- contract design
- service-to-service integration
- generation of a real artifact
- product UX
- the ability to translate benchmark/eval into an executive deck

---

## Recommended integration design in AI Workbench

## 1. Configuration layer

Add dedicated configuration for the feature.

### Suggested variables

```env
PRESENTATION_EXPORT_ENABLED=true
PRESENTATION_EXPORT_BASE_URL=http://127.0.0.1:8787
PRESENTATION_EXPORT_TIMEOUT_SECONDS=120
PRESENTATION_EXPORT_REMOTE_OUTPUT_DIR=outputs/ai_workbench_exports
PRESENTATION_EXPORT_REMOTE_PREVIEW_DIR=outputs/ai_workbench_export_previews
PRESENTATION_EXPORT_LOCAL_ARTIFACT_DIR=artifacts/presentation_exports
PRESENTATION_EXPORT_INCLUDE_REVIEW=true
PRESENTATION_EXPORT_PREVIEW_BACKEND=auto
PRESENTATION_EXPORT_REQUIRE_REAL_PREVIEWS=false
PRESENTATION_EXPORT_FAIL_ON_REGRESSION=false
```

### Where this goes

- `src/config.py`
- `.env.example`

### Why this matters

This turns executive export into **part of the product**, rather than a hardcoded detail of a local machine.

---

## 2. Service layer

Create a dedicated service in AI Workbench, for example:

- `src/services/presentation_export_service.py`

### Responsibilities of this service

- validate whether the feature is enabled
- check the health of `ppt_creator_app`
- build the contract and payload
- decide remote artifact names/directories
- call the renderer over HTTP
- download relevant artifacts
- persist local copies and metadata
- return a structured result for the UI and future endpoints

### Boundary recommendation

The service **should not** know how to assemble slides “by hand.”

It should delegate that to the existing flow:

- `build_benchmark_eval_contract_from_logs(...)`
- `build_ppt_creator_payload_from_benchmark_eval_contract(...)`

### HTTP client recommendation

Prefer a lightweight implementation that is consistent with the rest of the project.

Since the repository already uses `urllib` in other integrations, the most coherent choice for the first slice is:

- `urllib.request`

This avoids adding a new dependency just for this feature.

---

## 3. Path and artifact strategy

This point is important.

Based on the current behavior of `ppt_creator/api.py`, the most natural flow is:

1. AI Workbench requests rendering with a remote `output_path`
2. `ppt_creator_app` saves the file inside its own workspace
3. AI Workbench downloads the artifact through `GET /artifact`
4. AI Workbench persists a local copy as its own artifact

### Why this strategy is best for the first slice

Because it:

- reuses the existing API
- avoids a shared volume too early
- avoids changing the renderer to return bytes right now
- preserves the HTTP-first boundary defined in the roadmap

### Suggested remote structure in `ppt_creator_app`

```text
outputs/ai_workbench_exports/
  <export_id>/
    benchmark_eval_deck.pptx
    previews/
```

### Suggested local structure in AI Workbench

```text
artifacts/presentation_exports/
  <export_id>/
    contract.json
    ppt_creator_payload.json
    render_response.json
    benchmark_eval_deck.pptx
    review.json
    preview_manifest.json
    thumbnail_sheet.png
```

### Result

This gives AI Workbench full traceability for the feature without depending on the internal filesystem of the deck service.

---

## 4. Recommended HTTP flow

### Preflight

First, AI Workbench calls:

- `GET /health`

If the service is offline:

- the UI should fail gracefully
- the user should still be able to download `contract.json` and `payload.json`

### Render

Then it calls:

- `POST /render`

Recommended payload for the first slice:

```json
{
  "spec": {
    "presentation": {
      "title": "AI Workbench Local — Benchmark & Eval Review",
      "subtitle": "Executive summary of the current round",
      "author": "AI Workbench Local",
      "date": "2026-04-05",
      "theme": "executive_premium_minimal",
      "footer_text": "AI Workbench Local • Benchmark & Eval Review"
    },
    "slides": []
  },
  "output_path": "outputs/ai_workbench_exports/<export_id>/benchmark_eval_deck.pptx",
  "include_review": true,
  "preview_output_dir": "outputs/ai_workbench_exports/<export_id>/previews",
  "preview_backend": "auto",
  "preview_require_real": false,
  "preview_fail_on_regression": false
}
```

### Artifact download

After rendering:

- download the `.pptx` through `GET /artifact?path=...`
- persist `render_response.json`
- if relevant preview/manifest/thumbnail paths exist, save them as well

---

## 5. Structured result of the feature

`presentation_export_service` should return something structured, not a raw API dictionary.

Example useful result fields:

- `export_id`
- `export_kind`
- `contract_version`
- `status`
- `service_health`
- `remote_output_path`
- `local_artifact_dir`
- `local_pptx_path`
- `local_contract_path`
- `local_payload_path`
- `local_render_response_path`
- `local_review_path`
- `local_preview_manifest_path`
- `thumbnail_sheet_path`
- `warnings`
- `error_message`

This helps a lot to avoid coupling the UI to internal details of the HTTP call.

---

## How the feature should appear in the UI

## Product principle

In the UI, the capability should appear as part of the product, for example:

- **Export executive deck**
- **Executive artifacts**

And not as:

- “open ppt_creator_app”
- “use sibling project”

### Best initial entry point

Given the current state of the project, the best initial entry point is near the area where benchmark/evals are already read as executive signals.

Since `src/ui/sidebar.py` already exposes aggregated eval/readiness signals, the strongest first fit could be:

- an expander/dedicated panel for executive export
- or a separate visual panel inside the benchmark/evals flow

### Minimum UI actions

In the first slice, the UI should allow:

- generate the deck
- download `.pptx`
- download the contract
- download the payload
- view export status
- view warnings/fallbacks

### Desirable actions later

- open the thumbnail sheet
- download the deck review
- list recent exports
- rerun export from the same snapshot

---

## Why not use `ppt_creator_ai/` in this slice

This is an important decision.

`ppt_creator_app` has an optional `ppt_creator_ai/` layer, but **it should not be part of the first AI Workbench slice**.

### Reason

In this use case, AI Workbench already has the data and the domain intelligence.

It already knows:

- what the top model is
- what the PASS rate is
- what the watchouts are
- what the next steps are

Therefore, the strongest path is:

**deterministic and auditable**, not generative.

### Professional benefit

This shows AI Engineer maturity because it demonstrates that you know:

- where to use an LLM
- where **not** to use an LLM
- when to prefer a structured contract and deterministic rendering

---

## Tests required for the complete feature

## What already exists

- [x] contract builder test
- [x] payload adapter test

## What still needs to exist

### Service unit tests

- [x] `tests/test_presentation_export_service_unittest.py`

It should cover at least:

- remote path assembly
- correct render request
- handling service unavailability
- HTTP timeout
- local artifact persistence
- fallback when `/health` fails

### Optional integration tests

- [ ] smoke test with `ppt_creator_app` running locally

This test does not need to run all the time in the main CI if the sibling service is not part of the default environment. But it should exist as a reproducible local path.

### UI tests

- [ ] smoke test for the executive export panel

The goal is not to test real `.pptx` rendering in the UI, but rather:

- button present
- status handled
- coherent download/fallback behavior

---

## Feature observability

To make this capability feel professional, it is important to instrument the export flow.

### Minimum signals

- `export_id`
- `export_kind`
- `contract_version`
- `service_available`
- `render_latency_s`
- `artifact_download_latency_s`
- `pptx_size_bytes`
- `preview_count`
- `export_status`
- `error_type`

### Where to record it

These signals can go into a lightweight/versioned AI Workbench log, without depending on heavy observability at this phase.

### Why this matters

This makes it clearer that the feature was not added as an isolated integration, but as a capability with an explicit technical boundary:

- monitored
- auditable
- ready to grow

---

## How this feature fits into Phase 10.25

In the roadmap, Phase 10.25 is the evolution toward:

- Streamlit -> Gradio -> app web

Executive export fits very well here because it is a cross-cutting interface and backend capability.

### Correct interpretation

This feature is strongest when it evolves like this:

1. **first**: export in the current app, with simple and proven UX
2. **later**: internal AI Workbench export endpoint
3. **later**: Gradio/web surface
4. **only then**: Docker/hybrid deployment of the specialized service

### Why this order is best

Because it preserves a mature engineering narrative:

- first the domain foundation
- then service integration
- then UX
- then deployment

---

## Recommended future expansion of `export_kind`

After the benchmark/eval slice, the strongest direction is to reuse the same foundation for new artifacts.

### 1. `benchmark_eval_executive_deck`

First because the foundation already exists.

### 2. `evidenceops_document_review_deck`

Very strong for an enterprise product demonstration.

Examples of future blocks:

- executive summary
- risks and obligations
- evidence-backed findings
- recommended actions
- owners and due dates

### 3. `project_phase_closure_deck`

Useful to show the project itself as a professional engineering case.

Examples of future blocks:

- completed deliveries
- phase benchmarks/evals
- trade-offs
- next steps

---

## Done criteria by level

## Minimum technical done

We can consider the feature technically integrated when the following exist:

- [x] synchronous export working from AI Workbench to `ppt_creator_app`
- [x] `.pptx` download
- [x] local persistence of contract/payload/response
- [x] service tests
- [x] minimum UI with an explicit export action

## Product done

The feature starts to look like a real product when the following exist:

- [ ] correct capability naming
- [ ] clear success/failure/download UX
- [ ] recent exports or organized artifacts
- [ ] feature documentation in the repository

## Portfolio done

The feature becomes strong AI Engineer evidence when the following exist:

- [ ] screenshot/GIF of the export happening
- [ ] real deck generated from benchmark/eval
- [ ] architecture diagram for `domain contract -> renderer service`
- [ ] short write-up explaining why AI Workbench and `ppt_creator_app` are separated

---

## What this feature proves about you as an AI Engineer

If implemented in this direction, this feature helps prove that you know how to:

- transform technical signals into business artifacts
- design versioned contracts between services
- avoid early coupling between domain and renderer
- choose a deterministic path when it is better than using an LLM
- fit a new capability into product and interface evolution
- think about observability, QA, and artifact lifecycle

In other words, the desired reading becomes:

> this person not only builds AI pipelines and measures quality; they also know how to package the results into a clear, defensible, and useful product capability for stakeholders.

---

## Executive summary of the recommendation

The strongest path is to keep what has already been decided:

- **AI Workbench Local** remains the brain and source of truth
- **`ppt_creator_app`** enters as the specialized executive-artifact service
- the first official slice remains **benchmark/eval -> executive deck**
- the correct implementation is **HTTP first**, **Docker later**
- the first product path should be **deterministic**, without depending on `ppt_creator_ai/`

### Recommended next delivery

If you choose only one next concrete delivery, the best one is:

> implement `presentation_export_service` + an executive-export button in the current app + local persistence for render artifacts.

This is the smallest slice that already turns the current foundation into a real, demonstrable feature with strong portfolio value.