# Roadmap

This is the canonical public roadmap for AI Decision Studio.

It records the product and engineering chronology of the system: what was built,
why each phase mattered, which technical decisions shaped the architecture, what
validation evidence exists, and what remains open. The roadmap is written as a
project history rather than as a task list; later phases build on earlier ones
instead of replacing them.

The project should be read as the evolution of a local-first AI workbench into a
product-oriented AI engineering system with:

- document-grounded workflows;
- structured and evidence-based outputs;
- LangChain/LangGraph evolution used in bounded ways;
- evals, benchmarks, observability, and runtime diagnostics;
- EvidenceOps and external integration paths;
- a React product surface backed by a Product API;
- local Docker and AWS deployment contracts;
- public/admin policy and session-overlay discipline;
- a documentation and operations layer that preserves architecture, validation,
  deployment, and maintenance decisions.

---

## 1. Current State

AI Decision Studio now has two explicit surfaces.

### Product Surface

The current product is the React/Vite frontend backed by `product-api`.

Current product workflows:

- Document Review
- Policy / Contract Comparison
- Action Plan / Evidence Review
- Candidate Review
- Executive Deck Generation as a transversal capability

Current product surfaces:

- Command Center
- Document Library
- Workflow Catalog
- Run History
- Deck Center
- Preferences
- Runtime Controls
- integration handoff panels for Trello and Notion
- Nextcloud/WebDAV import paths

### AI Lab Surface

The AI Lab is the engineering-facing surface for:

- runtime diagnostics;
- grounded chat diagnostics;
- workflow inspection;
- benchmarks;
- evals;
- artifacts;
- EvidenceOps;
- provider/runtime decision support.

### Current Deployment Topology

The maintained deployment paths are:

- Local host/dev: `scripts/run_local_dev.sh`
- Local Docker: `.env.docker` with `docker-compose.local.yml`
- AWS: `.env.aws` with `docker-compose.aws.yml`
- Oracle-like: preserved as legacy/deferred operational history

AWS is the current validated cloud target.

### Current Documentation and Validation Path

Primary documents:

- `README.md`
- `docs/README.md`
- `docs/product/overview.md`
- `docs/architecture/current-product-surface.md`
- `docs/deployment/MULTI_ENVIRONMENT_CONTRACT.md`
- `scripts/README.md`
- `tests/README.md`

Primary validation commands:

```bash
npm --prefix frontend run test
npm --prefix frontend run build
scripts/run_current_test_gate.sh
scripts/readiness_multi_environment_contract_check.sh
```

---

## 2. Phase Status Overview

| Phase | Status | Main outcome |
| --- | --- | --- |
| 0 | Completed | Safe publication baseline and initial positioning |
| 0.5 | Completed | Repository governance and publication discipline |
| 1 | Completed | Usable local product baseline |
| 2 | Completed | Modular architecture |
| 3 | Completed | Multi-provider and prompt-profile foundation |
| 4 | Completed | Document-grounded RAG foundation |
| 4.5 | Completed | RAG validation, extraction benchmarks, retrieval hardening |
| 5 | Completed | Structured outputs and evidence-grounded CV workflows |
| 5.5 | Completed | Bounded LangChain and LangGraph evolution |
| 6 | Completed | Document Operations Copilot |
| 7 | Completed | Model comparison and benchmark reporting |
| 8 | Completed | Persistent eval foundation and runtime-quality signals |
| 8.5 | Completed / reference | Runtime, retrieval, and adaptation decision gates |
| 9 | Completed / reference | Observability and runtime visibility |
| 9.25 | Completed | Runtime economics, usage visibility, and provider diagnostics |
| 9.5 | Completed foundation | EvidenceOps, MCP-style operations, and external integration governance |
| 10 | Completed foundation | Engineering hardening, tests, scripts, and readiness discipline |
| 10.25 | Completed current product split | React product surface, AI Lab surface, Product API, live workflows, deck generation |
| 10.5 | Superseded / replaced | Original Oracle + Cloudflare hybrid plan replaced by local Docker and AWS |
| 11 | In progress | Final publication package and public narrative |
| 12 | Completed foundation | Production-readiness baseline, Golden Surface, provider strategy, frontend parity, and Docker real-backend discipline |
| 13 | Completed / legacy-deferred | Oracle-like Docker, public/admin overlays, hardening, sidecars, and later AWS convergence |
| 14 | In progress | Final validation, repository presentation, release polish, screenshots, and public handoff |

