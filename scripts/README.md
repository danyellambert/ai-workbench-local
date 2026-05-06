# Scripts

This directory contains operational commands, readiness checks, evaluation runners, reporting utilities, and maintenance helpers for AI Decision Studio.

For reviewers: this is not the main product surface. Start with `../README.md`, `../docs/`, and the current deployment docs first. Use this file when you want to understand how the repository is operated, validated, benchmarked, and packaged.

## What matters first

| Script | What it does |
| --- | --- |
| `build_deployment_bundle.sh` | Builds the clean application bundle used to transfer the app to an AWS/local deployment target. |
| `deploy_aws_slim.sh` | Starts or refreshes the current AWS slim deployment stack on the target host. |
| `smoke_aws_slim.sh` | Checks whether the AWS slim deployment responds correctly after it starts. |
| `run_local_docker.sh` | Executes the local Docker workflow for the product stack. |
| `run_local_dev.sh` | Runs or checks local host development mode outside the AWS target host. |
| `readiness_multi_environment_contract_check.sh` | Checks the local/Docker/AWS environment contract and protects cross-environment assumptions. |
| `readiness_final_deploy_check.sh` | Executes the final deployment-readiness gate for the repository. |

`build_oracle_deployment_bundle.sh` remains as a backward-compatible wrapper for the older Oracle-named bundle command. Oracle-only operational material lives under `../legacy/`.

## How to use this catalog

- **Deployment scripts** are the current operational path and should stay stable.
- **Readiness scripts** are guardrails that fail fast when a repo/runtime/deployment contract drifts.
- **Evaluation and benchmark scripts** are engineering tools. They are useful for review, but they are not required for the AWS slim deployment.
- **Reporting scripts** summarize stored logs, benchmark outputs, or eval stores.
- **Maintenance scripts** may create, restore, or stage local files. Review them before running.

## Repository boundaries

- Active deployment scripts stay at the root of `scripts/` for compatibility with docs, CI, and local workflows.
- Oracle-only historical scripts live in `../legacy/scripts/oracle/`.
- Tracked eval fixtures and benchmark workspace documentation live in `../evals/`.
- Generated reports, local benchmark runs, local PDF corpora, caches, secrets, and `.DS_Store` files should not be committed.
- Do not move or rename scripts referenced by CI, deployment docs, or local runbooks without adding a compatibility wrapper.

## Complete script catalog

Every top-level tracked script/support file in this directory is listed below.

### Deployment and local runtime

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `build_deployment_bundle.sh` | Builds the clean application bundle used to transfer the app to an AWS/local deployment target. | Use before copying the application package to a host or validating what the deployment bundle contains. | Reads the repository tree and writes a sanitized tarball/report. | Current packaging path; keep stable. |
| `build_oracle_deployment_bundle.sh` | Keeps the older Oracle-named bundle command working while delegating to the generic deployment bundle builder. | Use only when older notes or commands still call the Oracle-named entry point. | Delegates to the generic builder and preserves older environment variable names. | Compatibility wrapper; keep until legacy references are fully retired. |
| `deploy_aws_slim.sh` | Starts or refreshes the current AWS slim deployment stack on the target host. | Use on the AWS host after the app bundle and `.env.aws` are in place. | Reads AWS env settings and invokes the Docker Compose AWS slim stack. | Current AWS deployment path; keep stable. |
| `run_local_dev.sh` | Runs or checks local host development mode outside the AWS target host. | Use for local development and quick host-side validation. | Reads local env/config and executes local development checks. | Current local dev path; keep stable. |
| `run_local_docker.sh` | Executes the local Docker workflow for the product stack. | Use when validating the app locally through Docker rather than directly on the host. | Reads local Docker env/config and starts the compose-based local workflow. | Current local Docker path; keep stable. |
| `smoke_aws_slim.sh` | Checks whether the AWS slim deployment responds correctly after it starts. | Use after `deploy_aws_slim.sh` or after host-level changes. | Reads base URL/env settings and performs smoke requests. | Current AWS smoke path; keep stable. |

