# Executive Deck Generation — complete documentation plan

## Objective

Consolidate **absolutely everything that needs to be documented** to fully implement the **Executive Deck Generation** capability in the AI Workbench Local ecosystem.

This document exists to answer, in operational terms, four questions:

1. what is already documented
2. what still needs to be documented
3. what is mandatory before implementing P1
4. what can be documented in parallel with the implementation of the next deck types

---

## Current status

### Already documented

#### Capability / product vision
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

#### Technical productization of the first slice
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`

#### Concrete P1 contract
- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`

#### Main roadmap
- `ROADMAP.md`

### Complementary documentation scope completed in this round

- official catalog of deck types and `export_kind`
- capability service architecture
- API contract between AI Workbench and `ppt_creator_app`
- artifact lifecycle
- minimum UX and UI progression
- test strategy
- quality, observability, security, and rollout policies
- supporting docs for routing, versioning, recipes, and mapping
- dedicated contracts for P2/P3/P4/P5/P6 still pending specific writing

---

## Complete documentation package for the capability

## 1. Capability / product

### 1.1 Capability map
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

### 1.2 Complete documentation plan
- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENTATION_PLAN.md`

### 1.3 Official catalog of deck types
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG.md`

### 1.4 Routing policy
- `docs/EXECUTIVE_DECK_GENERATION_ROUTING.md`

### 1.5 Contract versioning
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_VERSIONING.md`

---

## 2. Data contracts by deck type

### P1 — already started
- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`

### P2/P3/P4/P5/P6 — required for the full capability
- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENT_REVIEW_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_ACTION_PLAN_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_CANDIDATE_REVIEW_DECK_CONTRACT_V1.md`
- `docs/EXECUTIVE_DECK_GENERATION_EVIDENCE_PACK_DECK_CONTRACT_V1.md`

---

## 3. Architecture and integration

- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE.md`
- `docs/EXECUTIVE_DECK_GENERATION_API_CONTRACT.md`
- `docs/EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE.md`
- `docs/EXECUTIVE_DECK_GENERATION_RENDERER_MAPPING.md`
- `docs/EXECUTIVE_DECK_GENERATION_SLIDE_RECIPES.md`
- `docs/EXECUTIVE_DECK_GENERATION_BRANDING_POLICY.md`
- `docs/EXECUTIVE_DECK_GENERATION_FAILURE_MODES.md`

---

## 4. Product / UX

- `docs/EXECUTIVE_DECK_GENERATION_UX_SPEC.md`
- `docs/EXECUTIVE_DECK_GENERATION_UI_EVOLUTION.md`
- `docs/EXECUTIVE_DECK_GENERATION_USER_JOURNEYS.md`

---

## 5. Quality, testing, and governance

- `docs/EXECUTIVE_DECK_GENERATION_TEST_STRATEGY.md`
- `docs/EXECUTIVE_DECK_GENERATION_QUALITY_AND_GOVERNANCE.md`
- `docs/EXECUTIVE_DECK_GENERATION_OBSERVABILITY.md`
- `docs/EXECUTIVE_DECK_GENERATION_SECURITY_AND_PII.md`
- `docs/EXECUTIVE_DECK_GENERATION_ROLLOUT_AND_GOVERNANCE.md`

---

## What is mandatory before implementing P1

To start implementing the **Benchmark & Eval Executive Review Deck** safely, the minimum required documentation is:

1. capability map
2. technical productization of the first slice
3. P1 contract v1
4. official catalog of deck types
5. service architecture
6. API contract
7. artifact lifecycle
8. minimum UX spec
9. test strategy

In other words: P1 does not depend on the complete contracts for all future decks, but it does depend on the documentation infrastructure that defines the capability as a coherent system.

---

## What can be documented in parallel with P1

The items below do not block the start of P1, but they do block the idea of a **complete capability**:

- contract v1 for `document_review_deck`
- contract v1 for `policy_contract_comparison_deck`
- contract v1 for `action_plan_deck`
- contract v1 for `candidate_review_deck`
- contract v1 for `evidence_pack_deck`
- full quality/governance/PII policy

---

## Recommended documentation order

### Documentation phase A — mandatory before P1

1. `EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG`
2. `EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE`
3. `EXECUTIVE_DECK_GENERATION_API_CONTRACT`
4. `EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE`
5. `EXECUTIVE_DECK_GENERATION_UX_SPEC`
6. `EXECUTIVE_DECK_GENERATION_TEST_STRATEGY`

### Documentation phase B — required for the full capability

7. `DOCUMENT_REVIEW_DECK_CONTRACT_V1`
8. `POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1`
9. `ACTION_PLAN_DECK_CONTRACT_V1`
10. `CANDIDATE_REVIEW_DECK_CONTRACT_V1`
11. `EVIDENCE_PACK_DECK_CONTRACT_V1`

---

## Documentation “done” criteria

We can consider the capability documentation-ready when:

- deck types P1/P2/P3/P4/P5/P6 are named and cataloged
- there is a concrete contract for each priority deck
- there is a defined service architecture
- there is an explicit API contract with `ppt_creator_app`
- there is a defined artifact/provenance lifecycle
- there is a described minimum UX
- there is a testing strategy and rollout/quality policy

---

## Executive summary

Today the project already had enough documentation for the **technical P1**.  
With this package, the goal becomes closing the documentation needed for the **complete Executive Deck Generation capability** as well.

The central principle is simple:

> it is not enough to document an isolated export; it is necessary to document the catalog, contracts, architecture, UX, artifacts, tests, and governance of a recurring product capability.
