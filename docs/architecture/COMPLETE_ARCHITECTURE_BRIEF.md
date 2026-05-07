# AI Decision Studio - Complete Architecture Brief

## 1. Product Boundary

AI Decision Studio is a local-first applied AI product for document-grounded decision workflows.

The active product is composed of:

- React/Vite frontend
- Python Product API served by `main_product_api.py`
- Docker Compose runtime with five services
- Mounted functional baseline payload
- RAG and document indexing layer
- AI provider abstraction for Ollama, OpenAI-compatible APIs, and Hugging Face lanes
- Nextcloud WebDAV document repository
- Trello and Notion publishing integrations
- ppt-creator sidecar for executive deck generation
- AI Lab for benchmarks, evals, runtime controls, model comparison, EvidenceOps, observability, and workflow inspection

Historical Streamlit, Gradio, heavy local AI dependencies, and older Oracle-specific paths are preserved under `legacy/`. They are not part of the active product runtime.

## 2. Deployment Topologies

The repository supports two active Docker deployment contracts.

### Local Docker

Local Docker uses:

- `.env.docker`
- `docker-compose.local.yml`
- `Dockerfile.product-api.local`
- `Dockerfile.frontend`
- `services/ppt_creator_app/Dockerfile`

The local stack is started through:

```bash
ENV_FILE=.env.docker scripts/run_local_docker.sh
```

The local Docker script:

- renders the local compose contract;
- restores the Nextcloud golden baseline when configured;
- starts the five-service stack;
- ensures the configured Ollama embedding model is available;
- checks `/health` through the frontend/Nginx entrypoint.

### AWS Slim

AWS slim uses:

- `.env.aws`
- `docker-compose.aws-slim.yml`
- `Dockerfile.product-api.aws-slim`
- `Dockerfile.frontend`
- `services/ppt_creator_app/Dockerfile`

AWS slim is deployed through:

```bash
ENV_FILE=.env.aws scripts/deploy_aws_slim.sh
```

AWS slim is a single-compose-file contract. It does not layer `docker-compose.local.yml` with an override.

The AWS deploy script:

- validates the rendered compose file;
- restores AWS baseline folders when needed;
- starts Ollama early;
- pulls the configured Ollama embedding model, normally `embeddinggemma:300m`;
- rebuilds and recreates all five services;
- checks the frontend health endpoint.

## 3. Planned DNS And Public Edge

The current AWS deployment exposes the frontend container through the host port configured in `.env.aws`, normally:

- public frontend bind host: `0.0.0.0`
- public frontend port: `8071`
- internal frontend container port: `8080`

The future production DNS layer should sit in front of this AWS host.

Recommended external flow:

```text
User Browser
  -> DNS provider / Route 53
  -> A record or CNAME
  -> AWS Elastic IP or Load Balancer
  -> TLS termination / reverse proxy
  -> frontend service on host port 8071
  -> Nginx inside frontend container
  -> React static app and proxied API routes
```

Recommended DNS records:

- `ai-decision-studio.example.com` as an `A` record pointing to an AWS Elastic IP, or as a `CNAME` pointing to a load balancer DNS name.
- Optional `www.ai-decision-studio.example.com` as a `CNAME` to the canonical hostname.

Recommended AWS networking:

- expose `80` and `443` publicly through a reverse proxy or load balancer;
- keep direct `8071` exposure temporary or restricted once DNS/TLS is configured;
- avoid exposing Product API port `8011` publicly unless there is a deliberate operational reason;
- keep Nextcloud, Ollama, and ppt-creator private inside the Docker network.

The repository currently models the application stack, not a full managed AWS edge. DNS, TLS, Elastic IP, Route 53, ALB, CloudFront, Caddy, or host-level Nginx would be infrastructure additions around the current compose deployment.

## 4. Container Runtime

Both local Docker and AWS slim run the same five logical services.

### frontend

The frontend service is built from `Dockerfile.frontend`.

