# Scripts

This directory contains operational commands, readiness checks, evaluation runners, reporting utilities, and maintenance helpers for AI Decision Studio.

For reviewers: this is not the main product surface. Start with `../README.md`, `../docs/`, and the current deployment docs first. Use this file when you want to understand how the repository is operated, validated, benchmarked, and packaged.

## Most important entry points

These are the scripts most likely to matter for running, packaging, or validating the current project.

| Script | Use when |
| --- | --- |
| `build_deployment_bundle.sh` | Building the clean app bundle used for AWS/local transfer workflows. |
| `deploy_aws_slim.sh` | Deploying the current AWS slim stack on the target host. |
| `smoke_aws_slim.sh` | Smoke-testing the AWS slim deployment. |
| `run_local_docker.sh` | Running the local Docker stack. |
| `run_local_dev.sh` | Running/checking local host development mode. |
| `readiness_multi_environment_contract_check.sh` | Checking the local/Docker/AWS environment contract. |
| `readiness_final_deploy_check.sh` | Running final deployment readiness checks before publication or handoff. |

`build_oracle_deployment_bundle.sh` remains as a backward-compatible wrapper for the older Oracle-named bundle command. Oracle-only scripts and docs live under `../legacy/`.

## How to read this directory

The script names follow a loose convention:

| Prefix | Meaning |
| --- | --- |
| `run_*` | Starts a workflow, evaluation, benchmark, validation suite, or service-like command. |
| `readiness_*` | Checks whether a capability, deployment contract, or repo state is ready. |
| `report_*` | Produces a diagnostic/reporting summary from existing logs or stored outputs. |
| `evaluate_*` | Runs a focused evaluation against tracked fixtures. |
| `validate_*` | Validates a contract, payload, index, or sanitized artifact. |
| `smoke_*` | Runs a small end-to-end check. |
| `build_*` | Builds a bundle, fixture set, baseline, or generated support artifact. |
| `restore_*` / `stage_*` / `select_*` | Maintenance and workspace preparation helpers. |

## Boundaries

- Active deployment scripts stay at the root of `scripts/` for compatibility with docs, CI, and local workflows.
- Oracle-only historical scripts live in `../legacy/scripts/oracle/`.
- Tracked eval fixtures and benchmark workspace documentation live in `../evals/`.
- Generated reports, local benchmark runs, local PDF corpora, caches, secrets, and `.DS_Store` files should not be committed.
- Do not move or rename scripts referenced by CI, deployment docs, or local runbooks without adding a compatibility wrapper.

## Deployment and local runtime

Stable operational entry points:

- `build_deployment_bundle.sh`
- `build_oracle_deployment_bundle.sh`
- `deploy_aws_slim.sh`
- `smoke_aws_slim.sh`
- `run_local_docker.sh`
- `run_local_dev.sh`

These scripts are intentionally kept easy to find. They are the practical path for packaging, local Docker execution, AWS deployment, and AWS smoke validation.

## Readiness gates

Readiness scripts are guardrails. They usually fail fast when a repository contract, environment assumption, or deployment expectation is not met.

Current readiness checks include:

- `readiness_admin_session_isolation_check.sh`
- `readiness_ai_lab_content_check.sh`
- `readiness_ai_lab_golden_state_check.sh`
- `readiness_artifacts_compact_check.sh`
- `readiness_candidate_review_contract_check.sh`
- `readiness_evidenceops_ui_cache_check.sh`
- `readiness_final_deploy_check.sh`
- `readiness_multi_environment_contract_check.sh`
- `readiness_nextcloud_golden_baseline_check.sh`
- `readiness_phase_13_2_public_session_retention_check.sh`
- `readiness_preferences_evals_surface_check.sh`
- `readiness_public_admin_policy_check.sh`
- `readiness_public_ai_lab_overlay_check.sh`
- `readiness_required_integrations_check.sh`
- `readiness_required_providers_check.sh`
- `readiness_run_history_compact_check.sh`
- `readiness_runbook_phases_8_12_check.sh`
- `readiness_trello_public_visibility_check.sh`

## Evaluation and benchmark runners

These scripts are used to run or replay evaluation workflows. They are useful for engineering review, but they are not required for the AWS slim deployment bundle.

