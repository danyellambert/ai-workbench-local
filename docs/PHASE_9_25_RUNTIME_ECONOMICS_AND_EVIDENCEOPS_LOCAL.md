# Phase 9.25 + Phase 9.5 (local) — Runtime economics and EvidenceOps foundation

## Objective of this iteration

Advance what could already be completed **without depending on** an external MCP, public deployment, Oracle, Gradio, or additional integrations.

The focus of this implementation was to strengthen two local tracks:

- **Phase 9.25** → runtime economics, usage observability, and budget-aware routing
- **Phase 9.5 (local foundation)** → reusable EvidenceOps worklog + evidence pack

---

## What was implemented

### 1. Richer runtime execution log

The aggregate execution view in `src/storage/runtime_execution_log.py` now also summarizes:

- `prompt_build_latency_s`
- average number of selected documents per run
- average number of retrieved chunks per run
- chunks used vs. discarded in the final context
- context truncation rate
- budget-routing auto-degrade rate
- average and maximum context pressure
- count of runs with:
  - `evidence_pipeline`
  - OCR
  - Docling
  - VLM
- aggregate distributions by:
  - `cost_source`
  - `budget_mode`
  - `budget_reason`
  - `context_window_mode`
  - `ocr_backend`

### 2. Operational document signals recorded per execution

The main app (`main.py`) now records local signals derived from the selected documents in `runtime_execution_log`, including:

- how many documents triggered the `evidence_pipeline` path
- how many involved OCR
- how many involved Docling
- how many involved VLM
- total suspicious pages
- total pages processed with Docling
- total VL regions attempted / successful
- distribution of OCR backends used

These signals are included in both the **chat with RAG** flow and the **structured** flow.

### 3. Expanded runtime snapshot

`src/services/runtime_snapshot.py` now exposes the recent operational state more clearly:

#### Chat

- `last_context_chars`
- `last_prompt_context_used_chunks`
- `last_prompt_context_dropped_chunks`
- `last_prompt_context_truncated`
- `last_total_tokens`
- `last_cost_usd`

#### Structured

- `last_context_chars`
- `last_full_document_chars`
- `last_context_strategy`
- `last_total_tokens`
- `last_cost_usd`
- budget-routing signals for the structured execution

### 4. More explainable operational sidebar

The sidebar panel (`src/ui/sidebar.py`) now shows more clearly:

- recent context signals in chat
- recent context signals in structured execution
- aggregate runtime economics metrics
- auto-degrade and truncation rate
- OCR / Docling / VL metrics
- new aggregate distributions for cost, budget, and OCR backend

### 5. EvidenceOps worklog with local evidence pack

`src/services/evidenceops_worklog.py` now generates an `evidence_pack` block inside each worklog entry.

That pack includes:

- `review_type`
- `summary`
- `document_ids`
- `source_documents`
- `source_count`
- `findings_count`
- `action_items_count`
- `recommended_actions_count`
- `limitations_count`
- `finding_type_counts`
- `owner_counts`
- `status_counts`
- `due_date_counts`
- `needs_review`
- `needs_review_reason`

In addition, the main worklog entry now exposes:

- `source_document_count`
- `finding_count`
- `action_item_count`
- `evidence_pack`

### 6. More useful aggregate EvidenceOps summary

The aggregate in `src/storage/phase95_evidenceops_worklog.py` now also calculates:

- `unique_document_count`
- `finding_type_counts`
- `due_date_counts`

This improves the operational readability of the local history even before an external MCP exists.

### 7. Local Phase 9.5 foundation for repository + action store

In addition to the worklog, this iteration also exposed the local backbone of `EvidenceOps` more clearly:

- `src/services/evidenceops_repository.py`
  - local corpus listing via `filesystem`
  - classification by category (`policies`, `contracts`, `audit`, `templates`)
  - extraction of `document_id`, title, extension, size, and relative path
  - aggregate summary of the local corpus

- `src/storage/phase95_evidenceops_action_store.py`
  - local update of actions already persisted in `SQLite`
  - incremental metadata patching for an auditable trail

- `src/services/evidenceops_local_ops.py`
  - reusable local query layer for a future MCP/HTTP adapter
  - listing and resolution of documents in the local repository
  - filterable action listing by `status`, `owner`, and `review_type`
  - local action update (`status`, `owner`, `due_date`, metadata)

- `src/services/runtime_snapshot.py`
  - new aggregate summary for `evidenceops_actions`
  - new aggregate summary for `evidenceops_repository`

- `src/ui/sidebar.py`
  - new panel for the local `action store`
  - new panel for the local `document repository`

In practice, this closes a first local slice of the **Document Repository + Action Store foundation**, still without a real MCP server, but already ready to be promoted to an external adapter later.

---

## Tests added / updated

Focused tests were updated to cover the changes:

- `tests/test_runtime_execution_log_unittest.py`
- `tests/test_phase95_evidenceops_worklog.py`
- `tests/test_runtime_snapshot_unittest.py`
- `tests/test_phase95_evidenceops_local_ops.py`

These tests now validate:

- new runtime economics aggregations
- the evidence pack and additional EvidenceOps counts
- exposure of the new signals in the runtime snapshot
- listing/querying of the local document repository
- listing/updating of the local action store

---

## What was documented as partially delivered in the roadmap

### Phase 9.25

Delivered in this iteration:

- a more unified local layer of per-execution metrics
- recording of context chars, used/discarded chunks, and truncation
- recording of OCR / Docling / VLM activation at the local operational level
- aggregate historical view by provider/model

### Phase 9.5 (local foundation)

Delivered in this iteration:

- a reusable structured evidence pack at the local level
- local action store in `SQLite` with reading, updating, and an auditable trail
- local document repository in `filesystem` over the synthetic business corpus
- local service layer ready for future exposure via MCP/HTTP
- snapshot/sidebar with an operational view of the repository and action store

---

## What has **not** been implemented yet

These parts remain pending and were kept as future work:

### Runtime economics / budget-aware routing

- capturing native tokens when the provider exposes real telemetry, instead of depending mainly on character-based estimation
- per-task budgets with explicit warning thresholds
- automatic local/cloud fallback policy guided by cost
- systematic validation of budget-aware routing against evals
- a complete aggregate view also including the `comparison` flow

### EvidenceOps / Phase 9.5

- real external MCP (`Document Repository MCP`, `Worklog / Action MCP`, etc.)
- real local MCP server over stdio/external configuration
- external document search via MCP
- version comparison via MCP
- permissions and human-in-the-loop for sensitive actions in external integration
- stronger diff/versioning inside the repository adapter

---

## Correct architectural reading of this iteration

What exists now is a **strong local foundation** for Phases 9.25 and 9.5.

It is not yet the full MCP phase, but there is already a practical base for:

- observing cost/usage in a more useful way
- auditing document behavior more effectively
- reusing evidence packs in the future
- preparing the transition to real operational integrations without losing traceability