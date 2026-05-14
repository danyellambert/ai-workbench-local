# Axiovance — AWS fresh EC2 bootstrap runbook

## Current validated AWS contract

This runbook assumes the current AWS deployment contract:

- real runtime env: `.env.aws`;
- safe example env: `.env.aws.example`;
- env contract validation:

    python3 scripts/validate_aws_env_contract.py --env .env.aws --example .env.aws.example

- real and example envs must have the same keys;
- local/dev-only Vite proxy must be disabled in AWS:
  - `VITE_PRODUCT_API_PROXY_ENABLED=0`;
  - `VITE_PRODUCT_API_PROXY_TARGET=`;
- compose file: `docker-compose.aws.yml`;
- deploy command:

    ENV_FILE=.env.aws scripts/deploy_aws.sh

- smoke command:

    ENV_FILE=.env.aws BASE_URL=http://127.0.0.1:8071 scripts/smoke_aws.sh

Do not commit real env files. `.env.aws` must stay ignored by Git.

The AWS host may be an applied bundle directory rather than a Git worktree. `scripts/readiness_multi_environment_contract_check.sh` auto-detects that mode and skips local host/dev runner checks that would otherwise require host-level `npm`.


This runbook describes how to rebuild the AWS demo environment from a fresh EC2
instance.

It is intentionally explicit about the real AWS env file, the Docker topology,
and the difference between first boot and later code-only redeploys.

## Current validated AWS contract

AWS uses:

- real env file: `.env.aws`
- safe template: `.env.aws.example`
- compose file: `docker-compose.aws.yml`
- product API image: `ai-decision-studio-product-api:aws`
- frontend image: `ai-decision-studio-frontend:aws`

Real env files must never be committed to Git or included in public bundles.

## What this runbook rebuilds

A successful fresh AWS bootstrap should end with five containers running:

- `frontend`
- `product-api`
- `nextcloud`
- `ollama`
- `ppt-creator`

The AWS host should then pass:

- `/health`
- `ENV_FILE=.env.aws scripts/smoke_aws.sh`
- target-specific readiness checks

## Inputs you need before starting

On your local machine, you need:

- SSH private key for the EC2 host
- the EC2 public IP or DNS name
- a clean local checkout of this repository
- the real `.env.aws` file, stored outside Git or ignored by Git
- private runtime credentials for the integrations you want enabled:
  - `OLLAMA_HOSTED_API_KEY` for hosted `*-cloud` generation models;
  - `EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD` and `NEXTCLOUD_ADMIN_PASSWORD` for
    Nextcloud/WebDAV;
  - `EVIDENCEOPS_TRELLO_API_KEY` and `EVIDENCEOPS_TRELLO_TOKEN` for Trello;
  - `EVIDENCEOPS_NOTION_API_KEY` for Notion;
- optional runtime/state archives:
  - `nextcloud-golden-baseline-v1.tar.gz`
  - `ai-lab-golden-state-v1.tar.gz`

The real `.env.aws` can live in the repo root on your Mac only because it is
ignored by Git. Confirm this before using it:

    git check-ignore -v .env.aws
    git status --short

`git status --short` must not show `.env.aws`.

## Security and cost guardrails

Before exposing the demo:

- keep SSH port `22` restricted to your IP;
- keep `8071` restricted to your IP until the demo is intentionally public;
- keep direct Nextcloud access private, preferably through SSH tunnel;
- use `80/443` only when domain/HTTPS is configured;
- keep an AWS budget alert active;
- do not run `docker system prune -a --volumes` on the demo host;
- avoid rebuilding unnecessary images on small disks.

The validated AWS flow uses the product API image to avoid the heavy build
path on a small EC2 disk.

## Step 1 — Create the EC2 instance

Create an Ubuntu EC2 instance.

Recommended minimum for the current demo:

- Ubuntu LTS
- 30 GiB gp3 root volume or larger
- instance type with enough RAM for the five-container stack
- public IPv4 only if you need browser access
- SSH key pair attached

