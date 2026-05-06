# Scripts

This directory contains operational commands, readiness checks, evaluation runners, reporting utilities, and maintenance helpers for AI Decision Studio.

For reviewers: this is not the main product surface. Start with `../README.md`, `../docs/`, and the current deployment docs first. Use this file when you want to understand how the repository is operated, validated, benchmarked, and packaged.

## What matters first

| Script | What it does |
| --- | --- |
| `build_deployment_bundle.sh` | Builds the clean application bundle used for AWS/local transfer workflows. This is the current generic bundle builder. |
| `deploy_aws_slim.sh` | Deploys the current AWS slim stack on the target host using the AWS environment contract. |
| `smoke_aws_slim.sh` | Runs smoke checks against the AWS slim deployment after it is started. |
| `run_local_docker.sh` | Starts or validates the local Docker workflow used to run the product locally. |
| `run_local_dev.sh` | Runs or checks local host development mode without relying on the AWS target host. |
| `readiness_multi_environment_contract_check.sh` | Checks the local/Docker/AWS environment contract and protects cross-environment assumptions. |
| `readiness_final_deploy_check.sh` | Final deployment-readiness gate before handoff/publication style work. |

`build_oracle_deployment_bundle.sh` remains as a backward-compatible wrapper for the older Oracle-named bundle command. Oracle-only operational material lives under `../legacy/`.

## Naming convention

| Prefix | Meaning |
| --- | --- |
| `build_*` | Builds a bundle, fixture set, baseline, or generated support artifact. |
| `run_*` | Starts a workflow, evaluation, benchmark, validation suite, or service-like command. |
| `readiness_*` | Checks whether a capability, deployment contract, or repository state is ready. |
| `report_*` | Produces a diagnostic/reporting summary from existing logs or stored outputs. |
| `evaluate_*` | Runs a focused evaluation against tracked fixtures. |
| `validate_*` | Validates a contract, payload, index, or sanitized artifact. |
| `smoke_*` | Runs a small end-to-end or surface check. |
| `restore_*`, `stage_*`, `select_*` | Maintenance and workspace preparation helpers. |

## Repository boundaries

- Active deployment scripts stay at the root of `scripts/` for compatibility with docs, CI, and local workflows.
- Oracle-only historical scripts live in `../legacy/scripts/oracle/`.
- Tracked eval fixtures and benchmark workspace documentation live in `../evals/`.
- Generated reports, local benchmark runs, local PDF corpora, caches, secrets, and `.DS_Store` files should not be committed.
- Do not move or rename scripts referenced by CI, deployment docs, or local runbooks without adding a compatibility wrapper.

## Complete script index

Every top-level tracked script/support file in this directory is listed below.

### Deployment and local runtime

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `build_deployment_bundle.sh` | Builds the clean application bundle used for AWS/local transfer workflows. This is the current generic bundle builder. | Use during normal local, Docker, or AWS operational workflows. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Current operational path; keep stable. |
| `build_oracle_deployment_bundle.sh` | Backward-compatible wrapper for the older Oracle-named bundle command. Kept so older commands do not break. | Use only when an older runbook or command still calls the Oracle-named bundle builder. | shell command; may read/write local runtime state; often reads/writes JSON | Compatibility wrapper; do not remove until old references are retired. |
| `deploy_aws_slim.sh` | Deploys the current AWS slim stack on the target host using the AWS environment contract. | Use during normal local, Docker, or AWS operational workflows. | shell command; may read deployment env files | Current operational path; keep stable. |
| `run_local_dev.sh` | Runs or checks local host development mode without relying on the AWS target host. | Use during normal local, Docker, or AWS operational workflows. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Current operational path; keep stable. |
| `run_local_docker.sh` | Starts or validates the local Docker workflow used to run the product locally. | Use during normal local, Docker, or AWS operational workflows. | shell command; may accept CLI arguments; may read deployment env files; uses eval fixtures/configs; may write local benchmark outputs; may read/write local runtime state; often reads/writes JSON | Current operational path; keep stable. |
| `smoke_aws_slim.sh` | Runs smoke checks against the AWS slim deployment after it is started. | Use during normal local, Docker, or AWS operational workflows. | shell command; may read deployment env files; often reads/writes JSON | Current operational path; keep stable. |

