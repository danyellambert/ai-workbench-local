# AI Decision Studio — Production Readiness Runbook

**Status:** updated clean-runbook version  
**Project name:** AI Decision Studio  
**Legacy/internal course name:** do not use “Aula 4” in new public-facing docs, repository descriptions, Docker service names, or portfolio copy. Use **AI Decision Studio** or **AI Studio** instead.  
**Core correction from previous attempt:** do **not** convert the product into frozen JSON payloads. Docker must run the real backend over a real, sanitized, functional baseline state.

---

## 0. Executive summary

The target is a Docker-local version of **AI Decision Studio** that behaves like the current local app:

- same frontend surfaces;
- same real documents;
- same real chunks/index metadata;
- same real artifacts and previews;
- same historical runs, benchmark/eval summaries, and EvidenceOps state;
- workflows that run against real indexed documents;
- new user/admin actions written to a mutable overlay;
- baseline state preserved read-only;
- secrets injected at runtime, not committed into the baseline.

The product should not be “a static demo that returns numbers.” If the local app shows 16 documents, the Docker baseline must contain the 16 document records and the backing document/index/chunk state needed for the backend to list, open, retrieve, and run workflows against them.

The main state model is:

```text
visible_state(user) = functional_baseline_readonly + user_overlay
```

Where:

```text
functional_baseline_readonly
  = curated, real, sanitized local state that powers the initial app

user_overlay
  = new mutable state created by the user/admin after Docker starts
```

---

## 1. Non-negotiable principles

### 1.1 Docker must reproduce the local product, not fake it

Avoid this pattern:

```text
GET /api/product/document-library -> frozen JSON file
POST /api/product/run-workflow -> prepared answer that ignores real input
```

Use this pattern:

```text
GET /api/product/document-library
  -> real backend
  -> reads baseline/runtime/index state
  -> returns real document records

POST /api/product/run-workflow
  -> real backend
  -> resolves selected document IDs
  -> uses real chunks/retrieval/preindexed state
  -> creates a new run in overlay
  -> returns a renderable workflow result
```

### 1.2 Golden Surface is a ruler, not the source of truth

Golden Surface captures what the local app returns today so that future changes can be compared.

It must not become the main Docker backend.

```text
Golden Surface Snapshot = measurement / parity check
Functional Baseline State = real state mounted into Docker
```

### 1.3 Sanitization must not break runtime functionality

Sanitization does **not** mean deleting every required configuration concept. It means:

- remove actual secret values from committed baseline files;
- preserve non-secret provider metadata and runtime contract;
- replace secret values with explicit secret references;
- inject actual secrets at runtime through local/private mechanisms;
- fail clearly when required secrets are missing.

Example:

```json
{
  "id": "ollama_hosted",
  "label": "Ollama Hosted",
  "base_url": "https://ollama.com/api",
  "credential_ref": "env:OLLAMA_HOSTED_API_KEY",
  "credential_status": "required",
  "public_visible": true,
  "admin_editable": true
}
```

The baseline should not contain the API key, but it should preserve the fact that the provider exists, which secret it needs, and how Docker/admin mode should satisfy it.

### 1.4 One phase per commit

Avoid mixing:

```text
Docker + Nextcloud + workflows + frontend payload fixes + credentials + public demo policy
```

Each phase must have:

- small scope;
- validation command;
- commit only after validation passes.

---

## 2. Terminology

### Functional Baseline State

A curated copy of real local state that makes AI Decision Studio open with realistic, working data.

It can contain:

- real documents;
- real document metadata;
- real chunks/RAG/preindexed state;
- real artifacts and previews;
- historical run records;
- historical benchmark/eval summaries;
- EvidenceOps actions/worklog state;
- sanitized runtime/preferences shape.

It must not contain:

- raw API keys;
- raw tokens;
- `.env` files;
- private local credentials;
- unreviewed absolute local paths;
- irrelevant caches or huge temporary experiments.

### User Overlay

Writable per-user or per-admin state layered on top of the baseline.

It contains:

- new workflow runs;
- generated artifacts;
- imported/uploaded documents;
- user EvidenceOps changes;
- tombstones for hidden/deleted baseline objects;
- user-specific runtime/preferences where allowed;
- audit logs.

### Golden Surface Snapshot

Read-only API capture used to compare app behavior before/after refactors.

It is useful for questions like:

```text
Does Docker still return 16 documents?
Does the response shape still include the same top-level keys?
Do artifacts, runs, EvidenceOps, Runtime and Preferences still render?
```

But it is not the functional backend.

### Secret Reference

