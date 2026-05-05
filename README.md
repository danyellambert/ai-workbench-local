# AI Decision Studio

## Deployment status

The current validated deployment target is the **AWS slim Docker deployment**.

- Current runtime path: **Product API + React/Vite frontend** through Docker Compose.
- AWS deploy path: `docs/deployment/AWS_FRESH_EC2_BOOTSTRAP.md` and `docs/deployment/REDEPLOY_FAST_PATH.md`.
- CI status: `product-ci.yml` validates Product API, frontend tests/build, and Docker/AWS compose contracts without deploying.
- Earlier Vercel work was **frontend-only / historical** and should not be treated as the current production contract.

<p align="center">
  <img src="data/materials_demo/Screenshot%202026-04-06%20at%2004.42.30.png" alt="AI Decision Studio landing page screenshot" width="49%" />
  <img src="data/materials_demo/Screenshot%202026-04-06%20at%2004.43.03.png" alt="AI Decision Studio application screenshot" width="49%" />
</p>

**AI Decision Studio** is a local-first applied AI platform for **document-grounded decision workflows**, **structured execution**, **evaluation**, and **executive artifact generation**.

This repository is meant to present a complete AI product system — not just a model wrapper, a chatbot demo, or a loose collection of experiments.

It is designed to show how an AI application becomes more credible when it combines:

- **workflow value** for real document-centered use cases
- **engineering rigor** through evaluation, observability, and structured execution
- **product direction** across Gradio, Streamlit, API, and web frontend surfaces

## Official product theory

It combines two linked layers:

- **Business Workflows** — the product-facing layer for document review, policy comparison, action plans, candidate review, and executive-ready outputs
- **AI Engineering Lab** — the engineering-facing layer for benchmarking, evaluation, routing, runtime analysis, observability, and controlled experimentation

In practical terms, the project already demonstrates how to:

- run **document-grounded workflows** with retrieval and structured outputs
- validate outputs with **explicit schemas and execution contracts**
- compare model/runtime behavior with **repeatable benchmark evidence**
- persist **evaluation history, logs, and operational state** locally
- expose **EvidenceOps operations** through a real local MCP server
- generate **executive deck artifacts** from grounded workflow outputs

## Current product reading

The current deployable product path is:

- **React/Vite frontend** as the current web product shell
- **Product API** as the backend contract for document-grounded workflows, run history, artifacts, preferences, and lab surfaces
- **Docker Compose / AWS slim deployment** as the validated runtime topology

The earlier surfaces are still useful, but they are no longer the main deployment contract:

- **Gradio** is a secondary workflow surface preserved from product exploration
- **Streamlit** is a historical AI Lab and engineering dashboard surface

This keeps the repository coherent:

- the **frontend + Product API path** represents the current deployable product
- the **workflow layer** solves real document-centered business problems
- the **AI Lab layer** preserves the evaluation, benchmark, observability, and experimentation history behind the product

## What is already implemented

The repository already includes real foundations for:

- **local model usage** and optional external provider lanes
- **document retrieval and RAG**
- **structured outputs with validation**
- **workflow-oriented document agents**
- **model comparison and benchmark reporting**
- **persistent eval storage and diagnosis**
- **EvidenceOps MCP tooling**
- **executive deck generation and presentation export flows**
- **engineering hardening** through Docker, logging, smoke tests, and artifact tracking

Today, the strongest interpretation is not “one finished app,” but rather **one coherent platform with multiple surfaces built on top of the same AI and workflow foundations**.

---

## Core business workflow families

### Document Review

Turn long or messy documents into:

- concise summaries
- key findings
- identified risks and gaps
- recommended next actions
- optional executive-ready deliverables

### Policy / Contract Comparison

Compare documents or versions to surface:

- meaningful differences
- likely impact
- compliance or risk observations
- review-ready findings for decision makers

### Action Plan / Evidence Review

Convert grounded findings into:

- checklists
- action items
- evidence bundles
- operational handoff artifacts

### Candidate Review

Use the CV pipeline and structured outputs to produce:

- candidate summaries
- strengths and gaps
- relevant experience signals
- initial recommendations
- executive-ready review artifacts

### Executive Deck Generation

Generate reusable business artifacts such as:

- benchmark and evaluation review decks
- document review decks
- policy comparison decks
- action plan decks
- candidate review decks
- evidence pack / audit decks

---

## Technology stack

This repository intentionally covers more than “LLM + UI.” It includes product UX, backend orchestration, retrieval, structured validation, evaluation, operations, and executive artifact generation.

### Backend and platform core

- **Python 3.11**
- **Pydantic**
- **python-dotenv**
- **SQLite**
- filesystem-backed artifacts and logs

### UI surfaces

