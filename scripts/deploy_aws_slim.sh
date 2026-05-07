#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.aws}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
PUBLIC_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8071}"
SKIP_OLLAMA_EMBEDDING_MODEL_PULL="${SKIP_OLLAMA_EMBEDDING_MODEL_PULL:-0}"

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

get_env_value() {
  key="$1"
  default="$2"
  awk -F= -v k="$key" -v d="$default" '
    $1 == k {
      v = substr($0, index($0, "=") + 1)
    }
    END {
      if (v == "") print d
      else {
        gsub(/^"|"$/, "", v)
        gsub(/^'\''|'\''$/, "", v)
        print v
      }
    }
  ' "$ENV_FILE"
}

compose() {
  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT_NAME" \
    -f docker-compose.aws-slim.yml \
    "$@"
}

CFG="/tmp/ads_aws_slim_compose_$(date +%Y%m%d_%H%M%S).yml"

compose config > "$CFG"

grep -q 'dockerfile: Dockerfile.product-api.aws-slim' "$CFG"
grep -q 'image: ai-decision-studio-product-api:aws-slim' "$CFG"

echo "OK: compose config uses AWS slim product-api."

wait_for_public_health() {
  local url="http://127.0.0.1:${PUBLIC_PORT}/health"

  echo
  echo "== Wait for public health =="
  echo "url=$url"

  for attempt in $(seq 1 60); do
    if curl -fsS "$url"; then
      echo
      echo "OK: public health is ready"
      return 0
    fi

    echo "public health not ready yet: attempt=$attempt"
    sleep 2
  done

  echo "ERROR: public health did not become ready." >&2
  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT_NAME" \
    -f docker-compose.aws-slim.yml \
    ps || true
  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT_NAME" \
    -f docker-compose.aws-slim.yml \
    logs --tail=160 frontend product-api || true
  return 1
}

ensure_ollama_embedding_model() {
  if [ "$SKIP_OLLAMA_EMBEDDING_MODEL_PULL" = "1" ]; then
    echo "SKIP: Ollama embedding model pull disabled by SKIP_OLLAMA_EMBEDDING_MODEL_PULL=1"
    return 0
  fi

  local embedding_model
  embedding_model="$(get_env_value AI_DECISION_STUDIO_OLLAMA_EMBEDDING_MODEL_PULL "embeddinggemma:300m")"

  if [ -z "$embedding_model" ]; then
    echo "SKIP: no Ollama embedding model configured."
    return 0
  fi

  echo
  echo
echo "== Restore AWS baselines if this is a fresh data root =="
if [ "${AI_DECISION_STUDIO_AWS_RESTORE_BASELINES:-1}" != "0" ]; then
  scripts/restore_aws_baselines.sh "$ENV_FILE"
else
  echo "AWS baseline restore disabled"
fi

echo "== Ensure Ollama embedding model =="
  echo "model=$embedding_model"

  compose up -d ollama

  for i in $(seq 1 60); do
    if compose exec -T ollama ollama list >/tmp/ads_aws_ollama_list.txt 2>/dev/null; then
      break
    fi
    if [ "$i" = "60" ]; then
      echo "ERROR: Ollama container did not become ready for model pull." >&2
      compose logs --tail=120 ollama || true
      exit 1
    fi
    sleep 2
  done

  compose exec -T ollama ollama pull "$embedding_model"
  echo "OK: Ollama embedding model is available."
}

ensure_ollama_embedding_model

DOCKER_BUILDKIT=1 docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.aws-slim.yml \
  up -d --build --force-recreate ollama nextcloud ppt-creator product-api frontend

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.aws-slim.yml \
  ps

wait_for_public_health

docker builder prune -af || true
docker image prune -f || true

echo
echo "== Cleanup temporary AWS deploy artifacts =="
if [ "${AI_DECISION_STUDIO_AWS_CLEANUP_DEPLOY_TMP:-1}" != "0" ]; then
  scripts/cleanup_aws_deploy_artifacts.sh
else
  echo "AWS deploy cleanup disabled"
fi

df -h /
docker system df || true

echo "OK: AWS slim deploy completed."