There is no intended gap between 10.5 and 13. After the original Phase 11
publication plan, the project entered a production-readiness runbook that used
its own internal phase numbering. In this public roadmap, that work is recorded
as Phase 12 through Phase 14 so the chronology remains continuous.

---

## 3. Strategic Thesis

The project is designed to show more than "calling an LLM."

It demonstrates:

- product thinking around concrete business workflows;
- retrieval engineering and document grounding;
- structured output design and validation;
- controlled framework adoption instead of framework-driven rewrites;
- eval and benchmark discipline;
- runtime and provider observability;
- external integration boundaries;
- deploy and operations thinking;
- repository hygiene and long-term maintainability.

Professional thesis:

> AI Decision Studio is an applied-AI product system that started as a local
> LLM workbench and matured into a document-grounded decision platform with
> workflows, evals, benchmarks, runtime controls, operational integrations,
> deck generation, and deployable product surfaces.

---

## 4. Chronology

### Phase 0 - Publication and Positioning

Purpose:

- make the repository safe to publish;
- remove obvious publication risks;
- create an initial external framing for the project;
- separate what is safe to share from local/private runtime state.

Completed work:

- established publication baseline;
- created public positioning notes;
- started documenting decisions instead of leaving the repository as only code;
- introduced rules for secrets, local state, generated outputs, and presentation materials.

Primary reference:

- `legacy/docs/phases/publication-and-positioning.md`

### Phase 0.5 - Repository Governance

Purpose:

- add lightweight governance before the project grew further;
- document how the repository should evolve;
- make publication decisions explicit.

Completed work:

- repository governance notes;
- publication guide;
- safer documentation conventions;
- initial separation between current docs and historical notes.

Primary references:

- `legacy/docs/phases/repository-governance.md`
- `legacy/docs/phases/publication-guide-phase-0-5.md`

### Phase 1 - Product Foundation

Purpose:

- move from a raw local app toward a usable product baseline.

Completed work:

- better local UX;
- streaming and interaction improvements;
- settings and error handling improvements;
- clearer user-facing behavior;
- first product-like structure around a local LLM app.

Primary reference:

- `legacy/docs/phases/product-foundation.md`

### Phase 2 - Modular Architecture

Purpose:

- move away from a single-file or tightly coupled app structure.

Completed work:

- clearer separation between UI, providers, services, storage, and config;
- shared runtime/provider abstractions;
- stronger maintainability as later phases added RAG, evals, and workflows.

Primary reference:

- `legacy/docs/phases/modular-architecture.md`

### Phase 3 - Multi-provider and Prompt Profiles

Purpose:

- make runtime choice explicit instead of assuming one local model path.

Completed work:

- multi-provider foundation;
- provider/model selection logic;
- prompt profiles;
- provider-specific controls;
- free-first and free-tier-aware positioning;
- clearer distinction between local Ollama, hosted Ollama-compatible routes,
  Hugging Face server/inference paths, OpenAI-compatible paths, and later
  provider diagnostics.

Primary references:

- `legacy/docs/phases/multi-provider-foundation.md`
- `docs/guides/huggingface-provider-setup.md`

### Phase 4 - Document-grounded RAG

Purpose:

- add real document-grounded question answering.

Completed work:

- ingestion;
- chunking;
- embeddings;
- retrieval;
- document-grounded answers;
- document context construction;
- first persistent RAG/runtime foundations.

Primary reference:

- `legacy/docs/phases/document-grounded-rag-foundation.md`

### Phase 4.5 - RAG Robustness, Tuning, and Observability

Purpose:

- prove and improve retrieval quality rather than assuming RAG works.

Completed work:

- PDF extraction benchmarks;
- retrieval-oriented benchmarks;
- chunking and retrieval tuning;
- reranking experiments;
- vector-store persistence improvements;
- embedding compatibility checks;
- fallback from unsafe vector retrieval to document scan when needed;
- `top_k` and effective runtime setting discipline;
- chart/report generation for benchmark interpretation;
- tracked Phase 4.5 chart assets for PDF extraction, embedding models,
  context-window experiments, retrieval tuning, winner matrix, and
  cost/quality summary;
- example benchmark/eval JSON files for reproducible local experimentation.

Key engineering signals:

- extraction quality became measurable;
- retrieval behavior became debuggable;
- embedding/provider drift became a known operational risk;
- fallback logic avoided brittle "vector store says nothing" failures.

Primary references:

- `legacy/docs/phases/phase-4-5-validation.md`
- `legacy/docs/phases/phase-4-5-benchmark-results.md`
- `docs/reference/benchmark-pdf-extraction.md`
- `docs/assets/phase_4_5/README.md`
- `docs/data/examples/`

### Phase 5 - Structured Outputs

Purpose:

- move from chat answers to validated, task-specific outputs.

Completed work:

- extraction;
- summary;
- checklist;
- code analysis;
- CV analysis;
- stronger output schemas;
- JSON repair/retry paths;
- parse-recovery telemetry;
- UI rendering for structured outputs;
- context-window auto/manual controls for structured tasks;
- smoke evals for the structured output suite.

Evidence CV track:

- evidence-grounded CV parsing;
- dedicated `src/evidence_cv` package with CLI, config, schemas, structure,
  reconciliation, pipeline runner, OCR backends, and Ollama VL integration;
- OCR fallback for insufficient text;
- Docling and OCRmyPDF-backed extraction options;
- VLM-on-demand exploration;
- shadow rollout;
- evidence packs;
- mini gold-set evaluation;
- stronger handling of languages, education, experience, dates, locations, and grounding.

Primary references:

- `legacy/docs/phases/structured-outputs-and-evidence-grounded-cv-extraction.md`
- `legacy/docs/phases/phase-5-structured-output-foundation.md`
- `legacy/docs/phases/phase-5-structured-outputs-usage-guide.md`
- `legacy/docs/phases/phase-5-automated-smoke-eval.md`
- `legacy/docs/phases/phase-5-evidence-pack.md`
- `legacy/docs/phases/phase-5-evidence-cv-evaluation-report.md`
- `docs/reference/evidence-cv-pipeline.md`

### Phase 5.5 - LangChain and LangGraph Evolution

Purpose:

- introduce frameworks as controlled engineering tools, not as a rewrite.

Completed work:

- LangChain shadow comparison;
- LangGraph context/retry workflow;
- workflow routing and guardrails;
- retry/fallback behavior;
- human-review signals;
- document-agent extension;
- tests for routing, retry, fallback, guardrails, and review flags;
- reports for LangChain/LangGraph shadow logs.

Architectural reading:

- manual foundations stayed understandable;
- frameworks were layered where they added orchestration value;
- the project preserved auditability and fallback behavior.

Primary reference:

- `legacy/docs/phases/framework-evolution-with-langchain-and-langgraph.md`

### Phase 6 - Document Operations Copilot

Purpose:

- turn isolated structured tasks into a workflow-oriented document copilot.

Completed work:

- intent classification;
- tool selection;
- policy/compliance review path;
- operational extraction;
- risk analysis;
- guardrails and limitations surfaced in payloads;
- local document-agent logs;
- aggregated reports by intent, tool, and human-review need;
- renderer-friendly document agent output with sources, tool runs, findings, and review flags.

Business direction:

- document review;
- policy/compliance comparison;
- action extraction;
- technical/document assistance;
- operational handoff foundation.

Primary reference:

- `legacy/docs/phases/document-operations-copilot.md`

### Phase 7 - Benchmark and Model Comparison

Purpose:

- compare providers and models with repeatable prompts and workflow presets.

Completed work:

- side-by-side model/provider comparison;
- latency, output size, format adherence, and ranking signals;
- persisted benchmark results;
- aggregate leaderboard views;
- retrieval/embedding/prompt profile comparisons;
- local/cloud/experimental runtime positioning;
- benchmark reports and interpretation guidance.

Primary reference:

- `legacy/docs/phases/phase-7-model-comparison.md`

### Phase 8 - Evals

Purpose:

- make quality regression visible and persistent.

Completed work:

- local SQLite eval store;
- tracked eval workspace under `evals/`;
- Phase 5 fixtures and gold sets for extraction, summary, checklist, code
  analysis, CV samples, and evidence CV;
- Phase 8 benchmark/eval configs and workflow cases;
- smoke eval/checklist regression persistence;
- historical eval import/backfill;
- eval reporting and diagnosis;
- evidence CV gold-set integration;
- routing and guardrail evals;
- live eval runner;
- consolidated runner with preflight, `--index-missing`, and batch execution;
- product runtime evals for contract, grounding, and actionability dimensions;
- backfill from persisted telemetry into runtime eval records.

Primary references:

- `legacy/docs/phases/eval-foundation.md`
- `docs/architecture/evals/operating-rhythm.md`

### Phase 8.5 - Runtime, Retrieval, and Adaptation Decision Support

