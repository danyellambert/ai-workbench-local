# AI Decision Studio documentation

This directory contains documentation for the current AI Decision Studio product.

Start here if you are new to the repository:

- product/overview.md — what the product is today and what surfaces are active.
- architecture/current-product-surface.md — how the frontend, product API, sidecars, and data roots relate.
- architecture/data-payload.md — the versioned Docker/AWS data payload and the four mounted roots.
- deployment/local-docker-compose.md — how to run the current product locally with Docker Compose.
- deployment/aws-slim-deploy.md — how the AWS slim deployment is structured.
- operations/backup-and-restore.md — operational backup and restore notes for local/AWS data roots.
- guides/ — task-oriented supporting workflow guides.
- reference/ — reference material for benchmarks and evidence/CV workflows.
- product/two-track-positioning.md — official product-vs-lab framing.
- operations/preindexed-nextcloud-import.md — operational guide for the preindexed Nextcloud import path.
- data/examples/ — small JSON examples used by benchmark/eval scripts.

Current official runtime paths:

- Local Docker: docker-compose.oracle-like.yml with .env.docker.
- AWS slim: docker-compose.oracle-like.yml plus docker-compose.aws-slim.override.yml with .env.aws.
- Product API entrypoint: main_product_api.py.
- Frontend Dockerfile: Dockerfile.frontend-public-demo.
- Local product API Dockerfile: Dockerfile.public-demo.
- AWS product API Dockerfile: Dockerfile.aws-slim-product-api.
- Versioned deploy payload: runtime/ai_decision_studio_functional_baseline/oracle_like_data.

Historical or secondary flows are kept under legacy/.
