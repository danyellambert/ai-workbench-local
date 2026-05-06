# AI Decision Studio redeploy fast path

This is the short redeploy path for the shared Oracle-like Docker topology.

The topology name `oracle-like` is historical. It describes the Docker shape:
frontend, product-api, Nextcloud, Ollama, PPT creator, baseline/runtime/artifact
mounts, and same-origin API routing.

Use the correct real env file for the target host:

| Target | Env file | Compose files |
| --- | --- | --- |
| AWS slim VM | `.env.aws` | `docker-compose.oracle-like.yml` + `docker-compose.aws-slim.override.yml` |
| Oracle VM | `.env.oracle` | `docker-compose.oracle-like.yml` |
| Local Docker | `.env.docker` | `docker-compose.oracle-like.yml` |

## Inputs that must exist outside Git

Do not commit these files or values:

- real `.env.aws`
- real `.env.oracle`
- real `.env.docker`
- real `.env.local`
- nextcloud-golden-baseline-v1.tar.gz
- ai-lab-golden-state-v1.tar.gz
- provider/integration secrets:
  - OLLAMA_HOSTED_API_KEY
  - HUGGINGFACE_INFERENCE_API_KEY
  - EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD
  - EVIDENCEOPS_TRELLO_API_KEY
  - EVIDENCEOPS_TRELLO_TOKEN
  - EVIDENCEOPS_NOTION_API_KEY

## AWS slim fast path

From the AWS VM:

    cd /opt/ai-decision-studio/app

    ENV_FILE=.env.aws scripts/smoke_aws_slim.sh

For code-only redeploys, use the AWS slim script:

    ENV_FILE=.env.aws scripts/deploy_aws_slim.sh

That script validates the compose config, rebuilds only `product-api` and
`frontend`, prunes build cache, and checks `/health`.

Manual equivalent:

    docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.oracle-like.yml \
      -f docker-compose.aws-slim.override.yml \
      up -d --no-deps --build --force-recreate product-api frontend

Required AWS final check:

    ENV_FILE=.env.aws scripts/smoke_aws_slim.sh

    ENV_FILE=.env.aws scripts/readiness_nextcloud_golden_baseline_check.sh \
      --env-file .env.aws \
      --base-url http://127.0.0.1:8071

    ENV_FILE=.env.aws scripts/readiness_preferences_evals_surface_check.sh \
      --env-file .env.aws \
      --base-url http://127.0.0.1:8011

    BASE_URL=http://127.0.0.1:8071 scripts/readiness_admin_session_isolation_check.sh

    ENV_FILE=.env.aws scripts/readiness_trello_public_visibility_check.sh

## Oracle fast path

From the Oracle VM:

    cd /opt/ai-decision-studio/app

    scripts/readiness_final_deploy_check.sh --env-file .env.oracle

On a fresh VM or full state rebuild, restore the runtime baselines:

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
      up -d --build

Finally:

    scripts/readiness_final_deploy_check.sh --env-file .env.oracle

    scripts/measure_surface_latency.sh \
      --base-url http://127.0.0.1:8071 \
      --iterations 5

## Bundle apply order

When applying a fresh bundle manually:

    cd /opt/ai-decision-studio

    rm -rf /tmp/ads_bundle
    mkdir -p /tmp/ads_bundle

    tar -xzf ~/ads_uploads/ai-decision-studio-app-bundle.tar.gz -C /tmp/ads_bundle

    rsync -a \
      /tmp/ads_bundle/ai-decision-studio-app-bundle/ \
      /opt/ai-decision-studio/app/

    chmod +x /opt/ai-decision-studio/app/scripts/*.sh 2>/dev/null || true

Then choose the AWS or Oracle fast path above.

## Expected result

The deployment is considered usable when:

- target-specific smoke/readiness passes;
- Nextcloud repository shows `/EvidenceOpsDemo`;
- AI Lab surfaces are live;
- public overlay check passes where applicable;
- required provider/integration checks pass for the target;
- surface latency report has no unexpected endpoint errors.

## EvidenceOps UI cache

EvidenceOps uses a persistent UI cache for the expensive Nextcloud/WebDAV
repository snapshot.

Default policy:

    EVIDENCEOPS_UI_CACHE_MODE=persistent_until_sync
    EVIDENCEOPS_UI_CACHE_PATH=/app/runtime/cache/lab/evidenceops_payload.json

Normal visitors should receive the last known good EvidenceOps snapshot
immediately. The cache is refreshed by deploy warmup, explicit EvidenceOps sync,
or action updates.