Purpose:

- decide whether to improve quality through runtime changes, retrieval changes,
  embeddings/rerankers, OCR/VLM paths, or adaptation.

Completed work:

- runtime-family normalization;
- benchmark-matrix execution;
- benchmark closure reports;
- decision gates;
- embedding baseline and challengers;
- reranking tradeoff analysis;
- OCR/VLM fallback matrix planning and evidence;
- adaptation decision criteria;
- explicit stance that fine-tuning/adaptation should follow eval evidence, not fashion.

Primary references:

- `docs/architecture/evals/decision-gate.md`
- `docs/architecture/evals/closure.md`
- `docs/architecture/evals/expanded-completion-roadmap.md`
- `docs/architecture/evals/benchmark-execution.md`

### Phase 9 - Observability

Purpose:

- make system behavior understandable during real execution.

Completed work:

- runtime snapshots;
- provider/model visibility;
- effective context-window display;
- retrieval diagnostics;
- workflow metadata;
- error and latency surfaces;
- execution history;
- product telemetry;
- runtime execution logs;
- product workflow history;
- chat/lab state persistence;
- runtime/provider information in UI surfaces;
- observability hooks that later fed AI Lab panels.

### Phase 9.25 - Runtime Economics and Provider Diagnostics

Purpose:

- expose cost, usage, latency, fallback pressure, and provider readiness.

Completed work:

- runtime economics foundation;
- usage observability;
- budget-aware-routing principles;
- provider diagnostics;
- hot credential updates through Preferences/Keychain;
- hosted Ollama credential refresh per request;
- model alias canonicalization;
- Hugging Face Inference resilience with embedding fallback;
- Runtime Controls and Preferences contract normalization;
- local diagnostics toolkit with redaction and stable fingerprints.

Primary reference:

- `legacy/docs/phases/runtime-economics-and-evidenceops-foundation.md`

### Phase 9.5 - EvidenceOps and Operational Integrations

Purpose:

- connect document intelligence to operational systems and governance.

Completed work:

- EvidenceOps/MCP-style console;
- local MCP server/client foundation using JSON-RPC stdio;
- repository/worklog/action store foundations;
- Nextcloud/WebDAV selected as external document repository target;
- Trello selected for action/worklog handoff;
- Notion selected for evidence register / executive handoff;
- backlog governance panels;
- actions by owner/status/due date;
- claim/close actions;
- EvidenceOps UI cache behavior;
- worklog/action backfill from persisted telemetry;
- external readiness matrix for Nextcloud, Trello, and Notion;
- demo corpus mapping.

Primary references:

- `legacy/docs/phases/local-evidenceops-mcp-server.md`
- `docs/architecture/evidenceops/vertical-slice.md`
- `docs/architecture/evidenceops/external-target-architecture.md`
- `docs/architecture/evidenceops/demo-corpus-mapping.md`

### Phase 10 - Professional Engineering Hardening

Purpose:

- make the codebase defensible as engineering work, not only as a demo.

Completed work:

- targeted Python tests;
- frontend Vitest coverage;
- frontend build validation;
- readiness scripts;
- smoke scripts;
- better logging and error handling;
- script catalog;
- test status documentation;
- distinction between current green gate and legacy/live/provider-heavy tests;
- deployment readiness checks;
- repository cleanup constraints.

Current references:

- `tests/README.md`
- `scripts/README.md`
- `scripts/run_current_test_gate.sh`
- `scripts/readiness_multi_environment_contract_check.sh`

### Phase 10.25 - Product/Lab Split: Streamlit to Gradio to React Web App

Purpose:

- split the product-facing workflow surface from the engineering-facing AI Lab;
- evolve the UI from prototype to product.

Major decisions:

- Streamlit became AI Lab / engineering dashboard context.
- Gradio was used as an intermediate product surface for the main workflows.
- React/Vite became the current product surface.
- `product-api` became the backend contract for the frontend.
- `cv_analysis` became an internal engine behind Candidate Review rather than the public product identity.
- Executive Deck Generation became a product capability, not a cosmetic export.

#### Phase 10.25A-10.25D - AI Lab Positioning and Modularization

Completed work:

- classified the UI between Business Workflows and AI Lab;
- adapted Streamlit toward AI Lab dashboard responsibilities;
- defined navigation such as Lab Overview, Benchmarks, Evals, Runtime, Workflow Inspector, MCP/EvidenceOps, and Advanced;
- modularized AI Lab panels;
- validated the split between product and lab.

