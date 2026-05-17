# Deployment Evolution

This document summarizes how deployment evolved from local experimentation into the current local Docker and AWS product contracts.

## Current Contracts

### Local Docker

Local Docker uses:

- `.env.docker`;
- `docker-compose.local.yml`;
- the five-service product stack;
- mounted runtime folders;
- optional local provider credentials;
- local host access through the frontend port.

### AWS

AWS uses:

- `.env.aws`;
- `docker-compose.aws.yml`;
- the same five-service product stack;
- Caddy as the public ingress/reverse proxy layer;
- a private Docker network for application services;
- mounted runtime folders;
- optional custom domain and TLS through DNS plus Caddy;
- credential storage outside source control.

AWS no longer uses local compose as a base layer. The AWS compose file is the deployment contract.

## Evolution Timeline

### Local Product Containerization

The product moved from direct local execution and historical app surfaces to a containerized product stack. The local Docker path made it possible to run the React frontend, Product API, PPT Creator, Nextcloud, Ollama, and mounted runtime data together.

Primary references:

- `docker-compose.local.yml`
- `Dockerfile.product-api.local`
- `Dockerfile.frontend`
- `scripts/run_local_docker.sh`
- `docs/deployment/local-docker-compose.md`

### AWS Productization

AWS deployment was cleaned up from inherited naming and layering into a single product deployment path. The AWS file is now `docker-compose.aws.yml`, and the AWS Dockerfile is `Dockerfile.product-api.aws`.

Primary references:

- `docker-compose.aws.yml`
- `Dockerfile.product-api.aws`
- `scripts/deploy_aws.sh`
- `scripts/smoke_aws.sh`
- `docs/deployment/aws-deploy.md`

### Caddy And Public Ingress

Caddy was added to make the public edge domain-ready. In AWS, Caddy receives the public request, handles the reverse proxy/TLS boundary, and forwards traffic to the frontend container on the private Docker network.

Primary references:

- `deploy/caddy/Caddyfile`
- `docs/deployment/cloudflare-caddy-container.md`
- `docs/deployment/aws-deploy.md`

### Baseline Restore And Runtime Mounts

The deployment path now treats runtime data as mounted state. Baselines can be restored without baking generated state into container images. This keeps the product reproducible while preserving demo-ready material.

Important restore areas:

- Nextcloud baseline material;
- AI Lab baseline state;
- functional baseline data;
- runtime payloads;
- artifacts and previews;
- user/session overlays.

Primary references:

- `docs/deployment/NEXTCLOUD_GOLDEN_BASELINE_RESTORE.md`
- `docs/deployment/AI_LAB_GOLDEN_STATE_RESTORE.md`
- `docs/operations/backup-and-restore.md`
- `docs/operations/LOCAL_BACKUP_REGISTER.md`

### Credential Store

Credentials moved toward a private runtime store so deployment can be configured without committing secrets. External publish credentials remain optional and admin-gated.

Primary references:

- `src/storage/secret_store.py`
- `docs/deployment/aws-deploy.md`
- `.env.aws.example`
- `.env.docker.example`

### Deployment Bundle Safety

Deployment bundle checks were added to keep archives focused on product files and exclude generated runtime, backups, secrets, and local-only state.

Primary references:

- `scripts/build_deployment_bundle.sh`
- `docs/deployment/AWS_FRESH_EC2_BOOTSTRAP.md`

## Operational Guarantees

The current deployment story is designed around these guarantees:

- the same five services define local Docker and AWS operation;
- AWS has a single compose file and does not depend on local compose layering;
- Caddy is the public ingress on AWS;
- frontend is the only public application entry point;
- Product API, Nextcloud, Ollama, and PPT Creator stay on the private network;
- runtime state is mounted, inspectable, and restorable;
- credentials stay outside Git;
- smoke and readiness scripts validate the active contracts.

## Historical Material

Oracle-specific scripts, old compose layering, historical frontend/demo Dockerfiles, and heavy historical dependency paths are preserved under `legacy/` or reference docs. They are not the current deployment contract.
