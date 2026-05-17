#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.conda-env/bin/python}"

if [[ $# -lt 2 ]]; then
  echo "Usage: bash bin/render_ppt_creator.sh <input.json> <output.pptx>"
  exit 1
fi

exec "$PYTHON_BIN" -m ppt_creator.cli render "$1" "$2"
