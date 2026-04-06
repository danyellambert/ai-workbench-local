# Phase 5 Evidence Pack

This document gathers the most useful reproducible evidence for the Phase 5 delivery, aligned with the canonical roadmap in `ROADMAP.md`.

---

## 1. Primary automated evidence

### Latest local smoke evaluation

Command:

```bash
python scripts/run_phase5_structured_eval.py --task all
```

Result:

```text
[PASS] extraction: 5/5
[PASS] summary: 5/5
[PASS] checklist: 5/5
[PASS] cv_analysis: 5/5
[PASS] code_analysis: 5/5
```

Generated report:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

Why this is the strongest baseline evidence:

- it is reproducible
- it covers the five main structured tasks of the phase
- it generates a versionable JSON artifact
- it demonstrates more than schema-valid JSON: it shows minimum task usefulness

---

## 2. What the smoke evaluation proves

The latest report confirms successful execution for:

1. `extraction`
2. `summary`
3. `checklist`
4. `cv_analysis`
5. `code_analysis`

That matches the Phase 5 objective:

- predictable structured outputs
- schema-based validation
- model usage as an integrable system component rather than only open-ended chat

---

## 3. Concrete evidence by task

### 3.1 Extraction

In the latest report, `extraction` passed `5/5` and produced fields such as:

- `main_subject`
- `entities`
- `extracted_fields`
- `important_dates`
- `risks`
- `action_items`

Evidence file:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### 3.2 Summary

`summary` passed `5/5` and produced:

- topic bullets
- `executive_summary`
- `key_insights`
- `reading_time_minutes`

Evidence file:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### 3.3 Checklist

`checklist` passed `5/5` and produced:

- title
- description
- structured checklist items
- priority
- dependencies
- estimated time

Evidence file:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### 3.4 CV analysis

The current smoke evaluation also passed `5/5` for `cv_analysis` on the textual fixture.

There is also a saved real-case example:

- `phase5_eval/CV - Lucas -gen.json`

This real case is useful as complementary evidence because it shows:

- the flow running on a real CV
- structured output with `education_entries` and `experience_entries`
- honest visibility into current system limits

Observable limitations in that JSON include:

- `full_name = null`
- truncated email output (`as.souza-ferreira@student-cs.fr`)
- duplicated `experience_entries`

That makes the evidence more useful because it shows both working behavior and remaining edge cases.

### 3.4.1 Strengthened `evidence_cv` rollout with semantic gate

Beyond the textual smoke evaluation, the phase also includes strengthened rollout evidence for the `evidence_cv` parser with:

- operational guardrails
- staged automatic promotion
- a semantic gate using more realistic CV-like samples in `data/materials_demo/cv_analysis`

Primary evidence files:

- `phase5_eval/reports/evidence_cv_auto_rollout_decision.json`
- `phase5_eval/reports/evidence_cv_auto_rollout.log`

Most important current interpretation:

- the strengthened rollout finished without critical operational failures
- the semantic gate passed with `3/3` real/demo samples containing confirmed names
- the name-fix path corrected the earlier `Francis B. Taylor` and `Nathaly Ortiz` cases that had previously been marked as `not_found`

### 3.4.2 Note on empty `sections` in `cv_analysis`

During the strengthened rollout investigation, an important behavior appeared in the `cv_analysis` payload: in some cases, `education_entries`, `experience_entries`, `skills`, and `languages` were present while `sections` could still be empty.

That did not necessarily mean the result was empty or unusable. The pipeline was already structuring useful top-level information, but the model did not always fill `sections` directly.

After later hardening, the UI rendering layer can synthesize section views from:

- `experience`
- `education`
- `skills`
- `languages`

when those blocks exist in the payload, even if `sections` itself is empty.

### 3.5 Code analysis

`code_analysis` passed `5/5` and produced:

- `snippet_summary`
- `main_purpose`
- `detected_issues`
- `refactor_plan`
- `test_suggestions`

Evidence file:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

---

## 4. Recommended visual evidence for the UI

The project already includes an explicit guide for screenshots:

- `docs/PHASE_5_UI_EXAMPLES_GUIDE.md`

It also includes a selected example manifest:

- `phase5_eval/ui_examples_manifest.json`

The four strongest cases for screenshots and documentation are:

1. **textual_pass**
   - PDF: `0001_medium_modern_two_column_gabriel.gomes.almeida.pdf`
   - status: `PASS`

2. **visual_pass**
   - PDF: `0002_hard_compact_sidebar_marina.gomes.ribeiro.pdf`
   - status: `PASS`

3. **scan_warn**
   - PDF: `0004_medium_scan_like_image_pdf_beatriz.barbosa.martins.pdf`
   - status: `WARN`

4. **scan_fail_or_low**
   - PDF: `0009_simple_scan_like_image_pdf_matheus.araujo.carvalho.pdf`
   - status: `FAIL`

Together, these four cases show:

- a good textual case
- a good visually dense case
- a partially improved scan-like case
- a still-difficult edge case

---

## 5. Minimal evidence package

The strongest compact package for this phase is:

### A. Automated evidence

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### B. Complementary real-case evidence

- `phase5_eval/CV - Lucas -gen.json`

### C. Visual evidence

- two screenshots from `PASS` cases
- one screenshot from a scan-like `WARN` case
- one screenshot from a difficult edge case

### D. Curated screenshot inputs

- `phase5_eval/ui_examples_manifest.json`
- `docs/PHASE_5_UI_EXAMPLES_GUIDE.md`

---

## 6. Suggested documentation summary

### Short version

> Phase 5 was validated through a reproducible local smoke evaluation covering `extraction`, `summary`, `checklist`, `cv_analysis`, and `code_analysis`, all with `PASS`. The repository also preserves real examples and curated UI cases to show success on textual documents, partial behavior on scan-like inputs, and known pipeline boundaries.

### Stronger engineering version

> The structured-output layer was not assessed only through manual inspection. It includes automated smoke evaluation, versioned real examples, selected UI cases, and explicit documentation of known limits. That makes the transition from open-ended chat to validated task outputs observable and reproducible.

---

## 7. Short commands to reproduce the evidence

Run the full smoke evaluation:

```bash
python scripts/run_phase5_structured_eval.py --task all
```

Open the latest report:

```bash
code phase5_eval/reports/phase5_structured_eval_20260319_082813.json
```

Open the saved Lucas case:

```bash
code "phase5_eval/CV - Lucas -gen.json"
```

Open the screenshot guide:

```bash
code docs/PHASE_5_UI_EXAMPLES_GUIDE.md
```

---

## 8. Conclusion

Today, the strongest combined evidence that the Phase 5 structured application layer works is:

1. an automated smoke evaluation with `PASS` across all main tasks
2. a versioned JSON report artifact
3. a versioned real-case output (`CV - Lucas -gen.json`)
4. a curated UI-example manifest for reproducible screenshots

This combination gives the phase a strong evidence base while keeping system limits explicit.