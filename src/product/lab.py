from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.app.product_bootstrap import ProductBootstrap
from src.product.models import ProductWorkflowRequest
from src.product.service import build_product_workflow_catalog, list_product_documents, run_product_workflow
from src.services.evidenceops_repository import list_evidenceops_repository_documents, summarize_evidenceops_repository_documents
from src.services.runtime_controls import build_effective_rag_settings, load_runtime_controls_state
from src.storage.lab_state import (
    append_lab_chat_message,
    append_lab_workflow_run,
    get_lab_chat_session,
    load_lab_chat_sessions,
    load_lab_workflow_runs,
    update_lab_chat_session_runtime,
)
from src.storage.phase7_model_comparison_log import load_model_comparison_log, summarize_model_comparison_log
from src.storage.phase8_eval_diagnosis import build_eval_diagnosis
from src.storage.phase8_eval_store import load_eval_runs, summarize_eval_runs
from src.storage.phase95_evidenceops_action_store import load_evidenceops_actions, summarize_evidenceops_actions
from src.storage.phase95_evidenceops_worklog import load_evidenceops_worklog, summarize_evidenceops_worklog
from src.storage.rag_store import load_rag_document_catalog, load_rag_store
from src.storage.runtime_execution_log import load_runtime_execution_log, summarize_runtime_execution_log
from src.storage.runtime_paths import (
    get_artifact_root,
    get_lab_chat_sessions_path,
    get_lab_workflow_runs_path,
    get_phase6_document_agent_log_path,
    get_phase7_model_comparison_log_path,
    get_phase8_eval_db_path,
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_worklog_path,
    get_product_workflow_history_path,
    get_rag_store_path,
    get_runtime_controls_state_path,
    get_runtime_execution_log_path,
)

LAB_CROSS_SURFACE_NOTES = [
    'Runtime shows operational telemetry, not workflow routing deep dives.',
    'Use Workflow Inspector for route selection, node traces and task-level execution detail.',
    'Use Benchmarks for model-vs-model tradeoffs and preset comparisons.',
    'Use Evals & Diagnosis for regression tracking, pass-rate drift and watchlists.',
    'Use Experiments & Artifacts for capture registry and generated evidence bundles.',
    'Use EvidenceOps / MCP for repository readiness, open actions and delivery operations.',
]

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


def _load_runtime_state(workspace_root: Path) -> dict[str, Any]:
    controls_state = load_runtime_controls_state(get_runtime_controls_state_path(workspace_root)) or {}
    profile = controls_state.get('profile') if isinstance(controls_state.get('profile'), dict) else {}
    rag_store = load_rag_store(get_rag_store_path(workspace_root)) or {}
    runtime_entries = load_runtime_execution_log(get_runtime_execution_log_path(workspace_root))
    runtime_summary = summarize_runtime_execution_log(runtime_entries)
    documents = _workspace_documents(workspace_root)
    document_lookup = _document_lookup(documents)
    chunks = rag_store.get('chunks') if isinstance(rag_store.get('chunks'), list) else []
    doc_list = rag_store.get('documents') if isinstance(rag_store.get('documents'), list) else []

    generation = profile.get('generation') if isinstance(profile.get('generation'), dict) else {}
    retrieval = profile.get('retrieval') if isinstance(profile.get('retrieval'), dict) else {}
    doc_processing = profile.get('docProcessing') if isinstance(profile.get('docProcessing'), dict) else {}

    context_pressure_values = [
        _normalize_ratio_to_unit(entry.get('context_pressure_ratio'))
        for entry in runtime_entries
        if _normalize_ratio_to_unit(entry.get('context_pressure_ratio')) > 0
    ]
    avg_context_pressure = _mean(context_pressure_values)
    latest_entry = runtime_entries[0] if runtime_entries else {}
    latest_context_pressure = _normalize_ratio_to_unit(latest_entry.get('context_pressure_ratio'))

    context_budget_total = 0
    if isinstance(latest_entry.get('context_window'), (int, float)):
        context_budget_total = _safe_int(latest_entry.get('context_window'))
    elif isinstance(generation.get('contextWindow'), (int, float)):
        context_budget_total = _safe_int(generation.get('contextWindow'))
    else:
        context_budget_total = 32768

    context_budget_used = _safe_int(latest_entry.get('context_chars') or 0)
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
        'runtime_summary': runtime_summary,
        'latest_entry': latest_entry,
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


