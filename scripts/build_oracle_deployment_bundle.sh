#!/usr/bin/env bash
set -euo pipefail

# Backward-compatible wrapper.
# The deployment bundle builder was renamed because it is used by the current
# AWS/local deployment flow too. Existing Oracle-oriented docs/scripts can still
# call this wrapper until the Oracle-only surface is moved to legacy.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

: "${AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_DIR:=${AI_DECISION_STUDIO_ORACLE_BUNDLE_DIR:-runtime/ai_decision_studio_functional_baseline/oracle_deployment_bundle}}"
: "${AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_NAME:=${AI_DECISION_STUDIO_ORACLE_BUNDLE_NAME:-ai-decision-studio-oracle-app-bundle}}"
: "${AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_REPORT:=${AI_DECISION_STUDIO_ORACLE_BUNDLE_REPORT:-runtime/ai_decision_studio_functional_baseline/parity_reports/oracle_deployment_bundle_report.json}}"

export AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_DIR
export AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_NAME
export AI_DECISION_STUDIO_DEPLOYMENT_BUNDLE_REPORT

exec "$SCRIPT_DIR/build_deployment_bundle.sh" "$@"
