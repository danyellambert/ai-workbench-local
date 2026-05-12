from __future__ import annotations

import json
import os
import math
import statistics
import time
from collections import Counter, defaultdict
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.app.product_bootstrap import ProductBootstrap
from src.product.command_center import _normalize_artifact_entry_from_metadata
from src.product.models import ProductWorkflowRequest
from src.product.service import build_product_workflow_catalog, list_product_documents, run_product_workflow
from src.config import get_evidenceops_external_settings
from src.services.evidenceops_external_targets import build_nextcloud_repository_snapshot
from src.services.evidenceops_local_ops import (
    compare_evidenceops_repository_state,
    list_evidenceops_repository_entries,
    register_evidenceops_entry,
    search_evidenceops_repository_entries,
    update_evidenceops_action_item,
)
from src.services.evidenceops_repository import (
    build_evidenceops_repository_snapshot,
    diff_evidenceops_repository_snapshots,
    list_evidenceops_repository_documents,
    summarize_evidenceops_repository_documents,
)
from src.services.document_context import build_structured_document_context
from src.services.runtime_controls import build_effective_rag_settings, load_runtime_controls_state
from src.storage.lab_state import (
    append_lab_chat_message,
    append_lab_workflow_run,
    get_lab_chat_session,
    load_lab_chat_sessions,
    load_lab_workflow_runs,
    upsert_lab_chat_session,
    update_lab_chat_session_runtime,
)
from src.storage.phase7_model_comparison_log import load_model_comparison_log, summarize_model_comparison_log
from src.storage.phase8_eval_diagnosis import build_eval_diagnosis
from src.storage.phase8_eval_store import load_eval_runs, summarize_eval_runs
from src.storage.product_telemetry import load_product_telemetry_runs
from src.storage.phase95_evidenceops_action_store import load_evidenceops_actions, summarize_evidenceops_actions
from src.storage.phase95_evidenceops_repository_snapshot import load_evidenceops_repository_snapshot
from src.storage.phase95_evidenceops_worklog import load_evidenceops_worklog, summarize_evidenceops_worklog
from src.storage.rag_store import load_rag_document_catalog, load_rag_store
from src.storage.runtime_execution_log import load_runtime_execution_log, summarize_runtime_execution_log
from src.structured.base import DocumentAgentPayload
from src.structured.envelope import StructuredResult, TaskExecutionRequest
from src.structured.langgraph_workflow import run_structured_execution_workflow
from src.storage.runtime_paths import (
    get_artifact_root,
    get_lab_chat_sessions_path,
    get_lab_workflow_runs_path,
    get_phase6_document_agent_log_path,
    get_phase7_model_comparison_log_path,
    get_phase8_eval_db_path,
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_worklog_path,
    get_product_telemetry_path,
    get_product_workflow_history_path,
    get_rag_store_path,
    get_runtime_controls_state_path,
    get_runtime_execution_log_path,
    get_phase95_evidenceops_repository_snapshot_path,
)

LAB_CROSS_SURFACE_NOTES = [
    'Runtime shows operational telemetry, not workflow routing deep dives.',
    'Use Workflow Inspector for route selection, node traces and task-level execution detail.',
    'Use Benchmarks for model-vs-model tradeoffs and preset comparisons.',
    'Use Evals & Diagnosis for regression tracking, pass-rate drift and watchlists.',
    'Use Experiments & Artifacts for capture registry and generated evidence bundles.',
    'Use EvidenceOps / MCP for repository readiness, open actions and delivery operations.',
]

LAB_CHAT_AUTOMATED_PROMPTS = {
    'Summarize the main control gaps in the selected evidence.',
    'Turn the findings into next actions with owners and due dates.',
    'What appears risky, unsupported or contradictory in these documents?',
}

LAB_CHAT_STOPWORDS = {
    'the', 'and', 'for', 'with', 'this', 'that', 'what', 'about', 'from', 'into', 'your', 'these',
    'those', 'document', 'documents', 'selected', 'evidence', 'main', 'does', 'mean', 'says',
    'uma', 'uns', 'das', 'dos', 'com', 'que', 'esse', 'essa', 'isso', 'isto', 'este', 'esta',
    'documento', 'documentos', 'quer', 'querendo', 'dizer', 'sobre', 'qual', 'quais', 'para',
    'por', 'como', 'mais', 'não', 'sim', 'ele', 'ela', 'está', 'esta', 'nas', 'nos', 'das',
}


def _resolve_evidenceops_repository_context(workspace_root: Path) -> dict[str, Any]:
    repository_root = workspace_root / 'data' / 'corpus_revisado'
    external_settings = get_evidenceops_external_settings()
    nextcloud_settings = getattr(external_settings, 'nextcloud', None)

    configured_backend = str(getattr(external_settings, 'repository_backend', '') or '').strip().lower()
    backend = configured_backend or 'local'

    if backend != 'nextcloud_webdav' and nextcloud_settings is not None:
        nextcloud_base_url = str(getattr(nextcloud_settings, 'base_url', '') or '').strip()
        nextcloud_username = str(getattr(nextcloud_settings, 'username', '') or '').strip()
        nextcloud_password = str(getattr(nextcloud_settings, 'app_password', '') or '').strip()
        if nextcloud_base_url and nextcloud_username and nextcloud_password:
            backend = 'nextcloud_webdav'

    if backend == 'nextcloud_webdav' and nextcloud_settings is not None:
        root_label = str(getattr(nextcloud_settings, 'root_path', '') or '/EvidenceOpsDemo').strip() or '/EvidenceOpsDemo'
        return {
            'repository_root': repository_root,
            'repository_backend': 'nextcloud_webdav',
            'repository_label': root_label,
            'repository_display_name': f'NextCloud {root_label}',
            'repository_tool_name': 'nextcloud_webdav',
            'external_settings': external_settings,
        }

    return {
        'repository_root': repository_root,
        'repository_backend': 'local',
        'repository_label': str(repository_root),
        'repository_display_name': 'corpus_revisado',
        'repository_tool_name': 'local_repository_scan',
        'external_settings': external_settings,
    }



WORKFLOW_TASK_LABELS = {
    'document_review': 'Document Review',
    'policy_contract_comparison': 'Policy / Contract Comparison',
    'action_plan_evidence_review': 'Action Plan / Evidence Review',
    'candidate_review': 'Candidate Review',
}

WORKFLOW_DESCRIPTIONS = {
    'document_review': 'Review one or more grounded documents and summarize findings, risks and next actions.',
    'policy_contract_comparison': 'Compare policy and contract evidence with grounded deltas and mismatches.',
    'action_plan_evidence_review': 'Extract operational tasks, owners and follow-up actions from evidence.',
    'candidate_review': 'Assess candidate evidence with structured findings and recommendation cues.',
}

WORKFLOW_INPUT_HINTS = {
    'document_review': 'Review the selected evidence and summarize the most important findings, risks and next steps.',
    'policy_contract_comparison': 'Compare the selected policy and contract evidence and surface the biggest gaps.',
    'action_plan_evidence_review': 'Extract operational action items, owners, due dates and blockers from the evidence.',
    'candidate_review': 'Review the selected candidate material and summarize strengths, risks and fit.',
}

EVIDENCEOPS_MCP_TOOL_CATALOG = [
    {
        'name': 'list_documents',
        'description': 'List repository documents with optional category, suffix and identifier filters.',
        'surface': 'repository',
    },
    {
        'name': 'search_documents',
        'description': 'Search repository documents using local term matching and ranking.',
        'surface': 'repository',
    },
    {
        'name': 'get_document',
        'description': 'Resolve a single repository document by document_id or relative_path.',
        'surface': 'repository',
    },
    {
        'name': 'summarize_repository',
        'description': 'Return the aggregated repository summary for the current evidence corpus.',
        'surface': 'repository',
    },
    {
        'name': 'compare_repository_state',
        'description': 'Compare the current repository against the persisted snapshot to detect drift.',
        'surface': 'repository',
    },
    {
        'name': 'register_evidenceops_entry',
        'description': 'Register worklog entries and materialize derived actions through MCP.',
        'surface': 'worklog',
    },
    {
        'name': 'list_actions',
        'description': 'List action-store records with status, owner and review-type filters.',
        'surface': 'actions',
    },
    {
        'name': 'summarize_actions',
        'description': 'Return the aggregated summary of the local action store.',
        'surface': 'actions',
    },
    {
        'name': 'update_action',
        'description': 'Update a stored action while preserving the EvidenceOps approval trail.',
        'surface': 'actions',
    },
    {
        'name': 'summarize_worklog',
        'description': 'Return the aggregated summary of the local EvidenceOps worklog.',
        'surface': 'worklog',
    },
]

RUNTIME_SURFACE_MAX_RUNS = 10
WORKFLOW_INSPECTOR_TASK_IDS = tuple(WORKFLOW_TASK_LABELS.keys())


def _looks_like_document_hash(value: str) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and bool(re.fullmatch(r'[0-9a-f]{32,64}', normalized))


def _resolve_workflow_document_label(value: str | None, document_lookup: dict[str, dict[str, Any]]) -> str:
    normalized = str(value or '').strip()
    if not normalized:
        return 'Workspace document'
    if normalized in document_lookup:
        return str(document_lookup[normalized].get('name') or normalized)
    for payload in document_lookup.values():
        name = str(payload.get('name') or '').strip()
        if name and name == normalized:
            return name
    if _looks_like_document_hash(normalized):
        return f'Document {normalized[:8]}…'
    return normalized


def _split_workflow_review_reasons(reason_text: str | None) -> list[str]:
    normalized = str(reason_text or '').strip()
    if not normalized:
        return []
    parts = [part.strip() for part in normalized.split(';') if part.strip()]
    return parts or [normalized]


def _humanize_workflow_review_reason(reason_text: str | None) -> str:
    normalized = str(reason_text or '').strip()
    if not normalized:
        return ''
    if normalized == 'operational_extraction_without_grounded_actions':
        return 'Operational extraction returned actions without grounded evidence.'
    if normalized == 'risk_review_has_gaps_without_grounded_risks':
        return 'Risk review surfaced gaps without grounded risks.'
    if normalized == 'Multiple documents are selected':
        return 'Multiple documents were selected; verify that the synthesis stayed scoped.'
    if normalized == 'confirm that the response did not improperly combine distinct contexts.':
        return 'Check that the response did not merge distinct document contexts.'
    if normalized.startswith('document_agent_confidence_below_review_threshold:'):
        threshold = normalized.split(':', 1)[1].strip()
        return f'Document agent confidence stayed below the review threshold ({threshold}).'
    if '_' in normalized and normalized.lower() == normalized:
        return normalized.replace('_', ' ').capitalize()
    return normalized


def _workflow_execution_label(run: dict[str, Any]) -> str:
    raw_mode = str(run.get('execution_mode') or '').strip()
    if raw_mode and raw_mode not in {'product_api', 'workflow_inspector', 'workflow_run'}:
        return raw_mode
    response_payload = run.get('response_payload') if isinstance(run.get('response_payload'), dict) else {}
    debug_metadata = response_payload.get('debug_metadata') if isinstance(response_payload.get('debug_metadata'), dict) else {}
    context_strategy = str(debug_metadata.get('context_strategy') or '').strip()
    if context_strategy:
        return context_strategy
    trace = run.get('trace') if isinstance(run.get('trace'), dict) else {}
    spans = trace.get('spans') if isinstance(trace.get('spans'), list) else []
    for span in spans:
        if not isinstance(span, dict):
            continue
        if str(span.get('name') or '') == 'route_agent_context_strategy':
            detail = str(span.get('detail') or '').strip()
            if ':' in detail:
                return detail.split(':', 1)[1].strip()
            if detail:
                return detail
    return raw_mode or 'workflow_run'


def _workflow_surface_label(run: dict[str, Any]) -> str:
    raw_surface = str(run.get('surface') or run.get('execution_mode') or '').strip()
    if raw_surface == 'workflow_inspector':
        return 'Workflow Inspector'
    if raw_surface == 'product_api':
        return 'Product API'
    if raw_surface == 'workflow_run':
        return 'Workflow Run'
    return raw_surface.replace('_', ' ') if raw_surface else 'Workflow Run'


def _pick_preferred_workflow_run(task_runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not task_runs:
        return None

    preferred_surface_runs = [
        run for run in task_runs if str(run.get('surface') or '').strip() == 'workflow_inspector'
    ]

    for candidate_runs in (preferred_surface_runs, task_runs):
        for run in candidate_runs:
            if isinstance(run.get('result'), dict) or isinstance(run.get('response_payload'), dict) or str(run.get('summary') or '').strip():
                return run

    return preferred_surface_runs[0] if preferred_surface_runs else task_runs[0]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
        return float(default)
    try:
        parsed = float(str(value).strip())
        return parsed if math.isfinite(parsed) else float(default)
    except Exception:
        return float(default)


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


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return float(ordered[low] * (1 - weight) + ordered[high] * weight)


def _normalize_ratio_to_unit(value: Any) -> float:
    raw = _safe_float(value, 0.0)
    if raw <= 0:
        return 0.0
    if raw <= 1.0:
        return min(raw, 1.0)
    if raw <= 100.0:
        return min(raw / 100.0, 1.0)
    return 1.0


def _percent_label(value: float, digits: int = 0) -> str:
    if digits <= 0:
        return f'{round(value * 100)}%'
    return f'{value * 100:.{digits}f}%'


def _bytes_label(size_bytes: int | float | None) -> str:
    amount = _safe_float(size_bytes, 0.0)
    if amount <= 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB']
    index = 0
    while amount >= 1024 and index < len(units) - 1:
        amount /= 1024
        index += 1
    if index == 0:
        return f'{int(amount)} {units[index]}'
    return f'{amount:.1f} {units[index]}'


def _format_timestamp(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def _trim_text(value: Any, *, max_chars: int = 80) -> str:
    text = str(value or '').strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + '…'


def _status_from_warnings(warnings: list[str]) -> str:
    return 'warning' if warnings else 'completed'


def _safe_iso_datetime(value: Any) -> datetime | None:
    text = str(value or '').strip()
    if not text:
        return None
    normalized = text.replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _runtime_entry_sort_key(entry: dict[str, Any]) -> datetime:
    parsed = _safe_iso_datetime(entry.get('timestamp'))
    return parsed if parsed is not None else datetime.min.replace(tzinfo=timezone.utc)


def _sort_runtime_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [entry for entry in entries if isinstance(entry, dict)]
    return sorted(normalized, key=_runtime_entry_sort_key, reverse=True)


def _is_product_runtime_entry(entry: dict[str, Any], product_workflow_ids: set[str]) -> bool:
    workflow_id = str(entry.get('workflow_id') or '').strip()
    flow_type = str(entry.get('flow_type') or '').strip()
    return workflow_id in product_workflow_ids or flow_type == 'product_workflow'


def _runtime_window_label(scope: str, size: int, max_size: int) -> str:
    if size <= 0:
        return 'recent runtime traces'
    noun = 'product run' if scope == 'product' else 'runtime trace'
    suffix = '' if size == 1 else 's'
    if size >= max_size:
        return f'last {max_size} {noun}{suffix}'
    return f'last {size} {noun}{suffix}'


def _format_runtime_timeline_label(value: Any) -> str:
    parsed = _safe_iso_datetime(value)
    if parsed is None:
        return str(value or 'runtime').strip() or 'runtime'
    return parsed.astimezone(timezone.utc).strftime('%m/%d %H:%M')


def _display_runtime_task(entry: dict[str, Any]) -> tuple[str, str | None]:
    workflow_id = str(entry.get('workflow_id') or '').strip()
    task_type = str(entry.get('task_type') or entry.get('flow_type') or 'runtime').strip() or 'runtime'
    workflow_label = WORKFLOW_TASK_LABELS.get(workflow_id)
    if workflow_label:
        detail = task_type if task_type and task_type != workflow_id else None
        return workflow_label, detail
    return task_type.replace('_', ' '), None


def _parse_due_date(value: Any):
    text = str(value or '').strip()
    if not text or text == '—':
        return None
    try:
        return datetime.fromisoformat(text).date() if 'T' in text else datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        return None


def _sorted_worklog_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    minimum = datetime.min.replace(tzinfo=timezone.utc)
    normalized = [entry for entry in entries if isinstance(entry, dict)]
    return sorted(normalized, key=lambda entry: _safe_iso_datetime(entry.get('timestamp')) or minimum, reverse=True)


def _latest_worklog_timestamp(
    entries: list[dict[str, Any]],
    *,
    tool_names: set[str] | None = None,
    operations: set[str] | None = None,
) -> str | None:
    for entry in _sorted_worklog_entries(entries):
        tool_name = str(entry.get('tool_used') or '').strip()
        operation = str(entry.get('operation') or '').strip()
        if tool_names and tool_name in tool_names:
            return _format_timestamp(entry.get('timestamp'))
        if operations and operation in operations:
            return _format_timestamp(entry.get('timestamp'))
        if not tool_names and not operations:
            return _format_timestamp(entry.get('timestamp'))
    return None


def _latest_repository_sync_timestamp(entries: list[dict[str, Any]], repository_snapshot: dict[str, Any] | None) -> str | None:
    synced_at = _latest_worklog_timestamp(entries, tool_names={'local_repository_scan'}, operations={'repository_sync'})
    if synced_at:
        return synced_at
    if isinstance(repository_snapshot, dict):
        return _format_timestamp(repository_snapshot.get('captured_at'))
    return None


def _workspace_documents(workspace_root: Path) -> list[dict[str, Any]]:
    try:
        rag_settings = build_effective_rag_settings(workspace_root=workspace_root)
        return [document.model_dump(mode='json') for document in list_product_documents(rag_settings)]
    except Exception:
        catalog = load_rag_document_catalog(get_rag_store_path(workspace_root)) or []
        normalized: list[dict[str, Any]] = []
        for item in catalog:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    'document_id': str(item.get('document_id') or item.get('id') or ''),
                    'name': str(item.get('name') or item.get('title') or 'Document').strip() or 'Document',
                    'status': str(item.get('status') or 'indexed'),
                    'chunk_count': _safe_int(item.get('chunk_count') or item.get('chunks') or 0),
                    'char_count': _safe_int(item.get('char_count') or item.get('chars') or 0),
                    'indexed_at': _format_timestamp(item.get('indexed_at')),
                    'loader_strategy_label': str(item.get('loader_strategy_label') or item.get('loader_strategy') or '').strip() or None,
                    'size_bytes': _safe_int(item.get('size_bytes') or 0),
                    'size_label': str(item.get('size_label') or _bytes_label(item.get('size_bytes') or 0)),
                    'source_type': str(item.get('source_type') or '').strip() or None,
                    'page_count': _safe_int(item.get('page_count') or 0) or None,
                    'warnings': [str(warning) for warning in (item.get('warnings') or []) if str(warning or '').strip()],
                }
            )
        return normalized


