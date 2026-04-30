#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE:-docker-compose.oracle-like.yml}"
DATA_ROOT="${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-../ai_decision_studio_functional_baseline/oracle_like_data}"
FRONTEND_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8069}"
FRONTEND_BASE_URL="http://127.0.0.1:${FRONTEND_PORT}"
REPORT="${AI_DECISION_STUDIO_ORACLE_COMPOSE_SMOKE_REPORT:-../ai_decision_studio_functional_baseline/parity_reports/oracle_like_compose_smoke_report.json}"

BASELINE_ROOT="$(cd "$DATA_ROOT/baseline" && pwd)"
RUNTIME_ROOT="$(cd "$DATA_ROOT/runtime" && pwd)"
ARTIFACT_ROOT="$(cd "$DATA_ROOT/artifacts" && pwd)"
USERS_ROOT="$(cd "$DATA_ROOT/users" && pwd)"

export AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT="$FRONTEND_PORT"
export AI_DECISION_STUDIO_BASELINE_ROOT="$BASELINE_ROOT"
export AI_DECISION_STUDIO_RUNTIME_ROOT="$RUNTIME_ROOT"
export AI_DECISION_STUDIO_ARTIFACT_ROOT="$ARTIFACT_ROOT"
export AI_DECISION_STUDIO_USERS_ROOT="$USERS_ROOT"

# Safe local defaults for this smoke. Real Oracle deployment should set these in .env.oracle.
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://ollama:11434/v1}"
export OLLAMA_HOSTED_BASE_URL="${OLLAMA_HOSTED_BASE_URL:-https://ollama.com/api}"
export HUGGINGFACE_INFERENCE_BASE_URL="${HUGGINGFACE_INFERENCE_BASE_URL:-https://router.huggingface.co/v1}"
export EVIDENCEOPS_REPOSITORY_BACKEND="${EVIDENCEOPS_REPOSITORY_BACKEND:-local}"
# Do not inherit external integration endpoints in the Oracle-like local smoke.
# Real Oracle deployments should set these in .env.oracle.
if [ "$EVIDENCEOPS_REPOSITORY_BACKEND" = "local" ]; then
  export EVIDENCEOPS_NEXTCLOUD_BASE_URL=""
  export EVIDENCEOPS_NEXTCLOUD_USERNAME=""
  export EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD=""
  export EVIDENCEOPS_TRELLO_API_KEY=""
  export EVIDENCEOPS_TRELLO_TOKEN=""
  export EVIDENCEOPS_NOTION_API_KEY=""
fi


mkdir -p "$(dirname "$REPORT")"

echo "== Oracle-like compose smoke =="
echo "compose=$COMPOSE_FILE"
echo "data_root=$DATA_ROOT"
echo "frontend=$FRONTEND_BASE_URL"
echo "baseline=$AI_DECISION_STUDIO_BASELINE_ROOT"
echo "runtime=$AI_DECISION_STUDIO_RUNTIME_ROOT"
echo "artifacts=$AI_DECISION_STUDIO_ARTIFACT_ROOT"
echo "users=$AI_DECISION_STUDIO_USERS_ROOT"
echo "report=$REPORT"

echo
echo "== Compose config =="
docker compose -f "$COMPOSE_FILE" config -q

cleanup() {
  if [ "${AI_DECISION_STUDIO_ORACLE_SMOKE_KEEP_STACK:-0}" != "1" ]; then
    echo
    echo "== Cleanup Oracle-like smoke stack =="
    docker compose -f "$COMPOSE_FILE" down --remove-orphans
  fi
}
trap cleanup EXIT

echo
echo "== Build Oracle-like images =="
docker compose -f "$COMPOSE_FILE" build

echo
echo "== Start Oracle-like stack =="
docker compose -f "$COMPOSE_FILE" up -d

echo
echo "== Wait for health =="
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
from urllib.request import urlopen

frontend = f"http://127.0.0.1:{os.environ.get('AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT', '8069')}"
report_path = os.environ.get(
    "AI_DECISION_STUDIO_ORACLE_COMPOSE_SMOKE_REPORT",
    "../ai_decision_studio_functional_baseline/parity_reports/oracle_like_compose_smoke_report.json",
)

def get(path):
    print(f"GET {path}")
    try:
        return json.loads(urlopen(frontend + path, timeout=90).read().decode("utf-8"))
    except Exception as exc:
        print(f"FAILED {path}: {type(exc).__name__}: {exc}")
        raise

health = get("/health")
workflows = get("/api/product/workflows")
documents = get("/api/product/document-library")
artifacts = get("/api/lab/artifacts")
evidenceops = get("/api/lab/evidenceops")

summary = {
    "health": health,
    "workflow_count": len(workflows.get("workflows") or []),
    "document_count": len(documents.get("documents") or []),
    "artifact_summary": artifacts.get("summary"),
    "evidenceops_summary": evidenceops.get("summary"),
}

evidenceops_summary = summary["evidenceops_summary"] or {}

checks = {
    "health_ok": bool(health.get("ok")),
    "workflow_count_gte_4": summary["workflow_count"] >= 4,
    "document_count_gte_10": summary["document_count"] >= 10,
    "artifacts_visible": int((summary["artifact_summary"] or {}).get("totalArtifacts") or 0) > 0,
    "evidenceops_endpoint_ok": bool(evidenceops.get("ok")),
    "evidenceops_backend_known": evidenceops_summary.get("repositoryBackend") in {"local", "nextcloud_webdav"},
    "evidenceops_tools_render": int(evidenceops_summary.get("toolsTotal") or 0) > 0,
}

report = {
    "ok": all(checks.values()),
    "frontend": frontend,
    "checks": checks,
    "summary": summary,
}

os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Oracle-like compose smoke completed =="
