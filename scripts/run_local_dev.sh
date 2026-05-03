#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.local}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
elif [[ -f ".env" ]]; then
  echo "WARN: $ENV_FILE not found; falling back to legacy .env." >&2
  set -a
  source ".env"
  set +a
else
  echo "WARN: no .env.local or .env found; using process defaults." >&2
fi

echo "Start API in one terminal:"
echo "  python3 main_product_api.py"
echo
echo "Start frontend in another terminal:"
echo "  npm --prefix frontend run dev"
echo
echo "Expected API:"
echo "  http://${PRODUCT_API_SERVER_NAME:-127.0.0.1}:${PRODUCT_API_SERVER_PORT:-8011}/health"
