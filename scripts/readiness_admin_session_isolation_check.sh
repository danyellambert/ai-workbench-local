#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8071}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"

usage() {
  cat <<'USAGE'
Usage:
  BASE_URL=http://127.0.0.1:8071 scripts/readiness_admin_session_isolation_check.sh

Optional env:
  BASE_URL
  ADMIN_USERNAME
  ADMIN_PASSWORD

Notes:
  - If ADMIN_PASSWORD is not provided, the script prompts through /dev/tty.
  - Do not pass real admin passwords on the command line.
  - This check uses two independent cookie jars:
      A logs in as admin.
      B must remain public.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --base-url)
      BASE_URL="${2:?missing value for --base-url}"
      shift 2
      ;;
    --username)
      ADMIN_USERNAME="${2:?missing value for --username}"
      shift 2
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

if [ -z "$ADMIN_PASSWORD" ]; then
  if [ ! -r /dev/tty ]; then
    echo "ERROR: ADMIN_PASSWORD is required when /dev/tty is unavailable." >&2
    exit 1
  fi

  printf "Admin password for %s: " "$ADMIN_USERNAME" > /dev/tty
  stty -echo < /dev/tty
  IFS= read -r ADMIN_PASSWORD < /dev/tty
  stty echo < /dev/tty
  printf "\n" > /dev/tty
fi

COOKIE_A="$(mktemp /tmp/ads_cookie_a.XXXXXX)"
COOKIE_B="$(mktemp /tmp/ads_cookie_b.XXXXXX)"
LOGIN_BODY="$(mktemp /tmp/ads_login_body.XXXXXX.json)"
LOGOUT_BODY="$(mktemp /tmp/ads_logout_body.XXXXXX.json)"

cleanup() {
  rm -f "$COOKIE_A" "$COOKIE_B" "$LOGIN_BODY" "$LOGOUT_BODY"
}
trap cleanup EXIT

ADMIN_USERNAME="$ADMIN_USERNAME" ADMIN_PASSWORD="$ADMIN_PASSWORD" python3 - <<'PY' > "$LOGIN_BODY"
import json
import os

print(json.dumps({
    "username": os.environ["ADMIN_USERNAME"],
    "password": os.environ["ADMIN_PASSWORD"],
}))
PY

chmod 600 "$LOGIN_BODY"
printf '{}' > "$LOGOUT_BODY"
chmod 600 "$LOGOUT_BODY"

echo "== Admin session isolation readiness =="
echo "base_url=$BASE_URL"

curl_json() {
  local cookie_file="$1"
  local method="$2"
  local path="$3"
  local body_file="${4:-}"

  if [ -n "$body_file" ]; then
    curl -fsS -c "$cookie_file" -b "$cookie_file" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json" \
      -X "$method" \
      "$BASE_URL$path" \
      --data-binary "@$body_file"
  else
    curl -fsS -c "$cookie_file" -b "$cookie_file" \
      -H "Accept: application/json" \
      -X "$method" \
      "$BASE_URL$path"
  fi
}

curl_json "$COOKIE_A" GET "/api/auth/session" > /tmp/ads_session_a_before.json
curl_json "$COOKIE_B" GET "/api/auth/session" > /tmp/ads_session_b_before.json

LOGIN_STATUS="$(
  curl -sS -c "$COOKIE_A" -b "$COOKIE_A" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -X POST "$BASE_URL/api/auth/admin/login" \
    --data-binary @"$LOGIN_BODY" \
    -o /tmp/ads_admin_login_a.json \
    -w "%{http_code}"
)"

if [ "$LOGIN_STATUS" != "200" ]; then
  echo "ERROR: admin login failed with HTTP $LOGIN_STATUS" >&2
  python3 -m json.tool /tmp/ads_admin_login_a.json >&2 || cat /tmp/ads_admin_login_a.json >&2
  exit 1
fi

curl_json "$COOKIE_A" GET "/api/auth/session" > /tmp/ads_session_a_after_login.json
curl_json "$COOKIE_B" GET "/api/auth/session" > /tmp/ads_session_b_after_login.json

python3 - <<'PY'
import json
from pathlib import Path

def load(path: str) -> dict:
    return json.loads(Path(path).read_text())

def role(payload: dict) -> str:
    identity = payload.get("identity") or {}
    auth = payload.get("auth") or {}
    return identity.get("role") or auth.get("role") or ("admin" if payload.get("is_admin") else "public")

def can_write(payload: dict):
    return (payload.get("identity") or {}).get("can_write_global")

def can_publish(payload: dict):
    return (payload.get("identity") or {}).get("can_publish_external")

a_before = load("/tmp/ads_session_a_before.json")
b_before = load("/tmp/ads_session_b_before.json")
a_after = load("/tmp/ads_session_a_after_login.json")
b_after = load("/tmp/ads_session_b_after_login.json")

assert role(a_before) == "public", a_before
assert role(b_before) == "public", b_before
assert role(a_after) == "admin", a_after
assert role(b_after) == "public", b_after

assert can_write(a_after) is True, a_after
assert can_publish(a_after) is True, a_after
assert can_write(b_after) is False, b_after
assert can_publish(b_after) is False, b_after

print("A before:", role(a_before), can_write(a_before), can_publish(a_before))
print("B before:", role(b_before), can_write(b_before), can_publish(b_before))
print("A after:", role(a_after), can_write(a_after), can_publish(a_after))
print("B after:", role(b_after), can_write(b_after), can_publish(b_after))
print("OK: admin login is isolated to cookie jar A.")
PY

curl_json "$COOKIE_A" POST "/api/auth/admin/logout" "$LOGOUT_BODY" > /tmp/ads_admin_logout_a.json
curl_json "$COOKIE_A" GET "/api/auth/session" > /tmp/ads_session_a_after_logout.json
curl_json "$COOKIE_B" GET "/api/auth/session" > /tmp/ads_session_b_final.json

python3 - <<'PY'
import json
from pathlib import Path

def load(path: str) -> dict:
    return json.loads(Path(path).read_text())

def role(payload: dict) -> str:
    identity = payload.get("identity") or {}
    auth = payload.get("auth") or {}
    return identity.get("role") or auth.get("role") or ("admin" if payload.get("is_admin") else "public")

a = load("/tmp/ads_session_a_after_logout.json")
b = load("/tmp/ads_session_b_final.json")

assert role(a) == "public", a
assert role(b) == "public", b

print("A after logout:", role(a))
print("B final:", role(b))
print("OK: admin logout is isolated to cookie jar A.")
PY

echo "OK: admin session isolation readiness passed."
