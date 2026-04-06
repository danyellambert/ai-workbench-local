# AI Workbench Local

[![phase8-evals](https://github.com/danyellambert/ai-workbench-local/actions/workflows/phase8-evals.yml/badge.svg)](https://github.com/danyellambert/ai-workbench-local/actions/workflows/phase8-evals.yml)

> **A local-first applied AI platform for document-grounded decision workflows, structured execution, evaluation, product UX, and executive artifact generation.**

AI Workbench Local is not a generic chatbot demo.

It is a portfolio-grade AI system designed to show how modern AI products should be built when the goal is not only text generation, but **grounded workflows, validated outputs, measurable quality, auditable behavior, and credible product architecture**.

This repository combines two complementary tracks:

- a **Business Workflow track** for document review, policy comparison, extraction, candidate analysis, and executive-ready outputs
- an **AI Engineering Lab track** for benchmarking, evaluation, routing, runtime analysis, observability, and controlled experimentation

In practical terms, the project already demonstrates how to:

- work with **local models** and optional external provider lanes
- run **document-grounded workflows** with retrieval and structured outputs
- validate results with **explicit schemas and execution contracts**
- compare model/runtime behavior with **repeatable benchmark evidence**
- persist **evaluation history, logs, and operational state** locally
- expose **EvidenceOps operations through a real local MCP server**
- generate **executive deck artifacts** from grounded workflow outputs

---

## Why this repository stands out

Most AI repositories stop at one layer:

- a thin UI around an API
- a toy RAG assistant
- a benchmark notebook
- a set of scripts without product framing

AI Workbench Local is stronger because it connects the full system:

1. **Product thinking** — workflows mapped to real decision-making tasks
2. **Engineering depth** — modular services, multiple surfaces, provider abstraction, guarded execution
3. **Quality discipline** — evals, benchmarks, logs, regression analysis, and diagnosis
4. **Operational maturity** — local-first reproducibility, runtime summaries, Docker, and artifact tracking
5. **Future-facing architecture** — MCP, product API foundations, EvidenceOps, and executive artifact pipelines

If you are a recruiter, hiring manager, or technical interviewer, the intended signal is not “I can call an LLM API.”

It is:

> **I can design and evolve an AI system across product UX, document intelligence, structured workflows, validation, evaluation, and operational concerns.**

---

## Product surfaces and entrypoints

This is not a single-surface demo. The repository already spans multiple interfaces, each with a different role in the ecosystem.

| Surface | Entrypoint / path | Role | Current status |
| --- | --- | --- | --- |
| Main AI Lab | `main.py` | Primary local experimentation and engineering dashboard | Implemented |
| Web product frontend | `frontend/` | Product north-star UX for workflows, artifacts, history, and AI Lab access | Implemented UI foundation |
| Product API | `main_product_api.py`, `src/product/api.py` | Dedicated API surface for product workflows and frontend integration | Foundation started |
| Gradio product surface | `main_gradio.py` | Product-facing workflow surface for faster UX experimentation | Implemented foundation |
| OpenAI-compatible sample app | `main_openai.py` | Alternate provider-focused app entrypoint | Implemented sample |
| Provider-specific experiments | `main_qwen.py` and related entrypoints | Focused runtime/provider experiments | Experimental |
| EvidenceOps MCP server | `scripts/run_evidenceops_mcp_server.py` | Real local MCP tool/resource surface | Implemented |
| PPT renderer host helper | `scripts/run_ppt_creator_renderer_host.sh` | Host-native integration helper for presentation export | Implemented helper |

The web frontend should be read as the **product north star**. Some views are already well defined but still partially backed by mock data while deeper backend integration continues.

---

## Current implementation status

The most honest and strongest way to read this repository is to separate **product vision**, **implemented platform foundations**, and **integration work still in progress**.

| Layer / surface | Status | What that means today |
| --- | --- | --- |
| Web product frontend in `frontend/` | **Implemented UI foundation** | A React/Vite product shell already exists with routes for landing, workflows, documents, deck center, run history, AI Lab, and settings |
| Frontend data wiring | **Partially mocked** | Several frontend views still rely on mock data while backend integration continues |
| Product API | **Foundation started** | `main_product_api.py` and `src/product/api.py` define a dedicated HTTP surface for product workflows |
| Streamlit AI Lab | **Implemented** | `main.py` is the richest currently wired engineering and experimentation surface |
| Gradio product surface | **Implemented foundation** | Supports workflow-oriented product UX experiments |
| Core services under `src/` | **Implemented foundation** | Retrieval, structured outputs, document-agent logic, benchmarking, logging, MCP, export, and product modules already exist |
| End-to-end frontend ↔ backend integration | **In progress** | The product frontend and backend foundations are converging, but not every page is fully live-wired yet |

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

## Full technology stack

This repository intentionally covers more than “LLM + UI.” It includes product UX, backend orchestration, retrieval, structured validation, evaluation, operations, and executive artifact generation.

| Layer | Technologies used here | Why they matter |
| --- | --- | --- |
| Core runtime | **Python 3.11** | Main backend, orchestration, workflows, services, evals, and app surfaces |
| Product web app | **React 18**, **TypeScript 5**, **Vite 5**, **Tailwind CSS 3**, **React Router 6**, **TanStack Query 5**, **Framer Motion**, **Zustand**, **Recharts**, **React Hook Form**, **Zod**, **Radix UI / shadcn-style primitives** | Defines the product-grade web surface and frontend architecture |
| Product / lab UI surfaces | **Streamlit**, **Gradio** | Support local experimentation, engineering visibility, and product workflow prototyping |
| Provider/runtime layer | **Ollama**, **OpenAI SDK / OpenAI-compatible APIs**, **Hugging Face local / server / inference lanes** | Enables local-first runtime operation with controlled multi-provider expansion |
| AI orchestration | **LangChain Community**, **LangChain Chroma**, **LangChain Text Splitters**, **LangGraph** | Supports retrieval flows, workflow evolution, and controlled orchestration |
| Retrieval & vector layer | **ChromaDB**, **sentence-transformers** | Powers local vector retrieval and embedding-backed context workflows |
| Document intelligence | **PyPDF**, **docling**, **Pillow**, **NumPy** | Supports parsing, extraction, OCR/VLM-adjacent flows, and artifact processing heuristics |
| Structured validation | **Pydantic** | Enforces contracts, validates payloads, and keeps structured execution reliable |
| Config & environment | **python-dotenv** | Local-first environment-driven configuration |
| Reporting & artifacts | **ReportLab**, **Matplotlib** | Reporting, charts, and artifact generation |
| Storage & ops | **SQLite**, **filesystem artifact stores**, JSON/JSONL logs | Local eval history, runtime logs, action state, artifacts, and worklogs |
| MCP / EvidenceOps | Local MCP server and client integration in `src/mcp/` and `src/services/evidenceops_mcp_client.py` | Real tool/resource integration instead of simulated tooling |
| Frontend quality | **Vitest**, **Playwright**, **ESLint** | Frontend testing and code-quality foundation |
| Backend quality | Python test suite under `tests/` | Verifies services, workflows, product foundations, and export logic |
| Packaging / reproducibility | **Docker**, **pip**, **npm** | Supports reproducible local execution and onboarding |

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
                           AI Workbench Local

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
cp .env.example .env
```

### 3. Run the main AI Lab application

```bash
streamlit run main.py
```

`main.py` is the canonical local entrypoint for the engineering surface.

### 4. Optional: run the OpenAI-compatible sample app

```bash
streamlit run main_openai.py
```

### 5. Optional: start the product API

```bash
python main_product_api.py
```

### 6. Optional: run the web product frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:8080` by default.

### 7. Optional: run the Gradio product surface

```bash
python main_gradio.py
```

### 8. Optional: start the executive renderer host helper

```bash
bash scripts/run_ppt_creator_renderer_host.sh
```

### 9. Optional: start the local EvidenceOps MCP server

```bash
python scripts/run_evidenceops_mcp_server.py
```

### 10. Optional: run the containerized baseline

```bash
docker build -t ai-workbench-local .
docker run --rm -p 8501:8501 --env-file .env ai-workbench-local
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

The `.env.example` file reflects the intended shape of the platform:

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
| Structured outputs | `src/structured/`, `docs/PHASE_5_STRUCTURED_OUTPUT_FOUNDATION.md` |
| Document Operations Copilot | `src/structured/document_agent.py`, `docs/PHASE_6_DOCUMENT_OPERATIONS_COPILOT.md` |
| Model comparison | `src/services/model_comparison.py`, `docs/PHASE_7_MODEL_COMPARISON.md`, `scripts/report_phase7_model_comparison_log.py` |
| Eval foundation | `docs/PHASE_8_EVAL_FOUNDATION.md`, `scripts/report_phase8_eval_store.py`, `scripts/run_phase8_live_evals.py` |
| EvidenceOps MCP | `src/mcp/evidenceops_server.py`, `scripts/run_evidenceops_mcp_server.py`, `docs/PHASE_9_5_EVIDENCEOPS_MCP_LOCAL_SERVER.md` |
| Executive deck generation | `src/services/presentation_export.py`, `docs/EXECUTIVE_DECK_GENERATION_*`, `scripts/run_presentation_export_smoke_suite.py` |
| Engineering hardening | `Dockerfile`, `docs/PHASE_10_ENGINEERING_PROFESSIONAL.md`, smoke/integration tests in `tests/` |

This section exists for a simple reason: a professional README should be impressive, but it should also be easy to defend line by line in a technical interview.

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

- wire the **web product frontend** into the product API and backend workflows
- sharpen the **product vs lab split** between frontend, Gradio, and Streamlit surfaces
- deepen **Executive Deck Generation** as a reusable product capability
- continue raising **evaluation and benchmark rigor** for routing, retrieval, OCR/VLM, and runtime choices
- extend **EvidenceOps** from local-first foundations toward broader external targets

Reference: `ROADMAP.md`

---

## Documentation map

### Best starting points

- `ROADMAP.md` — project chronology and direction
- `docs/INDEX_DOCUMENTATION.md` — organized documentation map
- `docs/POSITIONING_PROJECT_TWO_TRACKS.md` — official workflow-vs-lab framing
- `docs/PHASE_10_ENGINEERING_PROFESSIONAL.md` — engineering maturity direction
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md` — executive artifact capability direction
- `docs/PHASE_10_25_PRODUCT_SPLIT_GRADIO_AI_LAB.md` — rationale for the surface split

### Important capability clusters

- `docs/PHASE_4_DOCUMENT_RAG_FOUNDATION.md`
- `docs/PHASE_5_STRUCTURED_OUTPUT_FOUNDATION.md`
- `docs/PHASE_6_DOCUMENT_OPERATIONS_COPILOT.md`
- `docs/PHASE_7_MODEL_COMPARISON.md`
- `docs/PHASE_8_EVAL_FOUNDATION.md`
- `docs/PHASE_9_5_EVIDENCEOPS_MCP_LOCAL_SERVER.md`
- `docs/EXECUTIVE_DECK_GENERATION_*.md`

### Documentation naming conventions

- `PHASE_*` — canonical phase summaries and validation closures
- `EXECUTIVE_DECK_GENERATION_*` — architecture, contracts, rollout, UX, and governance for the deck capability
- `GUIDE_*` — practical operating guides for scripts and workflows
- `REFERENCE_*` — reference-oriented implementation or benchmark material

---

## Why this is a strong portfolio project

This repository is intentionally designed to be defendable in technical interviews.

It shows evidence of ability across:

- **product design** — defining workflows that map to real business problems
- **software architecture** — layered modules, multiple entrypoints, reusable services
- **LLM application engineering** — RAG, structured outputs, routing, guardrails, context strategies
- **AI evaluation** — benchmarks, local eval stores, regression signals, diagnosis
- **operations** — logs, runtime summaries, local persistence, environment-driven configuration
- **ecosystem thinking** — MCP, external renderer boundaries, product API evolution, and reusable artifact pipelines

In short, this repository reads like the work of someone building a real AI product system — not just a prompt demo.

---

## License

This repository is distributed under the terms defined in the `LICENSE` file at the project root.