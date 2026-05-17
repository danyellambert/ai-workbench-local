from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.evidenceops_local_ops import register_evidenceops_entry
from src.storage.phase95_evidenceops_action_store import load_evidenceops_actions
from src.storage.phase95_evidenceops_worklog import load_evidenceops_worklog
from src.storage.product_telemetry import load_product_telemetry_runs
from src.storage.runtime_paths import (
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_worklog_path,
    get_product_telemetry_path,
)


def _delivery_recommended_actions(deliveries: list[dict]) -> list[str]:
    actions: list[str] = []
    for item in deliveries:
        target = str(item.get('target') or '').strip()
        status = str(item.get('status') or '').strip()
        message = str(item.get('message') or item.get('summary') or '').strip()
        if not target:
            continue
        actions.append(f"Review delivery target {target} ({status or 'planned'}) and confirm publication state. {message}".strip())
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description='Backfill EvidenceOps worklog and action store from persisted product telemetry.')
    parser.add_argument('--workspace-root', default=str(ROOT_DIR))
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).resolve()
    telemetry_runs = load_product_telemetry_runs(get_product_telemetry_path(workspace_root))
    if args.limit and args.limit > 0:
        telemetry_runs = telemetry_runs[: args.limit]

    worklog_path = get_phase95_evidenceops_worklog_path(workspace_root)
    store_path = get_phase95_evidenceops_action_store_path(workspace_root)

    registered = 0
    for run in telemetry_runs:
        summary = run.get('summary') if isinstance(run.get('summary'), dict) else {}
        lineage = run.get('lineage') if isinstance(run.get('lineage'), dict) else {}
        actions = lineage.get('evidenceops_actions') if isinstance(lineage.get('evidenceops_actions'), list) else []
        deliveries = lineage.get('deliveries') if isinstance(lineage.get('deliveries'), list) else []
        warnings = summary.get('warnings') if isinstance(summary.get('warnings'), list) else []
        recommended_actions = [str(item).strip() for item in warnings if str(item).strip()]
        recommended_actions.extend(_delivery_recommended_actions([item for item in deliveries if isinstance(item, dict)]))
        if not actions and not recommended_actions:
            continue
        entry = {
            'timestamp': str(run.get('completed_at') or run.get('started_at') or ''),
            'task_type': str(run.get('workflow_id') or ''),
            'review_type': 'product_runtime_backfill',
            'tool_used': str(run.get('workflow_id') or 'product_workflow'),
            'query': str(((run.get('request') or {}) if isinstance(run.get('request'), dict) else {}).get('input_text') or ''),
            'confidence': None,
            'needs_review': bool(run.get('needs_review')),
            'needs_review_reason': str(run.get('review_reason') or '').strip() or None,
            'source_count': int((((run.get('runtime') or {}) if isinstance(run.get('runtime'), dict) else {}).get('retrieved_chunks_count') or 0)),
            'document_ids': list((((run.get('request') or {}) if isinstance(run.get('request'), dict) else {}).get('document_ids') or [])),
            'workflow_id': str(run.get('workflow_id') or ''),
            'execution_strategy_used': str((((run.get('routing') or {}) if isinstance(run.get('routing'), dict) else {}).get('execution_strategy_used') or '')),
            'summary': str(summary.get('summary') or 'Backfilled from product telemetry.'),
            'detail': str(summary.get('recommendation') or summary.get('summary') or ''),
            'operation': 'product_runtime_backfill',
            'status': 'success',
            'latency_s': 0.0,
            'findings': [],
            'action_items': actions,
            'recommended_actions': recommended_actions,
        }
        register_evidenceops_entry(worklog_path, store_path, entry=entry)
        registered += 1

    print({
        'workspace_root': str(workspace_root),
        'telemetry_runs': len(telemetry_runs),
        'registered_worklog_entries': registered,
        'worklog_total_after': len(load_evidenceops_worklog(worklog_path)),
        'actions_total_after': len(load_evidenceops_actions(store_path)),
        'worklog_path': str(worklog_path),
        'action_store_path': str(store_path),
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
