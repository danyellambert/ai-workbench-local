# Oracle operations runbook

This runbook describes how to move the validated Oracle-like Docker stack to an Oracle Always Free host.

## Validated local state

The local Oracle-like smoke validates:

- `docker-compose.oracle-like.yml` is valid.
- `product-api` binds to `0.0.0.0:8011` inside Docker.
- `frontend` reaches `product-api` through the Docker private network.
- `/health` passes through the frontend.
- workflows, document library, artifacts and EvidenceOps endpoints respond.
- EvidenceOps smoke uses `EVIDENCEOPS_REPOSITORY_BACKEND=local` unless a real NextCloud endpoint is configured.

## Target host layout

Recommended host directory:

/opt/ai-decision-studio/
  data/
    baseline/
    runtime/
    artifacts/
    users/
    backups/
  app/
    docker-compose.oracle-like.yml
    .env.oracle

## One-time server setup

Run on the Oracle host:

sudo mkdir -p /opt/ai-decision-studio/app
sudo mkdir -p /opt/ai-decision-studio/data/baseline
sudo mkdir -p /opt/ai-decision-studio/data/runtime
sudo mkdir -p /opt/ai-decision-studio/data/artifacts
sudo mkdir -p /opt/ai-decision-studio/data/users
sudo mkdir -p /opt/ai-decision-studio/data/backups
sudo chown -R "$USER":"$USER" /opt/ai-decision-studio

Install Docker and Docker Compose according to the Oracle image you selected.

Verify:

docker --version
docker compose version

## Copy application files

Copy the repository or a deployment bundle to:

/opt/ai-decision-studio/app

Required files on the host:

- docker-compose.oracle-like.yml
- .env.oracle
- Dockerfile.public-demo
- Dockerfile.frontend-public-demo
- requirements-public-demo.txt
- main_product_api.py
- src/
- frontend/

## Copy prepared data root

Use the prepared Oracle-like data root as the source:

runtime/ai_decision_studio_functional_baseline/oracle_like_data

Copy its contents into:

/opt/ai-decision-studio/data

Expected result:

- /opt/ai-decision-studio/data/baseline
- /opt/ai-decision-studio/data/runtime
- /opt/ai-decision-studio/data/artifacts
- /opt/ai-decision-studio/data/users
- /opt/ai-decision-studio/data/backups

## Create .env.oracle

On the server:

cd /opt/ai-decision-studio/app
cp .env.oracle.example .env.oracle
chmod 600 .env.oracle

Minimum local-smoke style config:

AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT=8080
AI_DECISION_STUDIO_PRODUCT_API_PUBLIC_PORT=8011

AI_DECISION_STUDIO_BASELINE_ROOT=/opt/ai-decision-studio/data/baseline
AI_DECISION_STUDIO_RUNTIME_ROOT=/opt/ai-decision-studio/data/runtime
AI_DECISION_STUDIO_ARTIFACT_ROOT=/opt/ai-decision-studio/data/artifacts
AI_DECISION_STUDIO_USERS_ROOT=/opt/ai-decision-studio/data/users

EVIDENCEOPS_REPOSITORY_BACKEND=local
OLLAMA_BASE_URL=http://ollama:11434/v1

For real provider integrations, fill secrets only in `.env.oracle`, never in Git.

## Start the stack

cd /opt/ai-decision-studio/app

docker compose \
  --env-file .env.oracle \
  -f docker-compose.oracle-like.yml \
  up -d --build

## Validate

docker compose --env-file .env.oracle -f docker-compose.oracle-like.yml ps

curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/api/product/workflows
curl -fsS http://127.0.0.1:8080/api/product/document-library
curl -fsS http://127.0.0.1:8080/api/lab/artifacts
curl -fsS http://127.0.0.1:8080/api/lab/evidenceops

Expected:

- `/health` returns `ok: true`.
- workflows count is at least 4.
- document library returns documents.
- artifacts summary has artifacts.
- EvidenceOps endpoint responds even when using local backend.

## Logs

docker logs ai-decision-studio-product-api-oracle-like --tail 200
docker logs ai-decision-studio-frontend-oracle-like --tail 200

## Stop and restart

docker compose --env-file .env.oracle -f docker-compose.oracle-like.yml down
docker compose --env-file .env.oracle -f docker-compose.oracle-like.yml up -d

## Backup

Back up:

- /opt/ai-decision-studio/data/runtime
- /opt/ai-decision-studio/data/artifacts
- /opt/ai-decision-studio/data/users

Do not commit or publish `.env.oracle`.

Example:

mkdir -p /opt/ai-decision-studio/data/backups

tar -czf "/opt/ai-decision-studio/data/backups/runtime-artifacts-users-$(date +%Y%m%d-%H%M%S).tar.gz" \
  -C /opt/ai-decision-studio/data \
  runtime artifacts users

## Restore

cd /opt/ai-decision-studio/data

tar -xzf backups/<backup-file>.tar.gz

Then restart:

cd /opt/ai-decision-studio/app
docker compose --env-file .env.oracle -f docker-compose.oracle-like.yml up -d

## Provider modes

### Local smoke mode

Use:

EVIDENCEOPS_REPOSITORY_BACKEND=local

This validates the app without requiring NextCloud.

### NextCloud mode

Use:

EVIDENCEOPS_REPOSITORY_BACKEND=nextcloud_webdav
EVIDENCEOPS_NEXTCLOUD_BASE_URL=<webdav-url>
EVIDENCEOPS_NEXTCLOUD_USERNAME=<username>
EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD=<app-password>
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo

### Ollama local mode

Preferred Oracle topology:

OLLAMA_BASE_URL=http://ollama:11434/v1

If Ollama runs outside this compose stack, set `OLLAMA_BASE_URL` to the reachable private endpoint.

## Final pre-public checklist

Before exposing the service publicly:

- Confirm `.env.oracle` is not committed.
- Confirm firewall allows only intended ports.
- Confirm reverse proxy and TLS are configured.
- Confirm admin/write actions policy is acceptable for the deployment mode.
- Confirm backups work.
- Run the Oracle-like smoke locally and on host.
