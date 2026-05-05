# Golden Surface Summary

This document records the reviewed Golden Surface capture for AI Decision Studio.

Golden Surface is a parity ruler only. It is not the Docker seed source and must not be served as a fake backend.

## Capture

- Snapshot path: `../ai_decision_studio_golden_snapshots/current_local_snapshot`
- Capture type: read-only API payloads
- Captured endpoints: 15
- Capture status: ok
- Raw snapshot committed: no

## Main parity counts

| Surface | Count / size |
|---|---:|
| Product workflows | 4 |
| Product documents | 17 |
| Product run history | 100 |
| Product artifacts | 100 |
| Lab artifacts | 80 |
| EvidenceOps actions | 72 |
| Raw snapshot size | 10M |

## Key response shapes

| Endpoint | Required top-level keys |
|---|---|
| `/health` | `ok`, `product_headline`, `service`, `workflow_count` |
| `/api/product/command-center` | `ok`, `recent_artifacts`, `recent_runs`, `summary` |
| `/api/product/workflows` | `contract_version`, `executive_deck_catalog`, `product_headline`, `workflow_count`, `workflows` |
| `/api/product/document-library` | `capabilities`, `documents`, `ok`, `summary` |
| `/api/product/run-history` | `history_path`, `ok`, `runs`, `source`, `summary` |
| `/api/product/artifacts` | `artifact_root`, `artifacts`, `ok`, `summary` |
| `/api/lab/overview` | `alerts`, `cross_surface_notes`, `degraded_reason`, `kpis`, `meta`, `ok`, `review_rate`, `runtime`, `status`, `workflow_mix` |
| `/api/lab/runtime` | `cost_summary`, `diagnostics_rows`, `failure_modes`, `generation_rows`, `latency_breakdown`, `meta`, `ok`, `provider_breakdown`, `recent_traces`, `retrieval_health`, `runtime`, `status`, `timeline`, `watchouts` |
| `/api/lab/workflow-inspector` | `capabilities`, `document_options`, `latest_runs`, `meta`, `ok`, `recent_cases`, `summary`, `task_details`, `task_health`, `task_options` |
| `/api/lab/benchmarks` | `leaderboardHighlights`, `meta`, `models`, `ok`, `presets`, `providerSummary`, `retrievalObservations`, `sourceBreakdown`, `status`, `summary` |
| `/api/lab/evals` | `cases`, `diagnosis`, `historicalCases`, `liveCases`, `liveTotals`, `meta`, `ok`, `passRate`, `providerBreakdown`, `status`, `suites`, `totals`, `watchlist` |
| `/api/lab/artifacts` | `artifacts`, `diagnostics`, `meta`, `ok`, `recentCaptures`, `runRegistry`, `status`, `summary` |
| `/api/lab/evidenceops` | `actions`, `categoryBreakdown`, `meta`, `ok`, `operations`, `readiness`, `repositoryStats`, `status`, `summary`, `telemetry`, `timeline`, `tools` |
| `/api/runtime/controls` | `active_profile`, `available_connections`, `catalogs`, `contract_version`, `data_source`, `ok`, `options`, `updated_at` |
| `/api/preferences` | `active_profile_id`, `catalogs`, `connection_policy_rules`, `contract_version`, `credential_policy`, `ok`, `operator_preferences`, `options`, `provider_connections`, `runtime_profiles`, `updated_at` |

## Review findings

The raw snapshot contains absolute local paths under artifact payloads, including `/private/local/user/artifacts/presentation_exports/...`.

Therefore:

- raw snapshot files must stay outside Git;
- Functional Baseline builder must rewrite artifact paths to logical URIs such as `baseline://artifacts/...`;
- backend resolver must map logical URIs to safe mounted paths;
- artifact open/download must keep working after rewrite.

The quick secret scan produced mostly metadata/key-name false positives such as `authMethod`, `api_key` field names, and token accounting fields such as `prompt_tokens` / `completion_tokens`.

Therefore:

- raw snapshot is not approved for commit;
- committed baseline must preserve provider metadata and credential references only;
- actual credentials must come from env, Docker secrets, or admin credential store.

## Phase 5 conclusion

Golden Surface capture is complete.

Next phase: Functional Baseline State Builder.

The builder must use real local state, not the Golden Surface JSON, and must produce a portable sanitized baseline with real documents, chunks, artifacts, run history, EvidenceOps state, benchmarks/evals, runtime/preferences metadata, path rewrite reports, and secret reference reports.
