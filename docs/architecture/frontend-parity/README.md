# Frontend parity

This document is the curated frontend parity reference for the current product.

It exists so new readers do not need to inspect raw grep outputs or temporary audit files to understand how the frontend surface is organized.

## Purpose

Frontend parity means that the visible product UI, backend API, and mounted data roots describe the same current product.

The current product should not expose screens that depend on missing backend routes, fake payloads, or historical-only state.

## Current product surfaces

The current frontend is expected to align with the product API and runtime/baseline data roots for surfaces such as:

- Command Center
- Workflow Catalog
- Document Library
- Run History
- Run Detail
- Artifacts / Deck Center
- AI Lab
- Benchmarks and evals
- EvidenceOps
- Candidate Review
- Action Plan
- Runtime and Preferences

## Canonical rule

The frontend should call product-api for product state.

It should not read baseline, runtime, artifacts, or users directly.

The backend is responsible for resolving:

- baseline state;
- runtime state;
- artifact records;
- user/session overlays;
- admin/global state;
- provider/runtime capabilities;
- document and RAG state.

## Deployment relevance

Frontend parity must hold in:

- local development;
- local Docker Compose;
- AWS Docker deployment;
- Oracle-like deployment.

The same visible product concepts should be backed by the same API contract and compatible mounted data roots across those modes.

## Raw provenance

Raw capture files used during the cleanup are preserved under:

- legacy/docs/provenance/frontend-parity/frontend-pages.txt
- legacy/docs/provenance/frontend-parity/navigation-sources.txt
- legacy/docs/provenance/frontend-parity/react-routes.txt
- legacy/docs/provenance/frontend-parity/frontend-actions-grep.txt
- legacy/docs/provenance/frontend-parity/frontend-api-grep.txt
- legacy/docs/provenance/frontend-parity/route-link-audit.json

Those files are provenance, not canonical onboarding documentation.