### Readiness gates

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `readiness_admin_session_isolation_check.sh` | Readiness gate for admin session isolation check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_ai_lab_content_check.sh` | Readiness gate for ai lab content check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_ai_lab_golden_state_check.sh` | Readiness gate for ai lab golden state check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may write local benchmark outputs; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_artifacts_compact_check.sh` | Readiness gate for artifacts compact check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_candidate_review_contract_check.sh` | Readiness gate for candidate review contract check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_evidenceops_ui_cache_check.sh` | Readiness gate for evidenceops ui cache check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_final_deploy_check.sh` | Final deployment-readiness gate before handoff/publication style work. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files | Safe to run as checks; should fail fast on contract drift. |
| `readiness_multi_environment_contract_check.sh` | Checks the local/Docker/AWS environment contract and protects cross-environment assumptions. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may read deployment env files | Safe to run as checks; should fail fast on contract drift. |
| `readiness_nextcloud_golden_baseline_check.sh` | Readiness gate for nextcloud golden baseline check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_phase_13_2_public_session_retention_check.sh` | Readiness gate for phase 13 2 public session retention check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_preferences_evals_surface_check.sh` | Readiness gate for preferences evals surface check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_public_admin_policy_check.sh` | Readiness gate for public admin policy check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_public_ai_lab_overlay_check.sh` | Readiness gate for public ai lab overlay check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_required_integrations_check.sh` | Readiness gate for required integrations check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_required_providers_check.sh` | Readiness gate for required providers check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_run_history_compact_check.sh` | Readiness gate for run history compact check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_runbook_phases_8_12_check.sh` | Readiness gate for runbook phases 8 12 check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may read/write local runtime state; often reads/writes JSON | Safe to run as checks; should fail fast on contract drift. |
| `readiness_trello_public_visibility_check.sh` | Readiness gate for trello public visibility check. It checks that a repository, runtime, or deployment assumption still holds. | Use before a handoff, deploy, CI check, or repository cleanup that could violate an expected contract. | shell command; may accept CLI arguments; may read deployment env files | Safe to run as checks; should fail fast on contract drift. |

### Evaluation and benchmark runners

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `backfill_product_runtime_evals.py` | Utility script for backfill product runtime evals. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state | Generated outputs should remain local/ignored. |
| `benchmark_vl_router_multilayout.py` | Utility script for benchmark vl router multilayout. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `evaluate_checklist_regression.py` | Runs checklist regression evaluation against tracked evaluation fixtures. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `evaluate_evidence_cv_gold_set.py` | Runs the Evidence CV gold-set evaluation against tracked Phase 5 fixtures. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `import_phase8_eval_history.py` | Utility script for import phase8 eval history. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state | Generated outputs should remain local/ignored. |
| `run_all_phase_4_5_benchmarks.py` | Runs the all phase 4 5 benchmarks workflow. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_embedding_benchmark.py` | Runs embedding benchmark experiments and writes local/generated benchmark outputs. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_pdf_extraction_benchmark.py` | Runs PDF extraction benchmark experiments. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may write local benchmark outputs | Generated outputs should remain local/ignored. |
| `run_pdf_extraction_benchmark_en.py` | Runs the English PDF extraction benchmark path. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_phase5_structured_eval.py` | Runs the phase5 structured eval workflow. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_phase8_5_benchmark_matrix.py` | Runs the Phase 8.5 benchmark matrix using tracked eval configuration. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_phase8_agent_workflow_eval.py` | Runs the phase8 agent workflow eval workflow. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_phase8_live_evals.py` | Runs the phase8 live evals workflow. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_phase_4_5_benchmark_suite.py` | Runs the phase 4 5 benchmark suite workflow. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Generated outputs should remain local/ignored. |
| `run_synthetic_resume_benchmark.py` | Runs synthetic resume benchmark workflows; generated outputs should remain local/ignored. | Use for engineering/evaluation work, not for the AWS slim deployment itself. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Generated outputs should remain local/ignored. |

### Reporting and diagnostics

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `report_evidence_shadow_rollout.py` | Generates a diagnostic report for evidence shadow rollout from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_phase55_langchain_shadow_log.py` | Generates a diagnostic report for phase55 langchain shadow log from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_phase55_langgraph_shadow_log.py` | Generates a diagnostic report for phase55 langgraph shadow log from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_phase6_document_agent_log.py` | Generates a diagnostic report for phase6 document agent log from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_phase7_model_comparison_log.py` | Generates a diagnostic report for phase7 model comparison log from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_phase8_5_audit.py` | Generates a diagnostic report for phase8 5 audit from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state | Review script-specific assumptions before changing. |
| `report_phase8_5_closure.py` | Generates a diagnostic report for phase8 5 closure from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_phase8_5_decision_gate.py` | Summarizes Phase 8.5 decision-gate results from benchmark/eval outputs. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; may read/write local runtime state | Review script-specific assumptions before changing. |
| `report_phase8_eval_diagnosis.py` | Generates a diagnostic report for phase8 eval diagnosis from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_phase8_eval_store.py` | Generates a diagnostic report for phase8 eval store from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `report_vl_called_cases.py` | Generates a diagnostic report for vl called cases from stored logs, run history, or local artifacts. | Use after runs/evals have produced logs or stored outputs that need summarizing. | Python command; may accept CLI arguments; uses eval fixtures/configs; often reads/writes JSON | Review script-specific assumptions before changing. |