def _build_runtime_core_payload(runtime_state: dict[str, Any]) -> dict[str, Any]:
    profile = runtime_state['profile']
    generation = runtime_state['generation']
    retrieval = runtime_state['retrieval']
    doc_processing = runtime_state['doc_processing']
    runtime_entries = runtime_state['runtime_entries']

    return {
        'generationProvider': str(profile.get('primaryConnectionId') or 'ollama'),
        'generationModel': str(profile.get('primaryModel') or 'unknown'),
        'promptProfile': str(generation.get('promptProfile') or 'neutro'),
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
    for index, entry in enumerate(runtime_entries[:8]):
        source_ids = [str(item) for item in (entry.get('source_document_ids') or []) if str(item or '').strip()]
        rows.append(
            {
                'id': f"trace-{index + 1}",
                'timestamp': str(entry.get('timestamp') or _now_iso()),
                'flow': str(entry.get('flow_type') or 'runtime'),
                'task': str(entry.get('task_type') or entry.get('workflow_id') or 'runtime'),
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
    recent = list(reversed(runtime_entries[:12]))
    for entry in recent:
        timeline.append(
            {
                'label': str(entry.get('task_type') or entry.get('flow_type') or 'runtime'),
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
    summary = runtime_state['runtime_summary']
    notes: list[str] = []
    if _safe_float(summary.get('error_rate')) >= 0.2:
        notes.append(f"Runtime error rate is elevated at {_percent_label(_safe_float(summary.get('error_rate')))} across persisted traces.")
    if _safe_float(summary.get('needs_review_rate')) >= 0.15:
        notes.append(f"Manual review pressure is non-trivial at {_percent_label(_safe_float(summary.get('needs_review_rate')))}.")
    if _safe_float(summary.get('avg_latency_s')) >= 10:
        notes.append(f"Average runtime latency is {_safe_float(summary.get('avg_latency_s')):.1f}s; investigate provider, prompt size or retrieval overhead.")
    if runtime_payload['runtime']['contextPressure'] >= 0.8:
        notes.append('Context pressure is high; this tab shows the pressure signal, while Evals & Diagnosis should confirm whether quality actually regressed.')
    if runtime_payload.get('retrieval_health', {}).get('emptyRetrievalRate', 0) >= 0.1:
        notes.append('Some traces return zero retrieved chunks; inspect retrieval quality here before escalating to Workflow Inspector or Evals.')
    return notes[:4]


def build_lab_runtime_payload(workspace_root: Path) -> dict[str, Any]:
    runtime_state = _load_runtime_state(workspace_root)
    runtime = _build_runtime_core_payload(runtime_state)
    summary = runtime_state['runtime_summary']
    runtime_entries = runtime_state['runtime_entries']

    latency_values = [_safe_float(entry.get('latency_s')) for entry in runtime_entries if _safe_float(entry.get('latency_s')) > 0]
    throughput_24h = 0
    now = datetime.now(timezone.utc)
    for entry in runtime_entries:
        timestamp_text = str(entry.get('timestamp') or '').strip()
        try:
            timestamp = datetime.fromisoformat(timestamp_text.replace('Z', '+00:00'))
        except Exception:
            continue
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if timestamp >= now - timedelta(hours=24):
            throughput_24h += 1

    retrieved_chunk_counts = [_safe_float(entry.get('retrieved_chunks_count')) for entry in runtime_entries]
    retrieval_count = max(len(runtime_entries), 1)
    empty_retrieval_rate = sum(1 for value in retrieved_chunk_counts if value <= 0) / retrieval_count
    context_utilization_values = []
    for entry in runtime_entries:
        budget = _safe_float(entry.get('context_budget_chars') or 0.0)
        used = _safe_float(entry.get('context_chars') or 0.0)
        if budget > 0:
            context_utilization_values.append(min(used / budget, 1.0))

    other_latency = max(
        _safe_float(summary.get('avg_latency_s'))
        - _safe_float(summary.get('avg_retrieval_latency_s'))
        - _safe_float(summary.get('avg_generation_latency_s'))
        - _safe_float(summary.get('avg_prompt_build_latency_s')),
        0.0,
    )

    payload: dict[str, Any] = {
        'ok': True,
        'meta': _runtime_meta(
            workspace_root,
            notes=[
                'This surface is intentionally focused on runtime posture, throughput, retrieval health and recent trace issues.',
                'It does not replace Workflow Inspector, Benchmarks, Evals & Diagnosis, Experiments & Artifacts, or EvidenceOps / MCP.',
            ],
        ),
        'status': 'live' if runtime_entries else 'empty',
        'degraded_reason': None if runtime_entries else 'No persisted runtime_execution_log entries were found in this workspace yet.',
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
            'providerSwitchRate': round(sum(1 for entry in runtime_entries if bool(entry.get('provider_switch_applied'))) / retrieval_count, 3),
            'recentWindowLabel': 'last 24h' if throughput_24h else 'persisted traces',
            'lastTraceAt': _format_timestamp(summary.get('latest_timestamp')),
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
        },
        'latency_breakdown': [
            {'stage': 'Retrieval', 'seconds': round(_safe_float(summary.get('avg_retrieval_latency_s')), 3)},
            {'stage': 'Generation', 'seconds': round(_safe_float(summary.get('avg_generation_latency_s')), 3)},
            {'stage': 'Prompt build', 'seconds': round(_safe_float(summary.get('avg_prompt_build_latency_s')), 3)},
            {'stage': 'Other', 'seconds': round(other_latency, 3)},
        ],
        'provider_breakdown': _build_runtime_provider_breakdown(runtime_entries),
        'failure_modes': _build_runtime_failure_modes(runtime_entries),
        'recent_traces': _build_recent_trace_rows(runtime_entries, runtime_state['document_lookup']),
        'timeline': _build_runtime_timeline(runtime_entries),
        'cross_surface_notes': LAB_CROSS_SURFACE_NOTES,
    }
    payload['watchouts'] = _build_runtime_watchouts(runtime_state, payload)
    return payload


def build_lab_overview_payload(workspace_root: Path) -> dict[str, Any]:
    runtime_payload = build_lab_runtime_payload(workspace_root)
    eval_payload = build_lab_evals_payload(workspace_root)
    evidence_payload = build_lab_evidenceops_payload(workspace_root)
    workflow_history = _read_json(get_product_workflow_history_path(workspace_root), [])
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


def build_lab_chat_payload(workspace_root: Path, session_id: str | None = None) -> dict[str, Any]:
    runtime_payload = build_lab_runtime_payload(workspace_root)
    documents = _workspace_documents(workspace_root)
    document_lookup = _document_lookup(documents)
    sessions = load_lab_chat_sessions(get_lab_chat_sessions_path(workspace_root))
    active_session = None
    if session_id:
        active_session = get_lab_chat_session(get_lab_chat_sessions_path(workspace_root), session_id)
    if active_session is None and sessions:
        active_session = sessions[0]

    default_document_ids = [str(document.get('document_id') or '') for document in documents[:4] if str(document.get('document_id') or '').strip()]
    selected_document_ids = [str(item) for item in (active_session.get('document_ids') if isinstance(active_session, dict) else []) if str(item or '').strip()] or default_document_ids
    selected_documents = [document_lookup[doc_id] for doc_id in selected_document_ids if doc_id in document_lookup]

    messages = []
    if isinstance(active_session, dict):
        for message in active_session.get('messages', []):
            if not isinstance(message, dict):
                continue
            messages.append(
                {
                    'id': str(message.get('id') or ''),
                    'role': str(message.get('role') or 'assistant'),
                    'content': str(message.get('content') or ''),
                    'timestamp': _format_timestamp(message.get('timestamp')),
                    'sources': message.get('sources') if isinstance(message.get('sources'), list) else [],
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
            }
        ]

    sessions_summary = []
    for session in sessions:
        runtime = session.get('runtime') if isinstance(session.get('runtime'), dict) else {}
        session_messages = session.get('messages') if isinstance(session.get('messages'), list) else []
        sessions_summary.append(
            {
                'session_id': str(session.get('session_id') or ''),
                'title': str(session.get('title') or 'AI Lab chat session'),
                'updated_at': _format_timestamp(session.get('updated_at') or session.get('created_at')),
                'message_count': len(session_messages),
                'status': str(session.get('status') or 'active'),
                'document_count': len([item for item in (session.get('document_ids') or []) if str(item or '').strip()]),
                'last_error': str(session.get('last_error') or '').strip() or None,
                'last_model': str(runtime.get('model') or runtime.get('generationModel') or ''),
                'avg_latency_s': _safe_float(runtime.get('avg_latency_s') or 0.0) or None,
                'grounded_messages': sum(1 for item in session_messages if isinstance(item, dict) and isinstance(item.get('sources'), list) and item.get('sources')),
            }
        )

    active_runtime = active_session.get('runtime') if isinstance(active_session, dict) and isinstance(active_session.get('runtime'), dict) else {}
    retrieval_quality = {
        'Strategy': runtime_payload['runtime'].get('retrievalStrategy') or 'hybrid',
        'Top-K': runtime_payload['runtime'].get('topK') or 0,
        'Rerank Pool': runtime_payload['runtime'].get('rerankPoolSize') or 0,
        'Avg Retrieved Chunks': runtime_payload.get('retrieval_health', {}).get('avgRetrievedChunks') or 0,
        'Empty Retrieval Rate': _percent_label(_safe_float(runtime_payload.get('retrieval_health', {}).get('emptyRetrievalRate') or 0.0)),
    }
    session_diagnostics = {
        'Messages': len(messages),
        'Documents': len(selected_documents),
        'Provider': str(active_runtime.get('provider') or runtime_payload['runtime'].get('generationProvider') or 'ollama'),
        'Model': str(active_runtime.get('model') or runtime_payload['runtime'].get('generationModel') or 'unknown'),
        'Avg Latency': f"{_safe_float(active_runtime.get('avg_latency_s') or runtime_payload.get('ops_summary', {}).get('avgLatencyS') or 0.0):.1f}s",
        'Last Tokens': _safe_int(active_runtime.get('total_tokens') or 0),
        'Top-K': runtime_payload['runtime'].get('topK') or 0,
    }
    grounding_overview = {
        'Selected Documents': len(selected_documents),
        'Available Chunks': sum(_safe_int(document.get('chunk_count') or 0) for document in selected_documents),
        'Context Window': f"{_safe_int(runtime_payload['runtime'].get('resolvedContext') or 0):,} tokens",
        'Context Pressure': _percent_label(_normalize_ratio_to_unit(runtime_payload['runtime'].get('contextPressure') or 0.0)),
    }

    session_timeline = []
    if isinstance(active_session, dict):
        for message in (active_session.get('messages') or [])[-8:]:
            if not isinstance(message, dict):
                continue
            session_timeline.append(
                {
                    'id': str(message.get('id') or ''),
                    'title': 'User message' if str(message.get('role') or '') == 'user' else 'Assistant response',
                    'subtitle': str(message.get('content') or '')[:120],
                    'timestamp': _format_timestamp(message.get('timestamp')),
                    'status': 'success',
                }
            )

    meta_notes = [
        'This surface keeps a persisted chat session registry so retrieval experiments do not disappear between refreshes.',
        'Use Runtime & Observability for system posture, and Workflow Inspector for deterministic workflow traces.',
    ]
    if not sessions:
        meta_notes.append('No persisted AI LAB chat sessions were found yet; the first message creates one automatically.')

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=meta_notes),
        'status': 'live' if sessions else 'derived',
        'degraded_reason': None,
        'capabilities': {'can_send': True, 'reason': None},
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


def execute_lab_chat_turn(
    *,
    bootstrap: ProductBootstrap,
    session_id: str,
    content: str,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    normalized_content = str(content or '').strip()
    if not normalized_content:
        raise ValueError('Message content is required.')

    sessions_path = get_lab_chat_sessions_path(bootstrap.workspace_root)
    session = get_lab_chat_session(sessions_path, session_id)
    if session is None:
        raise KeyError(f'Chat session not found: {session_id}')

    current_document_ids = [str(item) for item in (document_ids or session.get('document_ids') or []) if str(item or '').strip()]
    if not current_document_ids:
        current_document_ids = [str(document.get('document_id') or '') for document in _workspace_documents(bootstrap.workspace_root)[:3] if str(document.get('document_id') or '').strip()]
    if not current_document_ids:
        raise ValueError('At least one indexed document is required to execute AI LAB chat.')

    append_lab_chat_message(sessions_path, session_id=session_id, role='user', content=normalized_content)

    provider, model = _workflow_request_defaults(bootstrap.workspace_root)
    request = ProductWorkflowRequest(
        workflow_id='document_review',
        document_ids=current_document_ids,
        input_text=normalized_content,
        provider=provider,
        model=model,
        context_strategy='retrieval',
    )

    try:
        result = run_product_workflow(request)
        highlights = [str(item) for item in (result.highlights or []) if str(item or '').strip()]
        assistant_parts = [str(result.summary or '').strip()]
        if highlights:
            assistant_parts.append('Highlights:\n' + '\n'.join(f'- {item}' for item in highlights[:4]))
        if str(result.recommendation or '').strip():
            assistant_parts.append(f"Recommendation: {result.recommendation}")
        assistant_content = '\n\n'.join(part for part in assistant_parts if part)
        documents = _workspace_documents(bootstrap.workspace_root)
        sources = _result_sources(result, _document_lookup(documents), current_document_ids)
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
            },
        )
        update_lab_chat_session_runtime(
            sessions_path,
            session_id=session_id,
            runtime={
                'provider': provider,
                'model': model,
                'workflow_id': result.workflow_id,
                'avg_latency_s': _safe_float(getattr(result, 'debug_metadata', {}).get('latency_s') if isinstance(getattr(result, 'debug_metadata', None), dict) else 0.0),
                'total_tokens': _safe_float(getattr(result, 'debug_metadata', {}).get('total_tokens') if isinstance(getattr(result, 'debug_metadata', None), dict) else 0.0),
                'warning_count': len(result.warnings or []),
            },
            status='completed',
            last_error=None,
            document_ids=current_document_ids,
        )
        artifact_path = None
        if result.artifacts:
            artifact_path = str(result.artifacts[0].get('path') or result.artifacts[0].get('artifact_path') or '') or None if isinstance(result.artifacts[0], dict) else None
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


def build_lab_workflow_inspector_payload(workspace_root: Path) -> dict[str, Any]:
    task_options = _build_workflow_task_options(workspace_root)
    document_options = _document_options_for_inspector(workspace_root)
    documents = _workspace_documents(workspace_root)
    task_details, recent_cases, mode_counts, review_reason_counter = _build_task_details(workspace_root, task_options, _document_lookup(documents))
    workflow_runs = load_lab_workflow_runs(get_lab_workflow_runs_path(workspace_root))

    confidences = [case['confidence'] for case in recent_cases if _safe_float(case.get('confidence') or 0) > 0]
    summary = {
        'total_cases': len(recent_cases),
        'needs_review': sum(1 for case in recent_cases if bool(case.get('needsReview'))),
        'avg_confidence': round(_mean([_safe_float(value) for value in confidences]), 0) if confidences else 0,
        'review_blockers': sum(review_reason_counter.values()),
        'failed': sum(1 for case in recent_cases if str(case.get('status') or '') == 'error'),
        'task_count': len(task_options),
        'document_count': len(document_options),
        'live_runs': len(workflow_runs),
        'last_run_at': _format_timestamp(workflow_runs[0].get('updated_at')) if workflow_runs else None,
    }
    mode_breakdown = [{'label': label, 'value': value} for label, value in Counter(mode_counts).most_common(5)]
    review_reasons = [{'label': label, 'value': value} for label, value in review_reason_counter.most_common(5)]

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['Workflow Inspector is reserved for task routing, trace detail and explicit workflow execution.']),
        'status': 'live',
        'degraded_reason': None,
        'capabilities': {'can_execute': True, 'reason': None},
        'summary': summary,
        'task_options': task_options,
        'document_options': document_options,
        'selected_task_id': task_options[0]['id'] if task_options else None,
        'task_details': task_details,
        'recent_cases': recent_cases[:16],
        'mode_breakdown': mode_breakdown,
        'review_reasons': review_reasons,
    }