Build stages:

- Node 20 Alpine builds the React/Vite app.
- Nginx 1.27 Alpine serves the compiled static files.

Runtime behavior:

- serves the SPA from `/usr/share/nginx/html`;
- listens on container port `8080`;
- proxies `/api/` to `product-api:8011`;
- proxies `/health` to `product-api:8011/health`;
- falls back to `index.html` for client-side routes.

The frontend is the public user-facing entrypoint.

### product-api

The Product API is built from:

- `Dockerfile.product-api.local` for local Docker;
- `Dockerfile.product-api.aws-slim` for AWS slim.

It runs:

```bash
python main_product_api.py
```

It listens on port `8011`.

Responsibilities:

- product workflow catalog;
- document library;
- upload and delete flows;
- Nextcloud import and sync;
- RAG indexing and retrieval;
- workflow execution;
- deck generation orchestration;
- Trello and Notion publishing;
- run history;
- artifact serving;
- runtime controls;
- preferences and provider settings;
- AI Lab payloads;
- EvidenceOps state;
- admin/session behavior;
- health endpoint.

The Product API owns all mounted data roots. The frontend does not mount runtime data directly.

### ppt-creator

The ppt-creator service is built from `services/ppt_creator_app/Dockerfile`.

It exposes port `8787` inside the Docker network.

Responsibilities:

- accepts structured deck contracts from the Product API;
- renders PowerPoint artifacts;
- generates previews and export metadata;
- supports executive deck generation for document review, policy comparison, action plan, candidate review, EvidenceOps/evidence pack, and benchmark/eval review flows.

The Product API reaches it through:

```text
http://ppt-creator:8787
```

### nextcloud

The Nextcloud service uses:

```text
nextcloud:29-apache
```

Responsibilities:

- provides a WebDAV document repository;
- stores demo/reference documents;
- supports the EvidenceOps demo folder;
- supports import into the Product API document library.

The Product API talks to Nextcloud through WebDAV:

```text
http://nextcloud/remote.php/dav/files/<username>
```

The expected root folder is usually:

```text
/EvidenceOpsDemo
```

Credentials are required. A user can deploy the stack, but Product API import from Nextcloud requires a configured username and password/app password in the selected environment file.

### ollama

The Ollama service uses:

```text
ollama/ollama
```

Responsibilities:

- local model provider sidecar;
- local embedding model host when Ollama embeddings are selected;
- optional local generation path;
- runtime/provider readiness checks.

The deploy scripts can automatically pull:

```text
embeddinggemma:300m
```

through:

```text
AI_DECISION_STUDIO_OLLAMA_EMBEDDING_MODEL_PULL
```

This can be disabled with:

```text
SKIP_OLLAMA_EMBEDDING_MODEL_PULL=1
```

## 5. Internal Docker Network

All services share a private Compose network.

Typical internal service URLs:

```text
frontend -> product-api:8011
product-api -> ppt-creator:8787
product-api -> nextcloud:80
product-api -> ollama:11434
```

The public browser should normally enter through the frontend service only.

## 6. HTTP Request Flow

### Browser To Product API

```text
Browser
  -> DNS / public AWS endpoint
  -> frontend container on 8080
  -> Nginx
  -> /api/* proxy
  -> product-api:8011
```

The frontend calls Product API endpoints through the same origin path `/api/...`.

### Browser To React App

```text
Browser
  -> frontend container
  -> Nginx static files
  -> React Router
  -> product pages and AI Lab pages
```

### Health Check

```text
Browser or deploy script
  -> /health
  -> frontend Nginx proxy
  -> product-api:8011/health
```

## 7. Frontend Architecture

The frontend is a React 18 + TypeScript + Vite application.

Main frontend technologies:

- React
- TypeScript
- Vite
- Tailwind CSS
- Radix UI primitives
- TanStack Query
- React Router
- Zustand
- Framer Motion
- Recharts
- React Hook Form
- Zod
- lucide-react
- cmdk
- Sonner
- date-fns
- Playwright and Vitest for frontend validation

