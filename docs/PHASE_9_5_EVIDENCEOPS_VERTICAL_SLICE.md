# Phase 9.5 — EvidenceOps vertical slice 1B

## Objective of this iteration

Complete **slice 1B** of Phase 9.5 without depending on external infrastructure, strengthening the EvidenceOps vertical on top of `filesystem + SQLite`.

## What was added

- **stronger repository search**
  - filters by `category`, `suffix`, and `document_id`
  - local scoring for multiple terms
- **snapshot + document drift**
  - local snapshot persisted in `.phase95_evidenceops_repository_snapshot.json`
  - diff with counts of `new`, `changed`, and `removed` documents
- **auditable guardrails in the action store**
  - sensitive updates require `approval_status="approved"`, `approval_reason`, and `approved_by`
  - update history saved in `metadata.update_history`
- **a more complete local operational facade**
  - search, summary, and repository state comparison
  - actions/worklog summary ready for future promotion to an MCP/HTTP adapter
- **better observability in the sidebar/runtime snapshot**
  - document drift metrics
  - governance metrics (`review_required`, `approved`, `pending approval`, `overdue`)

## Architectural reading

This delivery is **not yet Slice 2**. It remains 100% within the scope of **Slice 1**:

- local document repository
- local worklog
- local action store
- human-in-the-loop governance for sensitive writes

The gain is that the vertical becomes more **“MCP-shaped”**:

- clearer local contracts
- better observability
- document state comparison
- an auditable trail for writes

## Official direction for Slice 2

After this iteration, the official direction of Phase 9.5 is no longer generic. It becomes:

- **`Nextcloud/WebDAV`** for the external **Document Repository MCP**
- **`Trello`** for the external **Worklog / Action MCP**
- **`Notion`** for the **evidence register, operational dashboard, and executive handoff**

Recommended reading:

- `filesystem + SQLite` remain the auditable local foundation
- the `Nextcloud/WebDAV + Trello + Notion` triad becomes the main external target
- `GitHub Issues` stops being the primary target and becomes a secondary alternative for more dev-centric contexts

## What this prepares for next

With this foundation, the next step can swap adapters without rewriting the vertical:

- `filesystem` -> `Nextcloud/WebDAV`
- local `SQLite` -> `Trello`
- local summaries/evidence packs -> `Notion`
- local facade -> MCP server/HTTP adapter

## What still depends on credentials/configuration

Slice 1B is complete without depending on external services.

To promote the vertical to the final external slice of Phase 9.5, the following will still be required:

- `Nextcloud/WebDAV` credentials
- `Trello` credentials plus board/list mapping
- `Notion` integration token plus database/page mapping

## Evidence of readiness

This iteration should allow the following to be demonstrated locally:

1. search and listing of the EvidenceOps corpus
2. detection of document drift between snapshots
3. auditable registration and updating of actions
4. blocking of sensitive writes without explicit approval
5. exposure of those signals in the runtime snapshot/sidebar