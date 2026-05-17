# Product Evolution

This document records how the active Axiovance product surface evolved into the current React/Vite application backed by the Product API, mounted runtime state, delivery integrations, and AI Lab controls.

## Current Product Boundary

The active product is the React/Vite frontend served by Nginx, the Product API in `main_product_api.py`, the PPT Creator sidecar, Nextcloud, Ollama, and mounted runtime data. Historical Streamlit, Gradio, Oracle-specific, and heavy dependency paths remain under `legacy/` or reference documentation and are not the active product contract.

The user-facing product now centers on these surfaces:

- Command Center and Document Library for navigation and source document selection.
- Workflow pages for Document Review, Policy Comparison, Action Plan, Candidate Review, and Deck Generation.
- Run History and artifact surfaces for reviewing what ran and what was produced.
- AI Lab pages for runtime observability, workflow inspection, benchmarks, evals, diagnostics, experiments, and MCP Operations.
- Runtime Controls and Preferences for provider/model behavior, credentials, and session/admin boundaries.

## Evolution Threads

### Product Surface And Identity

The repository moved from a mixed experimentation surface to a current product identity with a coherent public entry point. The README, Keystone header, current architecture overview, workflow screenshots, favicon variants, Open Graph image, robots file, sitemap, and product tagline now describe the active application rather than earlier demos.

The public name Axiovance is used where the deployed product and web metadata need a product name. AI Decision Studio remains useful for repository, architecture, and engineering context because it describes the system as a decision-workflow studio.

Primary evidence:

- `README.md`
- `frontend/index.html`
- `frontend/public/favicon.svg`
- `frontend/public/robots.txt`
- `frontend/public/sitemap.xml`
- `docs/assets/product/readme-header.svg`
- `docs/assets/product/architecture-overview.svg`
- `docs/assets/product/document-review.png`
- `docs/assets/product/policy-comparison.png`
- `docs/assets/product/action-plan.png`
- `docs/assets/product/candidate-review.png`
- `docs/assets/product/delivery-layer.png`
- `docs/assets/product/ai-lab-runtime.webp`

### Workflow Productization

The current workflow surface grew from document-grounded experimentation into five product workflows:

- Document Review turns selected evidence into reviewable findings.
- Policy Comparison compares two documents and surfaces grounded deltas.
- Action Plan converts review evidence into accountable work items.
- Candidate Review applies document-grounded assessment to candidate material.
- Deck Generation turns workflow contracts into presentation artifacts.

Later work made these workflows behave like product operations rather than one-shot scripts. Long-running workflow calls use async polling and timeout recovery, export states are visible, and publish actions are reviewed through product previews before external delivery.

Primary evidence:

- `frontend/src/pages/DocumentReviewPage.tsx`
- `frontend/src/pages/ComparisonPage.tsx`
- `frontend/src/pages/ActionPlanPage.tsx`
- `frontend/src/pages/CandidateReviewPage.tsx`
- `frontend/src/pages/DeckCenterPage.tsx`
- `frontend/src/components/product/WorkflowPublishActions.tsx`
- `frontend/src/lib/workflow-timeout-recovery.ts`
- `src/product/service.py`
- `src/product/presenters.py`
- `src/product/action_plan_presenter.py`
- `src/product/candidate_review_presenter.py`

### Product API And Runtime State

The Product API became the stable boundary between the frontend and mutable product state. The frontend calls API endpoints, and the backend owns workflow execution, provider selection, mounted data roots, integrations, artifacts, access control, telemetry, and runtime behavior.

The mounted runtime contract separates:

- `/app/baseline` for read-only functional baseline material.
- `/app/runtime` for logs, cache, RAG state, preferences, telemetry, and runtime state.
- `/app/artifacts` for decks, exports, previews, and generated outputs.
- `/app/users` for public session overlays and admin state.

This separation lets the container images stay rebuildable while runtime data stays external and inspectable.

Primary evidence:

- `main_product_api.py`
- `src/product/api.py`
- `src/product/access_control.py`
- `src/storage/runtime_paths.py`
- `src/storage/product_workflow_history.py`
- `docs/architecture/current-product-surface.md`
- `docs/architecture/COMPLETE_ARCHITECTURE_BRIEF.md`

### Delivery Layer

Delivery moved from simple output files to integrated handoff paths:

- Nextcloud/WebDAV provides the document repository and import/sync root.
- Trello preview and publish convert workflow results into operational cards.
- Notion preview and publish convert workflow results into memo/register pages.
- PPT Creator receives deck contracts and produces PPTX files, previews, and export metadata.

All delivery paths are optional and credential-gated. A workflow can be reviewed locally without publishing externally. Admin credentials unlock publish actions.

Primary evidence:

- `src/product/integration_hub.py`
- `frontend/src/components/product/WorkflowPublishActions.tsx`
- `services/ppt_creator_app/ppt_creator/api.py`
- `docs/architecture/evidenceops/integration-trajectory.md`

### Public And Admin Operation

The product now distinguishes public demo behavior from admin behavior:

- public visitors get isolated behavior and limited execution paths;
- public workflow execution is quota-controlled;
- public deck generation is rate-limited;
- overlapping public workflow execution is blocked by an in-flight gate;
- admin mode retains global runtime controls, credentials, publish actions, and private analytics.

This made the product safer to run in a shared environment while preserving the full engineering surface for private operation.

Primary evidence:

- `src/product/public_execution_quota.py`
- `src/product/public_execution_gate.py`
- `src/product/deck_rate_limit.py`
- `src/storage/product_usage_events.py`
- `frontend/src/components/usage/UsageTelemetryProvider.tsx`
- `frontend/src/pages/AdminUsagePage.tsx`
- `docs/operations/engineering-controls.md`
- `docs/ops/PUBLIC_EXECUTION_QUOTA.md`
- `docs/ops/PUBLIC_EXECUTION_GATE.md`
- `docs/ops/PUBLIC_DECK_RATE_LIMIT.md`

## Non-Adjacent Evolution Lines

Several capabilities were not built in a single continuous commit sequence. They reappear across the history as the product matured:

- RAG and document grounding started as an experimentation foundation, then became workflow context, grounding previews, and retrieval-backed product outputs.
- Structured output work started in extraction/eval experiments, then later shaped product presenters, workflow payloads, and delivery contracts.
- External delivery began as EvidenceOps/MCP concepts, then became Nextcloud, Trello, Notion, and PPT Creator product integrations.
- Deployment began as local and Oracle-like experimentation, then converged on local Docker and AWS with the same five-service contract.
- AI Lab started as an engineering surface and later gained provider controls, diagnostics, benchmarks, evals, telemetry, private analytics, and runtime observability.

## Current Status

The product is now a document-grounded decision workflow application with:

- one current React/Vite product surface;
- one Product API boundary;
- five Docker services in the active deployment contract;
- mounted runtime state instead of mutable container images;
- optional external delivery integrations;
- AI Lab observability and evaluation surfaces;
- documented local and AWS deployment paths.
