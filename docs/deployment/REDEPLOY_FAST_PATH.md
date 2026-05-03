# AI Decision Studio redeploy fast path

This is the short redeploy path for the Oracle/AWS-like deployment.

## Inputs that must exist outside Git

Do not commit these files or values:

- real .env.oracle
- nextcloud-golden-baseline-v1.tar.gz
- ai-lab-golden-state-v1.tar.gz
- provider/integration secrets:
  - OLLAMA_HOSTED_API_KEY
  - HUGGINGFACE_INFERENCE_API_KEY
  - EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD
  - EVIDENCEOPS_TRELLO_API_KEY
  - EVIDENCEOPS_TRELLO_TOKEN
  - EVIDENCEOPS_NOTION_API_KEY

## Required final check

A deploy is not complete until this passes:

    scripts/readiness_final_deploy_check.sh --env-file .env.oracle

That final check runs:

- Nextcloud golden baseline readiness
- AI Lab golden state readiness
- public AI Lab overlay readiness
- Preferences/Evals readiness
- required Trello/Notion integrations readiness
- required provider readiness, including Hugging Face Inference

## Fast redeploy order

From the VM:

    cd /opt/ai-decision-studio

    rm -rf /tmp/ads_bundle
    mkdir -p /tmp/ads_bundle

    tar -xzf ~/ads_uploads/ai-decision-studio-oracle-app-bundle.tar.gz -C /tmp/ads_bundle

    rsync -a \
      /tmp/ads_bundle/ai-decision-studio-oracle-app-bundle/ \
      /opt/ai-decision-studio/app/

    chmod +x /opt/ai-decision-studio/app/scripts/*.sh 2>/dev/null || true

On a fresh VM or full state rebuild, restore the runtime baselines:

    cd /opt/ai-decision-studio/app

    scripts/restore_nextcloud_golden_baseline.sh \
      --env-file .env.oracle \
      --archive ~/ads_uploads/nextcloud-golden-baseline-v1.tar.gz \
      --delete-archive

    scripts/restore_ai_lab_golden_state.sh \
      --env-file .env.oracle \
      --archive ~/ads_uploads/ai-lab-golden-state-v1.tar.gz \
      --delete-archive

Then rebuild/recreate:

    docker compose \
      --env-file .env.oracle \
      -p ai-decision-studio \
      -f docker-compose.oracle-like.yml \
      -f docker-compose.aws-slim.override.yml \
      build product-api frontend

    docker compose \
      --env-file .env.oracle \
      -p ai-decision-studio \
      -f docker-compose.oracle-like.yml \
      -f docker-compose.aws-slim.override.yml \
      up -d --force-recreate product-api frontend

Finally:

    scripts/readiness_final_deploy_check.sh --env-file .env.oracle

    scripts/measure_surface_latency.sh \
      --base-url http://127.0.0.1:8071 \
      --iterations 5

## Expected result

The deployment is considered usable when:

- final deploy readiness passes;
- Nextcloud repository shows /EvidenceOpsDemo;
- AI Lab surfaces are live;
- public overlay check passes;
- Trello, Notion and Hugging Face required checks pass;
- surface latency report has no unexpected endpoint errors.

## EvidenceOps UI cache

EvidenceOps uses a persistent UI cache for the expensive Nextcloud/WebDAV repository snapshot.

Default policy:

    EVIDENCEOPS_UI_CACHE_MODE=persistent_until_sync
    EVIDENCEOPS_UI_CACHE_PATH=/app/runtime/cache/lab/evidenceops_payload.json

Normal visitors should receive the last known good EvidenceOps snapshot immediately.
The cache is refreshed by deploy warmup, explicit EvidenceOps sync, or action updates.