### Validation helpers

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `validate_aws_env_contract.py` | Validates the AWS environment contract. | Use when changing contracts, payloads, indexes, baselines, or deployment environment files. | Python command; may accept CLI arguments; may read deployment env files | Review script-specific assumptions before changing. |
| `validate_evidence_cv_indexing_payload.py` | Validates the evidence cv indexing payload contract, payload, or artifact. | Use when changing contracts, payloads, indexes, baselines, or deployment environment files. | Python command; may accept CLI arguments; uses eval fixtures/configs; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `validate_phase_4_5.py` | Validates the phase 4 5 contract, payload, or artifact. | Use when changing contracts, payloads, indexes, baselines, or deployment environment files. | Python command; often reads/writes JSON | Review script-specific assumptions before changing. |
| `validate_sanitized_functional_baseline.py` | Validates the sanitized functional baseline package. | Use when changing contracts, payloads, indexes, baselines, or deployment environment files. | Python command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |

### Maintenance and workspace utilities

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `auto_rollout_evidence_cv.py` | Utility script for auto rollout evidence cv. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; uses eval fixtures/configs; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `build_resume_component_bank.py` | Builds or assembles resume component bank support artifacts. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments | Review before running if it stages, restores, or generates local files. |
| `build_sanitized_functional_baseline.py` | Builds or assembles sanitized functional baseline support artifacts. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `capture_golden_surface_snapshot.py` | Utility script for capture golden surface snapshot. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `cleanup_public_session_overlays.py` | Utility script for cleanup public session overlays. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments | Review before running if it stages, restores, or generates local files. |
| `download_phase8_public_materials.py` | Utility script for download phase8 public materials. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `generate_admin_password_hash.py` | Generates an admin password hash for environment/configuration use. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments | Do not commit real secrets or generated credentials. |
| `generate_multilayout_resumes.py` | Generates multilayout resumes support data or fixtures. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `generate_synthetic_resumes_with_pdf.py` | Generates synthetic resumes with pdf support data or fixtures. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `preindex_public_reference_corpus.py` | Build the hidden public-reference corpus index used by fast Nextcloud demo imports. Run this once on the machine that has Ollama/Nextcloud credentials. The script writes a separate RAG JSON store, so the visible document library stays empty until a user imports documents from Nex | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `preindex_public_reference_corpus_page_routes.json` | Utility script for preindex public reference corpus page routes. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | JSON support file; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `restore_ai_lab_golden_state.sh` | Restores ai lab golden state local or baseline state. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | shell command; may accept CLI arguments; may read deployment env files; uses eval fixtures/configs; may write local benchmark outputs; may read/write local runtime state; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `restore_nextcloud_golden_baseline.sh` | Restores nextcloud golden baseline local or baseline state. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | shell command; may accept CLI arguments; may read deployment env files; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `select_phase5_ui_examples.py` | Utility script for select phase5 ui examples. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; uses eval fixtures/configs; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |
| `stage_functional_baseline_sources.py` | Stages selected local/source artifacts into the functional baseline workspace. | Use for local workspace preparation, generated fixtures, baseline staging, or restore flows. | Python command; may accept CLI arguments; uses eval fixtures/configs; may write local benchmark outputs; may read/write local runtime state; often reads/writes JSON | Review before running if it stages, restores, or generates local files. |

