# Functional Baseline State

Functional Baseline State is the real sanitized runtime baseline that will eventually feed Docker.

It is not a frozen API snapshot.

## Phase 6A raw staging

The first staging step copies real local state outside Git into:

```bash
runtime/ai_decision_studio_functional_baseline/current_raw_stage
```

The raw stage is intentionally not committed because it contains local absolute paths and large runtime/artifact files.

## Sources copied

- `.runtime/state/rag`
- `.runtime/state/product`
- `.runtime/logs/product`
- `.runtime/state/lab`
- `.runtime/state/evidenceops`
- `.runtime/logs/evidenceops`
- `.phase95_evidenceops_actions.sqlite3`
- `artifacts/presentation_exports`
- selected corpus/document source directories under `data/`

## Current raw-stage observations

The staging script copies real state and reports counts for:

- RAG documents/chunks
- preindexed documents/chunks
- workflow history runs
- product telemetry runs
- lab workflow runs
- EvidenceOps worklog entries
- EvidenceOps action rows
- presentation export directories
- artifact metadata directories derived from presentation exports

Current observed raw-stage counts:

| Item | Count |
|---|---:|
| RAG documents | 17 |
| RAG chunks | 283 |
| Preindexed documents | 55 |
| Preindexed chunks | 967 |
| Workflow history runs | 532 |
| Product telemetry runs | 176 |
| Lab workflow runs | 176 |
| Lab artifacts derived from presentation exports | 183 |
| EvidenceOps worklog entries | 68 |
| EvidenceOps action rows | 75 |
| Presentation export directories | 196 |

## Audit result

The raw stage currently contains absolute paths and is not Docker-ready.

The raw stage did not detect secret-pattern hits in the current scan, but future baseline builders must continue scanning for credentials and sensitive values.

## Important rule

The raw stage is not Docker-ready.

Next subphase must build a portable sanitized baseline by:

- rewriting absolute paths to logical URIs;
- preserving real files needed by document/view/artifact workflows;
- validating references;
- keeping credentials out of committed state;
- preserving provider metadata and credential references only.
