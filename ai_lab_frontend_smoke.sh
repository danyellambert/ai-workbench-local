#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/.tmp_ai_lab_e2e}"

source "$REPO_ROOT/scripts/ai_lab_shell_lib.sh"

reset_ai_lab_output_dir "$OUT_DIR"
write_ai_lab_run_meta "$OUT_DIR" "./ai_lab_frontend_smoke.sh"
ensure_rollup_native "$REPO_ROOT"

FRONTEND_DIR="$REPO_ROOT/frontend"
cd "$FRONTEND_DIR"

echo "[ai-lab:frontend] repo root: $REPO_ROOT" | tee "$OUT_DIR/frontend-smoke.log"
echo "[ai-lab:frontend] output dir: $OUT_DIR" | tee -a "$OUT_DIR/frontend-smoke.log"
echo "[ai-lab:frontend] running typecheck..." | tee -a "$OUT_DIR/frontend-smoke.log"
node ./node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit 2>&1 | tee -a "$OUT_DIR/frontend-smoke.log"

echo "[ai-lab:frontend] running vitest smoke..." | tee -a "$OUT_DIR/frontend-smoke.log"
node ./node_modules/vitest/vitest.mjs run src/pages/AiLabPages.test.tsx src/pages/ActionPlanPage.test.tsx 2>&1 | tee -a "$OUT_DIR/frontend-smoke.log"
