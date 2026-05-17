# Legacy Research And Experiments

This document identifies historical research and implementation paths that are preserved for engineering context but are not the active product contract.

## Active Versus Historical

The active product is the React/Vite frontend, Product API, PPT Creator sidecar, Nextcloud, Ollama, mounted runtime roots, and the local/AWS Docker contracts.

Historical material is preserved when it explains earlier research, evaluation, deployment, or product decisions. It should not be read as the current deployment or runtime path unless a current document explicitly references it as active.

## Preserved Historical Areas

### Streamlit And Gradio Surfaces

Earlier UI experiments helped validate workflow ideas before the current React product surface. They remain historical and are not the current frontend.

Primary location:

- `legacy/`

### Evidence CV And OCR/VL Research

Evidence CV, OCR fallback, synthetic CV benchmarks, and VL-on-demand work helped establish extraction and evaluation practices. They remain useful reference material for the structured-output and evidence-grounding story.

Primary references:

- `docs/reference/evidence-cv-pipeline.md`
- `docs/reference/benchmark-pdf-extraction.md`
- `legacy/docs/phases/evaluations-and-synthetic-cv-benchmark.md`
- `legacy/docs/phases/ocr-fallback-and-synthetic-cv-benchmark.md`
- `legacy/docs/phases/ocr-first-vl-on-demand-production-readiness-for-cv-parsing.md`

### Historical Requirements

Heavy dependency sets with packages such as Docling, transformers, and sentence-transformers were part of earlier research and extraction paths. The current product dependency contract is root `requirements.txt`.

Primary references:

- `requirements.txt`
- `legacy/requirements/`
- `docs/deployment/python-dependencies.md`

### Oracle-Specific Deployment Paths

Oracle-specific and Oracle-like deployment paths are preserved as historical context. The current product deployment contracts are local Docker and AWS.

Primary references:

- `legacy/`
- `docs/deployment/deployment-evolution.md`
- `docs/deployment/local-docker-compose.md`
- `docs/deployment/aws-deploy.md`

### Historical Phase Documents

Earlier phase documents explain how the product capabilities emerged. They are stored under `legacy/docs/phases` so the public documentation can keep the current product docs focused while still preserving the engineering trail.

Primary location:

- `legacy/docs/phases/`

## Current Reading Path

Use these current docs first:

- `README.md`
- `ROADMAP.md`
- `docs/product/overview.md`
- `docs/product/product-evolution.md`
- `docs/architecture/capability-map.md`
- `docs/deployment/deployment-evolution.md`
- `docs/operations/engineering-controls.md`

Use legacy documents when tracing why a capability exists or how an earlier experiment informed the current implementation.