### Readiness gates

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `readiness_admin_session_isolation_check.sh` | Checks that admin/session isolation expectations are still represented in the repo and runtime contracts. | Use before publication or deployment changes that may affect admin/session behavior. | Reads repository files and expected markers; exits nonzero on drift. | Useful as a guardrail before handoff. |
| `readiness_ai_lab_content_check.sh` | Checks that AI Lab content expected by the current product surface is present and consistent. | Use when changing AI Lab copy, examples, fixtures, or product-facing lab material. | Reads repo/runtime content markers and validates expected files. | Helps prevent incomplete AI Lab handoffs. |
| `readiness_ai_lab_golden_state_check.sh` | Checks the AI Lab golden-state restore/validation assumptions. | Use before relying on a golden-state restore or publishing AI Lab demo state. | Reads golden-state paths, eval assets, and runtime markers. | Run after restore-related changes. |
| `readiness_artifacts_compact_check.sh` | Checks that artifact surfaces remain compact and suitable for public/reviewer use. | Use when changing artifact listing, run history, or generated output presentation. | Reads artifact/run-history conventions and expected compactness rules. | Prevents noisy or oversized artifact surfaces. |
| `readiness_candidate_review_contract_check.sh` | Checks the Candidate Review contract between expected inputs, outputs, and UI/backend assumptions. | Use when changing Candidate Review docs, tests, or data contracts. | Reads contract markers and likely sample payload expectations. | Protects a product-facing workflow. |
| `readiness_evidenceops_ui_cache_check.sh` | Checks EvidenceOps UI/cache assumptions so stale or missing cache state is visible. | Use when changing EvidenceOps UI, cache files, or related runtime expectations. | Reads cache/runtime markers and EvidenceOps references. | Useful before demos or handoff. |
| `readiness_final_deploy_check.sh` | Executes the final deployment-readiness gate for the repository. | Use as a last check before deploy, handoff, or publication. | Aggregates expected deployment/repo readiness assumptions. | High-signal pre-handoff check. |
| `readiness_multi_environment_contract_check.sh` | Checks the local/Docker/AWS environment contract and protects cross-environment assumptions. | Use when changing env files, compose files, bundle logic, or deployment docs. | Reads env examples, deployment docs, and script contracts. | Important cross-environment guardrail. |
| `readiness_nextcloud_golden_baseline_check.sh` | Checks Nextcloud golden-baseline assumptions and expected restore/import references. | Use when changing Nextcloud baseline, restore docs, or related integration material. | Reads baseline paths, docs, and integration markers. | Relevant to integration/demo state. |
| `readiness_phase_13_2_public_session_retention_check.sh` | Checks public session-retention assumptions from the later deployment-hardening work. | Use before changing public session, retention, cleanup, or admin/session policy behavior. | Reads policy/session markers and related runtime expectations. | Kept active because it is public-session related, not Oracle-only. |
| `readiness_preferences_evals_surface_check.sh` | Checks the Preferences/Evals product surface assumptions. | Use when changing preferences, eval summaries, or AI Lab eval visibility. | Reads product/eval surface markers and expected references. | Protects reviewer-facing eval surfaces. |
| `readiness_public_admin_policy_check.sh` | Checks that public admin policy assumptions remain explicit and safe. | Use when changing admin access, public mode, or publication settings. | Reads policy markers and expected admin visibility constraints. | Important for safe public demos. |
| `readiness_public_ai_lab_overlay_check.sh` | Checks that public AI Lab overlay behavior remains aligned with the intended public surface. | Use when changing AI Lab overlay, demo mode, or public UI controls. | Reads overlay-related markers and expected public-mode behavior. | Prevents accidental private/internal UI exposure. |
| `readiness_required_integrations_check.sh` | Checks that required integration expectations are documented/configured. | Use when changing integration setup, demo dependencies, or public handoff notes. | Reads integration markers and expected required-provider references. | Good pre-review integration guardrail. |
| `readiness_required_providers_check.sh` | Checks that required model/provider assumptions are represented. | Use when changing provider configuration, env examples, or model-routing docs. | Reads provider/env markers and expected configuration references. | Prevents provider drift. |
| `readiness_run_history_compact_check.sh` | Checks that run-history output remains compact and suitable for UI/reviewer display. | Use when changing run history, artifacts panels, or stored workflow output presentation. | Reads run-history paths/markers and compactness assumptions. | Prevents noisy demo surfaces. |
| `readiness_runbook_phases_8_12_check.sh` | Checks that the runbook material for phases 8–12 remains coherent. | Use when editing historical runbooks or phase documentation. | Reads runbook docs and expected phase references. | Protects documentation continuity. |
| `readiness_trello_public_visibility_check.sh` | Checks Trello/public visibility assumptions. | Use when changing Trello integration, public visibility docs, or external target references. | Reads visibility/integration markers and expected public-state references. | Useful before public-facing demos. |