- `backfill_product_runtime_evals.py`
- `benchmark_vl_router_multilayout.py`
- `evaluate_checklist_regression.py`
- `evaluate_evidence_cv_gold_set.py`
- `import_phase8_eval_history.py`
- `run_all_phase_4_5_benchmarks.py`
- `run_document_review_findings_experiment.py`
- `run_embedding_benchmark.py`
- `run_pdf_extraction_benchmark.py`
- `run_pdf_extraction_benchmark_en.py`
- `run_phase5_structured_eval.py`
- `run_phase8_5_benchmark_matrix.py`
- `run_phase8_agent_workflow_eval.py`
- `run_phase8_live_evals.py`
- `run_phase_4_5_benchmark_suite.py`
- `run_synthetic_resume_benchmark.py`

Tracked fixtures/configuration for these workflows live under `../evals/`.

## Reporting and diagnostics

These scripts summarize stored run history, evaluation logs, model-comparison traces, or operational artifacts.

- `report_evidence_shadow_rollout.py`
- `report_phase55_langchain_shadow_log.py`
- `report_phase55_langgraph_shadow_log.py`
- `report_phase6_document_agent_log.py`
- `report_phase7_model_comparison_log.py`
- `report_phase8_5_audit.py`
- `report_phase8_5_closure.py`
- `report_phase8_5_decision_gate.py`
- `report_phase8_eval_diagnosis.py`
- `report_phase8_eval_store.py`
- `report_vl_called_cases.py`

## Validation helpers

Validation scripts check payloads, indexes, contracts, or sanitized artifacts.

- `validate_aws_env_contract.py`
- `validate_evidence_cv_indexing_payload.py`
- `validate_phase_4_5.py`
- `validate_sanitized_functional_baseline.py`

## Maintenance and workspace utilities

These scripts support local workspace preparation, data staging, restore flows, or generated support artifacts.

- `ai_lab_shell_lib.sh`
- `auto_rollout_evidence_cv.py`
- `backfill_evidenceops_history.py`
- `build_resume_component_bank.py`
- `build_sanitized_functional_baseline.py`
- `capture_golden_surface_snapshot.py`
- `cleanup_public_session_overlays.py`
- `download_phase8_public_materials.py`
- `generate_admin_password_hash.py`
- `generate_multilayout_resumes.py`
- `generate_synthetic_resumes_with_pdf.py`
- `preindex_public_reference_corpus.py`
- `preindex_public_reference_corpus_page_routes.json`
- `restore_ai_lab_golden_state.sh`
- `restore_nextcloud_golden_baseline.sh`
- `resume_dataset_splitter_v2.py`
- `select_phase5_ui_examples.py`
- `stage_functional_baseline_sources.py`

## Frontend, MCP, and surface validation

These scripts validate application surfaces, payloads, MCP integration, or frontend parity.

- `run_ai_lab_validation.py`
- `run_ai_lab_validation.sh`
- `run_candidate_review_validation.py`
- `run_evidenceops_mcp_server.py`
- `run_frontend_surface_validation.py`
- `run_frontend_surface_validation.sh`
- `run_mcp_integration_validation.py`
- `run_mcp_integration_validation.sh`
- `run_ppt_creator_renderer_host.sh`
- `run_presentation_export_smoke_suite.py`
- `smoke_ai_lab_payloads.py`
- `smoke_docker_policy_comparison_write.sh`
- `smoke_docker_workflow_write.sh`
- `smoke_frontend_docker_workflows_ui.sh`
- `smoke_frontend_surface_payloads.py`
- `smoke_frontend_ui_parity_local_vs_docker.sh`

## Analysis and comparison helpers

These are specialized helpers for comparing extraction paths, benchmark configurations, charts, or latency.

- `compare_pdf_extraction_paths.py`
- `compare_phase_4_5_configs.py`
- `measure_surface_latency.sh`
- `render_phase_4_5_charts.py`

## Reviewer notes

A recruiter or technical reviewer should not need to inspect every script. The important signal is that the project has:

- a stable deployment path;
- explicit readiness gates;
- repeatable evaluation and benchmark tooling;
- reporting utilities for engineering decisions;
- a clear separation between current product, eval workspace, and legacy/deferred material.

When in doubt, treat `build_deployment_bundle.sh`, `deploy_aws_slim.sh`, `smoke_aws_slim.sh`, and `run_local_docker.sh` as the current operational path.
