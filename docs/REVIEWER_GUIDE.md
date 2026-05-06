# Reviewer Guide

This guide is the short path for recruiters, interviewers, and technical reviewers.

AI Decision Studio is a product-oriented AI workbench with a React/Vite frontend, a Python product API, Docker/local deployment support, and an AWS slim deployment path. The repository also contains historical evaluation, benchmark, and legacy UI material. Those are documented, but they are not the primary validation path for the current product.

## 5-minute review path

### 1. Start with the product surface

Read the root [`README.md`](../README.md) first for the product overview, stack, and quickstart.

Then inspect:

- [`docs/README.md`](README.md) for the documentation map.
- [`tests/README.md`](../tests/README.md) for the Python test status and current gate.
- [`scripts/README.md`](../scripts/README.md) for operational scripts.
- [`docs/deployment/README.md`](deployment/README.md) for deployment docs.

### 2. Run the current green validation path

These commands are the current reviewer-friendly validation path.

```bash
npm --prefix frontend run test
npm --prefix frontend run build
scripts/run_current_test_gate.sh
scripts/readiness_multi_environment_contract_check.sh
```

Expected current status:

- Frontend Vitest: 10 files / 23 tests pass.
- Frontend build: passes; known warning for large bundle chunk.
- Current Python test gate: 71 tests pass.
- Multi-environment readiness: local/Docker/AWS contract passes.

### 3. Understand what is not the gate

Do **not** use the full Python discovery command as the presentation gate today:

```bash
python -m unittest discover
```

The broad historical suite mixes current product tests, live/provider tests, legacy Streamlit/Gradio checks, EvidenceOps/MCP integration checks, and eval/benchmark history. It is documented in [`tests/README.md`](../tests/README.md), but it is not the current green gate.

### 4. Review the active operational commands

The most important scripts are:

```bash
scripts/run_current_test_gate.sh
scripts/readiness_multi_environment_contract_check.sh
scripts/build_deployment_bundle.sh
scripts/deploy_aws_slim.sh
scripts/smoke_aws_slim.sh
scripts/run_local_docker.sh
scripts/run_local_dev.sh
```

The full script catalog is in [`scripts/README.md`](../scripts/README.md).

### 5. Review deployment posture

The current maintained deployment posture is local/Docker/AWS. Oracle-specific material was moved to legacy documentation and is not the current deployment path.

Useful docs:

- [`docs/deployment/README.md`](deployment/README.md)
- [`docs/deployment/AWS_FRESH_EC2_BOOTSTRAP.md`](deployment/AWS_FRESH_EC2_BOOTSTRAP.md)
- [`docs/deployment/REDEPLOY_FAST_PATH.md`](deployment/REDEPLOY_FAST_PATH.md)
- [`docs/deployment/MULTI_ENVIRONMENT_CONTRACT.md`](deployment/MULTI_ENVIRONMENT_CONTRACT.md)

## Repository boundaries

The current cleanup has intentionally avoided functional product changes.

Do not treat repository organization commits as product behavior changes. The conservative boundary is:

- no route/schema/API behavior changes;
- no frontend product behavior changes;
- no Docker/AWS behavior changes;
- no runtime payload removal in this phase.

## Runtime and generated artifacts

The repository still contains runtime/baseline material used as historical payload/baseline context. That cleanup is intentionally deferred. The current goal is to make the repository understandable and reviewable without risking the working product or deployment path.

Generated/local artifacts should stay ignored. Historical eval and benchmark material is documented separately from the current product validation path.

## What to tell a reviewer

A concise reviewer summary:

> The product runs locally, in Docker, and on AWS. The current validation path is frontend Vitest, frontend build, the current Python test gate, and the multi-environment readiness check. The broader Python unittest inventory is preserved and documented, but it includes legacy/live/provider/eval tests and is not the current presentation gate.

## Current reviewer commands

```bash
npm --prefix frontend run test
npm --prefix frontend run build
scripts/run_current_test_gate.sh
scripts/readiness_multi_environment_contract_check.sh
```

## Supported run entrypoints

Use the repository scripts instead of running raw `docker compose` or ad-hoc API commands.

| Target | Supported command | Env contract | Why |
| --- | --- | --- | --- |
| Local host/dev | `ENV_FILE=.env.local scripts/run_local_dev.sh` | `.env.local` | Starts the host API/frontend with local writable users overlay and skips ignored root-level benchmark artifacts. |
| Local Docker/local | `scripts/run_local_docker.sh` | `.env.docker` plus script-resolved local data roots | Renders Docker volumes against the local `runtime/ai_decision_studio_functional_baseline/oracle_like_data` tree instead of falling back to `/opt/...` paths. |
| AWS slim deploy | `scripts/deploy_aws_slim.sh` | `.env.aws` | Uses the AWS deployment contract and avoids local/Oracle defaults. |
| AWS smoke validation | `scripts/smoke_aws_slim.sh` | `.env.aws` | Validates the deployed AWS surface with the same contract. |

Do not run `docker compose -f docker-compose.local.yml up ...` directly for local Docker. Without the script-provided environment, Compose can fall back to `/opt/ai-decision-studio/data/...`, which is a Linux/VM deploy layout and not the local Mac data root.

For local Docker, the expected data root is:

```text
runtime/ai_decision_studio_functional_baseline/oracle_like_data/
  baseline/
  runtime/
  artifacts/
  users/
```

For local host/dev, `scripts/run_local_dev.sh` protects the Lab benchmark surface from ignored root-level experiment artifacts such as `./benchmark_runs`.
