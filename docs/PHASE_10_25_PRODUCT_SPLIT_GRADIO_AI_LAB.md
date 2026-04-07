# Phase 10.25 — official split between the product in Gradio and the AI Lab dashboard

## Objective

Formalize the next evolution of the project as a **surface split**:

- **Gradio** for the **product** surface
- **Streamlit** for the **AI Lab / engineering dashboard** surface

This decision exists to solve a positioning and UX problem:

- the product should no longer look like a generic lab
- the lab should not compete with the business narrative
- the interface needs to reflect the separation between **solving a real pain point** and **measuring/evolving the system**

---

## Official phase decision

### Ecosystem surfaces

The ecosystem should now be understood like this:

- **Main product** = interface in **Gradio**
- **AI Lab dashboard** = interface in **Streamlit**
- **shared services / domain backend** = common layer between the two surfaces

### Architectural rule

- **Gradio** shows business workflows
- **Streamlit** shows benchmark, evals, observability, model comparison, MCP/ops console, and advanced engineering surfaces
- the business logic must not be tied to either of these UIs

---

## Main product

### Official definition

> **Decision workflows grounded in documents**

This becomes the product's main definition.

### Main product subworkflows

The product in Gradio should launch with four primary workflows:

1. **Document Review**
2. **Policy / Contract Comparison**
3. **Action Plan / Evidence Review**
4. **Candidate Review**

### Transversal product capability

In addition to the four workflows, the product should treat **Executive Deck Generation** as a transversal capability.

This means:

- it is not a separate workflow competing with the main narrative
- it is an action/capability that can appear inside the main workflows

Examples:

- `Document Review` -> generate a document review deck
- `Policy / Contract Comparison` -> generate a comparison / decision deck
- `Action Plan / Evidence Review` -> generate an action plan deck or evidence pack deck
- `Candidate Review` -> generate a candidate review deck

---

## Where `cv_analysis` fits in this new interpretation

`cv_analysis` stops being treated as a main product surface.

Recommended reading:

- `cv_analysis` = **internal engine / foundational capability**
- `Candidate Review` = **business workflow exposed in the product**

In practice:

- the technical name `cv_analysis` may continue to exist internally
- the product interface should speak in terms of **Candidate Review**, not `cv_analysis`

### What `Candidate Review` should deliver

- profile summary
- strengths
- gaps
- relevant experience
- seniority / fit signals
- initial recommendation
- executive deck when appropriate

---

## What belongs in the AI Lab dashboard

The Streamlit dashboard should concentrate the engineering reading of the project, including:

- model comparison
- parsing / retrieval / embeddings / reranking benchmarks
- evals and diagnosis
- runtime economics
- routing / guardrails / workflow traces
- observability
- EvidenceOps MCP console and advanced operational surfaces
- controlled experimentation across providers and runtimes

### UX rule

The AI Lab must not be the product homepage.

It exists to:

- develop
- inspect
- validate
- compare
- audit

---

## Recommended decision for the Streamlit lab surface

## Official recommendation right now

**Adapt the current Streamlit app** so it becomes the first **AI Lab dashboard**.

### Why this is the strongest recommendation right now

- it reuses the surface that already concentrates controls, benchmarks, evals, and observability
- it avoids opening two reconstruction fronts at the same time
- it reduces transition cost while Gradio is born as the product surface
- it preserves the value of the current app as an engineering console

### What this means in practice

In the short term, the recommended direction is:

- **do not immediately create a brand-new Streamlit app from scratch**
- reorganize the current Streamlit app so it explicitly takes on the role of the **AI Lab dashboard**

## When to consider a separate new Streamlit app

A separate Streamlit app specifically for the lab should only be created if, after the initial refactor, at least one of these signs appears:

- the current app remains excessively mixed between product and lab
- navigation remains confusing even after repositioning
- state and component coupling starts to block Gradio evolution
- the cost of maintaining the current surface becomes higher than separating a new app

### Recommended decision gate

First:

1. adapt the current Streamlit app
2. validate the surface split
3. only then decide whether the lab deserves its own dedicated Streamlit app

