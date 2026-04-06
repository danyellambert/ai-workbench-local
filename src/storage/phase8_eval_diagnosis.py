from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..evals.phase8_thresholds import DIAGNOSIS_THRESHOLDS


ADAPTATION_ELIGIBLE_TASKS = {
    "extraction",
    "checklist",
    "cv_contacts",
    "intent_classification",
    "classification",
    "reranking",
}


def _score_ratio(entry: dict[str, Any]) -> float | None:
    score = entry.get("score")
    max_score = entry.get("max_score")
    if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and float(max_score) > 0:
        return round(float(score) / float(max_score), 4)
    return None


def _status_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for entry in entries:
        counter[str(entry.get("status") or "UNKNOWN").upper()] += 1
    return dict(counter)


def _task_health_label(*, pass_rate: float, fail_rate: float, avg_score_ratio: float) -> str:
    if (
        pass_rate >= float(DIAGNOSIS_THRESHOLDS.get("healthy_pass_rate") or 0.75)
        and fail_rate <= float(DIAGNOSIS_THRESHOLDS.get("healthy_fail_rate") or 0.15)
        and avg_score_ratio >= float(DIAGNOSIS_THRESHOLDS.get("healthy_avg_score_ratio") or 0.8)
    ):
        return "healthy"
    if (
        pass_rate >= float(DIAGNOSIS_THRESHOLDS.get("monitor_pass_rate") or 0.6)
        and fail_rate <= float(DIAGNOSIS_THRESHOLDS.get("monitor_fail_rate") or 0.3)
        and avg_score_ratio >= float(DIAGNOSIS_THRESHOLDS.get("monitor_avg_score_ratio") or 0.7)
    ):
        return "monitor"
    return "needs_iteration"


def _adaptation_priority(task_type: str, *, total_runs: int, fail_rate: float, avg_score_ratio: float) -> str | None:
    if task_type not in ADAPTATION_ELIGIBLE_TASKS:
        return None
    if (
        total_runs >= int(DIAGNOSIS_THRESHOLDS.get("adaptation_high_min_runs") or 5)
        and fail_rate >= float(DIAGNOSIS_THRESHOLDS.get("adaptation_high_fail_rate") or 0.6)
        and avg_score_ratio < float(DIAGNOSIS_THRESHOLDS.get("adaptation_high_avg_score_ratio") or 0.65)
    ):
        return "high"
    if (
        total_runs >= int(DIAGNOSIS_THRESHOLDS.get("adaptation_medium_min_runs") or 5)
        and fail_rate >= float(DIAGNOSIS_THRESHOLDS.get("adaptation_medium_fail_rate") or 0.3)
        and avg_score_ratio < float(DIAGNOSIS_THRESHOLDS.get("adaptation_medium_avg_score_ratio") or 0.72)
    ):
        return "medium"
    return None


def _recommended_action(task_type: str, top_reasons: list[dict[str, Any]], health_label: str, adaptation_priority: str | None) -> str:
    reason_keys = {str(item.get("reason") or "") for item in top_reasons}
    if health_label == "healthy":
        return "prompt_rag_stack_currently_sufficient"
    if "collapsed items detected: 1" in reason_keys or any("collapsed items detected" in reason for reason in reason_keys):
        return "improve_checklist_decomposition_and_source_alignment"
    if any("email_f1_below_target" in reason or "phone_f1_below_target" in reason for reason in reason_keys):
        return "improve_ocr_router_contact_postprocessing_before_model_adaptation"
    if any("location_match_incomplete" in reason or "name_match_incomplete" in reason for reason in reason_keys):
        return "improve_grounding_and_field_resolution_before_model_adaptation"
    if adaptation_priority == "high":
        return "consider_task_specific_model_adaptation_after_more_eval_cases"
    if task_type in {"summary", "cv_analysis", "code_analysis"}:
        return "continue_prompt_grounding_and_schema_iteration"
    return "expand_eval_cases_and_iterate_prompt_rag_schema"


