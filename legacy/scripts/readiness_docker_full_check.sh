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
      echo "Usage: legacy/scripts/readiness_docker_full_check.sh [--skip-build] [--keep-up]" >&2
      exit 2
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="legacy/compose/docker-compose.frontend-public-demo.yml"

if [ -z "${AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT:-}" ]; then
  echo "Missing AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT" >&2
  echo "Example:" >&2
  echo 'export AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT="$(cd runtime/ai_decision_studio_functional_baseline/current_backend_smoke_overlay && pwd)"' >&2
  exit 1
fi

export AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT="${AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT:-8013}"
export AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8059}"
export AI_DECISION_STUDIO_FRONTEND_BASE_URL="${AI_DECISION_STUDIO_FRONTEND_BASE_URL:-http://127.0.0.1:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT}}"

cleanup() {
  if [ "$KEEP_UP" != "1" ]; then
    docker compose -f "$COMPOSE_FILE" down >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "== AI Decision Studio Docker full readiness check =="
echo "baseline=$AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT"
echo "api_port=$AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT"
echo "frontend_port=$AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT"
echo "frontend_base_url=$AI_DECISION_STUDIO_FRONTEND_BASE_URL"

echo
echo "== 1/4 Public demo Docker smoke =="
if [ "$SKIP_BUILD" = "1" ]; then
  legacy/scripts/smoke_docker_public_demo.sh --skip-build --keep-up
else
  legacy/scripts/smoke_docker_public_demo.sh --keep-up
fi

echo
echo "== 2/4 Document review workflow write smoke =="
scripts/smoke_docker_workflow_write.sh

echo
echo "== 3/4 Policy comparison workflow write smoke =="
scripts/smoke_docker_policy_comparison_write.sh

echo
echo "== 4/4 Frontend workflow UI smoke =="
scripts/smoke_frontend_docker_workflows_ui.sh

echo
echo "== Full readiness check passed =="
if [ "$KEEP_UP" = "1" ]; then
  echo "Stack kept up because --keep-up was provided."
else
  echo "Stack will be stopped by cleanup."
fi