A safe placeholder that tells the runtime where to find a secret without storing the secret itself.

Examples:

```text
env:OLLAMA_HOSTED_API_KEY
env:HUGGINGFACE_API_TOKEN
docker_secret:ollama_hosted_api_key
admin_credential_store:ollama_hosted
```

---

## 3. Secret and credential strategy

This section is critical. Previous attempts broke provider functionality because secrets were removed without a proper replacement mechanism.

### 3.1 What should be committed

Commit provider **metadata**, not provider **secret values**.

Allowed:

```json
{
  "id": "huggingface_inference",
  "label": "Hugging Face Inference",
  "base_url": "https://api-inference.huggingface.co",
  "credential_ref": "env:HUGGINGFACE_API_TOKEN",
  "credential_status": "required",
  "enabled_for_public": false,
  "enabled_for_admin": true
}
```

Not allowed:

```json
{
  "api_key": "hf_xxx..."
}
```

### 3.2 Runtime secret sources

Use these in priority order:

1. **Docker secret** in production-like deployment.
2. **Gitignored `.env.docker.local`** for local Docker validation.
3. **Admin credential store volume** for credentials saved through the admin UI.
4. **macOS Keychain** only for local non-Docker development, not as the primary Docker mechanism.
5. **Validation credential file** only for local validation containers, never committed.

Recommended local file:

```text
.env.docker.local
```

Example:

```env
OLLAMA_HOSTED_API_KEY=...
HUGGINGFACE_API_TOKEN=...
ADMIN_PASSWORD_HASH=...
ADMIN_SESSION_SECRET=...
```

This file must be in `.gitignore`.

### 3.3 Credential resolution contract

Create/standardize a backend resolver:

```text
credential_ref -> credential value
```

Example mapping:

```text
env:OLLAMA_HOSTED_API_KEY
  -> os.environ["OLLAMA_HOSTED_API_KEY"]

docker_secret:ollama_hosted_api_key
  -> /run/secrets/ollama_hosted_api_key

admin_credential_store:ollama_hosted
  -> /data/credentials/ollama_hosted.json or encrypted store
```

The resolver must never log secret values.

### 3.4 Missing-secret behavior

Missing secrets should not crash the frontend or make blank pages.

Expected behavior:

```text
Document Library / historical pages:
  still render from baseline

Provider test:
  returns ok=false with clear error: missing credential

Workflow requiring hosted model:
  either uses configured provider
  or returns a clear actionable error

Admin UI:
  shows "credential required"
```

Not acceptable:

```text
blank page
500 without explanation
silent fallback to fake result
unrelated Keychain error inside Docker
```

### 3.5 Public vs admin credentials

Public users:

- cannot view credentials;
- cannot save credentials;
- cannot switch to local providers;
- can use providers that the server/admin has already configured.

Admin users:

- can configure provider credentials;
- can test connections;
- can use local Ollama if enabled;
- can index new documents.

### 3.6 Preflight validation

Before enabling live workflows in Docker, run a provider preflight:

```text
scripts/validate_runtime_credentials.py
```

It should check:

- required env vars are present for enabled providers;
- secrets are not accidentally embedded in baseline;
- provider base URLs are reachable when expected;
- missing credentials produce explicit warnings.

Example output:

```json
{
  "ok": false,
  "missing_required": ["OLLAMA_HOSTED_API_KEY"],
  "providers": {
    "ollama_hosted": {
      "configured": false,
      "credential_ref": "env:OLLAMA_HOSTED_API_KEY"
    }
  }
}
```

### 3.7 Sanitization rule

Sanitization should preserve **operational references**, not destroy them.

Replace this:

```json
{
  "api_key": "real-secret"
}
```

With this:

```json
{
  "credential_ref": "env:OLLAMA_HOSTED_API_KEY",
  "credential_status": "required"
}
```

---

## 4. Path strategy

Absolute local paths are dangerous in Docker and public repos, but removing paths entirely can break artifacts/documents.

### 4.1 Use logical URI schemes

Convert local paths into logical references:

```text
baseline://documents/audit/Access Review Evidence Log.pdf
baseline://artifacts/presentation_exports/run_123/deck.pptx
runtime://runs/run_123/result.json
user://artifacts/generated/deck.pptx
```

### 4.2 Backend path resolver

Create/standardize a resolver:

```text
logical URI -> safe filesystem path
```

Examples:

```text
baseline://documents/foo.pdf
  -> /data/baseline/documents/foo.pdf

baseline://artifacts/bar.pptx
  -> /data/baseline/artifacts/bar.pptx

user://artifacts/baz.pptx
  -> /data/users/{user_id}/artifacts/baz.pptx
```