### Evaluation and benchmark runners

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `backfill_product_runtime_evals.py` | Backfills product runtime evaluation records from existing runtime/eval data. | Use when the eval store needs historical runtime records reconstructed. | Reads runtime/eval state and writes normalized eval records. | Generated outputs should remain local or intentionally staged. |
| `benchmark_vl_router_multilayout.py` | Benchmarks the visual-language routing path across multiple resume/document layouts. | Use when comparing VL/OCR behavior across synthetic or varied layouts. | Reads eval fixtures/local documents and writes benchmark outputs. | Benchmark outputs should remain ignored/local. |
| `evaluate_checklist_regression.py` | Runs checklist regression evaluation against tracked checklist fixtures. | Use after changing checklist extraction, structured output logic, or eval fixtures. | Reads tracked eval fixtures and writes/prints evaluation results. | Engineering eval, not required for AWS deploy. |
| `evaluate_evidence_cv_gold_set.py` | Runs Evidence CV evaluation against the tracked gold-set fixtures. | Use after changing CV extraction, evidence indexing, or Candidate Review evidence logic. | Reads `evals/phase5/fixtures` and writes/prints score details. | Engineering eval, not required for AWS deploy. |
| `import_phase8_eval_history.py` | Imports prior Phase 8 eval history into the current eval-store format. | Use when migrating or replaying older eval history. | Reads historical eval outputs and writes normalized eval records. | Do not commit generated migration outputs by default. |
| `run_all_phase_4_5_benchmarks.py` | Executes the full Phase 4.5 benchmark group across extraction and retrieval scenarios. | Use for engineering benchmark sweeps, not normal product deployment. | Reads benchmark configs/corpora and writes local benchmark runs. | Can be expensive/noisy; keep outputs ignored. |
| `run_document_review_findings_experiment.py` | Runs an experiment around document-review findings behavior. | Use when evaluating findings extraction or document-review workflow quality. | Reads local/eval inputs and writes experiment outputs. | Experimental outputs should remain local. |
| `run_embedding_benchmark.py` | Runs embedding-model and retrieval benchmark experiments. | Use when comparing embedding models, chunking, context windows, or retrieval tuning. | Reads benchmark inputs and writes local benchmark run artifacts. | Benchmark outputs should remain ignored. |
| `run_pdf_extraction_benchmark.py` | Runs PDF extraction benchmark experiments. | Use when comparing PDF extraction paths or parser behavior. | Reads benchmark PDFs/local corpora and writes benchmark results. | Local corpora/results should not be committed. |
| `run_pdf_extraction_benchmark_en.py` | Executes the English PDF extraction benchmark workflow. | Use when validating English-document extraction behavior. | Reads benchmark PDF fixtures/corpora and writes local benchmark outputs. | Benchmark outputs stay local/ignored. |
| `run_phase5_structured_eval.py` | Runs Phase 5 structured-output evaluation. | Use after changing structured extraction, summarization, checklist, or CV workflows. | Reads Phase 5 eval fixtures and writes local eval reports. | Generated reports should remain ignored unless curated. |
| `run_phase8_5_benchmark_matrix.py` | Executes the Phase 8.5 benchmark matrix from tracked configuration. | Use when evaluating benchmark-matrix scenarios and decision-gate inputs. | Reads `evals/phase8/configs` and writes benchmark-run outputs. | Outputs should remain local/ignored. |
| `run_phase8_agent_workflow_eval.py` | Runs Phase 8 agent-workflow evaluation cases. | Use when changing agent workflow behavior or eval fixtures. | Reads tracked Phase 8 workflow cases and writes eval results. | Engineering eval only. |
| `run_phase8_live_evals.py` | Runs live Phase 8 evaluations. | Use only when live provider/runtime dependencies are intentionally available. | Reads live env/provider settings and writes eval results. | Avoid accidental cost/provider calls. |
| `run_phase_4_5_benchmark_suite.py` | Executes the Phase 4.5 benchmark suite for retrieval and extraction validation. | Use for full retrieval/extraction benchmark validation. | Reads benchmark inputs and writes local benchmark outputs. | Can be slow; keep generated artifacts ignored. |
| `run_synthetic_resume_benchmark.py` | Runs synthetic-resume benchmark workflows. | Use when testing CV parsing/evidence behavior against generated resumes. | Reads/generated synthetic resumes and writes benchmark reports. | Generated benchmark data should remain local/ignored. |