def execute_lab_workflow_inspector_run(
    *,
    bootstrap: ProductBootstrap,
    task_id: str,
    document_id: str | None = None,
    input_text: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    workflow_id = str(task_id or 'document_review').strip() or 'document_review'
    if workflow_id not in WORKFLOW_TASK_LABELS:
        workflow_id = 'document_review'
    document_ids = [str(document_id).strip()] if str(document_id or '').strip() else []
    if not document_ids:
        document_ids = [str(document.get('document_id') or '') for document in _workspace_documents(bootstrap.workspace_root)[:1] if str(document.get('document_id') or '').strip()]
    resolved_provider, resolved_model = _workflow_request_defaults(bootstrap.workspace_root)
    request = ProductWorkflowRequest(
        workflow_id=workflow_id,
        document_ids=document_ids,
        input_text=str(input_text or WORKFLOW_INPUT_HINTS.get(workflow_id) or '').strip(),
        provider=str(provider or resolved_provider),
        model=str(model or resolved_model or '') or None,
        context_strategy='retrieval',
    )
    result = run_product_workflow(request)
    document_lookup = _document_lookup(_workspace_documents(bootstrap.workspace_root))
    run_record = {
        'task_id': workflow_id,
        'workflow_id': workflow_id,
        'status': 'warning' if result.warnings else 'completed',
        'input_text': request.input_text,
        'document_ids': document_ids,
        'document_names': [str(document_lookup.get(document_id, {}).get('name') or document_id) for document_id in document_ids],
        'confidence': _safe_float(getattr(result, 'debug_metadata', {}).get('confidence') if isinstance(getattr(result, 'debug_metadata', None), dict) else 0.0),
        'needs_review': bool(result.warnings),
        'review_reason': '; '.join(str(item) for item in (result.warnings or [])[:2]) or None,
        'provider': request.provider,
        'model': request.model,
        'summary': result.summary,
        'artifact_path': str(result.artifacts[0].get('path') or result.artifacts[0].get('artifact_path') or '') if result.artifacts and isinstance(result.artifacts[0], dict) else None,
        'artifact_label': str(result.artifacts[0].get('label') or result.artifacts[0].get('name') or '') if result.artifacts and isinstance(result.artifacts[0], dict) else None,
        'execution_mode': 'workflow_run',
        'result_title': f"{WORKFLOW_TASK_LABELS.get(workflow_id, workflow_id)} result",
        'source_count': _safe_int(getattr(result.grounding_preview, 'source_block_count', 0) if getattr(result, 'grounding_preview', None) is not None else 0),
        'result': result.model_dump(mode='json') if hasattr(result, 'model_dump') else {},
        'request_payload': request.model_dump(mode='json') if hasattr(request, 'model_dump') else {},
        'response_payload': result.model_dump(mode='json') if hasattr(result, 'model_dump') else {},
    }
    saved = append_lab_workflow_run(get_lab_workflow_runs_path(bootstrap.workspace_root), run_record)
    return {'result': result, 'request': request, 'run_record': saved}


def build_lab_benchmarks_payload(workspace_root: Path) -> dict[str, Any]:
    entries = load_model_comparison_log(get_phase7_model_comparison_log_path(workspace_root))
    summary = summarize_model_comparison_log(entries)
    model_rows: dict[str, dict[str, Any]] = {}
    preset_map: dict[str, dict[str, Any]] = {}
    strategy_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for entry in entries:
        retrieval_strategy = str(entry.get('retrieval_strategy') or 'manual_hybrid')
        strategy_buckets[retrieval_strategy].append(entry)
        preset_name = str(entry.get('prompt_profile') or 'default') or 'default'
        preset = preset_map.setdefault(
            preset_name,
            {'id': preset_name.replace(' ', '-').lower(), 'name': preset_name, 'description': f'{preset_name} benchmark preset derived from recorded comparison runs.', 'metrics': ['use case fit', 'groundedness', 'format adherence', 'latency'], 'models': []},
        )
        for candidate in entry.get('candidate_results') or []:
            if not isinstance(candidate, dict):
                continue
            model_name = str(candidate.get('model_effective') or candidate.get('model_requested') or 'unknown')
            provider_name = str(candidate.get('provider_effective') or candidate.get('provider_requested') or 'unknown')
            key = f'{provider_name}:{model_name}'
            bucket = model_rows.setdefault(
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
                },
            )
            bucket['runs'] += 1
            bucket['useCaseFitValues'].append(_safe_float(candidate.get('use_case_fit_score') or candidate.get('use_case_fit') or candidate.get('format_adherence') or 0.0))
            bucket['groundednessValues'].append(_safe_float(candidate.get('groundedness_score') or candidate.get('groundedness') or 0.0))
            bucket['adherenceValues'].append(_safe_float(candidate.get('format_adherence') or 0.0))
            bucket['latencyValues'].append(_safe_float(candidate.get('latency_s') or 0.0))
            bucket['outputCharsValues'].append(_safe_float(candidate.get('output_chars') or 0.0))
            if model_name not in preset['models']:
                preset['models'].append(model_name)

    models = []
    for row in model_rows.values():
        models.append(
            {
                'id': row['id'],
                'family': row['family'],
                'provider': row['provider'],
                'model': row['model'],
                'profileTag': row['profileTag'],
                'useCaseFit': round(_mean(row['useCaseFitValues']), 3),
                'groundedness': round(_mean(row['groundednessValues']), 3),
                'adherence': round(_mean(row['adherenceValues']), 3),
                'latency': round(_mean(row['latencyValues']), 3),
                'outputChars': round(_mean(row['outputCharsValues']), 0),
                'runtimeBucket': row['runtimeBucket'],
                'quantization': row['quantization'],
                'runs': row['runs'],
            }
        )
    models.sort(key=lambda item: (-item['useCaseFit'], item['latency']))
    if models:
        models[0]['profileTag'] = 'Recommended production'
        fastest = min(models, key=lambda item: item['latency'])
        if fastest['id'] != models[0]['id']:
            fastest['profileTag'] = 'Fastest observed'
        for item in models:
            if item['provider'] not in {'ollama', 'ollama_hosted'} and not item['profileTag']:
                item['profileTag'] = 'External reference'

    provider_summary = []
    for provider_name, provider_models in defaultdict(list, {item['provider']: [] for item in models}).items():
        pass
    grouped_providers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for model in models:
        grouped_providers[model['provider']].append(model)
    for provider_name, provider_models in grouped_providers.items():
        best_model = max(provider_models, key=lambda item: item['useCaseFit'])
        provider_summary.append(
            {
                'provider': provider_name,
                'models': len(provider_models),
                'bestFit': round(best_model['useCaseFit'] * 100),
                'avgLatency': round(_mean([_safe_float(item['latency']) for item in provider_models]), 2),
                'bestModel': best_model['model'],
            }
        )
    provider_summary.sort(key=lambda item: (-item['bestFit'], item['avgLatency']))

    retrieval_observations = []
    for strategy, strategy_entries in strategy_buckets.items():
        candidate_rows = [candidate for entry in strategy_entries for candidate in (entry.get('candidate_results') or []) if isinstance(candidate, dict)]
        retrieval_observations.append(
            {
                'strategy': strategy,
                'outputDiscipline': round(_mean([_safe_float(candidate.get('format_adherence') or 0.0) for candidate in candidate_rows]), 3),
                'contextRetention': round(min(_mean([_safe_float(candidate.get('used_chunks') or 0.0) / max((_safe_float(candidate.get('used_chunks') or 0.0) + _safe_float(candidate.get('dropped_chunks') or 0.0)), 1.0) for candidate in candidate_rows]), 1.0), 3) if candidate_rows else 0.0,
                'composite': round(_mean([_safe_float(candidate.get('format_adherence') or 0.0) * 0.5 + _safe_float(candidate.get('groundedness_score') or candidate.get('groundedness') or 0.0) * 0.5 for candidate in candidate_rows]), 3),
                'latency': round(_mean([_safe_float(candidate.get('latency_s') or 0.0) for candidate in candidate_rows]), 3),
                'coverage': round(_mean([_safe_float(candidate.get('context_preview_chars') or 0.0) for candidate in candidate_rows]), 0),
                'description': f'{strategy.replace("_", " ")} derived from persisted phase7 comparison runs.',
            }
        )
    retrieval_observations.sort(key=lambda item: (-item['composite'], item['latency']))

    leaderboard_highlights = []
    if models:
        leaderboard_highlights.append({'label': 'Best overall fit', 'model': models[0]['model'], 'detail': f"{round(models[0]['useCaseFit'] * 100)}% use-case fit"})
        fastest = min(models, key=lambda item: item['latency'])
        leaderboard_highlights.append({'label': 'Fastest observed', 'model': fastest['model'], 'detail': f"{fastest['latency']:.2f}s average latency"})
        best_grounded = max(models, key=lambda item: item['groundedness'])
        leaderboard_highlights.append({'label': 'Best groundedness', 'model': best_grounded['model'], 'detail': f"{round(best_grounded['groundedness'] * 100)}% groundedness"})

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['Benchmarks owns model-vs-model tradeoff evaluation. Runtime only links to provider posture, not benchmark scoring.']),
        'status': 'live' if models else 'empty',
        'degraded_reason': None if models else 'No phase7 model comparison log has been recorded yet.',
        'summary': {
            'modelCount': len(models),
            'bestGroundedness': round(max((item['groundedness'] for item in models), default=0.0), 3),
            'fastestLatency': round(min((item['latency'] for item in models), default=0.0), 3),
            'bestModel': models[0]['model'] if models else None,
            'totalRuns': _safe_int(summary.get('total_runs')),
        },
        'models': models,
        'presets': list(preset_map.values()),
        'providerSummary': provider_summary,
        'leaderboardHighlights': leaderboard_highlights,
        'retrievalObservations': retrieval_observations,
    }