#### Phase 10.25E-10.25U - AI Lab Operating Console

Completed work:

- shell, onboarding, and technical narrative;
- runtime and observability panels;
- evals and regression-control panels;
- runtime, retrieval, and document-intelligence panels;
- workflow, guardrail, and agent inspection;
- benchmark decision layer;
- artifact registry;
- MCP/EvidenceOps operations;
- visual analytics for runtime, evals, benchmarks, and operations;
- summary-first hierarchy and drilldown discipline;
- visual consistency improvements.

#### Document Library Real Data Track

Completed work:

- replaced mocks with `GET /api/product/documents`;
- enriched document fields;
- added product-grade document-library contract;
- exposed real document stats, chunks, indexed state, loader labels, warnings, and operational status.

#### Runtime Controls Track

Completed work:

- read-only runtime contract;
- active provider/model/profile visibility;
- real runtime-control persistence;
- safe profile behavior;
- frontend/backend contract alignment.

#### Preferences Track

Completed work:

- aggregate Preferences contract;
- workspace preferences;
- runtime profiles;
- provider connection metadata;
- credential policy;
- test-connection behavior;
- safe secret signaling without exposing raw secrets.

#### Executive Deck Generation Track

Completed work:

- `presentation_export_service` integration;
- HTTP integration with `ppt_creator_app`;
- config for base URL, timeout, and artifact strategy;
- deck contracts for Document Review, Policy Comparison, Action Plan, Candidate Review, Benchmark/Eval, and Evidence Pack;
- artifact lifecycle;
- routing and deck-type selection;
- quality/grounding/security policies;
- security and PII guidance;
- renderer payload mapping;
- slide recipes by deck type;
- UX specification;
- user journeys;
- rollout and governance notes;
- failure modes and fallback strategy;
- observability model for exports;
- Deck Center integration;
- workflow-level deck generation.

Primary references:

- `docs/architecture/executive-deck-generation/README.md`
- `docs/architecture/executive-deck-generation/product-capability.md`
- `docs/architecture/executive-deck-generation/productization.md`
- `docs/architecture/executive-deck-generation/official-catalog-of-deck-types-and-contracts.md`

#### Phase 10.25AJ-10.25AV - Current React Product Surfaces

Completed work:

- Action Plan / Evidence Review live workspace;
- isolated Action Plan validation harness;
- AI Lab live endpoints and validation harness;
- validation E2E scripts for AI Lab, user simulation, frontend smoke, Action Plan,
  and Candidate Review;
- Workflow Catalog, Run History, Deck Center, artifact detail, and Command Center expansions;
- frontend surface validation with payloads, screenshots, DOM, traces, logs, and summary artifacts;
- Candidate Review live workspace;
- role-brief context for Candidate Review;
- Candidate Review presenter with strengths, gaps, watchouts, seniority signals, and next steps;
- Keystone branding, guided shell, navigation, and workbench tour;
- command palette, runtime drawer, app sidebar/topbar, and shared layout shell;
- landing narrative with workflow, artifact, AI Lab, grounding, and final CTA sections;
- Document Library read-only/public-demo behavior;
- batch Nextcloud import with deduplication and lineage;
- Run History rehydration into workflows;
- guided document selection for demo workflows;
- AI Lab grounded chat with session lifecycle and operational diagnostics;
- AI Lab dashboards for benchmarks, evals, artifacts, and workflow health;
- preindexed public corpus fast-import path for demo use.

Current product references:

- `docs/product/overview.md`
- `docs/product/two-track-positioning.md`
- `docs/architecture/current-product-surface.md`
- `docs/operations/preindexed-nextcloud-import.md`

Open item retained from 10.25:

- final operational end-to-end validation of the preindexed Nextcloud fast-import path with the prepared corpus.

### Phase 10.5 - Deployment Strategy Change

Original plan:

- Oracle Always Free app;
- Cloudflare Tunnel;
- local Mac Ollama bridge;
- public frontend/backend calling local inference through a secured bridge.

Current interpretation:

- this plan is valuable as architecture thinking but is no longer the maintained path;
- the current cloud target is AWS;
- local Docker validates the full local product stack;
- Oracle-like material is preserved as legacy/deferred operational history.

Why the change matters:

- AWS is easier to explain and reproduce;
- local Docker and AWS now have explicit contracts;
- the product no longer depends on a public cloud app calling a private laptop bridge;
- Ollama is handled as a sidecar/deploy dependency where enabled.

