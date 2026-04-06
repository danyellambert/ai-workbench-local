# Roadmap

This is the canonical roadmap for the repository.

It organizes the project in chronological order and separates the documentation into:

- completed phases
- active phases
- bounded later-phase references
- planned future phases

The goal is to make the repository easy to understand as the evolution of a local-first AI system into a broader applied-AI platform for document-grounded workflows, structured execution, evaluation, and operational tooling.

---

## 1. How to read this roadmap

Recommended reading order:

1. review the current workstreams
2. inspect the phase status table
3. read the completed phases in order
4. use the linked phase documents for deeper technical detail

Primary documentation index:

- `docs/DOCUMENTATION_INDEX.md`

---

## 2. Current workstreams

These workstreams are narrower than the full roadmap and describe focused implementation slices currently being hardened.

### 2.1 External presentation renderer, host-native first

Goal:

- consolidate `ppt_creator_app` as the external HTTP renderer for executive deck generation
- keep host-native execution as the preferred operating mode for the current slice
- treat Docker as a later hardening step rather than a present blocker

Current state:

- presentation export already points to `http://127.0.0.1:8787`
- the local helper flow is already documented
- the sibling renderer is already prepared for service-first Docker later
- final manual smoke validation is still pending

### 2.2 Multi-provider sidebar and operational clarity

Goal:

- align provider behavior more clearly across `ollama`, `huggingface_server`, and related paths
- make embedding-provider availability explicit in the UI
- separate generation, embeddings, retrieval, reranking, OCR, and VLM controls more clearly

Current state:

- operational overrides are already more consistent
- embedding availability rules are already surfaced in the UI
- reranking, OCR, and VLM controls are already exposed
- focused validation and documentation updates were already completed for this slice

---

## 3. Phase status overview

| Phase | Status | Canonical document | Main outcome |
| --- | --- | --- | --- |
| 0 | Completed | `docs/PHASE_0_PUBLICATION_AND_POSITIONING.md` | Safe publication baseline |
| 0.5 | Completed | `docs/PHASE_0_5_REPOSITORY_GOVERNANCE.md` | Repository governance and publication discipline |
| 1 | Completed | `docs/PHASE_1_PRODUCT_FOUNDATION.md` | Usable local product baseline |
| 2 | Completed | `docs/PHASE_2_MODULAR_ARCHITECTURE.md` | Clearer modular architecture |
| 3 | Completed | `docs/PHASE_3_MULTI_PROVIDER_FOUNDATION.md` | Multi-provider and prompt-profile foundation |
| 4 | Completed | `docs/PHASE_4_DOCUMENT_RAG_FOUNDATION.md` | First document-grounded RAG flow |
| 4.5 | Completed | `docs/PHASE_4_5_VALIDATION.md` | Benchmarked and validated RAG |
| 5 | Completed | `docs/PHASE_5_SUMMARY.md` | Structured outputs and evidence-grounded CV workflows |
| 5.5 | Completed | `docs/PHASE_5_5_FRAMEWORK_EVOLUTION.md` | Controlled LangChain and LangGraph evolution |
| 6 | Completed | `docs/PHASE_6_DOCUMENT_OPERATIONS_COPILOT.md` | Workflow-oriented document copilot |
| 7 | Completed | `docs/PHASE_7_MODEL_COMPARISON.md` | Repeatable model comparison layer |
| 8 | Active | `docs/PHASE_8_EVAL_FOUNDATION.md` | Persistent local evaluation foundation |
| 8.5 | Bounded reference | `docs/PHASE_8_5_CLOSURE.md` | Runtime, retrieval, and adaptation decision support |
| 9 | Bounded reference | later technical references | System observability and runtime visibility |
| 9.25 | Bounded reference | `docs/PHASE_9_25_RUNTIME_ECONOMICS_AND_EVIDENCEOPS_LOCAL.md` | Runtime economics and budget-aware routing |
| 9.5 | Bounded reference | `docs/PHASE_9_5_EVIDENCEOPS_MCP_LOCAL_SERVER.md` | MCP and operational integration foundation |
| 10 | Bounded reference | `docs/PHASE_10_ENGINEERING_PROFESSIONAL.md` | Engineering hardening |
| 10.25 | Bounded reference | `docs/PHASE_10_25_PRODUCT_SPLIT_GRADIO_AI_LAB.md` | Product/lab surface split |
| 10.5 | Planned | future bounded reference | Hybrid deployment |
| 11 | Planned | future bounded reference | Final publication package |

