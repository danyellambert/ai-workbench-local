from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.product.models import ProductWorkflowResult
from src.storage.phase8_eval_store import append_eval_run
from src.storage.runtime_paths import get_phase8_eval_db_path
from src.app.product_bootstrap import ProductBootstrap

WORKFLOW_EVAL_EXPECTATIONS: dict[str, dict[str, Any]] = {
    'document_review': {
        'required_highlights': 2,
        'require_recommendation': True,
        'min_documents': 1,
        'require_grounding': True,
    },
    'policy_contract_comparison': {
        'required_highlights': 2,
        'require_recommendation': True,
        'min_documents': 2,
        'require_grounding': True,
    },
    'action_plan_evidence_review': {
        'required_highlights': 1,
        'require_recommendation': True,
        'min_documents': 1,
        'require_grounding': True,
        'require_actions': True,
    },
    'candidate_review': {
        'required_highlights': 2,
        'require_recommendation': True,
        'min_documents': 1,
        'require_grounding': True,
    },
}

LIVE_EVAL_SOURCE = 'product_runtime_eval'
HISTORICAL_BACKFILL_SOURCE = 'product_history_backfill'


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except Exception:
        return default


def _normalize_status(value: Any) -> str:
    normalized = str(value or '').strip().lower()
    return normalized or 'unknown'


def _collect_action_entries(telemetry_run: dict[str, Any]) -> list[dict[str, Any]]:
    lineage = telemetry_run.get('lineage') if isinstance(telemetry_run.get('lineage'), dict) else {}
    actions = lineage.get('evidenceops_actions') if isinstance(lineage.get('evidenceops_actions'), list) else []
    return [item for item in actions if isinstance(item, dict)]


def _collect_delivery_entries(telemetry_run: dict[str, Any]) -> list[dict[str, Any]]:
    lineage = telemetry_run.get('lineage') if isinstance(telemetry_run.get('lineage'), dict) else {}
    deliveries = lineage.get('deliveries') if isinstance(lineage.get('deliveries'), list) else []
    return [item for item in deliveries if isinstance(item, dict)]


def _compute_eval_status(score_ratio: float, *, hard_fail: bool = False) -> str:
    if hard_fail or score_ratio < 0.5:
        return 'FAIL'
    if score_ratio < 0.8:
        return 'WARN'
    return 'PASS'


def _base_metadata(telemetry_run: dict[str, Any], *, source: str) -> dict[str, Any]:
    runtime = telemetry_run.get('runtime') if isinstance(telemetry_run.get('runtime'), dict) else {}
    routing = telemetry_run.get('routing') if isinstance(telemetry_run.get('routing'), dict) else {}
    return {
        'source': source,
        'run_id': telemetry_run.get('run_id'),
        'trace_id': telemetry_run.get('trace_id'),
        'workflow_id': telemetry_run.get('workflow_id'),
        'surface': telemetry_run.get('surface'),
        'provider': runtime.get('provider'),
        'model': runtime.get('model'),
        'context_strategy': routing.get('context_strategy'),
        'execution_strategy_used': routing.get('execution_strategy_used'),
    }


