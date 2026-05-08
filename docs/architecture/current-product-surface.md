# Current product surface

This document maps the current product surface at a high level.

Primary services:

- frontend: React/Vite application served by Nginx.
- product-api: backend service started from main_product_api.py.
- ppt-creator: presentation generation/rendering sidecar.
- nextcloud: file/document integration sidecar.
- ollama: model provider sidecar where enabled.

Primary compose files:

- docker-compose.local.yml
- docker-compose.aws.yml

Primary Dockerfiles:

- Dockerfile.product-api.local for local product-api image.
- Dockerfile.product-api.aws for AWS product-api image.
- Dockerfile.frontend for the current frontend image.

Current product data contract:

- product-api reads /app/baseline.
- product-api reads and writes /app/runtime.
- product-api reads and writes /app/artifacts.
- product-api reads and writes /app/users.
- frontend does not mount these directories; it calls product-api.

Current product concepts visible in code/data:

- product document library;
- run history;
- artifacts and presentation exports;
- AI Lab overview/benchmarks/evals;
- EvidenceOps state;
- candidate review;
- action plan publishing/review;
- RAG/preindexed public corpus;
- runtime preferences and controls.

Historical surfaces:

The old Streamlit, Gradio, and frontend-local smoke/readiness flows are preserved under legacy/. They are not the official Docker/AWS product path.
