#!/usr/bin/env bash
set -euo pipefail

KEEP_UP=0
SKIP_BUILD=0

for arg in "$@"; do
  case "$arg" in
    --keep-up)
      KEEP_UP=1
      ;;
    --skip-build)
      SKIP_BUILD=1
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: scripts/smoke_docker_public_demo.sh [--skip-build] [--keep-up]" >&2
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="docker-compose.frontend-public-demo.yml"

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Missing compose file: $COMPOSE_FILE" >&2
  exit 1
fi

if [ -z "${AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT:-}" ]; then
  echo "Missing AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT" >&2
  echo "Example:" >&2
  echo 'export AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT="$(cd ../ai_decision_studio_functional_baseline/current_backend_smoke_overlay && pwd)"' >&2
  exit 1
fi

if [ ! -d "$AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT" ]; then
  echo "Baseline overlay does not exist: $AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT" >&2
  exit 1
fi

export AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT="${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT:-8013}"
export AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8059}"

SNAP_OUT="${AI_DECISION_STUDIO_DOCKER_SMOKE_OUT:-../ai_decision_studio_functional_baseline/current_docker_script_smoke_snapshot}"
REPORT_OUT="${AI_DECISION_STUDIO_DOCKER_SMOKE_REPORT:-../ai_decision_studio_functional_baseline/current_docker_script_smoke_report.json}"

cleanup() {
  if [ "$KEEP_UP" != "1" ]; then
    docker compose -f "$COMPOSE_FILE" down >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "== Docker public demo smoke =="
echo "baseline=$AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT"
echo "api_port=$AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT"
echo "frontend_port=$AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT"
echo "snapshot=$SNAP_OUT"
echo "report=$REPORT_OUT"

echo
echo "== Compose config validation =="
docker compose -f "$COMPOSE_FILE" config >/tmp/ai_decision_studio_smoke_compose_config.yml

if [ "$SKIP_BUILD" != "1" ]; then
  echo
  echo "== Build images =="
  docker compose -f "$COMPOSE_FILE" build product-api frontend
fi

echo
echo "== Start stack =="
docker compose -f "$COMPOSE_FILE" up -d

wait_container_healthy() {
  container_name="$1"
  label="$2"

  echo
  echo "== Wait for $label =="
  for i in $(seq 1 60); do
    status="$(docker inspect "$container_name" --format '{{.State.Health.Status}}' 2>/dev/null || true)"
    state="$(docker inspect "$container_name" --format '{{.State.Status}}' 2>/dev/null || true)"
    echo "$label[$i] state=$state health=$status"

    if [ "$status" = "healthy" ]; then
      return 0
    fi

    if [ "$state" = "exited" ] || [ "$state" = "dead" ]; then
      echo
      echo "ERROR: $label exited. Logs:"
      docker logs --tail 160 "$container_name" 2>&1 || true
      return 1
    fi

    sleep 2
  done

  echo
  echo "ERROR: $label did not become healthy. Logs:"
  docker logs --tail 160 "$container_name" 2>&1 || true
  return 1
}

wait_container_healthy "ai-decision-studio-product-api-frontend-public-demo" "product-api"
wait_container_healthy "ai-decision-studio-frontend-public-demo" "frontend"

echo
echo "== Direct backend health =="
curl -fsS "http://127.0.0.1:${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT}/health" | python3 -m json.tool

echo
echo "== Frontend route =="
curl -fsS "http://127.0.0.1:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT}/" >/tmp/ai_decision_studio_smoke_frontend.html
echo "OK: frontend / responded"

echo
echo "== Frontend health proxy =="
curl -fsS "http://127.0.0.1:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT}/health" | python3 -m json.tool

echo
echo "== Frontend API proxy workflow count =="
FRONTEND_PORT="$AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT" python3 - <<'PY'
import json
import os
from urllib.request import urlopen

port = os.environ["FRONTEND_PORT"]
payload = json.loads(urlopen(f"http://127.0.0.1:{port}/api/product/workflows", timeout=20).read().decode("utf-8"))
workflows = payload.get("workflows") or []
result = {
    "ok": len(workflows) >= 4,
    "workflow_count": len(workflows),
    "workflow_ids": [item.get("workflow_id") or item.get("id") for item in workflows],
}
print(json.dumps(result, indent=2, ensure_ascii=False))
if not result["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Capture Golden Surface against Docker backend =="
rm -rf "$SNAP_OUT"

python3 scripts/capture_golden_surface_snapshot.py \
  --base-url "http://127.0.0.1:${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT}" \
  --out "$SNAP_OUT"

echo
echo "== Compare required counts =="
SNAP_OUT="$SNAP_OUT" REPORT_OUT="$REPORT_OUT" python3 - <<'PY'
import json
import os
from pathlib import Path

snap_out = Path(os.environ["SNAP_OUT"])
report_out = Path(os.environ["REPORT_OUT"])
raw = snap_out / "raw"
manifest_path = snap_out / "manifest.json"

def load(name: str):
    return json.loads((raw / f"{name}.json").read_text(encoding="utf-8"))

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

checks = {
    "product_workflows": len(load("product_workflows").get("workflows") or []),
    "product_documents": len(load("product_document_library").get("documents") or []),
    "product_run_history": len(load("product_run_history").get("runs") or []),
    "product_artifacts": len(load("product_artifacts").get("artifacts") or []),
    "lab_artifacts": len(load("lab_artifacts").get("artifacts") or []),
    "evidenceops_actions": len(load("lab_evidenceops").get("actions") or []),
}

minimums = {
    "product_workflows": 4,
    "product_documents": 17,
    "product_run_history": 100,
    "product_artifacts": 100,
    "lab_artifacts": 80,
    "evidenceops_actions": 72,
}

failures = {
    key: {"actual": checks[key], "expected_min": expected}
    for key, expected in minimums.items()
    if checks.get(key, 0) < expected
}

if manifest.get("errors"):
    failures["golden_surface_errors"] = manifest.get("errors")

result = {
    "ok": not bool(failures),
    "snapshot": str(snap_out),
    "checks": checks,
    "failures": failures,
}

report_out.parent.mkdir(parents=True, exist_ok=True)
report_out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(result, indent=2, ensure_ascii=False))

if not result["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Docker public demo smoke completed =="
if [ "$KEEP_UP" = "1" ]; then
  echo "Stack kept up because --keep-up was provided."
else
  echo "Stack will be stopped by cleanup."
fi