def build_eval_diagnosis(entries: list[dict[str, Any]], *, recent_window: int = 10) -> dict[str, Any]:
    if not entries:
        return {
            "total_runs": 0,
            "top_failure_reasons": [],
            "task_diagnosis": [],
            "persistent_failure_tasks": [],
            "adaptation_candidates": [],
            "healthy_tasks": [],
            "decision_summary": {
                "global_recommendation": "insufficient_eval_data",
                "prompt_rag_sufficient_tasks": [],
                "iteration_before_adaptation_tasks": [],
                "adaptation_candidate_tasks": [],
                "next_eval_priorities": [],
            },
        }

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failure_reason_counter: Counter[str] = Counter()

    for entry in entries:
        grouped[str(entry.get("task_type") or "unknown")].append(entry)
        for reason in entry.get("reasons") or []:
            reason_text = str(reason or "").strip()
            if reason_text:
                failure_reason_counter[reason_text] += 1

    task_diagnosis: list[dict[str, Any]] = []
    persistent_failure_tasks: list[dict[str, Any]] = []
    adaptation_candidates: list[dict[str, Any]] = []
    healthy_tasks: list[dict[str, Any]] = []

    for task_type, task_entries in grouped.items():
        ordered_entries = sorted(task_entries, key=lambda item: (str(item.get("created_at") or ""), int(item.get("id") or 0)), reverse=True)
        total_runs = len(ordered_entries)
        status_counts = _status_counts(ordered_entries)
        pass_rate = round(status_counts.get("PASS", 0) / max(total_runs, 1), 3)
        warn_rate = round(status_counts.get("WARN", 0) / max(total_runs, 1), 3)
        fail_rate = round(status_counts.get("FAIL", 0) / max(total_runs, 1), 3)
        score_ratios = [ratio for ratio in (_score_ratio(entry) for entry in ordered_entries) if ratio is not None]
        avg_score_ratio = round(sum(score_ratios) / max(len(score_ratios), 1), 3) if score_ratios else 0.0
        recent_entries = ordered_entries[: max(1, recent_window)]
        recent_status_counts = _status_counts(recent_entries)
        recent_fail_rate = round(recent_status_counts.get("FAIL", 0) / max(len(recent_entries), 1), 3)

        task_reason_counter: Counter[str] = Counter()
        for entry in ordered_entries:
            for reason in entry.get("reasons") or []:
                reason_text = str(reason or "").strip()
                if reason_text:
                    task_reason_counter[reason_text] += 1
        top_reasons = [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                task_reason_counter.items(),
                key=lambda item: (int(item[1]), str(item[0])),
                reverse=True,
            )[:5]
        ]

        health_label = _task_health_label(
            pass_rate=pass_rate,
            fail_rate=fail_rate,
            avg_score_ratio=avg_score_ratio,
        )
        adaptation_priority = _adaptation_priority(
            task_type,
            total_runs=total_runs,
            fail_rate=fail_rate,
            avg_score_ratio=avg_score_ratio,
        )
        recommendation = _recommended_action(task_type, top_reasons, health_label, adaptation_priority)

        row = {
            "task_type": task_type,
            "total_runs": total_runs,
            "pass_rate": pass_rate,
            "warn_rate": warn_rate,
            "fail_rate": fail_rate,
            "recent_fail_rate": recent_fail_rate,
            "avg_score_ratio": avg_score_ratio,
            "health_label": health_label,
            "adaptation_priority": adaptation_priority,
            "recommended_action": recommendation,
            "top_reasons": top_reasons,
        }
        task_diagnosis.append(row)

        if health_label == "healthy":
            healthy_tasks.append(row)
        if total_runs >= int(DIAGNOSIS_THRESHOLDS.get("persistent_failure_min_runs") or 3) and (
            fail_rate >= float(DIAGNOSIS_THRESHOLDS.get("persistent_failure_fail_rate") or 0.3)
            or recent_fail_rate >= float(DIAGNOSIS_THRESHOLDS.get("persistent_failure_recent_fail_rate") or 0.4)
        ):
            persistent_failure_tasks.append(row)
        if adaptation_priority is not None:
            adaptation_candidates.append(row)

    task_diagnosis.sort(
        key=lambda item: (
            -float(item.get("fail_rate") or 0.0),
            float(item.get("avg_score_ratio") or 1.0),
            -int(item.get("total_runs") or 0),
        )
    )
    healthy_tasks.sort(key=lambda item: (-float(item.get("pass_rate") or 0.0), -float(item.get("avg_score_ratio") or 0.0)))
    persistent_failure_tasks.sort(key=lambda item: (-float(item.get("fail_rate") or 0.0), float(item.get("avg_score_ratio") or 1.0)))
    adaptation_candidates.sort(
        key=lambda item: (
            {"high": 0, "medium": 1, None: 2}.get(item.get("adaptation_priority"), 2),
            -float(item.get("fail_rate") or 0.0),
        )
    )

    decision_summary = {
        "global_recommendation": (
            "consider_targeted_adaptation_only_for_specific_tasks"
            if adaptation_candidates
            else "prompt_rag_schema_iteration_still_sufficient_globally"
        ),
        "prompt_rag_sufficient_tasks": [
            {
                "task_type": item["task_type"],
                "pass_rate": item["pass_rate"],
                "avg_score_ratio": item["avg_score_ratio"],
            }
            for item in healthy_tasks
        ],
        "iteration_before_adaptation_tasks": [
            {
                "task_type": item["task_type"],
                "recommended_action": item["recommended_action"],
                "fail_rate": item["fail_rate"],
                "avg_score_ratio": item["avg_score_ratio"],
            }
            for item in persistent_failure_tasks
            if item.get("adaptation_priority") is None
        ],
        "adaptation_candidate_tasks": [
            {
                "task_type": item["task_type"],
                "adaptation_priority": item["adaptation_priority"],
                "fail_rate": item["fail_rate"],
                "avg_score_ratio": item["avg_score_ratio"],
                "recommended_action": item["recommended_action"],
            }
            for item in adaptation_candidates
        ],
        "next_eval_priorities": [
            {
                "task_type": item["task_type"],
                "fail_rate": item["fail_rate"],
                "recent_fail_rate": item["recent_fail_rate"],
                "recommended_action": item["recommended_action"],
            }
            for item in persistent_failure_tasks[:5]
        ],
    }

    return {
        "total_runs": len(entries),
        "top_failure_reasons": [
            {"reason": reason, "count": count}
            for reason, count in failure_reason_counter.most_common(10)
        ],
        "task_diagnosis": task_diagnosis,
        "persistent_failure_tasks": persistent_failure_tasks,
        "adaptation_candidates": adaptation_candidates,
        "healthy_tasks": healthy_tasks,
        "decision_summary": decision_summary,
    }