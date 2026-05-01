# HF Local LLM Service → model server boundary

This file exists as an operational migration checklist so we no longer mix:

- **generic model-serving infrastructure** (`hf_local_llm_service`)
- **deck domain logic** (`ppt_creator_ai` / `ppt_creator`)

## Target boundary

- `hf_local_llm_service` should know how to:
  - resolve provider/model
  - generate generic text
  - operate persistent chat
  - generate images
  - expose health, readiness, registry, jobs, and uploads
- `hf_local_llm_service` should not know about:
  - `BriefingInput`
  - `PresentationInput`
  - decks, slides, deck revise/critique
- `ppt_creator_ai` should know how to:
  - build deck prompts
  - extract JSON from raw output
  - normalize slide payloads
  - validate deck schema
  - run revise/critique loops

## Implementation checklist

- [x] Introduce a generic inference endpoint (`/v1/generate`) in `hf_local_llm_service`
- [x] Migrate the app's main flow to a generic text-generation contract
- [x] Remove `ppt_creator*` imports from the service core in the main health/API path
- [x] Remove `app_bridge` from the critical path for health/API/main providers
- [x] Migrate `ppt_creator_ai.providers.local_service` to use `/v1/generate`
- [x] Move deck prompts / parsing / validation into `ppt_creator_ai`
- [x] Keep `/v1/presentation/*` only as temporary compatibility
- [x] Update service docs and tests to reflect the model server identity
- [x] Update app docs and tests for the new flow
- [x] Run tests on both sides and HTTP smoke tests

## Final state of this phase

- app **preferred** path: `ppt_creator_ai -> /v1/generate -> raw text/JSON -> parsing/validation in the app`
- **legacy/compat** path: `/v1/presentation/*`
- `app_bridge.py` still exists only for compatibility with the legacy deck endpoints, but it is no longer in the critical path of the generic server

## Guiding rule

> The server knows how to serve models. The app knows how to build decks.