# AWS SSM Code-Only Deploy

This document describes the current AWS deployment path for updating the product
on an existing EC2 host through GitHub Actions, AWS SSM, and a code-only rebuild.

## Purpose

The SSM code-only path exists to deploy the current product without treating the
EC2 host as disposable infrastructure and without committing runtime state.

It is designed to:

- deploy the exact Git commit selected by GitHub Actions;
- keep mounted runtime, artifacts, users, private baselines, secrets, and Docker
  volumes in place;
- replace application code and rebuild images safely;
- support `dry-run` checks before live execution;
- reduce public SSH dependency by using SSM port forwarding;
- tolerate constrained disk space during rebuilds.

## High-Level Flow

1. Product CI validates the current product contract.
2. AWS CD checks out the deploy commit.
3. AWS CD assumes the AWS deployment role through GitHub OIDC.
4. AWS CD validates the deploy scripts with `bash -n`.
5. AWS CD opens an AWS SSM port-forwarding tunnel to the target EC2 host's SSH
   port.
6. `scripts/deploy_aws_code_only.sh` connects through the local SSM tunnel.
7. The remote deploy path fetches the same Git commit from GitHub.
8. A deployment bundle is built from that source checkout.
9. Bundle checks confirm that secrets, real env files, runtime data, backups,
   and heavy generated payloads are excluded.
10. In `dry-run`, the process stops after validating the host and bundle.
11. In `execute`, the app is replaced, images are rebuilt, and the stack is
    restarted while persistent runtime paths remain mounted.
12. Smoke/readiness checks validate the live product path.

## Scripts

### `.github/workflows/deploy-aws.yml`

The GitHub Actions workflow owns:

- manual `dry-run` / `execute` dispatch;
- post-Product-CI deployment on `main`;
- AWS OIDC credential setup;
- protected `aws-production` environment usage;
- SSM tunnel creation;
- temporary SSH key setup inside the runner;
- deploy-script syntax validation.

### `scripts/deploy_aws_code_only.sh`

This is the existing code-only SSH deploy entrypoint. In the SSM workflow it is
pointed at the local tunnel host alias instead of a public EC2 address.

It is responsible for:

- selecting `--dry-run` or `--execute`;
- building or transferring the deploy bundle path expected by AWS;
- invoking the remote update flow;
- preserving runtime data and private env files.

### `scripts/deploy_aws_code_only_ssm.sh`

This is the SSM command driver for direct SSM execution. It sends a remote shell
command to the EC2 instance through AWS Systems Manager and points that command
at `scripts/deploy_aws_code_only_ssm_remote.sh` for the selected Git commit.

### `scripts/deploy_aws_code_only_ssm_remote.sh`

This remote script performs the host-side code-only deploy work:

- checks persistent paths and permissions;
- validates Docker and Docker Compose availability;
- checks expected Docker volumes;
- fetches the selected Git commit into temporary staging;
- builds the deployment bundle from release source;
- verifies the bundle report;
- supports `dry-run` without changing live app files;
- extracts and applies the new app in `execute` mode;
- keeps private data roots, secret roots, and Docker volumes intact.

### `scripts/deploy_aws.sh`

This script remains the AWS stack deployment contract. It handles the Docker
Compose update path, smoke/readiness behavior, Ollama readiness, and low-disk
rebuild hardening used by the code-only flow.

## Persistent State Boundary

The deploy is intentionally code-only.

It must not replace:

- `.env.aws` on the EC2 host;
- `/opt/ai-decision-studio/data/baseline`;
- `/opt/ai-decision-studio/data/runtime`;
- `/opt/ai-decision-studio/data/artifacts`;
- `/opt/ai-decision-studio/data/users`;
- `/opt/ai-decision-studio/secrets`;
- private baseline archives;
- Nextcloud, Ollama, Caddy, and PPT Creator Docker volumes.

Those paths are operational state. The release bundle updates product source,
safe deploy files, docs, frontend assets, and container build inputs.

## Low-Disk Rebuild Hardening

The EC2 host can have limited free disk during rebuilds. The current deploy path
therefore includes low-disk safeguards:

- dry-run disk checks are advisory so the host can still report its state;
- unused Docker data can be pruned before a live build;
- deployment staging is cleaned after use;
- bundle validation avoids sending runtime payloads into the app archive;
- Ollama readiness uses temporary handling that avoids stale file collisions;
- the rebuild path focuses on the current five-service product stack.

The goal is not to hide disk pressure. The goal is to keep deployment possible
while making disk pressure visible in logs and preserving persistent state.

## Security Boundary

AWS deployment uses several boundaries:

- GitHub OIDC instead of a long-lived AWS access key in the repository;
- protected GitHub environment settings for AWS production;
- secrets for EC2 instance identity and temporary SSH material;
- SSM port forwarding for the SSH path used by Actions;
- private EC2 env files and credential stores outside Git;
- deployment bundles that reject real env files and runtime data.

The public application entry remains the frontend through the AWS ingress layer.
Product API, Nextcloud, Ollama, and PPT Creator remain behind the Docker network
boundary.

## Verification

Useful verification points:

```bash
bash -n scripts/deploy_aws_code_only.sh
bash -n scripts/deploy_aws_code_only_ssm.sh
bash -n scripts/deploy_aws_code_only_ssm_remote.sh
bash -n scripts/deploy_aws.sh
bash -n scripts/smoke_aws.sh
```

For deployment:

- run AWS CD in `dry-run` to validate host preflight and bundle safety;
- run AWS CD in `execute` to apply a code-only rebuild;
- inspect Actions logs for the deploy commit and SSM tunnel readiness;
- inspect smoke/readiness output after the stack restarts.

## Primary References

- `.github/workflows/deploy-aws.yml`
- `.github/workflows/product-ci.yml`
- `scripts/deploy_aws_code_only.sh`
- `scripts/deploy_aws_code_only_ssm.sh`
- `scripts/deploy_aws_code_only_ssm_remote.sh`
- `scripts/deploy_aws.sh`
- `scripts/smoke_aws.sh`
- `scripts/build_deployment_bundle.sh`
- `docs/deployment/aws-deploy.md`
- `docs/deployment/deployment-evolution.md`
- `docs/operations/ci-cd-and-release-controls.md`
