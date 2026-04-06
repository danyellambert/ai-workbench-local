# Product Surface Evolution Plan

This document is a planning artifact for the product-surface split that introduces a clearer boundary between:

- a **product-facing surface** for document workflows
- an **engineering-facing surface** for benchmarking, evaluation, observability, and operational inspection

It is intentionally written as a forward-looking implementation plan, not as a completed-phase summary.

## Planning goal

Create a Gradio-based product surface while preserving the existing Streamlit application as the engineering and experimentation console.

## Why this plan exists

The repository already contains most of the backend capabilities required by the product direction:

- document ingestion and indexing
- RAG context assembly
- structured task execution
- EvidenceOps and MCP foundations
- presentation export services

The main gap is not backend capability. The gap is **surface separation**. The current Streamlit application still concentrates product workflows, operational inspection, benchmarking, and advanced controls in the same interface.

## Planned split

### Product surface

The planned Gradio surface is intended to present a smaller, workflow-oriented experience around document-grounded decision support.

Initial workflow set:

- Document Review
- Policy / Contract Comparison
- Action Plan / Evidence Review
- Candidate Review

### Engineering surface

The existing Streamlit application remains the engineering-facing surface for:

- benchmark execution and comparison
- evaluation and diagnosis
- runtime inspection
- workflow traces and audit logs
- MCP and EvidenceOps operations

## Architectural direction

The recommended boundary remains:

- shared logic in `src/services`, `src/structured`, `src/rag`, and `src/storage`
- product orchestration in `src/product`
- Gradio UI code in `src/gradio_ui`
- Streamlit retained as the engineering console

## Constraints

- The plan should stay additive rather than destructive.
- Shared backend contracts should remain canonical.
- UI-specific concerns should not leak into the shared task and service layers.
- Documentation for this plan must stay clearly separated from completed-phase documentation.

## Expected outcome

When implemented, the split should make the repository easier to read as both:

- a document workflow product
- a serious engineering environment for benchmarking and controlled AI system evolution
