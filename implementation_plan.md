# Implementation Plan

[Overview]
Adapt the Python product and AI Lab capabilities already present in the repository into the React frontend in `frontend/` by extending the existing product API into a typed backend-for-frontend layer and replacing all page-level mocks with live integrations.

The repository already contains most of the business and engineering logic needed for the target experience, but that logic is split across three different surfaces: a Gradio product app (`main_gradio.py` and `src/gradio_ui/`), a monolithic Streamlit AI Lab (`main.py`), and a lightweight HTTP product API (`main_product_api.py` and `src/product/api.py`). In parallel, the React frontend in `frontend/` already expresses the intended information architecture for both product and AI Lab, but nearly every page still reads from `frontend/src/lib/mock-data.ts` instead of calling real backend contracts.

The implementation should therefore avoid rewriting domain logic and instead standardize how the frontend reaches existing services. The strongest path is to keep `main_product_api.py` as the single web-facing backend entrypoint, expand it with typed endpoints for product workflows and AI Lab features, and extract any logic that still lives only inside `main.py` into reusable service functions before exposing it over HTTP. This keeps the Python side as the source of truth for workflow execution, grounding, deck export, structured outputs, model comparison, runtime observability, and EvidenceOps.

On the frontend side, the React application should remain the main product shell and AI Lab shell. The work is mostly about replacing mocked collections with a typed API client, query hooks, shared runtime preference state, real loading/error/empty states, and page-specific view-model adapters. The current route map is already a good fit for the product-plus-lab scope the user confirmed, so the primary goal is integration depth rather than a wholesale route redesign.

The implementation also needs a durable persistence layer for workflow history and artifact indexing so that `OverviewPage`, `RunHistoryPage`, and `DeckCenterPage` stop depending on fabricated data. Existing runtime path helpers already expose `get_product_workflow_history_path()` and the repo already stores logs for model comparison, runtime execution, evals, and EvidenceOps, so the plan should reuse those storage conventions instead of inventing a parallel persistence layout.

[Types]
The implementation introduces shared Python and TypeScript API contracts for product workflows, AI Lab execution requests, runtime options, history, artifacts, and EvidenceOps summaries.

Detailed contract changes:

- Extend `ProductDocumentRef` in `src/product/models.py` so the document library can render real operational status rather than a reduced catalog entry.
  - Existing fields kept: `document_id`, `name`, `file_type`, `char_count`, `chunk_count`, `indexed_at`, `loader_strategy_label`.
  - New fields: `status: Literal["indexed", "indexing", "error", "pending"]`, `size_bytes: int | None`, `warnings: list[str]`, `source_type: str | None`, `pdf_extraction_mode: str | None`, `ocr_backend: str | None`.
  - Validation rules: `document_id` must be non-empty; `status` must be one of the four allowed UI states; counts are non-negative integers; warning text is trimmed and deduplicated.

- Add `ProductWorkflowHistoryEntry` in `src/product/models.py` to persist and return product run history.
  - Fields: `run_id`, `workflow_id`, `workflow_label`, `status`, `created_at`, `duration_s`, `document_ids`, `document_names`, `input_text`, `summary`, `recommendation`, `provider`, `model`, `context_strategy`, `deck_export_kind`, `warnings`, `artifact_records`.
  - Relationships: generated from `ProductWorkflowRequest` + `ProductWorkflowResult`; drives `OverviewPage`, `RunHistoryPage`, and `DeckCenterPage`.

- Add `ProductArtifactRecord` in `src/product/models.py` so exported assets can be listed independently of the workflow result that created them.
  - Fields: `artifact_id`, `artifact_type`, `label`, `path`, `download_name`, `available`, `workflow_id`, `workflow_label`, `created_at`, `run_id`.
  - Validation rules: `artifact_type` must align with existing export kinds (`pptx`, `contract_json`, `payload_json`, `review_json`, `preview_manifest_json`, `thumbnail_sheet`); `path` is optional in payloads but required when `available=True`.

