# Oracle-like deployment readiness plan

This document tracks the transition from the validated local Docker frontend parity stack to an Oracle-like deployment topology.

## Current validated state

The local Docker frontend parity gate has passed with:

- Product API health.
- Frontend health.
- Provider integrations ready: NextCloud, Trello, Notion.
- Favicon check.
- Docker public demo smoke.
- Workflow write smoke for `document_review`.
- Workflow write smoke for `policy_contract_comparison`.
- Frontend workflow UI smoke.
- Local-vs-Docker route parity for stable routes.
- Product, AI Lab and Settings deep-click checks.
- AI Lab content checks.
- Runbook phases 8-12 checks.

## Deployment objective

Move from local validation mode to an Oracle-like reproducible deployment.

The deployment must keep the same product behavior while replacing local-machine assumptions with explicit runtime configuration.

## Target services

### product-api

Runs the backend application.

Required responsibilities:

- Serve product workflows.
- Read baseline state.
- Write runtime state to mounted persistent volumes.
- Connect to providers through explicit environment variables.
- Expose `/health`.
- Never receive raw secrets from committed files.

### frontend

Runs the built web UI behind Nginx.

Required responsibilities:

- Serve static frontend routes.
- Proxy `/api/*` to `product-api`.
- Serve favicon/static assets.
- Expose public HTTP port.

## Persistent data model

Recommended Oracle-like persistent roots:

- `/opt/ai-decision-studio/data/baseline`
- `/opt/ai-decision-studio/data/runtime`
- `/opt/ai-decision-studio/data/artifacts`
- `/opt/ai-decision-studio/data/users`
- `/opt/ai-decision-studio/backups`

Local validation currently uses a baseline overlay. Oracle-like hardening should separate immutable baseline data from mutable runtime state.

## Secret strategy

Secrets must come from runtime environment variables or Docker secrets, not committed files.

Required secret-like variables:

- `OLLAMA_HOSTED_API_KEY`
- `HUGGINGFACE_INFERENCE_API_KEY`
- `EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD`
- `EVIDENCEOPS_TRELLO_API_KEY`
- `EVIDENCEOPS_TRELLO_TOKEN`
- `EVIDENCEOPS_NOTION_API_KEY`

Non-secret config can be committed as examples only.

## Provider topology

### Ollama local

Local validation uses `OLLAMA_BASE_URL=http://host.docker.internal:11435/v1`.

Oracle deployment cannot assume `host.docker.internal` works unless explicitly provided by the host/network setup.

Oracle options:

1. Run Ollama on the same Oracle host and expose it to the Docker network as `http://ollama:11434/v1`.
2. Run Ollama outside this compose stack and set `OLLAMA_BASE_URL` to the reachable private host endpoint.
3. Disable local Ollama generation and use hosted generation plus remote embeddings.

### Ollama Hosted

Uses remote hosted endpoint and `OLLAMA_HOSTED_API_KEY`.

### Hugging Face Inference

Uses remote router endpoint and `HUGGINGFACE_INFERENCE_API_KEY`.

### NextCloud

Must use a reachable WebDAV endpoint and app password.

### Trello / Notion

Must use runtime credentials and configured IDs/databases.

## Public/admin policy

Local validation mode confirms generic unknown PATCH probes do not persist unexpected fields.

Oracle-like deployment should decide one of:

- Single-user private deployment behind private access/VPN.
- Public read-only demo with admin actions disabled.
- Authenticated admin mode with real login/session protection.

## Reverse proxy/TLS

Recommended production topology:

Internet -> Caddy/Nginx/Traefik -> frontend container -> product-api container on private Docker network.

TLS should be terminated by the reverse proxy.

## Backup/restore

Back up:

- runtime
- artifacts
- users
- provider-safe metadata

Do not back up raw `.env` into Git. Store secrets separately.

## Readiness gates before Oracle deployment

Required local gates:

- `legacy/scripts/readiness_full_frontend_parity_check.sh`
- `scripts/readiness_oracle_like_deploy_check.sh`