def build_lab_evals_payload(workspace_root: Path) -> dict[str, Any]:
    entries = load_eval_runs(get_phase8_eval_db_path(workspace_root))
    summary = summarize_eval_runs(entries)
    diagnosis = build_eval_diagnosis(entries)

    suites_map: dict[str, dict[str, Any]] = {}
    provider_map: dict[str, dict[str, Any]] = {}
    task_map: dict[str, dict[str, Any]] = {}
    cases = []
    watchlist = []

    for entry in entries:
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
            'id': str(entry.get('id') or f'{suite_name}-{task_type}-{len(cases) + 1}'),
            'task': task_type,
            'suite': suite_name,
            'verdict': verdict,
            'score': round(score_ratio, 3),
            'needsReview': needs_review,
            'model': str(entry.get('model') or 'unknown'),
            'latency': round(_safe_float(entry.get('latency_s') or 0.0), 3),
            'timestamp': _format_timestamp(entry.get('created_at')) or _now_iso(),
            'errorDetail': '; '.join(str(reason) for reason in (entry.get('reasons') or [])[:3]) or None,
        }
        cases.append(case_payload)
        if verdict in {'WARN', 'FAIL'} or needs_review:
            watchlist.append(case_payload)

        suite_bucket = suites_map.setdefault(suite_name, {'name': suite_name, 'total': 0, 'pass': 0, 'warn': 0, 'fail': 0, 'needsReview': 0, 'lastRun': _format_timestamp(entry.get('created_at')) or _now_iso()})
        suite_bucket['total'] += 1
        suite_bucket[verdict.lower()] += 1
        suite_bucket['needsReview'] += 1 if needs_review else 0
        suite_bucket['lastRun'] = max(str(suite_bucket['lastRun']), str(entry.get('created_at') or suite_bucket['lastRun']))

        provider_name = str(entry.get('provider') or 'unknown')
        provider_bucket = provider_map.setdefault(provider_name, {'provider': provider_name, 'total': 0, 'failures': 0, 'passes': 0})
        provider_bucket['total'] += 1
        provider_bucket['failures'] += 1 if verdict == 'FAIL' else 0
        provider_bucket['passes'] += 1 if verdict == 'PASS' else 0

        task_bucket = task_map.setdefault(task_type, {'task': task_type, 'total': 0, 'passes': 0, 'score_values': []})
        task_bucket['total'] += 1
        task_bucket['passes'] += 1 if verdict == 'PASS' else 0
        task_bucket['score_values'].append(score_ratio)

    suites = list(suites_map.values())
    suites.sort(key=lambda item: item['name'])
    provider_breakdown = []
    for bucket in provider_map.values():
        provider_breakdown.append({'provider': bucket['provider'], 'total': bucket['total'], 'failures': bucket['failures'], 'passRate': round((bucket['passes'] / max(bucket['total'], 1)) * 100)})
    provider_breakdown.sort(key=lambda item: (-item['total'], item['provider']))

    task_breakdown = []
    for bucket in task_map.values():
        task_breakdown.append({'task': bucket['task'], 'total': bucket['total'], 'passRate': round((bucket['passes'] / max(bucket['total'], 1)) * 100), 'avgScore': round(_mean(bucket['score_values']), 3)})
    task_breakdown.sort(key=lambda item: (-item['total'], item['task']))

    pass_rate = round((_safe_int(summary.get('pass')) / max(_safe_int(summary.get('total_runs')), 1)) * 100) if _safe_int(summary.get('total_runs')) else 0
    totals = {
        'pass': _safe_int(summary.get('pass')),
        'warn': _safe_int(summary.get('warn')),
        'fail': _safe_int(summary.get('fail')),
        'review': _safe_int(summary.get('needs_review')),
        'total': _safe_int(summary.get('total_runs')),
    }
    global_recommendation = diagnosis.get('decision_summary', {}).get('global_recommendation') if isinstance(diagnosis, dict) else None
    diagnosis_payload = dict(diagnosis) if isinstance(diagnosis, dict) else {}
    diagnosis_payload['globalRecommendation'] = str(global_recommendation or '').replace('_', ' ') or 'Review the worst-performing task slices and rerun the impacted eval suites.'

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['Evals & Diagnosis is the source of truth for regression posture; runtime only surfaces coarse operational symptoms.']),
        'status': 'live' if entries else 'empty',
        'degraded_reason': None if entries else 'No phase8 eval runs were found in this workspace yet.',
        'passRate': pass_rate,
        'totals': totals,
        'suites': suites,
        'cases': cases[:80],
        'providerBreakdown': provider_breakdown,
        'taskBreakdown': task_breakdown,
        'watchlist': watchlist[:12],
        'diagnosis': diagnosis_payload,
    }


