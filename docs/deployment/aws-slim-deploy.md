# AWS slim deploy

Use this document for the current AWS slim deployment shape.

Official AWS slim topology:

- base compose: docker-compose.oracle-like.yml
- AWS override: docker-compose.aws-slim.override.yml
- env file: .env.aws
- product API Dockerfile: Dockerfile.aws-slim-product-api
- frontend Dockerfile: Dockerfile.frontend-public-demo

Expected AWS services:

- nextcloud
- ollama
- ppt-creator
- product-api
- frontend

Expected AWS host paths:

- /opt/ai-decision-studio/app for the application repository.
- /opt/ai-decision-studio/data for the product data root.

Data root contract on AWS:

- /opt/ai-decision-studio/data/baseline mounted to /app/baseline
- /opt/ai-decision-studio/data/runtime mounted to /app/runtime
- /opt/ai-decision-studio/data/artifacts mounted to /app/artifacts
- /opt/ai-decision-studio/data/users mounted to /app/users

The local versioned payload can be used as the source for populating the AWS data root:

- runtime/ai_decision_studio_functional_baseline/oracle_like_data/baseline
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/runtime
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/artifacts
- runtime/ai_decision_studio_functional_baseline/oracle_like_data/users

Basic validation:

- docker compose --env-file .env.aws -f docker-compose.oracle-like.yml -f docker-compose.aws-slim.override.yml config --services
- docker compose --env-file .env.aws -f docker-compose.oracle-like.yml -f docker-compose.aws-slim.override.yml ps

Helper scripts:

- scripts/deploy_aws_slim.sh
- scripts/smoke_aws_slim.sh

Security rule:

.env.aws is intentionally not versioned. Use .env.aws.example as the contract and keep real secrets on the host.
