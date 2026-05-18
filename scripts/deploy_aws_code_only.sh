#!/usr/bin/env bash
set -euo pipefail

MODE="${1:---dry-run}"

if [ "$MODE" != "--dry-run" ] && [ "$MODE" != "--execute" ]; then
  echo "Usage: $0 --dry-run|--execute" >&2
  exit 2
fi

EC2_IP="${EC2_IP:-16.59.141.55}"
EC2_USER="${EC2_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/ai-decision-studio-aws.pem}"
REMOTE="${EC2_USER}@${EC2_IP}"

REMOTE_DEPLOY_ROOT="${REMOTE_DEPLOY_ROOT:-/opt/ai-decision-studio}"
REMOTE_APP_ROOT="${REMOTE_APP_ROOT:-$REMOTE_DEPLOY_ROOT/app}"
REMOTE_DATA_ROOT="${REMOTE_DATA_ROOT:-$REMOTE_DEPLOY_ROOT/data}"
REMOTE_SECRET_ROOT="${REMOTE_SECRET_ROOT:-$REMOTE_DEPLOY_ROOT/secrets}"
REMOTE_GOLDEN_ROOT="${REMOTE_GOLDEN_ROOT:-$REMOTE_DEPLOY_ROOT/golden_baseline}"

ARCHIVE="runtime/ai_decision_studio_functional_baseline/deployment_bundle/ai-decision-studio-app-bundle.tar.gz"
REPORT="runtime/ai_decision_studio_functional_baseline/parity_reports/deployment_bundle_report.json"

GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)"
RELEASE_ID="$(date -u +%Y%m%d_%H%M%S)_${GIT_SHA}"
REMOTE_STAGE="/tmp/ads_code_only_${RELEASE_ID}"

section() {
  echo
  echo "============================================================"
  echo "## $1"
  echo "============================================================"
}

section "0. Code-only deploy mode"
echo "mode=$MODE"
echo "remote=$REMOTE"
echo "release_id=$RELEASE_ID"
echo "remote_stage=$REMOTE_STAGE"

section "1. Local git context"
pwd
git branch --show-current
git log --oneline --decorate -5
echo
git status --short
echo

TRACKED_STATUS="$(git status --short --untracked-files=no)"
if [ -n "$TRACKED_STATUS" ]; then
  if [ "${ALLOW_DIRTY_CODE_ONLY:-0}" = "1" ]; then
    echo "WARN: existem alterações trackeadas não commitadas; prosseguindo porque ALLOW_DIRTY_CODE_ONLY=1."
    echo "$TRACKED_STATUS"
    echo
  else
    echo "ERROR: existem alterações trackeadas não commitadas."
    echo "$TRACKED_STATUS"
    echo
    echo "Faça commit/reverta antes, ou rode conscientemente com ALLOW_DIRTY_CODE_ONLY=1."
    exit 1
  fi
fi

section "2. Validate local scripts"
bash -n scripts/build_deployment_bundle.sh
bash -n scripts/deploy_aws.sh
bash -n scripts/smoke_aws.sh
bash -n scripts/readiness_multi_environment_contract_check.sh
echo "OK: local script syntax"

section "3. Generate and validate deployment bundle"
bash scripts/build_deployment_bundle.sh

python3 - <<'PY'
import json
from pathlib import Path

report = Path("runtime/ai_decision_studio_functional_baseline/parity_reports/deployment_bundle_report.json")
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

test -s "$ARCHIVE"
ls -lh "$ARCHIVE"

section "4. Remote read-only preflight"
ssh -i "$SSH_KEY" "$REMOTE" 'bash -s' <<'REMOTE_PREFLIGHT'
set -euo pipefail

REMOTE_DEPLOY_ROOT="/opt/ai-decision-studio"
REMOTE_APP_ROOT="/opt/ai-decision-studio/app"
REMOTE_DATA_ROOT="/opt/ai-decision-studio/data"
REMOTE_SECRET_ROOT="/opt/ai-decision-studio/secrets"
REMOTE_GOLDEN_ROOT="/opt/ai-decision-studio/golden_baseline"
REMOTE_NEXTCLOUD_ARCHIVE="/opt/ai-decision-studio/golden_baseline/nextcloud-golden-baseline-v1.tar.gz"

echo "-- host --"
hostname
whoami
date -u +%Y-%m-%dT%H:%M:%SZ
echo

echo "-- disk/docker before cleanup --"
df -h /
docker system df || true
echo

