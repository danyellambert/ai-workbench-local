# Capability Map

This map connects the current repository structure to the major engineering capabilities that evolved over the project history. It is organized by capability rather than by commit order, because several features were developed in multiple passes.

## Active Capability Threads

| Capability | Current Surface | Backend / Runtime Evidence | Public Documentation |
| --- | --- | --- | --- |
| Product shell | React/Vite app, sidebar, command center, product workflow pages | Nginx frontend container, Product API routing | `docs/product/overview.md`, `docs/product/product-evolution.md` |
| Product API | Workflow execution, document library, provider registry, artifacts, access control | `main_product_api.py`, `src/product/api.py`, `src/product/service.py` | `docs/architecture/current-product-surface.md` |
| Document grounding | import, extract, chunk, embed, sync, retrieve | RAG state, Chroma, LangChain/LangGraph helpers, mounted runtime roots | `docs/architecture/COMPLETE_ARCHITECTURE_BRIEF.md` |
| Workflows | Document Review, Policy Comparison, Action Plan, Candidate Review, Deck Generation | Product presenters, workflow payloads, run history | `docs/product/product-evolution.md` |
| Deck generation | deck contracts, PPTX service, previews, artifacts | `services/ppt_creator_app/ppt_creator/api.py`, artifact roots | `docs/architecture/executive-deck-generation/README.md` |
| Delivery integrations | Nextcloud, Trello, Notion, WebDAV, publish previews | `src/product/integration_hub.py`, credentials, delivery contracts | `docs/architecture/evidenceops/integration-trajectory.md` |
| AI provider control | OpenAI-compatible, Hugging Face, Ollama hosted-compatible, local Ollama embeddings | `src/providers/registry.py`, runtime controls, diagnostics | `docs/architecture/evals/ai-engineering-trajectory.md` |
| AI Lab | runtime observability, workflow inspector, benchmarks, evals, diagnostics, telemetry | telemetry logs, Actions DB, run history, eval payloads | `docs/architecture/evals/README.md` |
| Public/admin safety | public sessions, overlays, quotas, deck limits, admin-only publish | `src/product/public_execution_quota.py`, `src/product/public_execution_gate.py`, `src/product/deck_rate_limit.py` | `docs/operations/engineering-controls.md` |
| Deployment | local Docker, AWS, Caddy, private Docker network, mounted volumes | compose files, Dockerfiles, deploy scripts, Caddyfile | `docs/deployment/deployment-evolution.md` |
| Repository hygiene | README, roadmap, docs indexes, tests, scripts, requirements, legacy split | docs, validation scripts, CI gate | `docs/deployment/python-dependencies.md`, `docs/reference/legacy-research-and-experiments.md` |

## Current Product Architecture

The active architecture has three main boundaries:

1. Public edge:
   - user browser;
   - domain and DNS;
   - AWS public endpoint or local host port.

2. Private Docker stack:
   - Caddy public ingress on AWS;
   - frontend container;
   - Product API;
   - Nextcloud;
   - Ollama;
   - PPT Creator;
   - mounted runtime data.

3. External providers and delivery:
   - AI provider endpoints;
   - Trello;
   - Notion;
   - Nextcloud/WebDAV document repository;
   - product observability surfaces.

Local Docker and AWS share the same product idea: the frontend calls the Product API, the Product API owns state and integrations, and runtime data is mounted rather than baked into container images.

## Historical Capability Lines

### From Experimentation To Product

Earlier Streamlit, Gradio, Evidence CV, OCR, VL, benchmark, and Oracle deployment work provided the research base. The current product does not present those paths as the active user interface, but it preserves them under `legacy/` and reference documentation.

### From RAG Experiments To Workflow Grounding

Document-grounded RAG work became the current grounding preview, document import, retrieval, and evidence-backed workflow behavior. The active product still depends on grounded document context, but the frontend now exposes it through reviewable product pages instead of raw notebooks or one-off scripts.

### From Structured Outputs To Product Presenters

Structured output work started as extraction and eval discipline. It later became product presenter logic: workflow payloads are shaped into cards, summaries, action items, delivery sections, deck contracts, and publish previews.

### From EvidenceOps To Delivery Productization

EvidenceOps ideas evolved into current delivery controls. The active product now has preview-first Trello and Notion publishing, Nextcloud/WebDAV import paths, and PPT Creator artifacts. The UI label later shifted toward MCP Operations where the feature represents operational tooling.

### From Local/Oracle Deployments To Current Deployment Contracts

Deployment started with local and Oracle-like paths, then moved to a cleaner split:

- local Docker: `.env.docker` plus `docker-compose.local.yml`;
- AWS: `.env.aws` plus `docker-compose.aws.yml`;
- shared architecture: frontend, Product API, PPT Creator, Nextcloud, Ollama, mounted runtime roots.

## What Counts As Active

An item is active when it is part of the current React/Vite product, Product API, Docker compose contract, deployment documentation, validation path, or public docs index.

An item is historical when it is preserved under `legacy/`, described as reference material, or kept only to explain earlier research and engineering decisions.
