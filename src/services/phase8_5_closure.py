from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..storage.phase8_eval_diagnosis import build_eval_diagnosis
from ..storage.phase8_eval_store import load_eval_runs, summarize_eval_runs
from .phase8_5_audit import build_phase8_5_audit
from .phase8_5_decision_gate import (
    build_phase8_5_decision_summary,
    find_latest_phase8_5_run_dir,
    load_phase8_5_benchmark_artifacts,
)


class AdaptationQualitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pass_rate: float | None = None
    fail_rate: float | None = None
    avg_score_ratio: float | None = None


class AdaptationTargetQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_avg_score_ratio: float | None = None
    target_fail_rate_max: float | None = None


class MinimalAdaptationExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experiment_type: str
    task_scope: str
    primary_success_metric: str
    baseline_quality: AdaptationQualitySnapshot
    target_quality: AdaptationTargetQuality
    scope_constraints: list[str] = Field(default_factory=list)


class AdaptationCandidateScaffold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: str
    failure_pattern: list[str] = Field(default_factory=list)
    current_baseline_quality: AdaptationQualitySnapshot
    adaptation_priority: str | None = None
    non_training_alternatives_remaining: list[str] = Field(default_factory=list)
    why_prompt_rag_retrieval_changes_were_not_enough: str
    minimal_lora_peft_experiment: MinimalAdaptationExperiment
    recommended_action: str | None = None


def build_adaptation_scaffold_rows(decision_summary: dict[str, object]) -> list[dict[str, object]]:
    adaptation = decision_summary.get("adaptation_decision") if isinstance(decision_summary.get("adaptation_decision"), dict) else {}
    rows: list[dict[str, object]] = []
    for item in adaptation.get("adaptation_candidates") or []:
        if not isinstance(item, dict):
            continue
        model = AdaptationCandidateScaffold(
            task_type=str(item.get("task_type") or "unknown"),
            failure_pattern=[str(reason) for reason in (item.get("failure_pattern") or []) if str(reason).strip()],
            current_baseline_quality=AdaptationQualitySnapshot.model_validate(item.get("current_baseline_quality") or {}),
            adaptation_priority=str(item.get("adaptation_priority") or "").strip() or None,
            non_training_alternatives_remaining=[
                str(value) for value in (item.get("non_training_alternatives_remaining") or []) if str(value).strip()
            ],
            why_prompt_rag_retrieval_changes_were_not_enough=str(
                item.get("why_prompt_rag_retrieval_changes_were_not_enough") or ""
            ).strip(),
            minimal_lora_peft_experiment=MinimalAdaptationExperiment.model_validate(
                item.get("minimal_lora_peft_experiment") or {}
            ),
            recommended_action=str(item.get("recommended_action") or "").strip() or None,
        )
        rows.append(model.model_dump(exclude_none=True))
    return rows


def build_phase8_5_closure_summary(
    *,
    audit_summary: dict[str, object],
    decision_summary: dict[str, object],
) -> dict[str, object]:
    support = audit_summary.get("support_status") if isinstance(audit_summary.get("support_status"), dict) else {}
    adaptation_scaffolds = build_adaptation_scaffold_rows(decision_summary)
    fully_supported: list[str] = []
    partially_supported: list[str] = []

    if (support.get("round0") or {}).get("implemented"):
        fully_supported.append("round0_audit_preflight_layer")
    if (support.get("round1") or {}).get("implemented"):
        fully_supported.append("round1_generation_embeddings_workflow")
    if (support.get("round2") or {}).get("implemented"):
        if (support.get("round2") or {}).get("evidence_bundle_complete"):
            fully_supported.append("round2_reranker_ocr_vlm_workflow")
        else:
            partially_supported.append("round2_reranker_ocr_vlm_evidence_bundle_in_latest_run")
    if (support.get("round3") or {}).get("implemented"):
        fully_supported.append("round3_decision_gate_layer")

    all_rounds_fully_supported = not partially_supported and {
        "round0_audit_preflight_layer",
        "round1_generation_embeddings_workflow",
        "round2_reranker_ocr_vlm_workflow",
        "round3_decision_gate_layer",
    }.issubset(set(fully_supported))

    phase_status = (
        "phase8_5_fully_closed_local_execution_complete"
        if all_rounds_fully_supported
        else "phase8_5_technically_closed_with_explicit_support_boundaries"
        if fully_supported
        else "phase8_5_closure_not_ready"
    )

    runtime_model = decision_summary.get("runtime_model_decisions") if isinstance(decision_summary.get("runtime_model_decisions"), dict) else {}
    embedding = decision_summary.get("embedding_decisions") if isinstance(decision_summary.get("embedding_decisions"), dict) else {}
    reranker = decision_summary.get("reranker_decisions") if isinstance(decision_summary.get("reranker_decisions"), dict) else {}
    ocr_vlm = decision_summary.get("ocr_vlm_observations") if isinstance(decision_summary.get("ocr_vlm_observations"), dict) else {}

    return {
        "phase": "8.5",
        "closure_version": "phase8_5_closure.v1",
        "phase_status": phase_status,
        "benchmark_run_dir": audit_summary.get("benchmark_run_dir"),
        "benchmark_run_id": audit_summary.get("benchmark_run_id"),
        "fully_supported": fully_supported,
        "partially_supported": partially_supported,
        "not_in_scope": [
            "full_fine_tuning_jobs",
            "heavy_lora_peft_training_execution",
            "new_runtime_families_not_cleanly_supported_in_repo",
        ],
        "recommended_stack": {
            "best_local_runtime_by_use_case": runtime_model.get("best_local_runtime_by_use_case") or [],
            "best_embedding_strategy": embedding.get("best_embedding_strategy"),
            "best_reranker_tradeoff": reranker.get("best_reranker_tradeoff"),
            "best_ocr_tradeoff": ocr_vlm.get("best_ocr_tradeoff"),
            "best_vlm_tradeoff": ocr_vlm.get("best_vlm_tradeoff"),
        },
        "adaptation_scaffolds": adaptation_scaffolds,
        "audit_summary": audit_summary,
        "decision_summary": decision_summary,
    }


