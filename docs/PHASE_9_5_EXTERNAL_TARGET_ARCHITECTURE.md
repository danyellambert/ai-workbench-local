# Phase 9.5 — External target architecture

## Official decision for this phase

The official target for the external completion of Phase 9.5 is now:

- **Nextcloud/WebDAV** for the external document repository
- **Trello** for the operational queue of human actions/worklog
- **Notion** for the evidence register, operational dashboard, and executive handoff

The official main corpus for the demo is now:

- **`data/corpus_revisado/option_b_synthetic_premium`**

The complementary/canonical corpus is now:

- **`data/corpus_revisado/option_a_public_corpus_v2`**

## Role of each integration

### 1. Nextcloud/WebDAV

Responsible for:

- storing `policies`, `contracts`, `audit`, `templates`, and related artifacts
- serving as the foundation of the **Document Repository MCP**
- enabling external document search, metadata reading, and drift/version comparison

### 2. Trello

Responsible for:

- representing `action_items` outside the app
- providing owner, comments, status, and a human trail for actions
- serving as the foundation of the **Worklog / Action MCP**

### 3. Notion

Responsible for:

- storing evidence packs, dashboards, and executive views
- functioning as a readable layer for human review and handoff
- concentrating the view of status, evidence, owners, and links to documents/actions

## Final architectural reading

### What remains local

- `filesystem + SQLite`
- local MCP server
- app MCP client
- MCP observability
- local end-to-end demo

### What moves to the external layer

- documents: `Nextcloud/WebDAV`
- human actions/workflow: `Trello`
- executive register/dashboard: `Notion`

## Recommended implementation order

1. **Nextcloud/WebDAV**
   - list documents
   - search documents
   - read metadata
   - compare drift/versions

2. **Trello**
   - create action
   - update status
   - assign owner
   - comment on approval/rejection

3. **Notion**
   - register evidence packs
   - generate a summarized operational view
   - consolidate links to documents, actions, and evidence

## What still depends on the user

### Nextcloud/WebDAV

- base URL
- username
- password or app password
- target document folder/base

### Trello

- API key
- token
- target board
- minimum lists/statuses

### Notion

- integration token
- database IDs or page IDs
- minimum schema for the target tables/pages

## Practical definition of a “complete Phase 9.5”

Consider Phase 9.5 complete when there is:

1. a working **real local MCP**
2. the **app using MCP** in the main flow
3. **MCP observability** in the runtime
4. **Nextcloud/WebDAV** connected as the external repository
5. **Trello** connected as the external action/worklog layer
6. **Notion** connected as the evidence register/dashboard layer
7. an **end-to-end demo** showing external document -> analysis -> evidence pack -> action -> dashboard