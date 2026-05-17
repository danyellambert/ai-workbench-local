# OCR-first / VL-on-demand Production Readiness for CV Parsing

## 1. Executive summary

The `evidence_cv` pipeline has reached a state of **readiness for controlled rollout** in production for CV parsing, with an OCR-first architecture, selective VL triggering, a conservative hybrid consumption policy in the product, sufficient observability, and safe operational fallback.

Summary of the final decision:
- use OCR/native extraction as the main path
- call VL only when there is a real need
- keep automatic consumption restricted to `confirmed`
- use conservative hybrid merge for contacts
- enable rollout first for CV-like PDFs and strong scan-like cases

## 2. Final pipeline architecture

Final flow:
1. native text extraction + OCR
2. basic evidential reconciliation
3. OCR-first / VL-on-demand router
4. region-selective VL only when necessary
5. normalization, dedupe, and ranking
6. product consumption policy
7. shadow rollout / observability / fallback

Core files:
- `src/evidence_cv/pipeline/runner.py`
- `src/evidence_cv/vision/ollama_vl.py`
- `src/rag/loaders.py`
- `src/evidence_cv/config.py`

## 3. OCR-first / VL-on-demand policy

### Principle
OCR/native extraction always comes first.
VL is not called by default on every CV.

### Final router rule

#### For `digital_pdf`
VL may only be called when there is:
- `missing_contacts_after_ocr`
- or a strong structural problem in the top/header area

In the final calibration, this drastically reduced unnecessary VL calls in good digital PDFs.

#### For `scanned_pdf` and `mixed_pdf`
The router remains more permissive, since VL gains tend to be more real in these documents.

### Router telemetry
Per-file metadata:
- `vl_router.enabled`
- `vl_router.decision`
- `vl_router.reasons`
- `vl_router.document_signals`
- `vl_router.regions_selected`
- `vl_router.skipped_because`

## 4. Results of the 60-CV multilayout benchmark

Base file:
- `phase5_eval/reports/evidence_cv_multilayout_router_benchmark.json`

### Main totals
- `files_processed = 60`
- `vl_called = 12`
- `vl_skipped = 48`

### Distribution by type
- `digital_pdf = 48`
- `scanned_pdf = 12`

### Economic reading
The router was economically acceptable:
- VL was skipped in most digital documents
- VL was reserved mainly for difficult scans

## 5. Results of cases where VL was called

Specific file:
- `phase5_eval/reports/evidence_cv_vl_called_cases_report.json`

Cases with VL called:
- `vl_called_cases = 12`

Final semantic distribution:
- `vl_called_and_added_value = 8`
- `vl_called_and_added_partial_value = 4`
- `vl_called_but_review_only = 0`
- `vl_called_and_added_noise = 0`
- `vl_called_and_false_positive = 0`

### Interpretation
- most cases in which VL was called brought real gains
- the others brought partial gains with controlled residual noise
- semantically bad cases stopped being promoted as full gains

## 6. Final field policy

### `emails`
- use hybrid merge
- confirmed legacy data takes precedence
- evidence `confirmed` only fills gaps

### `phones`
- use hybrid merge
- confirmed legacy data takes precedence
- evidence `confirmed` only fills gaps

### `name`
- use only `confirmed`

### `location`
- use only `confirmed`

## 7. Status behavior

### `confirmed`
- automatically consumable

### `visual_candidate`
- do not consume automatically
- expose for future review / assisted UX

### `needs_review`
- do not consume automatically

### `not_found`
- treat as absent

## 8. Operational resilience and fallback

### VL/Ollama backend
- timeout kept at `600s`
- structured error via `VLInspectionError`
- short, conservative retry for transient failures

### Runner
- failure in one region does not bring down the entire PDF
- if all regions fail, processing continues without VL enrichment

### Script/benchmark
- failure in one file does not bring down the entire report
- the final JSON is still produced

### Operational metadata
- `vl_runtime.enabled`
- `vl_runtime.model`
- `vl_runtime.regions_attempted`
- `vl_runtime.regions_succeeded`
- `vl_runtime.regions_failed`
- `vl_runtime.timeouts`
- `vl_runtime.fallback_used`
- `vl_runtime.warnings`

## 9. Controlled rollout recommendation

### Objective recommendation
Enable first for:
- CV-like PDFs
- strong scan-like cases

### Production behavior
- keep OCR-first as the default
- use VL-on-demand only when the router decides to
- keep hybrid merge for contacts
- keep `visual_candidate` out of automatic consumption

### Readiness decision
**Recommendation: ready for controlled rollout.**

It is not a universally “solved” parser, but it is already mature enough for controlled production with telemetry, fallback, and conservative policy.

## 10. Suggested next steps

### 10.1 Rollout / product
- activate rollout through a feature flag for a subset of CV-like uploads
- monitor shadow rollout and real conflicts in production
- monitor cost/latency by document type
- maintain a dashboard for `vl_called`, `vl_skipped`, `fallback_used`, `timeouts`

### 10.2 Future parser improvements
- reduce residual noise in difficult scans with partial gains
- improve `location` semantics in international cases
- improve dedupe and validation of near-duplicate visual contacts
- only then consider expanding to `experience` / `education`

## Final conclusion

The final recommended pipeline for CVs is:
- OCR-first
- economical VL-on-demand
- conservative hybrid merge for contacts
- automatic consumption only of `confirmed`
- safe fallback and sufficient observability

In practical terms: the system is already ready for a controlled and measured rollout in production.