def build_phase8_5_closure_bundle(
    *,
    project_root: str | Path,
    benchmark_run_dir: str | Path | None = None,
    eval_db_path: str | Path | None = None,
) -> dict[str, object]:
    resolved_root = Path(project_root)
    resolved_run_dir = Path(benchmark_run_dir) if benchmark_run_dir else find_latest_phase8_5_run_dir(resolved_root)
    audit = build_phase8_5_audit(
        project_root=resolved_root,
        benchmark_run_dir=resolved_run_dir,
        eval_db_path=eval_db_path,
    )
    artifacts = (
        load_phase8_5_benchmark_artifacts(resolved_run_dir)
        if resolved_run_dir is not None
        else {"summary": {}, "events": [], "manifest": {}, "preflight": {}}
    )
    resolved_eval_db = Path(eval_db_path) if eval_db_path else resolved_root / ".phase8_eval_runs.sqlite3"
    eval_entries = load_eval_runs(resolved_eval_db)
    decision = build_phase8_5_decision_summary(
        benchmark_summary=artifacts.get("summary") if isinstance(artifacts.get("summary"), dict) else {},
        benchmark_events=[item for item in (artifacts.get("events") or []) if isinstance(item, dict)],
        manifest=artifacts.get("manifest") if isinstance(artifacts.get("manifest"), dict) else {},
        preflight=artifacts.get("preflight") if isinstance(artifacts.get("preflight"), dict) else {},
        eval_summary=summarize_eval_runs(eval_entries),
        eval_diagnosis=build_eval_diagnosis(eval_entries),
        benchmark_run_dir=str(resolved_run_dir) if resolved_run_dir else None,
    )
    return build_phase8_5_closure_summary(audit_summary=audit, decision_summary=decision)


def render_phase8_5_closure_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Phase 8.5 Closure Report",
        "",
        f"- Phase status: `{summary.get('phase_status') or 'n/a'}`",
        f"- Benchmark run id: `{summary.get('benchmark_run_id') or 'n/a'}`",
        f"- Benchmark run dir: `{summary.get('benchmark_run_dir') or 'n/a'}`",
        "",
        "## Fully supported now",
        "",
    ]
    fully_supported = [str(item) for item in (summary.get("fully_supported") or []) if str(item).strip()]
    partially_supported = [str(item) for item in (summary.get("partially_supported") or []) if str(item).strip()]
    if not fully_supported:
        lines.append("- No fully supported closure slice was detected.")
    else:
        for item in fully_supported:
            lines.append(f"- `{item}`")

    lines.extend(["", "## Partially supported / explicitly bounded", ""])
    if not partially_supported:
        lines.append("- No partial closure boundaries were detected in the current summary.")
    else:
        for item in partially_supported:
            lines.append(f"- `{item}`")

    lines.extend(["", "## Recommended stack from the current evidence", ""])
    for item in ((summary.get("recommended_stack") or {}).get("best_local_runtime_by_use_case") or []):
        if not isinstance(item, dict):
            continue
        best_local = item.get("best_local_candidate") if isinstance(item.get("best_local_candidate"), dict) else {}
        lines.append(
            f"- `{item.get('use_case_id')}` → `{best_local.get('candidate') or 'n/a'}`"
        )
    lines.append(
        f"- Best embedding strategy: `{((((summary.get('recommended_stack') or {}).get('best_embedding_strategy')) or {}).get('candidate')) or 'n/a'}`"
    )
    lines.append(
        f"- Best reranker tradeoff: `{((((summary.get('recommended_stack') or {}).get('best_reranker_tradeoff')) or {}).get('candidate_id')) or 'n/a'}`"
    )
    lines.append(
        f"- Best OCR fallback tradeoff: `{((((summary.get('recommended_stack') or {}).get('best_ocr_tradeoff')) or {}).get('variant')) or 'n/a'}`"
    )
    lines.append(
        f"- Best VLM fallback tradeoff: `{((((summary.get('recommended_stack') or {}).get('best_vlm_tradeoff')) or {}).get('variant')) or 'n/a'}`"
    )

    lines.extend(["", "## Adaptation scaffolds", ""])
    scaffolds = [item for item in (summary.get("adaptation_scaffolds") or []) if isinstance(item, dict)]
    if not scaffolds:
        lines.append("- No adaptation scaffold is required from the current evidence bundle.")
    else:
        for item in scaffolds:
            experiment = item.get("minimal_lora_peft_experiment") if isinstance(item.get("minimal_lora_peft_experiment"), dict) else {}
            lines.append(
                f"- `{item.get('task_type')}` → future experiment `{experiment.get('experiment_type')}` with primary metric `{experiment.get('primary_success_metric')}`"
            )

    lines.extend(
        [
            "",
            "## Honest closure notes",
            "",
            "- This closure keeps the phase conservative and interview-defendable.",
            "- Full fine-tuning is still out of scope; only a scaffold is recorded when the evidence justifies it.",
            "- If the latest benchmark run does not yet include all Round 2 groups, the closure report keeps that boundary explicit instead of inventing results.",
            "",
        ]
    )
    return "\n".join(lines)