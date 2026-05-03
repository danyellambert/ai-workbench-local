#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.docker}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  echo "Create it from .env.docker.example and adjust local data-root paths." >&2
  exit 1
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