Main user surfaces:

- landing page;
- guided product tour;
- overview page;
- workflow catalog;
- document library;
- document review;
- policy comparison;
- action plan;
- candidate review;
- deck center;
- run history;
- runtime controls;
- preferences;
- AI Lab overview;
- benchmarks;
- evals and diagnosis;
- EvidenceOps;
- chat;
- workflow inspector;
- runtime observability;
- advanced experiments;
- structured outputs;
- model comparison.

The frontend is product-focused and does not own workflow execution. It renders state, controls, and artifacts provided by the Product API.

## 8. Product API Surface

Important Product API routes include:

```text
GET  /health
GET  /api/auth/session

GET  /api/product/workflows
GET  /api/product/documents
GET  /api/product/document-library
POST /api/product/upload-documents
POST /api/product/delete-documents
GET  /api/product/upload-jobs/<job_id>

GET  /api/product/command-center
GET  /api/product/integrations
GET  /api/product/integrations/notion
GET  /api/product/integrations/nextcloud
GET  /api/product/integrations/nextcloud/open
POST /api/product/integrations/nextcloud/import
POST /api/product/integrations/nextcloud/sync

GET  /api/product/run-history
GET  /api/product/run-history/<run_id>
POST /api/product/run-history/<run_id>/rerun

GET  /api/product/artifacts
GET  /api/product/artifacts/<artifact_id>
GET  /api/product/artifact
GET  /api/product/grounding-preview

POST /api/product/run-workflow
POST /api/product/generate-deck
POST /api/product/publish-to-trello
POST /api/product/publish-to-notion

GET  /api/lab/overview
GET  /api/lab/runtime
GET  /api/lab/chat
GET  /api/lab/workflow-inspector
GET  /api/lab/benchmarks
GET  /api/lab/evals
GET  /api/lab/artifacts
GET  /api/lab/evidenceops
GET  /api/lab/evidenceops/search

POST /api/lab/workflow-inspector/run
POST /api/lab/chat/sessions
POST /api/lab/chat/sessions/<id>/delete
POST /api/lab/chat/sessions/<id>/messages
POST /api/lab/evidenceops/sync
POST /api/lab/evidenceops/actions/<id>

GET  /api/runtime/controls
POST /api/runtime/controls
GET  /api/preferences
POST /api/preferences
POST /api/preferences/connections/<id>/test
POST /api/preferences/connections/<id>/credential

POST /api/auth/admin/login
POST /api/auth/admin/logout
```

## 9. Core Product Workflows

The workflow product is organized around document-grounded decision workflows.

Primary workflows:

- Document Review
- Policy / Contract Comparison
- Action Plan
- Candidate Review
- Executive Deck Generation
- Evidence Pack / EvidenceOps review
- Benchmark and eval review

The general workflow path is:

```text
User selects workflow
  -> frontend sends workflow request
  -> Product API resolves documents and runtime preferences
  -> RAG layer retrieves grounded context when needed
  -> provider registry selects the active model/provider
  -> structured workflow execution runs
  -> output is normalized into product response models
  -> telemetry and run history are written
  -> optional delivery actions publish to Trello, Notion, or artifacts
```

## 10. Document And RAG Architecture

The document pipeline supports:

- local upload;
- Nextcloud WebDAV import;
- preindexed public corpus activation;
- extraction;
- chunking;
- embeddings;
- Chroma synchronization;
- canonical JSON fallback;
- retrieval;
- grounding preview;
- run-level document reuse.

Important RAG components:

- `src/rag/loaders.py`
- `src/rag/chunking.py`
- `src/rag/vector_store.py`
- `src/rag/service.py`
- `src/rag/langchain_adapter.py`
- `src/product/ingestion_jobs.py`
- `src/product/preindexed_corpus.py`

Supported AI/RAG technologies:

