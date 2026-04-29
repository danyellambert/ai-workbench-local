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
