#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.local}"
API_HOST="${PRODUCT_API_SERVER_NAME:-127.0.0.1}"
API_PORT="${PRODUCT_API_SERVER_PORT:-8011}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
LOG_DIR="${LOG_DIR:-/tmp/ai-decision-studio-local-dev}"
CHECK_ONLY="false"
PRINT_ONLY="false"

usage() {
  cat <<'USAGE'
Usage:
  scripts/run_local_dev.sh
  scripts/run_local_dev.sh --check
  scripts/run_local_dev.sh --print-only

Optional env:
  ENV_FILE=.env.local
  PRODUCT_API_SERVER_NAME=127.0.0.1
  PRODUCT_API_SERVER_PORT=8011
  FRONTEND_HOST=127.0.0.1
  FRONTEND_PORT=5173
  LOG_DIR=/tmp/ai-decision-studio-local-dev

Behavior:
  - Loads .env.local by default.
  - Falls back to legacy .env only for local developer convenience.
  - Starts product API and Vite frontend together.
  - Uses npm --prefix frontend run dev:frontend so the frontend script does not
    spawn a second product API.
  - Ctrl+C stops both child processes.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --check)
      CHECK_ONLY="true"
      shift
      ;;
    --print-only)
      PRINT_ONLY="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

trim_string() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

load_dotenv_file() {
  local file="$1"
  local line stripped key value
  local loaded=0
  local skipped=0

  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    stripped="$(trim_string "$line")"

    if [ -z "$stripped" ] || [[ "$stripped" == \#* ]]; then
      continue
    fi

    if [[ "$stripped" == export\ * ]]; then
      stripped="${stripped#export }"
      stripped="$(trim_string "$stripped")"
    fi

    if [[ "$stripped" != *"="* ]]; then
      skipped=$((skipped + 1))
      continue
    fi

    key="$(trim_string "${stripped%%=*}")"
    value="$(trim_string "${stripped#*=}")"

    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      skipped=$((skipped + 1))
      continue
    fi

    if [ "${#value}" -ge 2 ]; then
      if { [[ "${value:0:1}" == '"' ]] && [[ "${value: -1}" == '"' ]]; } || { [[ "${value:0:1}" == "'" ]] && [[ "${value: -1}" == "'" ]]; }; then
        value="${value:1:${#value}-2}"
      fi
    fi

    export "$key=$value"
    loaded=$((loaded + 1))
  done < "$file"

  echo "loaded_env_keys=$loaded"
  if [ "$skipped" -gt 0 ]; then
    echo "WARN: skipped $skipped non dotenv line(s) in $file" >&2
  fi
}

load_env() {
  if [ -f "$ENV_FILE" ]; then
    load_dotenv_file "$ENV_FILE"
    echo "env_file=$ENV_FILE"
  elif [ -f ".env" ]; then
    echo "WARN: $ENV_FILE not found; falling back to legacy .env for local dev." >&2
    load_dotenv_file ".env"
    echo "env_file=.env"
  else
    echo "WARN: no $ENV_FILE or .env found; using process defaults." >&2
    echo "env_file=<process-defaults>"
  fi

  API_HOST="${PRODUCT_API_SERVER_NAME:-$API_HOST}"
  API_PORT="${PRODUCT_API_SERVER_PORT:-$API_PORT}"
}


require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1" >&2
    exit 1
  fi
}

load_env

require_command python3
require_command npm
require_command curl

if [ ! -f "main_product_api.py" ]; then
  echo "ERROR: main_product_api.py not found. Run from repository root." >&2
  exit 1
fi

if [ ! -f "frontend/package.json" ]; then
  echo "ERROR: frontend/package.json not found. Run from repository root." >&2
  exit 1
fi

if [ "$PRINT_ONLY" = "true" ]; then
  cat <<EOF_PRINT
Start API:
  ENV_FILE=$ENV_FILE python3 main_product_api.py

Start frontend:
  VITE_PRODUCT_API_BASE_URL=http://$API_HOST:$API_PORT npm --prefix frontend run dev:frontend -- --host $FRONTEND_HOST --port $FRONTEND_PORT

Expected:
  API health: http://$API_HOST:$API_PORT/health
  Frontend:   http://$FRONTEND_HOST:$FRONTEND_PORT
EOF_PRINT
  exit 0
fi

if [ "$CHECK_ONLY" = "true" ]; then
  echo "== Local dev contract check =="
  echo "api_health=http://$API_HOST:$API_PORT/health"
  echo "frontend_url=http://$FRONTEND_HOST:$FRONTEND_PORT"
  echo "OK: local dev prerequisites are present."
  exit 0
fi

mkdir -p "$LOG_DIR"

API_LOG="$LOG_DIR/product-api.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

API_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "== Stopping local dev processes =="
  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${API_PID:-}" ] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "== Starting product API =="
echo "log=$API_LOG"
python3 main_product_api.py >"$API_LOG" 2>&1 &
API_PID="$!"

echo "api_pid=$API_PID"

echo "== Waiting for API health =="
for i in $(seq 1 60); do
  if curl -fsS "http://$API_HOST:$API_PORT/health" >/tmp/ads_local_dev_health.json 2>/dev/null; then
    echo "API health OK after ${i}s"
    cat /tmp/ads_local_dev_health.json
    echo
    break
  fi

  if ! kill -0 "$API_PID" >/dev/null 2>&1; then
    echo "ERROR: product API exited early. Last logs:" >&2
    tail -120 "$API_LOG" >&2 || true
    exit 1
  fi

  if [ "$i" = "60" ]; then
    echo "ERROR: API health did not become ready. Last logs:" >&2
    tail -160 "$API_LOG" >&2 || true
    exit 1
  fi

  sleep 1
done

echo "== Starting frontend =="
echo "log=$FRONTEND_LOG"
VITE_PRODUCT_API_BASE_URL="http://$API_HOST:$API_PORT" \
  npm --prefix frontend run dev:frontend -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
  >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID="$!"

echo "frontend_pid=$FRONTEND_PID"
echo
echo "Local dev is running:"
echo "  API:      http://$API_HOST:$API_PORT/health"
echo "  Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
echo "  Logs:     $LOG_DIR"
echo
echo "Press Ctrl+C to stop."

wait "$FRONTEND_PID"
