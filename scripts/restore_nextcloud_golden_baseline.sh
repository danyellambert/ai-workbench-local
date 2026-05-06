#!/usr/bin/env bash
set -euo pipefail

ARCHIVE=""
MANIFEST=""
EXPECTED_SHA=""
ENV_FILE="${ENV_FILE:-.env.oracle}"
PROJECT="${PROJECT:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.local.yml}"
OVERRIDE_FILE="${OVERRIDE_FILE:-docker-compose.aws-slim.yml}"
VOLUME="ai-decision-studio_nextcloud_app"
WEBDAV_USER="danyel"
ROOT_PATH="/EvidenceOpsDemo"
DELETE_ARCHIVE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --archive)
      ARCHIVE="${2:?}"
      shift 2
      ;;
    --manifest)
      MANIFEST="${2:?}"
      shift 2
      ;;
    --sha)
      EXPECTED_SHA="${2:?}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --project)
      PROJECT="${2:?}"
      shift 2
      ;;
    --volume)
      VOLUME="${2:?}"
      shift 2
      ;;
    --webdav-user)
      WEBDAV_USER="${2:?}"
      shift 2
      ;;
    --root-path)
      ROOT_PATH="${2:?}"
      shift 2
      ;;
    --delete-archive-after-restore)
      DELETE_ARCHIVE=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$ARCHIVE" ]; then
  echo "ERROR: --archive is required" >&2
  exit 1
fi

if [ ! -f "$ARCHIVE" ]; then
  echo "ERROR: archive not found: $ARCHIVE" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

if [ -z "$MANIFEST" ]; then
  CANDIDATE="${ARCHIVE%.tar.gz}.manifest.json"
  if [ -f "$CANDIDATE" ]; then
    MANIFEST="$CANDIDATE"
  fi
fi

COMPOSE_ARGS=(-p "$PROJECT" -f "$COMPOSE_FILE")

if [ -f "$OVERRIDE_FILE" ]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
fi

echo
echo "== Validate golden archive =="
python3 - "$ARCHIVE" "$MANIFEST" "$EXPECTED_SHA" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

archive = Path(sys.argv[1])
manifest_arg = sys.argv[2]
expected_sha = sys.argv[3].strip()

if manifest_arg and not expected_sha:
    manifest = Path(manifest_arg)
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        expected_sha = str(data.get("archive_sha256", "")).strip()

h = hashlib.sha256()
with archive.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)

actual_sha = h.hexdigest()

print(f"archive={archive}")
print(f"actual_sha256={actual_sha}")

if expected_sha:
    print(f"expected_sha256={expected_sha}")
    if actual_sha != expected_sha:
        raise SystemExit("ERROR: SHA mismatch")

print("OK: archive validated")
PY

if [ -z "${NEXTCLOUD_WEBDAV_PASSWORD:-}" ]; then
  echo
  read -r -s -p "Nextcloud WebDAV password/app-password for user ${WEBDAV_USER}: " NEXTCLOUD_WEBDAV_PASSWORD
  echo
  export NEXTCLOUD_WEBDAV_PASSWORD
fi

if [ -z "$NEXTCLOUD_WEBDAV_PASSWORD" ]; then
  echo "ERROR: empty Nextcloud password/app-password" >&2
  exit 1
fi

echo
echo "== Stop stack, keep volumes =="
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" down --remove-orphans

echo
echo "== Safety backup current Nextcloud volume =="
SAFETY_DIR="${AI_DECISION_STUDIO_NEXTCLOUD_SAFETY_BACKUP_DIR:-$HOME/ads_uploads/aws_nextcloud_safety_backups}"
mkdir -p "$SAFETY_DIR"

docker run --rm \
  -v "$VOLUME:/source:ro" \
  -v "$SAFETY_DIR:/backup" \
  alpine sh -lc 'cd /source && tar -czf /backup/nextcloud-before-golden-restore-$(date +%Y%m%d-%H%M%S).tar.gz .'

ARCHIVE_DIR="$(cd "$(dirname "$ARCHIVE")" && pwd)"
ARCHIVE_BASE="$(basename "$ARCHIVE")"

echo
echo "== Restore golden Nextcloud volume =="
docker run --rm \
  -v "$VOLUME:/target" \
  -v "$ARCHIVE_DIR:/backup:ro" \
  -e ARCHIVE_BASE="$ARCHIVE_BASE" \
  alpine sh -lc 'set -e; rm -rf /target/* /target/.[!.]* /target/..?* 2>/dev/null || true; tar -xzf "/backup/$ARCHIVE_BASE" -C /target'

echo
echo "== Start stack after restore =="
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" up -d

echo
echo "== Wait for Nextcloud =="
sleep 25

echo
echo "== Configure trusted domains =="
for item in "0=localhost" "1=127.0.0.1" "2=nextcloud" "3=127.0.0.1:8085"; do
  idx="${item%%=*}"
  value="${item#*=}"
  docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" \
    exec -T --user www-data nextcloud php occ config:system:set trusted_domains "$idx" --value="$value"
done

echo
echo "== Update ${ENV_FILE} WebDAV values =="
WEBDAV_USER="$WEBDAV_USER" ROOT_PATH="$ROOT_PATH" python3 - <<'PY'
import os
from pathlib import Path

p = Path(os.environ.get("ENV_FILE", ".env.oracle"))
lines = p.read_text(encoding="utf-8").splitlines()

user = os.environ["WEBDAV_USER"]
root_path = os.environ["ROOT_PATH"]
password = os.environ["NEXTCLOUD_WEBDAV_PASSWORD"]
quoted_password = "'" + password.replace("'", "'\"'\"'") + "'"

updates = {
    "EVIDENCEOPS_REPOSITORY_BACKEND": "nextcloud_webdav",
    "EVIDENCEOPS_NEXTCLOUD_BASE_URL": f"http://nextcloud/remote.php/dav/files/{user}",
    "EVIDENCEOPS_NEXTCLOUD_USERNAME": user,
    "EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD": quoted_password,
    "EVIDENCEOPS_NEXTCLOUD_ROOT_PATH": root_path,
    "NEXTCLOUD_ADMIN_USER": user,
}

seen = set()
out = []

for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        out.append(line)
        continue

    key = line.split("=", 1)[0].strip()
    if key in updates:
        if key not in seen:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        continue

    out.append(line)

for key, value in updates.items():
    if key not in seen:
        out.append(f"{key}={value}")

p.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY

chmod 600 "$ENV_FILE"

echo
echo "== Recreate product-api/frontend with updated env =="
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" up -d --force-recreate product-api frontend

sleep 15

echo
echo "== Containers =="
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" ps

echo
echo "== Readiness =="
scripts/readiness_nextcloud_golden_baseline_check.sh --env-file "$ENV_FILE"

if [ "$DELETE_ARCHIVE" -eq 1 ]; then
  rm -f "$ARCHIVE"
  if [ -n "$MANIFEST" ] && [ -f "$MANIFEST" ]; then
    rm -f "$MANIFEST"
  fi
fi

echo
echo "OK: Nextcloud golden baseline restored"