### Phase 11 - Final Publication Package and Public Narrative

Purpose:

- turn the project into a polished public artifact.

Completed or partly completed:

- stronger README narrative;
- short validation guide;
- documentation index;
- product overview;
- current product surface map;
- script README;
- test README;
- deployment docs;
- current run/validation path;
- repository cleanup that separates current product, docs, legacy material, runtime, scripts, and tests.

Still open:

- final screenshots;
- GIF or short video;
- final architecture diagram;
- final public demo script;
- final release notes;
- release tag such as `v1.0.0`;
- concise public product and architecture narrative.

Primary current references:

- `README.md`
- `docs/README.md`
- `docs/product/overview.md`

### Phase 12 - Production-readiness Baseline, Provider Strategy, and Frontend Parity

Purpose:

- make Docker/cloud deployment run the real backend over real state, not a fake demo payload.

This phase corresponds to the production-readiness runbook work that happened
after the original product roadmap. It fills the historical gap between the old
Phase 11 publication plan and the later Phase 13 deployment work.

Core rule:

```text
Golden Surface Snapshot = parity ruler
Functional Baseline State = real state mounted into Docker/deploy
```

Completed work:

- repository inventory;
- frontend surface provenance map;
- Golden Surface Snapshot;
- Golden Surface Summary;
- functional baseline state documentation;
- data payload documentation for baseline/runtime/artifacts/users boundaries;
- sanitized functional baseline builder;
- sanitized baseline validation;
- backend baseline smoke;
- frontend parity matrix;
- Docker backend over real baseline;
- workflow parity against real documents/chunks;
- provider strategy with env/secret separation;
- redacted provider/env readiness checks;
- Docker frontend route parity;
- Docker action/deep-click parity notes;
- frontend route-link audit;
- evidence that the frontend reads through Product API rather than mounting data directly.

Important surfaces mapped:

- Command Center
- Document Library
- Workflow Catalog
- Document Review
- Policy Comparison
- Action Plan
- Candidate Review
- Deck Center
- Run History
- AI Lab Overview
- Runtime Observability
- AI Lab Chat
- Workflow Inspector
- Benchmarks
- Evals
- Lab Artifacts
- EvidenceOps
- Runtime Controls
- Preferences

Key design rule:

- if a page shows documents, runs, artifacts, evals, benchmarks, or EvidenceOps state, the baseline must preserve the real backing objects;
- new public/user activity writes to overlay, not to the read-only baseline;
- secrets are injected through env/secret references, not committed into the baseline.

Primary references:

- `docs/architecture/REPOSITORY_INVENTORY.md`
- `docs/architecture/FRONTEND_SURFACE_PROVENANCE.md`
- `docs/architecture/GOLDEN_SURFACE_SNAPSHOT.md`
- `docs/architecture/GOLDEN_SURFACE_SUMMARY.md`
- `docs/architecture/FUNCTIONAL_BASELINE_STATE.md`
- `docs/architecture/data-payload.md`
- `docs/architecture/SANITIZED_FUNCTIONAL_BASELINE.md`
- `docs/architecture/SANITIZED_FUNCTIONAL_BASELINE_VALIDATION.md`
- `docs/architecture/BACKEND_BASELINE_SMOKE.md`
- `docs/architecture/frontend-parity/matrix.md`
- `docs/architecture/frontend-parity/route-link-audit.md`

### Phase 13 - Deployment, Public/Admin Policy, and Cloud Hardening

Purpose:

- move from product readiness to deployable operation.

#### Phase 13 - Oracle-like Docker

Completed work:

- Oracle-like Docker topology;
- separated data roots for baseline, runtime, artifacts, and users;
- deploy bundle builder;
- data-root preparation;
- compose smoke checks;
- final Oracle-like readiness gate;
- bundle safety rules around env files, secrets, and heavy runtime data.

Current status:

- Oracle-like deployment material is now legacy/deferred.
- The engineering decisions remain useful history.
- AWS replaced Oracle-like as the active cloud target.

Primary references:

- `legacy/docs/deployment/oracle/`
- `legacy/scripts/oracle/`

#### Phase 13.1 - Public/Admin Sessions and Overlay Policy

Completed work:

- public session identity;
- admin login foundation;
- public user writes routed to session overlay;
- admin writes allowed to global state;
- public workflow runs routed to overlay;
- public reruns routed to overlay;
- public Nextcloud imports routed or gated according to policy;
- public deck exports routed to overlay;
- artifact reads merge global baseline with session overlay;
- document reads merge global baseline with session overlay;
- Trello/Notion publish blocked for public users;
- Trello/Notion preview allowed when safe;
- admin-only cards/CTAs for protected operations.

