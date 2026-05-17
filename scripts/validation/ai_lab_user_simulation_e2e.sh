#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"


OUT_DIR="${OUT_DIR:-$REPO_ROOT/.tmp_ai_lab_user_simulation}"

export PRODUCT_API_REUSE_EXISTING="${PRODUCT_API_REUSE_EXISTING:-0}"
export FRONTEND_REUSE_EXISTING="${FRONTEND_REUSE_EXISTING:-0}"
export AI_LAB_WORKFLOW_TIMEOUT_SECONDS="${AI_LAB_WORKFLOW_TIMEOUT_SECONDS:-120}"
export OUT_DIR

"$REPO_ROOT/scripts/validation/ai_lab_validation_e2e.sh" "$@"

echo ""
echo "AI Lab user simulation artifacts saved to: $OUT_DIR"
echo "- summary: $OUT_DIR/summary.md"
echo "- page assessments: $OUT_DIR/page-assessments.md"
echo "- screenshots: $OUT_DIR/screenshots"
echo "- browser traces: $OUT_DIR/browser"
echo "- api captures: $OUT_DIR/api"