- Add `ProductRuntimeOptions` and supporting nested models to describe all selectable runtime controls shown in `SettingsPage` and `RuntimeDrawer`.
  - Provider option fields: `provider`, `label`, `supports_chat`, `supports_embeddings`, `default_model`, `available_models`, `default_context_window`.
  - Retrieval option fields: `embedding_provider`, `embedding_model`, `top_k_default`, `retrieval_strategies`, `chunk_size_default`, `chunk_overlap_default`, `rerank_pool_default`, `rerank_lexical_weight_default`.
  - Document processing fields: `pdf_extraction_modes`, `ocr_backends`, `vl_enabled_default`, `default_vl_model`.
  - Validation rules: selected models must exist in the provider-specific inventory; manual `context_window` values are rejected below the existing backend floor and clamped to provider caps.

- Add chat contracts in `src/product/models.py`.
  - `ProductChatMessage`: `id`, `role`, `content`, `timestamp`, `sources`, `metadata`.
  - `ProductChatRequest`: `message`, `document_ids`, `provider`, `model`, `temperature`, `context_window_mode`, `context_window`, `retrieval_strategy`, `top_k`, `history`.
  - `ProductChatResponse`: `reply`, `history`, `selected_documents`, `usage`, `runtime_snapshot`.
  - Validation rules: `message` must be non-empty; `history` is optional and trimmed to the backend-supported recent-turn window; `document_ids` must correspond to indexed documents when provided.

- Add structured-output contracts in `src/product/models.py`.
  - `ProductStructuredTaskDescriptor`: `task_type`, `label`, `description`, `primary_render_mode`, `default_model`.
  - `ProductStructuredTaskRequest`: `task_type`, `input_text`, `document_ids`, `provider`, `model`, `temperature`, `context_strategy`, `context_window_mode`, `context_window`, `use_document_context`.
  - `ProductStructuredTaskResponse`: `task_type`, `structured_result`, `display_sections`, `runtime_metadata`.
  - Relationships: `structured_result` wraps the existing `StructuredResult`; `display_sections` is a frontend-friendly projection derived from the validated payload.

- Add model-comparison contracts in `src/product/models.py`.
  - `ProductModelComparisonCandidate`: `provider`, `model`.
  - `ProductModelComparisonRequest`: `candidates`, `prompt_profile`, `prompt_text`, `benchmark_use_case`, `response_format`, `temperature`, `context_window`, `document_ids`, `top_k`, `top_p`, `max_tokens`, `think`.
  - `ProductModelComparisonResponse`: `results`, `ranking`, `history_summary`, `latest_log_entry`.
  - Validation rules: candidate list size must be between 1 and 5 for a single UI run; `(provider, model)` pairs must be unique; `response_format` must remain compatible with the selected benchmark preset.

- Add overview/runtime/EvidenceOps summary contracts in `src/product/models.py`.
  - `ProductOverviewSnapshot`: `system_stats`, `workflow_catalog`, `recent_runs`, `recent_artifacts`, `documents_summary`, `lab_summary`.
  - `ProductEvidenceOpsConsoleResponse`: `tool_catalog`, `repository_summary`, `worklog_summary`, `action_summary`, `search_results`, `mcp_telemetry`, `drift_summary`.
  - `ProductEvidenceOpsRegisterRequest` and `ProductEvidenceOpsActionUpdateRequest`: explicit request bodies for MCP-backed write operations.

- Mirror all of the above into `frontend/src/lib/api/types.ts`.
  - React components should no longer depend on the ad hoc shapes in `mock-data.ts`.
  - Frontend view-model adapters may still derive small UI helpers (status labels, chart series, grouped cards), but the transport layer should remain structurally aligned with the Python contracts.

[Files]
The implementation adds a small backend-for-frontend service layer, a workflow-history storage module, and a typed frontend API layer while updating every mock-backed page in the React app.

