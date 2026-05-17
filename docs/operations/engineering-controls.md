# Engineering Controls

This document records the operational controls that keep the current product safe, inspectable, and reproducible.

## Public/Admin Boundary

The product has two operating modes:

- public sessions use isolated behavior and limited execution paths;
- admin sessions can access global runtime state, credentials, private analytics, and external publishing.

This boundary lets the same product run as a public demo or a private engineering/admin tool without changing the core workflow code.

## Runtime State Policy

The Product API owns runtime state. The frontend calls API endpoints and does not mount runtime folders directly.

Mounted roots:

- `/app/baseline` - read-only functional baseline material;
- `/app/runtime` - logs, cache, RAG state, preferences, telemetry, and runtime state;
- `/app/artifacts` - decks, previews, exports, and generated outputs;
- `/app/users` - public session overlays and admin state.

## Execution Controls

Public workflow execution is controlled by:

- rolling execution quotas;
- visible quota UI;
- in-flight execution guard;
- public deck-generation rate limit;
- admin-only publish and credential actions.

These controls reduce accidental overload and prevent a public session from mutating shared global state.

Primary references:

- `src/product/public_execution_quota.py`
- `src/product/public_execution_gate.py`
- `src/product/deck_rate_limit.py`
- `docs/ops/PUBLIC_EXECUTION_QUOTA.md`
- `docs/ops/PUBLIC_EXECUTION_GATE.md`
- `docs/ops/PUBLIC_DECK_RATE_LIMIT.md`

## Credential Controls

External delivery credentials are optional and admin-gated. The credential store exists outside source control and is mounted as runtime state.

Credential-dependent features include:

- Nextcloud/WebDAV import and sync;
- Trello publish;
- Notion publish;
- provider keys for hosted AI endpoints.

Primary references:

- `src/storage/secret_store.py`
- `.env.aws.example`
- `.env.docker.example`
- `docs/deployment/aws-deploy.md`

## Readiness And Smoke Gates

The repository separates active product validation from legacy historical validation.

Current validation areas:

- local Docker compose config;
- AWS compose config;
- multi-environment contract checks;
- current product test gate;
- AWS smoke path;
- dependency contract validation.

Primary references:

- `README.md`
- `tests/README.md`
- `scripts/README.md`
- `scripts/run_current_test_gate.sh`
- `scripts/readiness_multi_environment_contract_check.sh`
- `scripts/smoke_aws.sh`
- `scripts/run_local_docker.sh`

## Observability

The product keeps evidence about what ran and why:

- run history;
- workflow inspector;
- telemetry logs;
- Actions DB;
- runtime timeline;
- benchmark and eval results;
- private usage analytics for admin review.

Primary references:

- `src/product/telemetry.py`
- `src/storage/product_usage_events.py`
- `frontend/src/components/usage/UsageTelemetryProvider.tsx`
- `frontend/src/pages/AdminUsagePage.tsx`
- `frontend/src/pages/RuntimeObservabilityPage.tsx`
- `frontend/src/pages/WorkflowInspectorPage.tsx`
- `frontend/src/pages/BenchmarksPage.tsx`
- `frontend/src/pages/EvalsDiagnosisPage.tsx`

## Backups And Restore

Runtime and baseline state can be backed up and restored without changing container images. This supports clean rebuilds, AWS redeploys, and repeatable demo baselines.

Primary references:

- `docs/operations/backup-and-restore.md`
- `docs/operations/LOCAL_BACKUP_REGISTER.md`
- `docs/deployment/AI_LAB_GOLDEN_STATE_RESTORE.md`
- `docs/deployment/NEXTCLOUD_GOLDEN_BASELINE_RESTORE.md`