echo "-- safe preflight Docker cleanup before disk guardrail, no volumes --"
sudo find /tmp -maxdepth 1 -type d -name 'ads_code_only_*' -print -exec rm -rf {} + 2>/dev/null || true
sudo apt-get clean || true
sudo journalctl --vacuum-size=50M || true

docker builder prune -af || true
docker container prune -f || true
docker image prune -af || true

echo
echo "-- disk/docker after cleanup --"
df -h /
docker system df || true
echo

FREE_KB="$(df --output=avail -k / | tail -n 1 | tr -d ' ')"
MIN_FREE_KB="${AWS_CODE_ONLY_MIN_FREE_KB:-3000000}"

echo "-- disk guardrail --"
echo "free_kb=$FREE_KB"
echo "min_free_kb=$MIN_FREE_KB"

if [ "$FREE_KB" -lt "$MIN_FREE_KB" ]; then
  echo "ERROR: espaço livre insuficiente para code-only deploy." >&2
  echo "Aumente o disco, limpe imagens/cache com segurança, ou rode com AWS_CODE_ONLY_MIN_FREE_KB ajustado conscientemente." >&2
  exit 11
fi
echo

echo "-- required persistent paths --"
for p in \
  "$REMOTE_DEPLOY_ROOT" \
  "$REMOTE_APP_ROOT" \
  "$REMOTE_DATA_ROOT" \
  "$REMOTE_DATA_ROOT/baseline" \
  "$REMOTE_DATA_ROOT/runtime" \
  "$REMOTE_DATA_ROOT/artifacts" \
  "$REMOTE_DATA_ROOT/users" \
  "$REMOTE_SECRET_ROOT" \
  "$REMOTE_GOLDEN_ROOT" \
  "$REMOTE_NEXTCLOUD_ARCHIVE" \
  "$REMOTE_APP_ROOT/.env.aws"
do
  if [ -e "$p" ]; then
    echo "OK      $p"
  else
    echo "MISSING $p" >&2
    exit 10
  fi
done
echo

echo "-- permissions --"
stat -c "%a %U:%G %n" "$REMOTE_SECRET_ROOT"
stat -c "%a %U:%G %n" "$REMOTE_APP_ROOT/.env.aws"
test "$(stat -c %a "$REMOTE_SECRET_ROOT")" = "700"
test "$(stat -c %a "$REMOTE_APP_ROOT/.env.aws")" = "600"
echo

echo "-- project volumes must exist and must be preserved --"
for v in \
  ai-decision-studio_caddy_config \
  ai-decision-studio_caddy_data \
  ai-decision-studio_nextcloud_app \
  ai-decision-studio_ollama_data \
  ai-decision-studio_ppt_creator_workspace
do
  docker volume inspect "$v" >/dev/null
  echo "OK      $v"
done
echo

echo "-- current containers --"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo

echo "-- current app health --"
curl -fsS http://127.0.0.1:8071/health
echo
REMOTE_PREFLIGHT

if [ "$MODE" = "--dry-run" ]; then
  section "5. Dry-run complete"
  cat <<'EOF'
DRY RUN OK.

Nenhum arquivo remoto foi alterado.
Nenhum container foi reiniciado.
Nenhum volume foi removido.

Para executar de verdade depois:
  scripts/deploy_aws_code_only.sh --execute
EOF
  exit 0
fi

section "5. Upload bundle to remote staging"
ssh -i "$SSH_KEY" "$REMOTE" "rm -rf '$REMOTE_STAGE' && mkdir -p '$REMOTE_STAGE' && chmod 700 '$REMOTE_STAGE'"
scp -i "$SSH_KEY" "$ARCHIVE" "$REMOTE:$REMOTE_STAGE/ai-decision-studio-app-bundle.tar.gz"

section "6. Remote code-only app update"
ssh -i "$SSH_KEY" "$REMOTE" 'bash -s' <<REMOTE_DEPLOY
set -euo pipefail

REMOTE_DEPLOY_ROOT="$REMOTE_DEPLOY_ROOT"
REMOTE_APP_ROOT="$REMOTE_APP_ROOT"
REMOTE_DATA_ROOT="$REMOTE_DATA_ROOT"
REMOTE_SECRET_ROOT="$REMOTE_SECRET_ROOT"
REMOTE_GOLDEN_ROOT="$REMOTE_GOLDEN_ROOT"
REMOTE_STAGE="$REMOTE_STAGE"
RELEASE_ID="$RELEASE_ID"

