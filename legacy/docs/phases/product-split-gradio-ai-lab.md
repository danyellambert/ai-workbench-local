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

## Additional execution plan — make Streamlit the AI Engineering Operating Console

The current Streamlit surface already contains real engineering depth:

- benchmark and model comparison
- evals and diagnosis
- runtime economics and execution history
- workflow inspection and `needs_review`
- OCR / VLM / retrieval / embedding experimentation
- MCP / EvidenceOps operational surfaces

The next problem is no longer "do we have enough engineering content?".

The next problem is:

> how do we present this engineering depth in a way that looks like a serious AI engineering operating console rather than a collection of technical panels?

### Reading from the current AI Lab surface

#### What is already strong

- the surface already communicates **AI Lab**, not generic product UI
- observability, evals, workflow traces, MCP, and document intelligence are already present
- the project already has enough signals to look like a serious engineering system

#### What still needs to improve

- observability exists, but it does not yet dominate the surface as the system's main operating layer
- several tabs still feel too close to raw metrics/tables instead of **summary -> triage -> drilldown**
- the UI does not yet answer the daily operational questions of an AI engineer quickly enough
- the full engineering offering of the repository is present, but not yet condensed into one clear operating model

---

## The 5 questions the Streamlit AI Lab must answer

The Streamlit surface should be reorganized so that an AI engineer can answer these five questions in under a minute:

1. **Is the system healthy right now?**
2. **Where is quality regressing?**
3. **Where are latency and cost getting worse?**
4. **Which part of the pipeline is failing or degrading?**
5. **What engineering action should be taken next?**

If the AI Lab consistently answers those questions, it stops looking like a collection of tabs and starts looking like an engineering control plane.

---

## Capability map the Streamlit AI Lab must expose clearly

The Streamlit AI Lab should make the project's engineering capabilities legible as a single system:

### 1. System health and operational status

- vector/index health
- embedding compatibility
- MCP connectivity/readiness
- OCR / Docling / VLM health
- quality gate status
- budget/routing status

### 2. Runtime and observability

- latency anatomy
- bottleneck distribution
- budget-aware routing
- token/cost estimation
- execution reliability and failure patterns

### 3. Quality and evaluation discipline

- eval suites
- persistent failures
- recent regressions
- adaptation/refactor candidates
- quality gate interpretation

### 4. Document intelligence engineering

- ingestion/indexation state
- retrieval/reranking behavior
- OCR/Docling/VLM usage
- suspicious documents/pages
- reindex recommendations

### 5. Agent and workflow orchestration

- routing decisions
- guardrails
- retry behavior
- `needs_review`
- direct vs LangGraph comparison

### 6. Benchmark and decision support

- best provider/model by use case
- best latency/runtime bucket
- best quality/format adherence trade-off
- recommended defaults and alternatives

### 7. Experiment and artifact registry

- benchmark reports
- eval artifacts
- runtime logs
- phase evidence and technical documents

### 8. MCP / EvidenceOps / operational governance

- client health
- external-target readiness
- repository state
- open actions
- governance/update operations

---

## Cross-cutting UX rules for the AI Lab

The lab should follow these presentation rules across all tabs:

- **summary first, drilldown second**
- **alert-first reading** before raw data
- **decision-oriented language** instead of metric dumping
- **recent window vs previous window** whenever possible
- **clear system-health badges** for important subsystems
- **operational recommendations** in every major area
- **artifact traceability** between UI panels and versioned repository evidence
- **PT/EN consistency** so the surface feels intentionally designed instead of gradually accumulated

---

## Layered execution priorities for the next 10.25 iteration

### Priority 0 — shell and narrative reframing

Goal:

- make the whole Streamlit feel like an **AI engineering operating console**

Checklist:

- turn the current home into a real command center
- ensure every major tab starts with a short operational reading
- reduce the feeling of technical fragmentation across tabs
- standardize terminology and mental model across the shell

### Priority 1 — observability and reliability as the dominant layer

Goal:

- make the project's engineering maturity immediately visible through health, latency, reliability, and budget signals

Checklist:

- consolidate health, latency, budget, and incident signals
- add recent-vs-previous comparisons where possible
- expose simple comfort zones / quality-floor logic
- make bottleneck analysis more operational and less purely descriptive

### Priority 2 — evals as regression control, not only historical storage

Goal:

- turn evals into a day-to-day decision surface for engineering iteration

Checklist:

- rank regressions by severity
- show what changed between recent windows
- make next engineering action explicit by task/suite
- surface task-level quality gates more prominently

