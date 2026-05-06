# AWS slim deploy

Use this document for the current AWS slim deployment shape.

Official AWS slim topology:

- compose: docker-compose.aws-slim.yml
- env file: .env.aws
- product API Dockerfile: Dockerfile.product-api.aws-slim
- frontend Dockerfile: Dockerfile.frontend

Expected AWS services:

- nextcloud
- ollama
- ppt-creator
- product-api
- frontend

Expected AWS host paths:

- /opt/ai-decision-studio/app for the application repository.
- /opt/ai-decision-studio/data for the product data root.

Data root contract on AWS:

- /opt/ai-decision-studio/data/baseline mounted to /app/baseline
- /opt/ai-decision-studio/data/runtime mounted to /app/runtime
- /opt/ai-decision-studio/data/artifacts mounted to /app/artifacts
- /opt/ai-decision-studio/data/users mounted to /app/users

The local versioned payload can be used as the source for populating the AWS data root:

- runtime/ai_decision_studio_functional_baseline/oracle_like_data/baseline
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/runtime
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/artifacts
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/users

Basic validation:

- docker compose --env-file .env.aws -f docker-compose.aws-slim.yml config --services
- docker compose --env-file .env.aws -f docker-compose.aws-slim.yml ps

Helper scripts:

- scripts/deploy_aws_slim.sh
- scripts/smoke_aws_slim.sh

## Runtime prerequisites

The AWS compose file creates the five-container stack, but some integrations
need runtime state or private credentials before the product surface is fully
usable.

Nextcloud:

- The `nextcloud` container and `nextcloud_app` Docker volume are created by
  Compose.
- The EvidenceOps demo corpus is not stored in Git. On a fresh AWS host, upload
  `nextcloud-golden-baseline-v1.tar.gz` and restore it with
  `scripts/restore_nextcloud_golden_baseline.sh`.
- `Import from Nextcloud` uses WebDAV Basic Auth. The real `.env.aws` must set
  `EVIDENCEOPS_NEXTCLOUD_USERNAME`,
  `EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD`, and
  `EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo`.
- The restored baseline user must match the WebDAV user in `.env.aws`. A
  baseline created under `danyel` will not be visible through an `ads_admin`
  WebDAV path unless it is regenerated or restored for that user.

Trello and Notion:

- Board/list/database ids in `.env.aws.example` document the expected shape;
  they do not grant access.
- Real publishing/sync requires `EVIDENCEOPS_TRELLO_API_KEY`,
  `EVIDENCEOPS_TRELLO_TOKEN`, and/or `EVIDENCEOPS_NOTION_API_KEY` in the private
  `.env.aws`.

Ollama:

- The deploy script starts the Ollama sidecar if needed and runs
  `ollama pull` for the deploy-only preloaded embedding model.
- The default preloaded model is `embeddinggemma:300m`, configured with
  `AI_DECISION_STUDIO_OLLAMA_EMBEDDING_MODEL_PULL`. This is not passed into the
  product API and does not override Runtime Controls selections in the app.
- Set `SKIP_OLLAMA_EMBEDDING_MODEL_PULL=1` only when you intentionally manage
  the Ollama model volume yourself.
- The preferred AWS generation model is `nemotron-3-super:cloud`; it requires a
  real `OLLAMA_HOSTED_API_KEY`.

Security rule:

.env.aws is intentionally not versioned. Use .env.aws.example as the contract and keep real secrets on the host.