### Reporting and diagnostics

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `report_evidence_shadow_rollout.py` | Summarizes Evidence CV shadow-rollout results. | Use after shadow rollout/eval runs to inspect adoption, deltas, and candidate outcomes. | Reads stored rollout/eval logs and prints/writes a report. | Report inputs should be sanitized before sharing. |
| `report_phase55_langchain_shadow_log.py` | Summarizes Phase 5.5 LangChain shadow-log results. | Use when reviewing framework-evolution experiments. | Reads shadow logs and emits a concise report. | Historical engineering diagnostic. |
| `report_phase55_langgraph_shadow_log.py` | Summarizes Phase 5.5 LangGraph shadow-log results. | Use when reviewing LangGraph workflow experiments. | Reads shadow logs and emits a concise report. | Historical engineering diagnostic. |
| `report_phase6_document_agent_log.py` | Summarizes Phase 6 document-agent logs. | Use when reviewing document-agent workflow behavior. | Reads stored document-agent logs and emits a report. | Historical/eval diagnostic. |
| `report_phase7_model_comparison_log.py` | Summarizes Phase 7 model-comparison logs. | Use after model comparison runs. | Reads model-comparison logs and writes/prints summary metrics. | Useful for model-selection evidence. |
| `report_phase8_5_audit.py` | Produces the Phase 8.5 audit summary. | Use when reviewing Phase 8.5 benchmark/eval readiness. | Reads Phase 8.5 eval/benchmark artifacts and reports audit status. | Engineering diagnostic. |
| `report_phase8_5_closure.py` | Produces Phase 8.5 closure reporting. | Use when closing a benchmark/eval workstream or checking completion status. | Reads Phase 8.5 result artifacts and emits closure summary. | Useful for handoff evidence. |
| `report_phase8_5_decision_gate.py` | Summarizes Phase 8.5 decision-gate results. | Use after benchmark-matrix runs to decide pass/fail or next action. | Reads benchmark/eval outputs and emits gate status. | Decision-support report. |
| `report_phase8_eval_diagnosis.py` | Diagnoses Phase 8 eval-store/result health. | Use when eval results look incomplete, stale, or inconsistent. | Reads eval store/history and prints diagnostic findings. | Engineering troubleshooting helper. |
| `report_phase8_eval_store.py` | Summarizes the Phase 8 eval store. | Use when reviewing what eval records are available. | Reads eval-store files and emits summary output. | Useful for audit/handoff. |
| `report_vl_called_cases.py` | Reports cases where the visual-language path was called. | Use when auditing VL/OCR routing and fallback behavior. | Reads stored case/run records and summarizes VL usage. | Useful for OCR/VL cost and quality review. |

### Validation helpers

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `validate_aws_env_contract.py` | Checks the AWS environment contract file/variables. | Use when editing `.env.aws`, env examples, or AWS deployment docs. | Reads env settings and validates required keys/contracts. | Prevents deployment drift. |
| `validate_evidence_cv_indexing_payload.py` | Checks Evidence CV indexing payload structure. | Use after changing evidence indexing, CV extraction payloads, or related fixtures. | Reads payload JSON/fixtures and validates required fields. | Protects Candidate Review/evidence workflows. |
| `validate_phase_4_5.py` | Checks Phase 4.5 validation artifacts and expected benchmark structure. | Use when reviewing Phase 4.5 benchmark/eval evidence. | Reads validation inputs/results and exits on mismatch. | Historical benchmark validation helper. |
| `validate_sanitized_functional_baseline.py` | Checks the sanitized functional baseline package. | Use before publishing or sharing a baseline package. | Reads baseline files and validates that forbidden/private content is absent. | Important publication-safety check. |

