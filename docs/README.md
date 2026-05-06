# AI Decision Studio documentation

This directory contains documentation for the current AI Decision Studio product.

Start here if you are new to the repository:

- product/overview.md — what the product is today and what surfaces are active.
- architecture/current-product-surface.md — how the frontend, product API, sidecars, and data roots relate.
- architecture/frontend-parity/ — curated frontend parity reference for the current product surface.
- architecture/data-payload.md — the versioned Docker/AWS data payload and the four mounted roots.
- deployment/local-docker-compose.md — how to run the current product locally with Docker Compose.
- deployment/aws-slim-deploy.md — how the AWS slim deployment is structured.
- deployment/python-dependencies.md — current single-file Python dependency contract.
- operations/backup-and-restore.md — operational backup and restore notes for local/AWS data roots.
- guides/ — task-oriented supporting workflow guides.
- reference/ — reference material for benchmarks and evidence/CV workflows.
- product/two-track-positioning.md — official product-vs-lab framing.
- operations/preindexed-nextcloud-import.md — operational guide for the preindexed Nextcloud import path.
- data/examples/ — small JSON examples used by benchmark/eval scripts.

Current official runtime paths:

- Local Docker: docker-compose.local.yml with .env.docker.
- AWS slim: docker-compose.aws-slim.yml with .env.aws.
- Product API entrypoint: main_product_api.py.
- Frontend Dockerfile: Dockerfile.frontend.
- Local product API Dockerfile: Dockerfile.product-api.local.
- AWS product API Dockerfile: Dockerfile.product-api.aws-slim.
- Python dependencies: requirements.txt.
- Versioned deploy payload: runtime/ai_decision_studio_functional_baseline/oracle_like_data.

Historical or secondary flows are kept under legacy/.

## Start here

- [`REVIEWER_GUIDE.md`](REVIEWER_GUIDE.md) — short review path for recruiters/interviewers.
- [`deployment/README.md`](deployment/README.md) — deployment documentation index.
- [`../tests/README.md`](../tests/README.md) — current Python test status and green gate.
- [`../scripts/README.md`](../scripts/README.md) — operational script catalog.