---

## 4. Strategic reading of the repository

The repository is intentionally structured around two connected layers.

### 4.1 Business workflows

This is the product-facing reading of the system.

Core workflow family:

- Document Review
- Policy / Contract Comparison
- Action Plan / Evidence Review
- Candidate Review
- Executive Deck Generation as a transversal capability

### 4.2 AI engineering lab

This is the engineering-facing reading of the system.

Core engineering areas:

- model comparison
- evaluation and diagnosis
- routing and guardrails
- runtime economics
- observability
- controlled architecture experiments
- MCP and operational tooling

Reference:

- `docs/PROJECT_POSITIONING_TWO_TRACKS.md`

---

## 5. Phase-by-phase chronology

### Phase 0 — Publication and positioning

**Status:** Completed

Goal:

- make the repository safe to publish
- establish an initial external framing for the project
- remove obvious publication risks such as unsafe defaults and secret leakage

Primary document:

- `docs/PHASE_0_PUBLICATION_AND_POSITIONING.md`

### Phase 0.5 — Repository governance

**Status:** Completed

Goal:

- add lightweight governance and repository discipline
- create clearer publication rules before broader expansion

Primary document:

- `docs/PHASE_0_5_REPOSITORY_GOVERNANCE.md`

### Phase 1 — Product foundation

**Status:** Completed

Goal:

- turn the original local application into a more usable product baseline
- improve streaming, settings, error handling, and interaction quality

Primary document:

- `docs/PHASE_1_PRODUCT_FOUNDATION.md`

### Phase 2 — Modular architecture

**Status:** Completed

Goal:

- move away from a single-file application structure
- separate UI, providers, services, storage, and shared configuration

Primary document:

- `docs/PHASE_2_MODULAR_ARCHITECTURE.md`

### Phase 3 — Multi-provider foundation

**Status:** Completed

Goal:

- support multiple providers and model families
- make prompt profiles reusable and explicit
- prepare the project for comparison rather than a single fixed runtime path

Primary document:

- `docs/PHASE_3_MULTI_PROVIDER_FOUNDATION.md`

### Phase 4 — Document-grounded RAG foundation

**Status:** Completed

Goal:

- add ingestion, chunking, embeddings, retrieval, and grounded answers over documents

Primary document:

- `docs/PHASE_4_DOCUMENT_RAG_FOUNDATION.md`

### Phase 4.5 — RAG validation and hardening

**Status:** Completed

Goal:

- validate retrieval quality through benchmarks
- improve vector-store persistence and operational clarity
- tune chunking, retrieval, reranking, PDF extraction, and embedding settings

Primary documents:

- `docs/PHASE_4_5_VALIDATION.md`
- `docs/PHASE_4_5_BENCHMARK_RESULTS.md`

### Phase 5 — Structured outputs and evidence-grounded CV workflows

**Status:** Completed

Goal:

- move beyond free-form chat into validated structured tasks
- support extraction, summary, checklist, CV analysis, and evidence-oriented parsing paths

Primary documents:

- `docs/PHASE_5_SUMMARY.md`
- `docs/EVIDENCE_CV_PIPELINE.md`
- `docs/PHASE_5_EVIDENCE_PACK.md`

### Phase 5.5 — Framework evolution

**Status:** Completed

Goal:

- make the move from manual foundations to framework-assisted workflows explicit
- add LangChain and LangGraph in bounded, auditable ways

Primary document:

- `docs/PHASE_5_5_FRAMEWORK_EVOLUTION.md`

### Phase 6 — Document Operations Copilot

**Status:** Completed

Goal:

- turn isolated structured tasks into a workflow-oriented document copilot
- add routing, tool selection, guardrails, and auditable execution

Primary document:

- `docs/PHASE_6_DOCUMENT_OPERATIONS_COPILOT.md`

### Phase 7 — Model comparison and benchmarking

**Status:** Completed

Goal:

- compare providers and models under repeatable prompts and workflow presets
- persist results and aggregate them into reusable benchmark views

Primary document:

- `docs/PHASE_7_MODEL_COMPARISON.md`

---

## 6. Active and bounded later-phase references

### Phase 8 — Evaluation foundation

**Status:** Active

Current focus:

- keep a local eval store in SQLite
- accumulate quality signals over time
- support reporting, diagnosis, and live/local evaluation routines

Primary document:

- `docs/PHASE_8_EVAL_FOUNDATION.md`

Related document:

- `docs/PHASE_8_EVAL_OPERATING_RHYTHM.md`

### Phase 8.5 — Runtime, retrieval, and adaptation decision support

**Status:** Bounded reference

Current focus:

- use benchmark and eval evidence to decide whether the next gain should come from:
  - provider or runtime changes
  - retrieval changes
  - embeddings or rerankers
  - narrowly scoped adaptation

Primary references:

- `docs/PHASE_8_5_DECISION_GATE.md`
- `docs/PHASE_8_5_CLOSURE.md`
- `docs/PHASE_8_5_EXPANDED_COMPLETION_ROADMAP.md`

### Phase 9 — Observability

**Status:** Bounded reference

Current focus:

- expose the system clearly enough to diagnose quality, latency, and routing behavior

### Phase 9.25 — Runtime economics and budget-aware routing

**Status:** Bounded reference

Current focus:

- measure cost, tokens, and operational pressure per execution
- introduce budget-aware routing without losing quality control

Primary document:

- `docs/PHASE_9_25_RUNTIME_ECONOMICS_AND_EVIDENCEOPS_LOCAL.md`

### Phase 9.5 — EvidenceOps MCP and operational integrations

**Status:** Bounded reference

Current focus:

- evolve the local EvidenceOps foundation into MCP-backed operational workflows
- support repository inspection, worklog handling, and action tracking

Primary references:

- `docs/PHASE_9_5_EVIDENCEOPS_MCP_LOCAL_SERVER.md`
- `docs/PHASE_9_5_EVIDENCEOPS_VERTICAL_SLICE.md`
- `docs/PHASE_9_5_EXTERNAL_TARGET_ARCHITECTURE.md`

### Phase 10 — Engineering hardening

**Status:** Bounded reference

Current focus:

- strengthen test coverage, smoke validation, error handling, logging, and maintainability

Primary document:

- `docs/PHASE_10_ENGINEERING_PROFESSIONAL.md`

### Phase 10.25 — Product/lab surface split and executive deck generation

**Status:** Bounded reference

Current focus:

- separate the product-facing and engineering-facing surfaces more clearly
- support executive deck generation as a reusable product capability

Primary references:

- `docs/PHASE_10_25_PRODUCT_SPLIT_GRADIO_AI_LAB.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`

### Phase 10.5 — Hybrid deployment

**Status:** Planned

Planned focus:

- support a demonstrable hybrid deployment path
- keep local-first runtime assumptions while enabling public-facing demos when appropriate

### Phase 11 — Final publication package

**Status:** Planned

Planned focus:

- finish publication polish, public-facing materials, and final repository packaging

---

## 7. Maturity narrative

The project progression is easiest to understand through six maturity steps:

1. manual local foundations
2. modular architecture and provider abstraction
3. document-grounded retrieval
4. validated structured execution
5. workflow orchestration and evaluation
6. operational visibility, economics, and integration

Each later phase builds on explicit evidence and infrastructure from the previous ones instead of adding isolated features.

---

## 8. Recommended reading order

1. `README.md`
2. `ROADMAP.md`
3. `docs/DOCUMENTATION_INDEX.md`
4. `docs/PROJECT_POSITIONING_TWO_TRACKS.md`
5. completed phase summaries from 0 to 7
6. active later-phase references as needed
7. `docs/plans/IMPLEMENTATION_PLAN.md` for forward-looking product-surface planning

---

## 9. Documentation conventions

- canonical entry documents live in the repository root and `docs/`
- forward-looking planning documents live under `docs/plans/`
- legacy transition files live under `old/docs/`
- runtime and operational state are moving toward `.runtime/` with compatibility fallbacks preserved
- generated artifacts remain under `artifacts/`

---

## 10. Summary

At this stage, the repository should be read as a local-first applied-AI workbench with two explicit surfaces:

- a product-facing workflow layer for document-grounded decisions
- an engineering-facing lab layer for benchmarking, evaluation, observability, and controlled system evolution

The canonical completed journey currently runs through Phases 0 to 7. Phase 8 and later already contain meaningful technical material in the repository, but they remain framed as active or bounded references until they are promoted through the same documented closure standard.
