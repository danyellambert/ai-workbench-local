# Integration Trajectory

This document explains how the external delivery and document-operation layer evolved into the current product integrations.

## Current Integration Surface

The active product supports these integration categories:

- document repository import and sync through Nextcloud/WebDAV;
- operational card delivery through Trello;
- memo/register publishing through Notion;
- PPTX generation through the PPT Creator sidecar;
- MCP Operations for operational tooling surfaces.

All publish actions are preview-first. Credentials are optional, private, and admin-gated.

## Nextcloud And WebDAV

Nextcloud provides the document repository surface used by the product. It can host the prepared demo corpus and supports import/sync behavior through WebDAV.

Key properties:

- Nextcloud runs as one of the five active Docker services;
- credentials and root paths come from environment/runtime configuration;
- baseline restore can prepare the document repository state;
- preindexed import behavior is documented for faster demo operation.

Primary references:

- `docs/operations/preindexed-nextcloud-import.md`
- `docs/deployment/NEXTCLOUD_GOLDEN_BASELINE_RESTORE.md`
- `src/product/integration_hub.py`

## Trello

Trello publishing converts workflow outputs into operational cards. The product supports preview before publish so users can inspect planned cards, labels, checklists, evidence, and handoff metadata.

Primary references:

- `frontend/src/components/product/WorkflowPublishActions.tsx`
- `src/product/integration_hub.py`

## Notion

Notion publishing converts workflow outputs into memo/register-style sections. The preview surface lets users inspect templates and sections before publishing.

Primary references:

- `frontend/src/components/product/WorkflowPublishActions.tsx`
- `src/product/integration_hub.py`

## PPT Creator

PPT Creator was separated as a sidecar so the Product API can hand off deck contracts without carrying presentation generation concerns in the main API container.

Key responsibilities:

- receive deck contracts;
- produce PPTX outputs;
- provide previews and export metadata;
- write generated artifacts into mounted artifact storage.

Primary references:

- `services/ppt_creator_app/ppt_creator/api.py`
- `docs/architecture/executive-deck-generation/README.md`
- `docs/product/product-evolution.md`

## From EvidenceOps To MCP Operations

Earlier EvidenceOps naming described the operational handoff layer. The current UI uses MCP Operations where the feature represents operational tooling and action surfaces. Historical EvidenceOps docs remain useful for understanding the original integration direction.

Primary references:

- `docs/architecture/evidenceops/external-target-architecture.md`
- `docs/architecture/evidenceops/vertical-slice.md`
- `frontend/src/pages/EvidenceOpsPage.tsx`

## Current Status

The delivery layer is integrated but optional:

- workflows can run without external publish credentials;
- previews are available before publishing;
- admin credentials unlock real external delivery;
- generated artifacts stay in mounted runtime/artifact storage.