- **Streamlit** for the AI Lab dashboard
- **Gradio** for the workflow-oriented product surface
- **React 18 + TypeScript 5 + Vite 5** for the web product shell
- **Tailwind CSS 3**, **React Router 6**, **TanStack Query 5**, **Framer Motion**, **Zustand**, **Recharts**, **React Hook Form**, **Zod**, and **Radix UI primitives** in the frontend

### Model and provider layer

- **Ollama**
- **OpenAI SDK / OpenAI-compatible APIs**
- **Hugging Face local / server / inference lanes**

### Retrieval, orchestration, and document intelligence

- **LangChain Community**
- **LangChain Chroma**
- **LangChain Text Splitters**
- **LangGraph**
- **ChromaDB**
- **sentence-transformers**
- **transformers**
- **PyPDF**
- **docling**
- **Pillow**
- **NumPy**

### Reporting, artifacts, and operations

- **ReportLab**
- **Matplotlib**
- local MCP server and client integration for **EvidenceOps**
- **Docker**, `pip`, and `npm` for reproducible local execution

### Quality layer

- Python test suite under `tests/`
- **Vitest**
- **Playwright**
- **ESLint**

### Backend dependency snapshot

The Python environment currently includes, among others:

- `streamlit`
- `gradio`
- `openai`
- `python-dotenv`
- `pydantic`
- `pypdf`
- `Pillow`
- `numpy`
- `chromadb`
- `langchain-community`
- `langchain-chroma`
- `langchain-text-splitters`
- `langgraph`
- `sentence-transformers`
- `transformers`
- `docling`
- `cryptography`
- `matplotlib`
- `reportlab`

### Frontend dependency snapshot

The web product surface uses:

- `react`, `react-dom`
- `vite`
- `tailwindcss`, `postcss`, `autoprefixer`
- `react-router-dom`
- `@tanstack/react-query`
- `react-hook-form`, `zod`, `@hookform/resolvers`
- `framer-motion`
- `recharts`
- `zustand`
- `@radix-ui/*` primitives
- `vitest`, `@testing-library/*`, `@playwright/test`, `eslint`

### Stack reading in one sentence

This is a **full-stack applied AI system** with a Python platform core, a React product frontend, local-first model/runtime support, retrieval and structured execution, and a serious evaluation and operations layer.

---

## Architecture at a glance

```text
                           AI Decision Studio

                ┌────────────────────────────────────┐
                │       Product / Workflow Layer     │
                │ Document Review, Comparison,       │
                │ Action Plans, Candidate Review,    │
                │ Executive Deck actions             │
                └────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
 ┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
 │  UI Surfaces  │   │ Domain Services  │   │ AI Engineering   │
 │ Web Frontend  │   │ retrieval,       │   │ benchmarks, eval │
 │ Streamlit Lab │   │ structured exec, │   │ diagnosis, logs, │
 │ Gradio Product│   │ export, MCP      │   │ runtime analysis │
 └───────────────┘   └──────────────────┘   └──────────────────┘
                               │
                               ▼
                 ┌─────────────────────────────┐
                 │ Local-first runtime/storage │
                 │ Ollama, SQLite, filesystem, │
                 │ Chroma, artifacts, logs     │
                 └─────────────────────────────┘
                               │
                               ▼
                ┌──────────────────────────────────┐
                │ Optional external/expansion lanes│
                │ HF runtimes, OpenAI-compatible,  │
                │ PPT renderer, external EvidenceOps│
                └──────────────────────────────────┘
```

### Architectural principles

- **Local-first by default** for control, reproducibility, and cost discipline
- **Workflow-driven product design** instead of a generic “ask anything” assistant
- **Structured contracts** around tasks, outputs, and artifacts
- **Separated product and lab surfaces** so user-facing workflows and engineering experimentation can evolve at different speeds
- **Evaluation and observability baked in** instead of added later

---

## Repository structure

```text
src/
  app/          # bootstrapping and application assembly
  evals/        # evaluation logic and thresholds
  evidence_cv/  # evidence-grounded CV extraction pipeline
  gradio_ui/    # Gradio product-facing surface
  mcp/          # local MCP server implementation
  product/      # product API, models, presenters, workflows
  providers/    # provider registry and runtime abstractions
  rag/          # ingestion, chunking, retrieval, PDF paths
  services/     # orchestration, export, comparison, runtime services
  storage/      # logs, eval stores, history, persistence
  structured/   # schemas, parsers, task handlers, workflows
  ui/           # Streamlit panels and UI components

frontend/       # React/Vite product surface
docs/           # canonical plans, contracts, specs, and phase docs
scripts/        # reports, benchmarks, validators, local helpers
tests/          # backend unit and integration tests
```

---

## Quickstart

### 1. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your environment file

```bash
cp .env.local.example .env.local
```

