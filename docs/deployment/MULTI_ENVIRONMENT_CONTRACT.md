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
| Oracle VM | .env.oracle | .env.oracle.example | existing Oracle runbooks/scripts |

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
- .env.oracle.example
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
