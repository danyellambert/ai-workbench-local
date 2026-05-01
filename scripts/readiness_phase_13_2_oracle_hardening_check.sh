#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 13.2 Oracle hardening readiness =="

export AI_DECISION_STUDIO_ORACLE_DATA_ROOT="${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-$(cd ../ai_decision_studio_functional_baseline/oracle_like_data && pwd)}"
export AI_DECISION_STUDIO_READINESS_BASE_URL="${AI_DECISION_STUDIO_READINESS_BASE_URL:-http://127.0.0.1:${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8071}}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-ai-decision-studio}"

echo
echo "data_root=$AI_DECISION_STUDIO_ORACLE_DATA_ROOT"
echo "readiness_base_url=$AI_DECISION_STUDIO_READINESS_BASE_URL"
echo "compose_project=$COMPOSE_PROJECT_NAME"

echo
echo "== Syntax checks =="
bash -n scripts/readiness_phase_13_2_public_session_retention_check.sh
bash -n scripts/readiness_phase_13_2_backup_restore_check.sh
bash -n scripts/readiness_phase_13_2_oracle_exposure_check.sh
bash -n scripts/readiness_phase_13_2_health_ops_check.sh
bash -n scripts/readiness_oracle_like_deploy_check.sh

python3 -m py_compile \
  scripts/cleanup_public_session_overlays.py \
  scripts/oracle_health_ops_report.py

echo
echo "== 13.2 retention/cleanup readiness =="
bash scripts/readiness_phase_13_2_public_session_retention_check.sh

echo
echo "== 13.2 backup/restore readiness =="
bash scripts/readiness_phase_13_2_backup_restore_check.sh

echo
echo "== 13.2 HTTPS/exposure readiness =="
bash scripts/readiness_phase_13_2_oracle_exposure_check.sh

echo
echo "== 13.2 health ops synthetic readiness =="
bash scripts/readiness_phase_13_2_health_ops_check.sh

echo
echo "== Oracle-like deploy readiness =="
bash scripts/readiness_oracle_like_deploy_check.sh

echo
echo "== Real local Oracle health ops report =="
python3 scripts/oracle_health_ops_report.py \
  --data-root "$AI_DECISION_STUDIO_ORACLE_DATA_ROOT" \
  --base-url "$AI_DECISION_STUDIO_READINESS_BASE_URL" \
  --compose-file docker-compose.oracle-like.yml \
  --compose-project "$COMPOSE_PROJECT_NAME" \
  --public-session-max-mb "${AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB:-250}" \
  --max-backup-age-hours "${AI_DECISION_STUDIO_MAX_BACKUP_AGE_HOURS:-48}"

echo
echo "== Phase 13.2 Oracle hardening readiness completed =="
