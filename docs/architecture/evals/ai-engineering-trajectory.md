# AI Engineering Trajectory

This document records the AI-engineering layer behind the product: provider controls, structured outputs, evals, benchmarks, diagnostics, and runtime observability.

## Current AI Engineering Surface

The AI Lab area provides:

- runtime and observability views;
- workflow inspector;
- document experiments;
- benchmarks;
- evals and diagnosis;
- experiments and artifacts;
- MCP Operations;
- provider/model controls through Runtime Controls and Preferences.

The product workflows use these controls indirectly through the Product API. The UI can run a workflow while the AI Lab explains what ran, which provider/model was selected, what evidence was used, and what artifacts were produced.

## Provider Evolution

The provider layer evolved from local experimentation into a configurable runtime surface:

- local Ollama can be used as the embedding sidecar path, especially for `embeddinggemma`;
- hosted Ollama-compatible endpoints can be discovered dynamically;
- OpenAI-compatible and Hugging Face lanes remain selectable through provider/runtime controls;
- provider diagnostics help validate whether a configured lane is available before relying on it.

Primary references:

- `src/providers/ollama_provider.py`
- `src/providers/openai_provider.py`
- `src/providers/huggingface_inference_provider.py`
- `src/providers/registry.py`
- `src/services/runtime_controls.py`
- `frontend/src/pages/RuntimeControlsPage.tsx`
- `frontend/src/pages/PreferencesPage.tsx`

## Structured Output Discipline

Structured-output work began in extraction and evaluation phases, then became a product discipline. Current workflows rely on shaped payloads and presenters so outputs can become UI cards, deck contracts, Trello cards, Notion pages, evidence packs, and run-history records.

Primary references:

- `src/structured/`
- `src/product/presenters.py`
- `src/product/service.py`
- `legacy/docs/phases/phase-5-structured-output-foundation.md`
- `legacy/docs/phases/phase-5-structured-outputs-usage-guide.md`

## Evals And Benchmarks

The repository preserves a trail from synthetic CV and document extraction evaluation into current AI Lab evals and benchmark surfaces.

Important threads:

- benchmark PDF extraction and evidence CV experiments;
- Phase 4.5 and Phase 5 evaluation reporting;
- model comparison and provider selection;
- eval typing and live verdict labels;
- current benchmark/eval UI surfaces.
- public workflow naming for maintained eval checks through `evals.yml` and
  `evals-live.yml`, replacing phase-numbered workflow names.

Primary references:

- `.github/workflows/evals.yml`
- `.github/workflows/evals-live.yml`
- `docs/architecture/evals/benchmark-execution.md`
- `docs/architecture/evals/decision-gate.md`
- `docs/architecture/evals/closure.md`
- `docs/reference/benchmark-pdf-extraction.md`
- `docs/reference/evidence-cv-pipeline.md`
- `legacy/docs/phases/phase-7-model-comparison.md`

## Runtime Observability

Runtime observability matured from logs and generated state into product-visible controls:

- UTC timestamps are persisted canonically;
- browser-local rendering makes timelines readable in the user's context;
- telemetry captures run behavior;
- private usage analytics capture sessions, attribution, referrers, source context, and click filters for admin review.

Primary references:

- `src/product/telemetry.py`
- `src/storage/product_usage_events.py`
- `frontend/src/pages/RuntimeObservabilityPage.tsx`
- `frontend/src/pages/LabOverviewPage.tsx`
- `frontend/src/pages/AdminUsagePage.tsx`

## Current Status

The current AI-engineering layer is not a separate demo. It is the observability and control plane around the product workflows. Historical evals and experiments remain available as reference material, while current runtime controls and diagnostics support live product operation.