def _artifact_inventory(workspace_root: Path) -> list[dict[str, Any]]:
    artifact_root = get_artifact_root(workspace_root)
    if not artifact_root.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(artifact_root.rglob('*')):
        if not path.is_file():
            continue
        if path.name.startswith('.'):
            continue
        relative = path.relative_to(artifact_root)
        suffix = path.suffix.lower()
        if suffix not in {'.json', '.pptx', '.png', '.md'}:
            continue
        status = 'ready'
        if 'error' in path.name.lower():
            status = 'error'
        artifact_type = 'report'
        category = relative.parts[0] if len(relative.parts) > 1 else 'root'
        if 'benchmark' in path.name.lower():
            artifact_type = 'benchmark'
        elif 'eval' in path.name.lower() or 'diagnosis' in path.name.lower():
            artifact_type = 'eval'
        elif 'ocr' in path.name.lower():
            artifact_type = 'ocr_diagnostic'
        elif 'embedding' in path.name.lower():
            artifact_type = 'embedding_experiment'
        elif 'run' in path.name.lower() or 'preview' in path.name.lower() or suffix == '.pptx':
            artifact_type = 'extraction'
        items.append(
            {
                'id': str(relative).replace('/', '__'),
                'name': path.name,
                'type': artifact_type,
                'category': category,
                'version': relative.parts[1] if len(relative.parts) > 1 else 'workspace',
                'createdAt': datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
                'size': _bytes_label(path.stat().st_size),
                'status': status,
                'description': f'Captured from {relative.parent.as_posix() or "artifact root"}.',
                'path': str(path),
            }
        )
    items.sort(key=lambda item: str(item['createdAt']), reverse=True)
    return items


