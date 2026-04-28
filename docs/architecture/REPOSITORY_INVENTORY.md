# Repository Inventory

This inventory records the repository structure at the start of the clean production-readiness runbook branch.

## Product frontend

- Path: `frontend/`
- Stack: React, TypeScript, Vite, Tailwind, React Query
- Main product API client: `frontend/src/lib/product-api.ts`
- AI Lab API client: `frontend/src/lib/ai-lab-data.ts`

## Product API

- Entrypoint: `main_product_api.py`
- Main route surface: `src/product/api.py`
- Runtime/path helpers: `src/storage/`
- Product services and workflow helpers: `src/product/`

## Runtime state

Runtime state is local and should not be committed directly.

Known local runtime areas include:

- `.runtime/`
- `.chroma_rag/`
- `artifacts/`
- `outputs/`
- benchmark output directories
- local `.env` files

## Demo seed goal

The production-readiness path should eventually produce a curated functional seed with:

- product state
- AI Lab state
- RAG/preindexed corpus state
- EvidenceOps state
- artifact metadata and safe artifact files
- no secrets
- no absolute local paths
- no mutable global state for public users

## External services

Known related services/projects:

- PPT Creator service
- Ollama / local model validation service
- Nextcloud corpus environment

These should be integrated only after the seed and golden surface contracts are stable.

## Generated inventory files

- `docs/architecture/repo_tree_depth2.txt`
- `docs/architecture/src_files.txt`
- `docs/architecture/frontend_files.txt`
- `docs/architecture/local_size_inventory.txt`

## Clean restart rule

This branch restarts the production-readiness work from the original base. Do not reapply experimental patches from the previous `production-readiness` branch directly. Reintroduce behavior only through small, validated phases.