Model:

```text
visible_state(user) = functional_baseline_readonly + user_overlay
```

Relevant checks:

- `scripts/readiness_public_admin_policy_check.sh`
- `scripts/readiness_admin_session_isolation_check.sh`
- `scripts/readiness_public_ai_lab_overlay_check.sh`

#### Phase 13.2 - Public Exposure Hardening

Completed work captured in legacy Oracle hardening:

- public session retention and cleanup;
- storage quota policy;
- backup/restore scripts;
- HTTPS/reverse-proxy/firewall posture;
- health ops report;
- consolidated hardening gate.

Current status:

- Oracle-specific pieces are legacy/deferred.
- Public/admin safety concepts remain current.

Primary reference:

- `legacy/docs/deployment/oracle/oracle-hardening-handoff.md`

#### Phase 13.3 - Sidecar and Integration Readiness

Completed / preserved work:

- Oracle sidecar readiness;
- sidecar smoke checks;
- product-api, frontend, ppt-creator, Ollama, and Nextcloud topology validation;
- EvidenceOps integration readiness;
- external integration contract checks.

Current status:

- Oracle-specific scripts moved to legacy;
- equivalent current active contracts are represented by local Docker and AWS docs/scripts.

#### Phase 13.4 - AWS Convergence

Purpose:

- adapt the deploy story to the actual current cloud target.

Completed work:

- `.env.aws.example`;
- AWS Product API Dockerfile;
- AWS compose file;
- single-compose AWS contract;
- AWS fresh EC2 bootstrap runbook;
- AWS fast redeploy path;
- AWS cost/resource audit;
- AWS smoke script;
- AWS env contract validation;
- current deployment bundle builder;
- explicit rule that AWS uses `docker-compose.aws.yml` alone;
- removal of the old AWS local-plus-override contract;
- deploy-only Ollama embedding model pre-pull (`embeddinggemma:300m`) without overriding Runtime Controls.

Current references:

- `docs/deployment/aws-deploy.md`
- `docs/deployment/AWS_FRESH_EC2_BOOTSTRAP.md`
- `docs/deployment/REDEPLOY_FAST_PATH.md`
- `docs/deployment/aws-cost-audit.md`
- `docs/deployment/MULTI_ENVIRONMENT_CONTRACT.md`
- `scripts/deploy_aws.sh`
- `scripts/smoke_aws.sh`
- `scripts/validate_aws_env_contract.py`

### Phase 14 - Final Validation and Repository Presentation

Purpose:

- make the repository understandable, navigable, and operationally coherent without risking product behavior.

Completed work:

- moved historical phase docs to `legacy/docs/phases`;
- moved Oracle-only deployment docs/scripts to legacy;
- documented current product surface;
- documented current deployment modes;
- curated script catalog;
- documented tests and current green gate;
- added short validation guide;
- organized docs indexes;
- moved historical frontend demo / Streamlit Docker material to legacy;
- moved heavy/historical requirements to `legacy/requirements`;
- unified current product dependencies in root `requirements.txt`;
- documented Python dependency contract;
- documented local Docker and AWS entrypoints;
- added multi-environment readiness guard;
- documented Nextcloud golden baseline restore;
- documented AI Lab golden state restore;
- documented backup and restore operations;
- documented local backup register;
- removed stale public-demo naming from current deployment path;
- clarified that generated/local runtime artifacts should stay local unless explicitly curated.

Current open work:

- final screenshots/media;
- public architecture diagram;
- final release tag;
- optional public domain/HTTPS decision for demo;
- final proof that preindexed Nextcloud fast import works end to end with the prepared corpus.

---

## 5. Current Integrations and Their Status

### Ollama

Status:

- supported as local/model-provider sidecar where enabled;
- deploy scripts can pre-pull `embeddinggemma:300m`;
- pre-pull is deploy-only and does not override app Runtime Controls;
- Runtime Controls remain the product-level source for active provider/model selection.

### Nextcloud / WebDAV

Status:

- used as the external document repository path;
- supports listing/import when credentials and root path are configured;
- has golden-baseline restore documentation;
- supports batch import and preindexed public-corpus fast path;
- public/admin behavior is governed by overlay/admin policy.

Open:

- final operational validation of preindexed fast import with the prepared corpus.

### Trello