### Maintenance and workspace utilities

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `ai_lab_shell_lib.sh` | Shared shell helpers used by AI Lab-related scripts. | Source/use indirectly from shell scripts that need common AI Lab helper behavior. | Defines reusable shell functions and constants. | Library file; avoid running directly. |
| `auto_rollout_evidence_cv.py` | Automates Evidence CV rollout/shadow-rollout support steps. | Use when promoting or comparing Evidence CV behavior across staged data. | Reads eval/runtime artifacts and writes rollout support output. | Review output before committing anything. |
| `backfill_evidenceops_history.py` | Backfills EvidenceOps history from existing local/runtime artifacts. | Use when historical EvidenceOps records need to be reconstructed. | Reads local history/runtime files and writes normalized records. | Generated history should be reviewed before sharing. |
| `build_resume_component_bank.py` | Builds a component bank for synthetic resume generation. | Use before generating varied synthetic resume datasets. | Reads component definitions and writes generated support data. | Generated artifacts should be controlled. |
| `build_sanitized_functional_baseline.py` | Builds the sanitized functional baseline package. | Use when preparing a safe baseline for handoff or publication. | Reads selected runtime/source artifacts and writes a sanitized baseline. | Check output with the sanitizer validator. |
| `capture_golden_surface_snapshot.py` | Captures a golden snapshot of the product/UI surface. | Use before/after UI changes to preserve a known-good reference state. | Reads product endpoints/runtime state and writes snapshot artifacts. | Keep generated snapshots curated. |
| `cleanup_public_session_overlays.py` | Cleans public-session overlay state. | Use when stale public/demo session overlays need removal. | Reads/removes overlay records according to policy. | Check target environment before running. |
| `download_phase8_public_materials.py` | Downloads or prepares public materials used by Phase 8 eval/reference flows. | Use when rebuilding local public-material corpora. | Fetches/writes local material artifacts. | Avoid committing downloaded payloads unless curated. |
| `generate_admin_password_hash.py` | Generates an admin password hash for configuration. | Use when creating a new admin credential hash for env/config use. | Reads password input and prints/writes a hash. | Do not commit real credentials. |
| `generate_multilayout_resumes.py` | Generates multi-layout resume samples for CV/OCR testing. | Use when building synthetic resume corpora for evaluation. | Writes generated resume data/PDFs. | Generated corpora should stay ignored/local unless curated. |
| `generate_synthetic_resumes_with_pdf.py` | Generates synthetic resumes with PDF output. | Use when building resume PDFs for parsing/evidence tests. | Writes synthetic resumes and PDFs. | Do not commit large generated corpora by default. |
| `preindex_public_reference_corpus.py` | Builds the hidden public-reference corpus index used by fast demo imports. | Use once on a machine with required local/provider credentials. | Reads public reference material and writes a separate RAG/index store. | Generated index should remain local/runtime state. |
| `preindex_public_reference_corpus_page_routes.json` | Maps public-reference corpus pages/routes for preindexing. | Use as support data for `preindex_public_reference_corpus.py`. | Static JSON mapping consumed by the preindex script. | Support file, not an executable command. |
| `restore_ai_lab_golden_state.sh` | Restores AI Lab golden-state files/runtime expectations. | Use when local AI Lab state needs to return to a known baseline. | Reads golden-state artifacts and writes/restores local runtime state. | Check target paths before running. |
| `restore_nextcloud_golden_baseline.sh` | Restores Nextcloud golden-baseline state. | Use when rebuilding the expected Nextcloud demo/baseline state. | Reads baseline artifacts and writes/restores local Nextcloud state. | Check target service/state before running. |
| `resume_dataset_splitter_v2.py` | Splits resume datasets into controlled subsets. | Use when preparing train/eval/demo subsets for resume parsing work. | Reads resume dataset files and writes split outputs. | Generated splits should be documented if committed. |
| `select_phase5_ui_examples.py` | Selects Phase 5 examples suitable for UI/demo presentation. | Use when curating structured-output examples for the interface. | Reads Phase 5 eval outputs/fixtures and writes selected example metadata. | Curated outputs should be reviewed. |
| `stage_functional_baseline_sources.py` | Stages selected source/runtime artifacts into the functional baseline workspace. | Use when preparing or refreshing a baseline package. | Reads selected repository/local paths and writes baseline staging output. | Be careful not to stage private/heavy artifacts. |

