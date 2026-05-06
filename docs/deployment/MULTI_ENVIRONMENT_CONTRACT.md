# AI Decision Studio — Multi-environment contract

This document separates the four supported execution modes so that local dev,
local Docker, AWS, and Oracle can coexist without rewriting paths or URLs.

## Modes

| Mode | Real env file | Safe example | Main command |
| --- | --- | --- | --- |
| Local host/dev | .env.local or legacy .env | .env.local.example | scripts/run_local_dev.sh |
| Local host/dev check | `.env.local` or legacy `.env` | `.env.local.example` | `scripts/run_local_dev.sh --check` |
| Local Docker | .env.docker | .env.docker.example | scripts/run_local_docker.sh |
| Local Docker config check | `.env.docker` | `.env.docker.example` | `ENV_FILE=.env.docker.example scripts/run_local_docker.sh --config-only` |
| AWS slim VM | .env.aws | .env.aws.example | scripts/deploy_aws_slim.sh |
| Oracle VM | .env.oracle | legacy/deploy/oracle/.env.oracle.example | existing Oracle runbooks/scripts |

Real env files are ignored by Git. Only *.example files are versioned.

## URL rules

localhost means different things depending on where code runs:

- host to host service: http://127.0.0.1:<port>
- host to published container: http://127.0.0.1:8071
- container to product-api: http://product-api:8011
- container to ollama sidecar: http://ollama:11434
- container to ppt sidecar: http://ppt-creator:8787
- container to nextcloud: http://nextcloud
- container to host service: host.docker.internal on Mac/Windows, host-gateway on Linux

## AWS slim deployment

For a fresh EC2 rebuild, use `docs/deployment/AWS_FRESH_EC2_BOOTSTRAP.md`.
For code-only redeploys on an existing AWS host, use the slim fast path below.

AWS currently uses the proven Oracle-like compose base plus an AWS-specific
slim override:

docker compose \
  --env-file .env.aws \
  -p ai-decision-studio \
  -f docker-compose.oracle-like.yml \
  -f docker-compose.aws-slim.override.yml \
  up -d --no-deps --build product-api frontend

For backward compatibility, scripts may fall back to .env.oracle if .env.aws
is not present on an existing AWS host. This is temporary.

AWS disk rule:

- Always use docker-compose.aws-slim.override.yml.
- product-api image must be ai-decision-studio-product-api:aws-slim.
- Do not build Dockerfile.public-demo for product-api on the 30GB AWS VM.
- Rebuild only product-api/frontend unless explicitly needed.
- Check df -h and docker system df before and after deploy.

## Oracle deployment

Oracle keeps the original contract:

- .env.oracle
- legacy/deploy/oracle/.env.oracle.example
- docker-compose.oracle-like.yml
- scripts/readiness_oracle_*.sh

The term oracle-like also describes the historical Docker topology: baseline,
runtime, artifacts, users, sidecars, healthchecks, and same-origin frontend/API.

## Migration note

Current AWS hosts may still have .env.oracle because the AWS deployment was
initially bootstrapped from the Oracle-like topology. The safe migration path is:

1. cp .env.oracle .env.aws
2. chmod 600 .env.aws
3. validate with docker compose --env-file .env.aws
4. run scripts/smoke_aws_slim.sh
5. only then switch deploy scripts to .env.aws

Do not delete .env.oracle from a live host until .env.aws has passed smoke.

For full local app usage, see [`LOCAL_FULL_APP_DEV.md`](LOCAL_FULL_APP_DEV.md).

## Supported run entrypoints

Use the repository scripts instead of running raw `docker compose` or ad-hoc API commands.

| Target | Supported command | Env contract | Why |
| --- | --- | --- | --- |
| Local host/dev | `ENV_FILE=.env.local scripts/run_local_dev.sh` | `.env.local` | Starts the host API/frontend with local writable users overlay and skips ignored root-level benchmark artifacts. |
| Local Docker/oracle-like | `scripts/run_local_docker.sh` | `.env.docker` plus script-resolved local data roots | Renders Docker volumes against the local `runtime/ai_decision_studio_functional_baseline/oracle_like_data` tree instead of falling back to `/opt/...` paths. |
| AWS slim deploy | `scripts/deploy_aws_slim.sh` | `.env.aws` | Uses the AWS deployment contract and avoids local/Oracle defaults. |
| AWS smoke validation | `scripts/smoke_aws_slim.sh` | `.env.aws` | Validates the deployed AWS surface with the same contract. |

Do not run `docker compose -f docker-compose.oracle-like.yml up ...` directly for local Docker. Without the script-provided environment, Compose can fall back to `/opt/ai-decision-studio/data/...`, which is a Linux/VM deploy layout and not the local Mac data root.

For local Docker, the expected data root is:

```text
runtime/ai_decision_studio_functional_baseline/oracle_like_data/
  baseline/
  runtime/
  artifacts/
  users/
```

For local host/dev, `scripts/run_local_dev.sh` protects the Lab benchmark surface from ignored root-level experiment artifacts such as `./benchmark_runs`.
