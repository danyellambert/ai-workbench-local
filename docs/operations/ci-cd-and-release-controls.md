# CI/CD And Release Controls

This document describes the current repository-level control plane for validation,
release preparation, and AWS deployment.

## Purpose

The CI/CD layer keeps the current product contract separate from historical
experiments. It validates the Product API, frontend, compose contracts, current
Python gate, and deployment scripts before AWS deployment is allowed to run.

The release path is intentionally conservative:

- source code, docs, and safe examples live in Git;
- real env files, runtime state, credentials, backups, and private baselines stay
  outside Git;
- Product CI validates the current product surface;
- AWS CD deploys only after explicit manual execution or successful Product CI on
  `main`;
- AWS deployment uses protected GitHub environment controls and SSM-based access.

## Product CI

Product CI is defined in `.github/workflows/product-ci.yml`.

It currently validates:

- current Product API Python entrypoints with `py_compile`;
- frontend dependency installation through `npm ci --prefix frontend`;
- frontend tests through `npm --prefix frontend run test`;
- frontend production build through `npm --prefix frontend run build`;
- shell syntax for the local, AWS, smoke, and bundle scripts;
- local Docker and AWS compose/readiness contracts through
  `scripts/readiness_multi_environment_contract_check.sh`;
- the current Python product test gate through `scripts/run_current_test_gate.sh`
  with root `requirements.txt`.

This gate is the maintained validation path. Historical tests and exploratory
evals remain useful reference material, but they are not treated as the current
green gate for release.

## AWS CD

AWS CD is defined in `.github/workflows/deploy-aws.yml`.

It can run in two ways:

- manual `workflow_dispatch` with `dry-run` or `execute`;
- automatic execution after Product CI completes successfully on `main`.

The workflow uses:

- GitHub OIDC to assume the AWS deployment role;
- the protected `aws-production` environment;
- GitHub secrets for EC2 instance identity and SSH material;
- GitHub environment variables for region and production URL;
- deploy-script syntax validation before remote execution;
- SSM port forwarding to reach EC2 SSH without relying on a broad public SSH
  workflow path.

The manual `dry-run` mode is the safety valve for checking the remote host,
deployment bundle, persistent paths, Docker volumes, and script behavior without
replacing the live app.

## Release Flow

The current release discipline is:

1. develop on a branch or local working state;
2. merge or push the intended release commit to `main`;
3. let Product CI validate the current product contract;
4. run AWS CD manually in `dry-run` when a remote host check is needed;
5. run AWS CD in `execute` mode, or allow the post-CI AWS CD path to execute when
   configured for the release;
6. inspect Actions logs, smoke checks, and runtime health after deployment.

This flow makes the repository history, CI result, deploy commit, and AWS
deployment run traceable to each other.

## Secrets And Environment Boundaries

The CI/CD layer never requires real env files to be committed.

Private values are expected in:

- GitHub Actions secrets and protected environment variables for CI/CD;
- `.env.local`, `.env.docker`, or `.env.aws` on the target machine;
- mounted private credential stores at runtime;
- private baseline archives outside the repository.

Safe `.example` files document the required keys and operational intent without
including private credentials or account-specific payloads.

## Eval Workflow Naming

The evaluation workflows were renamed from phase-numbered names to current
engineering names:

- `.github/workflows/evals.yml`;
- `.github/workflows/evals-live.yml`.

This keeps evals visible as maintained engineering controls while preserving the
historical phase material under documentation and legacy reference paths.

## Operational Guarantees

The current CI/CD setup is designed to guarantee that:

- frontend and Product API contracts are checked before AWS deployment;
- compose contracts are validated without deploying;
- AWS deploy scripts are syntax-checked in CI before remote execution;
- AWS CD uses protected credentials and a protected environment;
- deploys can be previewed through `dry-run`;
- deploys are tied to the exact Git commit checked out by Actions;
- secrets and runtime payloads stay outside Git;
- old exploratory material stays documented but does not blur the current gate.

## Primary References

- `.github/workflows/product-ci.yml`
- `.github/workflows/deploy-aws.yml`
- `.github/workflows/evals.yml`
- `.github/workflows/evals-live.yml`
- `scripts/run_current_test_gate.sh`
- `scripts/readiness_multi_environment_contract_check.sh`
- `scripts/deploy_aws_code_only.sh`
- `scripts/deploy_aws_code_only_ssm.sh`
- `scripts/deploy_aws_code_only_ssm_remote.sh`
- `docs/deployment/aws-ssm-code-only-deploy.md`
- `docs/deployment/FULL_LOCAL_PRODUCT_SETUP.md`
