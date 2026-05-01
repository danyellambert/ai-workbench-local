#!/usr/bin/env bash
set -euo pipefail

HOST="${PPT_CREATOR_API_HOST:-0.0.0.0}"
PORT="${PPT_CREATOR_API_PORT:-8787}"
ASSET_ROOT="${PPT_CREATOR_API_ASSET_ROOT:-/app/examples}"

echo "[INFO] Starting ppt_creator API in container mode"
echo "[INFO] host=$HOST port=$PORT asset_root=$ASSET_ROOT"

exec python -m ppt_creator.api --host "$HOST" --port "$PORT" --asset-root "$ASSET_ROOT"