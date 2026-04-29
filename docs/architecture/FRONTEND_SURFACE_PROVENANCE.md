# Frontend Surface Provenance Map

This document maps each AI Decision Studio frontend surface to the real backend endpoints and local state sources that power it today.

The goal is to prevent fake/count-only Docker behavior. If a surface shows documents, runs, artifacts, benchmarks, evals, or EvidenceOps state, the Functional Baseline State must include the real backing objects needed for the backend to list, open, retrieve, and mutate through overlay.

## Mapping status

| Surface | Status |
|---|---|
| Document Library | MAPPED INITIAL |
| Run History | TODO |
| Run Detail | TODO |
| Artifacts / Deck Center | TODO |
| Workflows | TODO |
| AI Lab | TODO |
| EvidenceOps | TODO |
| Runtime Controls | TODO |
| Preferences | TODO |

---

## Document Library

### Frontend files

Primary surface:

- `frontend/src/pages/DocumentsPage.tsx`
- `frontend/src/lib/product-api.ts`

Shared consumers:

- `frontend/src/pages/DocumentReviewPage.tsx`
- `frontend/src/pages/ComparisonPage.tsx`
- `frontend/src/pages/ActionPlanPage.tsx`
- `frontend/src/pages/CandidateReviewPage.tsx`
- `frontend/src/pages/WorkflowCatalogPage.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/pages/WorkflowInspectorPage.tsx`
- `frontend/src/lib/workflow-demo-documents.ts`

The document library is not only a table. It is the source of selectable documents for workflows, chat, workflow inspector, candidate review, policy comparison, action plan review, and document review.

### API endpoints

Read/list/open:

- `GET /api/product/document-library`
- `GET /api/product/grounding-preview`
- `GET /api/product/integrations/nextcloud`
- `GET /api/product/integrations/nextcloud/open`
- `GET /api/product/upload-jobs/<job_id>`

Mutating/importing:

- `POST /api/product/upload-documents`
- `POST /api/product/integrations/nextcloud/import`
- `POST /api/product/integrations/nextcloud/sync`

### Backend handlers and helpers

Primary route surface:

- `src/product/api.py`

Relevant helpers:

- `list_product_documents(...)`
- `build_grounding_preview(...)`
- `start_product_nextcloud_batch_import_job(...)`
- `start_product_cached_nextcloud_import_job(...)`
- `download_nextcloud_repository_document(...)`
- `build_product_nextcloud_documents_payload(...)`
- `src/product/preindexed_corpus.py`
- `src/storage/rag_store.py`
- `src/storage/runtime_paths.py`

### Current local state sources

Primary functional state:

- `.runtime/state/rag/rag_store.json`
- `.runtime/state/rag/rag_store_documents.json`
- `.runtime/state/rag/preindexed_public_corpus.json`
- `.runtime/state/rag/preindexed_public_corpus_documents.json`
- `.runtime/state/rag/preindexed_public_corpus_chroma/chroma.sqlite3`
- `.chroma_rag/`

Related state that references document IDs:

- `.runtime/logs/product/workflow_history.json`
- `.runtime/logs/product/telemetry_runs.json`
- `.runtime/state/lab/chat_sessions.json`
- `.runtime/state/lab/workflow_runs.json`
- `.runtime/state/evidenceops/repository_snapshot.json`
- `.runtime/logs/evidenceops/worklog.json`

Previous seed-build files under `.runtime/seed_build/current/` are diagnostic only. They must not become the main Docker data source. Docker should be built from real RAG/document/chunk/index state.

### Functional Baseline requirement

If the local app shows 16 documents, the baseline must include the 16 real document records and their backing state.

The baseline must preserve:

- stable `document_id` / hashes;
- document names, status, `chunk_count`, `char_count`, size labels and warnings;
- source document files or logical source references;
- chunks/index metadata used by grounding preview and workflows;
- preindexed corpus records where local fast-path import is used;
- Chroma/vector state or enough RAG state to rebuild/sync deterministically;
- portable path mappings.

Recommended logical paths:

- `baseline://documents/...`
- `baseline://rag/rag_store.json`
- `baseline://rag/preindexed_public_corpus.json`
- `baseline://rag/chroma/...`

### Overlay requirement

The overlay must store new mutable state without changing baseline:

- newly uploaded/imported documents;
- newly generated chunks/index records;
- upload/import jobs;
- tombstones for hidden/deleted baseline documents;
- user-specific chat/workflow document references;
- new workflow runs referencing baseline and overlay documents.

### Secrets and credentials

Baseline document listing should require no secret.

Nextcloud import/list/open may require external configuration. Do not commit raw values. Use credential references:

- `env:NEXTCLOUD_BASE_URL`
- `env:NEXTCLOUD_USERNAME`
- `env:NEXTCLOUD_PASSWORD`
- `admin_credential_store:nextcloud`

Provider credentials for workflows are separate from baseline document listing.

### Path rewrite requirement

Do not commit unreviewed absolute paths such as `/Users/...`.