def _document_lookup(documents: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for document in documents:
        document_id = str(document.get('document_id') or '').strip()
        if document_id:
            lookup[document_id] = document
    return lookup


def _load_runtime_state(workspace_root: Path, *, additional_runtime_log_paths: list[Path] | None = None) -> dict[str, Any]:
    controls_state = load_runtime_controls_state(get_runtime_controls_state_path(workspace_root)) or {}
    profile = controls_state.get('profile') if isinstance(controls_state.get('profile'), dict) else {}
    rag_store = load_rag_store(get_rag_store_path(workspace_root)) or {}
    runtime_entries_raw = list(load_runtime_execution_log(get_runtime_execution_log_path(workspace_root)))
    additional_runtime_sources: list[str] = []
    for additional_path in additional_runtime_log_paths or []:
        additional_entries = load_runtime_execution_log(additional_path)
        if additional_entries:
            additional_runtime_sources.append(str(additional_path))
            runtime_entries_raw.extend(additional_entries)

    runtime_entries = _sort_runtime_entries(runtime_entries_raw)
    documents = _workspace_documents(workspace_root)
    document_lookup = _document_lookup(documents)
    chunks = rag_store.get('chunks') if isinstance(rag_store.get('chunks'), list) else []
    doc_list = rag_store.get('documents') if isinstance(rag_store.get('documents'), list) else []

    generation = profile.get('generation') if isinstance(profile.get('generation'), dict) else {}
    retrieval = profile.get('retrieval') if isinstance(profile.get('retrieval'), dict) else {}
    doc_processing = profile.get('docProcessing') if isinstance(profile.get('docProcessing'), dict) else {}

    product_workflow_ids = set(build_product_workflow_catalog().keys())
    product_runtime_entries = [entry for entry in runtime_entries if _is_product_runtime_entry(entry, product_workflow_ids)]
    surface_scope = 'product' if product_runtime_entries else 'runtime'
    surface_runtime_entries = (product_runtime_entries or runtime_entries)[:RUNTIME_SURFACE_MAX_RUNS]
    telemetry_entries = product_runtime_entries or runtime_entries
    runtime_summary = summarize_runtime_execution_log(telemetry_entries)

    latest_entry = telemetry_entries[0] if telemetry_entries else {}
    latest_budget_entry = next(
        (
            entry
            for entry in telemetry_entries
            if _safe_int(entry.get('context_budget_chars') or entry.get('context_window') or 0) > 0
            or _safe_int(entry.get('context_chars') or 0) > 0
        ),
        latest_entry,
    )

    context_pressure_values = [
        _normalize_ratio_to_unit(entry.get('context_pressure_ratio'))
        for entry in telemetry_entries
        if _normalize_ratio_to_unit(entry.get('context_pressure_ratio')) > 0
    ]
    avg_context_pressure = _mean(context_pressure_values)
    latest_context_pressure = _normalize_ratio_to_unit(latest_entry.get('context_pressure_ratio'))

    context_budget_total = 0
    if isinstance(latest_budget_entry.get('context_budget_chars'), (int, float)):
        context_budget_total = _safe_int(latest_budget_entry.get('context_budget_chars'))
    elif isinstance(latest_budget_entry.get('context_window'), (int, float)):
        context_budget_total = _safe_int(latest_budget_entry.get('context_window'))
    elif isinstance(generation.get('contextWindow'), (int, float)):
        context_budget_total = _safe_int(generation.get('contextWindow'))
    else:
        context_budget_total = 32768

    context_budget_used = _safe_int(latest_budget_entry.get('context_chars') or 0)
    context_utilization = min((context_budget_used / context_budget_total), 1.0) if context_budget_total > 0 else 0.0
    context_pressure = latest_context_pressure or avg_context_pressure or context_utilization

    ingestion_health = 'healthy'
    if any(str(document.get('status') or '') in {'error', 'failed'} for document in documents):
        ingestion_health = 'error'
    elif any(str(document.get('status') or '') in {'warning', 'pending', 'indexing'} or (document.get('warnings') or []) for document in documents):
        ingestion_health = 'warning'

    return {
        'controls_state': controls_state,
        'profile': profile,
        'generation': generation,
        'retrieval': retrieval,
        'doc_processing': doc_processing,
        'rag_store': rag_store,
        'documents': documents,
        'document_lookup': document_lookup,
        'runtime_entries': runtime_entries,
        'additional_runtime_sources': additional_runtime_sources,
        'product_runtime_entries': product_runtime_entries,
        'surface_runtime_entries': surface_runtime_entries,
        'surface_scope': surface_scope,
        'runtime_summary': runtime_summary,
        'latest_entry': latest_entry,
        'latest_budget_entry': latest_budget_entry,
        'indexed_document_count': len(doc_list) or len(documents),
        'total_chunks': len(chunks),
        'context_budget_total': context_budget_total,
        'context_budget_used': context_budget_used,
        'context_utilization': context_utilization,
        'context_pressure': context_pressure,
        'avg_context_pressure': avg_context_pressure,
        'ingestion_health': ingestion_health,
    }


def _runtime_meta(workspace_root: Path, notes: list[str] | None = None) -> dict[str, Any]:
    controls_state = load_runtime_controls_state(get_runtime_controls_state_path(workspace_root)) or {}
    updated_at = str(controls_state.get('updated_at') or '') or None
    payload = {
        'source': 'derived',
        'updated_at': updated_at,
    }
    if notes:
        payload['notes'] = notes
    return payload


def _derive_benchmark_surface_status(latest_timestamp: Any, *, has_models: bool) -> str:
    if not has_models:
        return 'empty'
    observed_at = _safe_iso_datetime(latest_timestamp)
    if observed_at is None:
        return 'derived-live'
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - observed_at.astimezone(timezone.utc)
    return 'historical' if age > timedelta(days=7) else 'derived-live'


def _build_runtime_core_payload(runtime_state: dict[str, Any]) -> dict[str, Any]:
    profile = runtime_state['profile']
    generation = runtime_state['generation']
    retrieval = runtime_state['retrieval']
    doc_processing = runtime_state['doc_processing']
    runtime_entries = runtime_state['runtime_entries']

    return {
        'generationProvider': str(profile.get('primaryConnectionId') or 'ollama'),
        'generationModel': str(profile.get('primaryModel') or 'unknown'),
        'promptProfile': str(generation.get('promptProfile') or 'neutral'),
        'contextWindowMode': str(generation.get('contextWindow') or runtime_state['latest_entry'].get('context_window_mode') or 'auto'),
        'resolvedContext': runtime_state['context_budget_total'],
        'embeddingProvider': str(profile.get('embeddingConnectionId') or 'ollama'),
        'embeddingModel': str(profile.get('embeddingModel') or 'nomic-embed-text-v2-moe:latest'),
        'retrievalStrategy': str(profile.get('retrievalStrategy') or 'hybrid'),
        'chunkSize': _safe_int(retrieval.get('chunkSize') or runtime_state['latest_entry'].get('rag_chunk_size') or 0),
        'chunkOverlap': _safe_int(retrieval.get('chunkOverlap') or runtime_state['latest_entry'].get('rag_chunk_overlap') or 0),
        'topK': _safe_int(retrieval.get('topK') or runtime_state['latest_entry'].get('rag_top_k') or 0),
        'rerankPoolSize': _safe_int(retrieval.get('rerankPoolSize') or runtime_state['latest_entry'].get('top_k_effective') or 0),
        'rerankLexicalWeight': round(_safe_float(retrieval.get('rerankLexicalWeight') or 0.0), 2),
        'vectorBackend': str(runtime_state['latest_entry'].get('retrieval_backend_used') or 'ChromaDB'),
        'vectorBackendStatus': 'healthy' if runtime_state['indexed_document_count'] > 0 else 'degraded',
        'indexedDocumentCount': runtime_state['indexed_document_count'],
        'totalChunks': runtime_state['total_chunks'],
        'ingestionHealth': runtime_state['ingestion_health'],
        'contextPressure': runtime_state['context_pressure'],
        'contextPressurePct': round(runtime_state['context_pressure'] * 100, 1),
        'contextBudgetUsed': runtime_state['context_budget_used'],
        'contextBudgetTotal': runtime_state['context_budget_total'],
        'contextUtilizationPct': round(runtime_state['context_utilization'] * 100, 1),
        'pdfExtractionMode': str(doc_processing.get('pdfExtractionMode') or 'hybrid'),
        'ocrBackend': str(doc_processing.get('ocrBackend') or 'ocrmypdf'),
        'vlmEnhancement': bool(doc_processing.get('vlmEnhancement')),
        'executionPolicy': str(profile.get('executionPolicy') or 'prefer_local_burst_hosted'),
        'recentTraceCount': len(runtime_entries),
    }


def _build_runtime_generation_rows(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {'label': 'Provider', 'value': runtime['generationProvider']},
        {'label': 'Model', 'value': runtime['generationModel']},
        {'label': 'Prompt Profile', 'value': runtime['promptProfile']},
        {'label': 'Context Window', 'value': runtime['contextWindowMode']},
        {'label': 'Resolved Context', 'value': f"{_safe_int(runtime['resolvedContext']):,} tokens"},
        {'label': 'Execution Policy', 'value': runtime['executionPolicy']},
    ]


def _build_runtime_retrieval_rows(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {'label': 'Embedding Model', 'value': runtime['embeddingModel']},
        {'label': 'Strategy', 'value': runtime['retrievalStrategy']},
        {'label': 'Chunk Size / Overlap', 'value': f"{runtime['chunkSize']} / {runtime['chunkOverlap']}"},
        {'label': 'Top-K', 'value': runtime['topK']},
        {'label': 'Rerank Pool', 'value': runtime['rerankPoolSize']},
        {'label': 'Lexical Weight', 'value': runtime['rerankLexicalWeight']},
    ]


def _build_runtime_vector_rows(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {'label': 'Backend', 'value': runtime['vectorBackend']},
        {'label': 'Status', 'value': runtime['vectorBackendStatus']},
        {'label': 'Indexed Documents', 'value': runtime['indexedDocumentCount']},
        {'label': 'Total Chunks', 'value': runtime['totalChunks']},
    ]


def _build_runtime_diagnostics_rows(runtime: dict[str, Any], runtime_state: dict[str, Any]) -> list[dict[str, Any]]:
    summary = runtime_state['runtime_summary']
    return [
        {'label': 'OCR Backend', 'value': runtime['ocrBackend']},
        {'label': 'PDF Extraction', 'value': runtime['pdfExtractionMode']},
        {'label': 'VLM Enhancement', 'value': 'Enabled' if runtime['vlmEnhancement'] else 'Disabled'},
        {'label': 'Execution Policy', 'value': runtime['executionPolicy']},
        {'label': 'Recent Traces', 'value': len(runtime_state['runtime_entries'])},
        {'label': 'Needs Review Rate', 'value': _percent_label(_safe_float(summary.get('needs_review_rate')), 0)},
    ]


def _build_recent_trace_rows(runtime_entries: list[dict[str, Any]], document_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(runtime_entries[:RUNTIME_SURFACE_MAX_RUNS]):
        source_ids = [str(item) for item in (entry.get('source_document_ids') or []) if str(item or '').strip()]
        task_label, task_detail = _display_runtime_task(entry)
        rows.append(
            {
                'id': f"trace-{index + 1}",
                'timestamp': str(entry.get('timestamp') or _now_iso()),
                'flow': str(entry.get('flow_type') or 'runtime'),
                'task': task_label,
                'taskDetail': task_detail,
                'provider': str(entry.get('provider') or 'unknown'),
                'model': str(entry.get('model') or 'unknown'),
                'latencyS': round(_safe_float(entry.get('latency_s')), 3),
                'success': bool(entry.get('success')),
                'needsReview': bool(entry.get('needs_review')),
                'totalTokens': _safe_int(entry.get('total_tokens') or 0),
                'sourceCount': max(_safe_int(entry.get('retrieved_chunks_count') or 0), len(source_ids)),
                'contextPressurePct': round(_normalize_ratio_to_unit(entry.get('context_pressure_ratio')) * 100, 1),
                'errorMessage': str(entry.get('error_message') or '').strip() or None,
                'sourceDocuments': [document_lookup.get(source_id, {}).get('name') or source_id for source_id in source_ids[:3]],
            }
        )
    return rows


def _build_runtime_timeline(runtime_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    ordered = list(reversed(runtime_entries[:RUNTIME_SURFACE_MAX_RUNS]))
    for entry in ordered:
        task_label, _task_detail = _display_runtime_task(entry)
        timeline.append(
            {
                'label': _format_runtime_timeline_label(entry.get('timestamp')),
                'timestamp': _format_timestamp(entry.get('timestamp')),
                'task': task_label,
                'latencyS': round(_safe_float(entry.get('latency_s')), 3),
                'contextPressurePct': round(_normalize_ratio_to_unit(entry.get('context_pressure_ratio')) * 100, 1),
                'error': 0 if bool(entry.get('success')) else 1,
            }
        )
    return timeline


def _build_runtime_provider_breakdown(runtime_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for entry in runtime_entries:
        key = (str(entry.get('provider') or 'unknown'), str(entry.get('model') or 'unknown'))
        grouped[key].append(entry)
    rows: list[dict[str, Any]] = []
    for (provider, model), entries in grouped.items():
        rows.append(
            {
                'key': f'{provider}:{model}',
                'provider': provider,
                'model': model,
                'runs': len(entries),
                'errorRate': round(sum(1 for entry in entries if not bool(entry.get('success'))) / max(len(entries), 1), 3),
                'needsReviewRate': round(sum(1 for entry in entries if bool(entry.get('needs_review'))) / max(len(entries), 1), 3),
                'avgLatencyS': round(_mean([_safe_float(entry.get('latency_s')) for entry in entries]), 3),
                'avgTotalTokens': round(_mean([_safe_float(entry.get('total_tokens')) for entry in entries]), 1),
            }
        )
    rows.sort(key=lambda item: (-item['runs'], item['provider'], item['model']))
    return rows


def _build_runtime_failure_modes(runtime_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    error_counter: Counter[str] = Counter()
    review_counter: Counter[str] = Counter()
    for entry in runtime_entries:
        error_text = str(entry.get('error_message') or '').strip()
        if error_text:
            label = error_text.split(':', 1)[0][:80]
            error_counter[label] += 1
        review_reason = str(entry.get('needs_review_reason') or '').strip()
        if review_reason:
            review_counter[review_reason[:80]] += 1

    rows: list[dict[str, Any]] = []
    for label, count in error_counter.most_common(4):
        rows.append({'id': f'error-{label}', 'label': label, 'count': count, 'severity': 'error', 'detail': 'Repeated failed runtime traces.'})
    for label, count in review_counter.most_common(4):
        rows.append({'id': f'review-{label}', 'label': label, 'count': count, 'severity': 'warning', 'detail': 'Repeated review trigger in persisted traces.'})
    return rows[:6]


def _build_runtime_watchouts(runtime_state: dict[str, Any], runtime_payload: dict[str, Any]) -> list[str]:
    ops_summary = runtime_payload.get('ops_summary') if isinstance(runtime_payload.get('ops_summary'), dict) else {}
    window_label = str(runtime_payload.get('surface_window', {}).get('label') or 'recent runtime traces')
    notes: list[str] = []
    if _safe_float(ops_summary.get('errorRate')) >= 0.2:
        notes.append(f"Runtime error rate is elevated at {_percent_label(_safe_float(ops_summary.get('errorRate')))} across the {window_label}.")
    if _safe_float(ops_summary.get('needsReviewRate')) >= 0.15:
        notes.append(f"Manual review pressure is non-trivial at {_percent_label(_safe_float(ops_summary.get('needsReviewRate')))} in the {window_label}.")
    if _safe_float(ops_summary.get('avgLatencyS')) >= 10:
        notes.append(f"Average runtime latency is {_safe_float(ops_summary.get('avgLatencyS')):.1f}s in the {window_label}; investigate provider, prompt size or retrieval overhead.")
    if runtime_payload['runtime']['contextPressure'] >= 0.8:
        notes.append('The latest observed product trace is under high context pressure; confirm whether the most recent run needs fewer sources or a tighter prompt envelope.')
    if runtime_payload.get('retrieval_health', {}).get('emptyRetrievalRate', 0) >= 0.1:
        notes.append('Some recent runs returned zero retrieved chunks; inspect retrieval quality here before escalating to Workflow Inspector or Evals.')
    return notes[:4]


def build_lab_runtime_payload(workspace_root: Path, *, additional_runtime_log_paths: list[Path] | None = None) -> dict[str, Any]:
    runtime_state = _load_runtime_state(workspace_root, additional_runtime_log_paths=additional_runtime_log_paths)
    runtime = _build_runtime_core_payload(runtime_state)
    all_runtime_entries = runtime_state['runtime_entries']
    product_runtime_entries = runtime_state['product_runtime_entries']
    surface_entries = runtime_state['surface_runtime_entries']
    surface_scope = runtime_state['surface_scope']
    summary = summarize_runtime_execution_log(surface_entries)

    latency_values = [_safe_float(entry.get('latency_s')) for entry in surface_entries if _safe_float(entry.get('latency_s')) > 0]
    throughput_24h = 0
    now = datetime.now(timezone.utc)
    for entry in product_runtime_entries or all_runtime_entries:
        timestamp = _safe_iso_datetime(entry.get('timestamp'))
        if timestamp is not None and timestamp >= now - timedelta(hours=24):
            throughput_24h += 1

    retrieved_chunk_counts = [_safe_float(entry.get('retrieved_chunks_count')) for entry in surface_entries]
    retrieval_count = max(len(surface_entries), 1)
    empty_retrieval_rate = sum(1 for value in retrieved_chunk_counts if value <= 0) / retrieval_count
    context_utilization_values = []
    for entry in surface_entries:
        budget = _safe_float(entry.get('context_budget_chars') or entry.get('context_window') or 0.0)
        used = _safe_float(entry.get('context_chars') or 0.0)
        if budget > 0:
            context_utilization_values.append(min(used / budget, 1.0))

    total_prompt_tokens = _safe_int(summary.get('total_prompt_tokens'))
    if total_prompt_tokens <= 0:
        total_prompt_tokens = sum(_safe_int(entry.get('prompt_tokens') or 0) for entry in surface_entries)
    total_completion_tokens = _safe_int(summary.get('total_completion_tokens'))
    if total_completion_tokens <= 0:
        total_completion_tokens = sum(_safe_int(entry.get('completion_tokens') or 0) for entry in surface_entries)
    avg_prompt_tokens = _safe_float(summary.get('avg_prompt_tokens'))
    if avg_prompt_tokens <= 0 and surface_entries:
        avg_prompt_tokens = total_prompt_tokens / max(len(surface_entries), 1)
    avg_completion_tokens = _safe_float(summary.get('avg_completion_tokens'))
    if avg_completion_tokens <= 0 and surface_entries:
        avg_completion_tokens = total_completion_tokens / max(len(surface_entries), 1)

    instrumented_stage_runs = sum(
        1
        for entry in surface_entries
        if any(
            _safe_float(entry.get(field)) > 0
            for field in ('retrieval_latency_s', 'generation_latency_s', 'prompt_build_latency_s')
        )
    )
    latency_breakdown = [
        {'stage': 'Retrieval', 'seconds': round(_safe_float(summary.get('avg_retrieval_latency_s')), 3)},
        {'stage': 'Generation', 'seconds': round(_safe_float(summary.get('avg_generation_latency_s')), 3)},
        {'stage': 'Prompt build', 'seconds': round(_safe_float(summary.get('avg_prompt_build_latency_s')), 3)},
    ]
    total_known_latency = sum(item['seconds'] for item in latency_breakdown)
    other_latency = max(_safe_float(summary.get('avg_latency_s')) - total_known_latency, 0.0)
    if other_latency > 0 or not latency_breakdown:
        latency_breakdown.append({'stage': 'Other', 'seconds': round(other_latency, 3)})
    non_zero_latency_breakdown = [item for item in latency_breakdown if item['seconds'] > 0]
    if len(non_zero_latency_breakdown) == 1 and non_zero_latency_breakdown[0]['stage'] == 'Other':
        non_zero_latency_breakdown[0]['stage'] = 'Observed runtime'
    if not non_zero_latency_breakdown and _safe_float(summary.get('avg_latency_s')) > 0:
        non_zero_latency_breakdown = [{'stage': 'Observed runtime', 'seconds': round(_safe_float(summary.get('avg_latency_s')), 3)}]

    surface_window = {
        'scope': surface_scope,
        'size': len(surface_entries),
        'maxSize': RUNTIME_SURFACE_MAX_RUNS,
        'label': _runtime_window_label(surface_scope, len(surface_entries), RUNTIME_SURFACE_MAX_RUNS),
    }

    status = 'live' if surface_entries else 'empty'
    degraded_reason = None
    if not surface_entries:
        degraded_reason = 'No persisted runtime_execution_log entries were found in this workspace yet.'
    elif not product_runtime_entries and all_runtime_entries:
        status = 'degraded'
        degraded_reason = 'No product workflow traces were found yet; showing the most recent generic runtime entries instead.'

    payload: dict[str, Any] = {
        'ok': True,
        'meta': _runtime_meta(
            workspace_root,
            notes=[
                'This surface is intentionally focused on current product runtime posture, throughput, retrieval health and recent trace issues.',
                'It does not replace Workflow Inspector, Benchmarks, Evals & Diagnosis, Experiments & Artifacts, or EvidenceOps / MCP.',
            ],
        ),
        'status': status,
        'degraded_reason': degraded_reason,
        'surface_window': surface_window,
        'runtime': runtime,
        'generation_rows': _build_runtime_generation_rows(runtime),
        'retrieval_rows': _build_runtime_retrieval_rows(runtime),
        'vector_rows': _build_runtime_vector_rows(runtime),
        'diagnostics_rows': _build_runtime_diagnostics_rows(runtime, runtime_state),
        'ops_summary': {
            'totalRuns': _safe_int(summary.get('total_runs')),
            'successfulRuns': _safe_int(round(_safe_float(summary.get('success_rate')) * _safe_int(summary.get('total_runs')))),
            'errorRate': round(_safe_float(summary.get('error_rate')), 3),
            'successRate': round(_safe_float(summary.get('success_rate')), 3),
            'needsReviewRate': round(_safe_float(summary.get('needs_review_rate')), 3),
            'avgLatencyS': round(_safe_float(summary.get('avg_latency_s')), 3),
            'p95LatencyS': round(_percentile(latency_values, 0.95), 3),
            'avgTotalTokens': round(_safe_float(summary.get('avg_total_tokens')), 1),
            'throughput24h': throughput_24h,
            'providerSwitchRate': round(sum(1 for entry in surface_entries if bool(entry.get('provider_switch_applied'))) / retrieval_count, 3),
            'recentWindowLabel': surface_window['label'],
            'lastTraceAt': _format_timestamp(surface_entries[0].get('timestamp') if surface_entries else summary.get('latest_timestamp')),
        },
        'retrieval_health': {
            'avgRetrievedChunks': round(_safe_float(summary.get('avg_retrieved_chunks_count')), 2),
            'emptyRetrievalRate': round(empty_retrieval_rate, 3),
            'truncatedPromptRate': round(_safe_float(summary.get('truncated_prompt_rate')), 3),
            'avgContextPressurePct': round(_normalize_ratio_to_unit(summary.get('avg_context_pressure_ratio')) * 100, 1),
            'maxContextPressurePct': round(_normalize_ratio_to_unit(summary.get('max_context_pressure_ratio')) * 100, 1),
            'avgContextUtilizationPct': round(_mean(context_utilization_values) * 100, 1),
        },
        'cost_summary': {
            'totalTokens': _safe_int(summary.get('total_tokens')),
            'avgTotalTokens': round(_safe_float(summary.get('avg_total_tokens')), 1),
            'totalCostUsd': round(_safe_float(summary.get('total_cost_usd')), 4),
            'avgCostUsd': round(_safe_float(summary.get('avg_cost_usd')), 4),
            'pricedRunRate': round(_safe_int(summary.get('costed_runs')) / max(_safe_int(summary.get('total_runs')), 1), 3),
            'totalPromptTokens': total_prompt_tokens,
            'avgPromptTokens': round(avg_prompt_tokens, 1),
            'totalCompletionTokens': total_completion_tokens,
            'avgCompletionTokens': round(avg_completion_tokens, 1),
        },
        'latency_breakdown': non_zero_latency_breakdown,
        'latency_breakdown_meta': {
            'instrumentedRuns': instrumented_stage_runs,
            'totalRuns': len(surface_entries),
            'label': surface_window['label'],
        },
        'provider_breakdown': _build_runtime_provider_breakdown(surface_entries),
        'failure_modes': _build_runtime_failure_modes(surface_entries),
        'recent_traces': _build_recent_trace_rows(surface_entries, runtime_state['document_lookup']),
        'timeline': _build_runtime_timeline(surface_entries),
        'cross_surface_notes': LAB_CROSS_SURFACE_NOTES,
        'additional_runtime_log_paths': runtime_state.get('additional_runtime_sources') or [],
    }
    payload['watchouts'] = _build_runtime_watchouts(runtime_state, payload)
    return payload


def build_lab_overview_payload(
    workspace_root: Path,
    *,
    additional_workflow_history_paths: list[Path] | None = None,
    additional_runtime_log_paths: list[Path] | None = None,
    additional_product_telemetry_paths: list[Path] | None = None,
) -> dict[str, Any]:
    runtime_payload = build_lab_runtime_payload(workspace_root, additional_runtime_log_paths=additional_runtime_log_paths)
    eval_payload = build_lab_evals_payload(workspace_root, additional_product_telemetry_paths=additional_product_telemetry_paths)
    evidence_payload = build_lab_evidenceops_payload(workspace_root)
    workflow_history = _read_json(get_product_workflow_history_path(workspace_root), [])
    if not isinstance(workflow_history, list):
        workflow_history = []
    additional_workflow_history_sources: list[str] = []
    for additional_path in additional_workflow_history_paths or []:
        additional_history = _read_json(additional_path, [])
        if isinstance(additional_history, list) and additional_history:
            additional_workflow_history_sources.append(str(additional_path))
            workflow_history.extend(additional_history)
    workflow_history = sorted(
        [item for item in workflow_history if isinstance(item, dict)],
        key=lambda item: str(item.get('timestamp') or item.get('created_at') or ''),
    )
    workflow_counts: Counter[str] = Counter()
    warning_runs = 0
    for item in workflow_history:
        if not isinstance(item, dict):
            continue
        workflow_label = str(item.get('workflow_label') or item.get('workflow_id') or 'Unknown').strip() or 'Unknown'
        workflow_counts[workflow_label] += 1
        if str(item.get('status') or '').strip().lower() == 'warning':
            warning_runs += 1
    workflow_mix = [{'name': label, 'value': value} for label, value in workflow_counts.most_common(6)]
    review_rate = round((warning_runs / max(len(workflow_history), 1)) * 100, 1) if workflow_history else round(_safe_float(runtime_payload['ops_summary']['needsReviewRate']) * 100, 1)

    runtime = runtime_payload['runtime']
    eval_pass_rate = _safe_float(eval_payload.get('passRate') or 0.0) / 100.0
    open_actions = _safe_int(evidence_payload.get('summary', {}).get('openActions'))
    avg_latency = _safe_float(runtime_payload.get('ops_summary', {}).get('avgLatencyS'))
    p95_latency = _safe_float(runtime_payload.get('ops_summary', {}).get('p95LatencyS'))
    total_runs = _safe_int(runtime_payload.get('ops_summary', {}).get('totalRuns'))

    kpis = [
        {'label': 'Indexed Documents', 'value': _safe_int(runtime.get('indexedDocumentCount')), 'status': 'healthy'},
        {'label': 'Total Chunks', 'value': _safe_int(runtime.get('totalChunks')), 'status': 'healthy'},
        {'label': 'Workflow Runs', 'value': len(workflow_history), 'status': 'healthy' if workflow_history else 'neutral'},
        {'label': 'Open Actions', 'value': open_actions, 'status': 'warning' if open_actions else 'healthy'},
        {'label': 'Eval Pass Rate', 'value': f"{round(eval_pass_rate * 100)}%", 'status': 'healthy' if eval_pass_rate >= 0.8 else 'warning' if eval_pass_rate >= 0.65 else 'error'},
        {'label': 'Avg Latency', 'value': f'{avg_latency:.1f}s' if avg_latency else '—', 'status': 'warning' if avg_latency >= 10 else 'healthy'},
    ]

    alerts: list[dict[str, Any]] = []
    if _safe_float(runtime_payload.get('ops_summary', {}).get('errorRate')) >= 0.2:
        alerts.append({'id': 'runtime-error-rate', 'severity': 'critical', 'title': 'Runtime executions show degraded stability', 'detail': f"{_percent_label(_safe_float(runtime_payload['ops_summary']['errorRate']))} error rate and p95 latency of {p95_latency:.1f}s in persisted traces.", 'source': 'runtime_execution_log', 'timestamp': runtime_payload['meta'].get('updated_at') or _now_iso()})
    if _safe_float(runtime_payload.get('ops_summary', {}).get('needsReviewRate')) >= 0.15:
        alerts.append({'id': 'runtime-review-rate', 'severity': 'warning', 'title': 'Manual review pressure is elevated', 'detail': f"{_percent_label(_safe_float(runtime_payload['ops_summary']['needsReviewRate']))} of recent traces requested review follow-up.", 'source': 'runtime_execution_log', 'timestamp': runtime_payload['meta'].get('updated_at') or _now_iso()})
    if open_actions > 0:
        alerts.append({'id': 'open-actions', 'severity': 'warning', 'title': 'EvidenceOps has open actions waiting for ownership', 'detail': f'{open_actions} open action(s) remain visible in the EvidenceOps surface.', 'source': 'evidenceops_actions', 'timestamp': evidence_payload['meta'].get('updated_at') or _now_iso()})
    if eval_pass_rate < 0.8:
        alerts.append({'id': 'eval-pass-rate', 'severity': 'warning', 'title': 'Eval posture needs attention', 'detail': f"Current eval pass rate is {round(eval_pass_rate * 100)}%; use Evals & Diagnosis for task-level watchlists.", 'source': 'phase8_eval_runs', 'timestamp': eval_payload['meta'].get('updated_at') or _now_iso()})
    if runtime.get('ingestionHealth') != 'healthy':
        alerts.append({'id': 'ingestion-health', 'severity': 'info', 'title': 'Document ingestion is not fully clean', 'detail': f"Ingestion health is {runtime.get('ingestionHealth')}; inspect document library warnings before assuming runtime issues.", 'source': 'rag_store', 'timestamp': runtime_payload['meta'].get('updated_at') or _now_iso()})

    return {
        'ok': True,
        'meta': _runtime_meta(
            workspace_root,
            notes=['Overview compresses runtime, eval, workflow and EvidenceOps signals into one operator-facing triage surface.'],
        ),
        'status': 'live' if total_runs else 'empty',
        'degraded_reason': None if total_runs else 'No persisted workflow or runtime history was found yet.',
        'runtime': runtime,
        'kpis': kpis,
        'alerts': alerts,
        'workflow_mix': workflow_mix,
        'review_rate': review_rate,
        'cross_surface_notes': LAB_CROSS_SURFACE_NOTES,
    }



def _scoped_lab_state_copy(item: dict[str, Any], scope: str) -> dict[str, Any]:
    copied = dict(item)
    copied['scope'] = scope
    copied['is_global'] = scope == 'global'
    return copied


def _state_updated_sort_key(item: dict[str, Any]) -> str:
    return str(item.get('updated_at') or item.get('created_at') or '')


def _load_lab_chat_sessions_with_overlays(
    global_path: Path,
    additional_session_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    seen: set[str] = set()

    for path, scope in [*((item, 'session_overlay') for item in (additional_session_paths or [])), (global_path, 'global')]:
        for session in load_lab_chat_sessions(path):
            if not isinstance(session, dict):
                continue
            session_id = str(session.get('session_id') or '').strip()
            if not session_id or session_id in seen:
                continue
            seen.add(session_id)
            sessions.append(_scoped_lab_state_copy(session, scope))

    sessions.sort(key=_state_updated_sort_key, reverse=True)
    return sessions


def _load_lab_workflow_runs_with_overlays(
    global_path: Path,
    additional_run_paths: list[Path] | None = None,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []

    for path, scope in [(global_path, 'global'), *((item, 'session_overlay') for item in (additional_run_paths or []))]:
        for run in load_lab_workflow_runs(path):
            if not isinstance(run, dict):
                continue
            runs.append(_scoped_lab_state_copy(run, scope))

    runs.sort(key=_state_updated_sort_key, reverse=True)
    return runs



def build_lab_chat_payload(workspace_root: Path, session_id: str | None = None, *, additional_session_paths: list[Path] | None = None) -> dict[str, Any]:
    runtime_payload = build_lab_runtime_payload(workspace_root)
    documents = _workspace_documents(workspace_root)
    document_lookup = _document_lookup(documents)
    global_chat_sessions_path = get_lab_chat_sessions_path(workspace_root)
    sessions = _load_lab_chat_sessions_with_overlays(global_chat_sessions_path, additional_session_paths)
    active_session = None
    if session_id:
        active_session = next((session for session in sessions if str(session.get('session_id') or '') == str(session_id)), None)
    if active_session is None and sessions:
        active_session = sessions[0]

    default_document_ids = [str(document.get('document_id') or '') for document in documents[:4] if str(document.get('document_id') or '').strip()]
    selected_document_ids = [str(item) for item in (active_session.get('document_ids') if isinstance(active_session, dict) else []) if str(item or '').strip()] or default_document_ids
    selected_documents = [document_lookup[doc_id] for doc_id in selected_document_ids if doc_id in document_lookup]

    messages: list[dict[str, Any]] = []
    if isinstance(active_session, dict):
        for message in active_session.get('messages', []):
            if not isinstance(message, dict):
                continue
            message_diagnostics = message.get('diagnostics') if isinstance(message.get('diagnostics'), dict) else {}
            messages.append(
                {
                    'id': str(message.get('id') or ''),
                    'role': str(message.get('role') or 'assistant'),
                    'content': str(message.get('content') or ''),
                    'timestamp': _format_timestamp(message.get('timestamp')),
                    'sources': message.get('sources') if isinstance(message.get('sources'), list) else [],
                    'diagnostics': message_diagnostics,
                }
            )
    if not messages:
        seed_sources = [{'label': str(document.get('name') or 'Document'), 'detail': str(document.get('loader_strategy_label') or 'indexed'), 'score': 0.9} for document in selected_documents[:3]]
        messages = [
            {
                'id': 'assistant-seed',
                'role': 'assistant',
                'content': 'Grounded AI LAB chat is ready. Use this surface to probe the selected documents, validate retrieval quality and persist diagnostic conversations.',
                'timestamp': _now_iso(),
                'sources': seed_sources,
                'diagnostics': {'seed': True},
            }
        ]

    sessions_summary = []
    for session in sessions:
        runtime = session.get('runtime') if isinstance(session.get('runtime'), dict) else {}
        session_messages = session.get('messages') if isinstance(session.get('messages'), list) else []
        grounded_messages = sum(1 for item in session_messages if isinstance(item, dict) and isinstance(item.get('sources'), list) and item.get('sources'))
        sessions_summary.append(
            {
                'session_id': str(session.get('session_id') or ''),
                'scope': str(session.get('scope') or 'global'),
                'is_global': bool(session.get('scope') == 'global'),
                'title': str(session.get('title') or 'AI Lab chat session'),
                'updated_at': _format_timestamp(session.get('updated_at') or session.get('created_at')),
                'message_count': len(session_messages),
                'status': str(session.get('status') or 'active'),
                'document_count': len([item for item in (session.get('document_ids') or []) if str(item or '').strip()]),
                'last_error': str(session.get('last_error') or '').strip() or None,
                'last_model': str(runtime.get('model') or runtime.get('generationModel') or ''),
                'avg_latency_s': _safe_float(runtime.get('avg_latency_s') or 0.0) or None,
                'grounded_messages': grounded_messages,
            }
        )

    active_runtime = active_session.get('runtime') if isinstance(active_session, dict) and isinstance(active_session.get('runtime'), dict) else {}
    assistant_messages = [message for message in messages if message.get('role') == 'assistant']
    sourced_assistant_messages = [message for message in assistant_messages if isinstance(message.get('sources'), list) and message.get('sources')]
    source_counts = [len(message.get('sources') or []) for message in sourced_assistant_messages]
    warning_count = sum(1 for message in messages if isinstance(message.get('diagnostics'), dict) and _safe_int((message.get('diagnostics') or {}).get('warning_count')) > 0)
    artifact_hits = []
    for message in messages:
        diagnostics = message.get('diagnostics') if isinstance(message.get('diagnostics'), dict) else {}
        artifact_path = str(diagnostics.get('artifact_path') or '').strip()
        if artifact_path:
            artifact_hits.append(artifact_path)

    retrieval_quality = {
        'Strategy': runtime_payload['runtime'].get('retrievalStrategy') or 'hybrid',
        'Top-K': runtime_payload['runtime'].get('topK') or 0,
        'Rerank Pool': runtime_payload['runtime'].get('rerankPoolSize') or 0,
        'Avg Retrieved Chunks': runtime_payload.get('retrieval_health', {}).get('avgRetrievedChunks') or 0,
        'Empty Retrieval Rate': _percent_label(_safe_float(runtime_payload.get('retrieval_health', {}).get('emptyRetrievalRate') or 0.0)),
        'Grounded Assistant Rate': _percent_label(len(sourced_assistant_messages) / max(len(assistant_messages), 1)) if assistant_messages else '0%',
    }
    session_diagnostics = {
        'Messages': len(messages),
        'Documents': len(selected_documents),
        'Provider': str(active_runtime.get('provider') or runtime_payload['runtime'].get('generationProvider') or 'ollama'),
        'Model': str(active_runtime.get('model') or runtime_payload['runtime'].get('generationModel') or 'unknown'),
        'Avg Latency': f"{_safe_float(active_runtime.get('avg_latency_s') or runtime_payload.get('ops_summary', {}).get('avgLatencyS') or 0.0):.1f}s",
        'Last Tokens': _safe_int(active_runtime.get('total_tokens') or 0),
        'Top-K': runtime_payload['runtime'].get('topK') or 0,
        'Avg Sources / Reply': round(_mean([float(value) for value in source_counts]), 1) if source_counts else 0,
    }
    grounding_overview = {
        'Selected Documents': len(selected_documents),
        'Available Chunks': sum(_safe_int(document.get('chunk_count') or 0) for document in selected_documents),
        'Context Window': f"{_safe_int(runtime_payload['runtime'].get('resolvedContext') or 0):,} tokens",
        'Context Pressure': _percent_label(_normalize_ratio_to_unit(runtime_payload['runtime'].get('contextPressure') or 0.0)),
        'Artifacts Captured': len(artifact_hits),
    }

    session_timeline = []
    if isinstance(active_session, dict):
        for message in (active_session.get('messages') or [])[-10:]:
            if not isinstance(message, dict):
                continue
            diagnostics = message.get('diagnostics') if isinstance(message.get('diagnostics'), dict) else {}
            role = str(message.get('role') or '')
            title = 'User prompt' if role == 'user' else 'Assistant response'
            status = 'warning' if _safe_int(diagnostics.get('warning_count') or 0) > 0 else 'success'
            detail_bits = []
            if role != 'user' and isinstance(message.get('sources'), list):
                detail_bits.append(f"{len(message.get('sources') or [])} source(s)")
            if _safe_int(diagnostics.get('total_tokens') or 0) > 0:
                detail_bits.append(f"{_safe_int(diagnostics.get('total_tokens'))} tokens")
            if _safe_float(diagnostics.get('latency_s') or 0.0) > 0:
                detail_bits.append(f"{_safe_float(diagnostics.get('latency_s')):.1f}s")
            if str(diagnostics.get('artifact_path') or '').strip():
                detail_bits.append('artifact captured')
            session_timeline.append(
                {
                    'id': str(message.get('id') or ''),
                    'label': title,
                    'detail': ' · '.join(detail_bits) or _trim_text(message.get('content'), max_chars=96),
                    'timestamp': _format_timestamp(message.get('timestamp')),
                    'status': status,
                }
            )

    meta_notes = [
        'Chat now persists runnable AI LAB sessions instead of replaying mock messages.',
        'Use Runtime & Observability for system posture, Workflow Inspector for deterministic workflow traces and EvidenceOps for action governance.',
    ]
    if not sessions:
        meta_notes.append('No persisted AI LAB chat sessions were found yet; the first message creates one automatically.')

    active_session_status = str(active_session.get('status') or 'active') if isinstance(active_session, dict) else 'empty'
    grounded_message_rate = len(sourced_assistant_messages) / max(len(assistant_messages), 1) if assistant_messages else 0.0

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=meta_notes),
        'status': 'live' if sessions else 'derived',
        'degraded_reason': None,
        'capabilities': {'can_send': bool(selected_documents), 'reason': None if selected_documents else 'At least one indexed document is required to send grounded AI LAB chat messages.'},
        'active_session_id': str(active_session.get('session_id') or '') if isinstance(active_session, dict) else None,
        'sessions': sessions_summary,
        'messages': messages,
        'suggested_prompts': [
            'Summarize the main control gaps in the selected evidence.',
            'Turn the findings into next actions with owners and due dates.',
            'What appears risky, unsupported or contradictory in these documents?',
        ],
        'selected_documents': selected_documents,
        'session_diagnostics': session_diagnostics,
        'retrieval_quality': retrieval_quality,
        'grounding_overview': grounding_overview,
        'session_timeline': session_timeline,
        'summary': {
            'sessionCount': len(sessions_summary),
            'selectedDocumentIds': selected_document_ids,
            'activeSessionStatus': active_session_status,
            'groundedMessageRate': round(grounded_message_rate, 3),
            'artifactCount': len(artifact_hits),
            'warningCount': warning_count,
            'avgSourcesPerAssistant': round(_mean([float(value) for value in source_counts]), 2) if source_counts else 0.0,
            'lastLatencyS': _safe_float(active_runtime.get('avg_latency_s') or 0.0),
        },
    }

def _result_sources(result: Any, document_lookup: dict[str, dict[str, Any]], document_ids: list[str]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    grounded_preview = getattr(result, 'grounding_preview', None)
    source_block_count = _safe_int(getattr(grounded_preview, 'source_block_count', 0) if grounded_preview is not None else 0)
    context_chars = _safe_int(getattr(grounded_preview, 'context_chars', 0) if grounded_preview is not None else 0)
    for index, document_id in enumerate(document_ids[:4]):
        document = document_lookup.get(document_id, {})
        detail = []
        if source_block_count:
            detail.append(f'{source_block_count} source block(s)')
        if context_chars:
            detail.append(f'{context_chars} context chars')
        sources.append(
            {
                'label': str(document.get('name') or document_id),
                'detail': ' · '.join(detail) if detail else str(document.get('loader_strategy_label') or 'grounded document'),
                'score': 0.9 - (index * 0.05),
            }
        )
    return sources


def _workflow_request_defaults(workspace_root: Path) -> tuple[str, str | None]:
    controls_state = load_runtime_controls_state(get_runtime_controls_state_path(workspace_root)) or {}
    profile = controls_state.get('profile') if isinstance(controls_state.get('profile'), dict) else {}
    return str(profile.get('primaryConnectionId') or 'ollama'), str(profile.get('primaryModel') or '') or None



def _normalize_chat_prompt(value: str) -> str:
    return ' '.join(str(value or '').split()).strip().casefold()


def _is_automated_lab_chat_prompt(value: str) -> bool:
    # AI Lab suggested prompts should behave like normal grounded chat turns.
    # Older builds routed exact suggested prompts into the product document_review
    # workflow, which produced template-like answers that did not match the prompt.
    return False


def _lab_chat_suggested_prompt_instruction(value: str) -> str | None:
    normalized = _normalize_chat_prompt(value)

    if normalized == _normalize_chat_prompt('Summarize the main control gaps in the selected evidence.'):
        return (
            'Answer as a grounded control-gap review. Use only the selected document evidence.\n'
            'Return concise bullets with: Control gap, Evidence, Risk/impact, and Suggested mitigation.\n'
            'If a gap is inferred rather than explicitly stated, label it as an inference.'
        )

    if normalized == _normalize_chat_prompt('Turn the findings into next actions with owners and due dates.'):
        return (
            'Answer as a grounded action plan. Use only the selected document evidence.\n'
            'Return action bullets with these fields: Action, Owner role, Timing/due date, Evidence, Priority.\n'
            'If the document does not name a specific owner or due date, say "Proposed owner role" '
            'or "Proposed timing" instead of inventing a named person or exact date.'
        )

    if normalized == _normalize_chat_prompt('What appears risky, unsupported or contradictory in these documents?'):
        return (
            'Answer as a grounded risk/contradiction review. Use only the selected document evidence.\n'
            'Group the answer into: Risky, Unsupported, Contradictory, and Verify next.\n'
            'For every item, include the evidence basis or state that the item is an inference.'
        )

    return None


def _apply_lab_chat_prompt_policy(content: str) -> str:
    instruction = _lab_chat_suggested_prompt_instruction(content)
    if not instruction:
        return content

    return (
        f'{instruction}\n\n'
        f'User request: {content}'
    )


def _looks_portuguese(value: str) -> bool:
    lowered = f' {str(value or "").casefold()} '
    markers = (
        ' o ', ' a ', ' os ', ' as ', ' que ', ' esse ', ' essa ', ' documento ', ' documentos ',
        ' quer ', ' dizer ', ' sobre ', ' quais ', ' como ', ' por que ', ' risco ', ' riscos ',
        ' ação ', ' ações ', ' recomenda', ' evidência', ' evidencias', ' contrato ',
    )
    return any(marker in lowered for marker in markers)


def _is_summary_like_question(value: str) -> bool:
    lowered = str(value or '').casefold()
    return any(
        marker in lowered
        for marker in (
            'o que', 'quer dizer', 'querendo dizer', 'significa', 'explique', 'explica',
            'resuma', 'resumo', 'summary', 'summarize', 'what is this document', 'what does',
            'main point', 'main points', 'about this document',
        )
    )


def _chat_question_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[A-Za-zÀ-ÿ0-9]{3,}", str(value or '').casefold())
        if token not in LAB_CHAT_STOPWORDS
    }
    return tokens


def _extract_context_blocks(context: str) -> list[dict[str, str]]:
    cleaned_context = str(context or '').strip()
    if not cleaned_context:
        return []
    blocks: list[dict[str, str]] = []
    source_pattern = re.compile(r"^\[Source:\s*([^\]]+)\]\s*([\s\S]*?)(?=^\[Source:|\Z)", re.MULTILINE)
    for match in source_pattern.finditer(cleaned_context):
        source = ' '.join(str(match.group(1) or 'Grounded source').split()).strip()
        text = ' '.join(str(match.group(2) or '').split()).strip()
        if not text:
            continue
        blocks.append({'source': source or 'Grounded source', 'text': text})
    if blocks:
        return blocks

    section_pattern = re.compile(r"^\[([A-Z][A-Z\s]+)\]\s*([\s\S]*?)(?=^\[[A-Z][A-Z\s]+\]|\Z)", re.MULTILINE)
    for match in section_pattern.finditer(cleaned_context):
        source = ' '.join(str(match.group(1) or 'Grounded context').split()).title()
        text = ' '.join(str(match.group(2) or '').split()).strip()
        if text:
            blocks.append({'source': source, 'text': text})
    if blocks:
        return blocks

    return [{'source': 'Grounded context', 'text': ' '.join(cleaned_context.split())}]


def _score_context_block(question: str, block: dict[str, str], position: int) -> float:
    tokens = _chat_question_tokens(question)
    source = str(block.get('source') or '')
    text = str(block.get('text') or '')
    haystack = f'{source} {text}'.casefold()
    if not tokens:
        return max(0.05, 1.0 - position * 0.05)
    overlap = sum(1 for token in tokens if token in haystack)
    name_bonus = sum(0.08 for token in tokens if token in source.casefold())
    return (overlap / max(len(tokens), 1)) + name_bonus + max(0.0, 0.2 - position * 0.025)


def _split_evidence_sentences(text: str) -> list[str]:
    normalized = ' '.join(str(text or '').split()).strip()
    if not normalized:
        return []
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9])', normalized)
    sentences: list[str] = []
    for sentence in raw_sentences:
        candidate = sentence.strip(' -•\t')
        if len(candidate) < 35:
            continue
        if len(candidate) > 360:
            candidate = candidate[:357].rsplit(' ', 1)[0].rstrip(' ,;:') + '...'
        sentences.append(candidate)
    if sentences:
        return sentences
    fallback = normalized[:357].rsplit(' ', 1)[0].rstrip(' ,;:') or normalized[:357]
    return [fallback + ('...' if len(normalized) > len(fallback) else '')]


def _pick_relevant_evidence(question: str, blocks: list[dict[str, str]], *, limit: int = 4) -> list[dict[str, str]]:
    if not blocks:
        return []
    summary_like = _is_summary_like_question(question)
    scored_blocks = [
        (_score_context_block(question, block, index), index, block)
        for index, block in enumerate(blocks)
    ]
    if summary_like:
        # Preserve the opening evidence when the user asks what the selected document is saying.
        scored_blocks.sort(key=lambda item: (item[1] >= 4, -item[0], item[1]))
    else:
        scored_blocks.sort(key=lambda item: (-item[0], item[1]))

    evidence: list[dict[str, str]] = []
    seen: set[str] = set()
    question_tokens = _chat_question_tokens(question)
    for score, _, block in scored_blocks:
        sentences = _split_evidence_sentences(block.get('text', ''))
        if not sentences:
            continue
        if question_tokens and not summary_like:
            sentences.sort(
                key=lambda sentence: (
                    -sum(1 for token in question_tokens if token in sentence.casefold()),
                    len(sentence),
                )
            )
        sentence = sentences[0]
        key = f"{block.get('source')}::{sentence}".casefold()
        if key in seen:
            continue
        seen.add(key)
        evidence.append({'source': str(block.get('source') or 'Grounded source'), 'excerpt': sentence, 'score': f'{score:.3f}'})
        if len(evidence) >= limit:
            break
    return evidence


def _build_document_qa_answer(*, question: str, documents: list[dict[str, Any]], evidence: list[dict[str, str]], context_chars: int) -> str:
    pt = _looks_portuguese(question)
    selected_names = [str(document.get('name') or document.get('document_id') or '').strip() for document in documents if str(document.get('name') or document.get('document_id') or '').strip()]
    if not evidence:
        if pt:
            return (
                'Não encontrei contexto suficiente nos documentos selecionados para responder essa pergunta com segurança. '
                'Tente selecionar outro documento ou reformular a pergunta com uma palavra-chave mais específica.'
            )
        return (
            'I could not find enough grounded context in the selected documents to answer that question confidently. '
            'Try selecting another document or asking with a more specific keyword.'
        )

    if pt:
        intro = 'Com base nos trechos recuperados'
        if selected_names:
            intro += f" de {', '.join(selected_names[:2])}" + (f" + {len(selected_names) - 2} outro(s)" if len(selected_names) > 2 else '')
        intro += ', a resposta é:'
        bullets = '\n'.join(f"- {item['excerpt']}" for item in evidence[:3])
        sources = '\n'.join(f"- {item['source']}: “{_trim_text(item['excerpt'], max_chars=180)}”" for item in evidence[:4])
        return (
            f"{intro}\n\n"
            f"{bullets}\n\n"
            f"Evidência usada:\n{sources}\n\n"
            f"Grounding: {len(evidence)} trecho(s) selecionado(s), {context_chars:,} caracteres de contexto."
        )

    intro = 'Based on the retrieved evidence'
    if selected_names:
        intro += f" from {', '.join(selected_names[:2])}" + (f" + {len(selected_names) - 2} other(s)" if len(selected_names) > 2 else '')
    intro += ', the answer is:'
    bullets = '\n'.join(f"- {item['excerpt']}" for item in evidence[:3])
    sources = '\n'.join(f"- {item['source']}: “{_trim_text(item['excerpt'], max_chars=180)}”" for item in evidence[:4])
    return (
        f"{intro}\n\n"
        f"{bullets}\n\n"
        f"Evidence used:\n{sources}\n\n"
        f"Grounding: {len(evidence)} selected excerpt(s), {context_chars:,} context characters."
    )


def _normalize_lab_chat_source_score(value: object) -> float | None:
    try:
        score = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None

    if score != score or score <= 0:
        return None

    if score > 1:
        score = score / 100 if score <= 100 else 1.0

    return min(0.98, max(0.01, score))


def _sources_from_evidence(evidence: list[dict[str, str]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for index, item in enumerate(evidence[:6]):
        source: dict[str, Any] = {
            'label': str(item.get('source') or f'Source {index + 1}'),
            'detail': _trim_text(str(item.get('excerpt') or ''), max_chars=240),
            'score_kind': 'grounded_source',
        }
        normalized_score = _normalize_lab_chat_source_score(item.get('score'))
        if normalized_score is not None:
            source['score'] = normalized_score
            source['score_kind'] = 'retrieval_relevance'
            source['score_label'] = 'Relevance'
        sources.append(source)
    return sources



def _build_lab_chat_task_request(
    *,
    content: str,
    document_ids: list[str],
    provider: str,
    model: str | None,
) -> TaskExecutionRequest:
    return TaskExecutionRequest(
        task_type='document_agent',
        input_text=str(content or '').strip(),
        use_rag_context=False,
        use_document_context=True,
        source_document_ids=[str(document_id) for document_id in document_ids if str(document_id or '').strip()],
        context_strategy='retrieval',
        provider=provider,
        model=model,
        telemetry={
            'surface': 'lab_chat',
            'chat_mode': 'grounded_question_answering',
            'agent_intent': 'document_question',
            'agent_intent_reason': 'lab_chat_question_mode',
            'agent_tool': 'consult_documents',
            'agent_tool_reason': 'lab_chat_direct_question',
            'agent_answer_mode': 'friendly',
        },
    )


def _render_chat_assistant_content(result: Any) -> str:
    structured_result = getattr(result, 'structured_result', None)
    if structured_result is None and isinstance(result, StructuredResult):
        structured_result = result
    payload = getattr(structured_result, 'validated_output', None)
    if isinstance(payload, DocumentAgentPayload):
        summary = str(payload.summary or '').strip()
        if payload.tool_used == 'consult_documents':
            return summary or 'Could not generate a grounded document answer.'
        parts: list[str] = []
        if summary:
            parts.append(summary)
        if payload.key_points:
            parts.append('Evidence:\n' + '\n'.join(f'- {point}' for point in payload.key_points[:6] if str(point or '').strip()))
        if payload.limitations:
            parts.append('Caveats:\n' + '\n'.join(f'- {item}' for item in payload.limitations[:4] if str(item or '').strip()))
        if payload.recommended_actions:
            parts.append('Next actions:\n' + '\n'.join(f'- {item}' for item in payload.recommended_actions[:4] if str(item or '').strip()))
        return '\n\n'.join(part for part in parts if part).strip() or 'The document agent completed, but no response text was returned.'

    summary = str(getattr(result, 'summary', '') or '').strip()
    recommendation = str(getattr(result, 'recommendation', '') or '').strip()
    highlights = [str(item).strip() for item in (getattr(result, 'highlights', None) or []) if str(item or '').strip()]
    parts = [summary]
    if highlights:
        parts.append('Highlights:\n' + '\n'.join(f'- {item}' for item in highlights[:4]))
    if recommendation:
        parts.append(f'Recommendation: {recommendation}')
    return '\n\n'.join(part for part in parts if part).strip()


def _sources_from_document_agent_payload(payload: DocumentAgentPayload) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for index, source in enumerate(payload.sources[:6]):
        item: dict[str, Any] = {
            'label': str(getattr(source, 'source', None) or getattr(source, 'document_id', None) or f'Source {index + 1}'),
            'detail': _trim_text(str(getattr(source, 'snippet', None) or getattr(source, 'document_id', None) or 'grounded document'), max_chars=240),
            'score_kind': 'grounded_source',
        }

        normalized_score = _normalize_lab_chat_source_score(getattr(source, 'score', None))
        if normalized_score is not None:
            item['score'] = normalized_score
            item['score_kind'] = 'retrieval_relevance'
            item['score_label'] = 'Relevance'

        sources.append(item)
    return sources




LAB_CHAT_CONTEXTUAL_FOLLOWUPS = {
    'what else',
    'what else?',
    'anything else',
    'anything else?',
    'continue',
    'continue.',
    'go on',
    'go on.',
    'tell me more',
    'tell me more.',
    'and more',
    'more',
    'mais',
    'e mais',
    'o que mais',
    'o que mais?',
    'e o resto',
    'e o resto?',
    'continue',
    'continua',
    'continua.',
    'mais alguma coisa',
    'mais alguma coisa?',
}


def _is_contextual_chat_followup(content: str) -> bool:
    normalized = re.sub(r'\s+', ' ', str(content or '').strip().lower())
    normalized = normalized.strip()
    if normalized in LAB_CHAT_CONTEXTUAL_FOLLOWUPS:
        return True
    if len(normalized.split()) <= 4 and normalized in {'what more', 'what other', 'what about the rest', 'and then'}:
        return True
    return False


def _build_lab_chat_recent_context(session: dict[str, Any], *, max_messages: int = 6, max_chars: int = 1400) -> str:
    messages = session.get('messages') if isinstance(session.get('messages'), list) else []
    useful = []
    for message in messages[-max_messages:]:
        if not isinstance(message, dict):
            continue
        role = str(message.get('role') or '').strip().lower()
        content = str(message.get('content') or '').strip()
        if role not in {'user', 'assistant'} or not content:
            continue
        label = 'User' if role == 'user' else 'Assistant'
        useful.append(f'{label}: {_trim_text(content, max_chars=360)}')
    context = '\n'.join(useful)
    if len(context) > max_chars:
        context = context[-max_chars:]
    return context.strip()


def _contextualize_lab_chat_content(content: str, session: dict[str, Any]) -> str:
    normalized = str(content or '').strip()
    if not normalized or not _is_contextual_chat_followup(normalized):
        return normalized

    recent_context = _build_lab_chat_recent_context(session)
    if not recent_context:
        return normalized

    return (
        'The user is asking a follow-up question in the same AI Lab chat session.\n'
        'Use the recent conversation context below to resolve the follow-up, then answer the latest user message.\n\n'
        f'Recent conversation:\n{recent_context}\n\n'
        f'Latest user message: {normalized}'
    )


def _execute_lab_document_qa_turn(
    *,
    bootstrap: ProductBootstrap,
    sessions_path: Path,
    session_id: str,
    content: str,
    document_ids: list[str],
    provider: str,
    model: str | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        structured_request = _build_lab_chat_task_request(
            content=content,
            document_ids=document_ids,
            provider=provider,
            model=model,
        )
        structured_result = run_structured_execution_workflow(structured_request, strategy='direct')
        payload = structured_result.validated_output
        if structured_result.success and isinstance(payload, DocumentAgentPayload):
            assistant_content = _render_chat_assistant_content(structured_result)
            if assistant_content.strip():
                sources = _sources_from_document_agent_payload(payload)
                latency_s = round(time.perf_counter() - started, 3)
                assistant_message = append_lab_chat_message(
                    sessions_path,
                    session_id=session_id,
                    role='assistant',
                    content=assistant_content,
                    sources=sources,
                    diagnostics={
                        'workflow_id': 'lab_document_qa',
                        'workflow_label': 'Grounded Document Q&A',
                        'provider': provider,
                        'model': model,
                        'context_strategy': 'retrieval',
                        'structured_execution_id': structured_result.execution_id,
                        'tool_used': payload.tool_used,
                        'answer_mode': payload.answer_mode,
                        'confidence': payload.confidence,
                        'source_count': len(sources),
                        'latency_s': latency_s,
                    },
                )
                update_lab_chat_session_runtime(
                    sessions_path,
                    session_id=session_id,
                    runtime={
                        'provider': provider,
                        'model': model,
                        'workflow_id': 'lab_document_qa',
                        'avg_latency_s': latency_s,
                        'total_tokens': _safe_float(structured_result.execution_metadata.get('total_tokens') if isinstance(structured_result.execution_metadata, dict) else 0.0),
                        'warning_count': len(payload.limitations or []),
                        'context_chars': _safe_int(structured_result.execution_metadata.get('context_chars') if isinstance(structured_result.execution_metadata, dict) else 0),
                        'source_count': len(sources),
                        'grounded_documents': document_ids,
                    },
                    status='completed',
                    last_error=None,
                    document_ids=document_ids,
                )
                return {'assistant_message': assistant_message, 'artifact_path': None}
    except Exception:
        # Fall back to deterministic extractive answering below so custom user questions never collapse into canned review output.
        pass

    context = build_structured_document_context(
        query=content,
        document_ids=document_ids,
        strategy='retrieval',
        max_chunks=8,
        max_chars=10000,
    )
    blocks = _extract_context_blocks(context)
    ranked_blocks = [
        block
        for _, block in sorted(
            enumerate(blocks),
            key=lambda item: -_score_context_block(content, item[1], item[0]),
        )
    ]
    evidence = _pick_relevant_evidence(content, ranked_blocks, limit=4)
    documents = _workspace_documents(bootstrap.workspace_root)
    document_lookup = _document_lookup(documents)
    selected_documents = [document_lookup[document_id] for document_id in document_ids if document_id in document_lookup]
    assistant_content = _build_document_qa_answer(
        question=content,
        documents=selected_documents,
        evidence=evidence,
        context_chars=len(context),
    )
    sources = _sources_from_evidence(evidence)
    assistant_message = append_lab_chat_message(
        sessions_path,
        session_id=session_id,
        role='assistant',
        content=assistant_content,
        sources=sources,
        diagnostics={
            'workflow_id': 'lab_document_qa',
            'workflow_label': 'Grounded Document Q&A',
            'provider': provider,
            'model': model,
            'context_strategy': 'retrieval',
            'context_chars': len(context),
            'source_count': len(sources),
            'question_tokens': sorted(_chat_question_tokens(content))[:20],
            'latency_s': round(time.perf_counter() - started, 3),
        },
    )
    update_lab_chat_session_runtime(
        sessions_path,
        session_id=session_id,
        runtime={
            'provider': provider,
            'model': model,
            'workflow_id': 'lab_document_qa',
            'avg_latency_s': round(time.perf_counter() - started, 3),
            'total_tokens': 0.0,
            'warning_count': 0,
            'context_chars': len(context),
            'source_count': len(sources),
            'grounded_documents': document_ids,
        },
        status='completed',
        last_error=None,
        document_ids=document_ids,
    )
    return {'assistant_message': assistant_message, 'artifact_path': None}


def execute_lab_chat_turn(
    *,
    bootstrap: ProductBootstrap,
    session_id: str,
    content: str,
    document_ids: list[str] | None = None,
    sessions_path: Path | None = None,
) -> dict[str, Any]:
    normalized_content = str(content or '').strip()
    if not normalized_content:
        raise ValueError('Message content is required.')

    sessions_path = sessions_path or get_lab_chat_sessions_path(bootstrap.workspace_root)
    session = get_lab_chat_session(sessions_path, session_id)
    if session is None:
        raise KeyError(f'Chat session not found: {session_id}')

    current_document_ids = [str(item) for item in (document_ids or session.get('document_ids') or []) if str(item or '').strip()]
    if not current_document_ids:
        current_document_ids = [str(document.get('document_id') or '') for document in _workspace_documents(bootstrap.workspace_root)[:3] if str(document.get('document_id') or '').strip()]
    if not current_document_ids:
        raise ValueError('At least one indexed document is required to execute AI LAB chat.')

    effective_content = _apply_lab_chat_prompt_policy(_contextualize_lab_chat_content(normalized_content, session))

    if str(session.get('title') or '').strip().lower() == 'ai lab chat session':
        session['title'] = _trim_text(normalized_content, max_chars=72) or 'AI Lab chat session'
        session['document_ids'] = current_document_ids
        session = upsert_lab_chat_session(sessions_path, session)

    append_lab_chat_message(sessions_path, session_id=session_id, role='user', content=normalized_content)

    provider, model = _workflow_request_defaults(bootstrap.workspace_root)
    if not _is_automated_lab_chat_prompt(normalized_content):
        try:
            response = _execute_lab_document_qa_turn(
                bootstrap=bootstrap,
                sessions_path=sessions_path,
                session_id=session_id,
                content=effective_content,
                document_ids=current_document_ids,
                provider=provider,
                model=model,
            )
            if _is_contextual_chat_followup(normalized_content):
                assistant_message = response.get('assistant_message') if isinstance(response, dict) else None
                if isinstance(assistant_message, dict):
                    diagnostics = assistant_message.get('diagnostics') if isinstance(assistant_message.get('diagnostics'), dict) else {}
                    diagnostics['conversation_context_used'] = True
                    diagnostics['original_user_message'] = normalized_content
                    assistant_message['diagnostics'] = diagnostics
                response['contextualized'] = True
            return response
        except Exception as error:
            update_lab_chat_session_runtime(
                sessions_path,
                session_id=session_id,
                runtime={'provider': provider, 'model': model, 'document_ids': current_document_ids, 'workflow_id': 'lab_document_qa'},
                status='error',
                last_error=str(error),
                document_ids=current_document_ids,
            )
            raise

    request = ProductWorkflowRequest(
        workflow_id='document_review',
        document_ids=current_document_ids,
        input_text=effective_content,
        provider=provider,
        model=model,
        context_strategy='retrieval',
    )

    try:
        from src.product.service import run_product_workflow as _run_product_workflow

        result = _run_product_workflow(request)
        debug_metadata = getattr(result, 'debug_metadata', {}) if isinstance(getattr(result, 'debug_metadata', None), dict) else {}
        highlights = [str(item) for item in (result.highlights or []) if str(item or '').strip()]
        assistant_parts = [str(result.summary or '').strip()]
        if highlights:
            assistant_parts.append('Highlights:\n' + '\n'.join(f'- {item}' for item in highlights[:4]))
        if str(result.recommendation or '').strip():
            assistant_parts.append(f"Recommendation: {result.recommendation}")
        assistant_content = '\n\n'.join(part for part in assistant_parts if part)
        documents = _workspace_documents(bootstrap.workspace_root)
        sources = _result_sources(result, _document_lookup(documents), current_document_ids)
        artifact_path = None
        artifact_label = None
        if result.artifacts and isinstance(result.artifacts[0], dict):
            artifact_path = str(result.artifacts[0].get('path') or result.artifacts[0].get('artifact_path') or '').strip() or None
            artifact_label = str(result.artifacts[0].get('label') or result.artifacts[0].get('name') or '').strip() or None
        assistant_message = append_lab_chat_message(
            sessions_path,
            session_id=session_id,
            role='assistant',
            content=assistant_content or 'The workflow completed, but no assistant summary was returned.',
            sources=sources,
            diagnostics={
                'workflow_id': result.workflow_id,
                'workflow_label': result.workflow_label,
                'warning_count': len(result.warnings or []),
                'artifact_count': len(result.artifacts or []),
                'artifact_path': artifact_path,
                'artifact_label': artifact_label,
                'latency_s': _safe_float(debug_metadata.get('latency_s') or 0.0),
                'total_tokens': _safe_float(debug_metadata.get('total_tokens') or 0.0),
                'context_chars': _safe_int(getattr(result.grounding_preview, 'context_chars', 0) if getattr(result, 'grounding_preview', None) is not None else debug_metadata.get('context_chars') or 0),
                'source_count': len(sources),
            },
        )
        update_lab_chat_session_runtime(
            sessions_path,
            session_id=session_id,
            runtime={
                'provider': provider,
                'model': model,
                'workflow_id': result.workflow_id,
                'avg_latency_s': _safe_float(debug_metadata.get('latency_s') or 0.0),
                'total_tokens': _safe_float(debug_metadata.get('total_tokens') or 0.0),
                'warning_count': len(result.warnings or []),
                'artifact_path': artifact_path,
                'artifact_label': artifact_label,
                'context_chars': _safe_int(getattr(result.grounding_preview, 'context_chars', 0) if getattr(result, 'grounding_preview', None) is not None else debug_metadata.get('context_chars') or 0),
                'source_count': len(sources),
                'grounded_documents': current_document_ids,
            },
            status='completed' if not result.warnings else 'completed',
            last_error=None,
            document_ids=current_document_ids,
        )
        return {'assistant_message': assistant_message, 'artifact_path': artifact_path}
    except Exception as error:
        update_lab_chat_session_runtime(
            sessions_path,
            session_id=session_id,
            runtime={'provider': provider, 'model': model, 'document_ids': current_document_ids},
            status='error',
            last_error=str(error),
            document_ids=current_document_ids,
        )
        raise

def _load_document_agent_log(workspace_root: Path) -> list[dict[str, Any]]:
    return _read_json(get_phase6_document_agent_log_path(workspace_root), [])


def _build_workflow_task_options(workspace_root: Path) -> list[dict[str, Any]]:
    catalog = build_product_workflow_catalog()
    history = _read_json(get_product_workflow_history_path(workspace_root), [])
    counts: Counter[str] = Counter()
    for item in history:
        if isinstance(item, dict):
            counts[str(item.get('workflow_id') or '').strip() or 'unknown'] += 1
    options: list[dict[str, Any]] = []
    for workflow_id, label in WORKFLOW_TASK_LABELS.items():
        definition = catalog.get(workflow_id)
        description = WORKFLOW_DESCRIPTIONS.get(workflow_id)
        if definition is not None and getattr(definition, 'description', None):
            description = str(getattr(definition, 'description'))
        options.append(
            {
                'id': workflow_id,
                'label': str(getattr(definition, 'label', None) or label),
                'description': description or label,
                'recent_count': counts.get(workflow_id, 0),
            }
        )
    return options


def _document_options_for_inspector(workspace_root: Path) -> list[dict[str, Any]]:
    documents = _workspace_documents(workspace_root)
    return [
        {
            'id': str(document.get('document_id') or ''),
            'name': str(document.get('name') or 'Document'),
            'status': str(document.get('status') or 'indexed'),
        }
        for document in documents
        if str(document.get('document_id') or '').strip()
    ]


def _build_task_details(workspace_root: Path, task_options: list[dict[str, Any]], document_lookup: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, int], Counter[str]]:
    workflow_runs = load_lab_workflow_runs(get_lab_workflow_runs_path(workspace_root))
    runtime_entries = load_runtime_execution_log(get_runtime_execution_log_path(workspace_root))
    recent_cases: list[dict[str, Any]] = []
    mode_counter: dict[str, int] = Counter()
    review_reason_counter: Counter[str] = Counter()
    task_details: dict[str, Any] = {}

    latest_by_workflow: dict[str, dict[str, Any]] = {}
    for run in workflow_runs:
        workflow_id = str(run.get('workflow_id') or run.get('task_id') or 'document_review')
        if workflow_id not in latest_by_workflow:
            latest_by_workflow[workflow_id] = run

    for entry in runtime_entries[:24]:
        workflow_id = str(entry.get('workflow_id') or '') or 'document_review'
        mode = str(entry.get('execution_strategy_used') or entry.get('flow_type') or 'runtime')
        mode_counter[mode] += 1
        review_reason = str(entry.get('needs_review_reason') or '').strip()
        if review_reason:
            review_reason_counter[review_reason] += 1
        source_ids = [str(item) for item in (entry.get('source_document_ids') or []) if str(item or '').strip()]
        recent_cases.append(
            {
                'id': f"runtime-{len(recent_cases) + 1}",
                'task': WORKFLOW_TASK_LABELS.get(workflow_id, workflow_id),
                'document': ', '.join(str(document_lookup.get(doc_id, {}).get('name') or doc_id) for doc_id in source_ids[:2]) or 'Workspace documents',
                'mode': mode,
                'status': 'completed' if bool(entry.get('success')) else 'error',
                'confidence': round(_safe_float(entry.get('confidence') or 0.0) * 100, 0),
                'sourceCount': max(len(source_ids), _safe_int(entry.get('retrieved_chunks_count') or 0)),
                'needsReview': bool(entry.get('needs_review')),
            }
        )

    for task in task_options:
        workflow_id = str(task.get('id') or 'document_review')
        latest_run = latest_by_workflow.get(workflow_id)
        document_names = []
        result_items = []
        trace_fields = []
        raw_json = None
        executions = []
        if latest_run:
            document_names = [str(item) for item in (latest_run.get('document_names') or []) if str(item or '').strip()]
            result_items = [
                {'label': 'Summary', 'value': str(latest_run.get('summary') or 'Persisted workflow summary unavailable.'), 'confidence': _safe_float(latest_run.get('confidence') or 0.0) * 100 or None},
                {'label': 'Input', 'value': str(latest_run.get('input_text') or '—'), 'confidence': None},
            ]
            raw_json = latest_run.get('result') if isinstance(latest_run.get('result'), dict) else latest_run.get('response_payload')
            trace_fields = [
                {'label': 'Mode', 'value': str(latest_run.get('execution_mode') or 'workflow_run')},
                {'label': 'Status', 'value': str(latest_run.get('status') or 'completed')},
                {'label': 'Provider', 'value': str(latest_run.get('provider') or '—')},
                {'label': 'Model', 'value': str(latest_run.get('model') or '—')},
                {'label': 'Sources', 'value': _safe_int(latest_run.get('source_count') or 0)},
            ]
            executions.append(
                {
                    'id': str(latest_run.get('run_id') or ''),
                    'mode': str(latest_run.get('execution_mode') or 'workflow_run'),
                    'status': str(latest_run.get('status') or 'completed'),
                    'needs_review': bool(latest_run.get('needs_review')),
                    'review_reason': str(latest_run.get('review_reason') or '').strip() or None,
                    'latency_s': _safe_float(latest_run.get('latency_s') or 0.0) or None,
                    'confidence': round(_safe_float(latest_run.get('confidence') or 0.0) * 100, 0) or None,
                    'provider': str(latest_run.get('provider') or ''),
                    'model': str(latest_run.get('model') or ''),
                    'source_count': _safe_int(latest_run.get('source_count') or 0),
                }
            )
        task_details[workflow_id] = {
            'id': workflow_id,
            'label': str(task.get('label') or WORKFLOW_TASK_LABELS.get(workflow_id, workflow_id)),
            'description': str(task.get('description') or WORKFLOW_DESCRIPTIONS.get(workflow_id, workflow_id)),
            'document_names': document_names,
            'result_title': 'Latest persisted run' if latest_run else 'No persisted run yet',
            'result_items': result_items,
            'raw_json': raw_json,
            'executions': executions,
            'trace_fields': trace_fields,
        }
    return task_details, recent_cases, dict(mode_counter), review_reason_counter


def _resolve_inspector_document_ids(
    workspace_root: Path,
    workflow_id: str,
    requested_document_ids: list[str] | None = None,
    requested_document_id: str | None = None,
) -> list[str]:
    available_document_ids = [
        str(document.get('document_id') or '').strip()
        for document in _workspace_documents(workspace_root)
        if str(document.get('document_id') or '').strip()
    ]
    available_document_id_set = set(available_document_ids)

    requested_ids: list[str] = []
    for raw_document_id in list(requested_document_ids or []) + ([requested_document_id] if requested_document_id else []):
        normalized_document_id = str(raw_document_id or '').strip()
        if not normalized_document_id or normalized_document_id not in available_document_id_set or normalized_document_id in requested_ids:
            continue
        requested_ids.append(normalized_document_id)

    if workflow_id in {'candidate_review', 'document_review', 'action_plan_evidence_review'}:
        if requested_ids:
            return requested_ids[:1]
        return available_document_ids[:1]

    minimum_documents = 2 if workflow_id == 'policy_contract_comparison' else 1
    selected = list(requested_ids)
    auto_fill_allowed = workflow_id != 'policy_contract_comparison' or not requested_ids
    if auto_fill_allowed:
        for document_id in available_document_ids:
            if document_id not in selected:
                selected.append(document_id)
            if len(selected) >= minimum_documents:
                break
    return selected[:max(minimum_documents, len(selected))]


def build_lab_workflow_inspector_payload(workspace_root: Path, *, additional_run_paths: list[Path] | None = None) -> dict[str, Any]:
    documents = _workspace_documents(workspace_root)
    document_lookup = _document_lookup(documents)
    task_options = _build_workflow_task_options(workspace_root)
    document_options = _document_options_for_inspector(workspace_root)
    workflow_runs = [
        run
        for run in _load_lab_workflow_runs_with_overlays(get_lab_workflow_runs_path(workspace_root), additional_run_paths)
        if str(run.get('workflow_id') or run.get('task_id') or '').strip() in WORKFLOW_INSPECTOR_TASK_IDS
    ]

    recent_cases: list[dict[str, Any]] = []
    mode_counter: Counter[str] = Counter()
    review_reason_counter: Counter[str] = Counter()
    task_health: list[dict[str, Any]] = []
    task_details: dict[str, Any] = {}

    runs_by_workflow: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in workflow_runs:
        workflow_id = str(run.get('workflow_id') or run.get('task_id') or 'document_review')
        runs_by_workflow[workflow_id].append(run)

    recent_window_limit = 30
    recent_runs = workflow_runs[:recent_window_limit]
    for run in recent_runs:
        workflow_id = str(run.get('workflow_id') or run.get('task_id') or 'document_review')
        document_labels = [
            _resolve_workflow_document_label(item, document_lookup)
            for item in ([str(item) for item in (run.get('document_names') or []) if str(item or '').strip()] or [str(item) for item in (run.get('document_ids') or []) if str(item or '').strip()])
        ]
        execution_label = _workflow_execution_label(run)
        mode_counter[execution_label] += 1
        for reason in _split_workflow_review_reasons(str(run.get('review_reason') or '')):
            human_reason = _humanize_workflow_review_reason(reason)
            if human_reason:
                review_reason_counter[human_reason] += 1
        recent_cases.append(
            {
                'id': str(run.get('run_id') or ''),
                'task': WORKFLOW_TASK_LABELS.get(workflow_id, workflow_id),
                'document': ', '.join(document_labels[:2]) or 'Workspace documents',
                'mode': execution_label,
                'status': str(run.get('status') or 'completed'),
                'confidence': _safe_float(run.get('confidence') or 0.0),
                'sourceCount': _safe_int(run.get('source_count') or 0),
                'documentCount': len(document_labels) or len([str(item) for item in (run.get('document_ids') or []) if str(item or '').strip()]),
                'needsReview': bool(run.get('needs_review')),
            }
        )

    latest_runs = []
    for run in workflow_runs[:8]:
        document_labels = [
            _resolve_workflow_document_label(item, document_lookup)
            for item in ([str(item) for item in (run.get('document_names') or []) if str(item or '').strip()] or [str(item) for item in (run.get('document_ids') or []) if str(item or '').strip()])
        ]
        latest_runs.append(
            {
                'id': str(run.get('run_id') or ''),
                'task_id': str(run.get('workflow_id') or run.get('task_id') or 'document_review'),
                'task_label': WORKFLOW_TASK_LABELS.get(str(run.get('workflow_id') or run.get('task_id') or ''), str(run.get('workflow_id') or run.get('task_id') or 'Workflow')),
                'status': str(run.get('status') or 'completed'),
                'timestamp': _format_timestamp(run.get('updated_at') or run.get('created_at')),
                'provider': str(run.get('provider') or '').strip() or None,
                'model': str(run.get('model') or '').strip() or None,
                'latency_s': _safe_float(run.get('latency_s') or 0.0) or None,
                'source_count': _safe_int(run.get('source_count') or 0),
                'needs_review': bool(run.get('needs_review')),
                'review_reason': '; '.join(_humanize_workflow_review_reason(item) for item in _split_workflow_review_reasons(str(run.get('review_reason') or '')) if _humanize_workflow_review_reason(item)) or None,
                'artifact_label': str(run.get('artifact_label') or '').strip() or None,
                'artifact_path': str(run.get('artifact_path') or '').strip() or None,
                'document_names': document_labels,
            }
        )

    for task in task_options:
        workflow_id = str(task.get('id') or 'document_review')
        task_runs = runs_by_workflow.get(workflow_id, [])
        latest_run = _pick_preferred_workflow_run(task_runs)
        latest_overall_run = task_runs[0] if task_runs else None
        run_latencies = [_safe_float(run.get('latency_s') or 0.0) for run in task_runs if _safe_float(run.get('latency_s') or 0.0) > 0]
        needs_review_count = sum(1 for run in task_runs if bool(run.get('needs_review')))
        task_health.append(
            {
                'id': workflow_id,
                'label': str(task.get('label') or workflow_id),
                'runs': len(task_runs),
                'last_status': str(latest_overall_run.get('status') or 'not_run') if latest_overall_run else 'not_run',
                'needs_review_rate': round(needs_review_count / max(len(task_runs), 1), 3) if task_runs else 0.0,
                'avg_latency_s': round(_mean(run_latencies), 3) if run_latencies else 0.0,
                'last_run_at': _format_timestamp(latest_overall_run.get('updated_at') or latest_overall_run.get('created_at')) if latest_overall_run else None,
            }
        )

        document_names = [
            _resolve_workflow_document_label(item, document_lookup)
            for item in ([str(item) for item in (latest_run.get('document_names') or []) if str(item or '').strip()] if latest_run else [])
        ]
        if latest_run and not document_names:
            document_names = [
                _resolve_workflow_document_label(item, document_lookup)
                for item in [str(item) for item in (latest_run.get('document_ids') or []) if str(item or '').strip()]
            ]
        raw_json = latest_run.get('result') if isinstance(latest_run, dict) and isinstance(latest_run.get('result'), dict) else latest_run.get('response_payload') if isinstance(latest_run, dict) and isinstance(latest_run.get('response_payload'), dict) else {}
        trace = latest_run.get('trace') if isinstance(latest_run, dict) and isinstance(latest_run.get('trace'), dict) else {}
        executions = []
        for run in task_runs[:4]:
            executions.append(
                {
                    'id': str(run.get('run_id') or ''),
                    'mode': _workflow_execution_label(run),
                    'status': str(run.get('status') or 'completed'),
                    'needs_review': bool(run.get('needs_review')),
                    'review_reason': '; '.join(_humanize_workflow_review_reason(item) for item in _split_workflow_review_reasons(str(run.get('review_reason') or '')) if _humanize_workflow_review_reason(item)) or None,
                    'latency_s': _safe_float(run.get('latency_s') or 0.0) or None,
                    'confidence': _safe_float(run.get('confidence') or 0.0),
                    'provider': str(run.get('provider') or '').strip() or None,
                    'model': str(run.get('model') or '').strip() or None,
                    'source_count': _safe_int(run.get('source_count') or 0),
                    'surface': _workflow_surface_label(run),
                }
            )
        result_items = []
        if latest_run:
            result_items.append({'label': 'Summary', 'value': str(latest_run.get('summary') or 'Persisted workflow summary unavailable.'), 'confidence': _safe_float(latest_run.get('confidence') or 0.0)})
            if workflow_id == 'policy_contract_comparison' and document_names:
                visible_documents = document_names[:2]
                extra_document_count = max(len(document_names) - len(visible_documents), 0)
                suffix = f' +{extra_document_count} more' if extra_document_count else ''
                result_items.append({'label': 'Documents', 'value': ', '.join(visible_documents) + suffix, 'confidence': None})
            result_items.append({'label': 'Instructions', 'value': str(latest_run.get('input_text') or '—'), 'confidence': None})
            if latest_run.get('artifact_label') or latest_run.get('artifact_path'):
                result_items.append({'label': 'Artifact', 'value': str(latest_run.get('artifact_label') or latest_run.get('artifact_path') or 'Artifact captured'), 'confidence': None})

        stage_timeline = []
        for stage in (trace.get('stages') if isinstance(trace.get('stages'), list) else []):
            if not isinstance(stage, dict):
                continue
            stage_timeline.append(
                {
                    'label': str(stage.get('label') or stage.get('stage') or 'stage'),
                    'status': str(stage.get('status') or 'completed'),
                    'detail': str(stage.get('detail') or '').strip() or None,
                    'duration_ms': _safe_int(stage.get('duration_ms') or 0) or None,
                }
            )
        if not stage_timeline:
            for span in (trace.get('spans') if isinstance(trace.get('spans'), list) else []):
                if not isinstance(span, dict):
                    continue
                stage_timeline.append(
                    {
                        'label': str(span.get('name') or span.get('stage') or 'stage').replace('_', ' '),
                        'status': str(span.get('status') or 'completed'),
                        'detail': str(span.get('detail') or '').strip() or None,
                        'duration_ms': _safe_int(span.get('duration_ms') or 0) or None,
                    }
                )
        guardrails = []
        if latest_run:
            guardrails = [
                {
                    'label': _humanize_workflow_review_reason(item),
                    'severity': 'warning',
                    'detail': _humanize_workflow_review_reason(item),
                }
                for item in _split_workflow_review_reasons(str(latest_run.get('review_reason') or ''))
                if _humanize_workflow_review_reason(item)
            ]
        artifacts = []
        if latest_run and (latest_run.get('artifact_label') or latest_run.get('artifact_path')):
            artifacts.append(
                {
                    'label': str(latest_run.get('artifact_label') or 'Workflow artifact'),
                    'path': str(latest_run.get('artifact_path') or '').strip() or None,
                }
            )
        trace_fields = []
        if latest_run:
            trace_fields = [
                {'label': 'Surface', 'value': _workflow_surface_label(latest_run)},
                {'label': 'Route', 'value': _workflow_execution_label(latest_run)},
                {'label': 'Status', 'value': str(latest_run.get('status') or 'completed')},
                {'label': 'Provider', 'value': str(latest_run.get('provider') or '—')},
                {'label': 'Model', 'value': str(latest_run.get('model') or '—')},
                {'label': 'Documents', 'value': len(document_names)},
                {'label': 'Sources', 'value': _safe_int(latest_run.get('source_count') or 0)},
                {'label': 'Tokens', 'value': _safe_int(latest_run.get('total_tokens') or 0)},
                {'label': 'Context Chars', 'value': _safe_int(latest_run.get('context_chars') or 0)},
            ]
        task_details[workflow_id] = {
            'id': workflow_id,
            'label': str(task.get('label') or workflow_id),
            'description': str(task.get('description') or WORKFLOW_DESCRIPTIONS.get(workflow_id) or workflow_id),
            'document_names': document_names,
            'result_title': str(latest_run.get('result_title') or f"{task.get('label') or workflow_id} result") if latest_run else f"{task.get('label') or workflow_id} result",
            'result_items': result_items,
            'raw_json': raw_json if isinstance(raw_json, dict) else {},
            'executions': executions,
            'trace_fields': trace_fields,
            'stage_timeline': stage_timeline,
            'guardrails': guardrails,
            'artifacts': artifacts,
            'run_summary': {
                'runs': len(task_runs),
                'needsReviewRate': round(needs_review_count / max(len(task_runs), 1), 3) if task_runs else 0.0,
                'avgLatencyS': round(_mean(run_latencies), 3) if run_latencies else 0.0,
                'lastRunAt': _format_timestamp(latest_overall_run.get('updated_at') or latest_overall_run.get('created_at')) if latest_overall_run else None,
            },
        }

    selected_task_id = task_options[0]['id'] if task_options else 'document_review'
    confidence_values = [float(item['confidence']) for item in recent_cases if float(item['confidence']) > 0]
    summary = {
        'total_cases': len(workflow_runs),
        'recent_window_count': len(recent_cases),
        'recent_window_limit': recent_window_limit,
        'needs_review': sum(1 for item in recent_cases if item['needsReview']),
        'avg_confidence': round(_mean(confidence_values), 3) if confidence_values else 0.0,
        'review_blockers': sum(1 for item in recent_cases if item['needsReview']),
        'failed': sum(1 for item in recent_cases if item['status'] in {'error', 'failed'}),
        'task_count': len(task_options),
        'document_count': len(document_options),
        'live_runs': len(workflow_runs),
        'last_run_at': latest_runs[0]['timestamp'] if latest_runs else None,
    }

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['Workflow Inspector owns task-level execution traces, not runtime-wide health or benchmark comparisons.']),
        'status': 'live' if workflow_runs else 'derived',
        'degraded_reason': None if workflow_runs else 'No persisted workflow inspector runs were found yet. Execute a run to seed this surface.',
        'capabilities': {'can_execute': bool(document_options), 'reason': None if document_options else 'At least one indexed document is required to execute the inspector.'},
        'summary': summary,
        'task_options': task_options,
        'document_options': document_options,
        'selected_task_id': selected_task_id,
        'task_details': task_details,
        'recent_cases': recent_cases,
        'mode_breakdown': [{'label': key, 'value': value} for key, value in Counter(mode_counter).most_common(6)],
        'review_reasons': [{'label': key, 'value': value} for key, value in review_reason_counter.most_common(6)],
        'task_health': task_health,
        'latest_runs': latest_runs,
    }

def execute_lab_workflow_inspector_run(
    *,
    bootstrap: ProductBootstrap,
    task_id: str,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    input_text: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    runs_path: Path | None = None,
) -> dict[str, Any]:
    workflow_id = str(task_id or 'document_review').strip() or 'document_review'
    if workflow_id not in WORKFLOW_TASK_LABELS:
        workflow_id = 'document_review'
    document_ids = _resolve_inspector_document_ids(
        bootstrap.workspace_root,
        workflow_id,
        requested_document_ids=[str(item or '').strip() for item in (document_ids or []) if str(item or '').strip()],
        requested_document_id=str(document_id or '').strip() or None,
    )
    minimum_documents = 2 if workflow_id == 'policy_contract_comparison' else 1
    if len(document_ids) < minimum_documents:
        if workflow_id == 'policy_contract_comparison':
            raise ValueError('Policy / Contract Comparison requires two distinct indexed documents.')
        requirement = 'at least 1 indexed document'
        raise ValueError(f"{WORKFLOW_TASK_LABELS.get(workflow_id, workflow_id)} requires {requirement} in the workspace.")

    normalized_input_text = str(input_text or '').strip()
    if len(normalized_input_text) > 1000:
        raise ValueError('Instructions must stay within 1000 characters for Workflow Inspector runs.')

    resolved_provider, resolved_model = _workflow_request_defaults(bootstrap.workspace_root)
    request = ProductWorkflowRequest(
        workflow_id=workflow_id,
        document_ids=document_ids,
        input_text=normalized_input_text,
        provider=str(provider or resolved_provider),
        model=str(model or resolved_model or '') or None,
        context_strategy='retrieval',
    )
    from src.product.service import run_product_workflow as _run_product_workflow

    result = _run_product_workflow(request)
    debug_metadata = getattr(result, 'debug_metadata', {}) if isinstance(getattr(result, 'debug_metadata', None), dict) else {}
    document_lookup = _document_lookup(_workspace_documents(bootstrap.workspace_root))
    artifact_path = None
    artifact_label = None
    if result.artifacts:
        first_artifact = result.artifacts[0]
        artifact_payload = first_artifact.model_dump(mode='json') if hasattr(first_artifact, 'model_dump') else first_artifact if isinstance(first_artifact, dict) else {}
        if isinstance(artifact_payload, dict):
            artifact_path = str(artifact_payload.get('path') or artifact_payload.get('artifact_path') or '').strip() or None
            artifact_label = str(artifact_payload.get('label') or artifact_payload.get('name') or '').strip() or None
    trace = {
        'stages': [
            {'stage': 'request', 'label': 'Request prepared', 'status': 'completed', 'detail': f"{len(document_ids)} document(s) selected", 'duration_ms': None},
            {'stage': 'grounding', 'label': 'Grounding resolved', 'status': 'completed', 'detail': f"{_safe_int(getattr(result.grounding_preview, 'source_block_count', 0) if getattr(result, 'grounding_preview', None) is not None else 0)} source block(s)", 'duration_ms': None},
            {'stage': 'generation', 'label': 'Workflow generated output', 'status': 'warning' if result.warnings else 'completed', 'detail': _trim_text(result.summary or result.recommendation or 'Result persisted', max_chars=120), 'duration_ms': int(round(_safe_float(debug_metadata.get('latency_s') or 0.0) * 1000)) or None},
        ],
        'artifacts': [{'label': artifact_label or 'Workflow artifact', 'path': artifact_path}] if artifact_path or artifact_label else [],
        'warnings': [str(item) for item in (result.warnings or []) if str(item or '').strip()],
    }
    run_record = {
        'task_id': workflow_id,
        'workflow_id': workflow_id,
        'status': _status_from_warnings([str(item) for item in (result.warnings or []) if str(item or '').strip()]),
        'input_text': request.input_text,
        'document_ids': document_ids,
        'document_names': [str(document_lookup.get(document_id, {}).get('name') or document_id) for document_id in document_ids],
        'confidence': _safe_float(
            debug_metadata.get('confidence')
            or (getattr(result.structured_result, 'overall_confidence', None) if getattr(result, 'structured_result', None) is not None else None)
            or (getattr(result.structured_result, 'quality_score', None) if getattr(result, 'structured_result', None) is not None else None)
            or 0.0
        ),
        'needs_review': bool(result.warnings),
        'review_reason': '; '.join(str(item) for item in (result.warnings or [])[:2]) or None,
        'provider': request.provider,
        'model': request.model,
        'summary': result.summary,
        'artifact_path': artifact_path,
        'artifact_label': artifact_label,
        'surface': 'workflow_inspector',
        'execution_mode': str(debug_metadata.get('context_strategy') or request.context_strategy or 'workflow_run'),
        'result_title': f"{WORKFLOW_TASK_LABELS.get(workflow_id, workflow_id)} result",
        'source_count': _safe_int(getattr(result.grounding_preview, 'source_block_count', 0) if getattr(result, 'grounding_preview', None) is not None else 0),
        'latency_s': _safe_float(debug_metadata.get('latency_s') or 0.0),
        'total_tokens': _safe_float(debug_metadata.get('total_tokens') or 0.0),
        'context_chars': _safe_int(getattr(result.grounding_preview, 'context_chars', 0) if getattr(result, 'grounding_preview', None) is not None else debug_metadata.get('context_chars') or 0),
        'trace': trace,
        'result': result.model_dump(mode='json') if hasattr(result, 'model_dump') else {},
        'request_payload': request.model_dump(mode='json') if hasattr(request, 'model_dump') else {},
        'response_payload': result.model_dump(mode='json') if hasattr(result, 'model_dump') else {},
    }
    saved = append_lab_workflow_run(runs_path or get_lab_workflow_runs_path(bootstrap.workspace_root), run_record)
    return {'result': result, 'request': request, 'run_record': saved}


def build_lab_benchmarks_payload(workspace_root: Path) -> dict[str, Any]:
    def _load_json_payload(path: Path) -> dict[str, Any] | list[Any] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, (dict, list)) else None

    def _stable_payload_key(payload: Any) -> str:
        try:
            return json.dumps(payload, ensure_ascii=False, sort_keys=True)
        except TypeError:
            return str(payload)

    def _ensure_model_row(provider_name: str, model_name: str) -> dict[str, Any]:
        key = f'{provider_name}:{model_name}'
        return model_rows.setdefault(
            key,
            {
                'id': key,
                'family': model_name,
                'provider': provider_name,
                'model': model_name,
                'profileTag': None,
                'useCaseFitValues': [],
                'groundednessValues': [],
                'adherenceValues': [],
                'latencyValues': [],
                'outputCharsValues': [],
                'runtimeBucket': 'cloud',
                'quantization': 'cloud_managed',
                'runs': 0,
                'caseCount': 0,
                'sourceFamilies': set(),
            },
        )

    def _ensure_prompt_profile(
        profile_name: str,
        *,
        description: str,
        metrics: list[str],
    ) -> dict[str, Any]:
        return prompt_profile_map.setdefault(
            profile_name,
            {
                'id': profile_name.replace(' ', '-').replace('/', '-').lower(),
                'name': profile_name,
                'description': description,
                'metrics': metrics,
                'models': [],
                'runCount': 0,
                'metricSummary': {},
                'useCaseFitValues': [],
                'groundednessValues': [],
                'adherenceValues': [],
                'decisionValues': [],
                'groundingValues': [],
                'structuredValues': [],
                'latencyValues': [],
            },
        )

    def _append_numeric(bucket: dict[str, Any], field: str, value: Any) -> None:
        if isinstance(value, (int, float)):
            bucket[field].append(_safe_float(value))

    def _normalize_prompt_profile_name(value: Any) -> str:
        normalized = str(value or '').strip()
        if not normalized:
            return 'default'
        lowered = normalized.lower().replace('-', '_').replace(' ', '_')
        if lowered == 'neutro':
            return 'neutral'
        return normalized

    def _register_retrieval_observation(
        *,
        strategy: str,
        category: str,
        output_value: Any = None,
        retention_value: Any = None,
        composite_value: Any = None,
        latency_value: Any = None,
        candidate_count: Any = None,
        scored_candidate_count: Any = None,
        avg_context_chars: Any = None,
        description: str,
    ) -> None:
        normalized_strategy = str(strategy or '').strip()
        normalized_category = str(category or '').strip()
        if not normalized_strategy or not normalized_category:
            return
        key = f'{normalized_category}::{normalized_strategy}'
        bucket = retrieval_buckets.setdefault(
            key,
            {
                'strategy': normalized_strategy,
                'category': normalized_category,
                'outputValues': [],
                'retentionValues': [],
                'compositeValues': [],
                'latencyValues': [],
                'candidateCount': 0,
                'scoredCandidateCount': 0,
                'avgContextCharsValues': [],
                'description': description,
            },
        )
        if isinstance(output_value, (int, float)):
            bucket['outputValues'].append(_safe_float(output_value))
        if isinstance(retention_value, (int, float)):
            bucket['retentionValues'].append(_safe_float(retention_value))
        if isinstance(composite_value, (int, float)):
            bucket['compositeValues'].append(_safe_float(composite_value))
        if isinstance(latency_value, (int, float)):
            bucket['latencyValues'].append(_safe_float(latency_value))
        if isinstance(candidate_count, (int, float)):
            bucket['candidateCount'] += max(int(candidate_count), 0)
        if isinstance(scored_candidate_count, (int, float)):
            bucket['scoredCandidateCount'] += max(int(scored_candidate_count), 0)
        if isinstance(avg_context_chars, (int, float)):
            bucket['avgContextCharsValues'].append(_safe_float(avg_context_chars))
        if description and not bucket.get('description'):
            bucket['description'] = description

    def _benchmark_root_candidates() -> list[Path]:
        candidates: list[Path] = []

        def add(path: Path | None) -> None:
            if path is None:
                return
            resolved = path.expanduser()
            if resolved not in candidates:
                candidates.append(resolved)

        skip_workspace_benchmark_runs = str(os.getenv('AI_DECISION_STUDIO_SKIP_WORKSPACE_BENCHMARK_RUNS') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
        if not skip_workspace_benchmark_runs:
            add(workspace_root / 'benchmark_runs')

        baseline_root_raw = str(os.getenv('APP_BASELINE_ROOT') or '').strip()
        if baseline_root_raw:
            add(Path(baseline_root_raw) / 'benchmark_runs')

        runtime_root_raw = str(os.getenv('APP_RUNTIME_ROOT') or '').strip()
        if runtime_root_raw:
            add(Path(runtime_root_raw) / 'benchmark_runs')

        add(workspace_root / 'baseline' / 'benchmark_runs')
        return candidates

    def _collect_paths(*patterns: str) -> list[Path]:
        collected: list[Path] = []
        seen: set[Path] = set()
        for benchmark_root in _benchmark_root_candidates():
            if not benchmark_root.exists():
                continue
            for pattern in patterns:
                for path in benchmark_root.glob(pattern):
                    if path not in seen and path.exists():
                        seen.add(path)
                        collected.append(path)
        return sorted(collected)

    def _phase45_category(benchmark_name: str) -> str:
        normalized = str(benchmark_name or '').strip().replace('_', ' ')
        if not normalized:
            return 'Phase 4.5 retrieval'
        return f'Phase 4.5 {normalized}'

    entries = load_model_comparison_log(get_phase7_model_comparison_log_path(workspace_root))
    summary = summarize_model_comparison_log(entries)

    model_rows: dict[str, dict[str, Any]] = {}
    prompt_profile_map: dict[str, dict[str, Any]] = {}
    strategy_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    retrieval_buckets: dict[str, dict[str, Any]] = {}
    use_case_labels: set[str] = set()
    phase85_top_candidate_keys: set[str] = set()

    latest_timestamp = _format_timestamp(summary.get('latest_timestamp'))
    latest_datetimes: list[datetime] = []
    latest_phase7 = _safe_iso_datetime(latest_timestamp)
    if latest_phase7 is not None:
        latest_datetimes.append(latest_phase7)

    for entry in entries:
        retrieval_strategy = str(entry.get('retrieval_strategy') or 'manual_hybrid')
        strategy_buckets[retrieval_strategy].append(entry)

        prompt_profile_name = _normalize_prompt_profile_name(entry.get('prompt_profile') or 'default')
        prompt_profile = _ensure_prompt_profile(
            prompt_profile_name,
            description=f'{prompt_profile_name} prompt profile observed in recorded product comparison runs.',
            metrics=['use case fit', 'groundedness', 'format adherence', 'latency'],
        )
        prompt_profile['runCount'] += 1

        benchmark_use_case = str(entry.get('benchmark_use_case') or '').strip()
        if benchmark_use_case:
            use_case_labels.add(benchmark_use_case)

        for candidate in entry.get('candidate_results') or []:
            if not isinstance(candidate, dict):
                continue
            model_name = str(candidate.get('model_effective') or candidate.get('model_requested') or 'unknown')
            provider_name = str(candidate.get('provider_effective') or candidate.get('provider_requested') or 'unknown')
            bucket = _ensure_model_row(provider_name, model_name)
            bucket['runs'] += 1
            bucket['caseCount'] += 1
            bucket['sourceFamilies'].add('phase7')

            adherence_value = candidate.get('format_adherence')
            groundedness_value = candidate.get('groundedness_score') if isinstance(candidate.get('groundedness_score'), (int, float)) else candidate.get('groundedness')
            use_case_fit_value = candidate.get('use_case_fit_score') if isinstance(candidate.get('use_case_fit_score'), (int, float)) else candidate.get('use_case_fit')
            latency_value = candidate.get('latency_s')
            _append_numeric(bucket, 'adherenceValues', adherence_value)
            _append_numeric(bucket, 'groundednessValues', groundedness_value)
            _append_numeric(bucket, 'useCaseFitValues', use_case_fit_value)
            _append_numeric(bucket, 'latencyValues', latency_value)
            _append_numeric(bucket, 'outputCharsValues', candidate.get('output_chars'))

            _append_numeric(prompt_profile, 'adherenceValues', adherence_value)
            _append_numeric(prompt_profile, 'groundednessValues', groundedness_value)
            _append_numeric(prompt_profile, 'useCaseFitValues', use_case_fit_value)
            _append_numeric(prompt_profile, 'latencyValues', latency_value)

            if model_name not in prompt_profile['models']:
                prompt_profile['models'].append(model_name)

    phase8_bundle_paths = _collect_paths(
        'phase8_5_matrix/*/aggregated/summary.json',
        'phase8_5_round1/*/aggregated/summary.json',
        'phase8_5_matrix_campaigns/*/aggregated/summary.json',
        'phase8_5_matrix_campaigns/*/group_runs/*/aggregated/summary.json',
    )
    phase8_generation_paths = _collect_paths(
        'phase8_5_matrix/*/aggregated/generation_summary.json',
        'phase8_5_round1/*/aggregated/generation_summary.json',
        'phase8_5_matrix_campaigns/*/aggregated/generation_summary.json',
        'phase8_5_matrix_campaigns/*/group_runs/*/aggregated/generation_summary.json',
    )
    phase8_embedding_paths = _collect_paths(
        'phase8_5_matrix/*/aggregated/embedding_summary.json',
        'phase8_5_round1/*/aggregated/embedding_summary.json',
        'phase8_5_matrix_campaigns/*/aggregated/embedding_summary.json',
        'phase8_5_matrix_campaigns/*/group_runs/*/aggregated/embedding_summary.json',
    )
    phase8_reranker_paths = _collect_paths(
        'phase8_5_matrix/*/aggregated/reranker_summary.json',
        'phase8_5_round1/*/aggregated/reranker_summary.json',
        'phase8_5_matrix_campaigns/*/aggregated/reranker_summary.json',
        'phase8_5_matrix_campaigns/*/group_runs/*/aggregated/reranker_summary.json',
    )
    phase8_ocr_paths = _collect_paths(
        'phase8_5_matrix/*/aggregated/ocr_vlm_summary.json',
        'phase8_5_round1/*/aggregated/ocr_vlm_summary.json',
        'phase8_5_matrix_campaigns/*/aggregated/ocr_vlm_summary.json',
        'phase8_5_matrix_campaigns/*/group_runs/*/aggregated/ocr_vlm_summary.json',
    )
    phase45_result_paths = _collect_paths('20260315_011241_phase_4_5_all/*/*/*/result.json')
    doc_review_paths = _collect_paths('document_review_findings_experiment*/results.json')

    unique_generation_payloads: set[str] = set()
    for path in phase8_generation_paths:
        if 'phase8_5_matrix_campaigns' in str(path) and '/group_runs/' not in str(path):
            continue
        payload = _load_json_payload(path)
        if not isinstance(payload, dict):
            continue
        payload_key = _stable_payload_key(payload)
        if payload_key in unique_generation_payloads:
            continue
        unique_generation_payloads.add(payload_key)
        use_case_labels.add('phase8_5_generation')

        top_candidate = payload.get('top_candidate') if isinstance(payload.get('top_candidate'), dict) else {}
        top_provider = str(top_candidate.get('provider') or '').strip()
        top_model = str(top_candidate.get('model_effective') or top_candidate.get('model') or '').strip()
        if top_provider and top_model:
            phase85_top_candidate_keys.add(f'{top_provider}:{top_model}')

        for candidate in payload.get('candidate_ranking') or []:
            if not isinstance(candidate, dict):
                continue
            model_name = str(candidate.get('model_effective') or candidate.get('model') or 'unknown')
            provider_name = str(candidate.get('provider') or 'unknown')
            bucket = _ensure_model_row(provider_name, model_name)
            bucket['runs'] += 1
            bucket['caseCount'] += max(_safe_int(candidate.get('case_count') or 0), 1)
            bucket['sourceFamilies'].add('phase8_generation')
            _append_numeric(bucket, 'useCaseFitValues', candidate.get('avg_use_case_fit_score'))
            _append_numeric(bucket, 'groundednessValues', candidate.get('avg_groundedness_score'))
            _append_numeric(bucket, 'adherenceValues', candidate.get('avg_format_adherence'))
            _append_numeric(bucket, 'latencyValues', candidate.get('avg_latency_s'))
            _append_numeric(bucket, 'outputCharsValues', candidate.get('avg_total_tokens'))

    for path in doc_review_paths:
        payload = _load_json_payload(path)
        if not isinstance(payload, dict):
            continue
        generated_at = _safe_iso_datetime(payload.get('generated_at'))
        if generated_at is not None:
            latest_datetimes.append(generated_at)

        for config in payload.get('configs') or []:
            if not isinstance(config, dict):
                continue
            profile_name = _normalize_prompt_profile_name(config.get('prompt_style') or config.get('key') or config.get('label') or 'document_review_findings')
            prompt_profile = _ensure_prompt_profile(
                profile_name,
                description=f'{profile_name} findings experiment profile observed in benchmark_runs document review bundles.',
                metrics=['decision score', 'grounding ratio', 'structured success', 'latency'],
            )
            model_name = str(config.get('findings_model') or config.get('base_model') or '').strip()
            if model_name and model_name not in prompt_profile['models']:
                prompt_profile['models'].append(model_name)
            use_case_labels.add('document_review_findings')

        for run in payload.get('runs') or []:
            if not isinstance(run, dict):
                continue
            config = run.get('config') if isinstance(run.get('config'), dict) else {}
            profile_name = _normalize_prompt_profile_name(config.get('prompt_style') or config.get('key') or config.get('label') or 'document_review_findings')
            prompt_profile = _ensure_prompt_profile(
                profile_name,
                description=f'{profile_name} findings experiment profile observed in benchmark_runs document review bundles.',
                metrics=['decision score', 'grounding ratio', 'structured success', 'latency'],
            )
            prompt_profile['runCount'] += 1
            model_name = str(config.get('findings_model') or config.get('base_model') or '').strip()
            if model_name and model_name not in prompt_profile['models']:
                prompt_profile['models'].append(model_name)
            scores = run.get('scores') if isinstance(run.get('scores'), dict) else {}
            _append_numeric(prompt_profile, 'decisionValues', scores.get('decision_score'))
            _append_numeric(prompt_profile, 'groundingValues', scores.get('grounding_ratio'))
            structured_success = run.get('structured_success')
            if isinstance(structured_success, bool):
                prompt_profile['structuredValues'].append(1.0 if structured_success else 0.0)
            _append_numeric(prompt_profile, 'latencyValues', run.get('duration_s'))
            use_case_labels.add('document_review_findings')

    unique_embedding_payloads: set[str] = set()
    for path in phase8_embedding_paths:
        if 'phase8_5_matrix_campaigns' in str(path) and '/group_runs/' not in str(path):
            continue
        payload = _load_json_payload(path)
        if not isinstance(payload, dict):
            continue
        payload_key = _stable_payload_key(payload)
        if payload_key in unique_embedding_payloads:
            continue
        unique_embedding_payloads.add(payload_key)
        use_case_labels.add('phase8_5_embeddings')

        for candidate in payload.get('candidate_ranking') or []:
            if not isinstance(candidate, dict):
                continue
            strategy_parts = [
                str(candidate.get('model_effective') or candidate.get('model') or candidate.get('candidate') or 'embedding').strip(),
            ]
            subset_label = str(candidate.get('subset_label') or candidate.get('subset_id') or '').strip()
            if subset_label:
                strategy_parts.append(subset_label)
            strategy_label = ' · '.join(part for part in strategy_parts if part)
            _register_retrieval_observation(
                strategy=strategy_label,
                category='Phase 8.5 embeddings',
                output_value=candidate.get('avg_hit_at_1') if isinstance(candidate.get('avg_hit_at_1'), (int, float)) else candidate.get('avg_mrr'),
                retention_value=candidate.get('avg_hit_at_k'),
                composite_value=candidate.get('avg_mrr'),
                latency_value=candidate.get('avg_total_wall_time_s') if isinstance(candidate.get('avg_total_wall_time_s'), (int, float)) else candidate.get('avg_retrieval_seconds'),
                candidate_count=candidate.get('case_count'),
                scored_candidate_count=candidate.get('case_count') if isinstance(candidate.get('avg_mrr'), (int, float)) else 0,
                description=f"Phase 8.5 embeddings · {subset_label or 'retrieval'}",
            )

    unique_reranker_payloads: set[str] = set()
    for path in phase8_reranker_paths:
        if 'phase8_5_matrix_campaigns' in str(path) and '/group_runs/' not in str(path):
            continue
        payload = _load_json_payload(path)
        if not isinstance(payload, dict):
            continue
        payload_key = _stable_payload_key(payload)
        if payload_key in unique_reranker_payloads:
            continue
        unique_reranker_payloads.add(payload_key)
        use_case_labels.add('phase8_5_rerankers')

        for candidate in payload.get('candidate_ranking') or []:
            if not isinstance(candidate, dict):
                continue
            strategy_label = str(candidate.get('model_effective') or candidate.get('model') or candidate.get('candidate') or 'reranker').strip()
            _register_retrieval_observation(
                strategy=strategy_label,
                category='Phase 8.5 rerankers',
                output_value=candidate.get('avg_hit_at_1') if isinstance(candidate.get('avg_hit_at_1'), (int, float)) else candidate.get('avg_mrr'),
                retention_value=candidate.get('avg_hit_at_k'),
                composite_value=candidate.get('avg_mrr'),
                latency_value=candidate.get('avg_total_wall_time_s') if isinstance(candidate.get('avg_total_wall_time_s'), (int, float)) else candidate.get('avg_reranking_seconds'),
                candidate_count=candidate.get('case_count'),
                scored_candidate_count=candidate.get('case_count') if isinstance(candidate.get('avg_mrr'), (int, float)) else 0,
                description='Phase 8.5 reranker quality benchmark.',
            )

    unique_ocr_payloads: set[str] = set()
    for path in phase8_ocr_paths:
        if 'phase8_5_matrix_campaigns' in str(path) and '/group_runs/' not in str(path):
            continue
        payload = _load_json_payload(path)
        if not isinstance(payload, dict):
            continue
        payload_key = _stable_payload_key(payload)
        if payload_key in unique_ocr_payloads:
            continue
        unique_ocr_payloads.add(payload_key)
        use_case_labels.add('phase8_5_ocr_vlm')

        for variant in payload.get('variant_ranking') or []:
            if not isinstance(variant, dict):
                continue
            case_count = _safe_int(variant.get('case_count') or 0)
            helped_cases = _safe_int(variant.get('helped_cases') or 0)
            retention_ratio = helped_cases / max(case_count, 1) if case_count > 0 else None
            _register_retrieval_observation(
                strategy=str(variant.get('variant') or 'ocr_variant'),
                category='Phase 8.5 OCR / VLM',
                output_value=variant.get('avg_f1'),
                retention_value=retention_ratio,
                composite_value=variant.get('avg_f1'),
                latency_value=variant.get('avg_latency_s'),
                candidate_count=variant.get('case_count'),
                scored_candidate_count=variant.get('case_count') if isinstance(variant.get('avg_f1'), (int, float)) else 0,
                description=f"Phase 8.5 OCR/VLM variant · {variant.get('resolved_runtime_family') or variant.get('requested_runtime_family') or 'runtime'}",
            )

    phase45_root_name = '20260315_011241_phase_4_5_all'
    phase45_timestamp = _safe_iso_datetime(phase45_root_name.split('_phase_')[0].replace('_', 'T', 1).replace('_', ':', 2))
    if phase45_timestamp is not None:
        latest_datetimes.append(phase45_timestamp)

    for path in phase45_result_paths:
        payload = _load_json_payload(path)
        if not isinstance(payload, dict):
            continue
        metrics = payload.get('metrics') if isinstance(payload.get('metrics'), dict) else {}
        settings = payload.get('settings') if isinstance(payload.get('settings'), dict) else {}
        benchmark_name = str(payload.get('benchmark') or '').strip()
        strategy_label = str(payload.get('label') or path.parent.name).strip() or path.parent.name
        description_parts = []
        embedding_model = str(settings.get('embedding_model') or '').strip()
        if embedding_model:
            description_parts.append(embedding_model)
        top_k = settings.get('top_k')
        if isinstance(top_k, (int, float)):
            description_parts.append(f'top-k {int(top_k)}')
        _register_retrieval_observation(
            strategy=strategy_label,
            category=_phase45_category(benchmark_name),
            output_value=metrics.get('hit_at_1') if isinstance(metrics.get('hit_at_1'), (int, float)) else metrics.get('mrr'),
            retention_value=metrics.get('hit_at_k'),
            composite_value=metrics.get('mrr'),
            latency_value=metrics.get('avg_retrieval_seconds'),
            candidate_count=metrics.get('question_count'),
            scored_candidate_count=metrics.get('question_count') if isinstance(metrics.get('mrr'), (int, float)) else 0,
            description=' · '.join(description_parts) or 'Phase 4.5 retrieval benchmark bundle.',
        )
        use_case_labels.add(f'phase4_5_{benchmark_name}' if benchmark_name else 'phase4_5_retrieval')

    for strategy, strategy_entries in strategy_buckets.items():
        candidate_rows = [
            candidate
            for entry in strategy_entries
            for candidate in (entry.get('candidate_results') or [])
            if isinstance(candidate, dict)
        ]
        adherence_values = [_safe_float(candidate.get('format_adherence')) for candidate in candidate_rows if isinstance(candidate.get('format_adherence'), (int, float))]
        groundedness_values = [
            _safe_float(candidate.get('groundedness_score') if isinstance(candidate.get('groundedness_score'), (int, float)) else candidate.get('groundedness'))
            for candidate in candidate_rows
            if isinstance(candidate.get('groundedness_score'), (int, float)) or isinstance(candidate.get('groundedness'), (int, float))
        ]
        retention_values = [
            _safe_float(candidate.get('used_chunks') or 0.0) / max((_safe_float(candidate.get('used_chunks') or 0.0) + _safe_float(candidate.get('dropped_chunks') or 0.0)), 1.0)
            for candidate in candidate_rows
        ]
        latency_values = [_safe_float(candidate.get('latency_s')) for candidate in candidate_rows if isinstance(candidate.get('latency_s'), (int, float))]
        context_char_values = [_safe_float(candidate.get('context_preview_chars')) for candidate in candidate_rows if isinstance(candidate.get('context_preview_chars'), (int, float))]
        composite_values = [
            (float(candidate.get('format_adherence')) * 0.5) + (
                float(candidate.get('groundedness_score') if isinstance(candidate.get('groundedness_score'), (int, float)) else candidate.get('groundedness'))
                * 0.5
            )
            for candidate in candidate_rows
            if isinstance(candidate.get('format_adherence'), (int, float))
            and (isinstance(candidate.get('groundedness_score'), (int, float)) or isinstance(candidate.get('groundedness'), (int, float)))
        ]

        _register_retrieval_observation(
            strategy=strategy,
            category='Phase 7 product comparisons',
            output_value=round(_mean(adherence_values), 3) if adherence_values else None,
            retention_value=round(min(_mean(retention_values), 1.0), 3) if retention_values else None,
            composite_value=round(_mean(composite_values), 3) if composite_values else None,
            latency_value=round(_mean(latency_values), 3) if latency_values else None,
            candidate_count=len(candidate_rows),
            scored_candidate_count=len(composite_values),
            avg_context_chars=round(_mean(context_char_values), 0) if context_char_values else None,
            description=f'{strategy.replace("_", " ")} derived from persisted product comparison runs.',
        )

    for prompt_profile in prompt_profile_map.values():
        metric_summary: dict[str, Any] = {}
        if prompt_profile.get('useCaseFitValues'):
            metric_summary['useCaseFit'] = round(_mean(prompt_profile['useCaseFitValues']), 3)
        if prompt_profile.get('groundednessValues'):
            metric_summary['groundedness'] = round(_mean(prompt_profile['groundednessValues']), 3)
        if prompt_profile.get('adherenceValues'):
            metric_summary['adherence'] = round(_mean(prompt_profile['adherenceValues']), 3)
        if prompt_profile.get('decisionValues'):
            metric_summary['decisionScore'] = round(_mean(prompt_profile['decisionValues']), 3)
        if prompt_profile.get('groundingValues'):
            metric_summary['groundingRatio'] = round(_mean(prompt_profile['groundingValues']), 3)
        if prompt_profile.get('structuredValues'):
            metric_summary['structuredSuccess'] = round(_mean(prompt_profile['structuredValues']), 3)
        if prompt_profile.get('latencyValues'):
            metric_summary['latency'] = round(_mean(prompt_profile['latencyValues']), 3)
        prompt_profile['metricSummary'] = metric_summary

    models: list[dict[str, Any]] = []
    for row in model_rows.values():
        use_case_fit_values = list(row['useCaseFitValues'])
        groundedness_values = list(row['groundednessValues'])
        adherence_values = list(row['adherenceValues'])
        latency_values = list(row['latencyValues'])
        output_chars_values = list(row['outputCharsValues'])

        use_case_fit = round(_mean(use_case_fit_values), 3) if use_case_fit_values else None
        groundedness = round(_mean(groundedness_values), 3) if groundedness_values else None
        adherence = round(_mean(adherence_values), 3) if adherence_values else None
        latency = round(_mean(latency_values), 3) if latency_values else None
        output_chars = round(_mean(output_chars_values), 0) if output_chars_values else None

        score_status = 'scored' if use_case_fit is not None else 'partial'

        models.append(
            {
                'id': row['id'],
                'family': row['family'],
                'provider': row['provider'],
                'model': row['model'],
                'profileTag': row['profileTag'],
                'useCaseFit': use_case_fit,
                'groundedness': groundedness,
                'adherence': adherence,
                'latency': latency,
                'outputChars': output_chars,
                'runtimeBucket': row['runtimeBucket'],
                'quantization': row['quantization'],
                'runs': row['runs'],
                'caseCount': row['caseCount'],
                'scoreStatus': score_status,
                'sourceFamilies': sorted(str(item) for item in row['sourceFamilies']),
                'metricCoverage': {
                    'useCaseFit': len(use_case_fit_values),
                    'groundedness': len(groundedness_values),
                    'adherence': len(adherence_values),
                    'latency': len(latency_values),
                    'outputChars': len(output_chars_values),
                },
            }
        )

    def _sort_fit(value: Any) -> float:
        return float(value) if isinstance(value, (int, float)) else -1.0

    def _sort_groundedness(value: Any) -> float:
        return float(value) if isinstance(value, (int, float)) else -1.0

    def _sort_latency(value: Any) -> float:
        return float(value) if isinstance(value, (int, float)) else 10**9

    models.sort(
        key=lambda item: (
            0 if item.get('useCaseFit') is not None else 1,
            -_sort_fit(item.get('useCaseFit')),
            -_sort_groundedness(item.get('groundedness')),
            -_sort_groundedness(item.get('adherence')),
            _sort_latency(item.get('latency')),
        )
    )

    scored_models = [item for item in models if isinstance(item.get('useCaseFit'), (int, float))]
    partially_scored_models = [item for item in models if item not in scored_models]

    if scored_models:
        scored_models[0]['profileTag'] = 'Recommended production'

    fastest_candidates = [item for item in models if isinstance(item.get('latency'), (int, float))]
    if fastest_candidates:
        fastest = min(fastest_candidates, key=lambda item: float(item.get('latency') or 10**9))
        if fastest['id'] != scored_models[0]['id'] if scored_models else True:
            fastest['profileTag'] = 'Fastest observed'

    for item in models:
        if item['id'] in phase85_top_candidate_keys and not item.get('profileTag'):
            item['profileTag'] = 'Phase 8.5 winner'
        if item['provider'] not in {'ollama', 'ollama_hosted', 'huggingface_server', 'huggingface_local'} and not item.get('profileTag'):
            item['profileTag'] = 'External reference'
        if not item.get('profileTag') and item.get('scoreStatus') == 'partial':
            item['profileTag'] = 'Benchmark candidate'

    provider_summary: list[dict[str, Any]] = []
    grouped_providers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for model in models:
        grouped_providers[model['provider']].append(model)
    for provider_name, provider_models in grouped_providers.items():
        scored_provider_models = [item for item in provider_models if isinstance(item.get('useCaseFit'), (int, float))]
        latency_values = [float(item['latency']) for item in provider_models if isinstance(item.get('latency'), (int, float))]
        best_model = max(scored_provider_models, key=lambda item: float(item.get('useCaseFit') or 0.0)) if scored_provider_models else None
        provider_summary.append(
            {
                'provider': provider_name,
                'models': len(provider_models),
                'scoredModels': len(scored_provider_models),
                'bestFit': round(float(best_model.get('useCaseFit') or 0.0) * 100) if best_model else None,
                'avgLatency': round(_mean(latency_values), 2) if latency_values else None,
                'bestModel': best_model['model'] if best_model else None,
            }
        )
    provider_summary.sort(
        key=lambda item: (
            0 if item.get('bestFit') is not None else 1,
            -(item.get('bestFit') or 0),
            item.get('avgLatency') if isinstance(item.get('avgLatency'), (int, float)) else 10**9,
        )
    )

    retrieval_observations: list[dict[str, Any]] = []
    for bucket in retrieval_buckets.values():
        output_values = list(bucket['outputValues'])
        retention_values = list(bucket['retentionValues'])
        composite_values = list(bucket['compositeValues'])
        latency_values = list(bucket['latencyValues'])
        avg_context_values = list(bucket['avgContextCharsValues'])
        retrieval_observations.append(
            {
                'strategy': bucket['strategy'],
                'category': bucket['category'],
                'outputDiscipline': round(_mean(output_values), 3) if output_values else None,
                'contextRetention': round(min(_mean(retention_values), 1.0), 3) if retention_values else None,
                'composite': round(_mean(composite_values), 3) if composite_values else None,
                'latency': round(_mean(latency_values), 3) if latency_values else None,
                'candidateCount': bucket['candidateCount'],
                'scoredCandidateCount': bucket['scoredCandidateCount'],
                'avgContextChars': round(_mean(avg_context_values), 0) if avg_context_values else None,
                'description': str(bucket.get('description') or ''),
            }
        )
    retrieval_observations.sort(
        key=lambda item: (
            0 if item.get('composite') is not None else 1,
            -(item.get('composite') or 0),
            item.get('latency') if isinstance(item.get('latency'), (int, float)) else 10**9,
            item.get('strategy') or '',
        )
    )

    leaderboard_highlights: list[dict[str, Any]] = []
    if scored_models:
        leaderboard_highlights.append(
            {
                'label': 'Best scored fit',
                'model': scored_models[0]['model'],
                'detail': f"{round(float(scored_models[0]['useCaseFit']) * 100)}% use-case fit across {scored_models[0]['metricCoverage']['useCaseFit']} scored run(s)",
            }
        )
    if fastest_candidates:
        fastest_model = min(fastest_candidates, key=lambda item: float(item.get('latency') or 10**9))
        leaderboard_highlights.append(
            {
                'label': 'Fastest observed',
                'model': fastest_model['model'],
                'detail': f"{float(fastest_model['latency']):.2f}s average latency",
            }
        )
    grounded_candidates = [item for item in models if isinstance(item.get('groundedness'), (int, float))]
    if grounded_candidates:
        best_grounded = max(grounded_candidates, key=lambda item: float(item.get('groundedness') or 0.0))
        leaderboard_highlights.append(
            {
                'label': 'Best groundedness',
                'model': best_grounded['model'],
                'detail': f"{round(float(best_grounded['groundedness']) * 100)}% groundedness across {best_grounded['metricCoverage']['groundedness']} scored run(s)",
            }
        )
    retrieval_candidates = [item for item in retrieval_observations if isinstance(item.get('composite'), (int, float))]
    if retrieval_candidates:
        top_retrieval = retrieval_candidates[0]
        leaderboard_highlights.append(
            {
                'label': 'Top retrieval quality',
                'model': top_retrieval['strategy'],
                'detail': f"{round(float(top_retrieval['composite']) * 100)}% composite in {top_retrieval['category']}",
            }
        )

    phase85_case_count = 0
    for path in phase8_bundle_paths:
        bundle_payload = _load_json_payload(path)
        if isinstance(bundle_payload, dict):
            phase85_case_count += _safe_int(bundle_payload.get('total_cases') or 0)

    total_runs = _safe_int(summary.get('total_runs')) + len(phase8_bundle_paths) + len(phase45_result_paths) + len(doc_review_paths)
    source_breakdown = []
    if entries:
        source_breakdown.append(
            {
                'id': 'phase7',
                'label': 'Phase 7 comparison log',
                'bundles': 1,
                'runs': _safe_int(summary.get('total_runs')),
                'detail': 'Persisted product comparison runs already recorded in this workspace.',
            }
        )
    if phase8_bundle_paths:
        source_breakdown.append(
            {
                'id': 'phase8_5',
                'label': 'Phase 8.5 benchmark bundles',
                'bundles': len(phase8_bundle_paths),
                'runs': len(phase8_bundle_paths),
                'detail': 'Generation, embeddings, rerankers, and OCR / VLM benchmark outputs under benchmark_runs.',
            }
        )
    if phase45_result_paths:
        source_breakdown.append(
            {
                'id': 'phase4_5',
                'label': 'Phase 4.5 retrieval sweeps',
                'bundles': len(phase45_result_paths),
                'runs': len(phase45_result_paths),
                'detail': 'Embedding model, context-window, and retrieval-tuning result bundles.',
            }
        )
    if doc_review_paths:
        source_breakdown.append(
            {
                'id': 'document_review_findings',
                'label': 'Document review findings experiments',
                'bundles': len(doc_review_paths),
                'runs': len(doc_review_paths),
                'detail': 'Structured findings experiments captured in benchmark_runs.',
            }
        )

    latest_recorded_at = None
    if latest_datetimes:
        latest_candidate = max(latest_datetimes)
        latest_recorded_at = latest_candidate.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

    notes = ['Benchmarks now merges persisted phase7 comparisons with benchmark_runs bundles that exist inside this workspace.']
    if phase45_result_paths:
        notes.append('Phase 4.5 retrieval sweeps contribute retrieval observations but do not get mixed into the response-model leaderboard.')
    if partially_scored_models:
        notes.append('Some historical rows predate groundedness/use-case-fit scoring; unmeasured metrics remain visible as not scored instead of being inferred.')

    meta = _runtime_meta(workspace_root, notes=notes)
    if latest_recorded_at:
        meta['updated_at'] = latest_recorded_at

    scored_candidate_count = sum(item['metricCoverage']['useCaseFit'] for item in models)
    best_groundedness = max((float(item['groundedness']) for item in grounded_candidates), default=None) if grounded_candidates else None
    fastest_latency = min((float(item['latency']) for item in fastest_candidates), default=None) if fastest_candidates else None

    return {
        'ok': True,
        'meta': meta,
        'status': _derive_benchmark_surface_status(latest_recorded_at or latest_timestamp, has_models=bool(models)),
        'degraded_reason': (
            'No recorded benchmark bundle was found yet.'
            if total_runs == 0
            else 'Recorded benchmark bundles exist, but this workspace has no scored use-case-fit telemetry yet.'
            if not scored_models
            else None
        ),
        'summary': {
            'modelCount': len(models),
            'scoredModelCount': len(scored_models),
            'partialModelCount': len(partially_scored_models),
            'promptProfileCount': len(prompt_profile_map),
            'useCaseCount': len(use_case_labels),
            'scoredCandidateCount': scored_candidate_count,
            'bestGroundedness': round(best_groundedness, 3) if isinstance(best_groundedness, (int, float)) else None,
            'fastestLatency': round(fastest_latency, 3) if isinstance(fastest_latency, (int, float)) else None,
            'bestModel': scored_models[0]['model'] if scored_models else None,
            'totalRuns': total_runs,
            'lastRecordedAt': latest_recorded_at or latest_timestamp,
            'sourceBundleCount': sum(item['bundles'] for item in source_breakdown),
            'phase85CaseCount': phase85_case_count,
            'phase85WinnerCount': len(phase85_top_candidate_keys),
        },
        'models': models,
        'presets': [
            {
                'id': preset['id'],
                'name': preset['name'],
                'description': preset['description'],
                'metrics': preset['metrics'],
                'models': preset['models'],
                'runCount': preset.get('runCount') or 0,
                'metricSummary': preset.get('metricSummary') or {},
            }
            for preset in prompt_profile_map.values()
        ],
        'providerSummary': provider_summary,
        'leaderboardHighlights': leaderboard_highlights,
        'retrievalObservations': retrieval_observations,
        'sourceBreakdown': source_breakdown,
    }


def _build_product_eval_scope(workspace_root: Path, *, additional_product_telemetry_paths: list[Path] | None = None) -> dict[str, Any]:
    catalog = build_product_workflow_catalog()
    workflow_labels = {workflow_id: definition.label for workflow_id, definition in catalog.items()}
    capable_task_types = sorted({task_type for definition in catalog.values() for task_type in definition.backend_task_types})

    observed_workflow_ids: set[str] = set()
    workflow_history = _read_json(get_product_workflow_history_path(workspace_root), [])
    for entry in workflow_history:
        if not isinstance(entry, dict):
            continue
        workflow_id = str(entry.get('workflow_id') or '').strip()
        if workflow_id in catalog:
            observed_workflow_ids.add(workflow_id)

    telemetry_runs = list(load_product_telemetry_runs(get_product_telemetry_path(workspace_root)))
    additional_telemetry_sources: list[str] = []
    for additional_path in additional_product_telemetry_paths or []:
        additional_runs = load_product_telemetry_runs(additional_path)
        if additional_runs:
            additional_telemetry_sources.append(str(additional_path))
            telemetry_runs.extend(additional_runs)
    for run in telemetry_runs:
        if not isinstance(run, dict):
            continue
        workflow_id = str(run.get('workflow_id') or '').strip()
        if workflow_id in catalog:
            observed_workflow_ids.add(workflow_id)

    observed_task_types = sorted({
        task_type
        for workflow_id in observed_workflow_ids
        for task_type in catalog[workflow_id].backend_task_types
    })

    return {
        'catalog': catalog,
        'workflow_labels': workflow_labels,
        'capable_task_types': capable_task_types,
        'observed_workflow_ids': sorted(observed_workflow_ids),
        'observed_workflow_labels': [workflow_labels[workflow_id] for workflow_id in sorted(observed_workflow_ids)],
        'observed_task_types': observed_task_types,
        'telemetry_runs': telemetry_runs,
        'additional_telemetry_sources': additional_telemetry_sources,
        'workflow_history_count': len([entry for entry in workflow_history if isinstance(entry, dict)]),
    }




def _technical_failure_markers() -> tuple[str, ...]:
    return (
        'document agent execution failed',
        'execution failed:',
        'http error',
        '401',
        '403',
        'unauthorized',
        'forbidden',
        'timeout',
        'timed out',
        'traceback',
        'no valid json',
        'remote end closed',
        'connection refused',
        'workflow failed',
        'parse failure',
        'json object could be extracted',
        'insufficient_document_summaries',
    )


def _live_run_text_blob(run: dict[str, Any]) -> str:
    # Only technical fields should participate in technical-failure detection.
    # Business language can contain terms like "exception justification", which is not a runtime exception.
    values = [
        run.get('status'),
        run.get('review_reason'),
        run.get('error_message'),
    ]
    return ' '.join(str(value or '') for value in values).casefold()


def _has_live_run_technical_failure(run: dict[str, Any]) -> bool:
    status = str(run.get('status') or '').strip().lower()
    text_blob = _live_run_text_blob(run)
    return (
        status in {'error', 'failed', 'failure'}
        or any(marker in text_blob for marker in _technical_failure_markers())
    )


def _safe_count_from_run(run: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = run.get(key)
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, float):
            return max(int(value), 0)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for nested_key in (
                'findings',
                'deltas',
                'differences',
                'must_fix_items',
                'negotiation_priorities',
                'actions',
                'next_steps',
                'highlights',
                'strengths',
                'watchouts',
                'interview_focus',
            ):
                nested_value = value.get(nested_key)
                if isinstance(nested_value, list) and nested_value:
                    return len(nested_value)
    return 0


def _surface_count_from_live_run(run: dict[str, Any]) -> tuple[int, str]:
    """Return count + label for useful workflow-specific surfaced output."""
    workflow_id = str(run.get('workflow_id') or run.get('workflowId') or '').strip()

    common_keys = (
        'findings_count',
        'finding_count',
        'findings',
        'highlights',
        'actions',
        'next_steps',
        'watchouts',
        'result_view',
        'view',
        'preview_payload',
    )

    if workflow_id == 'policy_contract_comparison':
        count = _safe_count_from_run(
            run,
            'deltas',
            'differences',
            'must_fix_items',
            'negotiation_priorities',
            'comparison_findings',
            *common_keys,
        )
        return count, 'comparison output'

    if workflow_id == 'candidate_review':
        count = _safe_count_from_run(
            run,
            'strengths',
            'gaps',
            'risks',
            'watchouts',
            'interview_focus',
            'recommendations',
            *common_keys,
        )
        return count, 'candidate review output'

    if workflow_id == 'action_plan_evidence_review':
        count = _safe_count_from_run(
            run,
            'actions',
            'action_items',
            'next_steps',
            'evidence_gaps',
            'risks',
            *common_keys,
        )
        return count, 'action plan output'

    count = _safe_count_from_run(run, *common_keys)
    return count, 'finding(s)'


def _score_live_product_workflow_run(run: dict[str, Any]) -> tuple[float, list[str], str, str]:
    """Cheap operational proxy for model output quality.

    This is not an LLM judge. It scores execution health, output structure,
    useful surfaced content, and review/warning signals.
    """
    status = str(run.get('status') or '').strip().lower()
    review_reason = str(run.get('review_reason') or '').strip()
    error_message = str(run.get('error_message') or '').strip()

    warnings_value = run.get('warnings')
    warnings = warnings_value if isinstance(warnings_value, list) else []

    factors: list[str] = []

    if _has_live_run_technical_failure(run):
        factors.append('technical failure or provider/parse error detected')
        return 0.35, factors, 'Fail', 'Technical failure'

    score = 0.62

    if status in {'completed', 'warning'}:
        score += 0.12
        factors.append('workflow completed')
    else:
        score -= 0.10
        factors.append(f'workflow status: {status or "unknown"}')

    if str(run.get('summary') or '').strip():
        score += 0.05
        factors.append('summary present')
    else:
        score -= 0.05
        factors.append('summary missing')

    surface_count, surface_label = _surface_count_from_live_run(run)
    summary_present = bool(str(run.get('summary') or '').strip())

    if surface_count > 0:
        score += min(0.10, 0.04 + 0.015 * min(surface_count, 4))
        factors.append(f'{surface_count} {surface_label} item(s) surfaced')
    elif review_reason:
        score += 0.02
        factors.append('review rationale present')
    elif summary_present:
        # Some live eval rows only retain summary/status, not the full result_view.
        # This is not a failure, but it is partial evaluation coverage, so keep it
        # below the PASS threshold unless richer artifacts are available.
        score -= 0.05
        factors.append('summary-only output available')
    else:
        score -= 0.06
        factors.append('no workflow output surfaced')

    if str(run.get('recommendation') or '').strip():
        score += 0.05
        factors.append('recommendation present')

    if bool(run.get('needs_review')):
        score -= 0.04
        factors.append('needs review signal present')

    if warnings:
        penalty = min(0.06, 0.015 * len(warnings))
        score -= penalty
        factors.append(f'{len(warnings)} warning/review signal(s)')

    if review_reason:
        score -= 0.02
        factors.append('review reason present')

    if error_message:
        score -= 0.12
        factors.append('error message present')

    score = round(max(0.20, min(1.0, score)), 3)

    technical_status = 'Pass'
    has_review_signal = bool(run.get('needs_review')) or bool(review_reason) or bool(warnings)
    has_summary_only_output = 'summary-only output available' in factors

    if has_summary_only_output and not has_review_signal:
        review_signal = 'Partial eval coverage'
    elif score >= 0.82 or (score >= 0.75 and not has_review_signal):
        review_signal = 'Clean'
    elif score >= 0.60:
        review_signal = 'Needs review'
    else:
        review_signal = 'Poor output'

    return score, factors, technical_status, review_signal


def _build_live_product_eval_cases(scope: dict[str, Any], historical_entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    catalog = scope.get('catalog') if isinstance(scope.get('catalog'), dict) else {}
    workflow_labels = scope.get('workflow_labels') if isinstance(scope.get('workflow_labels'), dict) else {}
    observed_workflow_ids = [workflow_id for workflow_id in (scope.get('observed_workflow_ids') or []) if workflow_id in catalog]
    telemetry_runs = [run for run in (scope.get('telemetry_runs') or []) if isinstance(run, dict)]

    live_cases: list[dict[str, Any]] = []
    workflow_buckets: dict[str, dict[str, Any]] = {}
    provider_buckets: dict[str, dict[str, Any]] = {}
    task_buckets: dict[str, dict[str, Any]] = {}

    filtered_runs = [run for run in telemetry_runs if str(run.get('workflow_id') or '').strip() in observed_workflow_ids]
    filtered_runs.sort(key=lambda item: str(item.get('completed_at') or item.get('started_at') or ''), reverse=True)

    for index, run in enumerate(filtered_runs):
        workflow_id = str(run.get('workflow_id') or '').strip()
        runtime = run.get('runtime') if isinstance(run.get('runtime'), dict) else {}
        status = str(run.get('status') or '').strip().lower()
        score, score_factors, technical_status, review_signal = _score_live_product_workflow_run(run)
        # Evals verdict is based on model-output quality score.
        # 0.75+ is good enough to count as PASS while reviewSignal still communicates
        # whether the output needs human/business review.
        verdict = 'PASS' if score >= 0.75 else 'WARN' if score >= 0.55 else 'FAIL'
        provider = str(runtime.get('provider') or 'unknown')
        model = str(runtime.get('model') or 'unknown')
        latency = round(_safe_float(runtime.get('latency_s') or 0.0), 3)
        timestamp = _format_timestamp(run.get('completed_at') or run.get('started_at')) or _now_iso()
        reasons: list[str] = []
        review_reason = str(run.get('review_reason') or '').strip()
        error_message = str(run.get('error_message') or '').strip()
        if review_reason:
            reasons.append(review_reason)
        if error_message:
            reasons.append(error_message)
        task_type = workflow_id
        live_case = {
            'id': str(run.get('run_id') or f'live-{workflow_id}-{index + 1}'),
            'task': workflow_labels.get(workflow_id, workflow_id.replace('_', ' ').title()),
            'taskType': task_type,
            'workflowId': workflow_id,
            'suite': 'live_product_workflows',
            'verdict': verdict,
            'score': round(score, 3),
            'modelQualityScore': round(score, 3),
            'scoreFactors': score_factors,
            'technicalStatus': technical_status,
            'reviewSignal': review_signal,
            'needsReview': bool(run.get('needs_review')),
            'model': model,
            'provider': provider,
            'latency': latency,
            'timestamp': timestamp,
            'reason': '; '.join(reasons[:2]) or None,
            'errorDetail': '; '.join(reasons[:3]) or None,
            'sourceKind': 'live',
            'traceId': str(run.get('trace_id') or '').strip() or None,
            'runId': str(run.get('run_id') or '').strip() or None,
        }
        live_cases.append(live_case)

        workflow_bucket = workflow_buckets.setdefault(workflow_id, {'workflowId': workflow_id, 'label': workflow_labels.get(workflow_id, workflow_id), 'pass': 0, 'warn': 0, 'fail': 0, 'total': 0})
        workflow_bucket[verdict.lower()] += 1
        workflow_bucket['total'] += 1

        provider_bucket = provider_buckets.setdefault(provider, {'provider': provider, 'total': 0, 'passes': 0, 'failures': 0, 'warnings': 0})
        provider_bucket['total'] += 1
        provider_bucket['passes'] += 1 if verdict == 'PASS' else 0
        provider_bucket['warnings'] += 1 if verdict == 'WARN' else 0
        provider_bucket['failures'] += 1 if verdict == 'FAIL' else 0

        for backend_task_type in catalog.get(workflow_id).backend_task_types if workflow_id in catalog else []:
            task_bucket = task_buckets.setdefault(backend_task_type, {'task': backend_task_type, 'total': 0, 'passes': 0, 'score_values': [], 'warnings': 0, 'failures': 0})
            task_bucket['total'] += 1
            task_bucket['passes'] += 1 if verdict == 'PASS' else 0
            task_bucket['warnings'] += 1 if verdict == 'WARN' else 0
            task_bucket['failures'] += 1 if verdict == 'FAIL' else 0
            task_bucket['score_values'].append(score)

    if not live_cases:
        for entry in historical_entries:
            metadata = entry.get('metadata') if isinstance(entry.get('metadata'), dict) else {}
            if str(metadata.get('source') or '').strip() != 'product_runtime_sample':
                continue
            workflow_id = str(entry.get('task_type') or '').strip()
            if workflow_id not in observed_workflow_ids:
                continue
            status = str(entry.get('status') or 'WARN').upper()
            verdict = 'PASS' if status == 'PASS' else 'FAIL' if status == 'FAIL' else 'WARN'
            score_ratio = 0.0
            max_score = _safe_float(entry.get('max_score') or 0.0)
            if max_score > 0:
                score_ratio = _safe_float(entry.get('score') or 0.0) / max_score
            score_ratio = min(max(score_ratio, 0.0), 1.0)
            live_cases.append({
                'id': str(entry.get('id') or f'live-fallback-{len(live_cases) + 1}'),
                'task': workflow_labels.get(workflow_id, workflow_id.replace('_', ' ').title()),
                'taskType': workflow_id,
                'workflowId': workflow_id,
                'suite': 'live_product_workflows',
                'verdict': verdict,
                'score': round(score_ratio, 3),
                'needsReview': bool(entry.get('needs_review')),
                'model': str(entry.get('model') or 'unknown'),
                'provider': str(entry.get('provider') or 'unknown'),
                'latency': round(_safe_float(entry.get('latency_s') or 0.0), 3),
                'timestamp': _format_timestamp(entry.get('created_at')) or _now_iso(),
                'reason': '; '.join(str(reason) for reason in (entry.get('reasons') or [])[:2]) or None,
                'errorDetail': '; '.join(str(reason) for reason in (entry.get('reasons') or [])[:3]) or None,
                'sourceKind': 'live',
                'traceId': str(metadata.get('trace_id') or '').strip() or None,
                'runId': str(metadata.get('run_id') or '').strip() or None,
            })

    live_cases.sort(key=lambda item: str(item.get('timestamp') or ''), reverse=True)
    verdict_counter = Counter(str(item.get('verdict') or 'WARN') for item in live_cases)
    live_summary = {
        'total': len(live_cases),
        'pass': int(verdict_counter.get('PASS', 0)),
        'warn': int(verdict_counter.get('WARN', 0)),
        'fail': int(verdict_counter.get('FAIL', 0)),
        'review': sum(1 for item in live_cases if bool(item.get('needsReview'))),
        'passRate': round((int(verdict_counter.get('PASS', 0)) / max(len(live_cases), 1)) * 100) if live_cases else 0,
        'workflowBreakdown': sorted(workflow_buckets.values(), key=lambda item: (-int(item.get('total') or 0), str(item.get('label') or ''))),
        'providerBreakdown': sorted([
            {
                'provider': bucket['provider'],
                'total': bucket['total'],
                'failures': bucket['failures'],
                'warnings': bucket['warnings'],
                'passRate': round((bucket['passes'] / max(bucket['total'], 1)) * 100),
            }
            for bucket in provider_buckets.values()
        ], key=lambda item: (-int(item.get('total') or 0), str(item.get('provider') or ''))),
        'taskBreakdown': sorted([
            {
                'task': bucket['task'],
                'total': bucket['total'],
                'passRate': round((bucket['passes'] / max(bucket['total'], 1)) * 100),
                'avgScore': round(_mean(bucket['score_values']), 3),
                'warnings': bucket['warnings'],
                'failures': bucket['failures'],
            }
            for bucket in task_buckets.values()
        ], key=lambda item: (-int(item.get('total') or 0), str(item.get('task') or ''))),
    }
    return live_cases, live_summary


def build_lab_evals_payload(workspace_root: Path, *, additional_product_telemetry_paths: list[Path] | None = None) -> dict[str, Any]:
    scope = _build_product_eval_scope(workspace_root, additional_product_telemetry_paths=additional_product_telemetry_paths)
    observed_task_types = [task_type for task_type in (scope.get('observed_task_types') or []) if str(task_type or '').strip()]
    all_entries = load_eval_runs(get_phase8_eval_db_path(workspace_root))
    historical_entries = []
    for entry in all_entries:
        if not isinstance(entry, dict):
            continue
        metadata = entry.get('metadata') if isinstance(entry.get('metadata'), dict) else {}
        if str(metadata.get('source') or '').strip() == 'product_runtime_sample':
            continue
        if str(entry.get('task_type') or '').strip() in observed_task_types:
            historical_entries.append(entry)

    summary = summarize_eval_runs(historical_entries)
    diagnosis = build_eval_diagnosis(historical_entries)

    suites_map: dict[str, dict[str, Any]] = {}
    provider_map: dict[str, dict[str, Any]] = {}
    task_map: dict[str, dict[str, Any]] = {}
    historical_cases = []
    watchlist = []

    for entry in historical_entries:
        suite_name = str(entry.get('suite_name') or 'general')
        task_type = str(entry.get('task_type') or 'task')
        status = str(entry.get('status') or 'WARN').upper()
        verdict = 'PASS' if status == 'PASS' else 'FAIL' if status == 'FAIL' else 'WARN'
        needs_review = bool(entry.get('needs_review'))
        score_ratio = 0.0
        max_score = _safe_float(entry.get('max_score') or 0.0)
        if max_score > 0:
            score_ratio = _safe_float(entry.get('score') or 0.0) / max_score
        score_ratio = min(max(score_ratio, 0.0), 1.0)
        case_payload = {
            'id': str(entry.get('id') or f'{suite_name}-{task_type}-{len(historical_cases) + 1}'),
            'task': task_type,
            'taskType': task_type,
            'workflowId': None,
            'suite': suite_name,
            'verdict': verdict,
            'score': round(score_ratio, 3),
            'needsReview': needs_review,
            'model': str(entry.get('model') or 'unknown'),
            'provider': str(entry.get('provider') or 'unknown'),
            'latency': round(_safe_float(entry.get('latency_s') or 0.0), 3),
            'timestamp': _format_timestamp(entry.get('created_at')) or _now_iso(),
            'reason': '; '.join(str(reason) for reason in (entry.get('reasons') or [])[:2]) or None,
            'errorDetail': '; '.join(str(reason) for reason in (entry.get('reasons') or [])[:3]) or None,
            'sourceKind': 'historical',
        }
        historical_cases.append(case_payload)
        if verdict in {'WARN', 'FAIL'} or needs_review:
            watchlist.append(case_payload)

        suite_bucket = suites_map.setdefault(suite_name, {'name': suite_name, 'total': 0, 'pass': 0, 'warn': 0, 'fail': 0, 'needsReview': 0, 'lastRun': _format_timestamp(entry.get('created_at')) or _now_iso()})
        suite_bucket['total'] += 1
        suite_bucket[verdict.lower()] += 1
        suite_bucket['needsReview'] += 1 if needs_review else 0
        suite_bucket['lastRun'] = max(str(suite_bucket['lastRun']), str(entry.get('created_at') or suite_bucket['lastRun']))

        provider_name = str(entry.get('provider') or 'unknown')
        provider_bucket = provider_map.setdefault(provider_name, {'provider': provider_name, 'total': 0, 'failures': 0, 'warnings': 0, 'passes': 0})
        provider_bucket['total'] += 1
        provider_bucket['failures'] += 1 if verdict == 'FAIL' else 0
        provider_bucket['warnings'] += 1 if verdict == 'WARN' else 0
        provider_bucket['passes'] += 1 if verdict == 'PASS' else 0

        task_bucket = task_map.setdefault(task_type, {'task': task_type, 'total': 0, 'passes': 0, 'warnings': 0, 'failures': 0, 'score_values': []})
        task_bucket['total'] += 1
        task_bucket['passes'] += 1 if verdict == 'PASS' else 0
        task_bucket['warnings'] += 1 if verdict == 'WARN' else 0
        task_bucket['failures'] += 1 if verdict == 'FAIL' else 0
        task_bucket['score_values'].append(score_ratio)

    suites = list(suites_map.values())
    suites.sort(key=lambda item: item['name'])
    provider_breakdown = sorted([
        {
            'provider': bucket['provider'],
            'total': bucket['total'],
            'failures': bucket['failures'],
            'warnings': bucket['warnings'],
            'passRate': round((bucket['passes'] / max(bucket['total'], 1)) * 100),
        }
        for bucket in provider_map.values()
    ], key=lambda item: (-item['total'], item['provider']))

    task_breakdown = sorted([
        {
            'task': bucket['task'],
            'total': bucket['total'],
            'passRate': round((bucket['passes'] / max(bucket['total'], 1)) * 100),
            'avgScore': round(_mean(bucket['score_values']), 3),
            'warnings': bucket['warnings'],
            'failures': bucket['failures'],
        }
        for bucket in task_map.values()
    ], key=lambda item: (-item['total'], item['task']))

    status_counts = summary.get('status_counts') if isinstance(summary.get('status_counts'), dict) else {}
    pass_count = _safe_int(status_counts.get('PASS'))
    warn_count = _safe_int(status_counts.get('WARN'))
    fail_count = _safe_int(status_counts.get('FAIL'))
    historical_totals = {
        'pass': pass_count,
        'warn': warn_count,
        'fail': fail_count,
        'review': sum(1 for entry in historical_entries if bool(entry.get('needs_review'))),
        'total': _safe_int(summary.get('total_runs')),
    }
    historical_pass_rate = round(_safe_float(summary.get('pass_rate')) * 100) if historical_totals['total'] else 0

    live_cases, live_summary = _build_live_product_eval_cases(scope, historical_entries)

    recent_live_window_size = 10
    recent_live_cases = live_cases[:recent_live_window_size]
    recent_live_verdict_counter = Counter(str(item.get('verdict') or 'WARN') for item in recent_live_cases)
    recent_live_summary = {
        'total': len(recent_live_cases),
        'pass': int(recent_live_verdict_counter.get('PASS', 0)),
        'warn': int(recent_live_verdict_counter.get('WARN', 0)),
        'fail': int(recent_live_verdict_counter.get('FAIL', 0)),
        'review': sum(1 for item in recent_live_cases if bool(item.get('needsReview'))),
        'passRate': round((int(recent_live_verdict_counter.get('PASS', 0)) / max(len(recent_live_cases), 1)) * 100) if recent_live_cases else 0,
    }
    recent_live_window = {
        'label': f"last {len(recent_live_cases)} visible product check{'s' if len(recent_live_cases) != 1 else ''}" if recent_live_cases else 'no recent visible product checks',
        'size': len(recent_live_cases),
        'maxSize': recent_live_window_size,
        'source': 'visible product telemetry',
    }

    combined_cases = sorted([*live_cases, *historical_cases], key=lambda item: str(item.get('timestamp') or ''), reverse=True)
    combined_watchlist = [item for item in combined_cases if str(item.get('verdict') or '') in {'WARN', 'FAIL'} or bool(item.get('needsReview'))]
    fail_cases = [item for item in combined_cases if str(item.get('verdict') or '') == 'FAIL']
    global_recommendation = diagnosis.get('decision_summary', {}).get('global_recommendation') if isinstance(diagnosis, dict) else None
    diagnosis_payload = dict(diagnosis) if isinstance(diagnosis, dict) else {}
    diagnosis_payload['globalRecommendation'] = str(global_recommendation or '').replace('_', ' ') or 'Review the worst-performing task slices and rerun the impacted eval suites.'

    historical_present = historical_totals['total'] > 0
    live_present = live_summary.get('total', 0) > 0
    if live_present:
        status = 'live'
    elif historical_present:
        status = 'derived-live'
    else:
        status = 'empty'

    if not observed_task_types:
        degraded_reason = 'This surface now scopes to workflows actually observed in the product. Run product workflows first so live and historical product-only evals can appear.'
    elif not historical_present and not live_present:
        degraded_reason = 'No eval history matched the workflows currently observed in the product.'
    elif live_present and not historical_present:
        degraded_reason = 'Live product evals are available. Historical baseline is still empty for the currently observed workflows.'
    elif historical_present and not live_present:
        degraded_reason = 'Historical product-scoped evals are available. No recent live product evals were sampled yet.'
    else:
        degraded_reason = None

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['Evals & Diagnosis is now scoped to workflows actually observed in the product and separates live product evals from historical baselines.']),
        'status': status,
        'degraded_reason': degraded_reason,
        'scope': {
            'observedWorkflowIds': scope.get('observed_workflow_ids') or [],
            'observedWorkflowLabels': scope.get('observed_workflow_labels') or [],
            'observedTaskTypes': observed_task_types,
            'capableTaskTypes': scope.get('capable_task_types') or [],
        },
        'passRate': historical_pass_rate,
        'totals': historical_totals,
        'suites': suites,
        'cases': combined_cases[:120],
        'historicalCases': historical_cases[:80],
        'liveCases': live_cases[:40],
        'recentLiveCases': recent_live_cases,
        'providerBreakdown': provider_breakdown,
        'taskBreakdown': task_breakdown,
        'liveProviderBreakdown': live_summary.get('providerBreakdown') or [],
        'liveTaskBreakdown': live_summary.get('taskBreakdown') or [],
        'liveWorkflowBreakdown': live_summary.get('workflowBreakdown') or [],
        'liveTotals': {
            'pass': int(live_summary.get('pass') or 0),
            'warn': int(live_summary.get('warn') or 0),
            'fail': int(live_summary.get('fail') or 0),
            'review': int(live_summary.get('review') or 0),
            'total': int(live_summary.get('total') or 0),
        },
        'livePassRate': int(live_summary.get('passRate') or 0),
        'recentLiveTotals': {
            'pass': int(recent_live_summary.get('pass') or 0),
            'warn': int(recent_live_summary.get('warn') or 0),
            'fail': int(recent_live_summary.get('fail') or 0),
            'review': int(recent_live_summary.get('review') or 0),
            'total': int(recent_live_summary.get('total') or 0),
        },
        'recentLivePassRate': int(recent_live_summary.get('passRate') or 0),
        'recentLiveWindow': recent_live_window,
        'watchlist': combined_watchlist[:16],
        'liveWatchlist': [item for item in live_cases if str(item.get('verdict') or '') in {'WARN', 'FAIL'} or bool(item.get('needsReview'))][:10],
        'historicalWatchlist': [item for item in historical_cases if str(item.get('verdict') or '') in {'WARN', 'FAIL'} or bool(item.get('needsReview'))][:10],
        'investigateFirst': fail_cases[:12],
        'diagnosis': diagnosis_payload,
    }


def _normalize_lab_artifact_status(status: Any) -> str:
    normalized = str(status or '').strip().lower()
    if normalized == 'ready':
        return 'ready'
    if normalized == 'error':
        return 'error'
    if normalized in {'warning', 'disabled', 'service_unavailable'}:
        return 'warning'
    return 'pending'


def _lab_artifact_type(entry: dict[str, Any]) -> str:
    export_kind = str(entry.get('export_kind') or '').strip().lower()
    workflow_label = str(entry.get('workflow_label') or '').strip().lower()
    if export_kind == 'benchmark_eval_executive_deck':
        return 'benchmark_bundle'
    if export_kind == 'evidence_pack_deck' or 'evidence' in workflow_label:
        return 'evidence_bundle'
    return 'deck_bundle'


def _build_lab_artifact_inventory(workspace_root: Path) -> list[dict[str, Any]]:
    artifact_root = get_artifact_root(workspace_root) / 'presentation_exports'
    if not artifact_root.exists() or not artifact_root.is_dir():
        return []

    metadata_paths = sorted(artifact_root.glob('deckexp_*/metadata.json'), key=lambda item: item.stat().st_mtime, reverse=True)
    bundles: list[dict[str, Any]] = []
    for metadata_path in metadata_paths:
        normalized = _normalize_artifact_entry_from_metadata(metadata_path)
        if not isinstance(normalized, dict):
            continue
        status = _normalize_lab_artifact_status(normalized.get('status'))
        workflow_label = str(normalized.get('workflow_label') or '').strip() or 'Unlabeled workflow'
        export_kind = str(normalized.get('export_kind') or '').strip() or 'deck_export'
        slide_count = _safe_int(normalized.get('slide_count') or 0)
        preview_count = _safe_int(normalized.get('preview_count') or 0)
        issue_count = _safe_int(normalized.get('issue_count') or 0)
        warning_count = _safe_int(normalized.get('warning_count') or 0)
        asset_count = _safe_int(normalized.get('asset_count') or 0)
        average_score = normalized.get('average_score')
        review_status = str(normalized.get('review_status') or '').strip() or None
        description_parts: list[str] = [export_kind.replace('_', ' ')]
        if slide_count:
            description_parts.append(f'{slide_count} slide(s)')
        if preview_count:
            description_parts.append(f'{preview_count} preview(s)')
        if issue_count:
            description_parts.append(f'{issue_count} issue(s)')
        elif warning_count:
            description_parts.append(f'{warning_count} warning(s)')
        if isinstance(average_score, (int, float)) and average_score > 0:
            description_parts.append(f'avg score {average_score:.2f}')
        if review_status:
            description_parts.append(f'review {review_status}')

        bundles.append(
            {
                'id': str(normalized.get('id') or metadata_path.parent.name),
                'name': str(normalized.get('title') or normalized.get('name') or metadata_path.parent.name),
                'type': _lab_artifact_type(normalized),
                'category': workflow_label,
                'version': str(normalized.get('id') or metadata_path.parent.name),
                'createdAt': _format_timestamp(normalized.get('created_at')) or datetime.fromtimestamp(metadata_path.stat().st_mtime, tz=timezone.utc).isoformat(),
                'size': str(normalized.get('size') or _bytes_label(normalized.get('pptx_size_bytes') or 0)),
                'status': status,
                'description': ' · '.join(part for part in description_parts if part),
                'workflowLabel': workflow_label,
                'exportKind': export_kind,
                'slideCount': slide_count,
                'previewCount': preview_count,
                'issueCount': issue_count,
                'warningCount': warning_count,
                'assetCount': asset_count,
            }
        )
    bundles.sort(key=lambda item: str(item.get('createdAt') or ''), reverse=True)
    return bundles




def _workflow_run_id_for_artifact_link(run: dict[str, Any]) -> str:
    return str(run.get('run_id') or run.get('id') or run.get('trace_id') or '').strip()


def _parse_artifact_link_timestamp(value: Any) -> datetime | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    try:
        if raw.endswith('Z'):
            raw = raw[:-1] + '+00:00'
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _collect_artifact_link_strings(value: Any, *, limit: int = 80) -> list[str]:
    collected: list[str] = []

    def walk(item: Any) -> None:
        if len(collected) >= limit:
            return
        if isinstance(item, str):
            normalized = item.strip()
            if normalized:
                collected.append(normalized.lower())
            return
        if isinstance(item, (int, float)):
            return
        if isinstance(item, dict):
            for key, nested in item.items():
                if str(key).lower() in {'artifact_path', 'artifact_label', 'path', 'label', 'name', 'id', 'export_id', 'version', 'local_pptx_path', 'local_artifact_dir', 'remote_output_path'}:
                    walk(nested)
                elif key in {'artifacts', 'artifact_items', 'delivery_outputs', 'result', 'response_payload'}:
                    walk(nested)
            return
        if isinstance(item, list):
            for nested in item:
                walk(nested)

    walk(value)
    return collected


def _artifact_matches_workflow_run(artifact: dict[str, Any], run: dict[str, Any]) -> bool:
    artifact_id = str(artifact.get('id') or artifact.get('version') or '').strip().lower()
    artifact_name = str(artifact.get('name') or '').strip().lower()
    artifact_workflow = str(artifact.get('workflowLabel') or artifact.get('category') or '').strip().lower()

    run_tokens = _collect_artifact_link_strings(run)
    if artifact_id and any(artifact_id in token for token in run_tokens):
        return True
    if artifact_name and any(artifact_name in token for token in run_tokens):
        return True

    run_workflow = str(run.get('workflow_label') or run.get('workflowLabel') or '').strip().lower()
    if artifact_workflow and run_workflow and artifact_workflow != run_workflow:
        return False

    artifact_ts = _parse_artifact_link_timestamp(artifact.get('createdAt'))
    run_ts = _parse_artifact_link_timestamp(run.get('timestamp') or run.get('created_at') or run.get('updated_at'))
    if artifact_ts and run_ts:
        distance_s = abs((artifact_ts - run_ts).total_seconds())
        if distance_s <= 6 * 60 * 60:
            return True

    return False


def _load_product_history_runs_for_artifacts(workspace_root: Path) -> list[dict[str, Any]]:
    raw = _read_json(get_product_workflow_history_path(workspace_root), [])
    if isinstance(raw, dict):
        entries = raw.get('runs') or raw.get('history') or raw.get('items') or []
    elif isinstance(raw, list):
        entries = raw
    else:
        entries = []

    normalized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        run = dict(entry)
        run.setdefault('run_id', str(entry.get('run_id') or entry.get('id') or '').strip())
        run.setdefault('created_at', entry.get('timestamp') or entry.get('created_at') or entry.get('updated_at'))
        normalized.append(run)
    return normalized


def _merge_artifact_workflow_runs(*run_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in run_groups:
        for entry in group:
            if not isinstance(entry, dict):
                continue
            run_id = _workflow_run_id_for_artifact_link(entry)
            key = run_id or json.dumps(entry, sort_keys=True, default=str)[:160]
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)
    merged.sort(key=lambda item: str(item.get('timestamp') or item.get('created_at') or item.get('updated_at') or ''), reverse=True)
    return merged


def _build_artifact_workflow_linkage(artifacts: list[dict[str, Any]], workflow_runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    linked: dict[str, dict[str, Any]] = {}
    for run in workflow_runs:
        run_id = _workflow_run_id_for_artifact_link(run)
        if not run_id:
            continue
        for artifact in artifacts:
            if _artifact_matches_workflow_run(artifact, run):
                linked[run_id] = artifact
                break
    return linked


def build_lab_artifacts_payload(workspace_root: Path) -> dict[str, Any]:
    artifacts = _build_lab_artifact_inventory(workspace_root)
    chat_sessions = load_lab_chat_sessions(get_lab_chat_sessions_path(workspace_root))
    lab_workflow_runs = load_lab_workflow_runs(get_lab_workflow_runs_path(workspace_root))
    product_workflow_runs = _load_product_history_runs_for_artifacts(workspace_root)
    workflow_runs = _merge_artifact_workflow_runs(lab_workflow_runs, product_workflow_runs)
    linked_artifacts_by_run_id = _build_artifact_workflow_linkage(artifacts, workflow_runs)

    def _is_bundle_link(run: dict[str, Any]) -> bool:
        run_id = _workflow_run_id_for_artifact_link(run)
        artifact_path = str(run.get('artifact_path') or '').strip().lower()
        artifact_label = str(run.get('artifact_label') or '').strip().lower()
        return bool(run_id and run_id in linked_artifacts_by_run_id) or 'deckexp_' in artifact_path or artifact_path.endswith('.pptx') or 'deck' in artifact_label

    linked_workflow_runs = [run for run in workflow_runs if _is_bundle_link(run)]
    latest_linked_run = linked_workflow_runs[0] if linked_workflow_runs else None
    latest_linked_artifact = linked_artifacts_by_run_id.get(_workflow_run_id_for_artifact_link(latest_linked_run or {})) if latest_linked_run else None

    ready_count = sum(1 for item in artifacts if item['status'] == 'ready')
    warning_count = sum(1 for item in artifacts if item['status'] == 'warning')
    error_count = sum(1 for item in artifacts if item['status'] == 'error')
    preview_assets = sum(_safe_int(item.get('previewCount') or 0) for item in artifacts)
    total_issues = sum(_safe_int(item.get('issueCount') or 0) for item in artifacts)
    workflow_count = len({str(item.get('workflowLabel') or '').strip() for item in artifacts if str(item.get('workflowLabel') or '').strip()})
    benchmark_count = sum(1 for item in artifacts if item.get('type') == 'benchmark_bundle')

    diagnostics = [
        {'label': 'Artifact root', 'detail': 'presentation_exports metadata registry is connected.', 'status': 'connected', 'health': 'healthy' if artifacts else 'neutral'},
        {'label': 'Bundle registry', 'detail': f'{len(artifacts)} product-visible export bundle(s) were derived from top-level metadata manifests.', 'status': 'ready' if artifacts else 'empty', 'health': 'healthy' if artifacts else 'neutral'},
        {'label': 'Workflow linkage', 'detail': f'{len(linked_workflow_runs)} of {len(workflow_runs)} persisted workflow run(s) currently point to a captured artifact bundle.', 'status': 'linked' if linked_workflow_runs else ('warning' if workflow_runs else 'empty'), 'health': 'healthy' if linked_workflow_runs else ('warning' if workflow_runs else 'neutral')},
        {'label': 'Attention required', 'detail': f'{error_count} failed bundle(s) and {warning_count} bundle(s) with degraded or disabled posture.', 'status': 'warning' if (error_count or warning_count) else 'ready', 'health': 'warning' if (error_count or warning_count) else 'healthy'},
        {'label': 'Chat capture registry', 'detail': f'{len(chat_sessions)} persisted chat session(s) are visible to the artifact surface.', 'status': 'linked' if chat_sessions else 'empty', 'health': 'healthy' if chat_sessions else 'neutral'},
    ]
    summary = {
        'totalArtifacts': len(artifacts),
        'readyArtifacts': ready_count,
        'warningArtifacts': warning_count,
        'errorArtifacts': error_count,
        'chatSessions': len(chat_sessions),
        'workflowRuns': len(workflow_runs),
        'linkedWorkflowRuns': len(linked_workflow_runs),
        'unlinkedWorkflowRuns': max(len(workflow_runs) - len(linked_workflow_runs), 0),
        'previewAssets': preview_assets,
        'issueCount': total_issues,
        'workflowCount': workflow_count,
        'benchmarkArtifacts': benchmark_count,
    }
    run_registry = {
        'chatSessions': len(chat_sessions),
        'workflowRuns': len(workflow_runs),
        'latestChatSession': str(chat_sessions[0].get('session_id') or '') if chat_sessions else None,
        'latestWorkflowRun': _workflow_run_id_for_artifact_link(workflow_runs[0]) if workflow_runs else None,
        'latestWorkflowArtifact': {
            'label': str((latest_linked_artifact or {}).get('name') or (latest_linked_run or {}).get('artifact_label') or Path(str((latest_linked_run or {}).get('artifact_path') or '')).name or 'Workflow artifact').strip() or 'Workflow artifact',
            'artifactId': str((latest_linked_artifact or {}).get('id') or '').strip() or None,
            'runId': _workflow_run_id_for_artifact_link(latest_linked_run or {}) or None,
            'updatedAt': _format_timestamp((latest_linked_run or {}).get('updated_at') or (latest_linked_run or {}).get('created_at') or (latest_linked_run or {}).get('timestamp')),
        } if latest_linked_run else None,
    }
    recent_captures = [
        {
            'id': item['id'],
            'label': item['name'],
            'workflowLabel': item.get('workflowLabel'),
            'exportKind': item.get('exportKind'),
            'status': item['status'],
            'createdAt': item['createdAt'],
            'slideCount': item.get('slideCount'),
            'previewCount': item.get('previewCount'),
            'issueCount': item.get('issueCount'),
            'warningCount': item.get('warningCount'),
            'assetCount': item.get('assetCount'),
        }
        for item in artifacts[:8]
    ]
    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['This surface is scoped to product-visible export bundles and workflow linkage. Raw sidecars, nested test suites and filesystem-only noise are intentionally suppressed.']),
        'status': 'live' if artifacts else 'empty',
        'degraded_reason': None if artifacts else 'No persisted export bundles were found in the top-level presentation export registry yet.',
        'artifacts': artifacts[:80],
        'summary': summary,
        'diagnostics': diagnostics,
        'runRegistry': run_registry,
        'recentCaptures': recent_captures,
    }


def _build_lab_evidenceops_payload_uncached(workspace_root: Path) -> dict[str, Any]:
    repository_context = _resolve_evidenceops_repository_context(workspace_root)
    repository_root = repository_context['repository_root']
    repository_backend = str(repository_context['repository_backend'])
    repository_label = str(repository_context['repository_label'])
    repository_display_name = str(repository_context['repository_display_name'])
    repository_tool_name = str(repository_context['repository_tool_name'])
    external_settings = repository_context['external_settings']

    repository_documents = list_evidenceops_repository_entries(
        repository_root,
        repository_backend=repository_backend,
        external_settings=external_settings,
    )
    repository_summary = {
        **summarize_evidenceops_repository_documents(repository_documents),
        'repository_backend': repository_backend,
    }

    repository_snapshot_path = get_phase95_evidenceops_repository_snapshot_path(workspace_root)
    previous_repository_snapshot = load_evidenceops_repository_snapshot(repository_snapshot_path)
    current_repository_snapshot = (
        build_nextcloud_repository_snapshot(settings=external_settings)
        if repository_backend == 'nextcloud_webdav'
        else build_evidenceops_repository_snapshot(repository_root)
    )
    repository_diff = diff_evidenceops_repository_snapshots(previous_repository_snapshot, current_repository_snapshot)

    actions = load_evidenceops_actions(get_phase95_evidenceops_action_store_path(workspace_root))
    action_summary = summarize_evidenceops_actions(actions)
    worklog = load_evidenceops_worklog(get_phase95_evidenceops_worklog_path(workspace_root))
    worklog_summary = summarize_evidenceops_worklog(worklog)
    sorted_worklog = _sorted_worklog_entries(worklog)
    latest_action_window = 10
    open_statuses = {'recommended', 'open', 'pending', 'suggested', 'in_progress'}
    open_actions = [entry for entry in actions if str(entry.get('status') or '').strip().lower() in open_statuses]
    latest_actions = actions[:latest_action_window]
    latest_open_actions = sum(1 for entry in latest_actions if str(entry.get('status') or '').strip().lower() in open_statuses)
    repository_tool_last_call = _latest_worklog_timestamp(sorted_worklog, tool_names={repository_tool_name, 'local_repository_scan'}, operations={'repository_sync', 'repository_search'})
    action_tool_last_call = _latest_worklog_timestamp(sorted_worklog, tool_names={'action_store'}, operations={'action_update'}) or _format_timestamp(action_summary.get('latest_created_at'))
    worklog_tool_last_call = _latest_worklog_timestamp(sorted_worklog)
    action_store_available = bool(actions) or get_phase95_evidenceops_action_store_path(workspace_root).exists()
    worklog_available = bool(worklog) or get_phase95_evidenceops_worklog_path(workspace_root).exists()

    tools = []
    for tool in EVIDENCEOPS_MCP_TOOL_CATALOG:
        surface = str(tool.get('surface') or '').strip()
        if surface == 'repository':
            status = 'active' if repository_documents else 'degraded'
            last_call = repository_tool_last_call
        elif surface == 'actions':
            status = 'active' if action_store_available else 'inactive'
            last_call = action_tool_last_call
        else:
            status = 'active' if worklog_available else 'inactive'
            last_call = worklog_tool_last_call
        tools.append(
            {
                'name': str(tool.get('name') or 'tool'),
                'description': str(tool.get('description') or 'EvidenceOps MCP capability.'),
                'status': status,
                'lastCall': last_call,
            }
        )

    operation_rows = []
    for index, entry in enumerate(sorted_worklog[:12]):
        operation_rows.append(
            {
                'id': str(entry.get('timestamp') or f'op-{index + 1}'),
                'operation': str(entry.get('operation') or entry.get('tool_used') or 'operation'),
                'tool': str(entry.get('tool_used') or 'evidenceops'),
                'status': str(entry.get('status') or 'success'),
                'timestamp': _format_timestamp(entry.get('timestamp')) or _now_iso(),
                'durationMs': round(_safe_float(entry.get('latency_s') or 0.0) * 1000),
                'detail': str(entry.get('summary') or entry.get('detail') or 'Persisted EvidenceOps operation.'),
            }
        )
    if not operation_rows:
        operation_rows = [
            {
                'id': 'repository-scan',
                'operation': 'repository_scan',
                'tool': 'local_repository_scan',
                'status': 'success',
                'timestamp': _now_iso(),
                'durationMs': 12,
                'detail': f"{repository_summary.get('total_documents', 0)} repository document(s) visible.",
            }
        ]

    status_counter: Counter[str] = Counter()
    action_rows = []
    for entry in open_actions:
        normalized_status = str(entry.get('status') or '').strip().lower() or 'open'
        status = 'open' if normalized_status in {'recommended', 'open', 'pending', 'suggested'} else normalized_status
        owner = str(entry.get('owner') or 'Unassigned')
        due_date = str(entry.get('due_date') or '—')
        status_counter[status] += 1
        action_rows.append(
            {
                'id': str(entry.get('id') or ''),
                'title': str(entry.get('description') or entry.get('query') or 'EvidenceOps action'),
                'status': status,
                'owner': owner,
                'target': WORKFLOW_TASK_LABELS.get(str(entry.get('workflow_id') or ''), str(entry.get('tool_used') or 'EvidenceOps')),
                'priority': 'high' if bool(entry.get('needs_review')) else 'medium',
                'dueDate': due_date,
                'rawStatus': str(entry.get('status') or 'recommended'),
                'evidence': entry.get('evidence'),
                'sourceCount': _safe_int(entry.get('source_count') or 0),
                'reviewType': str(entry.get('review_type') or '').strip() or None,
                'approvalStatus': str((entry.get('metadata') or {}).get('approval_status') or '').strip() if isinstance(entry.get('metadata'), dict) else None,
            }
        )

    timeline = [
        {
            'id': operation['id'],
            'label': operation['operation'],
            'detail': operation['detail'],
            'timestamp': operation['timestamp'],
            'status': operation['status'],
        }
        for operation in operation_rows[:8]
    ]

    telemetry = [
        {
            'event': operation['operation'],
            'tool': operation['tool'],
            'status': 'ok' if operation['status'] == 'success' else 'warning',
            'latency': f"{_safe_int(operation['durationMs'])}ms",
            'ts': operation['timestamp'],
        }
        for operation in operation_rows[:12]
    ]

    readiness = [
        {'target': 'Repository', 'status': 'ready' if repository_documents else 'degraded', 'detail': f"{repository_summary.get('total_documents', 0)} documents visible in {repository_display_name}."},
        {'target': 'Action store', 'status': 'ready' if actions else 'degraded', 'detail': f"{action_summary.get('open_actions', 0)} open action(s) persisted."},
        {'target': 'Operations log', 'status': 'ready' if worklog else 'degraded', 'detail': 'Worklog persisted.' if worklog else 'No dedicated EvidenceOps worklog persisted in this workspace yet.'},
    ]

    ownership_summary = [{'owner': owner or 'Unassigned', 'count': count} for owner, count in Counter(str(entry.get('owner') or 'Unassigned') for entry in actions if isinstance(entry, dict)).most_common(6)]
    operation_breakdown = [{'label': label, 'value': value} for label, value in Counter(operation['operation'] for operation in operation_rows).most_common(6)]
    category_breakdown = [{'label': label, 'value': value} for label, value in Counter(str(item.get('category') or 'root') for item in repository_documents if isinstance(item, dict)).most_common(8)]

    recent_searches = []
    for entry in sorted_worklog:
        if str(entry.get('operation') or entry.get('tool_used') or '').strip() != 'repository_search':
            continue
        recent_searches.append(
            {
                'query': str(entry.get('query') or '').strip(),
                'timestamp': _format_timestamp(entry.get('timestamp')),
                'hits': _safe_int(entry.get('source_count') or 0),
            }
        )
        if len(recent_searches) >= 6:
            break

    changed_documents = _safe_int(repository_diff.get('changed_documents_count'))
    new_documents = _safe_int(repository_diff.get('new_documents_count'))
    if not bool(repository_diff.get('has_previous_snapshot')):
        changed_documents = _safe_int(repository_summary.get('total_documents'))
        new_documents = _safe_int(repository_summary.get('total_documents'))

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['EvidenceOps / MCP owns delivery readiness, open action governance and repository-backed search.']),
        'status': 'live' if repository_documents else 'derived',
        'degraded_reason': None if worklog else 'Operations telemetry is partly derived-live because no dedicated EvidenceOps worklog was persisted in this workspace.',
        'summary': {
            'toolsTotal': len(tools),
            'activeTools': sum(1 for tool in tools if tool['status'] == 'active'),
            'openActions': _safe_int(action_summary.get('open_actions')),
            'latestOpenActions': latest_open_actions,
            'latestActionWindow': latest_action_window,
            'operationsCount': len(operation_rows),
            'repositoryDocumentCount': _safe_int(repository_summary.get('total_documents')),
            'repositoryRoot': repository_label,
            'repositoryBackend': repository_backend,
            'repositoryDisplayName': repository_display_name,
            'lastSyncAt': _latest_repository_sync_timestamp(sorted_worklog, previous_repository_snapshot) or _format_timestamp(worklog_summary.get('latest_timestamp')) or _format_timestamp(action_summary.get('latest_created_at')),
            'overdueActions': _safe_int(action_summary.get('overdue_actions')),
            'unassignedActions': _safe_int(action_summary.get('unassigned_open_actions')),
            'inProgressActions': sum(1 for entry in open_actions if str(entry.get('status') or '').strip().lower() == 'in_progress'),
            'needsReviewActions': sum(1 for entry in open_actions if bool(entry.get('needs_review'))),
        },
        'repositoryStats': {
            'changedDocuments': changed_documents,
            'newDocuments': new_documents,
            'categories': _safe_int(repository_summary.get('total_categories')),
            'totalSizeLabel': _bytes_label(_safe_int(repository_summary.get('total_size_bytes') or 0)),
        },
        'searchHints': ['vendor', 'policy', 'access review', 'audit'],
        'tools': tools,
        'actions': action_rows,
        'operations': operation_rows,
        'timeline': timeline,
        'telemetry': telemetry,
        'readiness': readiness,
        'ownershipSummary': ownership_summary,
        'operationBreakdown': operation_breakdown,
        'categoryBreakdown': category_breakdown,
        'statusBreakdown': [{'label': label, 'value': value} for label, value in status_counter.most_common(6)],
        'recentSearches': recent_searches,
    }



