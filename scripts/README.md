# Scripts

This directory contains operational entry points, readiness gates, evaluation runners, reporting utilities, and repository maintenance scripts for AI Decision Studio.

Start here instead of browsing individual scripts one by one.

## Current deployment entry points

These scripts are the most important operational commands and should remain stable:

| Script | Purpose |
| --- | --- |
| `build_deployment_bundle.sh` | Builds the app deployment bundle used for AWS/local transfer workflows. |
| `build_oracle_deployment_bundle.sh` | Backward-compatible wrapper for older Oracle-named bundle commands. |
| `deploy_aws_slim.sh` | Deploys the AWS slim stack on the target host. |
| `smoke_aws_slim.sh` | Smoke-tests the AWS slim deployment. |
| `run_local_docker.sh` | Runs the local Docker stack. |
| `run_local_dev.sh` | Runs/checks local host development mode. |

## Layout policy

- Root-level scripts are kept for compatibility with existing docs, CI, and local workflows.
- Oracle-only historical scripts live under `../legacy/scripts/oracle/`.
- Evaluation fixtures and benchmark workspace files live under `../evals/`.
- Generated reports, benchmark outputs, local corpora, caches, and secrets should not be committed.
- Do not move or rename scripts that are referenced by deployment docs, CI, or local runbooks without adding a compatibility wrapper.

## Script categories

### Deployment and local runtime

| Script | Notes |
| --- | --- |
| `build_deployment_bundle.sh` | Entry points for local, Docker, AWS, and deployment bundle flows. |
| `build_oracle_deployment_bundle.sh` | Entry points for local, Docker, AWS, and deployment bundle flows. |
| `deploy_aws_slim.sh` | Entry points for local, Docker, AWS, and deployment bundle flows. |
| `run_local_dev.sh` | Entry points for local, Docker, AWS, and deployment bundle flows. |
| `run_local_docker.sh` | Entry points for local, Docker, AWS, and deployment bundle flows. |
| `smoke_aws_slim.sh` | Entry points for local, Docker, AWS, and deployment bundle flows. |

### Readiness and repository gates