Detailed breakdown:

- New files to be created:
  - `src/storage/product_workflow_history.py` — load/append/summarize helpers for workflow history and artifact flattening.
  - `src/services/chat_runtime.py` — reusable chat-with-RAG orchestration extracted from `main.py` so Streamlit and the product API share one execution path.
  - `src/product/ai_lab_service.py` — frontend-oriented orchestration for chat, structured outputs, model comparison, overview snapshots, runtime options, and EvidenceOps responses.
  - `frontend/src/lib/api/types.ts` — TypeScript contract mirror for Python API payloads.
  - `frontend/src/lib/api/client.ts` — low-level `fetch` client with JSON parsing, upload handling, error normalization, and base-URL resolution.
  - `frontend/src/lib/api/queryKeys.ts` — canonical TanStack Query keys for product and AI Lab resources.
  - `frontend/src/lib/api/hooks.ts` — query and mutation hooks shared across pages.
  - `frontend/src/components/shared/LoadingErrorState.tsx` — reusable loading/error/empty-state renderer for pages and panels.
  - `frontend/src/components/shared/ArtifactDownloads.tsx` — shared artifact list/download renderer used by workflow pages and `DeckCenterPage`.
  - `frontend/src/components/workflows/WorkflowRunnerForm.tsx` — shared form logic for workflow detail pages.
  - `frontend/src/components/lab/StructuredResultPanel.tsx` — UI renderer for structured-output results in the web app.
  - `frontend/src/components/lab/RuntimeSummaryCards.tsx` — reusable lab/observability cards used by `OverviewPage`, `ModelComparisonPage`, `EvidenceOpsPage`, and `SettingsPage`.
  - `frontend/.env.example` — frontend-specific environment variables such as `VITE_PRODUCT_API_BASE_URL`.
  - `implementation_task_draft.md` — manual fallback task prompt because the current tool environment does not expose a `new_task` tool.

- Existing files to be modified:
  - `src/product/models.py` — extend product contracts and add new API request/response models.
  - `src/product/service.py` — enrich document metadata, optionally persist run/deck history, and expose artifact-friendly outputs.
  - `src/product/api.py` — add new GET/POST routes, multipart upload parsing, history/artifact endpoints, AI Lab endpoints, and consistent error handling.
  - `src/app/product_bootstrap.py` — attach resolved runtime/log/artifact paths and any extra service dependencies needed by the expanded API.
  - `main.py` — replace Streamlit-only chat orchestration with calls into `src/services/chat_runtime.py` so web and Streamlit behavior stay aligned.
  - `frontend/vite.config.ts` — add proxy/base-URL behavior for `/api` and `/health` during local development.
  - `frontend/README.md` — update integration status and local run instructions.
  - `frontend/src/App.tsx` — optionally add any missing routes needed to surface data already represented in the frontend shell.
  - `frontend/src/lib/store.ts` — expand Zustand state to hold runtime preferences, API availability flags, and cross-page UI selections that should survive navigation.
  - `frontend/src/components/layout/AppSidebar.tsx` — adjust labels/navigation only if route additions are required for missing AI Lab surfaces.
  - `frontend/src/components/layout/RuntimeDrawer.tsx` — hydrate controls from live runtime options instead of hardcoded values.
  - `frontend/src/pages/OverviewPage.tsx` — swap mock metrics/runs/artifacts for real overview and lab-summary queries.
  - `frontend/src/pages/DocumentsPage.tsx` — integrate live documents, upload/indexing, and real corpus stats.
  - `frontend/src/pages/WorkflowCatalogPage.tsx` — render the workflow catalog and deck metadata from the backend contract.
  - `frontend/src/pages/DocumentReviewPage.tsx` — run workflow, fetch grounding preview, show real findings/evidence/artifacts.
  - `frontend/src/pages/ComparisonPage.tsx` — run comparison workflow and render comparison findings from live results.
  - `frontend/src/pages/ActionPlanPage.tsx` — render extracted action items, statuses, and evidence gaps from workflow output.
  - `frontend/src/pages/CandidateReviewPage.tsx` — render live CV analysis sections and exported artifacts.
  - `frontend/src/pages/DeckCenterPage.tsx` — render persisted artifact history rather than static exports.
  - `frontend/src/pages/RunHistoryPage.tsx` — render stored product workflow history.
  - `frontend/src/pages/ChatPage.tsx` — execute real chat turns, persist/reload history, and render citations/usage metadata.
  - `frontend/src/pages/StructuredOutputsPage.tsx` — pull task registry from backend and execute real structured tasks.
  - `frontend/src/pages/ModelComparisonPage.tsx` — execute real comparison candidates and display ranking/history summaries.
  - `frontend/src/pages/EvidenceOpsPage.tsx` — render MCP tools, repository drift, search results, and write operations from the backend.
  - `frontend/src/pages/SettingsPage.tsx` — bind controls to the runtime options contract and shared runtime preferences.
  - `frontend/src/test/example.test.ts` — replace the placeholder test with real API-backed component coverage.
  - `tests/test_product_api_unittest.py` — extend API coverage to the new endpoints.
  - `tests/test_product_service_unittest.py` — cover run/deck persistence and enriched product contracts.
  - `tests/test_product_workflows_front_integration_unittest.py` and `tests/test_candidate_review_front_integration_unittest.py` — keep workflow front-door coverage valid after history/artifact changes.

