#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.oracle}"
PROJECT="${PROJECT:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.oracle-like.yml}"
OVERRIDE_FILE="${OVERRIDE_FILE:-docker-compose.aws-slim.override.yml}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8011}"
REPORT="../ai_decision_studio_functional_baseline/parity_reports/required_integrations_readiness_report.json"

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

required_env = [
    "EVIDENCEOPS_TRELLO_API_KEY",
    "EVIDENCEOPS_TRELLO_TOKEN",
    "EVIDENCEOPS_TRELLO_BOARD_ID",
    "EVIDENCEOPS_TRELLO_LIST_OPEN_ID",
    "EVIDENCEOPS_TRELLO_LIST_REVIEW_ID",
    "EVIDENCEOPS_TRELLO_LIST_APPROVED_ID",
    "EVIDENCEOPS_TRELLO_LIST_DONE_ID",
    "EVIDENCEOPS_NOTION_API_KEY",
    "EVIDENCEOPS_NOTION_DATABASE_ID",
]

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

env_state = {}
for key in required_env:
    value = str(os.environ.get(key) or "").strip()
    env_state[key] = "<set>" if value else "<empty>"
    require(f"env_{key}_set", bool(value), key)

integrations = fetch_json("/api/product/integrations")
targets = {
    str(item.get("key") or ""): item
    for item in integrations.get("targets") or []
    if isinstance(item, dict)
}

evidence["integrations_http_status"] = integrations.get("_http_status")
evidence["integrations_ok"] = integrations.get("ok")
evidence["summary"] = integrations.get("summary")
evidence["env_state"] = env_state
evidence["targets"] = {
    key: {
        "configured": target.get("configured"),
        "status": target.get("status"),
        "detail": target.get("detail"),
    }
    for key, target in targets.items()
}

require("integrations_ok", integrations.get("ok") is True)
require("trello_target_present", "trello" in targets)
require("notion_target_present", "notion" in targets)

trello = targets.get("trello") or {}
notion = targets.get("notion") or {}

require("trello_configured", trello.get("configured") is True, json.dumps(trello, ensure_ascii=False))
require("trello_ready", trello.get("status") == "ready", json.dumps(trello, ensure_ascii=False))
require("notion_configured", notion.get("configured") is True, json.dumps(notion, ensure_ascii=False))
require("notion_ready", notion.get("status") == "ready", json.dumps(notion, ensure_ascii=False))

# Detail endpoints are evidence only. Trello currently may not expose a detail endpoint,
# while Notion does. Required readiness is based on env + integration summary.
for key in ["trello", "notion"]:
    detail = fetch_json(f"/api/product/integrations/{key}?limit=4", allow_http_error=True)
    evidence[f"{key}_detail_http_status"] = detail.get("_http_status")
    evidence[f"{key}_detail_ok"] = detail.get("ok")
    evidence[f"{key}_detail_status"] = detail.get("status")
    evidence[f"{key}_detail_shape"] = sorted([str(item) for item in detail.keys()])[:20]

    if detail.get("_http_status") != 404:
        require(
            f"{key}_detail_not_error",
            detail.get("ok") is True or detail.get("status") in {"success", "ready", "live"},
            json.dumps(detail, ensure_ascii=False)[:500],
        )

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
