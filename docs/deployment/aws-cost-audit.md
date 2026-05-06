# AWS Cost and Resource Audit

This document records the current AWS deployment resource posture for AI Decision Studio.

## Current AWS host

- Public endpoint: http://16.59.141.55:8071
- Instance type observed during audit: m7i-flex.large
- Availability zone observed during audit: us-east-2a
- Root volume observed during audit: 30 GB
- Public ports observed: 22 SSH and 8071 app entrypoint
- Internal services are container-network only: product API, Nextcloud, Ollama, and PPT creator.

## Main recurring cost drivers

The main recurring cost drivers are expected to be:

1. EC2 instance runtime.
2. Public IPv4 address.
3. EBS root volume.
4. Data transfer, if the public demo receives meaningful traffic.

Docker images and local volumes consume disk space, but they are not separate AWS services by themselves.

## Resource posture after cleanup

Safe cleanup was performed without removing application volumes or required images.

Before cleanup:

- Root filesystem: 84% used.
- Free space: about 4.7 GB.
- Docker build cache: about 1.45 GB.
- Docker images: 7.

After cleanup:

- Root filesystem: 79% used.
- Free space: about 6.1 GB.
- Docker build cache: 0 B.
- Docker images: 5.
- Application stack remained healthy.
- /health returned OK.

Removed safely:

- APT cache.
- Old temporary ADS bundle under /tmp.
- Unused demo images: hello-world and alpine.
- Docker build cache.

Not removed:

- Docker volumes.
- Nextcloud data.
- Ollama data.
- Application images required by the running stack.
- The Ollama image, because it is large but functionally relevant unless separately proven unused.

## Expected Docker stack

- frontend
- product-api
- nextcloud
- ollama
- ppt-creator

Expected internal health check:

curl -fsS http://127.0.0.1:8071/health

Expected external endpoint:

http://16.59.141.55:8071

## Safe cleanup command

Use this only for safe cache cleanup. It does not remove volumes.

sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*
sudo find /tmp -maxdepth 1 -type d \( -name "ads_*" -o -name "tmp.*" \) -mtime +1 -print -exec rm -rf {} +
docker image rm hello-world:latest alpine:latest 2>/dev/null || true
docker builder prune -af || true

After cleanup, verify:

df -h /
docker system df
docker compose --env-file .env.aws -p ai-decision-studio -f docker-compose.local.yml -f docker-compose.aws-slim.yml ps
curl -fsS http://127.0.0.1:8071/health

## Do not run without review

Avoid these commands unless there is a specific recovery plan:

docker system prune -a
docker volume prune
sudo rm -rf /var/lib/docker
sudo rm -rf /var/lib/containerd

These may remove required images, containers, or persistent application state.

## Cost recommendations

- Keep AWS Budgets enabled.
- Treat this host as a paid public demo environment, not a free-tier deployment.
- Stop the instance when the public demo is not needed, if downtime is acceptable.
- Consider increasing EBS from 30 GB to 50 GB if frequent rebuilds continue.
- Consider removing the local Ollama service only after verifying that all app flows use hosted/cloud providers and do not require the internal Ollama container.