### 3. Run the local product stack

The current product path is the Product API plus the React frontend.

```bash
ENV_FILE=.env.local scripts/run_local_dev.sh
```

This starts:

- the Product API from `main_product_api.py`;
- the React/Vite frontend from `frontend/`;
- local runtime paths from the selected env file.

For a non-blocking contract check, use:

```bash
ENV_FILE=.env.local.example scripts/run_local_dev.sh --check
```

### 4. Optional: start only the Product API

```bash
python main_product_api.py
```

### 5. Optional: run only the web product frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev:frontend
```

This is for frontend-only visual work. For product-level validation, prefer `scripts/run_local_dev.sh` so the frontend and backend use the same local contract.

### 6. Optional: run the containerized product baseline

```bash
ENV_FILE=.env.docker scripts/run_local_docker.sh
```

For a non-building Docker contract check, use:

```bash
ENV_FILE=.env.docker.example scripts/run_local_docker.sh --config-only
```

### 7. Optional: run historical Streamlit / OpenAI-compatible surfaces

These entrypoints are preserved as earlier engineering surfaces. They are useful for understanding the project evolution, but they are not the primary product path.

```bash
streamlit run legacy/entrypoints/main_streamlit_lab.py
streamlit run legacy/entrypoints/main_openai_streamlit.py
```

The historical Streamlit Docker image is intentionally labeled as legacy:

```bash
docker build -f legacy/docker/Dockerfile.legacy-streamlit -t ai-decision-studio-streamlit-legacy .
```

### 8. Optional: run the historical Gradio product surface

```bash
python legacy/entrypoints/main_gradio_product_surface.py
```

### 9. Optional: start the executive renderer host helper

```bash
bash scripts/run_ppt_creator_renderer_host.sh
```

### 10. Optional: start the local EvidenceOps MCP server

```bash
python scripts/run_evidenceops_mcp_server.py
```

---

## Product API surface

The dedicated product API is intentionally small and workflow-oriented.

### Product API endpoints

- `GET /health`
- `GET /api/product/workflows`
- `GET /api/product/documents`
- `GET /api/product/grounding-preview`
- `POST /api/product/run-workflow`
- `POST /api/product/generate-deck`

### Engineering / export API endpoints

The broader engineering and artifact-facing API surface also exposes:

#### GET

- `/health`
- `/playground`
- `/profiles`
- `/assets`
- `/workflows`
- `/marketplace`
- `/ai/providers`
- `/ai/status`
- `/ai/models`
- `/templates`
- `/brand-packs`
- `/artifact`

#### POST

- `/validate`
- `/render`
- `/review`
- `/preview`
- `/generate`
- `/generate-and-render`
- `/preview-pptx`
- `/review-pptx`
- `/compare-pptx`
- `/promote-baseline`
- `/template`
- `/workflow-template`

This split matters because the repository already contains both a **product-facing API direction** and a **broader engineering / artifact operations surface**.

---

## Configuration themes

Environment-specific example files define the intended runtime contracts:

- local runtime defaults for **Ollama**
- optional **OpenAI** and **Hugging Face** lanes
- RAG chunking, retrieval, reranking, and PDF extraction controls
- OCR and VLM-assisted evidence extraction settings
- **Executive Deck Generation** integration settings
- **EvidenceOps** local and external adapter settings

That is a good indicator of maturity: configuration is treated as part of the platform design, not just incidental glue.

---

## Quality, evaluation, and operational posture

One of the biggest differences between this repository and a typical AI side project is that it does not stop at inference.

It explicitly invests in:

- **quality measurement**
- **persistent evaluation history**
- **benchmark evidence**
- **auditability**
- **operational logging**
- **controlled fallbacks**

### Evaluation foundations already present

- SQLite-backed local eval storage
- structured smoke evals and regression-oriented validation
- historical eval reporting and diagnosis scripts
- benchmark execution layers for model/runtime/retrieval decisions
- workflow evaluation paths for routing and guardrail behavior

### Operational and observability foundations already present

- runtime execution logs and summaries
- document-agent audit logs
- model comparison logs and aggregate reports
- EvidenceOps worklog and action-store persistence
- MCP telemetry and repository/action summaries
- controlled UI error handling and failure reporting

### Why this matters

This gives the repository a much more professional reading.

Instead of saying:

> “I built an AI app.”

the project can credibly say:

> “I built an AI platform with product workflows, measurable quality, reproducible local operation, and engineering evidence for how it behaves.”

---

## Concrete implementation evidence

For reviewers who want to verify the claims quickly, here are direct pointers into the codebase and documentation.

| Capability | Evidence in the repository |
| --- | --- |
| Product web surface | `frontend/src/App.tsx`, `frontend/src/pages/`, `frontend/src/components/` |
| Product API foundation | `main_product_api.py`, `src/product/api.py`, `src/product/service.py`, `src/product/models.py` |
| Structured outputs | `src/structured/`, `legacy/docs/phases/phase-5-structured-output-foundation.md` |
| Document Operations Copilot | `src/structured/document_agent.py`, `legacy/docs/phases/document-operations-copilot.md` |
| Model comparison | `src/services/model_comparison.py`, `legacy/docs/phases/phase-7-model-comparison.md`, `scripts/report_phase7_model_comparison_log.py` |
| Eval foundation | `legacy/docs/phases/eval-foundation.md`, `scripts/report_phase8_eval_store.py`, `scripts/run_phase8_live_evals.py` |
| EvidenceOps MCP | `src/mcp/evidenceops_server.py`, `scripts/run_evidenceops_mcp_server.py`, `legacy/docs/phases/local-evidenceops-mcp-server.md` |
| Executive deck generation | `src/services/presentation_export.py`, `docs/architecture/executive-deck-generation/`, `scripts/run_presentation_export_smoke_suite.py` |
| Deployment and hardening | `Dockerfile.public-demo`, `Dockerfile.aws-slim-product-api`, `Dockerfile.frontend-public-demo`, `docker-compose.oracle-like.yml`, `docker-compose.aws-slim.override.yml`, `docs/deployment/`, smoke/integration tests in `tests/` |

This section exists for a simple reason: the README should make the current product architecture easy to verify line by line.

---

## Roadmap direction

### Already demonstrated

- modular architecture evolution across multiple phases
- document-grounded retrieval foundations
- structured outputs with validation
- workflow-oriented document-agent behavior
- model comparison and benchmark reporting
- local eval persistence and diagnosis
- EvidenceOps local MCP foundations
- executive deck generation foundations
- Docker, logging, and smoke-test hardening

### Active direction

- continue hardening the multi-environment deployment path across local dev, local Docker, AWS, and future Oracle deployment
- keep historical engineering surfaces documented without making them the primary product path
- sharpen the **product vs lab split** between frontend, Gradio, and Streamlit surfaces
- deepen **Executive Deck Generation** as a reusable product capability
- continue raising **evaluation and benchmark rigor** for routing, retrieval, OCR/VLM, and runtime choices
- extend **EvidenceOps** from local-first foundations toward broader external targets

Reference: `ROADMAP.md`

---

## Documentation map

### Best starting points

- `ROADMAP.md` — project chronology and direction
- `legacy/docs/archive/old-documentation-index.md` — organized documentation map
- `docs/POSITIONING_PROJECT_TWO_TRACKS.md` — official workflow-vs-lab framing
- `legacy/docs/phases/engineering-hardening.md` — engineering maturity direction
- `docs/architecture/executive-deck-generation/product-capability.md` — executive artifact capability direction
- `legacy/docs/phases/product-split-gradio-ai-lab.md` — rationale for the surface split

### Important capability clusters

- `legacy/docs/phases/document-grounded-rag-foundation.md`
- `legacy/docs/phases/phase-5-structured-output-foundation.md`
- `legacy/docs/phases/document-operations-copilot.md`
- `legacy/docs/phases/phase-7-model-comparison.md`
- `legacy/docs/phases/eval-foundation.md`
- `legacy/docs/phases/local-evidenceops-mcp-server.md`
- `docs/architecture/executive-deck-generation/.md`

### Documentation naming conventions

- `PHASE_*` — canonical phase summaries and validation closures
- `EXECUTIVE_DECK_GENERATION_*` — architecture, contracts, rollout, UX, and governance for the deck capability
- `GUIDE_*` — practical operating guides for scripts and workflows
- `REFERENCE_*` — reference-oriented implementation or benchmark material

---

## Why this repository is technically meaningful

AI Decision Studio is organized as a product system rather than a single prompt demo.

It demonstrates:

- **product workflow design** — document review, policy comparison, action planning, candidate review, and executive deck generation;
- **software architecture** — separated product API, frontend surface, provider layer, storage layer, retrieval layer, structured workflow layer, and export services;
- **LLM application engineering** — RAG, structured outputs, routing, guardrails, context strategies, and provider abstraction;
- **evaluation discipline** — benchmarks, local eval stores, regression signals, diagnosis, and historical quality evidence;
- **operational maturity** — logs, runtime summaries, persistence, environment-driven configuration, public/admin session separation, and deployment contracts;
- **integration boundaries** — EvidenceOps, MCP, Nextcloud/WebDAV, Trello/Notion handoff paths, and an external presentation renderer.

In short, the repository documents the evolution from early local experimentation to a multi-surface AI product with measurable behavior and deployable runtime contracts.

---

## License

This repository is distributed under the terms defined in the `LICENSE` file at the project root.