### 4.3 Validation

The path resolver must reject:

- `../`;
- absolute arbitrary paths;
- `.env`;
- secret files;
- paths outside allowed roots.

### 4.4 Do not break artifact open

When sanitizing an artifact record, preserve enough metadata for the backend to open it.

Bad:

```json
{
  "artifact_id": "deck_1",
  "path": null
}
```

Good:

```json
{
  "artifact_id": "deck_1",
  "path": "baseline://artifacts/presentation_exports/deck_1/output.pptx",
  "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
}
```

---

## 5. Updated phase plan

| Phase | Name | Result |
|---|---|---|
| 1 | Backup local state | Ignored local state preserved |
| 2 | Clean branch | Safe base and clean working tree |
| 3 | Repository Inventory | Repo and local state inventoried |
| 4 | Frontend Surface Provenance Map | Each surface mapped to real data sources |
| 5 | Golden Surface Snapshot | Read-only behavior captured as parity ruler |
| 6 | Functional Baseline State Builder | Real local state copied/sanitized into baseline |
| 7 | Functional Baseline Validation | Baseline verified safe and operational |
| 8 | Docker local backend over real baseline | Real backend reads real baseline |
| 9 | Workflow parity | Workflows run against real indexed documents |
| 10 | User Overlay | New state isolated per user/admin |
| 11 | Public/Admin policy | Public locked down, admin operational |
| 12 | Provider strategy | Secrets and provider capabilities cleanly separated |
| 13 | Oracle-like Docker | Resource limits, proxy, healthchecks, volumes |
| 14 | Final validation | UI, data, workflows, artifacts, security pass |

---

## Phase 1 — Backup local state

### Goal

Preserve all ignored local state before changing anything.

Important local state:

```text
.runtime/
.chroma_rag/
artifacts/
outputs/
.env
benchmark_runs/
benchmark_pdfs/
data/
phase5_eval/
materials_local/
```

### Rule

Do not delete ignored state until the provenance map confirms it is not needed.

---

## Phase 2 — Clean branch

### Goal

Work from the original safe base.

Current clean branch:

```text
production-readiness-runbook-clean
```

Base:

```text
snapshot/before-production-readiness-20260427
```

Public demo containers from experimental work should be removed before new Docker tests.

External helper services may remain running:

```text
Nextcloud
PPT Creator
Ollama
```

But they must not be confused with the new Docker app.

---

## Phase 3 — Repository Inventory

### Goal

Map repository structure.

Committed output:

```text
docs/architecture/REPOSITORY_INVENTORY.md
docs/architecture/repo_tree_depth2.txt
docs/architecture/src_files.txt
docs/architecture/frontend_files.txt
docs/architecture/local_size_inventory.txt
```

### Status

Already completed on clean branch:

```text
f9108b8 docs(readiness): add clean repository inventory
```

---

## Phase 4 — Frontend Surface Provenance Map

### Goal

Map each frontend surface to its real data sources.

This phase prevents the mistake:

```text
number exists, but backing real object does not exist
```

### Document to create

```text
docs/architecture/FRONTEND_SURFACE_PROVENANCE.md
```

### Required columns per surface

For each screen/endpoint:

```text
Screen
Frontend files
API endpoint(s)
Backend function(s)
Current local state sources
Real files/DBs/indexes required
Mutable or historical
Docker baseline requirement
Overlay requirement
Secrets required?
Path rewrite required?
Validation command
```

### Surfaces to map

```text
Command Center
Workflow Catalog
Document Library
Run History
Run Detail
Artifacts / Deck Center
AI Lab Overview
AI Lab Runtime
Workflow Inspector
Benchmarks
Evals
EvidenceOps
Runtime Controls
Preferences
Chat / Document Experiments if visible
```

### Example: Document Library

```md
## Document Library

Frontend:
- frontend/src/pages/DocumentLibraryPage.tsx
- frontend/src/lib/product-api.ts

Endpoint:
- GET /api/product/document-library
- GET /api/product/grounding-preview
- POST /api/product/upload-documents
- POST /api/product/integrations/nextcloud/import

Backend:
- src/product/api.py
- src/product/preindexed_corpus.py
- src/storage/...

Current local state sources:
- .runtime/state/rag/...
- .chroma_rag/
- data/materials_demo/
- preindexed corpus metadata

Functional baseline requirement:
- every visible document record
- source document file
- chunk/index metadata
- stable document IDs/hashes
- open/preview path mapping

Overlay requirement:
- user-imported documents
- user-generated chunks/index records
- tombstones for hidden baseline documents

Secrets:
- none for listing baseline docs
- provider credentials only for live indexing/workflows
```

