# Sanitized Functional Baseline

This document records Phase 6B of the AI Decision Studio production-readiness runbook.

The sanitized functional baseline is generated outside Git from the raw functional baseline stage.

## Input

```bash
../ai_decision_studio_functional_baseline/current_raw_stage
```

## Output

```bash
../ai_decision_studio_functional_baseline/current_sanitized_baseline
```

## Purpose

The sanitized baseline is a portable candidate runtime baseline for future Docker mounting.

It is built from real local state, not from Golden Surface JSON snapshots.

## Current behavior

The builder:

- copies the raw staged sources into a baseline candidate;
- rewrites absolute local paths to logical URIs;
- copies externally referenced files into `baseline/external_files`;
- writes `uri_rewrite_map.json`;
- writes `path_rewrite_report.json`;
- writes `audit_after.json`;
- writes `manifest.json`;
- reports whether the candidate is Docker-ready from a sanitization perspective.

## Current observed output

The latest generated candidate reported:

- RAG documents: 17
- RAG chunks: 283
- Preindexed documents: 55
- Preindexed chunks: 967
- Workflow history runs: 532
- Product telemetry runs: 176
- Lab workflow runs: 176
- Lab artifacts derived from presentation exports: 183
- EvidenceOps worklog entries: 68
- EvidenceOps action rows: 75
- Presentation export directories: 196
- Remaining absolute path files: 0
- Secret-pattern files: 0
- Sanitization-level Docker-ready: true

## Important note

Docker-ready in this phase only means the generated candidate has no detected absolute local paths or secret-pattern hits.

It does not yet mean the backend has been wired to load from this baseline.

## Commit policy

Generated baseline data is not committed.

Only the builder script and documentation are committed.
