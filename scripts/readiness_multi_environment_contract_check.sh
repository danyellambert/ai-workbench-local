#!/usr/bin/env bash
set -euo pipefail

echo "== Multi-environment contract readiness =="

SKIP_LOCAL_DEV_CHECK="${SKIP_LOCAL_DEV_CHECK:-auto}"
SKIP_LOCAL_DOCKER_CHECK="${SKIP_LOCAL_DOCKER_CHECK:-auto}"


required_examples=(
  ".env.local.example"
  ".env.docker.example"
  ".env.aws.example"
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
  scripts/build_deployment_bundle.sh
do
  bash -n "$script"
done

if [ "$SKIP_LOCAL_DEV_CHECK" = "auto" ] || [ "$SKIP_LOCAL_DOCKER_CHECK" = "auto" ]; then
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    DEFAULT_SKIP_LOCAL_RUNNER_CHECKS=0
  else
    DEFAULT_SKIP_LOCAL_RUNNER_CHECKS=1
  fi

  if [ "$SKIP_LOCAL_DEV_CHECK" = "auto" ]; then
    SKIP_LOCAL_DEV_CHECK="$DEFAULT_SKIP_LOCAL_RUNNER_CHECKS"
  fi

  if [ "$SKIP_LOCAL_DOCKER_CHECK" = "auto" ]; then
    SKIP_LOCAL_DOCKER_CHECK="$DEFAULT_SKIP_LOCAL_RUNNER_CHECKS"
  fi
fi

echo "local_dev_check_skipped=$SKIP_LOCAL_DEV_CHECK"
echo "local_docker_check_skipped=$SKIP_LOCAL_DOCKER_CHECK"

if [ "$SKIP_LOCAL_DEV_CHECK" = "1" ]; then
  echo "SKIP: local host/dev contract check"
else
  ENV_FILE=.env.local.example scripts/run_local_dev.sh --check
fi
if [ "$SKIP_LOCAL_DOCKER_CHECK" = "1" ]; then
  echo "SKIP: local Docker compose contract check"
else
  ENV_FILE=.env.docker.example scripts/run_local_docker.sh --config-only
fi
grep -q 'PRODUCT_API_PROXY_ENABLED' frontend/vite.config.ts
grep -q 'PRODUCT_API_DEV_PROXY' frontend/vite.config.ts
grep -q '"/api"' frontend/vite.config.ts
grep -q '^VITE_PRODUCT_API_PROXY_ENABLED=1$' .env.local.example
grep -q '^VITE_PRODUCT_API_BASE_URL=http://127.0.0.1:5173$' .env.local.example
grep -q '^VITE_PRODUCT_API_PROXY_TARGET=http://127.0.0.1:8011$' .env.local.example
grep -q '^VITE_PRODUCT_API_PROXY_ENABLED=0$' .env.aws.example

grep -q 'PRODUCT_API_PROXY_ENABLED' frontend/vite.config.ts
grep -q 'PRODUCT_API_DEV_PROXY' frontend/vite.config.ts
grep -q '"/api"' frontend/vite.config.ts
grep -q '^VITE_PRODUCT_API_PROXY_ENABLED=1$' .env.local.example
grep -q '^VITE_PRODUCT_API_BASE_URL=http://127.0.0.1:5173$' .env.local.example
grep -q '^VITE_PRODUCT_API_PROXY_TARGET=http://127.0.0.1:8011$' .env.local.example


INSIDE_GIT_WORKTREE="false"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  INSIDE_GIT_WORKTREE="true"
fi

for real_env in .env .env.local .env.docker .env.aws; do
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
  -f docker-compose.local.yml \
  config >/tmp/ads_multi_env_docker_config.yml

grep -q 'image: ai-decision-studio-product-api:local' /tmp/ads_multi_env_docker_config.yml
grep -q 'image: ai-decision-studio-frontend:local' /tmp/ads_multi_env_docker_config.yml

docker compose \
  --env-file .env.aws.example \
  -p ai-decision-studio-contract-aws \
  -f docker-compose.aws-slim.yml \
  config >/tmp/ads_multi_env_aws_config.yml

grep -q 'dockerfile: Dockerfile.product-api.aws-slim' /tmp/ads_multi_env_aws_config.yml
grep -q 'image: ai-decision-studio-product-api:aws-slim' /tmp/ads_multi_env_aws_config.yml


echo
echo "== AWS compose single-file guardrail =="
if grep -Rqs 'docker-compose.local.yml' scripts/deploy_aws_slim.sh scripts/smoke_aws_slim.sh; then
  echo "ERROR: AWS deploy/smoke scripts must not use docker-compose.local.yml." >&2
  exit 1
fi
if grep -nE 'docker-compose\.local\.yml.*docker-compose\.aws-slim\.yml|docker-compose\.aws-slim\.yml.*docker-compose\.local\.yml' scripts/deploy_aws_slim.sh scripts/smoke_aws_slim.sh; then
  echo "ERROR: AWS scripts still look like a local+AWS layered compose contract." >&2
  exit 1
fi
echo "OK: AWS scripts use docker-compose.aws-slim.yml as a single compose contract"

echo "OK: local Docker and AWS compose contracts render correctly."
echo "OK: multi-environment contract readiness passed."
