#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

export AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT="${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT:-8013}"
export AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8059}"
export AI_DECISION_STUDIO_PRODUCT_API_BASE_URL="${AI_DECISION_STUDIO_PRODUCT_API_BASE_URL:-http://127.0.0.1:${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT}}"
export AI_DECISION_STUDIO_FRONTEND_BASE_URL="${AI_DECISION_STUDIO_FRONTEND_BASE_URL:-http://127.0.0.1:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT}}"
export AI_DECISION_STUDIO_DOCKER_FRONTEND_URL="${AI_DECISION_STUDIO_DOCKER_FRONTEND_URL:-$AI_DECISION_STUDIO_FRONTEND_BASE_URL}"
export AI_DECISION_STUDIO_LOCAL_FRONTEND_URL="${AI_DECISION_STUDIO_LOCAL_FRONTEND_URL:-http://127.0.0.1:8080}"
export AI_DECISION_STUDIO_WORKFLOW_SMOKE_TIMEOUT_SECONDS="${AI_DECISION_STUDIO_WORKFLOW_SMOKE_TIMEOUT_SECONDS:-420}"
export AI_DECISION_STUDIO_ROUTE_PARITY_SKIP="${AI_DECISION_STUDIO_ROUTE_PARITY_SKIP:-/app/lab/chat}"

REPORT_DIR="${AI_DECISION_STUDIO_PARITY_REPORT_DIR:-runtime/ai_decision_studio_functional_baseline/parity_reports}"
mkdir -p "$REPORT_DIR"


ensure_public_demo_stack() {
  echo
  echo "== Ensure public demo stack is running =="
  docker compose -f legacy/compose/docker-compose.frontend-public-demo.yml up -d

  echo
  echo "== Wait for stack after restart =="
  for i in $(seq 1 40); do
    API_STATUS="$(docker inspect ai-decision-studio-product-api-frontend-public-demo --format '{{.State.Health.Status}}' 2>/dev/null || true)"
    FE_STATUS="$(docker inspect ai-decision-studio-frontend-public-demo --format '{{.State.Health.Status}}' 2>/dev/null || true)"
    echo "health[$i] api=$API_STATUS frontend=$FE_STATUS"
    if [ "$API_STATUS" = "healthy" ] && [ "$FE_STATUS" = "healthy" ]; then
      break
    fi
    sleep 2
  done

  curl -fsS "$AI_DECISION_STUDIO_PRODUCT_API_BASE_URL/health" >/dev/null
  curl -fsS "$AI_DECISION_STUDIO_FRONTEND_BASE_URL" >/dev/null
}

echo "== AI Decision Studio full frontend parity check =="
echo "api=$AI_DECISION_STUDIO_PRODUCT_API_BASE_URL"
echo "frontend=$AI_DECISION_STUDIO_FRONTEND_BASE_URL"
echo "local_frontend=$AI_DECISION_STUDIO_LOCAL_FRONTEND_URL"
echo "report_dir=$REPORT_DIR"

ensure_public_demo_stack

echo
echo "== Health =="
curl -fsS "$AI_DECISION_STUDIO_PRODUCT_API_BASE_URL/health" | python3 -m json.tool

echo
echo "== Provider integrations =="
python3 - <<'PY'
import json
import os
from urllib.request import urlopen

base = os.environ["AI_DECISION_STUDIO_PRODUCT_API_BASE_URL"]
payload = json.loads(urlopen(base + "/api/product/integrations", timeout=30).read().decode("utf-8"))
targets = {item["key"]: item for item in payload.get("targets", [])}

summary = {
    "ready_targets": payload.get("summary", {}).get("ready_targets"),
    "nextcloud": targets.get("nextcloud", {}).get("status"),
    "trello": targets.get("trello", {}).get("status"),
    "notion": targets.get("notion", {}).get("status"),
}

print(json.dumps(summary, indent=2, ensure_ascii=False))

assert summary["nextcloud"] == "ready", summary
assert summary["trello"] == "ready", summary
assert summary["notion"] == "ready", summary
PY

echo
echo "== Favicon =="
curl -I -fsS "$AI_DECISION_STUDIO_FRONTEND_BASE_URL/favicon.svg" >/dev/null

echo
echo "== Existing readiness scripts =="
legacy/scripts/smoke_docker_public_demo.sh
ensure_public_demo_stack
scripts/smoke_docker_workflow_write.sh
scripts/smoke_docker_policy_comparison_write.sh
scripts/smoke_frontend_docker_workflows_ui.sh

echo
echo "== Route parity local vs Docker =="
if curl -fsS "$AI_DECISION_STUDIO_LOCAL_FRONTEND_URL" >/dev/null 2>&1; then
  scripts/smoke_frontend_ui_parity_local_vs_docker.sh
else
  echo "SKIP route parity: local frontend not reachable at $AI_DECISION_STUDIO_LOCAL_FRONTEND_URL"
fi

echo
echo "== Product deep clicks =="
node .tmp_playwright/product_deep_clicks_docker.cjs

echo
echo "== AI Lab deep clicks =="
node .tmp_playwright/ai_lab_deep_clicks_docker.cjs

echo
echo "== Settings deep clicks =="
node .tmp_playwright/settings_deep_clicks_docker.cjs

echo
echo "== Ensure stack before AI Lab content check =="
ensure_public_demo_stack

echo
echo "== AI Lab content check =="
scripts/readiness_ai_lab_content_check.sh

echo
echo "== Ensure stack before runbook phases 8-12 check =="
ensure_public_demo_stack

echo
echo "== Runbook phases 8-12 check =="
scripts/readiness_eval_runbook_check.sh

echo
echo "== Full frontend parity check completed =="
