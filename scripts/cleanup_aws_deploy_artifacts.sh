#!/usr/bin/env bash
set -euo pipefail

enabled="${AI_DECISION_STUDIO_AWS_CLEANUP_DEPLOY_TMP:-1}"

case "$enabled" in
  0|false|FALSE|no|NO|off|OFF)
    echo "AWS deploy cleanup disabled"
    exit 0
    ;;
esac

echo
echo "== AWS deploy cleanup: temporary deploy/restore artifacts =="

sudo rm -rf \
  /tmp/ai-decision-studio-app-bundle-fresh.tar.gz \
  /tmp/ai-decision-studio-app-bundle-five-service-fix.tar.gz \
  /tmp/ai-decision-studio-code-sync-after-secret-cleanup.tar.gz \
  /tmp/ai-decision-studio-rebuild-head.tar.gz \
  /tmp/ai-decision-studio-product-data-baseline.tar.gz \
  /tmp/ai-decision-studio-product-data-baseline.sha256 \
  /tmp/nextcloud-golden-baseline-v1.tar.gz \
  /tmp/ads_oracle_bundle_validate_20260503_234757 \
  /tmp/ads_admin_session_readiness_bundle_validate_20260504_004554 \
  /tmp/ads_trello_public_readiness_bundle_validate_20260504_011249 \
  /tmp/ads_multi_env_readiness_bundle_validate_20260504_012337 \
  /tmp/ads_latency_runbook_bundle \
  /tmp/ads_code_sync_after_secret_cleanup_20260504_133012 \
  /tmp/ads_rebuild_head_20260504_140314 \
  /tmp/ads_candidate_review_stage_20260503_131848 \
  /tmp/ads_release_candidate_review_backend_role_brief_20260503_192052

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get clean || true
  sudo rm -rf /var/lib/apt/lists/* || true
fi

df -h / || true
sudo du -sh /tmp /var/cache 2>/dev/null || true

echo "OK: AWS deploy cleanup completed"
