#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.oracle}"
PROJECT="${PROJECT:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.oracle-like.yml}"
OVERRIDE_FILE="${OVERRIDE_FILE:-docker-compose.aws-slim.override.yml}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8011}"
REPORT="../ai_decision_studio_functional_baseline/parity_reports/evidenceops_ui_cache_readiness_report.json"
MAX_HIT_MS=2500

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --project)
      PROJECT="${2:?}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:?}"
      shift 2
      ;;
    --report)
      REPORT="${2:?}"
      shift 2
      ;;
    --max-hit-ms)
      MAX_HIT_MS="${2:?}"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$REPORT")"

COMPOSE_ARGS=(-p "$PROJECT" -f "$COMPOSE_FILE")
if [ -f "$OVERRIDE_FILE" ]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
fi

docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T product-api python - "$BASE_URL" "$MAX_HIT_MS" <<'PY' | tee "$REPORT"
import json
import sys
import time
import urllib.request

base_url = sys.argv[1].rstrip("/")
max_hit_ms = float(sys.argv[2])

errors = []
checks = {}
evidence = {}

def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))

def fetch(path):
    start = time.perf_counter()
    with urllib.request.urlopen(base_url + path, timeout=180) as resp:
        raw = resp.read()
        status = resp.status
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    payload = json.loads(raw.decode("utf-8"))
    return status, elapsed_ms, payload

first_status, first_ms, first_payload = fetch("/api/lab/evidenceops")
second_status, second_ms, second_payload = fetch("/api/lab/evidenceops")
overview_status, overview_ms, overview_payload = fetch("/api/lab/overview")

first_cache = (first_payload.get("meta") or {}).get("evidenceopsCache") or {}
second_cache = (second_payload.get("meta") or {}).get("evidenceopsCache") or {}

evidence["first_call"] = {
    "status": first_status,
    "elapsed_ms": first_ms,
    "cache": first_cache,
    "summary": first_payload.get("summary"),
}

evidence["second_call"] = {
    "status": second_status,
    "elapsed_ms": second_ms,
    "cache": second_cache,
    "summary": second_payload.get("summary"),
}

evidence["overview_call"] = {
    "status": overview_status,
    "elapsed_ms": overview_ms,
    "kpis": overview_payload.get("kpis"),
}

require("first_evidenceops_ok", first_status == 200 and first_payload.get("ok") is True)
require("second_evidenceops_ok", second_status == 200 and second_payload.get("ok") is True)
require("overview_ok", overview_status == 200 and overview_payload.get("ok") is True)

require("cache_meta_present_first", bool(first_cache), json.dumps(first_cache, ensure_ascii=False))
require("cache_meta_present_second", bool(second_cache), json.dumps(second_cache, ensure_ascii=False))
require("cache_mode_persistent_until_sync", second_cache.get("mode") == "persistent_until_sync", json.dumps(second_cache, ensure_ascii=False))
require("cache_exists", second_cache.get("exists") is True, json.dumps(second_cache, ensure_ascii=False))
require("cache_second_call_hit", second_cache.get("status") == "hit", json.dumps(second_cache, ensure_ascii=False))

require("second_evidenceops_fast", second_ms < max_hit_ms, f"{second_ms} >= {max_hit_ms}")
require("overview_fast_after_cache", overview_ms < max_hit_ms, f"{overview_ms} >= {max_hit_ms}")

payload = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "max_hit_ms": max_hit_ms,
    "evidence": evidence,
}

print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)
PY
