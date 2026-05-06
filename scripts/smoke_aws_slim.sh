#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.aws}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8071}"

echo "== AWS slim smoke =="
echo "env_file=$ENV_FILE"
echo "base_url=$BASE_URL"

docker compose \
  --env-file "$ENV_FILE" \
  -p "$PROJECT_NAME" \
  -f docker-compose.aws-slim.yml \
  ps

curl -fsS "$BASE_URL/health"
echo

curl -fsS "$BASE_URL/api/preferences" > /tmp/ads_aws_slim_preferences.json

python3 - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/ads_aws_slim_preferences.json").read_text())
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

echo "OK: AWS slim smoke passed."