def build_lab_artifacts_payload(workspace_root: Path) -> dict[str, Any]:
    artifacts = _artifact_inventory(workspace_root)
    chat_sessions = load_lab_chat_sessions(get_lab_chat_sessions_path(workspace_root))
    workflow_runs = load_lab_workflow_runs(get_lab_workflow_runs_path(workspace_root))
    diagnostics = [
        {'label': 'Artifact root', 'detail': str(get_artifact_root(workspace_root)), 'status': 'connected', 'health': 'healthy'},
        {'label': 'Runtime linked runs', 'detail': f'{len(workflow_runs)} persisted workflow run(s) linked into AI LAB.', 'status': 'linked', 'health': 'healthy' if workflow_runs else 'neutral'},
        {'label': 'Chat capture registry', 'detail': f'{len(chat_sessions)} persisted chat session(s) are visible to the artifact surface.', 'status': 'linked', 'health': 'healthy' if chat_sessions else 'neutral'},
    ]
    summary = {
        'totalArtifacts': len(artifacts),
        'readyArtifacts': sum(1 for item in artifacts if item['status'] == 'ready'),
        'errorArtifacts': sum(1 for item in artifacts if item['status'] == 'error'),
        'chatSessions': len(chat_sessions),
        'workflowRuns': len(workflow_runs),
    }
    run_registry = {
        'chatSessions': len(chat_sessions),
        'workflowRuns': len(workflow_runs),
        'latestChatSession': str(chat_sessions[0].get('session_id') or '') if chat_sessions else None,
        'latestWorkflowRun': str(workflow_runs[0].get('run_id') or '') if workflow_runs else None,
        'latestWorkflowArtifact': str(workflow_runs[0].get('artifact_path') or '') if workflow_runs and str(workflow_runs[0].get('artifact_path') or '').strip() else None,
    }
    recent_captures = [
        {
            'id': item['id'],
            'label': item['name'],
            'category': item['category'],
            'status': item['status'],
            'createdAt': item['createdAt'],
            'artifactPath': item.get('path'),
        }
        for item in artifacts[:8]
    ]
    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['Artifacts stores technical evidence. It complements, but does not replace, Benchmarks, Evals or Workflow Inspector.']),
        'status': 'live' if artifacts else 'empty',
        'degraded_reason': None if artifacts else 'Artifact inventory is empty in this workspace.',
        'artifacts': artifacts[:80],
        'summary': summary,
        'diagnostics': diagnostics,
        'runRegistry': run_registry,
        'recentCaptures': recent_captures,
    }