- ChromaDB
- LangChain Community loaders
- LangChain Text Splitters
- LangChain Chroma adapter
- LangGraph structured workflow path
- PyPDF
- Pillow
- NumPy
- Ollama embeddings
- OpenAI-compatible embeddings/generation
- Hugging Face provider lanes

The system keeps a canonical JSON RAG store and can synchronize it to Chroma. If Chroma is unavailable or stale, the product can fall back to the local canonical store.

## 11. Preindexed Nextcloud Import

The product includes a fast path for known Nextcloud demo documents.

Flow:

```text
User opens Documents
  -> clicks Import from Nextcloud
  -> selects documents
  -> Product API checks hidden preindexed corpus
  -> if document exists, chunks and embeddings are activated
  -> normal upload job stages are emitted
  -> document appears indexed in the library
```

This preserves the user-facing indexing experience while avoiding expensive or slow reprocessing for known demo material.

The visible behavior still looks like extraction, chunking, embeddings, and index sync. Internally, the system may activate prebuilt chunks and embeddings instead of recomputing them.

## 12. Runtime Data Contract

The active payload lives under:

```text
runtime/ai_decision_studio_functional_baseline/oracle_like_data/
```

The `oracle_like_data` name is historical. It is the current functional baseline payload for local Docker and AWS slim.

Mounted roots inside Product API:

```text
/app/baseline
/app/runtime
/app/artifacts
/app/users
```

Host roots:

- local Docker: usually under `./runtime/ai_decision_studio_functional_baseline/oracle_like_data`
- AWS slim: usually under `/opt/ai-decision-studio/data`

Root responsibilities:

```text
baseline/
  immutable or reference demo data
  benchmark runs
  public materials
  reference artifacts
  deck samples
  eval evidence

runtime/
  active mutable runtime state
  logs
  caches
  RAG stores
  EvidenceOps state
  product preferences
  runtime controls
  workflow history
  telemetry
  eval databases

artifacts/
  generated files
  exported decks
  previews
  thumbnails
  workflow outputs

users/
  admin overlays
  session state
  user-scoped runtime overlays
```

## 13. Runtime State Files

Important runtime state includes:

```text
runtime/cache/lab/evidenceops_payload.json
runtime/evals/phase8/phase8_eval_runs.sqlite3
runtime/logs/evidenceops/worklog.json
runtime/logs/product/telemetry_runs.json
runtime/logs/product/workflow_history.json
runtime/logs/runtime/runtime_execution_log.json
runtime/state/evidenceops/actions.sqlite3
runtime/state/evidenceops/repository_snapshot.json
runtime/state/lab/chat_sessions.json
runtime/state/lab/workflow_runs.json
runtime/state/product/preferences.json
runtime/state/product/runtime_controls.json
runtime/state/rag/preindexed_public_corpus.json
runtime/state/rag/preindexed_public_corpus_documents.json
runtime/state/rag/rag_store.json
runtime/state/rag/rag_store_documents.json
```

These files explain why normal product interaction can modify runtime state. Indexing, importing, running workflows, testing providers, publishing outputs, or chatting in AI Lab can legitimately update logs, caches, RAG state, run history, and telemetry.

## 14. AI Provider Architecture

The product has a provider registry instead of hardcoding one model path.

Provider lanes include:

- Ollama local sidecar
- Ollama hosted-compatible path
- OpenAI-compatible APIs
- Hugging Face inference path
- local/server Hugging Face experimental lanes

Runtime preferences control:

- generation provider;
- embedding provider;
- model selection;
- embedding model;
- retrieval settings;
- provider readiness;
- credential availability;
- runtime profile.

Ollama is included as a sidecar for local-first operation. External provider credentials are configured through environment variables and product preferences.

## 15. LangChain And LangGraph Usage

LangChain is used in controlled, optional strategy paths:

- LangChain Community loaders for basic TXT/CSV-style loading experiments;
- LangChain Recursive Text Splitter as an optional chunking strategy;
- LangChain Chroma as an optional retrieval adapter.

LangGraph is used for structured workflow experimentation and workflow inspection:

- direct execution remains available;
- LangGraph context-retry path can be selected for structured/document-agent execution;
- failures fall back to direct execution;
- AI Lab records direct vs LangGraph comparisons.

This makes LangChain/LangGraph part of the AI engineering layer without forcing every product path through them.

## 16. EvidenceOps Architecture

EvidenceOps is the product's evidence and operations layer.

It includes:

- repository snapshot state;
- worklog state;
- actions database;
- EvidenceOps cache payload;
- Nextcloud-backed document repository;
- MCP server support;
- AI Lab EvidenceOps page;
- search and sync APIs;
- delivery metadata in run history.

EvidenceOps connects product outputs back to operational evidence, tasks, and external repositories.

## 17. External Integrations

### Nextcloud

Used for:

- document repository;
- EvidenceOps demo material;
- WebDAV import;
- public reference corpus flow.

Requires:

- base WebDAV URL;
- username;
- password or app password;
- root path.

### Trello

Used for:

- publishing workflow outputs into cards/lists;
- delivery loop demonstration;
- run-history delivery metadata.

Requires:

- API key;
- token;
- board/list IDs.

### Notion

Used for:

- publishing workflow outputs into a Notion database;
- delivery loop demonstration;
- run-history delivery metadata.

Requires:

- integration token;
- database ID.

### Ollama

Used for:

- local embeddings;
- optional local generation;
- local runtime readiness;
- embedding model pull automation.

Requires no login for local Ollama model pulls, but the host must have network access to download models.

### Hugging Face

Used for:

- optional provider lanes;
- inference route experiments;
- benchmark/provider comparison work.

May require token depending on the selected model/provider path.

### OpenAI-Compatible APIs

Used for:

- optional hosted generation;
- optional hosted embeddings;
- model comparison;
- runtime profile experiments.

Requires provider credentials when selected.

## 18. Executive Deck Generation

Deck generation is implemented through a sidecar architecture.

Flow:

```text
Frontend
  -> Product API /api/product/generate-deck
  -> Product API builds deck contract
  -> ppt-creator service renders presentation
  -> generated files are written to artifacts
  -> frontend displays artifact metadata, preview, and download/open options
```

Deck-related capabilities include:

- deck contracts;
- renderer payload mapping;
- artifact lifecycle;
- preview manifests;
- quality and governance documentation;
- workflow-specific deck families.

Supported or documented deck families include:

- document review deck;
- policy/contract comparison deck;
- action plan deck;
- candidate review deck;
- evidence pack deck;
- benchmark/eval executive review deck.

## 19. AI Lab Architecture

AI Lab is the engineering observability layer.

It exposes:

- runtime overview;
- model/provider readiness;
- benchmarks;
- evals;
- diagnosis;
- workflow inspector;
- direct vs LangGraph traces;
- model comparison;
- EvidenceOps state;
- chat sessions;
- runtime observability;
- generated artifacts.

It uses stored benchmark runs, eval databases, runtime logs, telemetry files, provider settings, and workflow traces to explain system behavior.

## 20. Observability And Auditability

The product records:

- workflow history;
- telemetry runs;
- runtime execution logs;
- model comparison logs;
- LangChain shadow logs;
- LangGraph shadow logs;
- EvidenceOps worklog;
- RAG indexing state;
- provider readiness;
- generated artifact metadata.

These records allow the system to answer:

- what ran;
- which documents were used;
- which provider/model was selected;
- whether retrieval was used;
- what artifacts were generated;
- where outputs were delivered;
- whether evals or benchmarks show regression risk.

## 21. Validation And Operations

Important operational scripts include:

