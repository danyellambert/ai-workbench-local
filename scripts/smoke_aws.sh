#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.aws}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8071}"

echo "== AWS smoke =="
echo "env_file=$ENV_FILE"
echo "base_url=$BASE_URL"

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.aws.yml \
  ps

curl -fsS "$BASE_URL/health"
echo

curl -fsS "$BASE_URL/api/preferences" > /tmp/ads_aws_preferences.json

python3 - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/ads_aws_preferences.json").read_text())
connections = payload.get("provider_connections") or []
ids = [item.get("id") for item in connections]

print("provider_connections:", ids)

assert "huggingface_server" not in ids, "local Hugging Face server should not be exposed"
assert "huggingface_local" not in ids, "local Hugging Face server should not be exposed"

ollama = next((item for item in connections if item.get("id") == "ollama"), None)
assert ollama, "Ollama connection missing"

print("ollama preferredModel:", ollama.get("preferredModel"))
assert ollama.get("preferredModel") == "nemotron-3-super:cloud"

print("OK: preferences smoke passed")
PY


echo
echo "== Required AWS service check =="
for service in ollama nextcloud ppt-creator product-api frontend; do
  cid="$(
    docker compose \
      --env-file "$ENV_FILE" \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      ps -q "$service"
  )"

  if [ -z "$cid" ]; then
    echo "ERROR: required AWS service is missing: $service" >&2
    exit 1
  fi

  state="$(docker inspect -f '{{.State.Status}}' "$cid")"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid")"

  echo "$service state=$state health=$health"

  if [ "$state" != "running" ]; then
    echo "ERROR: required AWS service is not running: $service" >&2
    exit 1
  fi

  if [ "$health" != "none" ] && [ "$health" != "healthy" ]; then
    echo "ERROR: required AWS service is not healthy: $service health=$health" >&2
    exit 1
  fi
done

echo "OK: AWS smoke passed."
