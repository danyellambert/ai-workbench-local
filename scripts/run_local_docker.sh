#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.docker}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
CONFIG_ONLY="false"

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_local_docker.sh
  scripts/run_local_docker.sh --config-only

Optional env:
  ENV_FILE=.env.docker
  COMPOSE_PROJECT_NAME=ai-decision-studio

Behavior:
  - Uses docker-compose.oracle-like.yml as the shared local Docker topology.
  - Does not use AWS slim override.
  - --config-only renders compose config without building or starting containers.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --config-only)
      CONFIG_ONLY="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  echo "Create it from .env.docker.example and adjust local data-root paths." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker command not found." >&2
  exit 1
fi

if [ "$CONFIG_ONLY" = "true" ]; then
  CFG="/tmp/ads_local_docker_compose_$(date +%Y%m%d_%H%M%S).yml"

  docker compose \
    --env-file "$ENV_FILE" \
    -p "$PROJECT_NAME" \
    -f docker-compose.oracle-like.yml \
    config > "$CFG"

  grep -q 'image: ai-decision-studio-product-api:oracle-like' "$CFG"
  grep -q 'image: ai-decision-studio-frontend:oracle-like' "$CFG"
  grep -q 'image: ai-decision-studio-ppt-creator:oracle-like' "$CFG"
  grep -q 'image: ollama/ollama' "$CFG"
  grep -q 'image: nextcloud:29-apache' "$CFG"

  echo "OK: local Docker compose config rendered: $CFG"
  exit 0
fi

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.oracle-like.yml \
  up -d --build

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.oracle-like.yml \
  ps
