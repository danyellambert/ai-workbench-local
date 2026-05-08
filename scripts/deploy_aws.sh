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

echo "== AWS deploy =="
echo "env_file=$ENV_FILE"
echo "project=$PROJECT_NAME"

ensure_docker_runtime() {
  echo
  echo "== Ensure Docker runtime =="

  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker --version
    docker compose version
    echo "OK: Docker runtime already available for current user."
    return 0
  fi

  if ! command -v apt-get >/dev/null 2>&1; then
    echo "ERROR: Docker is missing and this bootstrap only supports apt-based Linux hosts." >&2
    exit 1
  fi

  echo "Docker runtime missing or not accessible. Installing/repairing Docker via apt..."

  sudo apt-get update

  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    acl \
    ca-certificates \
    curl \
    docker.io

  if ! sudo docker compose version >/dev/null 2>&1; then
    if apt-cache show docker-compose-v2 >/dev/null 2>&1; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-v2
    elif apt-cache show docker-compose-plugin >/dev/null 2>&1; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-compose-plugin
    else
      echo "ERROR: could not find a Docker Compose v2 package in apt." >&2
      exit 1
    fi
  fi

  sudo systemctl enable --now docker || true
  sudo usermod -aG docker "$(id -un)" || true

  if ! docker info >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
    echo "Docker installed, but current SSH session does not have socket access yet."
    echo "Granting current user temporary access to /var/run/docker.sock for this deploy session."
    sudo setfacl -m "u:$(id -un):rw" /var/run/docker.sock || true
  fi

  if docker info >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    docker --version
    docker compose version
    echo "OK: Docker runtime installed and accessible."
    return 0
  fi

  if sudo -n docker info >/dev/null 2>&1 && sudo -n docker compose version >/dev/null 2>&1; then
    echo "Docker is installed, but current SSH session lacks docker group access. Using sudo docker for this deploy."
    docker() {
      sudo docker "$@"
    }
    docker --version
    docker compose version
    echo "OK: Docker runtime available through sudo for this deploy."
    return 0
  fi

  echo "ERROR: Docker was installed but is not accessible." >&2
  echo "Try reconnecting over SSH so docker group membership is refreshed." >&2
  exit 1
}

ensure_docker_runtime

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
    -f docker-compose.aws.yml \
    "$@"
}

CFG="/tmp/ads_aws_compose_$(date +%Y%m%d_%H%M%S).yml"

compose config > "$CFG"

grep -q 'dockerfile: Dockerfile.product-api.aws' "$CFG"
grep -q 'image: ai-decision-studio-product-api:aws' "$CFG"

echo "OK: compose config uses AWS product-api."

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
    -f docker-compose.aws.yml \
    ps || true
  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT_NAME" \
    -f docker-compose.aws.yml \
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
  -f docker-compose.aws.yml \
  up -d --build --force-recreate ollama nextcloud ppt-creator product-api frontend

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.aws.yml \
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

echo "OK: AWS deploy completed."