---

## What the adapted Streamlit will become

## Official role

The adapted Streamlit becomes the ecosystem's **AI Lab dashboard**.

It should be understood as:

- an engineering console
- a benchmark/evals/observability surface
- an operational inspection environment
- a panel for advanced, experimental, or diagnostic workflows

### Target user of Streamlit

- you as the system builder
- a technical operator validating behavior, cost, routing, and quality
- a technical maintainer inspecting engineering depth

## Proposed navigation for the adapted Streamlit

### 1. Lab Overview

Objective:

- open the AI Lab with a summarized view of the current system state

Suggested content:

- overall runtime status
- recent benchmark/evals summary
- observability snapshot
- main operational alerts
- shortcuts for diagnosis and MCP

### 2. Benchmarks & Model Comparison

Objective:

- concentrate everything related to model, runtime, and strategy comparison

Suggested content:

- model comparison
- parsing/retrieval/embeddings/reranking benchmark
- aggregated benchmark reports
- comparison between providers and quantizations

### 3. Evals & Diagnosis

Objective:

- turn measurements into an operational reading of quality

Suggested content:

- eval suites
- history and trends
- diagnosis / persistent failures
- quality gates
- signals for pipeline adaptation or refactoring

### 4. Runtime & Observability

Objective:

- show latency, cost, routing, and traces

Suggested content:

- runtime economics
- budget-aware routing
- latency by flow
- workflow traces
- execution bottlenecks

### 5. Document Agent & Workflow Inspector

Objective:

- inspect the internal behavior of the document agent

Suggested content:

- intent routing
- tool selection
- guardrails
- needs review
- recent examples of workflow execution

### 6. EvidenceOps / MCP / Ops Console

Objective:

- concentrate the project's advanced operational surface

Suggested content:

- repository state
- actions/worklog
- MCP health
- MCP tools/resources
- local and external EvidenceOps operations

### 7. Structured / Advanced Experiments

Objective:

- keep technical playgrounds and experimental surfaces away from the main product showcase

Suggested content:

- extraction playground
- code analysis
- structured debugging
- OCR/VLM experiments
- shadow workflows and experimental comparisons

## What should leave the Streamlit homepage

For Streamlit to fully assume the AI Lab role, its home page should no longer look like the product homepage.

It should stop emphasizing:

- the main business-use CTA
- final-product language
- hero flows for `Document Review`, `Policy / Contract Comparison`, `Action Plan / Evidence Review`, and `Candidate Review`
- deck generation as the main end-user call to action

These elements should move to **Gradio**.

---

## What Gradio will become

## Official role

Gradio becomes the **main product surface**.

Recommended reading:

- AI-first experience
- clean interface for business workflows
- demonstrable surface for non-technical users

### Target user of Gradio

- business analyst
- document reviewer
- manager / decision-maker
- hiring manager

## Common product shell in Gradio

Regardless of the selected workflow, the base structure of the product should look similar:

1. **product home** with the 4 main workflows
2. **workflow selection**
3. **document input** (upload, corpus selection, or context selection)
4. **grounded preview** of the inputs
5. **findings / recommendation / action output**
6. **final actions** (download, export, deck, handoff)

## Main Gradio workflows

### 1. Document Review

Inputs:

- one or more documents

Expected outputs:

- grounded summary
- risks/gaps
- structured findings
- recommended actions
- optional document review deck

### 2. Policy / Contract Comparison

Inputs:

- two documents or two related versions

Expected outputs:

- relevant differences
- business impact
- watchouts
- recommendation
- optional comparison / decision deck

### 3. Action Plan / Evidence Review

Inputs:

- existing findings
- evidence packs
- operational documents

Expected outputs:

- owners
- tasks
- deadlines
- operational backlog
- optional action plan deck or evidence pack deck

### 4. Candidate Review

Inputs:

- candidate documents
- optional role profile / evaluation criteria

Expected outputs:

- candidate summary
- strengths
- gaps
- fit signals
- initial recommendation
- optional candidate review deck

### Important note about `cv_analysis`

