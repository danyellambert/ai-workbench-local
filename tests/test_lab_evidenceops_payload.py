from __future__ import annotations

from pathlib import Path

from src.product.lab import build_lab_evidenceops_payload, sync_lab_evidenceops_state
from src.services.evidenceops_repository import build_evidenceops_repository_snapshot
from src.storage.phase95_evidenceops_action_store import (
    append_evidenceops_actions_from_worklog_entry,
    load_evidenceops_actions,
)
from src.storage.phase95_evidenceops_repository_snapshot import save_evidenceops_repository_snapshot
from src.storage.phase95_evidenceops_worklog import append_evidenceops_worklog_entry, load_evidenceops_worklog
from src.storage.runtime_paths import (
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_repository_snapshot_path,
    get_phase95_evidenceops_worklog_path,
)


def _make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / 'workspace'
    repository_root = workspace / 'data' / 'corpus_revisado' / 'audit'
    repository_root.mkdir(parents=True)
    (repository_root / 'evidence-log.md').write_text('Evidence log', encoding='utf-8')
    (repository_root / 'vendor-policy.md').write_text('Vendor policy', encoding='utf-8')
    return workspace


def test_build_lab_evidenceops_payload_uses_full_action_store_latest_worklog_and_snapshot_diff(tmp_path: Path) -> None:
    workspace = _make_workspace(tmp_path)
    repository_root = workspace / 'data' / 'corpus_revisado'
    snapshot_path = get_phase95_evidenceops_repository_snapshot_path(workspace)
    worklog_path = get_phase95_evidenceops_worklog_path(workspace)
    action_store_path = get_phase95_evidenceops_action_store_path(workspace)

    save_evidenceops_repository_snapshot(snapshot_path, build_evidenceops_repository_snapshot(repository_root))

    entry_with_many_actions = {
        'timestamp': '2099-01-01T00:00:00+00:00',
        'tool_used': 'action_plan_evidence_review',
        'workflow_id': 'action_plan_evidence_review',
        'review_type': 'document_agent',
        'query': 'Extract actions',
        'status': 'success',
        'latency_s': 0.01,
        'summary': 'Created recommendation set.',
        'source_count': 2,
        'document_ids': ['doc-1'],
        'findings': [],
        'action_items': [],
        'recommended_actions': [f'Action {index}' for index in range(30)],
    }
    append_evidenceops_worklog_entry(worklog_path, entry_with_many_actions)
    append_evidenceops_actions_from_worklog_entry(action_store_path, entry_with_many_actions)

    append_evidenceops_worklog_entry(
        worklog_path,
        {
            'timestamp': '2099-01-02T00:00:00+00:00',
            'operation': 'repository_search',
            'tool_used': 'local_repository_scan',
            'status': 'success',
            'latency_s': 0.02,
            'summary': 'Search returned 1 result.',
            'query': 'vendor',
            'source_count': 1,
            'document_ids': [],
            'findings': [],
            'action_items': [],
            'recommended_actions': [],
        },
    )
    append_evidenceops_worklog_entry(
        worklog_path,
        {
            'timestamp': '2099-01-03T00:00:00+00:00',
            'operation': 'repository_sync',
            'tool_used': 'local_repository_scan',
            'status': 'success',
            'latency_s': 0.02,
            'summary': 'Repository sync captured 2 document(s).',
            'detail': 'new=0 changed=0 removed=0',
            'source_count': 2,
            'document_ids': [],
            'findings': [],
            'action_items': [],
            'recommended_actions': [],
        },
    )

    payload = build_lab_evidenceops_payload(workspace)

    assert payload['summary']['openActions'] == 30
    assert payload['summary']['unassignedActions'] == 30
    assert payload['summary']['lastSyncAt'] == '2099-01-03T00:00:00+00:00'
    assert len(payload['actions']) == 30
    assert payload['operations'][0]['operation'] == 'repository_sync'
    assert payload['telemetry'][0]['event'] == 'repository_sync'
    assert payload['repositoryStats']['changedDocuments'] == 0
    assert payload['repositoryStats']['newDocuments'] == 0
    assert payload['recentSearches'][0]['query'] == 'vendor'
    assert 'candidate' not in payload['searchHints']


def test_sync_lab_evidenceops_state_writes_numeric_repository_counts_to_worklog(tmp_path: Path) -> None:
    workspace = _make_workspace(tmp_path)
    repository_root = workspace / 'data' / 'corpus_revisado'
    snapshot_path = get_phase95_evidenceops_repository_snapshot_path(workspace)
    worklog_path = get_phase95_evidenceops_worklog_path(workspace)

    save_evidenceops_repository_snapshot(snapshot_path, build_evidenceops_repository_snapshot(repository_root))

    response = sync_lab_evidenceops_state(workspace)
    latest_entry = load_evidenceops_worklog(worklog_path)[-1]

    assert response['diff']['current_total_documents'] == 2
    assert latest_entry['summary'] == 'Repository sync captured 2 document(s).'
    assert latest_entry['detail'] == 'new=0 changed=0 removed=0'
    assert latest_entry['source_count'] == 2
    assert load_evidenceops_actions(get_phase95_evidenceops_action_store_path(workspace)) == []
