#!/usr/bin/env bash
set -euo pipefail

ENV_FILE=".env.oracle"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo
echo "== Final deploy readiness battery =="

scripts/readiness_nextcloud_golden_baseline_check.sh --env-file "$ENV_FILE"
scripts/readiness_ai_lab_golden_state_check.sh --env-file "$ENV_FILE"
scripts/readiness_public_ai_lab_overlay_check.sh --env-file "$ENV_FILE"
scripts/readiness_preferences_evals_surface_check.sh --env-file "$ENV_FILE"
scripts/readiness_required_integrations_check.sh --env-file "$ENV_FILE"
scripts/readiness_required_providers_check.sh --env-file "$ENV_FILE"
scripts/readiness_evidenceops_ui_cache_check.sh --env-file "$ENV_FILE"
scripts/readiness_run_history_compact_check.sh --env-file "$ENV_FILE"
scripts/readiness_artifacts_compact_check.sh --env-file "$ENV_FILE"

echo
echo "OK: final deploy readiness battery passed"