Status:

- used for operational/action handoff;
- preview and publish flows exist;
- real publish requires configured credentials;
- public users are blocked from unsafe publish actions.

### Notion

Status:

- used for evidence register / executive handoff;
- preview and publish flows exist;
- real publish requires configured credentials and database access;
- public users are blocked from unsafe publish actions.

### PPT Creator

Status:

- external rendering sidecar for Executive Deck Generation;
- AI Decision Studio owns intelligence, grounding, contracts, and workflow orchestration;
- `ppt_creator_app` owns rendering, packaging, previews, and `.pptx` artifacts.

### Backup and Restore

Status:

- backup and restore operations are documented as part of the deployment and
  operations layer;
- local backup register keeps local operational snapshots traceable without
  committing private payloads;
- Oracle-specific backup/restore scripts are retained under legacy deployment
  material.

---

## 6. Current Validation Contract

Current green gate:

```bash
npm --prefix frontend run test
npm --prefix frontend run build
scripts/run_current_test_gate.sh
scripts/readiness_multi_environment_contract_check.sh
```

Important interpretation:

- the full historical Python discovery suite is not the canonical validation gate;
- it contains legacy, live-provider, integration, and eval-history tests;
- the current green gate is documented in `tests/README.md`;
- deployment contracts are protected by readiness scripts.

Additional focused checks exist for:

- admin/session isolation;
- public/admin policy;
- AI Lab content;
- AI Lab golden state;
- Nextcloud golden baseline;
- required integrations;
- required providers;
- run history compactness;
- artifact compactness;
- Candidate Review contract;
- Preferences/Evals surface;
- EvidenceOps UI cache;
- Trello public visibility;
- AWS env contract.

---

## 7. Technical Capabilities Demonstrated

The repository demonstrates:

- LLM application foundations;
- modular architecture;
- RAG implementation and retrieval evaluation;
- structured outputs with schema and repair discipline;
- evidence-grounded CV parsing;
- bounded LangChain/LangGraph adoption;
- agent/tool orchestration with guardrails;
- benchmark and eval infrastructure;
- runtime observability;
- runtime economics and provider diagnostics;
- external integration design;
- React frontend/product API separation;
- public/admin access policy;
- overlay-based demo safety;
- deck/artifact generation through a dedicated rendering sidecar;
- Docker and AWS deployment discipline;
- repository cleanup and operational documentation.

---

## 8. Remaining Work

The remaining work is presentation and final proof, not a product rewrite.

Open:

- validate preindexed Nextcloud fast import end to end with the prepared corpus;
- capture current screenshots of the React product, AI Lab, Deck Center, Run History, Runtime Controls, Preferences, and deployment;
- produce a short GIF/video of the main product flow;
- add a final architecture diagram;
- write a final public demo script;
- decide whether current public demo needs domain/HTTPS or whether AWS IP/local Docker evidence is enough;
- create a final release tag;
- keep docs synchronized if any deployment contract changes.

Deferred:

- Oracle + Cloudflare Tunnel + local Ollama bridge;
- Oracle Always Free public exposure as the primary path;
- full production-grade multi-user auth beyond the current controlled public/admin demo model;
- large-scale provider fine-tuning unless eval evidence justifies it.

---

## 9. Recommended Reading Order

Recommended:

1. `README.md`
2. `ROADMAP.md`
3. `docs/product/overview.md`
4. `docs/architecture/current-product-surface.md`
5. `docs/deployment/MULTI_ENVIRONMENT_CONTRACT.md`
6. `scripts/README.md`
7. `tests/README.md`
8. phase references under `legacy/docs/phases/` only when deeper history is needed

---

## 10. Executive Summary

AI Decision Studio evolved through a coherent engineering arc:

1. local LLM foundations;
2. modular provider/runtime architecture;
3. document-grounded RAG;
4. retrieval validation and fallback hardening;
5. structured outputs and evidence-grounded extraction;
6. controlled LangChain/LangGraph orchestration;
7. document operations workflows;
8. model comparison, evals, and observability;
9. runtime economics and provider diagnostics;
10. EvidenceOps and external integrations;
11. product/lab UI split;
12. React product surface backed by Product API;
13. deck/artifact generation;
14. production-readiness baseline and public/admin overlay policy;
15. local Docker and AWS deployment;
16. repository organization for long-term maintainability.

The next milestone is final publication polish: screenshots, architecture diagram,
demo narrative, release tag, and one final preindexed Nextcloud fast-import proof.