| Script | Notes |
| --- | --- |
| `readiness_admin_session_isolation_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_ai_lab_content_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_ai_lab_golden_state_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_artifacts_compact_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_candidate_review_contract_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_evidenceops_ui_cache_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_final_deploy_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_multi_environment_contract_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_nextcloud_golden_baseline_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_phase_13_2_public_session_retention_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_preferences_evals_surface_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_public_admin_policy_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_public_ai_lab_overlay_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_required_integrations_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_required_providers_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_run_history_compact_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_runbook_phases_8_12_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |
| `readiness_trello_public_visibility_check.sh` | Checks that validate environment contracts, repo state, or deployment readiness. |

### Evaluation and benchmark runners

| Script | Notes |
| --- | --- |
| `backfill_product_runtime_evals.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `benchmark_vl_router_multilayout.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `evaluate_checklist_regression.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `evaluate_evidence_cv_gold_set.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `import_phase8_eval_history.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `report_phase8_eval_diagnosis.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `report_phase8_eval_store.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_all_phase_4_5_benchmarks.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_document_review_findings_experiment.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_embedding_benchmark.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_pdf_extraction_benchmark.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_pdf_extraction_benchmark_en.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_phase5_structured_eval.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_phase8_5_benchmark_matrix.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_phase8_agent_workflow_eval.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_phase8_live_evals.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_phase_4_5_benchmark_suite.py` | Manual/CI-oriented evaluation and benchmark entry points. |
| `run_synthetic_resume_benchmark.py` | Manual/CI-oriented evaluation and benchmark entry points. |

### Reporting and diagnostics

| Script | Notes |
| --- | --- |
| `report_evidence_shadow_rollout.py` | Report generators and diagnostic summaries. |
| `report_phase55_langchain_shadow_log.py` | Report generators and diagnostic summaries. |
| `report_phase55_langgraph_shadow_log.py` | Report generators and diagnostic summaries. |
| `report_phase6_document_agent_log.py` | Report generators and diagnostic summaries. |
| `report_phase7_model_comparison_log.py` | Report generators and diagnostic summaries. |
| `report_phase8_5_audit.py` | Report generators and diagnostic summaries. |
| `report_phase8_5_closure.py` | Report generators and diagnostic summaries. |
| `report_phase8_5_decision_gate.py` | Report generators and diagnostic summaries. |
| `report_vl_called_cases.py` | Report generators and diagnostic summaries. |

### Validation helpers

| Script | Notes |
| --- | --- |
| `validate_aws_env_contract.py` | Payload, index, and contract validators. |
| `validate_evidence_cv_indexing_payload.py` | Payload, index, and contract validators. |
| `validate_phase_4_5.py` | Payload, index, and contract validators. |
| `validate_sanitized_functional_baseline.py` | Payload, index, and contract validators. |

### Maintenance and workspace utilities

| Script | Notes |
| --- | --- |
| `auto_rollout_evidence_cv.py` | Repository maintenance, workspace preparation, and support utilities. |
| `restore_ai_lab_golden_state.sh` | Repository maintenance, workspace preparation, and support utilities. |
| `restore_nextcloud_golden_baseline.sh` | Repository maintenance, workspace preparation, and support utilities. |
| `select_phase5_ui_examples.py` | Repository maintenance, workspace preparation, and support utilities. |
| `stage_functional_baseline_sources.py` | Repository maintenance, workspace preparation, and support utilities. |

### Operational runners

| Script | Notes |
| --- | --- |
| `run_ai_lab_validation.py` | Manual operational commands and workflow runners. |
| `run_ai_lab_validation.sh` | Manual operational commands and workflow runners. |
| `run_candidate_review_validation.py` | Manual operational commands and workflow runners. |
| `run_evidenceops_mcp_server.py` | Manual operational commands and workflow runners. |
| `run_frontend_surface_validation.py` | Manual operational commands and workflow runners. |
| `run_frontend_surface_validation.sh` | Manual operational commands and workflow runners. |
| `run_mcp_integration_validation.py` | Manual operational commands and workflow runners. |
| `run_mcp_integration_validation.sh` | Manual operational commands and workflow runners. |
| `run_ppt_creator_renderer_host.sh` | Manual operational commands and workflow runners. |
| `run_presentation_export_smoke_suite.py` | Manual operational commands and workflow runners. |

### Other utilities

| Script | Notes |
| --- | --- |
| `ai_lab_shell_lib.sh` | Utility scripts that do not yet fit a narrower bucket. |
| `backfill_evidenceops_history.py` | Utility scripts that do not yet fit a narrower bucket. |
| `build_resume_component_bank.py` | Utility scripts that do not yet fit a narrower bucket. |
| `build_sanitized_functional_baseline.py` | Utility scripts that do not yet fit a narrower bucket. |
| `capture_golden_surface_snapshot.py` | Utility scripts that do not yet fit a narrower bucket. |
| `cleanup_public_session_overlays.py` | Utility scripts that do not yet fit a narrower bucket. |
| `compare_pdf_extraction_paths.py` | Utility scripts that do not yet fit a narrower bucket. |
| `compare_phase_4_5_configs.py` | Utility scripts that do not yet fit a narrower bucket. |
| `demo_phase95_evidenceops_mcp.py` | Utility scripts that do not yet fit a narrower bucket. |
| `download_phase8_public_materials.py` | Utility scripts that do not yet fit a narrower bucket. |
| `generate_admin_password_hash.py` | Utility scripts that do not yet fit a narrower bucket. |
| `generate_multilayout_resumes.py` | Utility scripts that do not yet fit a narrower bucket. |
| `generate_synthetic_resumes_with_pdf.py` | Utility scripts that do not yet fit a narrower bucket. |
| `measure_surface_latency.sh` | Utility scripts that do not yet fit a narrower bucket. |
| `preindex_public_reference_corpus.py` | Utility scripts that do not yet fit a narrower bucket. |
| `preindex_public_reference_corpus_page_routes.json` | Utility scripts that do not yet fit a narrower bucket. |
| `render_phase_4_5_charts.py` | Utility scripts that do not yet fit a narrower bucket. |
| `resume_dataset_splitter_v2.py` | Utility scripts that do not yet fit a narrower bucket. |
| `smoke_ai_lab_payloads.py` | Utility scripts that do not yet fit a narrower bucket. |
| `smoke_docker_policy_comparison_write.sh` | Utility scripts that do not yet fit a narrower bucket. |
| `smoke_docker_workflow_write.sh` | Utility scripts that do not yet fit a narrower bucket. |
| `smoke_frontend_docker_workflows_ui.sh` | Utility scripts that do not yet fit a narrower bucket. |
| `smoke_frontend_surface_payloads.py` | Utility scripts that do not yet fit a narrower bucket. |
| `smoke_frontend_ui_parity_local_vs_docker.sh` | Utility scripts that do not yet fit a narrower bucket. |

## Recruiter/readability notes

For a quick review of the project, the important paths are:

- `../README.md` for product overview.
- `../docs/` for current architecture, deployment, and operations documentation.
- `../evals/` for tracked evaluation fixtures and benchmark workspace documentation.
- `../legacy/` for historical/deferred materials that are not the active product path.

The presence of many scripts reflects the project’s engineering/evaluation history. The active product deployment path is intentionally documented at the top of this file.