def build_lab_evidenceops_payload(workspace_root: Path) -> dict[str, Any]:
    repository_root = workspace_root / 'data' / 'corpus_revisado'
    repository_documents = list_evidenceops_repository_documents(repository_root)
    repository_summary = summarize_evidenceops_repository_documents(repository_documents)
    actions = load_evidenceops_actions(get_phase95_evidenceops_action_store_path(workspace_root))
    action_summary = summarize_evidenceops_actions(actions)
    worklog = load_evidenceops_worklog(get_phase95_evidenceops_worklog_path(workspace_root))
    worklog_summary = summarize_evidenceops_worklog(worklog)

    tools = [
        {'name': 'local_repository_scan', 'description': 'Scans the grounded evidence repository for searchable documents.', 'status': 'active', 'lastCall': _format_timestamp(action_summary.get('latest_created_at'))},
        {'name': 'action_store', 'description': 'Persists EvidenceOps action recommendations and operator follow-up.', 'status': 'active' if actions else 'inactive', 'lastCall': _format_timestamp(action_summary.get('latest_created_at'))},
        {'name': 'worklog_registry', 'description': 'Tracks EvidenceOps operation telemetry and readiness.', 'status': 'active' if worklog else 'degraded', 'lastCall': _format_timestamp(worklog_summary.get('latest_timestamp'))},
    ]
    operation_rows = []
    for index, entry in enumerate(worklog[:10]):
        if not isinstance(entry, dict):
            continue
        operation_rows.append(
            {
                'id': f'op-{index + 1}',
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
                'timestamp': _format_timestamp(action_summary.get('latest_created_at')) or _now_iso(),
                'durationMs': 12,
                'detail': f"{repository_summary.get('total_documents', 0)} repository document(s) visible.",
            }
        ]

    action_rows = []
    for entry in actions[:20]:
        action_rows.append(
            {
                'id': str(entry.get('id') or ''),
                'title': str(entry.get('description') or entry.get('query') or 'EvidenceOps action'),
                'status': 'open' if str(entry.get('status') or '').strip() in {'recommended', 'open', 'pending'} else str(entry.get('status') or 'open'),
                'owner': str(entry.get('owner') or 'Unassigned'),
                'target': WORKFLOW_TASK_LABELS.get(str(entry.get('workflow_id') or ''), str(entry.get('tool_used') or 'EvidenceOps')),
                'priority': 'high' if bool(entry.get('needs_review')) else 'medium',
                'dueDate': str(entry.get('due_date') or '—'),
                'rawStatus': str(entry.get('status') or 'recommended'),
                'evidence': entry.get('evidence'),
                'sourceCount': _safe_int(entry.get('source_count') or 0),
            }
        )

    timeline = []
    for operation in operation_rows[:8]:
        timeline.append(
            {
                'id': operation['id'],
                'title': operation['operation'],
                'subtitle': operation['detail'],
                'timestamp': operation['timestamp'],
                'status': operation['status'],
            }
        )

    telemetry = []
    for operation in operation_rows[:12]:
        telemetry.append(
            {
                'event': operation['operation'],
                'tool': operation['tool'],
                'status': 'ok' if operation['status'] == 'success' else 'warning',
                'latency': f"{_safe_int(operation['durationMs'])}ms",
                'ts': operation['timestamp'],
            }
        )

    readiness = [
        {'target': 'Repository', 'status': 'ready' if repository_documents else 'degraded', 'detail': f"{repository_summary.get('total_documents', 0)} documents visible under corpus_revisado."},
        {'target': 'Action store', 'status': 'ready' if actions else 'degraded', 'detail': f"{action_summary.get('open_actions', 0)} open action(s) persisted."},
        {'target': 'Operations log', 'status': 'ready' if worklog else 'degraded', 'detail': 'Worklog persisted.' if worklog else 'No dedicated EvidenceOps worklog persisted in this workspace yet.'},
    ]

    ownership_summary = [{'owner': owner or 'Unassigned', 'count': count} for owner, count in Counter(str(entry.get('owner') or 'Unassigned') for entry in actions if isinstance(entry, dict)).most_common(6)]
    operation_breakdown = [{'label': label, 'value': value} for label, value in Counter(operation['operation'] for operation in operation_rows).most_common(6)]

    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root, notes=['EvidenceOps / MCP owns delivery readiness, open action governance and repository-backed search.']),
        'status': 'live' if repository_documents else 'derived',
        'degraded_reason': None if worklog else 'Operations telemetry is partly derived-live because no dedicated EvidenceOps worklog was persisted in this workspace.',
        'summary': {
            'toolsTotal': len(tools),
            'activeTools': sum(1 for tool in tools if tool['status'] == 'active'),
            'openActions': _safe_int(action_summary.get('open_actions')),
            'operationsCount': len(operation_rows),
            'repositoryDocumentCount': _safe_int(repository_summary.get('total_documents')),
            'repositoryRoot': str(repository_root),
            'lastSyncAt': _format_timestamp(action_summary.get('latest_created_at') or worklog_summary.get('latest_timestamp')),
        },
        'repositoryStats': {'changedDocuments': _safe_int(repository_summary.get('total_documents')), 'newDocuments': _safe_int(repository_summary.get('total_documents'))},
        'searchHints': ['vendor', 'policy', 'access review', 'candidate'],
        'tools': tools,
        'actions': action_rows,
        'operations': operation_rows,
        'timeline': timeline,
        'telemetry': telemetry,
        'readiness': readiness,
        'ownershipSummary': ownership_summary,
        'operationBreakdown': operation_breakdown,
    }


