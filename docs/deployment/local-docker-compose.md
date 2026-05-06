# Local Docker Compose

Use this document when running the current AI Decision Studio product locally through Docker Compose.

Official local Docker topology:

- compose file: docker-compose.local.yml
- env file: .env.docker
- frontend Dockerfile: Dockerfile.frontend
- local product API Dockerfile: Dockerfile.product-api.local
- product API entrypoint: main_product_api.py

Expected services:

- nextcloud
- ollama
- ppt-creator
- product-api
- frontend

Data payload used locally:

- runtime/ai_decision_studio_functional_baseline/oracle_like_data/baseline mounted to /app/baseline
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/runtime mounted to /app/runtime
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/artifacts mounted to /app/artifacts
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/users mounted to /app/users

Basic validation:

1. Confirm .env.docker exists.
2. Confirm the four oracle_like_data roots exist.
3. Render the compose config.
4. Build and start the stack.
5. Confirm the frontend and product-api containers are healthy.
6. Confirm the frontend reaches product-api through the Docker network.

Example commands:

- docker compose --env-file .env.docker -f docker-compose.local.yml config --services
- docker compose --env-file .env.docker -f docker-compose.local.yml up -d --build
- docker compose --env-file .env.docker -f docker-compose.local.yml ps

There is also a helper script for local Docker operation:

- scripts/run_local_docker.sh

Prefer the helper for local demos. It renders the same compose contract, restores
the Nextcloud golden baseline when the external archive exists, and pulls the
deploy-only preloaded Ollama embedding model into the `ollama_data` volume. The
default is `embeddinggemma:300m`, configured with
`AI_DECISION_STUDIO_OLLAMA_EMBEDDING_MODEL_PULL`; it does not override Runtime
Controls selections in the app. Set `SKIP_OLLAMA_EMBEDDING_MODEL_PULL=1` only
when the Ollama volume is managed separately.

Do not use legacy/compose/docker-compose.frontend-local.yml for the current product. That file is preserved for historical smoke/readiness context only.