Rewrite local or service-specific paths into logical URIs and validate every referenced file.

### Validation command

```bash
python3 - <<'PY'
import json
from pathlib import Path

rag_store = Path(".runtime/state/rag/rag_store.json")
preindexed = Path(".runtime/state/rag/preindexed_public_corpus.json")

assert rag_store.exists(), rag_store
assert preindexed.exists(), preindexed

rag = json.loads(rag_store.read_text(encoding="utf-8"))
pre = json.loads(preindexed.read_text(encoding="utf-8"))

print({
    "rag_documents": len(rag.get("documents") or []),
    "preindexed_documents": len(pre.get("documents") or []),
    "rag_chunks": len(rag.get("chunks") or []),
    "preindexed_chunks": len(pre.get("chunks") or []),
})
PY
```

### Status

Initial provenance mapped from frontend/backend grep and local runtime inspection.

---

## Run History and Run Detail

### Frontend files

Primary surface:

- `frontend/src/pages/RunHistoryPage.tsx`
- `frontend/src/lib/product-api.ts`

Shared consumers:

- `frontend/src/pages/DocumentReviewPage.tsx`
- `frontend/src/pages/ComparisonPage.tsx`
- `frontend/src/pages/ActionPlanPage.tsx`
- `frontend/src/pages/CandidateReviewPage.tsx`
- `frontend/src/pages/WorkflowCatalogPage.tsx`
- `frontend/src/pages/DeckCenterPage.tsx`

Run History is not only a log table. It is the bridge between historical workflow executions, rerun controls, result hydration, linked artifacts, generated decks, delivery outputs and product telemetry.

### API endpoints

Read/list/detail:

- `GET /api/product/run-history`
- `GET /api/product/run-history/<run_id>`
- `GET /api/product/artifacts`
- `GET /api/product/artifacts/<artifact_id>`
- `GET /api/product/artifact?path=...`

Mutating actions:

- `POST /api/product/run-history/<run_id>/rerun`
- workflow deck generation endpoint using `run_id`
- Trello/Notion delivery endpoints using `run_id`, when enabled

### Backend handlers and helpers

Primary route surface:

- `src/product/api.py`

Relevant backend helpers:

- `build_product_workflow_history_entry(...)`
- `build_product_run_detail_payload(...)`
- `build_product_artifact_payload(...)`
- `build_product_artifact_detail_payload(...)`
- `_build_product_workflow_response_payload(...)`
- `_resolve_product_artifact_path(...)`
- `append_product_workflow_history_entry(...)`
- `update_product_workflow_history_entry(...)`
- `attach_artifact_lineage(...)`
- `attach_delivery_lineage(...)`
- `execute_product_workflow_with_telemetry(...)`

Storage helpers:

- `src/storage/product_workflow_history.py`
- `src/storage/product_telemetry.py`
- `src/storage/runtime_paths.py`
- `src/storage/lab_state.py`

### Current local state sources

Primary product history state:

- `.runtime/logs/product/workflow_history.json`
- `.runtime/logs/product/telemetry_runs.json`
- `.runtime/state/product/runtime_controls.json`
- `.runtime/state/product/preferences.json`

Related lab/workflow state:

- `.runtime/state/lab/workflow_runs.json`
- `.runtime/state/lab/artifacts_index.json`
- `.runtime/state/lab/chat_sessions.json`

Artifact state:

- `artifacts/`
- `outputs/`
- `.runtime/state/product/artifacts_index.json`, if present
- `.runtime/seed_build/current/product/artifacts_index.json`, diagnostic only
- `.runtime/seed_build/current/product/workflow_history.json`, diagnostic only

Previous seed-build/public-surface files under `.runtime/seed_build/current/public_surface/run_history.json` and `artifacts.json` are useful as comparison material, but they must not become the main Docker data source.

### Functional Baseline requirement

The baseline must preserve real historical runs and their relationships.

Each baseline run should preserve:

- stable run ID;
- workflow ID and workflow label;
- status;
- timestamps and duration metadata;
- selected `document_ids`;
- selected document names where available;
- request payload;
- result payload;
- `result_sections`;
- workflow-specific views such as `result_view`, `comparison_view`, `action_plan_view`, and `candidate_review_view`;
- linked artifact metadata;
- delivery metadata, if present;
- telemetry metadata, if present.

If a run references artifacts, the artifact records and files must exist in the baseline or be explicitly marked unavailable with a clear reason.

### Artifact/path requirement

Artifact paths must be portable.

Do not preserve raw host-only paths as operational paths. Convert artifact references to logical URIs such as:

- `baseline://artifacts/...`
- `baseline://outputs/...`
- `runtime://artifacts/...`
- `user://artifacts/...`

The backend artifact resolver must allow only approved roots and reject path traversal or arbitrary absolute paths.

### Overlay requirement

The overlay must store new mutable history without changing baseline:

- new workflow runs;
- reruns created from baseline runs;
- new generated decks/artifacts;
- new delivery outputs;
- new telemetry records;
- tombstones or user-hidden baseline run records, if needed.

