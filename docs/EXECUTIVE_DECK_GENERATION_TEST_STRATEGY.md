# Executive Deck Generation — test strategy

## Objective

Define the minimum testing strategy for the capability.

---

## Test layers

## 1. Unit tests for builders and adapters

Cover:

- contract builders
- payload adapters
- validation of required fields

Current status:

- P1/P2/P3 builders and adapters are already covered in `tests/test_presentation_export_unittest.py`

---

## 2. Service tests

Suggested file:

- `tests/test_presentation_export_service_unittest.py`

Cover:

- healthcheck
- render request
- timeouts
- artifact downloads
- local persistence
- partial failures

Current status:

- `tests/test_presentation_export_service_unittest.py` already covers P1
- the same file now also covers the deck types `document_review_deck`, `policy_contract_comparison_deck`, `action_plan_deck`, `candidate_review_deck`, and `evidence_pack_deck`
- there is also coverage for the P1 naming alias and the feature flag by `export_kind`

---

## 3. Contract tests by deck type

Each new v1 contract should have focused tests:

- `document_review_deck`
- `policy_contract_comparison_deck`
- `action_plan_deck`
- `candidate_review_deck`
- `evidence_pack_deck`

Current status:

- these deck types already have builder/adapter unit-test coverage in `tests/test_presentation_export_unittest.py`

---

## 4. Smoke tests with `ppt_creator_app`

Optional tests that can be reproduced locally:

- the service starts
- `GET /health` responds
- `POST /render` responds
- `.pptx` downloads successfully

Current status:

- still pending as a reproducible manual smoke/integration test with the real `ppt_creator_app` running

---

## 5. UI smoke tests

Cover:

- presence of the capability entry point
- generation button
- loading state
- friendly error state
- available downloads on success

Current status:

- the Streamlit UI already exposes deck-type selection, generation, and downloads
- capability-specific smoke tests are still a pending track

---

## 6. Artifacts and regression

For later evolution:

- golden payloads by deck type
- manifest/review-response comparison
- optionally visual regression by reusing `ppt_creator_app` capabilities

---

## Minimum criteria to consider a deck type tested

A deck type should only be treated as implemented when it has:

1. unit test do contract builder
2. a unit test for the payload adapter
3. a service test for the generation flow
4. a reproducible local smoke/integration test

## Current summarized status

- **already done:** multi-deck builder/adapter unit tests
- **already done:** generation-flow service tests for the currently supported deck types
- **still missing:** a real smoke test with `ppt_creator_app` and capability-specific UI smoke tests