Security group during bootstrap:

- `22/tcp` from your IP only
- `8071/tcp` from your IP only
- `80/tcp` and `443/tcp` from your IP only, or closed until HTTPS/domain work
- no public direct Nextcloud port

Record:

- EC2 public IP
- SSH key path
- AWS region
- instance ID

## Step 2 — Install Docker and minimal host dependencies

SSH into the EC2 host:

    ssh -i ~/.ssh/ai-decision-studio-aws.pem ubuntu@<EC2_PUBLIC_IP>

Install packages and Docker:

    set -euo pipefail

    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release rsync tar unzip

    sudo install -m 0755 -d /etc/apt/keyrings

    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    sudo usermod -aG docker ubuntu

Open a new SSH session or run:

    newgrp docker

Validate:

    docker version
    docker compose version

## Step 3 — Create application directories

On the EC2 host:

    sudo mkdir -p /opt/ai-decision-studio/app
    sudo mkdir -p /opt/ai-decision-studio/data
    sudo mkdir -p /opt/ai-decision-studio/data/baseline
    sudo mkdir -p /opt/ai-decision-studio/data/runtime
    sudo mkdir -p /opt/ai-decision-studio/data/artifacts
    sudo mkdir -p /opt/ai-decision-studio/data/users
    sudo chown -R ubuntu:ubuntu /opt/ai-decision-studio

    mkdir -p ~/ads_uploads
    chmod 700 ~/ads_uploads

## Step 4 — Build the deployment bundle locally

From your local Mac checkout:

    cd "/path/to/ai-decision-studio"

    git status --short
    scripts/build_deployment_bundle.sh

The bundle path defaults to:

    runtime/ai_decision_studio_functional_baseline/deployment_bundle/ai-decision-studio-app-bundle.tar.gz

The bundle name still says `oracle` for historical compatibility. The bundle now
contains the AWS env template and AWS scripts too.

Validate that the bundle report says:

- `ok=true`
- `required_paths_present=true`
- `no_real_env_files=true`
- `no_secret_findings=true`
- `no_runtime_or_baseline_data=true`

## Step 5 — Upload bundle and real AWS env file

From your local Mac:

    EC2_HOST=ubuntu@<EC2_PUBLIC_IP>
    SSH_KEY=~/.ssh/ai-decision-studio-aws.pem
    BUNDLE="runtime/ai_decision_studio_functional_baseline/deployment_bundle/ai-decision-studio-app-bundle.tar.gz"

    scp -i "$SSH_KEY" "$BUNDLE" "$EC2_HOST:~/ads_uploads/"
    scp -i "$SSH_KEY" .env.aws "$EC2_HOST:~/ads_uploads/.env.aws"

Optional state archives:

    scp -i "$SSH_KEY" nextcloud-golden-baseline-v1.tar.gz "$EC2_HOST:~/ads_uploads/"
    scp -i "$SSH_KEY" ai-lab-golden-state-v1.tar.gz "$EC2_HOST:~/ads_uploads/"

Do not upload `.env.aws` to Git, GitHub, public bundles, issue trackers, or chat.

## Step 6 — Apply the bundle on EC2