### Validation

The provenance map is complete when every major frontend tab has a real source plan.

---

## Phase 5 — Golden Surface Snapshot

### Goal

Capture read-only current API payloads as a comparison ruler.

### Important

Do not use this as backend source.

### Capture only read-only endpoints

Examples:

```text
GET /health
GET /api/product/command-center
GET /api/product/workflows
GET /api/product/document-library
GET /api/product/run-history
GET /api/product/artifacts
GET /api/lab/overview
GET /api/lab/runtime
GET /api/lab/workflow-inspector
GET /api/lab/benchmarks
GET /api/lab/evals
GET /api/lab/artifacts
GET /api/lab/evidenceops
GET /api/runtime/controls
GET /api/preferences
```

### Do not execute

```text
POST run-workflow
POST generate-deck
POST upload/import/delete
PATCH runtime/preferences
provider credential/test calls
```

### Recommended raw output

Outside repo first:

```text
../ai_decision_studio_golden_snapshots/current_local_snapshot/
```

### Commit only safe summaries

Examples:

```text
docs/architecture/GOLDEN_SURFACE_SUMMARY.md
tests/golden/frontend_surface/summary.json
```

After review.

---

## Phase 6 — Functional Baseline State Builder

### Goal

Create a real functional baseline bundle from local state.

### Script to create

```text
scripts/build_functional_baseline.py
```

### Recommended output

```text
data/functional_baseline/
```

Alternative public-facing name:

```text
data/demo_baseline/
```

Avoid “Aula 4” naming in new paths.

### Bundle structure

```text
data/functional_baseline/
  manifest.json
  README.md

  runtime/
    state/
      product/
      lab/
      rag/
      evidenceops/

  documents/
    ...

  rag/
    rag_store.json
    preindexed_public_corpus.json
    chroma/

  artifacts/
    ...

  outputs/
    ...

  benchmarks/
    summaries/

  evals/
    summaries/

  evidenceops/
    actions.sqlite3
    worklog.json
    repository_snapshot.json

  config/
    runtime_controls.sanitized.json
    preferences.sanitized.json
    provider_connections.sanitized.json

  manifests/
    document_manifest.json
    artifact_manifest.json
    run_history_manifest.json
    path_rewrite_report.json
    sanitization_report.json
    secret_reference_report.json
```

### Builder responsibilities

The builder must:

- copy real files required by the frontend/backend;
- preserve document IDs and hashes where possible;
- preserve artifact references;
- preserve run/artifact relationships;
- preserve benchmark/eval historical summaries;
- preserve EvidenceOps state;
- rewrite absolute local paths to logical paths;
- replace secret values with secret references;
- generate reports;
- validate that referenced files exist.

### What must not happen

The builder must not replace real objects with only counts.

Bad:

```json
{
  "document_count": 16
}
```

Good:

```json
{
  "documents": [
    {
      "document_id": "...",
      "title": "...",
      "path": "baseline://documents/...",
      "chunk_count": 7
    }
  ]
}
```

---

## Phase 7 — Functional Baseline Validation

### Goal

Validate that the baseline is real and safe.

### Script to create

```text
scripts/validate_functional_baseline.py
```

### Validation categories

#### Existence

- every document path exists;
- every artifact path exists;
- run history references existing artifacts where expected;
- RAG/chunk records exist for indexed documents;
- EvidenceOps DB/worklog loads.

#### Safety

- no `.env`;
- no raw API keys;
- no tokens;
- no local secret files;
- no unreviewed `/Users/...` paths;
- no path traversal;
- no missing referenced files.

#### Operational readiness

- provider metadata contains credential references;
- missing secrets are reported as missing, not silently removed;
- baseline can be mounted read-only;
- overlay path is writable separately.

### Output

```text
data/functional_baseline/manifests/validation_report.json
```

---

## Phase 8 — Docker local backend over real baseline

### Goal

Run the real backend in Docker over the functional baseline.

### Volumes

```text
/data/baseline:ro
/data/runtime:rw
/data/artifacts:rw
/data/users:rw
/run/secrets:ro, optional
```

### Environment

```env
APP_BASELINE_ROOT=/data/baseline
APP_RUNTIME_ROOT=/data/runtime
APP_ARTIFACT_ROOT=/data/artifacts
APP_USERS_ROOT=/data/users
APP_PUBLIC_DEMO_MODE=false
APP_USE_FUNCTIONAL_BASELINE=true
```

