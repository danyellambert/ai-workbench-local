# Phase 5 Evidence CV Evaluation Report

## Objective

Consolidate the evaluation of the `evidence_cv` pipeline with per-field metrics and guide the rollout decision.

## Evaluated comparison

- legacy
- evidence without VL
- evidence with VL

Evaluated fields:
- `name`
- `emails`
- `phones`
- `location`

## Evaluation hardening for contacts

This phase focused on correctly aligning the evaluation of `emails` and `phones` across:
- predicted values
- manual gold set
- normalization used in the comparison
- aggregate and per-file metrics

### Final canonical form for emails
- case-insensitive comparison
- trimmed whitespace
- duplicates removed through normalized form
- invalid/incomplete emails discarded from comparison

Comparison form used:
- `local@domain.tld` in lowercase

### Final canonical form for phones
- comparison by normalized digits
- removal of spaces, parentheses, hyphens, and decorative symbols
- deduplication by the final numeric sequence
- short/implausible sequences discarded

Comparison form used:
- digits-only string
- accepting country/area codes when they are present in the document

### What was misaligned before
- cosmetic differences counted as errors
- the contact report did not clearly show TP/FP/FN per file
- there was little debug material for quick inspection

### What was fixed
- explicit and consistent normalization on both sides
- per-file debug with predicted contacts, normalized gold, matches, false positives, and false negatives
- aggregate metrics for `predicted_total`, `gold_total`, `tp`, `fp`, `fn`, `precision`, `recall`

### Practical reading of the current state
- the evaluation is now more coherent and reproducible
- there is still misalignment between the synthetic corpus and predicted contact values in some documents
- this indicates that the evaluation infrastructure is better, but some of the noise is now truly extraction/data noise, not just comparison noise

### Conclusion of this phase
For a controlled rollout:
- `confirmed` remains ready for automatic consumption
- `visual_candidate` still requires review
- contact evaluation is now significantly more auditable
- however, it still should not be treated as fully resolved while strong divergence remains between predicted contacts and the gold set in part of the synthetic corpus

## Adjudication of divergent contact cases

Generated file:
- `phase5_eval/reports/evidence_cv_contact_adjudication.json`

### Root causes found

After inspecting the divergent cases:

- `gold_set_incorrect`: **6** contact divergences
- `corpus_inconsistent`: **0**
- `pipeline_false_positive`: **2**
- `pipeline_false_negative`: **0**
- `normalization_mismatch`: **0**
- `ambiguous_document`: **0**

### Objective reading

The Gabriel, Marina, and Beatriz cases showed that most of the earlier error was in the **gold set**, not in the comparison and not necessarily in the pipeline.

The Matheus case remains the main example of a **pipeline false positive** in a difficult scan-like document, especially when VL steps in and proposes contacts not supported by the document.

### Final metrics after adjudication

#### Legacy
- emails: precision **1.0**, recall **1.0**
- phones: precision **1.0**, recall **1.0**

#### Evidence without VL
- emails: precision **1.0**, recall **0.6**
- phones: precision **0.2727**, recall **0.6**

#### Evidence with VL
- emails: precision **0.7143**, recall **1.0**
- phones: precision **0.8333**, recall **1.0**

### Rollout conclusion for contacts

With adjudication applied:
- contact evaluation became sufficiently trustworthy to guide rollout
- the gain from the VL path in contact **recall** is real
- the main residual risk is concentrated in difficult scan-like cases such as Matheus

Practical recommendation:
- keep a controlled rollout of the evidence pipeline for **CV-like PDFs** and **strong scan-like cases**
- continue automatically consuming only `confirmed`
- keep `visual_candidate` out of automatic consumption until a new precision-refinement round for edge cases

## Product usage

Recommended policy in this phase:
- automatically use only `confirmed`
- keep `visual_candidate` and `needs_review` out of automatic consumption
- expose those states only as metadata/review

## Where VL adds the most value

Current best cost/benefit:
- `scanned_pdf` PDFs
- medium scan-like documents
- documents with headers/contacts that are difficult for pure OCR

Current lowest benefit:
- already readable digital PDFs
- documents where OCR/native text already recovers contact information with good quality

## Where noise still exists

The hardest cases still present:
- extra `visual_candidate` items
- residual false positive contacts
- uncertain location in degraded scans

## Objective rollout recommendation

Enable by default first for:
- CV-like PDFs
- strong scan-like cases

Keep it disabled by default for all generic PDFs until the next refinement round.

## Hybrid consumption policy and shadow rollout

In this phase, the product starts operating with a hybrid policy for contacts:

### Hybrid merge for contacts
- `emails`:
  - confirmed legacy data takes precedence
  - evidence `confirmed` only fills gaps
- `phones`:
  - confirmed legacy data takes precedence
  - evidence `confirmed` only fills gaps

### Singular fields
- `name`: consume only `evidence confirmed`
- `location`: consume only `evidence confirmed`

### Shadow rollout
The metadata now records:
- when legacy and evidence agree
- when evidence only complements
- when there is a conflict

Fields available in the upload pipeline:
- `metadata.hybrid_contact_policy`
- `metadata.shadow_rollout`

## Final field-by-field rollout recommendation

- `emails`: use hybrid merge
- `phones`: use hybrid merge
- `name`: remain conservative, only `confirmed`
- `location`: remain conservative, only `confirmed`

## Shadow rollout report

Script:
- `scripts/report_evidence_shadow_rollout.py`

Default output:
- `phase5_eval/reports/evidence_cv_shadow_rollout_report.json`

## Final shadow rollout observability

After adjusting metadata propagation and aligning the script with the same load/extraction path used by the real flow, the shadow rollout report started quantitatively reflecting hybrid behavior.

### Current totals
- `agreements`: **2**
- `email_complements`: **5**
- `phone_complements`: **5**
- `email_conflicts`: **0**
- `phone_conflicts`: **0**

### Concrete examples

#### Complement
- `0001_medium_modern_two_column_gabriel.gomes.almeida.pdf`
  - email_complement = 1
  - phone_complement = 1

- `0002_hard_compact_sidebar_marina.gomes.ribeiro.pdf`
  - email_complement = 1
  - phone_complement = 1

- `0004_medium_scan_like_image_pdf_beatriz.barbosa.martins.pdf`
  - email_complement = 3
  - phone_complement = 3

#### Agreement
- `0009_simple_scan_like_image_pdf_matheus.araujo.carvalho.pdf`
  - agreements = 2
  - no contact was promoted by the hybrid merge

#### Conflict
- in this shadow rollout round: **no quantitative conflict appeared**

### Conclusion of this stage
The shadow rollout telemetry is now **complete and trustworthy** for:
- agreement
- complement
- conflict

This closes the minimum observability needed for a controlled rollout of the hybrid policy in the product.