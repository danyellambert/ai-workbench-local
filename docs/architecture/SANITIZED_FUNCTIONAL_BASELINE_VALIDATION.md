# Sanitized Functional Baseline Validation

This document records the validation step for the sanitized functional baseline candidate.

## Baseline validated

../ai_decision_studio_functional_baseline/current_sanitized_baseline

## Validation command

python3 scripts/validate_sanitized_functional_baseline.py \
  --baseline-dir ../ai_decision_studio_functional_baseline/current_sanitized_baseline \
  --out ../ai_decision_studio_functional_baseline/current_sanitized_baseline/validation_report.json

## Latest validation result

- ok: true
- manifest Docker-ready from sanitization perspective: true
- absolute path files: 0
- secret-pattern files: 0
- failures: 0

## Counts validated

| Item | Count |
|---|---:|
| RAG documents | 17 |
| RAG chunks | 283 |
| Preindexed documents | 55 |
| Preindexed chunks | 967 |
| Workflow history runs | 532 |
| Product telemetry runs | 176 |
| Lab workflow runs | 176 |
| EvidenceOps worklog entries | 68 |
| EvidenceOps action rows | 75 |
| Artifact metadata files | 203 |
| PPTX files | 460 |
| PDF files | 51 |
| PNG files | 2014 |
| JSON files | 2607 |
| External copied files | 2942 |

## Important note

This validation proves that the sanitized baseline candidate is internally present and sanitized.

It does not yet prove that the backend can load this baseline in Docker. Backend wiring and Docker mounting are the next phases.
