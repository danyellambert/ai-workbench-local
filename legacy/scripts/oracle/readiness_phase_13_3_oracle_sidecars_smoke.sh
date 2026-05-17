#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 13.3 Oracle sidecar smoke =="

COMPOSE_FILE="${AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE:-docker-compose.oracle-like.yml}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
SAFE_ENV_FILE="${AI_DECISION_STUDIO_PHASE_13_3_SAFE_ENV_FILE:-/tmp/ads-oracle-sidecars-safe.env}"
BASE_URL="${AI_DECISION_STUDIO_READINESS_BASE_URL:-http://127.0.0.1:8071}"

cat > "$SAFE_ENV_FILE" <<'ENV'
COMPOSE_PROJECT_NAME=ai-decision-studio

AI_DECISION_STUDIO_FRONTEND_BIND_HOST=127.0.0.1
AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT=8071

AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB=250
AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH=
AI_DECISION_STUDIO_SESSION_SECRET=

EVIDENCEOPS_REPOSITORY_BACKEND=nextcloud_webdav
EVIDENCEOPS_NEXTCLOUD_BASE_URL=http://nextcloud/remote.php/dav/files/ads_admin
EVIDENCEOPS_NEXTCLOUD_USERNAME=ads_admin
EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD=change-me-oracle-nextcloud-password
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo

EVIDENCEOPS_TRELLO_API_KEY=
EVIDENCEOPS_TRELLO_TOKEN=
EVIDENCEOPS_NOTION_API_KEY=

PRESENTATION_EXPORT_ENABLED=true
PRESENTATION_EXPORT_BASE_URL=http://ppt-creator:8787
PRESENTATION_EXPORT_TIMEOUT_SECONDS=120
PPT_CREATOR_AI_SERVICE_URL=

OLLAMA_BASE_URL=http://ollama:11434/v1
OLLAMA_HOST=http://ollama:11434
OLLAMA_HOSTED_API_KEY=
OLLAMA_CPUS=2
OLLAMA_MEM_LIMIT=12g
OLLAMA_MEMSWAP_LIMIT=12g
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1

HUGGINGFACE_INFERENCE_API_KEY=
OPENAI_API_KEY=
ENV

chmod 600 "$SAFE_ENV_FILE"

echo
echo "== Static sidecar readiness =="
bash legacy/scripts/oracle/readiness_phase_13_3_oracle_sidecars_check.sh

echo
echo "== Compose up =="
docker compose \
  --env-file "$SAFE_ENV_FILE" \
  -p "$COMPOSE_PROJECT_NAME" \
  -f "$COMPOSE_FILE" \
  up -d --build

echo
echo "== Compose ps =="
docker compose \
  --env-file "$SAFE_ENV_FILE" \
  -p "$COMPOSE_PROJECT_NAME" \
  -f "$COMPOSE_FILE" \
  ps

echo
echo "== Wait frontend/product-api health =="
python3 - <<PY
from __future__ import annotations

import json
import time
import urllib.request

base_url = "${BASE_URL}".rstrip("/")

def fetch(path: str, timeout: int = 10):
    with urllib.request.urlopen(base_url + path, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body

deadline = time.time() + 120
last_error = None

while time.time() < deadline:
    try:
        status, body = fetch("/health")
        data = json.loads(body)
        if status == 200 and data.get("ok") is True:
            print(json.dumps({"health": data}, indent=2, ensure_ascii=False))
            break
    except Exception as exc:
        last_error = repr(exc)
    time.sleep(3)
else:
    raise SystemExit(f"frontend health did not become ready: {last_error}")
PY

echo
echo "== Session through frontend =="
python3 - <<PY
from __future__ import annotations

import json
import urllib.request

base_url = "${BASE_URL}".rstrip("/")
with urllib.request.urlopen(base_url + "/api/auth/session", timeout=20) as resp:
    data = json.loads(resp.read().decode("utf-8") or "{}")

print(json.dumps(data, indent=2, ensure_ascii=False))

assert data.get("ok") is True, data
identity = data.get("identity") or {}
policy = data.get("policy") or {}
assert identity.get("role") == "public", data
assert identity.get("can_write_global") is False, data
assert identity.get("can_publish_external") is False, data
assert policy.get("public_can_write_overlay") is True, data
assert policy.get("public_can_write_global") is False, data
assert policy.get("public_can_publish_external") is False, data
PY

echo
echo "== Internal sidecars from product-api container =="
docker compose \
  --env-file "$SAFE_ENV_FILE" \
  -p "$COMPOSE_PROJECT_NAME" \
  -f "$COMPOSE_FILE" \
  exec -T product-api python - <<'PY'
import json
import urllib.request

checks = {}

def probe(name, url, timeout=20):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(500).decode("utf-8", errors="replace")
            checks[name] = {
                "ok": 200 <= resp.status < 500,
                "status": resp.status,
                "url": url,
                "body_preview": body[:220],
            }
    except Exception as exc:
        checks[name] = {
            "ok": False,
            "url": url,
            "error": repr(exc),
        }

probe("ppt_creator_health", "http://ppt-creator:8787/health")
probe("ollama_tags", "http://ollama:11434/api/tags")
probe("nextcloud_status", "http://nextcloud/status.php")

print(json.dumps(checks, indent=2, ensure_ascii=False))

assert checks["ppt_creator_health"]["ok"], checks["ppt_creator_health"]
assert checks["ollama_tags"]["ok"], checks["ollama_tags"]
assert checks["nextcloud_status"]["ok"], checks["nextcloud_status"]

print("OK: internal sidecars reachable from product-api")
PY

echo
echo "== Compose exposure check =="
docker compose \
  --env-file "$SAFE_ENV_FILE" \
  -f "$COMPOSE_FILE" \
  config >/tmp/ads-compose-sidecars-safe.yml

python3 - <<'PY'
from __future__ import annotations

import json
import re
from pathlib import Path

config = Path("/tmp/ads-compose-sidecars-safe.yml").read_text(encoding="utf-8")

checks = {
    "frontend_publishes_localhost_8071": "host_ip: 127.0.0.1" in config and 'published: "8071"' in config and "target: 8080" in config,
    "no_localhost_legacy_nextcloud_url": "127.0.0.1:8085" not in config,
    "no_localhost_legacy_ppt_url": "127.0.0.1:8787" not in config.replace("http://127.0.0.1:8787/health", ""),
    "uses_internal_nextcloud_url": "http://nextcloud/remote.php/dav/files/ads_admin" in config,
    "uses_internal_ppt_creator_url": "http://ppt-creator:8787" in config,
    "uses_internal_ollama_url": "http://ollama:11434/v1" in config,
}

for service in ["product-api", "ppt-creator", "ollama", "nextcloud"]:
    pattern = rf"(?ms)^  {re.escape(service)}:\n(.*?)(?=^  [a-zA-Z0-9_-]+:|\nvolumes:|\nnetworks:|\Z)"
    match = re.search(pattern, config)
    block = match.group(1) if match else ""
    checks[f"{service}_has_no_ports_block"] = "ports:" not in block

print(json.dumps({"checks": checks}, indent=2, ensure_ascii=False))

failed = {k: v for k, v in checks.items() if not v}
if failed:
    raise SystemExit(f"Exposure check failed: {failed}")
PY

echo
echo "== Safe env secret placeholders check =="
grep -nE "API_KEY|TOKEN|PASSWORD|SECRET|HASH" /tmp/ads-compose-sidecars-safe.yml | sed -n '1,160p'

echo
echo "OK: Phase 13.3 Oracle sidecar smoke passed"
