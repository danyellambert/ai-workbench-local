#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"

if [ "$MODE" != "--dry-run" ] && [ "$MODE" != "--execute" ]; then
  echo "Usage: $0 --dry-run|--execute" >&2
  exit 2
fi

REPO="${REPO:-danyellambert/ai-workbench-local}"
DEPLOY_SHA="${DEPLOY_SHA:?DEPLOY_SHA is required}"
APP_DIR="${APP_DIR:-/opt/ai-decision-studio/app}"
APP_USER="${APP_USER:-ubuntu}"

DEPLOY_ROOT="$(dirname "$APP_DIR")"
DATA_ROOT="${DATA_ROOT:-$DEPLOY_ROOT/data}"
SECRET_ROOT="${SECRET_ROOT:-$DEPLOY_ROOT/secrets}"
GOLDEN_ROOT="${GOLDEN_ROOT:-$DEPLOY_ROOT/golden_baseline}"
NEXTCLOUD_ARCHIVE="${NEXTCLOUD_ARCHIVE:-$GOLDEN_ROOT/nextcloud-golden-baseline-v1.tar.gz}"

RELEASE_ID="$(date -u +%Y%m%d_%H%M%S)_${DEPLOY_SHA:0:12}"
STAGE="/tmp/ads_ssm_code_only_${RELEASE_ID}"
SOURCE_PARENT="$STAGE/source"
BUNDLE_PARENT="$STAGE/bundle"
NEW_APP_PARENT="$STAGE/new_app"
APP_BACKUP_ROOT="$DEPLOY_ROOT/backups"
APP_BACKUP="$APP_BACKUP_ROOT/app_before_${RELEASE_ID}.tar.gz"

ARCHIVE_PATH="$BUNDLE_PARENT/ai-decision-studio-app-bundle.tar.gz"
BUNDLE_ROOT="$BUNDLE_PARENT/ai-decision-studio-app-bundle"

section() {
  echo
  echo "============================================================"
  echo "## $1"
  echo "============================================================"
}

section "0. SSM code-only deploy"
echo "mode=$MODE"
echo "repo=$REPO"
echo "deploy_sha=$DEPLOY_SHA"
echo "app_dir=$APP_DIR"
echo "stage=$STAGE"

section "1. Host preflight"
hostname
whoami
date -u +%Y-%m-%dT%H:%M:%SZ
df -h /

command -v curl >/dev/null
command -v tar >/dev/null
command -v rsync >/dev/null
command -v docker >/dev/null
docker compose version

FREE_KB="$(df --output=avail -k / | tail -n 1 | tr -d ' ')"
MIN_FREE_KB="${AWS_CODE_ONLY_MIN_FREE_KB:-3000000}"

echo "free_kb=$FREE_KB"
echo "min_free_kb=$MIN_FREE_KB"

if [ "$FREE_KB" -lt "$MIN_FREE_KB" ]; then
  echo "ERROR: insufficient disk space for code-only deploy." >&2
  exit 11
fi

section "2. Persistent paths guardrail"

for p in \
  "$DEPLOY_ROOT" \
  "$APP_DIR" \
  "$DATA_ROOT" \
  "$DATA_ROOT/baseline" \
  "$DATA_ROOT/runtime" \
  "$DATA_ROOT/artifacts" \
  "$DATA_ROOT/users" \
  "$SECRET_ROOT" \
  "$GOLDEN_ROOT" \
  "$NEXTCLOUD_ARCHIVE" \
  "$APP_DIR/.env.aws"
do
  if [ -e "$p" ]; then
    echo "OK $p"
  else
    echo "MISSING $p" >&2
    exit 10
  fi
done

echo
echo "-- permissions --"
stat -c "%a %U:%G %n" "$SECRET_ROOT"
stat -c "%a %U:%G %n" "$APP_DIR/.env.aws"

test "$(stat -c %a "$SECRET_ROOT")" = "700"
test "$(stat -c %a "$APP_DIR/.env.aws")" = "600"

section "3. Docker volumes guardrail"

for v in \
  ai-decision-studio_caddy_config \
  ai-decision-studio_caddy_data \
  ai-decision-studio_nextcloud_app \
  ai-decision-studio_ollama_data \
  ai-decision-studio_ppt_creator_workspace
do
  docker volume inspect "$v" >/dev/null
  echo "OK $v"
done

echo
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

section "4. Current health"
curl -fsS http://127.0.0.1:8071/health || true

section "5. Download release source"

rm -rf "$STAGE"
mkdir -p "$SOURCE_PARENT" "$BUNDLE_PARENT" "$NEW_APP_PARENT" "$APP_BACKUP_ROOT"

SOURCE_TARBALL="$STAGE/source.tar.gz"
SOURCE_URL="https://github.com/${REPO}/archive/${DEPLOY_SHA}.tar.gz"

echo "source_url=$SOURCE_URL"

curl -fsSL "$SOURCE_URL" -o "$SOURCE_TARBALL"
tar -xzf "$SOURCE_TARBALL" -C "$SOURCE_PARENT"

SOURCE_DIR="$(find "$SOURCE_PARENT" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

if [ -z "$SOURCE_DIR" ] || [ ! -d "$SOURCE_DIR" ]; then
  echo "ERROR: could not locate extracted source directory." >&2
  exit 12