def build_lab_evidenceops_search_payload(workspace_root: Path, *, query: str) -> dict[str, Any]:
    repository_root = workspace_root / 'data' / 'corpus_revisado'
    results = list_evidenceops_repository_documents(repository_root, query=query, limit=20)
    normalized_results = []
    query_tokens = [token for token in str(query or '').lower().split() if token]
    for entry in results:
        relative_path = str(entry.get('relative_path') or '')
        haystack = f"{entry.get('title') or ''} {relative_path}".lower()
        match_score = float(sum(1 for token in query_tokens if token in haystack) or 1)
        normalized_results.append(
            {
                'title': str(entry.get('title') or Path(relative_path).stem or 'Document'),
                'relativePath': relative_path,
                'category': str(entry.get('category') or '').strip() or None,
                'suffix': str(entry.get('suffix') or '').strip() or None,
                'sizeKb': round(_safe_float(entry.get('size_bytes') or 0.0) / 1024, 1),
                'modifiedAt': datetime.fromtimestamp(_safe_float(entry.get('modified_at') or 0.0), tz=timezone.utc).isoformat() if _safe_float(entry.get('modified_at') or 0.0) > 0 else None,
                'matchScore': match_score,
            }
        )
    return {
        'ok': True,
        'meta': _runtime_meta(workspace_root),
        'query': str(query or ''),
        'repositoryRoot': str(repository_root),
        'results': normalized_results,
    }
