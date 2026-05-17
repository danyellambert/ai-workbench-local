#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 2 ]]; then
  echo "Usage: bash bin/render_ppt_creator_docker.sh <input.json> <output.pptx>"
  exit 1
fi

docker build -t ppt-creator "$ROOT"
docker run --rm -v "$ROOT:/work" ppt-creator python -m ppt_creator.cli render "/work/$1" "/work/$2"