Rerunning a baseline run should create a new overlay run, not mutate the baseline run.

### Secrets and credentials

Historical run display should require no secret.

Rerun may require provider credentials depending on the workflow. Those credentials must be resolved through credential references, not stored in the run history baseline.

Expected missing-secret behavior:

- history still renders;
- run detail still opens;
- artifacts still open when present;
- rerun returns a clear missing credential error instead of a blank page or fake response.

### Validation requirement

For the Functional Baseline builder, validate:

- every run with `document_ids` references known baseline or overlay documents;
- every artifact item with a path resolves under an allowed logical root;
- every run detail can be converted back into a workflow response shape;
- rerun creates a new overlay run;
- baseline history remains read-only.

---

## Artifacts / Deck Center

### Frontend files

Primary surface:

- `frontend/src/pages/DeckCenterPage.tsx`
- `frontend/src/lib/product-api.ts`

Shared consumers:

- `frontend/src/pages/RunHistoryPage.tsx`
- `frontend/src/pages/DocumentReviewPage.tsx`
- `frontend/src/pages/ComparisonPage.tsx`
- `frontend/src/pages/ActionPlanPage.tsx`
- `frontend/src/pages/CandidateReviewPage.tsx`
- `frontend/src/pages/AdvancedExperimentsPage.tsx`

The Deck Center is the product artifact registry. It must point to real persisted files, not only artifact counts.

### API endpoints

Read/list/detail/open:

- `GET /api/product/artifacts`
- `GET /api/product/artifacts/<artifact_id>`
- `GET /api/product/artifact?path=...`

Mutating/generation:

- workflow deck generation endpoint using `run_id`
- workflow pages call `generateProductWorkflowDeck(...)`
- artifact lineage is attached back to run history when generation succeeds

### Backend handlers and helpers

Primary route surface:

- `src/product/api.py`

Relevant helpers:

- `build_product_artifact_payload(...)`
- `build_product_artifact_detail_payload(...)`
- `_resolve_product_artifact_path(...)`
- `generate_product_workflow_deck(...)`
- `attach_artifact_lineage(...)`
- `get_artifact_root(...)`

Artifact catalog logic:

- `src/product/command_center.py`
- `src/product/service.py`
- `src/product/telemetry.py`
- `src/storage/runtime_paths.py`

### Current local state sources

Primary artifact state:

- `artifacts/presentation_exports/`

Each deck export directory can include:

- `metadata.json`
- `payload.json`
- `review.json`
- `contract.json`
- `render_request.json`
- `render_response.json`
- `preview-manifest.json`
- `*.pptx`
- `*-thumbnails.png`
- preview PNG files

Related state:

- `.runtime/logs/product/workflow_history.json`
- `.runtime/logs/product/telemetry_runs.json`
- `.runtime/state/lab/artifacts_index.json`
- `.runtime/state/lab/workflow_runs.json`
- `.runtime/seed_build/current/product/artifacts_index.json`, diagnostic only

### Functional Baseline requirement

The baseline must include real artifact records and real files.

For every artifact shown in Deck Center, the baseline should preserve:

- artifact ID;
- workflow label;
- created timestamp;
- status;
- slide count;
- preview count;
- asset count;
- `local_pptx_path` or equivalent logical path;
- `local_payload_path` or equivalent logical path;
- preview assets;
- metadata sidecars;
- links back to run history when available.

A deck card should not appear as ready unless its referenced files exist.

### Path rewrite requirement

Artifact paths must become portable logical URIs.

Examples:

- `baseline://artifacts/presentation_exports/deckexp_x/metadata.json`
- `baseline://artifacts/presentation_exports/deckexp_x/deck.pptx`
- `baseline://artifacts/presentation_exports/deckexp_x/payload.json`
- `baseline://artifacts/presentation_exports/deckexp_x/preview-manifest.json`
- `user://artifacts/presentation_exports/deckexp_y/deck.pptx`

The backend resolver must reject arbitrary absolute paths and path traversal.

### Overlay requirement

New generated artifacts must be written to overlay, not baseline.

Overlay stores:

- new deck export directories;
- new metadata sidecars;
- new previews;
- new payload files;
- artifact lineage back to overlay run history.

Baseline artifacts remain read-only.

### Secrets and credentials

Viewing historical artifacts should require no provider secret.

Generating a new deck may require:

- model/provider credentials for workflow generation;
- PPT Creator service configuration;
- renderer/export service configuration.

Those must be injected at runtime through env, Docker secrets or admin credential store. They must not be embedded in artifact metadata.

### Validation requirement

For the Functional Baseline builder, validate:

- every ready artifact has existing files;
- every `local_pptx_path` resolves to a real `.pptx`;
- every `local_payload_path` resolves to a real JSON payload;
- preview manifests reference existing preview files;
- artifact paths resolve only under allowed baseline or overlay roots;
- run history artifact links point to existing artifact records where expected.
