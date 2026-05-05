# Phase 8 — Eval Operating Rhythm

This document defines a lightweight operating routine for using evals continuously instead of only when something breaks.

## 1. Deterministic baseline after logic/routing changes

Run when you touch:

- routing heuristics
- LangGraph guardrails / retry logic
- runtime snapshot / eval diagnosis logic

Commands:

```bash
python -m unittest tests.test_phase8_eval_store_unittest tests.test_phase8_eval_diagnosis_unittest tests.test_phase8_agent_workflow_eval_unittest tests.test_runtime_snapshot_unittest tests.test_phase5_real_document_eval_unittest
python scripts/run_phase8_agent_workflow_eval.py
python scripts/report_phase8_eval_store.py --limit 20
python scripts/report_phase8_eval_diagnosis.py
```

## 2. Real-document eval cycle after prompt / RAG / schema changes

Run when you touch:

- prompts
- document grounding
- extraction / summary / cv-analysis repair logic
- checklist generation behavior

Recommended commands:

```bash
python scripts/run_phase5_structured_eval.py --task summary --use-indexed-document --document-name "fy25-afr-final-tagged.pdf"
python scripts/run_phase5_structured_eval.py --task summary --use-indexed-document --document-name "asap-2025-annual-report-tagged.pdf"
python scripts/run_phase5_structured_eval.py --task extraction --use-indexed-document --document-name "exhib101.pdf"
python scripts/run_phase5_structured_eval.py --task extraction --use-indexed-document --document-name "exhibit10-3.pdf"
python scripts/evaluate_checklist_regression.py --document-name "9789241598590_eng.pdf"
python scripts/evaluate_evidence_cv_gold_set.py
python scripts/report_phase8_eval_store.py --limit 50
python scripts/report_phase8_eval_diagnosis.py
```

If the local environment is already prepared with provider + RAG + documents, you can also use the consolidated live runner:

```bash
python scripts/run_phase8_live_evals.py --preflight-only
python scripts/run_phase8_live_evals.py --limit-structured-docs 3
```

This is the recommended entrypoint for self-hosted/manual CI-like validation of environment-dependent evals.

## 3. What to inspect in the diagnosis

After each cycle, check:

- `top_failure_reasons`
- `healthy_tasks`
- `adaptation_candidates`
- `next_eval_priorities`

Interpretation:

- if a task is healthy repeatedly, prompt + RAG are probably sufficient for now
- if a task fails persistently, keep iterating prompt / grounding / schema first
- if a task remains poor after repeated iteration, it may become a Phase 8.5 candidate

## 4. Human review expectations

For every new real-document gold set:

1. read the source document manually
2. define the minimum grounded facts that must appear
3. tolerate wording variation, but not factual omission or hallucination
4. add notes explaining what should be rewarded and what should be penalized

## 5. When to escalate to Phase 8.5

Escalate only when:

- the task has enough eval volume
- failures are persistent
- prompt + grounding + schema iteration stopped helping materially

Only then test:

- better embedding models
- rerankers
- Hugging Face runtimes
- targeted adaptation / LoRA / PEFT