def _evidenceops_ui_cache_enabled() -> bool:
    import os

    mode = str(os.environ.get('EVIDENCEOPS_UI_CACHE_MODE') or 'persistent_until_sync').strip().lower()
    return mode not in {'0', 'false', 'off', 'disabled', 'none'}


def _evidenceops_ui_cache_path(workspace_root: Path) -> Path:
    import os

    configured = str(os.environ.get('EVIDENCEOPS_UI_CACHE_PATH') or '').strip()
    if configured:
        return Path(configured)
    return Path(workspace_root) / 'runtime' / 'cache' / 'lab' / 'evidenceops_payload.json'


def _load_evidenceops_ui_cache(workspace_root: Path) -> dict[str, Any] | None:
    cache_path = _evidenceops_ui_cache_path(workspace_root)
    if not cache_path.exists():
        return None

    try:
        payload = json.loads(cache_path.read_text(encoding='utf-8'))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get('ok') is not True:
        return None

    return payload


def _evidenceops_ui_cache_updated_at(cache_path: Path) -> str | None:
    try:
        from datetime import datetime, timezone

        if not cache_path.exists():
            return None
        return datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _annotate_evidenceops_ui_cache_payload(
    payload: dict[str, Any],
    *,
    workspace_root: Path,
    cache_status: str,
) -> dict[str, Any]:
    annotated = dict(payload)
    meta = dict(annotated.get('meta') or {})
    cache_path = _evidenceops_ui_cache_path(workspace_root)
    cache_exists = cache_path.exists()

    meta['evidenceopsCache'] = {
        'mode': 'persistent_until_sync',
        'status': cache_status,
        'path': str(cache_path),
        'exists': cache_exists,
        'updatedAt': _evidenceops_ui_cache_updated_at(cache_path),
        'servedAt': _now_iso(),
        'refreshPolicy': 'manual_sync_or_deploy_warmup',
        'notes': [
            'The UI serves the last known good EvidenceOps snapshot immediately.',
            'Nextcloud/WebDAV rescan is intentionally explicit because repository state changes rarely.',
            'Run /api/lab/evidenceops/sync or the final deploy readiness check to refresh this cache.',
        ],
    }
    annotated['meta'] = meta
    return annotated


