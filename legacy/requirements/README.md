# Legacy Python Requirements

The current product uses the root `requirements.txt` file for local Docker,
AWS slim, local development, and tests.

This directory keeps older dependency snapshots for provenance:

- `requirements.legacy-full.txt` was the previous root development/test
  dependency set.
- `requirements-product-api.local.txt` was the previous local Docker product API
  dependency set.
- `requirements-product-api.aws-slim.txt` was the previous AWS slim product API
  dependency set.

These files are not used by the current Docker or AWS deployment contracts.
They are preserved because earlier project phases used heavier optional
capabilities such as Docling PDF extraction, Evidence CV experiments, local
Hugging Face `transformers`, `sentence-transformers`, and neural reranking
benchmarks.