- Files to be deleted or moved:
  - `frontend/src/lib/mock-data.ts` — delete once the last page import is removed, to eliminate drift between mock shapes and backend contracts.
  - No file moves are required; the plan should favor additive integration over folder churn.

- Configuration file updates:
  - `.env.example` — document `PRODUCT_API_SERVER_NAME`, `PRODUCT_API_SERVER_PORT`, `PRODUCT_API_ALLOW_CORS`, `APP_RUNTIME_ROOT`, and `APP_ARTIFACT_ROOT` if they are not already described clearly enough.
  - `frontend/.env.example` — add `VITE_PRODUCT_API_BASE_URL=http://127.0.0.1:8011` for non-proxied environments.
  - `frontend/vite.config.ts` — proxy `/api` and `/health` to the product API during local development to simplify CORS and deployment parity.

[Functions]
Implementation centers on new backend orchestration functions and frontend data hooks that replace mock imports with typed API calls and shared execution paths.

Detailed breakdown:

- New functions:
  - `load_product_workflow_history(path: Path) -> list[dict[str, object]]` in `src/storage/product_workflow_history.py` — read persisted product workflow history.
  - `append_product_workflow_history_entry(path: Path, entry: dict[str, object]) -> list[dict[str, object]]` in `src/storage/product_workflow_history.py` — persist a normalized run entry.
  - `summarize_product_workflow_history(entries: list[dict[str, object]]) -> dict[str, object]` in `src/storage/product_workflow_history.py` — produce counts/recents for `OverviewPage` and `RunHistoryPage`.
  - `list_recent_product_artifacts(entries: list[dict[str, object]], *, limit: int = 20) -> list[dict[str, object]]` in `src/storage/product_workflow_history.py` — flatten artifact history for `DeckCenterPage`.
  - `run_chat_turn(bootstrap: ProductBootstrap, request: ProductChatRequest) -> ProductChatResponse` in `src/services/chat_runtime.py` — execute a chat turn with retrieval, usage capture, citations, and history persistence.
  - `build_runtime_options_contract(bootstrap: ProductBootstrap) -> ProductRuntimeOptions` in `src/product/ai_lab_service.py` — expose selectable providers/models/defaults to the frontend.
  - `build_overview_snapshot(bootstrap: ProductBootstrap) -> ProductOverviewSnapshot` in `src/product/ai_lab_service.py` — aggregate product stats, recent runs/artifacts, and AI Lab summaries.
  - `build_structured_task_contract(bootstrap: ProductBootstrap) -> dict[str, Any]` in `src/product/ai_lab_service.py` — serialize the structured task registry for the frontend.
  - `run_structured_task_for_frontend(bootstrap: ProductBootstrap, request: ProductStructuredTaskRequest) -> ProductStructuredTaskResponse` in `src/product/ai_lab_service.py` — execute a structured task and add display-friendly sections.
  - `run_model_comparison_for_frontend(bootstrap: ProductBootstrap, request: ProductModelComparisonRequest) -> ProductModelComparisonResponse` in `src/product/ai_lab_service.py` — execute one web comparison run and return ranking + persisted-summary data.
  - `build_evidenceops_console_payload(bootstrap: ProductBootstrap, *, query: str | None = None, limit: int = 25) -> ProductEvidenceOpsConsoleResponse` in `src/product/ai_lab_service.py` — aggregate repository, action, worklog, MCP telemetry, and optional search results.
  - `register_evidenceops_entry_for_frontend(bootstrap: ProductBootstrap, request: ProductEvidenceOpsRegisterRequest) -> dict[str, Any]` in `src/product/ai_lab_service.py` — wrap MCP-backed register actions.
  - `update_evidenceops_action_for_frontend(bootstrap: ProductBootstrap, request: ProductEvidenceOpsActionUpdateRequest) -> dict[str, Any]` in `src/product/ai_lab_service.py` — wrap local/MCP-backed action updates.
  - `getOverview()`, `getWorkflowCatalog()`, `listDocuments()`, `uploadDocuments(formData: FormData)`, `getGroundingPreview(params)`, `runWorkflow(payload)`, `generateDeck(payload)`, `getRunHistory()`, `getArtifacts()`, `getRuntimeOptions()`, `sendChatTurn(payload)`, `getStructuredTaskContract()`, `runStructuredTask(payload)`, `runModelComparison(payload)`, `getEvidenceOpsSummary(params)` in `frontend/src/lib/api/client.ts` — low-level HTTP client functions.
  - `useOverviewQuery()`, `useDocumentsQuery()`, `useWorkflowRunMutation()`, `useDeckMutation()`, `useChatMutation()`, `useStructuredTaskMutation()`, `useModelComparisonMutation()`, `useEvidenceOpsSummaryQuery()` in `frontend/src/lib/api/hooks.ts` — React Query hooks shared across pages.

