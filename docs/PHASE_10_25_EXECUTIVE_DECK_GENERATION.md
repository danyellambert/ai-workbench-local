# Phase 10.25 — Executive Deck Generation as a product capability

## Objective

Clearly define the project's new direction: the current ecosystem will no longer have just an isolated **presentation export** feature, but a recurring **Executive Deck Generation** capability.

In practice, this means that AI Workbench Local can continuously generate **grounded executive decks** based on:

- documents
- structured outputs
- document comparisons
- benchmark/evals
- EvidenceOps and action plans

This capability should be understood as one of the ecosystem's internal products, not as a disconnected side project.

---

## Official thesis

> AI Workbench Local does not just converse with documents, extract information, and evaluate quality. It also delivers **recurring executive decks** for review, decision-making, operations, and stakeholder communication.

This is the strongest product framing because it brings the project closer to a real business use case:

1. documents and signals come in
2. AI analyzes, summarizes, compares, and structures
3. the system generates an executive artifact that can be used in the real workflow

---

## What this capability is

### What it is

Executive Deck Generation is the capability of transforming grounded AI Workbench outputs into recurring executive presentations.

### What it is not

It should **not** be positioned as:

- a generic slide generator with no context
- a separate product competing with AI Workbench
- a purely cosmetic export layer

The correct positioning is:

**grounded deck generation for business workflows**

In plain English:

**grounded executive deck generation based on documents, structured analysis, and operational decisions**

---

## Architectural boundary

### AI Workbench Local

It remains the source of truth for:

- document ingestion
- RAG
- structured outputs
- agents/workflows
- benchmark/evals
- EvidenceOps
- recommendation logic

### `ppt_creator_app`

It acts as the specialized layer for:

- presentation schema validation
- `.pptx` rendering
- visual preview/review
- artifact comparison
- final deck packaging

### Separation rule

**AI Workbench Local = intelligence, grounding, and orchestration**  
**`ppt_creator_app` = specialized executive rendering**

This separation is important because it demonstrates product and engineering maturity:

- the domain does not become coupled to the renderer
- the renderer does not need to know the deep business logic
- the capability can grow through a catalog of decks, not through specific hacks

---

## Deck families the product can generate continuously

The strongest way to think about this capability is in terms of **recurring deck families**.

## 1. Summary decks

Decks for executive synthesis of one or more documents.

Examples:

- executive summary deck
- leadership briefing deck
- monthly/weekly review deck

Typical inputs:

- long document
- document corpus
- structured summary

## 2. Review decks

Decks for reviewing documents, policies, contracts, or document sets.

Examples:

- document review deck
- compliance review deck
- risk review deck

Typical inputs:

- findings
- risks
- gaps
- recommended actions

## 3. Comparison decks

Decks for comparing versions, options, or candidates.

Examples:

- policy/contract comparison deck
- option comparison deck
- candidate comparison deck

Typical inputs:

- structured comparison
- document diff
- side-by-side scorecards

## 4. Decision decks

Decks whose main question is: **what should we do?**

Examples:

- decision memo deck
- recommendation deck
- model/runtime decision deck

Typical inputs:

- trade-offs
- recommendation
- watchouts
- quality gates

## 5. Action-plan decks

Operational decks focused on owners, timelines, priorities, and execution.

Examples:

- action plan deck
- remediation plan deck
- operational handoff deck

Typical inputs:

- checklist
- action items
- owners
- due dates

## 6. Evidence / audit decks

Decks for audit, compliance, evidence repositories, and executive reporting.

Examples:

- evidence pack deck
- audit review deck
- EvidenceOps operating review deck

Typical inputs:

- evidence packs
- findings
- repository state
- action backlog

## 7. Candidate / talent decks

People intelligence decks using the CV track and structured extraction.

Examples:

- candidate review deck
- candidate comparison deck
- hiring decision deck

Typical inputs:

- CV structured extraction
- comparison findings
- recommendation

---

## Recommended initial catalog for the capability

To keep the roadmap focused, the capability should start with an explicit catalog of priority types.

### P1 — Benchmark & Eval Executive Review Deck

The first deck to finalize because a structured foundation already exists and a contract is already underway.

Objective:

- translate benchmark/evals into an executive view
- show recommendation, watchouts, and next steps

### P2 — Document Review Deck

The first strongly enterprise-oriented deck.

Objective:

- summarize the document
- highlight risks/gaps
- organize recommendations

### P3 — Policy / Contract Comparison Deck

A natural extension of the document product.

Objective:

- show relevant differences
- highlight business impact
- support human decision/review

### P4 — Action Plan Deck

Objective:

- turn findings and checklists into an executable operational plan

### P5 — Candidate Review Deck

Objective:

- leverage the `cv_analysis` track to generate an executive candidate evaluation deck

### P6 — Evidence Pack / Audit Deck

Objective:

- turn EvidenceOps outputs into an executive audit/compliance handoff

---

## Realistic roadmap priority

### Now

1. **Benchmark & Eval Executive Review Deck**

### Next

2. **Document Review Deck**
3. **Policy / Contract Comparison Deck**

### Later

4. **Action Plan Deck**
5. **Candidate Review Deck**
6. **Evidence Pack / Audit Deck**