### Frontend, MCP, and surface validation

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `run_evidenceops_mcp_server.py` | Runs the evidenceops mcp server workflow. | Use when validating UI/API/MCP surfaces or frontend parity. | Python command | Review script-specific assumptions before changing. |
| `run_frontend_surface_validation.py` | Runs the frontend surface validation workflow. | Use when validating UI/API/MCP surfaces or frontend parity. | Python command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `run_frontend_surface_validation.sh` | Runs the frontend surface validation workflow. | Use when validating UI/API/MCP surfaces or frontend parity. | shell command | Review script-specific assumptions before changing. |
| `run_mcp_integration_validation.py` | Runs the mcp integration validation workflow. | Use when validating UI/API/MCP surfaces or frontend parity. | Python command; may accept CLI arguments; often reads/writes JSON | Review script-specific assumptions before changing. |
| `run_mcp_integration_validation.sh` | Runs the mcp integration validation workflow. | Use when validating UI/API/MCP surfaces or frontend parity. | shell command | Review script-specific assumptions before changing. |
| `run_ppt_creator_renderer_host.sh` | Runs the ppt creator renderer host workflow. | Use when validating UI/API/MCP surfaces or frontend parity. | shell command | Review script-specific assumptions before changing. |
| `run_presentation_export_smoke_suite.py` | Runs the presentation export smoke suite workflow. | Use when validating UI/API/MCP surfaces or frontend parity. | Python command; may accept CLI arguments; often reads/writes JSON | Review script-specific assumptions before changing. |
| `smoke_ai_lab_payloads.py` | Runs a smoke test for ai lab payloads. | Use when validating UI/API/MCP surfaces or frontend parity. | Python command; may accept CLI arguments; often reads/writes JSON | Review script-specific assumptions before changing. |
| `smoke_frontend_docker_workflows_ui.sh` | Runs a smoke test for frontend docker workflows ui. | Use when validating UI/API/MCP surfaces or frontend parity. | shell command; often reads/writes JSON | Review script-specific assumptions before changing. |
| `smoke_frontend_surface_payloads.py` | Runs a smoke test for frontend surface payloads. | Use when validating UI/API/MCP surfaces or frontend parity. | Python command; may accept CLI arguments; may read/write local runtime state | Review script-specific assumptions before changing. |
| `smoke_frontend_ui_parity_local_vs_docker.sh` | Runs a smoke test for frontend ui parity local vs docker. | Use when validating UI/API/MCP surfaces or frontend parity. | shell command; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |

### Analysis and comparison helpers

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `compare_pdf_extraction_paths.py` | Compares pdf extraction paths outputs or configurations. | Use only when working on the related subsystem. | Python command; may accept CLI arguments | Review script-specific assumptions before changing. |
| `compare_phase_4_5_configs.py` | Compares phase 4 5 configs outputs or configurations. | Use only when working on the related subsystem. | Python command; may accept CLI arguments; often reads/writes JSON | Review script-specific assumptions before changing. |
| `measure_surface_latency.sh` | Utility script for measure surface latency. | Use only when working on the related subsystem. | shell command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `render_phase_4_5_charts.py` | Utility script for render phase 4 5 charts. | Use only when working on the related subsystem. | Python command; often reads/writes JSON | Review script-specific assumptions before changing. |

### Other utilities

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `ai_lab_shell_lib.sh` | Utility script for ai lab shell lib. | Use only when working on the related subsystem. | shell command; may accept CLI arguments; often reads/writes JSON | Review script-specific assumptions before changing. |
| `backfill_evidenceops_history.py` | Utility script for backfill evidenceops history. | Use only when working on the related subsystem. | Python command; may accept CLI arguments; may read/write local runtime state | Review script-specific assumptions before changing. |
| `demo_phase95_evidenceops_mcp.py` | Utility script for demo phase95 evidenceops mcp. | Use only when working on the related subsystem. | Python command; often reads/writes JSON | Review script-specific assumptions before changing. |
| `resume_dataset_splitter_v2.py` | Utility script for resume dataset splitter v2. | Use only when working on the related subsystem. | Python command; may accept CLI arguments; often reads/writes JSON | Review script-specific assumptions before changing. |
| `run_ai_lab_validation.py` | Runs the ai lab validation workflow. | Use only when working on the related subsystem. | Python command; may accept CLI arguments; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `run_ai_lab_validation.sh` | Runs the ai lab validation workflow. | Use only when working on the related subsystem. | shell command | Review script-specific assumptions before changing. |
| `run_candidate_review_validation.py` | Runs the candidate review validation workflow. | Use only when working on the related subsystem. | Python command; may accept CLI arguments; often reads/writes JSON | Review script-specific assumptions before changing. |
| `run_document_review_findings_experiment.py` | Runs the document review findings experiment workflow. | Use only when working on the related subsystem. | Python command; uses eval fixtures/configs; may write local benchmark outputs; often reads/writes JSON | Review script-specific assumptions before changing. |
| `smoke_docker_policy_comparison_write.sh` | Runs a smoke test for docker policy comparison write. | Use only when working on the related subsystem. | shell command; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |
| `smoke_docker_workflow_write.sh` | Runs a smoke test for docker workflow write. | Use only when working on the related subsystem. | shell command; may read/write local runtime state; often reads/writes JSON | Review script-specific assumptions before changing. |

## Reviewer notes

A recruiter or technical reviewer should not need to inspect every script. The important signal is that the project has:

- a stable deployment path;
- explicit readiness gates;
- repeatable evaluation and benchmark tooling;
- reporting utilities for engineering decisions;
- a clear separation between current product, eval workspace, and legacy/deferred material.

When in doubt, treat `build_deployment_bundle.sh`, `deploy_aws_slim.sh`, `smoke_aws_slim.sh`, and `run_local_docker.sh` as the current operational path.
