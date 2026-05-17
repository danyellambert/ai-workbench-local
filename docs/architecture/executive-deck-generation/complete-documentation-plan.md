# Executive Deck Generation — complete documentation plan

## Objective

Consolidate **absolutely everything that needs to be documented** to fully implement the **Executive Deck Generation** capability in the Axiovance ecosystem.

This document exists to answer, in operational terms, four questions:

1. what is already documented
2. what still needs to be documented
3. what is mandatory before implementing P1
4. what can be documented in parallel with the implementation of the next deck types

---

## Current status

### Already documented

#### Capability / product vision
- `docs/architecture/executive-deck-generation/product-capability.md`

#### Technical productization of the first slice
- `docs/architecture/executive-deck-generation/productization.md`

#### Concrete P1 contract
- `docs/architecture/executive-deck-generation/benchmark-eval-executive-review-contract-v1.md`

#### Main roadmap
- `ROADMAP.md`

### Complementary documentation scope completed in this round

- official catalog of deck types and `export_kind`
- capability service architecture
- API contract between Axiovance and `ppt_creator_app`
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
- `docs/architecture/executive-deck-generation/product-capability.md`

### 1.2 Complete documentation plan
- `docs/architecture/executive-deck-generation/complete-documentation-plan.md`

### 1.3 Official catalog of deck types
- `docs/architecture/executive-deck-generation/official-catalog-of-deck-types-and-contracts.md`

### 1.4 Routing policy
- `docs/architecture/executive-deck-generation/routing-and-deck-type-selection.md`

### 1.5 Contract versioning
- `docs/architecture/executive-deck-generation/contract-versioning-and-naming.md`

---

## 2. Data contracts by deck type

### P1 — already started
- `docs/architecture/executive-deck-generation/benchmark-eval-executive-review-contract-v1.md`

### P2/P3/P4/P5/P6 — required for the full capability
- `docs/architecture/executive-deck-generation/document-review-deck-contract-v1.md`
- `docs/architecture/executive-deck-generation/policy-contract-comparison-deck-contract-v1.md`
- `docs/architecture/executive-deck-generation/action-plan-deck-contract-v1.md`
- `docs/architecture/executive-deck-generation/candidate-review-deck-contract-v1.md`
- `docs/architecture/executive-deck-generation/evidence-pack-deck-contract-v1.md`

---

## 3. Architecture and integration

- `docs/architecture/executive-deck-generation/productization.md`
- `legacy/docs/archive/executive-deck-generation-service-architecture.md`
- `docs/architecture/executive-deck-generation/api-contract.md`
- `docs/architecture/executive-deck-generation/artifact-lifecycle.md`
- `docs/architecture/executive-deck-generation/mapping-contract-renderer-payload.md`
- `docs/architecture/executive-deck-generation/slide-recipes-by-deck-type.md`
- `docs/architecture/executive-deck-generation/branding-and-visual-policy.md`
- `docs/architecture/executive-deck-generation/failure-modes-and-fallback-strategy.md`

---

## 4. Product / UX

- `docs/architecture/executive-deck-generation/ux-spec.md`
- `docs/architecture/executive-deck-generation/ui-evolution.md`
- `docs/architecture/executive-deck-generation/user-journeys.md`

---

## 5. Quality, testing, and governance

- `docs/architecture/executive-deck-generation/test-strategy.md`
- `docs/architecture/executive-deck-generation/quality-grounding-and-governance.md`
- `docs/architecture/executive-deck-generation/observability.md`
- `docs/architecture/executive-deck-generation/security-and-pii.md`
- `docs/architecture/executive-deck-generation/rollout-and-governance.md`

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