This order is the strongest because it moves from:

- more structured data that is easier to consolidate
- to richer enterprise use cases
- and then to more premium catalog families

---

## Capability contract model

The product should grow through a **catalog of contracts/versioning**, not through loose UI logic.

### Main concepts

- `contract_version`
- `export_kind`
- `deck_family`

### Target catalog for `export_kind`

Suggested official direction:

- `benchmark_eval_executive_review`
- `document_review_deck`
- `policy_contract_comparison_deck`
- `action_plan_deck`
- `candidate_review_deck`
- `evidence_pack_deck`

### Important note about the current state

Today, the first technical slice already implemented in the repository still uses the naming:

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

This should be understood as the **technical foundation already in place** for P1, not as the final naming of the capability as a whole.

---

## Current state of the repository

Today the project already has a concrete foundation for the first type of deck.

### Already in place

- technical contract for the benchmark/eval slice
- contract builder in AI Workbench
- adapter for a payload compatible with `ppt_creator`
- focused unit tests
- initial productization documentation for the first slice

Main files:

- `src/services/presentation_export.py`
- `tests/test_presentation_export_unittest.py`
- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`

### Still missing

- real HTTP service for the renderer
- explicit UX in the main app
- official catalog of `export_kind`s
- artifact lifecycle per export
- capability-specific observability
- expansion to families beyond benchmark/eval

---

## Capability roadmap

## Slice 0 — Foundation of the first deck

**Status: already started / partially delivered**

- benchmark/eval contract
- builder
- adapter
- foundation tests

## Slice 1 — First operational deck

Complete the **Benchmark & Eval Executive Review Deck** as the first usable capability in the product.

Deliverables:

- `presentation_export_service`
- HTTP call to `ppt_creator_app`
- local artifact persistence
- minimum UX in the current app

## Slice 2 — First enterprise document deck

Complete the **Document Review Deck**.

Deliverables:

- dedicated contract
- mapping of findings/risks/recommendations
- executive review deck

## Slice 3 — Comparison / decision layer

Complete the **Policy / Contract Comparison Deck** and prepare the foundation for **Decision Decks**.

## Slice 4 — Operational action layer

Complete the **Action Plan Deck**.

## Slice 5 — Talent / EvidenceOps expansion

Complete:

- Candidate Review Deck
- Evidence Pack / Audit Deck

## Slice 6 — UI and recurring product usage

Turn the capability into a real product surface:

- visible catalog of deck types
- flow-based triggering
- history of generated decks
- integration with Gradio / web app

---

## Expected product UX

In the UI, this should not appear as “use the PPT project.”

It should appear as an AI Workbench capability, for example:

- **Executive Deck Generation**
- **Generate executive deck**
- **Business review decks**

### What the UX should allow in the future

- choose the deck type
- review the grounded input
- generate the deck
- download `.pptx`
- download contract/payload
- view recent exports

---

## Why this strengthens the project as an AI product for business

Because the business does not want only:

- chat
- JSON
- raw technical analysis

The business wants:

- executive synthesis
- recommendation
- decision support
- action plan
- presentable handoff

Executive Deck Generation closes exactly that gap.

---

## Success criterion

This capability will be well defined when the roadmap makes clear:

1. which deck families exist
2. which are P1, P2, and P3
3. what the boundary is between AI Workbench and `ppt_creator_app`
4. how contracts grow through `export_kind`
5. how this becomes a recurring product surface rather than just an isolated export

---

## Related documents

- `ROADMAP.md`
- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENTATION_PLAN.md`
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG.md`
- `docs/EXECUTIVE_DECK_GENERATION_ROUTING.md`
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_VERSIONING.md`
- `docs/EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE.md`
- `docs/EXECUTIVE_DECK_GENERATION_API_CONTRACT.md`
- `docs/EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE.md`
- `docs/EXECUTIVE_DECK_GENERATION_SLIDE_RECIPES.md`
- `docs/EXECUTIVE_DECK_GENERATION_RENDERER_MAPPING.md`
- `docs/EXECUTIVE_DECK_GENERATION_BRANDING_POLICY.md`
- `docs/EXECUTIVE_DECK_GENERATION_FAILURE_MODES.md`
- `docs/EXECUTIVE_DECK_GENERATION_UX_SPEC.md`
- `docs/EXECUTIVE_DECK_GENERATION_UI_EVOLUTION.md`
- `docs/EXECUTIVE_DECK_GENERATION_USER_JOURNEYS.md`
- `docs/EXECUTIVE_DECK_GENERATION_TEST_STRATEGY.md`
- `docs/EXECUTIVE_DECK_GENERATION_QUALITY_AND_GOVERNANCE.md`
- `docs/EXECUTIVE_DECK_GENERATION_OBSERVABILITY.md`
- `docs/EXECUTIVE_DECK_GENERATION_SECURITY_AND_PII.md`
- `docs/EXECUTIVE_DECK_GENERATION_ROLLOUT_AND_GOVERNANCE.md`
- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENT_REVIEW_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_ACTION_PLAN_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_CANDIDATE_REVIEW_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_EVIDENCE_PACK_DECK_CONTRACT_V1.md`
