#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.oracle}"
PROJECT="${PROJECT:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.local.yml}"
OVERRIDE_FILE="${OVERRIDE_FILE:-docker-compose.aws-slim.yml}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8011}"
REPORT="runtime/ai_decision_studio_functional_baseline/parity_reports/required_providers_readiness_report.json"

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

docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T product-api python - "$BASE_URL" <<'PY' | tee "$REPORT"
import json
import os
import sys
import urllib.request
import urllib.error

base_url = sys.argv[1].rstrip("/")
errors = []
checks = {}
evidence = {}

def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))

def fetch_json(path, *, allow_http_error=False):
    try:
        with urllib.request.urlopen(base_url + path, timeout=120) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
        if not allow_http_error:
            raise
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        payload = {"ok": False, "raw": raw.decode("utf-8", errors="replace")[:500]}
    payload["_http_status"] = status
    return payload

hf_key = str(os.environ.get("HUGGINGFACE_INFERENCE_API_KEY") or os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN") or "").strip()
hf_base = str(os.environ.get("HUGGINGFACE_INFERENCE_BASE_URL") or "").strip()

evidence["env"] = {
    "HUGGINGFACE_INFERENCE_BASE_URL": hf_base or "<empty>",
    "HUGGINGFACE_INFERENCE_API_KEY": "<set>" if os.environ.get("HUGGINGFACE_INFERENCE_API_KEY") else "<empty>",
    "HUGGINGFACE_API_KEY": "<set>" if os.environ.get("HUGGINGFACE_API_KEY") else "<empty>",
    "HF_TOKEN": "<set>" if os.environ.get("HF_TOKEN") else "<empty>",
    "OLLAMA_HOSTED_API_KEY": "<set>" if os.environ.get("OLLAMA_HOSTED_API_KEY") else "<empty>",
}

require("huggingface_key_set", bool(hf_key), "HUGGINGFACE_INFERENCE_API_KEY/HUGGINGFACE_API_KEY/HF_TOKEN")
require("huggingface_base_url_set", bool(hf_base), "HUGGINGFACE_INFERENCE_BASE_URL")

preferences = fetch_json("/api/preferences", allow_http_error=True)
evidence["preferences_http_status"] = preferences.get("_http_status")
evidence["preferences_ok"] = preferences.get("ok")
evidence["credential_policy"] = preferences.get("credential_policy")

text = json.dumps(preferences, ensure_ascii=False).lower()
evidence["preferences_mentions_huggingface"] = ("hugging" in text or "huggingface" in text)

require("preferences_endpoint_ok", preferences.get("ok") is True, json.dumps(preferences, ensure_ascii=False)[:500])
require("preferences_mentions_huggingface", evidence["preferences_mentions_huggingface"], "Hugging Face not present in preferences payload")

payload = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}

print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)
PY
