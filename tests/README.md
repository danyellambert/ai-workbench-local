# Tests

This directory contains Python test modules for AI Decision Studio.

The suite is currently a mixed historical/current test surface. It includes current product tests, API/service tests, provider tests, evaluation/benchmark tests, EvidenceOps/MCP tests, and legacy Streamlit/Gradio smoke tests.

This README exists so a reviewer does not assume every file in `tests/` represents the current deployable product path or that the full suite is green.

## Current audit snapshot

Last audited locally on 2026-05-06 after the script-name cleanup commits.

```text
test_files=56
py_compile_failures=0
test_modules=56
PASS=35
FAIL=21
TIMEOUT=0
phase_like_test_files=0
```

Interpretation:

- All Python test files compiled.
- 35 test modules passed individually.
- 21 test modules did not pass individually.
- Several failures are environment-dependent, legacy-surface-related, provider-contract-related, or expectation-drift-related.
- The full `tests/` directory should not yet be advertised as a clean green CI suite.

## How to run tests

Run an individual module:

```bash
python3 -m unittest tests.test_product_presenters_unittest
```

Run a focused current-product smoke subset:

```bash
python3 -m unittest \
  tests.test_app_bootstrap_smoke_unittest \
  tests.test_product_presenters_unittest \
  tests.test_document_context_runtime_unittest \
  tests.test_runtime_execution_log_unittest
```

Run all top-level unittest modules one by one:

```bash
find tests -maxdepth 1 -type f -name 'test*.py' \
  | sed 's#/#.#g; s#.py$##' \
  | sort \
  | while read -r module; do
      python3 -m unittest "$module"
    done
```

## Test categories

### Current product, API, and service tests

These target the current product backend, service layer, runtime state, or product-facing behavior.

Examples:

- `test_app_bootstrap_smoke_unittest.py`
- `test_product_api_unittest.py`
- `test_product_service_unittest.py`
- `test_product_presenters_unittest.py`
- `test_runtime_execution_log_unittest.py`
- `test_runtime_snapshot_unittest.py`
- `test_candidate_review_context_unittest.py`
- `test_candidate_review_presenter_unittest.py`

Some of these currently fail and need expectation updates or environment setup fixes before they can be considered part of a green current-product gate.

### Provider and structured-output tests

These validate provider selection, provider fallback behavior, local/remote provider integrations, and structured response handling.

Examples:

- `test_provider_registry_unittest.py`
- `test_structured_provider_resolution_unittest.py`
- `test_structured_service_unittest.py`
- `test_huggingface_local_provider_unittest.py`
- `test_huggingface_remote_providers_unittest.py`
- `test_ollama_provider_service_compat_unittest.py`

Some failures here indicate provider-contract drift or missing optional/provider-specific dependencies.

### AI Lab and live endpoint tests

These cover AI Lab behavior, live endpoints, payload shape, and validation harnesses.

Examples:

- `test_ai_lab_live_endpoints_unittest.py`
- `test_ai_lab_validation_harness_unittest.py`
- `test_lab_chat_unittest.py`
- `test_lab_evidenceops_payload.py`

Some live/API tests depend on runtime path configuration and may fail if local `/app`-style paths are not mapped for the current host.

### Evaluation and benchmark tests

These validate eval-store behavior, benchmark matrix behavior, closure/decision-gate reports, document-agent logs, and historical evaluation helpers.

Historical `phase*` filenames were renamed after reference auditing. Some test contents may still mention historical phases when describing legacy/eval provenance.

### EvidenceOps and MCP tests

These cover EvidenceOps local operations, external targets, repository snapshots, worklogs, and MCP integration.

Several currently fail on import or integration setup. Treat them as integration/legacy-adjacent until repaired.

### Legacy Streamlit and Gradio tests

These touch legacy or secondary UI surfaces, not the current AWS/React/Vite product path.

Examples:

- `test_streamlit_ai_lab_functional_unittest.py`
- `test_streamlit_app_smoke_unittest.py`
- `test_gradio_app_smoke_unittest.py`
- `test_gradio_components_candidate_review_unittest.py`

Streamlit/Gradio failures should be handled separately from the current deployable product path unless those legacy surfaces are intentionally being maintained.

## Current known non-passing modules

The latest audit found 21 non-passing modules:

- `tests.test_ai_lab_live_endpoints_unittest` — **FAIL**, 2.11s. `EE ⏎ ====================================================================== ⏎ ERROR: test_chat_session_message_roundtrip_persists_runtime_state (tests.test_ai_lab_live_endpoints_unittest.AiLabLiveApiTests.test_chat_session_message_roundtrip...`
- `tests.test_ai_lab_validation_harness_unittest` — **FAIL**, 1.07s. `127.0.0.1 - - [06/May/2026 08:51:54] "GET /health HTTP/1.1" 200 - ⏎ 127.0.0.1 - - [06/May/2026 08:51:54] "GET /api/product/workflows HTTP/1.1" 200 - ⏎ ---------------------------------------- ⏎ Exception occurred during processing of reques...`
- `tests.test_candidate_review_context_unittest` — **FAIL**, 3.26s. `FF. ⏎ ====================================================================== ⏎ FAIL: test_build_candidate_review_input_text_prefers_explicit_input (tests.test_candidate_review_context_unittest.CandidateReviewContextTests.test_build_candidat...`
- `tests.test_candidate_review_front_integration_unittest` — **FAIL**, 0.07s. `E ⏎ ====================================================================== ⏎ ERROR: test_candidate_review_front_integration_unittest (unittest.loader._FailedTest.test_candidate_review_front_integration_unittest) ⏎ --------------------------...`
- `tests.test_evidenceops_external_targets_unittest` — **FAIL**, 0.40s. `....E... ⏎ ====================================================================== ⏎ ERROR: test_create_trello_cards_from_product_result_can_publish_only_selected_card (tests.test_evidenceops_external_targets_unittest.EvidenceOpsExternalTarg...`
- `tests.test_gradio_components_candidate_review_unittest` — **FAIL**, 0.03s. `E ⏎ ====================================================================== ⏎ ERROR: test_gradio_components_candidate_review_unittest (unittest.loader._FailedTest.test_gradio_components_candidate_review_unittest) ⏎ --------------------------...`
- `tests.test_huggingface_remote_providers_unittest` — **FAIL**, 0.07s. `E ⏎ ====================================================================== ⏎ ERROR: test_huggingface_remote_providers_unittest (unittest.loader._FailedTest.test_huggingface_remote_providers_unittest) ⏎ --------------------------------------...`
- `tests.test_ollama_provider_service_compat_unittest` — **FAIL**, 0.80s. `..E... ⏎ ====================================================================== ⏎ ERROR: test_ollama_provider_falls_back_to_openai_compat_chat_when_native_route_is_missing (tests.test_ollama_provider_service_compat_unittest.OllamaProviderSe...`
- `tests.test_benchmark_campaign_unittest` — **FAIL**, 0.40s. `..F ⏎ ====================================================================== ⏎ FAIL: test_find_latest_phase8_5_run_dir_sees_campaign_runs (tests.test_benchmark_campaign_unittest.Phase85CampaignTests.test_find_latest_phase8_5_run_dir_sees_cam...`
- `tests.test_evidenceops_local_ops` — **FAIL**, 0.39s. `E ⏎ ====================================================================== ⏎ ERROR: test_evidenceops_local_ops (unittest.loader._FailedTest.test_evidenceops_local_ops) ⏎ ------------------------------------------------------...`
- `tests.test_evidenceops_mcp_client` — **FAIL**, 0.39s. `E ⏎ ====================================================================== ⏎ ERROR: test_evidenceops_mcp_client (unittest.loader._FailedTest.test_evidenceops_mcp_client) ⏎ ----------------------------------------------------...`
- `tests.test_evidenceops_mcp_server` — **FAIL**, 0.39s. `E ⏎ ====================================================================== ⏎ ERROR: test_evidenceops_mcp_server (unittest.loader._FailedTest.test_evidenceops_mcp_server) ⏎ ----------------------------------------------------...`
- `tests.test_evidenceops_external_targets_legacy_unittest` — **FAIL**, 0.38s. `E ⏎ ====================================================================== ⏎ ERROR: test_evidenceops_external_targets_legacy_unittest (unittest.loader._FailedTest.test_evidenceops_external_targets_legacy_unittest) ⏎ ----------------------------------------------...`
- `tests.test_product_api_unittest` — **FAIL**, 9.06s. `127.0.0.1 - - [06/May/2026 08:52:08] "GET /api/product/command-center HTTP/1.1" 200 - ⏎ ---------------------------------------- ⏎ Exception occurred during processing of request from ('127.0.0.1', 57466) ⏎ Traceback (most recent call last)...`
- `tests.test_product_service_unittest` — **FAIL**, 0.36s. `...E.....F. ⏎ ====================================================================== ⏎ ERROR: test_generate_product_workflow_deck_uses_current_action_plan_items_instead_of_global_action_store (tests.test_product_service_unittest.ProductServ...`
- `tests.test_product_workflows_front_integration_unittest` — **FAIL**, 0.06s. `E ⏎ ====================================================================== ⏎ ERROR: test_product_workflows_front_integration_unittest (unittest.loader._FailedTest.test_product_workflows_front_integration_unittest) ⏎ ------------------------...`
- `tests.test_provider_registry_unittest` — **FAIL**, 0.26s. `...FF.F ⏎ ====================================================================== ⏎ FAIL: test_resolve_provider_entry_falls_back_when_requested_provider_is_missing (tests.test_provider_registry_unittest.ProviderRegistryTests.test_resolve_pro...`
- `tests.test_runtime_snapshot_unittest` — **FAIL**, 0.39s. `....E........... ⏎ ====================================================================== ⏎ ERROR: test_build_runtime_snapshot_exposes_action_governance_metrics_after_sensitive_update (tests.test_runtime_snapshot_unittest.RuntimeSnapshotTes...`
- `tests.test_streamlit_ai_lab_functional_unittest` — **FAIL**, 43.43s. `E2026-05-06 08:52:20.881 Uncaught app execution ⏎ Traceback (most recent call last): ⏎   File "/Users/danyellambert/.pyenv/versions/3.11.9/lib/python3.11/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 129, in exec_func_wit...`
- `tests.test_streamlit_app_smoke_unittest` — **FAIL**, 0.80s. `2026-05-06 08:53:03.164 Uncaught app execution ⏎ Traceback (most recent call last): ⏎   File "/Users/danyellambert/.pyenv/versions/3.11.9/lib/python3.11/site-packages/streamlit/runtime/scriptrunner/exec_code.py", line 129, in exec_func_with...`
- `tests.test_structured_provider_resolution_unittest` — **FAIL**, 0.36s. `E. ⏎ ====================================================================== ⏎ ERROR: test_resolve_provider_falls_back_to_ollama_and_records_reason (tests.test_structured_provider_resolution_unittest.StructuredProviderResolutionTests.test_re...`