On the EC2 host:

    set -euo pipefail

    cd /opt/ai-decision-studio

    rm -rf /tmp/ads_bundle
    mkdir -p /tmp/ads_bundle

    tar -xzf ~/ads_uploads/ai-decision-studio-app-bundle.tar.gz -C /tmp/ads_bundle

    rsync -a \
      /tmp/ads_bundle/ai-decision-studio-app-bundle/ \
      /opt/ai-decision-studio/app/

    chmod +x /opt/ai-decision-studio/app/scripts/*.sh 2>/dev/null || true

Install the real AWS env file:

    install -m 600 ~/ads_uploads/.env.aws /opt/ai-decision-studio/app/.env.aws

Validate:

    cd /opt/ai-decision-studio/app

    ls -lh .env.aws
    stat -c "%a %n" .env.aws

Expected permission is `600`.

Before building, verify that the real AWS env and the safe example expose the
same key contract:

    python3 scripts/validate_aws_env_contract.py \
      --env .env.aws \
      --example .env.aws.example

## Step 7 — Validate the AWS env and compose config

On the EC2 host:

    cd /opt/ai-decision-studio/app

    docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      config > /tmp/ads_aws_fresh_compose.yml

    grep -q "dockerfile: Dockerfile.product-api.aws" /tmp/ads_aws_fresh_compose.yml
    grep -q "image: ai-decision-studio-product-api:aws" /tmp/ads_aws_fresh_compose.yml

    echo "OK: AWS compose uses the product-api image"

This check must pass before any build.

## Step 8 — First boot: build and start all five containers

For a truly fresh EC2, start the full stack once. This is different from the
normal code-only redeploy path.

On the EC2 host:

    cd /opt/ai-decision-studio/app

    df -h /
    docker system df || true

    DOCKER_BUILDKIT=1 docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      up -d --build

    docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      ps

    docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      exec -T ollama ollama pull embeddinggemma:300m

Wait for health:

    for i in $(seq 1 60); do
      if curl -fsS http://127.0.0.1:8071/health; then
        echo
        echo "health OK after ${i}s"
        break
      fi

      if [ "$i" = "60" ]; then
        echo "ERROR: health did not return"
        docker compose \
          --env-file .env.aws \
          -p ai-decision-studio \
          -f docker-compose.aws.yml \
          ps
        docker logs ai-decision-studio-product-api-aws --tail 120 || true
        docker logs ai-decision-studio-frontend-aws --tail 120 || true
        exit 1
      fi

      sleep 2
    done

## Step 9 — Restore runtime/state baselines if needed

If this is a fresh state rebuild and you have the frozen archives, restore them.

On the EC2 host:

    cd /opt/ai-decision-studio/app

    if [ -f ~/ads_uploads/nextcloud-golden-baseline-v1.tar.gz ]; then
      ENV_FILE=.env.aws scripts/restore_nextcloud_golden_baseline.sh \
        --env-file .env.aws \
        --archive ~/ads_uploads/nextcloud-golden-baseline-v1.tar.gz \
        --delete-archive
    fi

    if [ -f ~/ads_uploads/ai-lab-golden-state-v1.tar.gz ]; then
      ENV_FILE=.env.aws scripts/restore_ai_lab_golden_state.sh \
        --env-file .env.aws \
        --archive ~/ads_uploads/ai-lab-golden-state-v1.tar.gz \
        --delete-archive
    fi

Then re-check:

    docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      ps

The Nextcloud golden baseline is a Docker volume snapshot stored outside Git.
It must be uploaded to the AWS host before restore. The WebDAV user in `.env.aws`
must match the restored Nextcloud user, and
`EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD` must be a valid password/app-password for
that user.

## Step 10 — Run AWS smoke

On the EC2 host:

    cd /opt/ai-decision-studio/app

    ENV_FILE=.env.aws BASE_URL=http://127.0.0.1:8071 scripts/smoke_aws.sh

This smoke should confirm:

- `/health` is OK
- Preferences endpoint works
- local Hugging Face server is not exposed
- Ollama preferred model is `nemotron-3-super:cloud`

During deploy, `scripts/deploy_aws.sh` also ensures the deploy-only
preloaded Ollama embedding model is available in the Ollama sidecar. The default
is `embeddinggemma:300m`, configured with
`AI_DECISION_STUDIO_OLLAMA_EMBEDDING_MODEL_PULL`. This does not override Runtime
Controls selections in the app. Set `SKIP_OLLAMA_EMBEDDING_MODEL_PULL=1` only if
the Ollama volume is managed separately.

## Step 11 — Run target readiness checks

Minimum AWS readiness checks:

    cd /opt/ai-decision-studio/app

    ENV_FILE=.env.aws BASE_URL=http://127.0.0.1:8071 \
      scripts/readiness_nextcloud_golden_baseline_check.sh \
      --env-file .env.aws \
      --base-url http://127.0.0.1:8071

    ENV_FILE=.env.aws BASE_URL=http://127.0.0.1:8011 \
      scripts/readiness_preferences_evals_surface_check.sh \
      --env-file .env.aws \
      --base-url http://127.0.0.1:8011

Additional readiness checks may be required before public demo exposure,
depending on whether Trello, Notion, hosted providers, and AI Lab baselines are
expected to be live.

## Step 12 — Code-only redeploy after first boot

After the five-container stack exists, use the AWS redeploy script for normal
code-only updates:

    cd /opt/ai-decision-studio/app

    ENV_FILE=.env.aws scripts/deploy_aws.sh
    ENV_FILE=.env.aws BASE_URL=http://127.0.0.1:8071 scripts/smoke_aws.sh

This path rebuilds/recreates `product-api` and `frontend` only. It is the
preferred fast path for AWS after first boot.

## Step 13 — Disk hygiene

After builds:

    df -h /
    docker system df

The deploy script prunes build cache. Avoid aggressive volume pruning.

Safe cleanup examples:

    docker builder prune -af || true
    docker image prune -f || true

Do not run:

    docker system prune -a --volumes

unless you intentionally want to destroy persistent Docker volumes.

## Step 14 — Optional read-only AWS audit role

If AWS CLI is installed and an EC2 read-only audit role is attached, validate:

    aws sts get-caller-identity --region <AWS_REGION>

The role is useful for checking security groups, attached volumes, public IPs,
and accidental resources. It is not required for the application to run.

## Rollback notes

If the new app bundle fails before containers are changed:

- restore the previous `/opt/ai-decision-studio/app` backup if one exists;
- keep `.env.aws` unchanged;
- rerun the previous known-good compose command.

If containers fail after a compose change:

    cd /opt/ai-decision-studio/app

    docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      ps

    docker logs ai-decision-studio-product-api-aws --tail 200
    docker logs ai-decision-studio-frontend-aws --tail 200

Keep `.env.oracle` only as a compatibility fallback on migrated hosts. New AWS
hosts should use `.env.aws` as the real env file.

## Final post-rebuild readiness

After a fresh AWS EC2 bootstrap or controlled rebuild, validate the stack from inside the VM:

    cd /opt/ai-decision-studio/app
    set -e

    python3 scripts/validate_aws_env_contract.py --env .env.aws --example .env.aws.example

    scripts/readiness_multi_environment_contract_check.sh

    ENV_FILE=.env.aws BASE_URL=http://127.0.0.1:8071 scripts/smoke_aws.sh

    BASE_URL=http://127.0.0.1:8071 scripts/readiness_admin_session_isolation_check.sh

    ENV_FILE=.env.aws scripts/readiness_trello_public_visibility_check.sh

    docker compose \
      --env-file .env.aws \
      -p ai-decision-studio \
      -f docker-compose.aws.yml \
      ps

Expected results:

- env contract returns `ok: true`;
- multi-environment contract readiness passes without manual skip flags;
- AWS smoke passes;
- admin session isolation passes;
- Trello public visibility passes;
- all stack services are `healthy`.

Expected stack services:

- `frontend`;
- `product-api`;
- `nextcloud`;
- `ollama`;
- `ppt-creator`.

For public/external validation from the operator machine:

    BASE_URL=http://<PUBLIC_IP>:8071

Validate:

    curl -fsS "$BASE_URL" >/tmp/ads_frontend.html
    curl -fsS "$BASE_URL/health" | python3 -m json.tool
    curl -fsS "$BASE_URL/api/auth/session" | python3 -m json.tool
    curl -fsS "$BASE_URL/api/preferences" -o /tmp/ads_preferences.json
    curl -fsS "$BASE_URL/api/product/document-library" -o /tmp/ads_doclib.json
    curl -fsS "$BASE_URL/api/product/run-history?compact=1&limit=100" -o /tmp/ads_run_history.json

The real AI Lab runtime endpoint is:

    /api/lab/runtime

Do not use `/api/lab/runtime-observability`; that is not a backend route.

Real external AI Lab/API endpoints validated after rebuild:

    /api/lab/overview
    /api/lab/runtime
    /api/lab/workflow-inspector
    /api/lab/benchmarks
    /api/lab/evals
    /api/lab/artifacts
    /api/lab/evidenceops
    /api/product/artifacts
    /api/runtime/controls

Admin external validation should confirm:

- `/api/auth/admin/login` returns role `admin`;
- `/api/auth/session` returns `can_publish_external: true`;
- `/api/preferences/connections/huggingface_inference/test` returns `status: connected`.

<!-- AWS_LINUX_ONLY_BOOTSTRAP_VALIDATION -->

## AWS Linux-only bootstrap validation

The AWS deployment has been validated from a stronger baseline than a Docker-ready host: a fresh EC2 state with Linux only.

Validated starting state:

~~~text
Docker absent
Docker Compose absent
No Axiovance containers
No Axiovance images
No Axiovance volumes
No Docker build cache
/opt/ai-decision-studio empty
/tmp free of previous deployment artifacts
~~~

The deployment still requires four input artifacts to be copied to the EC2 host before running the deployment script:

~~~text
/tmp/ai-decision-studio-app-bundle.tar.gz
/tmp/ai-decision-studio.env.aws
/tmp/nextcloud-golden-baseline-v1.tar.gz
/tmp/ai-decision-studio-product-data-baseline.tar.gz
~~~

The app bundle must remain code-only. It must not include real environment files, runtime state, Nextcloud data, product baseline data, or secrets. Baseline data is intentionally transported as separate tar archives and validated by SHA256.

The deployment entrypoint is:

~~~bash
cd /opt/ai-decision-studio/app
scripts/deploy_aws.sh
~~~

The deployment script is now responsible for bootstrapping the host when Docker is missing. It performs these actions idempotently:

~~~text
Install Docker when the docker command is absent
Install Docker Compose v2 when docker compose is absent
Enable/start the Docker service
Grant the current SSH session temporary Docker socket access when group membership has not refreshed yet
Render the single AWS compose contract
Restore the Nextcloud golden baseline when the Nextcloud volume is fresh/missing
Restore the Axiovance product data baseline when the product data root is fresh/missing
Pull the required Ollama embedding model
Build and start the AWS stack
Wait for the public health endpoint before cleanup
Clean temporary deployment artifacts and Docker build cache
~~~

The AWS compose contract is intentionally single-file:

~~~text
docker-compose.aws.yml
~~~

The required runtime services are:

~~~text
frontend
nextcloud
ollama
ppt-creator
product-api
~~~

Final validation command:

~~~bash
scripts/smoke_aws.sh
~~~

Expected successful end state:

~~~text
Docker installed
Docker Compose v2 installed
frontend healthy
nextcloud healthy
ollama healthy
ppt-creator healthy
product-api healthy
/health returns ok=true
scripts/smoke_aws.sh returns OK
Nextcloud golden baseline persisted under /opt/ai-decision-studio/golden_baseline
Product data baseline persisted under /opt/ai-decision-studio/baselines
Docker Build Cache cleaned to 0B or near-zero
~~~

Important cleanup rule:

~~~text
The post-deploy cleanup may prune Docker build cache.
It must not remove active runtime volumes.
It must not run docker image prune -a as a default post-deploy step.
~~~

The latest Linux-only validation confirmed that the deployment script can start from an EC2 host with no Docker installed, install Docker/Compose, restore both baselines, start all five services healthy, pass the smoke test, and clean build cache.