- Modified functions:
  - `list_product_documents(rag_settings: RagSettings) -> list[ProductDocumentRef]` in `src/product/service.py` — enrich document rows with status/warnings/size/source metadata.
  - `run_product_workflow(request: ProductWorkflowRequest, *, history_path: Path | None = None) -> ProductWorkflowResult` in `src/product/service.py` — keep the existing workflow dispatch while optionally persisting history records.
  - `generate_product_workflow_deck(result: ProductWorkflowResult, *, settings: PresentationExportSettings, workspace_root: Path | None = None, history_path: Path | None = None) -> tuple[dict[str, Any], list[ProductArtifact]]` in `src/product/service.py` — update artifact history after deck generation.
  - `build_product_bootstrap() -> ProductBootstrap` in `src/app/product_bootstrap.py` — resolve runtime roots/log paths so API/service code does not recompute them ad hoc.
  - `ProductApiHandler.do_GET(self) -> None` in `src/product/api.py` — dispatch overview/runtime/history/artifact/chat/structured/evidenceops GET endpoints.
  - `ProductApiHandler.do_POST(self) -> None` in `src/product/api.py` — dispatch workflow run/deck generation/document upload/chat/structured/model comparison/EvidenceOps write endpoints.
  - `main.py` event handlers in the Streamlit app — replace inline chat orchestration with the extracted reusable service.
  - All page components in `frontend/src/pages/*.tsx` listed above — replace imports from `mock-data.ts` with hooks, loading states, mutation handlers, and response mappers.
  - `frontend/src/lib/store.ts` — expand from layout-only state to shared runtime preferences and API-backed UI state.