### Priority 3 — runtime + document intelligence as one coherent subsystem

Goal:

- present ingestion, retrieval, embeddings, OCR/VLM, and corpus health as one document-intelligence layer

Checklist:

- create a corpus/index health view
- add document-level operational badges
- highlight anomalies, suspicious pages, and reindex recommendations
- improve retrieval diagnostics beyond raw parameter display

### Priority 4 — workflow / guardrails / agent operations

Goal:

- make the internal behavior of the document agent and workflow system inspectable in operational terms

Checklist:

- summarize route decisions, guardrails, retries, and `needs_review`
- show which parts of the workflow are adding safety vs only adding latency
- prioritize actionable examples for human inspection

### Priority 5 — benchmark as a decision system

Goal:

- make benchmark outputs directly useful for runtime/model decisions by use case

Checklist:

- show recommended default by use case
- expose best alternative by latency/cost/stability
- move raw candidate dumps further down into drilldowns
- add decision memo language around benchmark results

### Priority 6 — artifacts and experiment registry

Goal:

- make reports and artifacts feel like a navigable engineering evidence registry

Checklist:

- strengthen top-level artifact summaries
- organize by operational category, not only by file group
- connect reports back to the tabs they explain

### Priority 7 — MCP / EvidenceOps operations and governance

Goal:

- evolve MCP from functional console to operational governance surface

Checklist:

- separate health snapshot, client operations, external readiness, and governance actions more clearly
- elevate latest state / latest error / last successful action
- improve product-language consistency for the ops surface

---

## Suggested additional slices inside Phase 10.25

### Slice 10.25I — AI Lab Command Center and system health

Objective:

- turn the home into the main command center of the engineering surface

Checklist:

- add a global health bar for index, evals, MCP, OCR/VLM, and budget routing
- add an operational alerts block
- add triage cards for quality, latency, cost, workflow, document intelligence, and ops
- add recommended next actions with links into drilldown tabs

### Slice 10.25J — Observability & reliability control plane

Objective:

- make observability the dominant reading of the AI Lab

Checklist:

- consolidate latency, reliability, and budget signals
- add recent-vs-previous operational comparisons
- add comfort-zone / warning-zone interpretation for key metrics
- add an incident-style execution table for problematic recent runs

### Slice 10.25K — Quality, evals, and regression control

Objective:

- turn evals into an operational quality control system

Checklist:

- add a quality gate summary at the top of the tab
- rank regressions and persistent failures more explicitly
- highlight candidate engineering actions by task/suite
- show what changed in the recent window

### Slice 10.25L — Runtime, retrieval, and document intelligence

Objective:

- unify index health, retrieval behavior, and document-processing signals

Checklist:

- add corpus/index health summary
- add document-level status badges (`OCR used`, `Docling`, `VL`, `suspicious`, `reindex recommended`)
- improve retrieval diagnostics and context-pressure visibility
- make OCR/VLM anomalies easier to inspect operationally

### Slice 10.25M — Workflow, guardrails, and agent inspection

Objective:

- expose the internal reasoning of workflow orchestration in operator terms

Checklist:

- summarize routing and guardrail behavior in a workflow-health block
- show the dominant reasons for `needs_review`
- compare direct vs LangGraph more explicitly as an engineering decision
- prioritize recent problematic examples for human inspection

### Slice 10.25N — Benchmark decisions and experiment registry

Objective:

- make model comparison and experiment history drive technical decisions more directly

Checklist:

- show recommended default model/provider by use case
- show alternatives by cost/latency/stability
- add decision-memo language above raw benchmark tables
- strengthen the artifact explorer as an engineering evidence registry

### Slice 10.25O — MCP / EvidenceOps operational governance

Objective:

- elevate MCP from functional panel to governance/ops console

Checklist:

- separate health snapshot, client operations, external targets, and governance actions clearly
- expose latest successful operation and latest failure more explicitly
- improve the operational readability of external readiness
- align language and hierarchy with the rest of the AI Lab shell

---

## Definition of done for the Streamlit AI Lab at this stage

The Streamlit AI Lab should be considered well-positioned for this stage when:

- the home behaves like a genuine engineering command center
- observability is immediately visible as a first-class layer
- every major tab answers a specific operational question
- benchmark, evals, runtime, workflow, artifacts, and MCP read as one coherent system
- the repository's engineering depth is legible without requiring a technical deep dive into the code first

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
- `docs/architecture/executive-deck-generation/product-capability.md`
- `docs/architecture/executive-deck-generation/ui-evolution.md`
- `ROADMAP.md`