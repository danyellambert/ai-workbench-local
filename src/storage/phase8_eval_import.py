from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..evals.phase8_thresholds import EVIDENCE_CV_GOLD_THRESHOLDS
from .phase8_eval_store import append_eval_run


def _json_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _f1_score(field_score: dict[str, Any]) -> float:
    precision = float(field_score.get("precision") or 0.0)
    recall = float(field_score.get("recall") or 0.0)
    if precision + recall <= 0:
        return 0.0
    return round((2 * precision * recall) / (precision + recall), 4)


def _build_evidence_eval_entry(
    *,
    report_path: Path,
    gold_set: str,
    file_name: str,
    variant: str,
    variant_scores: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    email_f1 = _f1_score(variant_scores.get("emails") or {})
    phone_f1 = _f1_score(variant_scores.get("phones") or {})
    name_f1 = _f1_score(variant_scores.get("name") or {})
    location_f1 = _f1_score(variant_scores.get("location") or {})
    avg_f1 = round((email_f1 + phone_f1 + name_f1 + location_f1) / 4, 4)
    score = round(avg_f1 * 4, 3)

    status = "PASS"
    if avg_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("warn_min_avg_f1") or 0.65):
        status = "FAIL"
    elif avg_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("pass_min_avg_f1") or 0.9):
        status = "WARN"

    reasons: list[str] = []
    if email_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("email_f1_target") or 0.9):
        reasons.append(f"email_f1_below_target:{email_f1:.3f}")
    if phone_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("phone_f1_target") or 0.9):
        reasons.append(f"phone_f1_below_target:{phone_f1:.3f}")
    if name_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("name_f1_target") or 1.0):
        reasons.append(f"name_match_incomplete:{name_f1:.3f}")
    if location_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("location_f1_target") or 1.0):
        reasons.append(f"location_match_incomplete:{location_f1:.3f}")

    return {
        "created_at": _json_mtime_iso(report_path),
        "suite_name": "evidence_cv_gold_eval",
        "task_type": "cv_contacts",
        "case_name": file_name,
        "provider": "evidence_cv",
        "model": variant,
        "status": status,
        "score": score,
        "max_score": 4,
        "metrics": {
            "avg_f1": avg_f1,
            "email_f1": email_f1,
            "phone_f1": phone_f1,
            "name_f1": name_f1,
            "location_f1": location_f1,
        },
        "reasons": reasons,
        "metadata": {
            "source_report": str(report_path),
            "gold_set": gold_set,
            "variant": variant,
            "thresholds": EVIDENCE_CV_GOLD_THRESHOLDS,
        },
    }