fi

echo "source_dir=$SOURCE_DIR"

section "6. Build deployment bundle from release source"

cd "$SOURCE_DIR"

bash -n scripts/build_deployment_bundle.sh
bash -n scripts/deploy_aws.sh
bash -n scripts/smoke_aws.sh
bash -n scripts/readiness_multi_environment_contract_check.sh

AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_DIR="$BUNDLE_PARENT" \
AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_REPORT="$STAGE/deployment_bundle_report.json" \
bash scripts/build_deployment_bundle.sh

python3 - <<PY
import json
from pathlib import Path

report = Path("$STAGE/deployment_bundle_report.json")
data = json.loads(report.read_text())
checks = data.get("checks", {})

print("report:", report)
print("ok:", data.get("ok"))

for key in sorted(checks):
    print(f"checks.{key}: {checks[key]}")

assert data.get("ok") is True, "deployment bundle report ok != true"
assert checks.get("required_paths_present") is True
assert checks.get("no_real_env_files") is True
assert checks.get("no_secret_findings") is True
assert checks.get("no_runtime_or_baseline_data") is True
assert checks.get("no_macos_metadata") is True
assert not data.get("forbidden_files")
assert not data.get("secret_findings")
assert not data.get("runtime_or_heavy_path_findings")
PY

test -s "$ARCHIVE_PATH"
ls -lh "$ARCHIVE_PATH"

if [ "$MODE" = "--dry-run" ]; then
  section "7. Dry-run complete"
  cat <<'EOF'
DRY RUN OK.

No live app files were changed.
No containers were restarted.
No Docker volumes were removed.
No persistent runtime state was touched.
EOF
  rm -rf "$STAGE"
  exit 0
fi

section "7. Extract new app bundle"

tar -xzf "$ARCHIVE_PATH" -C "$NEW_APP_PARENT"

NEW_APP="$NEW_APP_PARENT/ai-decision-studio-app-bundle"

if [ ! -d "$NEW_APP" ]; then
  echo "ERROR: bundle did not extract to expected directory: $NEW_APP" >&2
  exit 13
fi

section "8. Validate new app with existing private .env.aws"

cp "$APP_DIR/.env.aws" "$NEW_APP/.env.aws"
chmod 600 "$NEW_APP/.env.aws"

cd "$NEW_APP"

python3 scripts/validate_aws_env_contract.py --env .env.aws

ENV_FILE=.env.aws docker compose \
  --env-file .env.aws \
  -p ai-decision-studio \
  -f docker-compose.aws.yml \
  config > "$STAGE/compose_config.yml"

grep -q "/opt/ai-decision-studio/secrets" "$STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/baseline" "$STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/runtime" "$STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/artifacts" "$STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/users" "$STAGE/compose_config.yml"

rm -f "$NEW_APP/.env.aws"

section "9. Backup current app code only"

tar --warning=no-file-changed --ignore-failed-read \
  --exclude='.env.aws' \
  --exclude='node_modules' \
  --exclude='frontend/node_modules' \
  -czf "$APP_BACKUP" \
  -C "$APP_DIR" .

test -s "$APP_BACKUP"
ls -lh "$APP_BACKUP"

section "10. Rsync new code into live app, preserving .env.aws"

rsync -a --delete \
  --exclude='.env.aws' \
  "$NEW_APP/" "$APP_DIR/"

chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env.aws"

test -s "$APP_DIR/.env.aws"
test "$(stat -c %a "$APP_DIR/.env.aws")" = "600"

section "11. Deploy with existing AWS script"

cd "$APP_DIR"

python3 scripts/validate_aws_env_contract.py --env .env.aws

COMPOSE_PROJECT_NAME=ai-decision-studio \
ENV_FILE=.env.aws \
bash scripts/deploy_aws.sh

section "12. Smoke test"

BASE_URL=http://127.0.0.1:8071 \
ENV_FILE=.env.aws \
COMPOSE_PROJECT_NAME=ai-decision-studio \
bash scripts/smoke_aws.sh

section "13. Post-deploy health"

curl -fsS http://127.0.0.1:8071/health

section "14. Safe Docker cleanup, no volumes"

docker builder prune -af || true
docker container prune -f || true
docker image prune -a -f || true

df -h /
docker system df || true

section "15. Cleanup staging and old app backups"

rm -rf "$STAGE"

ls -1t "$APP_BACKUP_ROOT"/app_before_*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f

section "16. Final verification"

docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

for p in \
  "$DATA_ROOT" \
  "$SECRET_ROOT" \
  "$GOLDEN_ROOT" \
  "$NEXTCLOUD_ARCHIVE"
do
  test -e "$p"
  echo "OK $p"
done

for v in \
  ai-decision-studio_caddy_config \
  ai-decision-studio_caddy_data \
  ai-decision-studio_nextcloud_app \
  ai-decision-studio_ollama_data \
  ai-decision-studio_ppt_creator_workspace
do
  docker volume inspect "$v" >/dev/null
  echo "OK $v"
done

curl -fsS http://127.0.0.1:8071/health

section "17. Done"

echo "✅ SSM code-only deploy completed successfully."