## Phase-like test names

A prior audit found 21 historical phase-like filenames. They have since been renamed to behavior/subsystem names:

- `test_langgraph_shadow_log.py`
- `test_evidence_cv_real_document_eval_unittest.py`
- `test_document_agent_log.py`
- `test_model_comparison_log.py`
- `test_benchmark_audit_unittest.py`
- `test_benchmark_matrix_round2_unittest.py`
- `test_benchmark_matrix_unittest.py`
- `test_benchmark_campaign_unittest.py`
- `test_benchmark_closure_unittest.py`
- `test_benchmark_decision_gate_unittest.py`
- `test_benchmark_timeout_unittest.py`
- `test_agent_workflow_eval_unittest.py`
- `test_eval_store_diagnosis_unittest.py`
- `test_eval_store_unittest.py`
- `test_live_evals_unittest.py`
- `test_evidenceops_local_ops.py`
- `test_evidenceops_mcp_client.py`
- `test_evidenceops_mcp_server.py`
- `test_evidenceops_repository_snapshot.py`
- `test_evidenceops_worklog.py`
- `test_evidenceops_external_targets_legacy_unittest.py`

Current behavior/subsystem names include:

```text
test_benchmark_decision_gate_unittest.py
test_eval_store_diagnosis_unittest.py
test_model_comparison_log_unittest.py
test_evidenceops_mcp_client.py
test_structured_output_eval_unittest.py
```

## Naming policy

Avoid new test names with historical phase labels such as:

```text
phase5
phase6
phase7
phase8
phase8_5
phase95
```

Preferred names should describe the subsystem or behavior:

```text
test_structured_output_eval_unittest.py
test_benchmark_decision_gate_unittest.py
test_eval_store_diagnosis_unittest.py
test_model_comparison_log_unittest.py
test_evidenceops_mcp_client.py
```

## Maintenance policy

Before changing tests:

1. Check whether the test targets the current product path, eval tooling, provider integration, or legacy UI.
2. Do not delete failing tests just to make the suite green.
3. Mark or document environment-dependent tests clearly.
4. Rename historical/phase-like tests in small commits.
5. Keep product logic changes separate from test organization changes.
6. Re-run focused subsets after each commit.

## Current recommended next steps

1. Maintain behavior/subsystem test names; avoid reintroducing phase-like filenames.
2. Create a green current-product test subset.
3. Repair or quarantine environment-dependent tests.
4. Separate legacy Streamlit/Gradio tests from current product tests.
5. Fix provider expectation drift separately from repository cleanup.
