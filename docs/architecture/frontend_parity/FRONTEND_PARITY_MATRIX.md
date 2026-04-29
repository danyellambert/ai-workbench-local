# Frontend Parity Matrix

This matrix defines what must be validated before claiming Docker frontend parity with the local frontend.

Parity means the Docker frontend is not only rendering routes, but also showing real data and supporting the same user-visible actions as the local frontend.

## Scope

Compare:

- Local frontend: `http://127.0.0.1:8080`
- Local backend: `http://127.0.0.1:8011`
- Docker frontend: `http://127.0.0.1:8059`
- Docker backend: `http://127.0.0.1:8013`

## Validation phases

| Phase | Purpose | Status |
|---|---|---|
| 1 | Inventory all routes, links, pages, API calls and actions | Passed |
| 2 | Compare local vs Docker API surfaces | Passed |
| 3 | Compare local vs Docker UI route rendering | Passed |
| 4 | Validate actions per tab | Pending |
| 5 | Create one full parity script | Pending |

## Product tabs

| Area | Route | Data that must appear | Actions that must work | Current coverage |
|---|---|---|---|---|
| Command Center | `/app` | workflow summary, document/runs/artifacts overview, dashboard cards | navigate to workflows, documents, deck center, history | route render only |
| Document Library | `/app/documents` | 17 indexed documents, names, statuses, chunk counts | open/select document, confirm details/evidence preview if exposed | route render + API parity |
| Workflow Catalog | `/app/workflows` | 4 workflows | open each workflow card | route render + API parity |
| Document Review | `/app/workflows/document-review` | indexed document options, grounding preview, run surface | Run Review, render result, create run, no blank page | backend write + UI run passed |
| Policy Comparison | `/app/workflows/comparison` | v3.1 and v3.2 policy documents, comparison options | Run Comparison, render result, create run, no blank page | backend write + UI run passed |
| Action Plan | `/app/workflows/action-plan` | relevant remediation/vendor documents, run controls | Run workflow, render result, create run | pending |
| Candidate Review | `/app/workflows/candidate-review` | CV and role brief documents, run controls | Run workflow, render result, create run | pending |
| Deck Center | `/app/deck-center` | artifact/deck list, preview metadata, asset counts | open artifact detail, open/download referenced assets if exposed | route render only |
| Run History | `/app/history` | latest runs, workflow labels, statuses, artifacts | open run detail, verify latest Docker-created runs visible | route render only |
| Run Surface Alias | `/app/run` | should redirect or render valid run surface | route should not blank or 404 | pending explicit parity |
| Lab Structured Alias | `/app/lab/structured` | should redirect to workflow inspector | redirect should work | pending explicit parity |
| Lab Models Alias | `/app/lab/models` | should redirect to benchmarks | redirect should work | pending explicit parity |

## AI Lab tabs

| Area | Route | Data that must appear | Actions that must work | Current coverage |
|---|---|---|---|---|
| AI Lab Overview | `/app/lab/overview` | KPIs, alerts, workflow mix, runtime status | navigation/filter cards if exposed | route render + API parity |
| Runtime Observability | `/app/lab/runtime` | latency, provider, retrieval, diagnostics, traces | expand/filter details if exposed | route render + API parity |
| Chat | `/app/lab/chat` | chat surface, provider/runtime state | send safe message or validate disabled/degraded state clearly | route render only |
| Workflow Inspector | `/app/lab/workflow-inspector` | task options, latest runs, task details, document options | select task/document, inspect result | route render + API parity |
| Benchmarks | `/app/lab/benchmarks` | models, presets, leaderboard, source breakdown | select preset/model details if exposed | route render + API parity |
| Evals Diagnosis | `/app/lab/evals` | cases, totals, pass rates, watchlists, breakdowns | filter/select cases if exposed | route render + API parity |
| Lab Artifacts | `/app/lab/artifacts` | 80 artifacts, recent captures, artifact statuses | open artifact/detail/preview if exposed | route render + API parity |
| EvidenceOps | `/app/lab/evidenceops` | 72 actions, repository/worklog evidence | open action/detail or validate evidence panel | route render + API parity |

## Settings tabs

| Area | Route | Data that must appear | Actions that must work | Current coverage |
|---|---|---|---|---|
| Runtime Controls | `/app/settings/runtime` | active profile, available connections, runtime options | safe read-only controls, profile display, no broken test action | route render + API parity |
| Preferences | `/app/settings/preferences` | active profile, provider connections, options, credential policy | switch/read profile, test connection behavior safe, no secrets displayed | route render + API parity |

## Required automated checks

### Phase 3 UI parity

For every route above:

- local route returns status below 500
- Docker route returns status below 500
- local and Docker pages are non-blank
- no React page errors
- no severe console errors
- no failed API requests
- visible text length is comparable
- redirects land on equivalent destinations
- screenshots are captured for manual review

### Phase 4 action parity

For every tab above:

- identify clickable buttons, tabs, cards, dropdowns, links and inputs
- click or interact with every safe action
- validate result is visible
- validate no blank page
- validate no severe console/page error
- validate API response is not failing
- for write actions, validate persistence in run history/artifacts/preferences only when expected

## Current known passing evidence

- Docker public demo smoke passes.
- Docker backend and frontend become healthy.
- Docker Golden Surface captures 15 endpoints with no errors.
- Docker Document Review workflow write smoke passes.
- Docker Policy Comparison workflow write smoke passes.
- Docker frontend UI smoke for Document Review and Policy Comparison passes.
- Docker route-only audit passed for 20 routes.
- Local vs Docker API parity passed for the Golden Surface endpoints.
- Local vs Docker UI route parity passed for 23 routes with no failed routes.

## Not yet proven

The following are not yet fully proven:

- Action Plan workflow through Docker frontend.
- Candidate Review workflow through Docker frontend.
- Document Library document detail/open behavior.
- Deck Center artifact detail/open/download behavior.
- Run History detail behavior.
- AI Lab artifacts detail behavior.
- EvidenceOps action/detail behavior.
- Runtime Controls user actions.
- Preferences user actions.
- Chat tab behavior.
- Full local vs Docker UI parity for all routes. Passed for 23 routes in Phase 3 route rendering parity.
- Full local vs Docker action parity for every tab.
