# Python Dependency Contract

The current Axiovance product uses one Python dependency file:

- `requirements.txt`

Both Docker product API builds install from this same file:

- `Dockerfile.product-api.local`
- `Dockerfile.product-api.aws`

This keeps local Docker and AWS aligned and avoids the old split between
environment-specific requirements files.

## Current Product Scope

`requirements.txt` intentionally keeps the runtime lean. It supports the current
React product surface, product API, retrieval stack, ChromaDB, LangChain,
LangGraph, reporting, and operational scripts used by the deployable product.

The current Docker/AWS product runtime does not require the heavier local
document-intelligence packages that were used by earlier project phases.

## Legacy Dependency Sets

Historical requirements files are archived under `legacy/requirements/`:

- `requirements.legacy-full.txt`
- `requirements-product-api.local.txt`
- `requirements-product-api.aws.txt`

Those files are kept for provenance only. Earlier flows used packages such as
`docling`, `transformers`, and `sentence-transformers` for Evidence CV,
Docling-based PDF extraction, local Hugging Face experiments, and neural
reranking benchmarks. Those capabilities remain useful historical context, but
they are not part of the default deployable product dependency contract.