### Credentials

Local Docker should load:

```text
.env.docker.local
```

or Docker secrets.

Never bake secrets into the image.

### Startup behavior

If runtime is empty:

```text
backend initializes from baseline metadata
or reads baseline read-only directly and writes overlay separately
```

Preferred long-term:

```text
baseline read-only + overlay writable
```

Short-term acceptable:

```text
copy baseline to runtime on first boot
```

But if copied, document clearly that this is local validation mode, not final multi-user mode.

---

## Phase 9 — Workflow parity

### Goal

Workflows must run over real indexed documents.

### Required tests

```text
Document Review -> Master Service Agreement
Policy Comparison -> Information Security Policy v3.1/v3.2
Action Plan Evidence Review -> Access Review Evidence Log
Candidate Review -> real candidate CV
```

### Validation

Each workflow must show:

- selected document names, not hashes;
- grounding context from real indexed docs;
- result view renders;
- run history gets a new run;
- new run opens;
- no blank page.

### Allowed

Preindexed fast path is allowed if it is the same functional path used locally.

### Not allowed

```text
prepared response detached from selected docs
"No specific documents provided"
hash-only document labels
workflow ignores document_ids
```

---

## Phase 10 — User Overlay

### Goal

Allow mutation without changing baseline.

### Overlay paths

```text
/data/users/{user_id}/
  state/
  artifacts/
  documents/
  rag/
  logs/
  overlay/
```

### Mutation examples

- new workflow run;
- generated deck;
- imported document;
- EvidenceOps update;
- deleted/hidden baseline item tombstone.

### Rule

Baseline is never modified by public users.

---

## Phase 11 — Public/Admin policy

### Public user

Can:

- view baseline;
- run allowed workflows;
- create runs in own overlay;
- generate artifacts if enabled;
- update own EvidenceOps overlay.

Cannot:

- view secrets;
- save credentials;
- change global runtime;
- change global preferences;
- use local Ollama;
- mutate baseline.

### Admin

Can:

- configure providers;
- save/test credentials;
- use local Ollama;
- index new documents;
- inspect runtime;
- manage baseline/overlay operations.

---

## Phase 12 — Provider strategy

### Public/hosted

```text
OLLAMA_HOSTED_API_KEY via env/secret
HUGGINGFACE_API_TOKEN via env/secret, if enabled
```

### Admin/local

```text
OLLAMA_BASE_URL=http://ollama:11434/v1
local model options admin-only
embedding local admin-only
```

### Provider UI behavior

If credential missing:

```text
show "credential required"
disable test/run requiring credential
do not blank page
do not silently fallback to fake result
```

---

## Phase 13 — Oracle-like Docker

### Services

```text
reverse-proxy
frontend
product-api
ppt-creator
optional ollama admin profile
```

### Requirements

- baseline mounted read-only;
- runtime/user overlay writable;
- frontend and API same origin through proxy;
- no internal ports public except proxy;
- healthchecks;
- resource limits;
- backup/restore scripts.

---

## Phase 14 — Final validation

### Product

- frontend opens;
- Document Library shows real docs;
- View opens docs/artifacts;
- Run History opens historical runs;
- workflows run on real docs;
- artifacts open;
- AI Lab surfaces render;
- EvidenceOps works;
- Runtime/Preferences respect role.

### Data parity

Compare Docker against Golden Surface:

- counts within expected tolerance;
- response shapes compatible;
- no missing major surfaces.

### Safety

- no secrets in committed files;
- no raw `.env`;
- no unsafe absolute paths;
- credential refs work;
- missing secrets produce clear errors.

### Multi-user

- user A changes do not affect user B;
- baseline remains unchanged.

---

## 6. Immediate next step

Because repository inventory is already committed, the next clean commit should be:

```text
docs(readiness): add frontend surface provenance map
```

Create:

```text
docs/architecture/FRONTEND_SURFACE_PROVENANCE.md
```

Do not build Docker yet. Do not create the baseline yet. First map what real state each screen needs.

---

## 7. Definition of ready

AI Decision Studio is production-readiness Docker-local ready when:

> Docker runs the real backend over a real, sanitized Functional Baseline State. The frontend renders the same meaningful product surfaces as local. Documents, chunks, artifacts, run history, benchmarks, evals, and EvidenceOps are backed by real files/state, not fake counts. Workflows run over real indexed documents. New activity writes to an overlay. Secrets are injected at runtime through explicit references. The baseline remains safe, portable, and read-only.
