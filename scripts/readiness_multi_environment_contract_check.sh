#!/usr/bin/env bash
set -euo pipefail

echo "== Multi-environment contract readiness =="

required_examples=(
  ".env.local.example"
  ".env.docker.example"
  ".env.aws.example"
  ".env.oracle.example"
)

required_scripts=(
  "scripts/run_local_dev.sh"
  "scripts/run_local_docker.sh"
  "scripts/deploy_aws_slim.sh"
  "scripts/smoke_aws_slim.sh"
  "scripts/validate_aws_env_contract.py"
)

for path in "${required_examples[@]}" "${required_scripts[@]}"; do
  if [ ! -f "$path" ]; then
    echo "ERROR: missing required path: $path" >&2
    exit 1
  fi
done

for script in \
  scripts/run_local_dev.sh \
  scripts/run_local_docker.sh \
  scripts/deploy_aws_slim.sh \
  scripts/smoke_aws_slim.sh \
  scripts/build_oracle_deployment_bundle.sh
do
  bash -n "$script"
done

ENV_FILE=.env.local.example scripts/run_local_dev.sh --check
ENV_FILE=.env.docker.example scripts/run_local_docker.sh --config-only

grep -q 'PRODUCT_API_PROXY_TARGET' frontend/vite.config.ts
grep -q '"/api"' frontend/vite.config.ts

if grep -Rqs 'falling back to legacy .env.oracle' scripts/deploy_aws_slim.sh scripts/smoke_aws_slim.sh; then
  echo "ERROR: AWS slim scripts must not fall back to .env.oracle." >&2
  exit 1
fi

INSIDE_GIT_WORKTREE="false"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  INSIDE_GIT_WORKTREE="true"
fi

for real_env in .env .env.local .env.docker .env.aws .env.oracle; do
  if [ -e "$real_env" ]; then
    if [ "$INSIDE_GIT_WORKTREE" = "true" ]; then
      if ! git check-ignore -q "$real_env"; then
        echo "ERROR: real env file is not ignored by Git: $real_env" >&2
        exit 1
      fi
      echo "OK: $real_env is ignored"
    else
      echo "WARN: $real_env exists, but this directory is not a Git worktree; skipping gitignore check."
    fi
  fi
done

if [ -f ".env.aws" ]; then
  python3 scripts/validate_aws_env_contract.py --env .env.aws --example .env.aws.example
else
  echo "WARN: .env.aws real not present locally; skipping real AWS env parity."
fi

docker compose \
  --env-file .env.docker.example \
  -p ai-decision-studio-contract-docker \
  -f docker-compose.oracle-like.yml \
  config >/tmp/ads_multi_env_docker_config.yml

grep -q 'image: ai-decision-studio-product-api:oracle-like' /tmp/ads_multi_env_docker_config.yml
grep -q 'image: ai-decision-studio-frontend:oracle-like' /tmp/ads_multi_env_docker_config.yml

docker compose \
  --env-file .env.aws.example \
  -p ai-decision-studio-contract-aws \
  -f docker-compose.oracle-like.yml \
  -f docker-compose.aws-slim.override.yml \
  config >/tmp/ads_multi_env_aws_config.yml

grep -q 'dockerfile: Dockerfile.aws-slim-product-api' /tmp/ads_multi_env_aws_config.yml
grep -q 'image: ai-decision-studio-product-api:aws-slim' /tmp/ads_multi_env_aws_config.yml

echo "OK: local Docker and AWS compose contracts render correctly."
echo "OK: multi-environment contract readiness passed."
