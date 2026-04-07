# Phase 9.5 — Local EvidenceOps MCP server

## What this delivery adds

This iteration promotes the local EvidenceOps vertical into a **real MCP server over stdio**, without depending on an external SDK and without leaving the current `filesystem + SQLite` stack.

## Where the server is

- main implementation: `src/mcp/evidenceops_server.py`
- JSON-RPC stdio transport/framing: `src/mcp/jsonrpc_stdio.py`
- simple entrypoint: `scripts/run_evidenceops_mcp_server.py`

## Exposed tools

- `list_documents`
- `search_documents`
- `get_document`
- `summarize_repository`
- `compare_repository_state`
- `register_evidenceops_entry`
- `list_actions`
- `summarize_actions`
- `update_action`
- `summarize_worklog`

## Exposed resources

- `evidenceops://repository/summary`
- `evidenceops://repository/drift`
- `evidenceops://actions/summary`
- `evidenceops://worklog/summary`

## How to run locally

```bash
python scripts/run_evidenceops_mcp_server.py
```

## Registration in Cline

Registering the server in Cline is **optional**.

- it can be useful for debugging/manual testing with Cline as the MCP client
- but it is **not part of the product core**
- the main project flow remains:
  - local MCP server
  - app MCP client
  - integration with `main.py`

If you do not want to mix the project infrastructure with the assistant infrastructure, you can leave Cline **without this registration**.

## Supported environment variables

- `EVIDENCEOPS_REPOSITORY_ROOT`
- `EVIDENCEOPS_REPOSITORY_BACKEND` (`local` or `nextcloud_webdav`)
- `EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH`
- `EVIDENCEOPS_ACTION_STORE_PATH`
- `EVIDENCEOPS_WORKLOG_PATH`

When `EVIDENCEOPS_REPOSITORY_BACKEND=nextcloud_webdav`, the **Document Repository MCP** starts using the real Nextcloud/WebDAV adapter for repository tools (`list_documents`, `search_documents`, `get_document`, `summarize_repository`, `compare_repository_state`), preserving the local fallback when the backend remains `local`.

If they are not defined, the server uses the project's default local paths.

## Local demo

There is a deterministic demo that starts the server, initializes the MCP client, and calls the main tools:

```bash
python scripts/demo_phase95_evidenceops_mcp.py
```

It demonstrates:

1. `initialize`
2. `tools/list`
3. `list_documents`
4. `register_evidenceops_entry`
5. `list_actions`
6. `compare_repository_state`
7. `update_action`
8. `resources/read`

## Current product integration

In addition to the local server itself, the phase now already includes:

- a **reusable MCP client in the app** (`src/services/evidenceops_mcp_client.py`)
- use of MCP in the main `document_agent` flow
- **MCP telemetry** in the runtime execution log and sidebar
- an **"EvidenceOps MCP"** tab in the app to operate repository/actions/worklog through a real MCP

## Correct interpretation of this delivery

This still remains inside **slice 1** of Phase 9.5:

- the server is a **real MCP**
- but the adapters are still **local**
- in other words: the engine remains on `filesystem + SQLite`

## Official target architecture for Phase 9.5

After this iteration, the official target for the phase becomes:

- **`Nextcloud/WebDAV`** for the external document repository
- **`Trello`** for actions, owners, comments, and the human workflow
- **`Notion`** for the evidence register, operational dashboard, and executive handoff

Recommended reading:

- the local baseline (`filesystem + SQLite`) remains the fallback and debug trail
- the external triad (`Nextcloud/WebDAV + Trello + Notion`) becomes the main direction of the external slice of the phase

## What still depends on external setup

To complete the phase with real external adapters, the following will still be required:

- **Nextcloud/WebDAV**
  - base URL
  - username
  - password or app password
  - target document folder/base
- **Trello**
  - API key
  - token
  - target board
  - minimum list/status mapping
- **Notion**
  - integration token
  - database IDs or page IDs
  - minimum schema for evidence packs, status, owner, due date, and source links

## Natural next step

The natural next step is no longer generic. It becomes opening the external adapters in order:

1. `Nextcloud/WebDAV`
2. `Trello`
3. `Notion`