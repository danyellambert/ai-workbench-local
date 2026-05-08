# Product overview

AI Decision Studio is the current product surface of this repository.

The current product is not the historical Streamlit app and not the old Gradio surface. Those historical entrypoints and demo flows are preserved under legacy/.

The active product stack is composed of:

- frontend: React/Vite build served by Nginx.
- product-api: FastAPI-compatible backend entrypoint through main_product_api.py.
- ppt-creator: presentation rendering sidecar.
- nextcloud: document/file integration sidecar.
- ollama: local/model provider sidecar where enabled.
- mounted data roots: baseline, runtime, artifacts, and users.

The frontend does not mount product data directly. It calls product-api. Product-api reads and writes the mounted data roots.

Main product capabilities represented in the current code and data roots include:

- document library and document-grounded workflows;
- AI Lab and benchmark/eval surfaces;
- EvidenceOps state and payloads;
- candidate review flows;
- action plan flows;
- presentation/deck artifact generation;
- run history and telemetry-style workflow state;
- runtime preferences and controls;
- preindexed RAG/public corpus state.

Current deployment modes:

- Local Docker uses .env.docker and docker-compose.local.yml.
- AWS uses .env.aws and docker-compose.aws.yml.
- Oracle-like deployment uses the same product topology concept with an environment-specific data root.

Documentation rule:

Docs in this directory should describe what exists in the product today. Historical phase notes, old demos, Streamlit/Gradio-specific flows, and already-executed handoffs should live under legacy/docs unless they are still required as current operational documentation.
