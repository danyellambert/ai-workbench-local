# AI Decision Studio Frontend

This is the **web product surface** for the AI Workbench Local ecosystem.

If the root repository explains the platform as a whole, this folder explains the **product experience the platform is converging toward**.

In the UI, this surface is branded as **AI Decision Studio**. In architectural terms, it should be read as the frontend north star for **AI Workbench Local**.

---

## What this frontend is

This application is a React/Vite product shell for a document-grounded AI platform focused on:

- **Document Review**
- **Policy / Contract Comparison**
- **Action Plan / Evidence Review**
- **Candidate Review**
- **Executive Deck Generation** as a transversal capability
- **AI Lab** access for chat, structured outputs, model comparison, and EvidenceOps

The goal is to make the repository read less like “a big Streamlit experiment” and more like a real product system with:

- a clear landing page
- an operational command center
- workflow-centric navigation
- artifact and history surfaces
- a dedicated place for engineering tooling and observability

---

## Current status

The strongest and most honest way to describe this frontend is:

| Area | Status | Notes |
| --- | --- | --- |
| Information architecture | **Implemented** | Route structure, shell, navigation, workflow grouping, and product hierarchy are already defined |
| Visual product surface | **Implemented** | Landing page, app shell, workflow catalog, command center, document library, deck center, and AI Lab pages already exist |
| Data integration | **Partially mocked** | Many current pages read from `src/lib/mock-data.ts` while the backend integration path is still being connected |
| API integration | **In progress** | The repository now includes `main_product_api.py` as a foundation for a dedicated product API |
| Role inside the repo | **Product north star** | This frontend expresses what the end-user experience should become as the platform layers converge |

So yes: this frontend is real and worth showcasing in the README.

But it should be presented as a **product surface in active integration**, not as if every route is already fully wired to production backend flows.

---

## Route map

The current route structure already describes the product clearly.

### Public route

- `/` — landing page and product narrative

### Main application shell

- `/app` — command center / overview
- `/app/documents` — document library, ingestion, indexing status, and corpus operations
- `/app/workflows` — workflow catalog
- `/app/workflows/document-review` — document review workflow
- `/app/workflows/comparison` — policy / contract comparison workflow
- `/app/workflows/action-plan` — action plan / evidence review workflow
- `/app/workflows/candidate-review` — candidate review workflow
- `/app/deck-center` — executive artifact center
- `/app/history` — workflow run history

### AI Lab routes

- `/app/lab/chat` — chat with RAG
- `/app/lab/structured` — structured outputs
- `/app/lab/models` — model comparison
- `/app/lab/evidenceops` — EvidenceOps MCP surface

### System routes

- `/app/settings/runtime` — runtime controls
- `/app/settings/preferences` — preferences

This route map is one of the strongest assets in the repo because it turns the project into a clearly understandable product narrative.

---

## Technology stack

- **React 18**
- **TypeScript**
- **Vite**
- **React Router**
- **TanStack Query**
- **Tailwind CSS**
- **Radix UI / shadcn-style component stack**
- **Framer Motion**
- **Zustand**
- **Vitest**
- **Playwright** (dependency present for browser-oriented testing)

---

## Local development

### Requirements

- Node.js 18+
- npm 9+

### Run locally

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:8080` in your browser.

The Vite dev server is configured in `vite.config.ts`.

---

## Useful scripts

- `npm run dev` — start the development server
- `npm run build` — create a production build
- `npm run build:dev` — create a development-mode build
- `npm run preview` — preview the build locally
- `npm run test` — run tests with Vitest
- `npm run test:watch` — run Vitest in watch mode
- `npm run lint` — run ESLint

---

## How this frontend relates to the rest of the repository

This frontend is not a disconnected side project.

It sits on top of a repository that already contains substantial backend and platform foundations for:

- document RAG
- structured outputs
- document-agent workflows
- model comparison and evals
- EvidenceOps via MCP
- executive deck generation foundations

In other words:

- the **root repository** proves the engineering depth
- the **frontend** proves the product direction

That combination is exactly what makes the overall project much stronger.

---

## Honesty note for reviewers and recruiters

If you are reviewing this repository, the correct reading is:

- this frontend already defines the intended product UX and workflow architecture
- the platform underneath already contains many of the core service foundations
- the remaining work is largely about **wiring the product surface to the platform more completely**

That is a much stronger and more credible story than either:

- pretending everything is already fully integrated
- or hiding the frontend and underselling the actual product ambition