### Frontend, MCP, and surface validation

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `run_ai_lab_validation.py` | Runs AI Lab validation from Python. | Use when validating AI Lab backend/API behavior. | Reads product endpoints/fixtures and returns validation results. | Good focused surface check. |
| `run_ai_lab_validation.sh` | Shell wrapper for AI Lab validation. | Use when a shell entry point is more convenient than the Python command. | Delegates to AI Lab validation logic. | Wrapper; keep behavior aligned with Python command. |
| `run_candidate_review_validation.py` | Validates Candidate Review behavior. | Use after changing Candidate Review flow, payloads, or evidence presentation. | Reads sample inputs/endpoints and reports validation status. | Product-facing validation. |
| `run_evidenceops_mcp_server.py` | Starts the EvidenceOps MCP server. | Use when validating MCP integration or local EvidenceOps tool access. | Starts a local MCP server process. | Operational/dev server helper. |
| `run_frontend_surface_validation.py` | Validates frontend surface expectations from Python. | Use after frontend/API surface changes. | Reads/queries frontend-related routes and checks expected behavior. | Surface parity guard. |
| `run_frontend_surface_validation.sh` | Shell wrapper for frontend surface validation. | Use in shell/CI-style flows for frontend surface checks. | Delegates to frontend validation logic. | Wrapper; keep aligned with Python command. |
| `run_mcp_integration_validation.py` | Validates MCP integration behavior. | Use when changing MCP server/client integration paths. | Starts/checks MCP-related behavior and outputs validation status. | Integration-focused check. |
| `run_mcp_integration_validation.sh` | Shell wrapper for MCP integration validation. | Use in shell/CI-style MCP validation flows. | Delegates to MCP validation logic. | Wrapper; keep aligned with Python command. |
| `run_ppt_creator_renderer_host.sh` | Starts the PowerPoint creator renderer host. | Use when testing presentation rendering/export support locally. | Starts renderer host process/config. | Development helper, not AWS slim deploy. |
| `run_presentation_export_smoke_suite.py` | Runs smoke tests for presentation export. | Use after changing executive deck or export rendering code. | Reads presentation/export fixtures and reports smoke status. | Product-adjacent validation. |
| `smoke_ai_lab_payloads.py` | Smoke-tests AI Lab payload shapes. | Use after changing AI Lab API payloads or examples. | Reads sample payloads and checks accepted/expected structure. | Fast payload contract check. |
| `smoke_docker_policy_comparison_write.sh` | Smoke-tests Docker write behavior for policy comparison workflows. | Use when checking Dockerized workflow write paths. | Executes a small write-path smoke in Docker context. | Keep generated output local. |
| `smoke_docker_workflow_write.sh` | Smoke-tests Docker workflow write behavior. | Use when validating that Docker workflows can write required runtime outputs. | Executes a small workflow write-path check. | Keep generated output local. |
| `smoke_frontend_docker_workflows_ui.sh` | Smoke-tests frontend UI workflow behavior in Docker. | Use after Docker/frontend UI workflow changes. | Queries or drives frontend Docker workflow surface. | Good local Docker UI smoke. |
| `smoke_frontend_surface_payloads.py` | Smoke-tests frontend surface payloads. | Use when API/frontend payload contracts change. | Reads or requests payloads and checks structure. | Fast product-surface payload check. |
| `smoke_frontend_ui_parity_local_vs_docker.sh` | Compares local vs Docker frontend UI parity. | Use when checking that local and Docker surfaces remain aligned. | Runs local/Docker parity checks and reports differences. | Useful before handoff. |

### Analysis and comparison helpers

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `compare_pdf_extraction_paths.py` | Compares PDF extraction paths or parser outputs. | Use when deciding between extraction implementations or validating parser drift. | Reads comparable extraction outputs and reports differences. | Engineering comparison helper. |
| `compare_phase_4_5_configs.py` | Compares Phase 4.5 benchmark/eval configurations. | Use when reviewing config drift between benchmark runs. | Reads JSON/config files and reports differences. | Helps preserve benchmark reproducibility. |
| `measure_surface_latency.sh` | Measures latency for selected product/API surfaces. | Use when checking response time after deploy or performance changes. | Executes timing requests/commands and prints latency data. | Performance diagnostic. |
| `render_phase_4_5_charts.py` | Renders charts from Phase 4.5 benchmark results. | Use when turning benchmark outputs into reviewable visuals. | Reads result JSON/CSV and writes chart artifacts. | Generated charts should be curated before commit. |

### Other utilities

| Script | Purpose | When to use | Inputs/outputs | Notes |
| --- | --- | --- | --- | --- |
| `demo_phase95_evidenceops_mcp.py` | Demonstrates the Phase 9.5 EvidenceOps MCP flow. | Use as a manual demo/reference for EvidenceOps MCP behavior. | Runs a focused MCP demonstration path. | Historical/demo helper; not core deploy. |

## Reviewer notes

A recruiter or technical reviewer should not need to inspect every script. The important signal is that the project has:

- a stable deployment path;
- explicit readiness gates;
- repeatable evaluation and benchmark tooling;
- reporting utilities for engineering decisions;
- a clear separation between current product, eval workspace, and legacy/deferred material.

When in doubt, treat `build_deployment_bundle.sh`, `deploy_aws_slim.sh`, `smoke_aws_slim.sh`, and `run_local_docker.sh` as the current operational path.
