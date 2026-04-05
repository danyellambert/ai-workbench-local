#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT/.env" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "${line//[[:space:]]/}" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    export "$line"
  done < "$ROOT/.env"
fi

APP_ROOT="${PPT_CREATOR_APP_ROOT:-/Users/danyellambert/ppt_creator_app}"
PYTHON_BIN="${PPT_CREATOR_APP_PYTHON_BIN:-$APP_ROOT/.conda-env/bin/python}"
HOST="${PPT_CREATOR_APP_HOST:-127.0.0.1}"
PORT="${PPT_CREATOR_APP_PORT:-8787}"
ASSET_ROOT="${PPT_CREATOR_APP_ASSET_ROOT:-$APP_ROOT/examples}"

if [[ ! -d "$APP_ROOT" ]]; then
  echo "[ERROR] PPT Creator app root not found: $APP_ROOT"
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo "[ERROR] Could not resolve a Python binary to launch ppt_creator_app"
  exit 1
fi

echo "[INFO] Starting ppt_creator_app in host-native mode"
echo "[INFO] app_root=$APP_ROOT"
echo "[INFO] python=$PYTHON_BIN"
echo "[INFO] host=$HOST port=$PORT asset_root=$ASSET_ROOT"

cd "$APP_ROOT"
exec "$PYTHON_BIN" -m ppt_creator.api --host "$HOST" --port "$PORT" --asset-root "$ASSET_ROOT"