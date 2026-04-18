#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/.tmp_ai_lab_e2e}"
PYTHON_BIN="${PYTHON_BIN:-python}"

source "$REPO_ROOT/scripts/ai_lab_shell_lib.sh"

PRESERVED_FRONTEND_SMOKE=""
if [ -f "$OUT_DIR/frontend-smoke.log" ]; then
  PRESERVED_FRONTEND_SMOKE="$(mktemp)"
  cp "$OUT_DIR/frontend-smoke.log" "$PRESERVED_FRONTEND_SMOKE"
fi

reset_ai_lab_output_dir "$OUT_DIR"
if [ -n "$PRESERVED_FRONTEND_SMOKE" ]; then
  mv "$PRESERVED_FRONTEND_SMOKE" "$OUT_DIR/frontend-smoke.log"
fi
write_ai_lab_run_meta "$OUT_DIR" "AI_LAB_WORKFLOW_TIMEOUT_SECONDS=${AI_LAB_WORKFLOW_TIMEOUT_SECONDS:-45} ./ai_lab_validation_e2e.sh"
ensure_rollup_native "$REPO_ROOT"

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434/v1}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-nemotron-3-nano:30b-cloud}"
export OLLAMA_AVAILABLE_MODELS="${OLLAMA_AVAILABLE_MODELS:-$OLLAMA_MODEL}"
export AI_LAB_WORKFLOW_PROVIDER="${AI_LAB_WORKFLOW_PROVIDER:-ollama}"
export AI_LAB_WORKFLOW_MODEL="${AI_LAB_WORKFLOW_MODEL:-$OLLAMA_MODEL}"
export PRODUCT_API_SERVER_NAME="${PRODUCT_API_SERVER_NAME:-127.0.0.1}"
export PRODUCT_API_REUSE_EXISTING="${PRODUCT_API_REUSE_EXISTING:-0}"
export FRONTEND_REUSE_EXISTING="${FRONTEND_REUSE_EXISTING:-0}"
export PRODUCT_API_SERVER_PORT="$(ai_lab_choose_port "${PRODUCT_API_SERVER_PORT:-8011}" "$PRODUCT_API_REUSE_EXISTING")"
export FRONTEND_DEV_PORT="$(ai_lab_choose_port "${FRONTEND_DEV_PORT:-8080}" "$FRONTEND_REUSE_EXISTING")"
export VITE_PRODUCT_API_BASE_URL="${VITE_PRODUCT_API_BASE_URL:-http://${PRODUCT_API_SERVER_NAME}:${PRODUCT_API_SERVER_PORT}}"
export AI_LAB_WORKFLOW_TIMEOUT_SECONDS="${AI_LAB_WORKFLOW_TIMEOUT_SECONDS:-45}"

cd "$REPO_ROOT"

echo "[ai-lab] repo root: $REPO_ROOT"
echo "[ai-lab] output dir: $OUT_DIR"
echo "[ai-lab] product api: http://${PRODUCT_API_SERVER_NAME}:${PRODUCT_API_SERVER_PORT}"
echo "[ai-lab] frontend: http://127.0.0.1:${FRONTEND_DEV_PORT}"
echo "[ai-lab] workflow provider: ${AI_LAB_WORKFLOW_PROVIDER}"
echo "[ai-lab] workflow model: ${AI_LAB_WORKFLOW_MODEL}"

"$PYTHON_BIN" "$REPO_ROOT/scripts/run_ai_lab_validation.py" \
  --output-dir "$OUT_DIR" \
  --start-product-api \
  --start-frontend \
  --run-playwright \
  --exercise-live \
  "$@"