- Removed functions:
  - No Python callable APIs should be removed in this implementation; the goal is extraction and reuse, not functional regression.
  - On the frontend, no exported helper functions need a formal migration path because the current mock layer is data constants, not business functions. The migration strategy is to remove `mock-data.ts` only after every import has been replaced by live hooks.

[Classes]
Class changes are limited to extending existing Pydantic/dataclass contracts and the HTTP handler, while the React UI remains function-component-based.

Detailed breakdown:

- New classes:
  - `ProductWorkflowHistoryEntry` in `src/product/models.py` — persisted representation of a workflow run.
  - `ProductArtifactRecord` in `src/product/models.py` — persisted/listable representation of one exported artifact.
  - `ProductRuntimeOptions` and nested option models in `src/product/models.py` — typed runtime settings contract.
  - `ProductChatMessage`, `ProductChatRequest`, `ProductChatResponse` in `src/product/models.py` — typed chat transport layer.
  - `ProductStructuredTaskDescriptor`, `ProductStructuredTaskRequest`, `ProductStructuredTaskResponse` in `src/product/models.py` — typed structured-output transport layer.
  - `ProductModelComparisonCandidate`, `ProductModelComparisonRequest`, `ProductModelComparisonResponse` in `src/product/models.py` — typed model-comparison transport layer.
  - `ProductOverviewSnapshot` and `ProductEvidenceOpsConsoleResponse` in `src/product/models.py` — aggregate read models for overview and EvidenceOps pages.
  - `UploadedFilePayload` (dataclass or lightweight model) in `src/product/api.py` or `src/product/ai_lab_service.py` — normalized representation of files received over HTTP.

- Modified classes:
  - `ProductDocumentRef` in `src/product/models.py` — expanded to include operational document-library metadata.
  - `ProductWorkflowResult` in `src/product/models.py` — should gain stable identifiers/timestamps needed for history and artifact linking.
  - `ProductBootstrap` in `src/app/product_bootstrap.py` — extend with resolved runtime/log/artifact paths needed by the frontend API layer.
  - `ProductApiHandler` in `src/product/api.py` — extend route coverage, request parsing, and shared serialization/error helpers.

- Removed classes:
  - No existing backend classes should be removed in this implementation.
  - No React class components are planned; all new UI composition should stay within the current functional-component pattern.

[Dependencies]
The implementation should reuse the existing Python and React stacks, with no mandatory new runtime dependencies in the first pass.

Dependency details:

- Frontend already has the main pieces needed for the migration:
  - `@tanstack/react-query` for server-state caching and mutations.
  - `zustand` for runtime preference state.
  - `zod` if frontend request/response validation is desired.
  - `react-hook-form` if workflow/settings forms need stronger field control.

- Backend can stay on the current dependency set:
  - stdlib HTTP server in `src/product/api.py` remains acceptable for the first integrated pass.
  - Existing Pydantic models and Python services remain the source of truth.
  - Existing runtime/logging/storage helpers are sufficient for overview, evidence, and history surfaces.

- Version changes / new packages:
  - No package version bumps are required to execute the initial integration plan.
  - No new Python or frontend package is required if multipart upload parsing is handled in the current server layer.
  - If multipart parsing or long-term API evolution becomes a bottleneck later, a follow-up evaluation of FastAPI/Uvicorn can happen separately, but that is not the primary implementation path for this task.

[Testing]
Testing will combine Python API/unit coverage, frontend component/integration tests, and a browser smoke path that proves the React app works against real backend contracts instead of mocks.

Detailed testing requirements:

- Backend tests:
  - Extend `tests/test_product_api_unittest.py` to cover:
    - `GET /api/product/overview`
    - `GET /api/product/history`
    - `GET /api/product/artifacts`
    - `GET /api/product/runtime/options`
    - `POST /api/product/documents/upload`
    - `POST /api/product/lab/chat`
    - `GET /api/product/lab/structured/tasks`
    - `POST /api/product/lab/structured/run`
    - `POST /api/product/lab/models/compare`
    - `GET /api/product/lab/evidenceops/summary`
    - `GET /api/product/lab/evidenceops/search`
    - `POST /api/product/lab/evidenceops/register`
    - `POST /api/product/lab/evidenceops/actions/update`
  - Add `tests/test_product_workflow_history_unittest.py` for the new storage module.
  - Add `tests/test_chat_runtime_unittest.py` for extracted chat orchestration and citation/history behavior.
  - Update `tests/test_product_service_unittest.py` to assert history persistence and enriched artifact/document fields.
  - Keep `tests/test_product_workflows_front_integration_unittest.py` and `tests/test_candidate_review_front_integration_unittest.py` green after the history/deck changes.

- Frontend tests:
  - Replace `frontend/src/test/example.test.ts` with real API/client and route tests.
  - Add Vitest + Testing Library coverage for:
    - `OverviewPage` overview-query rendering.
    - `DocumentsPage` live document list + upload mutation states.
    - one workflow detail page exercising run + grounding preview + artifact rendering.
    - `ChatPage` sending a turn and rendering source citations.
    - `StructuredOutputsPage` rendering a backend `StructuredResult` projection.
    - `ModelComparisonPage` rendering ranking rows from a real API payload.
    - `EvidenceOpsPage` rendering summary/search states.
  - Mock network calls with `vi.stubGlobal("fetch", ...)` or equivalent built-in Vitest techniques so no new mocking dependency is required.

- End-to-end / smoke validation:
  - Use the existing Playwright setup in `frontend/` to verify the shell loads against the API.
  - Minimum smoke flow: Overview → Documents → one workflow page → Deck Center → Chat → Structured Outputs → Model Comparison → EvidenceOps.
  - Add a regression check that no production page still imports `frontend/src/lib/mock-data.ts`.

[Implementation Order]
The sequence should stabilize backend contracts and persistence first, then wire the React pages feature-by-feature, and only remove the mock layer after all routes are consuming live data.

1. Extend `src/product/models.py` and `src/app/product_bootstrap.py` with the API contracts and resolved runtime/log paths the frontend integration needs.
2. Create `src/storage/product_workflow_history.py` and wire `src/product/service.py` so workflow runs and deck exports can be persisted and listed.
3. Extract reusable chat orchestration from `main.py` into `src/services/chat_runtime.py` to eliminate Streamlit-only execution logic.
4. Create `src/product/ai_lab_service.py` to assemble overview, runtime-options, structured-task, model-comparison, and EvidenceOps payloads from existing service modules.
5. Expand `src/product/api.py` with the new overview/history/artifact/documents/chat/structured/model-comparison/EvidenceOps endpoints, keeping backward compatibility for existing workflow endpoints where practical.
6. Add the typed frontend API layer in `frontend/src/lib/api/` and expand `frontend/src/lib/store.ts` for shared runtime preferences.
7. Migrate product-facing pages first: `OverviewPage`, `DocumentsPage`, `WorkflowCatalogPage`, workflow detail pages, `DeckCenterPage`, and `RunHistoryPage`.
8. Migrate AI Lab pages second: `ChatPage`, `StructuredOutputsPage`, `ModelComparisonPage`, `EvidenceOpsPage`, and `SettingsPage`/`RuntimeDrawer`.
9. Delete `frontend/src/lib/mock-data.ts`, refresh docs/config examples, and update page-level imports.
10. Finish with backend API tests, frontend Vitest coverage, and one Playwright-backed smoke path against the live API.

## next_steps

- As a later step, formalize the implementation task via `new_task` when the tool becomes available, using `implementation_plan.md` and `implementation_task_draft.md` as the foundation.