#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.aws}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
PUBLIC_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8071}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  echo "Create it from .env.aws.example on AWS." >&2
  exit 1
fi

echo "== AWS slim deploy =="
echo "env_file=$ENV_FILE"
echo "project=$PROJECT_NAME"

df -h /
docker system df || true

CFG="/tmp/ads_aws_slim_compose_$(date +%Y%m%d_%H%M%S).yml"

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.oracle-like.yml \
  -f docker-compose.aws-slim.override.yml \
  config > "$CFG"

grep -q 'dockerfile: Dockerfile.aws-slim-product-api' "$CFG"
grep -q 'image: ai-decision-studio-product-api:aws-slim' "$CFG"

echo "OK: compose config uses AWS slim product-api."

DOCKER_BUILDKIT=1 docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.oracle-like.yml \
  -f docker-compose.aws-slim.override.yml \
  up -d --no-deps --build --force-recreate product-api frontend

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.oracle-like.yml \
  -f docker-compose.aws-slim.override.yml \
  ps

curl -fsS "http://127.0.0.1:${PUBLIC_PORT}/health"
echo

docker builder prune -af || true
docker image prune -f || true

df -h /
docker system df || true

echo "OK: AWS slim deploy completed."