```text
scripts/run_local_docker.sh
scripts/deploy_aws_slim.sh
scripts/smoke_aws_slim.sh
scripts/readiness_multi_environment_contract_check.sh
scripts/run_current_test_gate.sh
scripts/validate_aws_env_contract.py
scripts/build_deployment_bundle.sh
```

Operational validation covers:

- compose rendering;
- AWS single-compose-file contract;
- local Docker contract;
- required five-service deployment;
- Product API health;
- frontend surface;
- Nextcloud assumptions;
- Ollama embedding model availability;
- environment variable contracts;
- integration/provider readiness;
- AI Lab content;
- EvidenceOps cache;
- candidate review;
- presentation export;
- run history.

## 22. Security And Credential Boundary

Secrets are not expected to be committed.

Environment-specific files provide:

- admin username;
- admin password hash;
- session secret;
- Nextcloud username/password;
- Trello key/token;
- Notion token;
- external AI provider API keys;
- hosted provider URLs;
- runtime limits.

For AWS:

- `.env.aws.example` documents required keys;
- real `.env.aws` should stay private;
- Product API and frontend should be the only public-facing app layer;
- service-to-service traffic should remain inside Docker network;
- DNS/TLS/reverse proxy should terminate public traffic before reaching the app.

## 23. Diagram Nodes To Include

A complete architecture diagram should include these node groups.

### Public Edge

- User Browser
- DNS provider / Route 53
- Domain name
- AWS Elastic IP or Load Balancer
- TLS termination / reverse proxy
- EC2 host / Docker Engine

### Docker Compose Stack

- frontend container
- Product API container
- ppt-creator container
- Nextcloud container
- Ollama container
- private Docker network

### Frontend Layer

- React
- Vite
- Nginx
- React Router
- TanStack Query
- Product workbench
- AI Lab pages

### Backend Layer

- Product API
- Workflow service
- Document library
- Integration hub
- Ingestion jobs
- RAG service
- Provider registry
- Runtime controls
- Preferences
- Telemetry
- Artifact service
- EvidenceOps services

### AI/RAG Layer

- Ollama
- OpenAI-compatible providers
- Hugging Face providers
- embeddinggemma:300m
- ChromaDB
- canonical JSON RAG store
- LangChain loaders/splitters/Chroma adapter
- LangGraph structured workflow path

### Data Layer

- `/app/baseline`
- `/app/runtime`
- `/app/artifacts`
- `/app/users`
- Nextcloud Docker volume
- Ollama Docker volume
- ppt-creator workspace volume

### External Integrations

- Nextcloud WebDAV
- Trello API
- Notion API
- Ollama model registry
- OpenAI-compatible API endpoints
- Hugging Face inference endpoints

### Operations Layer

- local Docker script
- AWS deploy script
- AWS smoke script
- readiness contract check
- test/eval scripts
- deployment bundle script

## 24. Primary Architecture Flow For Diagram

The main diagram should show this flow:

```text
User Browser
  -> DNS / AWS public edge
  -> Frontend Nginx
  -> React application
  -> Product API
  -> Workflow service
  -> RAG service
  -> Provider registry
  -> Ollama / OpenAI-compatible / Hugging Face
  -> Product response
  -> Run history + telemetry
  -> Optional deck generation through ppt-creator
  -> Optional publishing to Trello / Notion
  -> Optional document import from Nextcloud
  -> Runtime state and artifacts persisted to mounted data roots
```

## 25. Key Architectural Message

AI Decision Studio is not only a demo UI over an LLM. It is a complete applied AI product architecture:

- user-facing workflow product;
- document-grounded RAG system;
- versioned runtime payload;
- local and AWS deployment contracts;
- AI provider abstraction;
- Nextcloud/Trello/Notion delivery loop;
- deck-generation sidecar;
- runtime controls;
- benchmark and eval infrastructure;
- AI Lab observability;
- EvidenceOps state and operational evidence.

The architecture is designed so the product can run locally or on AWS while preserving the same core runtime contract and keeping mutable state outside the container images.