def _store_evidenceops_ui_cache(workspace_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    cache_path = _evidenceops_ui_cache_path(workspace_root)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Write once first so the persisted metadata can accurately report exists/updatedAt.
    cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    stored_payload = _annotate_evidenceops_ui_cache_payload(
        payload,
        workspace_root=workspace_root,
        cache_status='stored',
    )

    cache_path.write_text(json.dumps(stored_payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return stored_payload


def invalidate_evidenceops_ui_cache(workspace_root: Path) -> None:
    cache_path = _evidenceops_ui_cache_path(workspace_root)
    try:
        cache_path.unlink()
    except FileNotFoundError:
        return
    except Exception:
        return


def build_lab_evidenceops_payload(
    workspace_root: Path,
    *,
    refresh_cache: bool = False,
    use_cache: bool = True,
) -> dict[str, Any]:
    cache_enabled = _evidenceops_ui_cache_enabled()

    if cache_enabled and use_cache and not refresh_cache:
        cached_payload = _load_evidenceops_ui_cache(workspace_root)
        if cached_payload is not None:
            return _annotate_evidenceops_ui_cache_payload(
                cached_payload,
                workspace_root=workspace_root,
                cache_status='hit',
            )

    payload = _build_lab_evidenceops_payload_uncached(workspace_root)

    if cache_enabled and use_cache:
        return _store_evidenceops_ui_cache(workspace_root, payload)

    return _annotate_evidenceops_ui_cache_payload(
        payload,
        workspace_root=workspace_root,
        cache_status='bypass',
    )

def build_lab_evidenceops_search_payload(workspace_root: Path, *, query: str) -> dict[str, Any]:
    repository_context = _resolve_evidenceops_repository_context(workspace_root)
    repository_root = repository_context['repository_root']
    repository_backend = str(repository_context['repository_backend'])
    repository_label = str(repository_context['repository_label'])
    repository_display_name = str(repository_context['repository_display_name'])
    repository_tool_name = str(repository_context['repository_tool_name'])
    external_settings = repository_context['external_settings']

    results = search_evidenceops_repository_entries(
        repository_root,
        query=query,
        limit=20,
        repository_backend=repository_backend,
        external_settings=external_settings,
    )

    normalized_results = []
    query_tokens = [token for token in str(query or '').lower().split() if token]
    for entry in results:
        relative_path = str(entry.get('relative_path') or '')
        haystack = f"{entry.get('title') or ''} {relative_path}".lower()
        fallback_score = float(sum(1 for token in query_tokens if token in haystack) or 1)
        match_score = _safe_float(entry.get('match_score') or fallback_score)

        normalized_results.append(
            {
                'title': str(entry.get('title') or Path(relative_path).stem or 'Document'),
                'relativePath': relative_path,
                'category': str(entry.get('category') or '').strip() or None,
                'suffix': str(entry.get('suffix') or '').strip() or None,
                'sizeKb': round(_safe_float(entry.get('size_bytes') or 0.0) / 1024, 1),
                'modifiedAt': datetime.fromtimestamp(_safe_float(entry.get('modified_at') or 0.0), tz=timezone.utc).isoformat() if _safe_float(entry.get('modified_at') or 0.0) > 0 else None,
                'matchScore': match_score,
                'source': str(entry.get('source') or ('remote' if repository_backend == 'nextcloud_webdav' else 'local')),
                'repositoryBackend': repository_backend,
            }
        )

    if str(query or '').strip():
        register_evidenceops_entry(
            get_phase95_evidenceops_worklog_path(workspace_root),
            get_phase95_evidenceops_action_store_path(workspace_root),
            entry={
                'timestamp': _now_iso(),
                'operation': 'repository_search',
                'tool_used': repository_tool_name,
                'query': str(query or '').strip(),
                'status': 'success',
                'latency_s': 0.01,
                'summary': f"Repository search returned {len(normalized_results)} result(s) from {repository_display_name}.",
                'source_count': len(normalized_results),
                'document_ids': [],
                'findings': [],
                'action_items': [],
                'recommended_actions': [],
            },
        )

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root),
        'query': str(query or ''),
        'repositoryRoot': repository_label,
        'repositoryBackend': repository_backend,
        'repositoryDisplayName': repository_display_name,
        'results': normalized_results,
    }

def sync_lab_evidenceops_state(workspace_root: Path) -> dict[str, Any]:
    repository_context = _resolve_evidenceops_repository_context(workspace_root)
    repository_root = repository_context['repository_root']
    repository_backend = str(repository_context['repository_backend'])
    repository_display_name = str(repository_context['repository_display_name'])
    repository_tool_name = str(repository_context['repository_tool_name'])
    external_settings = repository_context['external_settings']

    diff_payload = compare_evidenceops_repository_state(
        repository_root,
        snapshot_path=get_phase95_evidenceops_repository_snapshot_path(workspace_root),
        repository_backend=repository_backend,
        external_settings=external_settings,
    )
    current_total_documents = _safe_int(diff_payload.get('current_total_documents') or 0)
    new_documents_count = _safe_int(diff_payload.get('new_documents_count') or 0)
    changed_documents_count = _safe_int(diff_payload.get('changed_documents_count') or 0)
    removed_documents_count = _safe_int(diff_payload.get('removed_documents_count') or 0)
    register_evidenceops_entry(
        get_phase95_evidenceops_worklog_path(workspace_root),
        get_phase95_evidenceops_action_store_path(workspace_root),
        entry={
            'timestamp': _now_iso(),
            'operation': 'repository_sync',
            'tool_used': repository_tool_name,
            'status': 'success',
            'latency_s': 0.02,
            'summary': f"Repository sync captured {current_total_documents} document(s).",
            'detail': f"new={new_documents_count} changed={changed_documents_count} removed={removed_documents_count}",
            'source_count': current_total_documents,
            'document_ids': [],
            'findings': [],
            'action_items': [],
            'recommended_actions': [],
        },
    )
    return {'ok': True, 'diff': diff_payload, 'page': build_lab_evidenceops_payload(workspace_root, refresh_cache=True)}


def update_lab_evidenceops_action(workspace_root: Path, *, action_id: int, status: str | None = None, owner: str | None = None) -> dict[str, Any]:
    resolved_operator = str(owner or 'AI Lab operator').strip() or 'AI Lab operator'
    updated = update_evidenceops_action_item(
        get_phase95_evidenceops_action_store_path(workspace_root),
        action_id=action_id,
        status=status,
        owner=owner,
        approval_status='approved',
        approval_reason='Operator update from the AI Lab EvidenceOps backlog surface.',
        approved_by=resolved_operator,
    )
    if updated is None:
        raise KeyError(f'EvidenceOps action not found: {action_id}')
    register_evidenceops_entry(
        get_phase95_evidenceops_worklog_path(workspace_root),
        get_phase95_evidenceops_action_store_path(workspace_root),
        entry={
            'timestamp': _now_iso(),
            'operation': 'action_update',
            'tool_used': 'action_store',
            'status': 'success',
            'latency_s': 0.01,
            'summary': f"Action {action_id} updated to {str(updated.get('status') or status or 'open')}",
            'detail': str(updated.get('description') or updated.get('evidence') or 'EvidenceOps action updated.'),
            'source_count': _safe_int(updated.get('source_count') or 0),
            'document_ids': list(updated.get('document_ids') or []),
            'findings': [],
            'action_items': [],
            'recommended_actions': [],
        },
    )
    return {'ok': True, 'action': updated, 'page': build_lab_evidenceops_payload(workspace_root, refresh_cache=True)}