def import_eval_history_reports(reports_dir: Path, db_path: Path) -> dict[str, int]:
    counts = {
        "structured_smoke_eval": 0,
        "structured_real_document_eval": 0,
        "checklist_regression": 0,
        "evidence_cv_gold_eval": 0,
        "document_agent_routing_eval": 0,
        "langgraph_workflow_eval": 0,
    }

    for report_path in sorted(reports_dir.glob("phase5_structured_eval_*.json")):
        payload = _read_json(report_path)
        if not payload:
            continue
        created_at = str(payload.get("generated_at") or _json_mtime_iso(report_path))
        provider = payload.get("provider")
        model = payload.get("model")
        for task_entry in payload.get("tasks") or []:
            if not isinstance(task_entry, dict):
                continue
            suite_name = str(task_entry.get("suite_name") or "structured_smoke_eval")
            row_id = append_eval_run(
                db_path,
                {
                    "created_at": created_at,
                    "suite_name": suite_name,
                    "task_type": str(task_entry.get("task") or "unknown"),
                    "case_name": f"fixture:{str(task_entry.get('task') or 'unknown')}",
                    "provider": provider,
                    "model": model,
                    "status": str(task_entry.get("status") or "UNKNOWN"),
                    "score": task_entry.get("score"),
                    "max_score": task_entry.get("max_score"),
                    "metrics": {
                        "success": bool(task_entry.get("success")),
                    },
                    "reasons": task_entry.get("reasons") or [],
                    "metadata": {
                        "source_report": str(report_path),
                        "validation_error": task_entry.get("validation_error"),
                        "parsing_error": task_entry.get("parsing_error"),
                    },
                },
            )
            if row_id:
                counts[suite_name] = counts.get(suite_name, 0) + 1

    for report_path in sorted(reports_dir.glob("checklist_regression_*.json")):
        payload = _read_json(report_path)
        if not payload:
            continue
        evaluation = payload.get("evaluation") if isinstance(payload.get("evaluation"), dict) else {}
        resolved_document = payload.get("resolved_document") if isinstance(payload.get("resolved_document"), dict) else {}
        row_id = append_eval_run(
            db_path,
            {
                "created_at": str(payload.get("generated_at") or _json_mtime_iso(report_path)),
                "suite_name": "checklist_regression",
                "task_type": "checklist",
                "case_name": str(resolved_document.get("name") or report_path.stem),
                "provider": payload.get("provider"),
                "model": payload.get("model"),
                "status": str(evaluation.get("status") or "UNKNOWN"),
                "score": evaluation.get("matched_items"),
                "max_score": evaluation.get("expected_items"),
                "needs_review": bool((payload.get("execution_metadata") or {}).get("needs_review")) if isinstance(payload.get("execution_metadata"), dict) else False,
                "context_strategy": payload.get("context_strategy"),
                "metrics": {
                    "coverage": evaluation.get("coverage"),
                    "duplicate_ids": len(evaluation.get("duplicate_ids") or []),
                    "artifact_items": len(evaluation.get("artifact_items") or []),
                    "collapsed_items": len(evaluation.get("collapsed_items") or []),
                    "style_issue_items": len(evaluation.get("style_issue_items") or []),
                },
                "reasons": evaluation.get("reasons") or [],
                "metadata": {
                    "source_report": str(report_path),
                    "fixture": payload.get("fixture"),
                    "document_id": resolved_document.get("document_id"),
                },
            },
        )
        if row_id:
            counts["checklist_regression"] += 1

    for report_path in sorted(reports_dir.glob("evidence_cv_eval_metrics*.json")):
        payload = _read_json(report_path)
        if not payload:
            continue
        gold_set = str(payload.get("gold_set") or "")
        for per_file_entry in payload.get("per_file") or []:
            if not isinstance(per_file_entry, dict):
                continue
            file_name = Path(str(per_file_entry.get("file") or report_path.stem)).name
            scores = per_file_entry.get("scores") if isinstance(per_file_entry.get("scores"), dict) else {}
            for variant, variant_scores in scores.items():
                if not isinstance(variant_scores, dict):
                    continue
                row_id = append_eval_run(
                    db_path,
                    _build_evidence_eval_entry(
                        report_path=report_path,
                        gold_set=gold_set,
                        file_name=file_name,
                        variant=str(variant),
                        variant_scores=variant_scores,
                    ),
                )
                if row_id:
                    counts["evidence_cv_gold_eval"] += 1

    for report_path in sorted(reports_dir.glob("phase8_agent_workflow_eval*.json")):
        payload = _read_json(report_path)
        if not payload:
            continue
        generated_at = str(payload.get("generated_at") or _json_mtime_iso(report_path))
        for result_key, suite_name in (("routing_results", "document_agent_routing_eval"), ("workflow_results", "langgraph_workflow_eval")):
            for item in payload.get(result_key) or []:
                if not isinstance(item, dict):
                    continue
                row_id = append_eval_run(
                    db_path,
                    {
                        "created_at": generated_at,
                        **item,
                        "suite_name": str(item.get("suite_name") or suite_name),
                        "metadata": {
                            **(item.get("metadata") if isinstance(item.get("metadata"), dict) else {}),
                            "source_report": str(report_path),
                        },
                    },
                )
                if row_id:
                    counts[suite_name] = counts.get(suite_name, 0) + 1

    return counts