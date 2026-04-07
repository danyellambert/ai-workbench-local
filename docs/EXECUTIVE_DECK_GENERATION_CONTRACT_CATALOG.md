# Executive Deck Generation — official catalog of deck types and contracts

## Objective

Formalize the official catalog of the **Executive Deck Generation** capability.

This document answers:

- which deck types officially exist
- which `export_kind` each one uses
- which priority each one has
- which project sources feed each deck
- what the documentation/implementation status of each contract is

---

## Conventions

### Official catalog fields

- `deck_family`
- `product_name`
- `export_kind`
- `priority`
- `source_flows`
- `target_audience`
- `status`
- `contract_doc`

### Possible statuses

- `foundation_exists`
- `planned`
- `contract_defined`
- `implemented`
- `implemented_foundation`

---

## Official catalog

| deck_family | product_name | export_kind | priority | source_flows | target_audience | status | contract_doc |
|---|---|---|---|---|---|---|---|
| executive_review | Benchmark & Eval Executive Review Deck | `benchmark_eval_executive_review` | P1 | benchmark, evals, readiness | technical leadership, product, executive stakeholder | implemented | `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md` |
| document_review | Document Review Deck | `document_review_deck` | P2 | summary, extraction, document agent, EvidenceOps | compliance, operations, leadership | implemented_foundation | `docs/EXECUTIVE_DECK_GENERATION_DOCUMENT_REVIEW_DECK_CONTRACT_V1.md` |
| comparison | Policy / Contract Comparison Deck | `policy_contract_comparison_deck` | P2 | comparison findings, structured outputs, document agent | legal, compliance, procurement | implemented_foundation | `docs/EXECUTIVE_DECK_GENERATION_POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1.md` |
| action_plan | Action Plan Deck | `action_plan_deck` | P3 | checklist, findings, owners, due dates | operations, PM, compliance | implemented_foundation | `docs/EXECUTIVE_DECK_GENERATION_ACTION_PLAN_DECK_CONTRACT_V1.md` |
| candidate_review | Candidate Review Deck | `candidate_review_deck` | P3 | `cv_analysis`, evidence_cv, candidate comparison | talent review, hiring panel | implemented_foundation | `docs/EXECUTIVE_DECK_GENERATION_CANDIDATE_REVIEW_DECK_CONTRACT_V1.md` |
| evidence_audit | Evidence Pack / Audit Deck | `evidence_pack_deck` | P3 | EvidenceOps, repository state, action backlog | audit, governance, leadership | implemented_foundation | `docs/EXECUTIVE_DECK_GENERATION_EVIDENCE_PACK_DECK_CONTRACT_V1.md` |

---

## Note on P1 legacy naming

The currently implemented code uses the foundation:

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

This naming continues to be accepted as the **existing technical base of P1**.

Current code status:

- the service accepts the product alias `benchmark_eval_executive_review`
- the internal implementation remains compatible with the legacy naming `benchmark_eval_executive_deck`

Recommended long-term direction:

- the capability/catalog use the product naming above
- the implementation may keep compatibility with the legacy naming until an explicit migration occurs

---

## Criteria to promote a deck type from `planned` to `contract_defined`

A deck type should only be treated as truly ready for implementation when there is:

1. a clear product objective
2. `export_kind` definido
3. explicit input sources
4. a documented v1 JSON contract
5. an initial documented slide recipe
6. minimum quality/review criteria

## Current real implementation state

The codebase already contains:

- multi-deck builders in `src/services/presentation_export.py`
- a generic service in `src/services/presentation_export_service.py`
- Streamlit UI with deck-type selection in `src/ui/executive_deck_generation.py`
- builder/adapter unit tests in `tests/test_presentation_export_unittest.py`

Recommended interpretation of the statuses:

- `implemented` = a deck type whose main flow is already consolidated in the current product
- `implemented_foundation` = a deck type already present in code, UI, and unit tests, but still needing smoke tests/operational hardening before being treated as fully closed

---

## Recommended order for closing the catalog

### Now
- `benchmark_eval_executive_review`

### Next
- `document_review_deck`
- `policy_contract_comparison_deck`

### Later
- `action_plan_deck`
- `candidate_review_deck`
- `evidence_pack_deck`
