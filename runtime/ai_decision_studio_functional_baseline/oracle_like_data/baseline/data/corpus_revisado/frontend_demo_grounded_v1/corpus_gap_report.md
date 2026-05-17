# Corpus gap report

## Audit conclusion
`data/corpus_revisado/option_b_synthetic_premium` was strong enough to reuse as the official base narrative, but it did not cover the frontend demo 1:1.
The main gaps were:
- March 2024 timeline mismatch
- no candidate-review pack
- no approval-email artifact
- no hard ambiguity redline summary
- no formal risk acceptance / waiver
- no subprocessor change notice
- no spreadsheet-export PDF in the main demo storyline
- no OCR-hard technical brief aligned to the frontend warning
- no explicit frontend mock → evidence mapping

## Architecture decision
Best option: create a derived corpus rather than overwrite Option B.

Chosen path:
- keep Option B as the official audited base
- derive a clean, traceable corpus at `data/corpus_revisado/frontend_demo_grounded_v1`
- preserve Option A as public reference only

## What was reused
Reused structurally from Option B:
- contract / policy / audit / evidence storylines
- metadata conventions
- narrative pattern linking findings → actions → evidence → closure

## What was altered / rewritten
Rewritten derivatives of Option B counterparts:
- MSA, SLA, DPA
- Information Security Policy v3.1 / v3.2
- Data Retention Policy
- Supplier Code of Conduct
- audit checklist, NCR, evidence log, committee minutes

## What was created from scratch
Created to close explicit frontend and realism gaps:
- candidate pack (CV, role brief, scorecard, interview memo)
- approval email artifact
- legal redline summary hard case
- temporary risk acceptance request
- subprocessor change notice
- remediation closure note
- spreadsheet-export vendor risk assessment PDF
- OCR-hard technical architecture brief
- board memo
- handbook
- coverage map and manifest files

## Out of scope / still partial
- Exact frontend operational metadata such as chunk counts, char counts, indexing timestamps, and workflow durations remain UI or system-state data, not document content.
- Candidate experience signals are grounded, but exact employer / institution names in the mock UI were intentionally not reproduced because the corpus uses fictionalized career history for safety.