NEW_APP="\$REMOTE_STAGE/app"
APP_BACKUP_ROOT="\$REMOTE_DATA_ROOT/backups/app_code"
APP_BACKUP="\$APP_BACKUP_ROOT/app_before_\$RELEASE_ID.tar.gz"

echo "-- create staging app --"
mkdir -p "\$NEW_APP" "\$APP_BACKUP_ROOT"
tar -xzf "\$REMOTE_STAGE/ai-decision-studio-app-bundle.tar.gz" \
  -C "\$NEW_APP" \
  --strip-components=1

echo "-- preserve remote .env.aws from current app --"
test -s "\$REMOTE_APP_ROOT/.env.aws"
install -m 600 "\$REMOTE_APP_ROOT/.env.aws" "\$NEW_APP/.env.aws"

echo "-- validate staged app before touching live app --"
cd "\$NEW_APP"
python3 scripts/validate_aws_env_contract.py --env .env.aws

ENV_FILE=.env.aws docker compose \
  --env-file .env.aws \
  -p ai-decision-studio \
  -f docker-compose.aws.yml \
  config > "\$REMOTE_STAGE/compose_config.yml"

grep -q "/opt/ai-decision-studio/secrets" "\$REMOTE_STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/baseline" "\$REMOTE_STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/runtime" "\$REMOTE_STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/artifacts" "\$REMOTE_STAGE/compose_config.yml"
grep -q "/opt/ai-decision-studio/data/users" "\$REMOTE_STAGE/compose_config.yml"

echo "-- backup current app code only --"
tar --warning=no-file-changed --ignore-failed-read \
  --exclude='.env.aws' \
  --exclude='node_modules' \
  --exclude='frontend/node_modules' \
  -czf "\$APP_BACKUP" \
  -C "\$REMOTE_APP_ROOT" .

test -s "\$APP_BACKUP"
ls -lh "\$APP_BACKUP"

echo "-- rsync staged app into live app, preserving .env.aws --"
rsync -a --delete \
  --exclude='.env.aws' \
  "\$NEW_APP/" "\$REMOTE_APP_ROOT/"

test -s "\$REMOTE_APP_ROOT/.env.aws"
test "\$(stat -c %a "\$REMOTE_APP_ROOT/.env.aws")" = "600"

echo "-- validate live app after code update --"
cd "\$REMOTE_APP_ROOT"
python3 scripts/validate_aws_env_contract.py --env .env.aws

ENV_FILE=.env.aws docker compose \
  --env-file .env.aws \
  -p ai-decision-studio \
  -f docker-compose.aws.yml \
  config > /tmp/ads_code_only_live_compose.yml

echo "-- deploy with existing AWS deploy script --"
COMPOSE_PROJECT_NAME=ai-decision-studio \
ENV_FILE=.env.aws \
bash scripts/deploy_aws.sh

echo "-- smoke after deploy --"
BASE_URL=http://127.0.0.1:8071 \
ENV_FILE=.env.aws \
COMPOSE_PROJECT_NAME=ai-decision-studio \
bash scripts/smoke_aws.sh

echo "-- post-deploy health --"
curl -fsS http://127.0.0.1:8071/health
echo

echo "-- post-deploy safe docker cleanup, no volumes --"
docker builder prune -af || true
docker container prune -f || true
docker image prune -a -f || true

df -h /
docker system df || true
echo

echo "-- cleanup staging only --"
rm -rf "\$REMOTE_STAGE"

echo "-- keep latest 3 app code backups --"
ls -1t "\$APP_BACKUP_ROOT"/app_before_*.tar.gz 2>/dev/null | tail -n +4 | xargs -r rm -f

echo "OK: code-only deploy completed."
REMOTE_DEPLOY

section "7. Final remote verification"
ssh -i "$SSH_KEY" "$REMOTE" 'bash -s' <<'REMOTE_VERIFY'
set -euo pipefail

echo "-- containers --"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo

echo "-- persistent dirs still present --"
for p in \
  /opt/ai-decision-studio/data \
  /opt/ai-decision-studio/secrets \
  /opt/ai-decision-studio/golden_baseline \
  /opt/ai-decision-studio/golden_baseline/nextcloud-golden-baseline-v1.tar.gz
do
  test -e "$p"
  echo "OK $p"
done
echo

echo "-- volumes still present --"
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

curl -fsS http://127.0.0.1:8071/health
echo
REMOTE_VERIFY

section "8. Done"
echo "✅ Code-only deploy completed successfully."
