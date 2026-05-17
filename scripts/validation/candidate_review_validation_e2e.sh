#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

OUT_DIR="${OUT_DIR:-$REPO_ROOT/.tmp_candidate_review_validation}"
PYTHON_BIN="${PYTHON_BIN:-python}"
source "$REPO_ROOT/scripts/ai_lab_shell_lib.sh"
reset_ai_lab_output_dir "$OUT_DIR"
write_ai_lab_run_meta "$OUT_DIR" "scripts/validation/candidate_review_validation_e2e.sh"
ensure_rollup_native "$REPO_ROOT"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434/v1}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-nemotron:30b}"
export OLLAMA_AVAILABLE_MODELS="${OLLAMA_AVAILABLE_MODELS:-$OLLAMA_MODEL}"
export PRODUCT_API_SERVER_NAME="${PRODUCT_API_SERVER_NAME:-127.0.0.1}"
export PRODUCT_API_REUSE_EXISTING="${PRODUCT_API_REUSE_EXISTING:-0}"
export FRONTEND_REUSE_EXISTING="${FRONTEND_REUSE_EXISTING:-0}"
export PRODUCT_API_SERVER_PORT="$(ai_lab_choose_port "${PRODUCT_API_SERVER_PORT:-8011}" "$PRODUCT_API_REUSE_EXISTING")"
export FRONTEND_DEV_PORT="$(ai_lab_choose_port "${FRONTEND_DEV_PORT:-8080}" "$FRONTEND_REUSE_EXISTING")"
export VITE_PRODUCT_API_BASE_URL="${VITE_PRODUCT_API_BASE_URL:-http://${PRODUCT_API_SERVER_NAME}:${PRODUCT_API_SERVER_PORT}}"
export CANDIDATE_REVIEW_CORPUS_ROOT="${CANDIDATE_REVIEW_CORPUS_ROOT:-$REPO_ROOT/data/corpus_revisado}"
export CANDIDATE_REVIEW_CANDIDATE_DOC_NAME="${CANDIDATE_REVIEW_CANDIDATE_DOC_NAME:-Sarah Chen - Senior ML Engineer CV.pdf}"
cd "$REPO_ROOT"
echo "[candidate-review] repo root: $REPO_ROOT"
echo "[candidate-review] output dir: $OUT_DIR"
echo "[candidate-review] product api: http://${PRODUCT_API_SERVER_NAME}:${PRODUCT_API_SERVER_PORT}"
echo "[candidate-review] frontend: http://127.0.0.1:${FRONTEND_DEV_PORT}"
echo "[candidate-review] corpus root: $CANDIDATE_REVIEW_CORPUS_ROOT"
echo "[candidate-review] candidate doc: $CANDIDATE_REVIEW_CANDIDATE_DOC_NAME"
echo "[candidate-review] ollama base url: $OLLAMA_BASE_URL"
echo "[candidate-review] ollama model: $OLLAMA_MODEL"
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_candidate_review_validation.py" \
  --output-dir "$OUT_DIR" \
  --product-api-url "http://${PRODUCT_API_SERVER_NAME}:${PRODUCT_API_SERVER_PORT}" \
  --frontend-url "http://127.0.0.1:${FRONTEND_DEV_PORT}" \
  --product-api-port "$PRODUCT_API_SERVER_PORT" \
  --frontend-port "$FRONTEND_DEV_PORT" \
  --corpus-root "$CANDIDATE_REVIEW_CORPUS_ROOT" \
  --candidate-doc-name "$CANDIDATE_REVIEW_CANDIDATE_DOC_NAME" \
  --ollama-model "$OLLAMA_MODEL" \
  --start-product-api \
  --start-frontend \
  --run-playwright \
  --exercise-live \
  "$@"
