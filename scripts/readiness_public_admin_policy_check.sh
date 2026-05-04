#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE:-docker-compose.oracle-like.yml}"
DATA_ROOT="${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-runtime/ai_decision_studio_functional_baseline/oracle_like_data}"
FRONTEND_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8071}"
FRONTEND_BASE_URL="http://127.0.0.1:${FRONTEND_PORT}"
REPORT="${AI_DECISION_STUDIO_PUBLIC_ADMIN_POLICY_REPORT:-runtime/ai_decision_studio_functional_baseline/parity_reports/public_admin_policy_check_report.json}"

export AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT="$FRONTEND_PORT"
export AI_DECISION_STUDIO_BASELINE_ROOT="$(cd "$DATA_ROOT/baseline" && pwd)"
export AI_DECISION_STUDIO_RUNTIME_ROOT="$(cd "$DATA_ROOT/runtime" && pwd)"
export AI_DECISION_STUDIO_ARTIFACT_ROOT="$(cd "$DATA_ROOT/artifacts" && pwd)"
export AI_DECISION_STUDIO_USERS_ROOT="$(cd "$DATA_ROOT/users" && pwd)"
export EVIDENCEOPS_REPOSITORY_BACKEND="${EVIDENCEOPS_REPOSITORY_BACKEND:-local}"

mkdir -p "$(dirname "$REPORT")"

echo "== Public/Admin policy readiness check =="
echo "compose=$COMPOSE_FILE"
echo "frontend=$FRONTEND_BASE_URL"
echo "users=$AI_DECISION_STUDIO_USERS_ROOT"
echo "report=$REPORT"

cleanup() {
  if [ "${AI_DECISION_STUDIO_PUBLIC_ADMIN_POLICY_KEEP_STACK:-0}" != "1" ]; then
    echo
    echo "== Cleanup public/admin policy stack =="
    docker compose -f "$COMPOSE_FILE" down --remove-orphans
  fi
}
trap cleanup EXIT

docker compose -f "$COMPOSE_FILE" build
docker compose -f "$COMPOSE_FILE" up -d

for i in $(seq 1 60); do
  API_STATUS="$(docker inspect ai-decision-studio-product-api-oracle-like --format '{{.State.Health.Status}}' 2>/dev/null || true)"
  FE_STATUS="$(docker inspect ai-decision-studio-frontend-oracle-like --format '{{.State.Health.Status}}' 2>/dev/null || true)"
  echo "health[$i] api=$API_STATUS frontend=$FE_STATUS"
  if [ "$API_STATUS" = "healthy" ] && [ "$FE_STATUS" = "healthy" ]; then
    break
  fi
  sleep 2
done

python3 - <<'PY'
import json
import os
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.request import Request, urlopen

frontend = f"http://127.0.0.1:{os.environ.get('AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT', '8071')}"
users_root = Path(os.environ["AI_DECISION_STUDIO_USERS_ROOT"])
report_path = Path(os.environ.get(
    "AI_DECISION_STUDIO_PUBLIC_ADMIN_POLICY_REPORT",
    "runtime/ai_decision_studio_functional_baseline/parity_reports/public_admin_policy_check_report.json",
))

def fetch_session(cookie_header=None):
    headers = {}
    if cookie_header:
        headers["Cookie"] = cookie_header
    req = Request(frontend + "/api/auth/session", headers=headers)
    with urlopen(req, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))
        set_cookie = response.headers.get("Set-Cookie")
    return body, set_cookie

first, set_cookie = fetch_session()

cookie = SimpleCookie()
if set_cookie:
    cookie.load(set_cookie)

session_id = first.get("identity", {}).get("session_id")
cookie_session = cookie.get("ads_session_id").value if "ads_session_id" in cookie else None

cookie_header = f"ads_session_id={cookie_session}"
second, _ = fetch_session(cookie_header)

overlay_root = users_root / "public_sessions" / session_id / "overlay"

checks = {
    "session_endpoint_ok": bool(first.get("ok")),
    "role_public": first.get("identity", {}).get("role") == "public",
    "session_id_created": bool(session_id and session_id.startswith("sess_")),
    "cookie_set": cookie_session == session_id,
    "same_cookie_same_session": second.get("identity", {}).get("session_id") == session_id,
    "public_cannot_write_global": first.get("identity", {}).get("can_write_global") is False,
    "public_cannot_publish_external": first.get("identity", {}).get("can_publish_external") is False,
    "overlay_root_exists": overlay_root.exists(),
    "overlay_subdirs_exist": all((overlay_root / name).exists() for name in [
        "documents",
        "indexes",
        "runs",
        "artifacts",
        "handoffs",
        "actions",
    ]),
}

report = {
    "ok": all(checks.values()),
    "checks": checks,
    "summary": {
        "session_id": session_id,
        "overlay_root": str(overlay_root),
        "first_identity": first.get("identity"),
        "second_identity": second.get("identity"),
    },
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY

echo

echo
echo "== Public admin-only write guard checks =="
python3 - <<'PY2'
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

frontend_port = os.environ.get("AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT", "8071")
base_url = f"http://127.0.0.1:{frontend_port}"

report_dir = Path("runtime/ai_decision_studio_functional_baseline/parity_reports")
report_dir.mkdir(parents=True, exist_ok=True)
report_path = report_dir / "public_admin_write_guard_report.json"

def request_json(method: str, path: str, payload: dict | None = None, cookie: str | None = None) -> tuple[int, dict, str | None]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw or "{}")
            return resp.status, body, resp.headers.get("Set-Cookie")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        try:
            body = json.loads(raw or "{}")
        except Exception:
            body = {"ok": False, "raw": raw}
        return error.code, body, error.headers.get("Set-Cookie")

session_status, session_body, set_cookie = request_json("GET", "/api/auth/session")
cookie = set_cookie.split(";", 1)[0] if set_cookie else None

session_identity = session_body.get("identity") if isinstance(session_body, dict) else {}
if not isinstance(session_identity, dict):
    session_identity = {}

checks: dict[str, bool] = {
    "session_available": session_status == 200 and session_identity.get("role") == "public",
    "cookie_available": bool(cookie),
}

probes = {
    "public_runtime_controls_patch_blocked": ("PATCH", "/api/runtime/controls", {}),
    "public_preferences_patch_blocked": ("PATCH", "/api/preferences", {}),
    "public_credential_test_blocked": ("POST", "/api/preferences/connections/readiness_guard_probe/test", {}),
    "public_credential_update_blocked": ("POST", "/api/preferences/connections/readiness_guard_probe/credential", {"api_key": "readiness-placeholder-not-a-secret"}),
    "public_trello_publish_blocked": ("POST", "/api/product/publish-to-trello", {}),
    "public_notion_publish_blocked": ("POST", "/api/product/publish-to-notion", {}),
}

responses: dict[str, dict] = {}
for check_name, (method, path, payload) in probes.items():
    status, body, _ = request_json(method, path, payload, cookie)
    checks[check_name] = status == 403 and body.get("ok") is False and body.get("required_role") == "admin"
    responses[check_name] = {"status": status, "body": body}

report = {"ok": all(checks.values()), "checks": checks, "responses": responses}
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY2

echo "== Public/Admin policy readiness check completed =="