def evaluate_product_runtime_run(
    telemetry_run: dict[str, Any],
    *,
    result: ProductWorkflowResult | None = None,
    source: str = LIVE_EVAL_SOURCE,
) -> list[dict[str, Any]]:
    workflow_id = str(telemetry_run.get('workflow_id') or '').strip()
    if not workflow_id:
        return []

    expectations = WORKFLOW_EVAL_EXPECTATIONS.get(workflow_id, {})
    runtime = telemetry_run.get('runtime') if isinstance(telemetry_run.get('runtime'), dict) else {}
    summary_block = telemetry_run.get('summary') if isinstance(telemetry_run.get('summary'), dict) else {}
    request = telemetry_run.get('request') if isinstance(telemetry_run.get('request'), dict) else {}
    routing = telemetry_run.get('routing') if isinstance(telemetry_run.get('routing'), dict) else {}

    summary_text = str(summary_block.get('summary') or '').strip()
    highlights = [str(item).strip() for item in (summary_block.get('highlights') or []) if str(item or '').strip()]
    recommendation = str(summary_block.get('recommendation') or '').strip()
    warnings = [str(item).strip() for item in (summary_block.get('warnings') or []) if str(item or '').strip()]
    grounding = summary_block.get('grounding_preview') if isinstance(summary_block.get('grounding_preview'), dict) else {}
    document_count = len(request.get('document_ids') or [])
    source_count = _safe_int(runtime.get('retrieved_chunks_count') or grounding.get('source_block_count') or 0)
    context_chars = _safe_int(runtime.get('context_chars') or grounding.get('context_chars') or 0)
    total_tokens = _safe_int(runtime.get('total_tokens') or 0)
    action_entries = _collect_action_entries(telemetry_run)
    deliveries = _collect_delivery_entries(telemetry_run)
    open_action_count = sum(1 for item in action_entries if str(item.get('status') or '').strip().lower() not in {'done', 'closed', 'resolved', 'completed'})
    due_date_count = sum(1 for item in action_entries if str(item.get('due_date') or '').strip())
    owner_count = sum(1 for item in action_entries if str(item.get('owner') or '').strip())

    common_reasons: list[str] = []
    if warnings:
        common_reasons.extend(warnings[:2])
    if telemetry_run.get('review_reason'):
        common_reasons.insert(0, str(telemetry_run.get('review_reason')))
    if telemetry_run.get('error_message'):
        common_reasons.insert(0, str(telemetry_run.get('error_message')))

    created_at = str(telemetry_run.get('completed_at') or telemetry_run.get('started_at') or _now_iso())
    provider = runtime.get('provider')
    model = runtime.get('model')
    latency_s = runtime.get('latency_s')
    context_strategy = routing.get('context_strategy')
    needs_review = bool(telemetry_run.get('needs_review'))
    max_score = 100.0

    eval_rows: list[dict[str, Any]] = []

    # Contract completeness
    contract_points = 0
    contract_total = 0
    contract_reasons: list[str] = []
    if summary_text:
        contract_points += 1
    else:
        contract_reasons.append('Missing workflow summary.')
    contract_total += 1

    if expectations.get('require_recommendation'):
        contract_total += 1
        if recommendation:
            contract_points += 1
        else:
            contract_reasons.append('Missing explicit recommendation.')

    required_highlights = _safe_int(expectations.get('required_highlights') or 0)
    if required_highlights > 0:
        contract_total += 1
        if len(highlights) >= required_highlights:
            contract_points += 1
        else:
            contract_reasons.append(f'Only {len(highlights)} highlight(s); expected at least {required_highlights}.')

    min_documents = _safe_int(expectations.get('min_documents') or 0)
    if min_documents > 0:
        contract_total += 1
        if document_count >= min_documents:
            contract_points += 1
        else:
            contract_reasons.append(f'Only {document_count} selected document(s); expected at least {min_documents}.')

    if expectations.get('require_actions'):
        contract_total += 1
        if action_entries:
            contract_points += 1
        else:
            contract_reasons.append('No extracted action items or evidenceops actions were attached to the run.')

    contract_ratio = contract_points / max(contract_total, 1)
    eval_rows.append({
        'created_at': created_at,
        'suite_name': 'product_workflow_contract_eval',
        'task_type': workflow_id,
        'case_name': f"{telemetry_run.get('run_id')}::contract",
        'provider': provider,
        'model': model,
        'status': _compute_eval_status(contract_ratio, hard_fail=_normalize_status(telemetry_run.get('status')) == 'error'),
        'score': round(contract_ratio * max_score, 2),
        'max_score': max_score,
        'quality_score': round(contract_ratio, 4),
        'overall_confidence': _safe_float((getattr(result.structured_result, 'overall_confidence', None) if result is not None and result.structured_result is not None else summary_block.get('overall_confidence')) or 0.0),
        'latency_s': latency_s,
        'needs_review': needs_review or contract_ratio < 0.8,
        'context_strategy': context_strategy,
        'metrics': {
            'summary_present': bool(summary_text),
            'highlight_count': len(highlights),
            'recommendation_present': bool(recommendation),
            'document_count': document_count,
            'action_count': len(action_entries),
        },
        'reasons': contract_reasons or common_reasons,
        'metadata': {
            **_base_metadata(telemetry_run, source=source),
            'eval_dimension': 'contract',
        },
        'run_key': f"{source}::{telemetry_run.get('run_id')}::contract",
    })

    # Grounding quality
    grounding_points = 0
    grounding_total = 0
    grounding_reasons: list[str] = []
    grounding_total += 1
    if source_count > 0:
        grounding_points += 1
    else:
        grounding_reasons.append('No grounded source blocks were recorded for this run.')
    grounding_total += 1
    if context_chars > 0:
        grounding_points += 1
    else:
        grounding_reasons.append('No grounded context_chars were recorded for this run.')
    grounding_total += 1
    if document_count > 0 or not expectations.get('require_grounding'):
        grounding_points += 1
    else:
        grounding_reasons.append('No selected documents were attached to the run.')
    if expectations.get('require_grounding'):
        grounding_total += 1
        if bool(summary_block.get('grounding_preview')) or bool(runtime.get('retrieved_chunks_count')):
            grounding_points += 1
        else:
            grounding_reasons.append('Grounding preview is missing.')

    grounding_ratio = grounding_points / max(grounding_total, 1)
    eval_rows.append({
        'created_at': created_at,
        'suite_name': 'product_workflow_grounding_eval',
        'task_type': workflow_id,
        'case_name': f"{telemetry_run.get('run_id')}::grounding",
        'provider': provider,
        'model': model,
        'status': _compute_eval_status(grounding_ratio, hard_fail=_normalize_status(telemetry_run.get('status')) == 'error' and source_count <= 0),
        'score': round(grounding_ratio * max_score, 2),
        'max_score': max_score,
        'quality_score': round(grounding_ratio, 4),
        'overall_confidence': None,
        'latency_s': runtime.get('retrieval_latency_s') or latency_s,
        'needs_review': needs_review or grounding_ratio < 0.8,
        'context_strategy': context_strategy,
        'metrics': {
            'source_count': source_count,
            'context_chars': context_chars,
            'document_count': document_count,
            'total_tokens': total_tokens,
        },
        'reasons': grounding_reasons or common_reasons,
        'metadata': {
            **_base_metadata(telemetry_run, source=source),
            'eval_dimension': 'grounding',
        },
        'run_key': f"{source}::{telemetry_run.get('run_id')}::grounding",
    })

    # Actionability / operational readiness
    action_points = 0
    action_total = 0
    action_reasons: list[str] = []
    action_total += 1
    if recommendation:
        action_points += 1
    else:
        action_reasons.append('No recommendation was captured for operational follow-up.')
    action_total += 1
    if highlights:
        action_points += 1
    else:
        action_reasons.append('No highlights were captured to justify next steps.')
    if workflow_id == 'action_plan_evidence_review':
        action_total += 2
        if open_action_count > 0:
            action_points += 1
        else:
            action_reasons.append('Action plan run did not create open follow-up items.')
        if owner_count > 0 or due_date_count > 0:
            action_points += 1
        else:
            action_reasons.append('Action plan items are missing owners and due dates.')
    else:
        action_total += 1
        if deliveries or needs_review or recommendation:
            action_points += 1
        else:
            action_reasons.append('Run has no delivery or operator-ready signal yet.')

    action_ratio = action_points / max(action_total, 1)
    eval_rows.append({
        'created_at': created_at,
        'suite_name': 'product_workflow_actionability_eval',
        'task_type': workflow_id,
        'case_name': f"{telemetry_run.get('run_id')}::actionability",
        'provider': provider,
        'model': model,
        'status': _compute_eval_status(action_ratio, hard_fail=_normalize_status(telemetry_run.get('status')) == 'error' and not recommendation),
        'score': round(action_ratio * max_score, 2),
        'max_score': max_score,
        'quality_score': round(action_ratio, 4),
        'overall_confidence': None,
        'latency_s': latency_s,
        'needs_review': needs_review or action_ratio < 0.8,
        'context_strategy': context_strategy,
        'metrics': {
            'delivery_count': len(deliveries),
            'open_action_count': open_action_count,
            'owner_count': owner_count,
            'due_date_count': due_date_count,
        },
        'reasons': action_reasons or common_reasons,
        'metadata': {
            **_base_metadata(telemetry_run, source=source),
            'eval_dimension': 'actionability',
        },
        'run_key': f"{source}::{telemetry_run.get('run_id')}::actionability",
    })

    return eval_rows


def persist_product_runtime_evals(
    *,
    bootstrap: ProductBootstrap,
    telemetry_run: dict[str, Any],
    result: ProductWorkflowResult | None = None,
    source: str = LIVE_EVAL_SOURCE,
) -> list[int]:
    db_path = get_phase8_eval_db_path(bootstrap.workspace_root)
    inserted: list[int] = []
    for row in evaluate_product_runtime_run(telemetry_run, result=result, source=source):
        inserted.append(append_eval_run(db_path, row))
    return inserted
