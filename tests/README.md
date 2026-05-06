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

## Current green gate

Use this as the current presentation/reviewer gate. It is intentionally smaller than the full historical suite and avoids known failing live/provider/legacy UI modules.

Prepare the Python environment with the same interpreter you will use to run the gate:

```bash
python3 -m pip install -r requirements.txt
```

Then run:

```bash
scripts/run_current_test_gate.sh
```

To force a specific interpreter:

```bash
PYTHON=python3.11 scripts/run_current_test_gate.sh
```

This gate is not a replacement for repairing the broader suite. It is the currently documented deterministic/offline-ish subset that a reviewer can run without invoking the known non-current/live/provider/legacy failures.

Run an individual module:

```bash
python3 -m unittest tests.test_product_presenters_unittest
```

Run a minimal current-product smoke subset:

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

The latest audit found 21 non-passing modules. They are intentionally documented here, but they are not part of the current green gate.

| Module | Current interpretation |
| --- | --- |
| `tests.test_ai_lab_live_endpoints_unittest` | Live/API runtime-path dependent. |
| `tests.test_ai_lab_validation_harness_unittest` | AI Lab harness/runtime-path dependent. |
| `tests.test_candidate_review_context_unittest` | Candidate Review expectation drift. |
| `tests.test_candidate_review_front_integration_unittest` | Front integration/import drift. |
| `tests.test_evidenceops_external_targets_unittest` | External targets/Trello optional integration. |
| `tests.test_gradio_components_candidate_review_unittest` | Legacy Gradio surface. |
| `tests.test_huggingface_remote_providers_unittest` | Optional remote provider dependency. |
| `tests.test_ollama_provider_service_compat_unittest` | Provider compatibility/expectation drift. |
| `tests.test_benchmark_campaign_unittest` | Benchmark campaign discovery expectation drift. |
| `tests.test_evidenceops_local_ops` | EvidenceOps local integration drift. |
| `tests.test_evidenceops_mcp_client` | EvidenceOps MCP integration drift. |
| `tests.test_evidenceops_mcp_server` | EvidenceOps MCP server/import drift. |
| `tests.test_evidenceops_external_targets_legacy_unittest` | Legacy external targets integration. |
| `tests.test_product_api_unittest` | Product API runtime-path/environment mismatch. |
| `tests.test_product_service_unittest` | Product service expectation drift. |
| `tests.test_product_workflows_front_integration_unittest` | Product/front integration import drift. |
| `tests.test_provider_registry_unittest` | Provider registry expectation drift. |
| `tests.test_runtime_snapshot_unittest` | Runtime snapshot expectation/import drift. |
| `tests.test_streamlit_ai_lab_functional_unittest` | Legacy Streamlit surface. |
| `tests.test_streamlit_app_smoke_unittest` | Legacy Streamlit surface. |
| `tests.test_structured_provider_resolution_unittest` | Structured provider fallback expectation drift. |

## Historical test names cleanup

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
test_model_comparison_log.py
test_evidenceops_mcp_client.py
test_structured_service_unittest.py
```

## Naming policy

Avoid new test names with historical phase labels. Prefer behavior/subsystem names instead of milestone labels.

Preferred names should describe the subsystem or behavior:

```text
test_structured_service_unittest.py
test_benchmark_decision_gate_unittest.py
test_eval_store_diagnosis_unittest.py
test_model_comparison_log.py
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

1. Maintain behavior/subsystem test names and avoid reintroducing historical phase-like filenames.
2. Maintain the documented current green gate while repairing the broader suite.
3. Repair or quarantine environment-dependent tests.
4. Separate legacy Streamlit/Gradio tests from current product tests.
5. Fix provider expectation drift separately from repository cleanup.
