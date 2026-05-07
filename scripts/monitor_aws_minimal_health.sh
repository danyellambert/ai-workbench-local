#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8071}}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.aws-slim.yml}"
DISK_WARN_PERCENT="${AI_DECISION_STUDIO_DISK_WARN_PERCENT:-85}"
DISK_FAIL_PERCENT="${AI_DECISION_STUDIO_DISK_FAIL_PERCENT:-95}"

echo "== AI Decision Studio minimal health =="
echo "base_url=$BASE_URL"
echo "project=$PROJECT_NAME"
echo "compose_file=$COMPOSE_FILE"
echo "disk_warn_percent=$DISK_WARN_PERCENT"
echo "disk_fail_percent=$DISK_FAIL_PERCENT"

echo
echo "== disk =="
df -h /
used_percent="$(df -P / | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
echo "disk_used_percent=$used_percent"

if [ "$used_percent" -ge "$DISK_FAIL_PERCENT" ]; then
  echo "ERROR: disk usage ${used_percent}% >= fail threshold ${DISK_FAIL_PERCENT}%" >&2
  exit 2
fi

if [ "$used_percent" -ge "$DISK_WARN_PERCENT" ]; then
  echo "WARNING: disk usage ${used_percent}% >= warn threshold ${DISK_WARN_PERCENT}%"
fi

echo
echo "== docker system df =="
docker system df || true

echo
echo "== compose services =="
if [ -f "$COMPOSE_FILE" ]; then
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps
else
  echo "WARNING: compose file not found: $COMPOSE_FILE"
fi

echo
echo "== public health =="
curl -fsS "$BASE_URL/health"
echo

echo
echo "OK: minimal health check passed"