In Gradio, the user does not interact with a task called `cv_analysis`.

The correct approach is:

- `cv_analysis` remains in the backend as an internal engine
- the product surface shows only **Candidate Review**

## What should not be front and center in Gradio

For Gradio to keep a product feel, it should not present the following as its main surface:

- benchmark matrix
- detailed model comparison
- advanced provider knobs
- OCR/VLM debug
- technical workflow traces
- operational MCP console
- shadow logs

### Controlled exception

Elements such as grounding, status, and warnings may appear, as long as they are presented in product language rather than looking like a technical console.

## Role of free-form chat after the split

Free-form chat with documents may continue to exist, but it should no longer be the product homepage.

Recommended reading:

- secondary assistive mode inside workflows
- or advanced utility preserved in the AI Lab

---

## Initial surface migration map

### Goes to the adapted Streamlit

- model comparison
- benchmark reports
- eval suites and diagnosis
- runtime economics
- workflow traces
- MCP / EvidenceOps console
- advanced structured/debug surfaces
- code analysis and adjacent technical experimentation

### Goes to Gradio

- Document Review
- Policy / Contract Comparison
- Action Plan / Evidence Review
- Candidate Review
- downloads and final workflow artifacts
- Executive Deck Generation as a transversal product action

### Remains in the shared backend

- document ingestion
- grounding / retrieval
- structured outputs
- document agent / orchestration
- `cv_analysis`
- presentation export service
- adapters / contracts / observability

---

## Recommended roadmap inside Phase 10.25

## Slice 10.25A — surface split and repositioning

Objective:

- officially separate product and lab
- define the role of the current Streamlit app
- prepare contracts and boundaries for Gradio

Suggested checklist:

- classify current screens/controls into **product** and **AI Lab**
- turn the current Streamlit app into the official baseline AI Lab dashboard
- remove from the main Streamlit narrative the flows that should move to the Gradio product
- extract shared services to avoid UI duplication
- formalize the contract of each business workflow

## Slice 10.25B — product in Gradio

Objective:

- create the first clear, AI-first product surface

Suggested checklist:

- build the product home around **Decision workflows grounded in documents**
- expose the four main workflows
- integrate Executive Deck Generation as a transversal capability
- promote `cv_analysis` to an internal engine behind `Candidate Review`
- preserve status feedback, grounding, and artifact downloads

## Slice 10.25C — HTTP backend and web app

Objective:

- definitively decouple UI, backend, and specialized services

Suggested checklist:

- define clear HTTP contracts between frontend and backend
- move deck-generation integrations into backend services
- prepare the evolution from Gradio to a web app
- keep the AI Lab as a parallel engineering surface

---

## Consolidated checklist of the change

- [x] map everything that appears today in the current app between **product** and **AI Lab**
- [x] define navigation and the home of the current Streamlit app as the engineering dashboard
- [x] decide what leaves the Streamlit home and moves to the Gradio product
- [x] formalize `Decision workflows grounded in documents` as the product headline
- [x] implement the 4 main workflows in Gradio
- [x] promote `cv_analysis` to the `Candidate Review` workflow
- [x] treat Executive Deck Generation as a transversal capability across workflows
- [x] decouple shared backend/services from the two surfaces
- [x] define the decision gate for whether the current Streamlit app is enough as AI Lab or whether a new app will be required

---

## Expected deliverables

- **AI Lab dashboard** in Streamlit, focused on engineering
- **product in Gradio**, focused on business workflows
- a clear boundary between product, lab, and the shared backend
- an explicit roadmap for the later evolution into a web app

---

## Design rationale to preserve

- why separating product and lab strengthens the repository structure
- why the product is organized around document-grounded decision workflows
- why `Candidate Review` is exposed at the product level while `cv_analysis` remains an internal engine
- why the current Streamlit app is reused first as the AI Lab dashboard
- why Gradio is the intermediate product surface

---

## Related documents

- `docs/PROJECT_POSITIONING_TWO_TRACKS.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_UI_EVOLUTION.md`
- `ROADMAP.md`