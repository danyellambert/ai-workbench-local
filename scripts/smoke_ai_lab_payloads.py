from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LAB_MODULE_PATH = REPO_ROOT / 'src' / 'product' / 'lab.py'


def load_lab_module():
    spec = importlib.util.spec_from_file_location('product_lab_smoke', LAB_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Could not load lab module from {LAB_MODULE_PATH}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _slugify(value: str) -> str:
    cleaned = ''.join(character.lower() if character.isalnum() else '-' for character in str(value or '').strip())
    while '--' in cleaned:
        cleaned = cleaned.replace('--', '-')
    return cleaned.strip('-') or 'item'


def ensure_output_dir(output_dir: Path | None) -> Path | None:
    if output_dir is None:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def assert_keys(name: str, payload: dict[str, Any], required: list[str]) -> None:
    missing = [key for key in required if key not in payload]
    if missing:
        raise AssertionError(f'{name} payload missing required keys: {missing}')


def summarize(payload: dict[str, Any]) -> str:
    if 'kpis' in payload:
        return f"{len(payload.get('kpis', []))} kpis / {len(payload.get('alerts', []))} alerts"
    if 'generation_rows' in payload:
        return f"{len(payload.get('generation_rows', []))} generation rows / {len(payload.get('diagnostics_rows', []))} diagnostics rows"
    if 'messages' in payload:
        return f"{len(payload.get('messages', []))} messages / {len(payload.get('selected_documents', []))} documents"
    if 'task_options' in payload:
        return f"{len(payload.get('task_options', []))} tasks / {len(payload.get('recent_cases', []))} recent cases"
    if 'models' in payload:
        return f"{len(payload.get('models', []))} models / {len(payload.get('presets', []))} presets"
    if 'suites' in payload:
        return f"{len(payload.get('suites', []))} suites / {len(payload.get('cases', []))} cases"
    if 'artifacts' in payload:
        return f"{len(payload.get('artifacts', []))} artifacts / {len(payload.get('diagnostics', []))} diagnostics"
    if 'tools' in payload:
        return f"{len(payload.get('tools', []))} tools / {len(payload.get('actions', []))} actions / {len(payload.get('operations', []))} operations"
    if 'results' in payload:
        return f"{len(payload.get('results', []))} search results"
    return json.dumps(payload)[:120]


def _write_summary(output_dir: Path | None, summary: dict[str, Any]) -> None:
    if output_dir is None:
        return
    write_json(output_dir / 'summary.json', summary)
    lines = [
        '# AI LAB validation summary',
        '',
        f"Generated at: {summary.get('generated_at')}",
        f"Repo root: {summary.get('repo_root')}",
        '',
        '## Checks',
        '',
    ]
    for check in summary.get('checks', []):
        lines.append(f"- {check.get('name')}: {check.get('status')} — {check.get('summary')}")
    if summary.get('errors'):
        lines.extend(['', '## Errors', ''])
        for error in summary['errors']:
            lines.append(f"- {error}")
    write_text(output_dir / 'summary.md', '\n'.join(lines) + '\n')


def _record_check(summary: dict[str, Any], *, name: str, status: str, detail: dict[str, Any], errors: list[str] | None = None) -> None:
    checks = summary.setdefault('checks', [])
    checks.append(
        {
            'name': name,
            'status': status,
            'summary': detail.get('summary'),
            'detail': detail,
        }
    )
    if errors:
        summary.setdefault('errors', []).extend(errors)


def run_builder_smoke(output_dir: Path | None = None) -> tuple[int, dict[str, Any]]:
    module = load_lab_module()
    builders: list[tuple[str, Callable[..., dict[str, Any]], list[str], tuple[Any, ...]]] = [
        ('overview', module.build_lab_overview_payload, ['ok', 'meta', 'runtime', 'kpis', 'alerts', 'workflow_mix'], (REPO_ROOT,)),
        ('runtime', module.build_lab_runtime_payload, ['ok', 'meta', 'runtime', 'generation_rows', 'retrieval_rows', 'vector_rows', 'diagnostics_rows'], (REPO_ROOT,)),
        ('chat', module.build_lab_chat_payload, ['ok', 'meta', 'capabilities', 'messages', 'selected_documents', 'session_diagnostics'], (REPO_ROOT,)),
        ('workflow-inspector', module.build_lab_workflow_inspector_payload, ['ok', 'meta', 'capabilities', 'summary', 'task_options', 'task_details', 'recent_cases'], (REPO_ROOT,)),
        ('benchmarks', module.build_lab_benchmarks_payload, ['ok', 'meta', 'summary', 'models', 'presets', 'retrievalObservations'], (REPO_ROOT,)),
        ('evals', module.build_lab_evals_payload, ['ok', 'meta', 'passRate', 'totals', 'suites', 'cases', 'diagnosis'], (REPO_ROOT,)),
        ('artifacts', module.build_lab_artifacts_payload, ['ok', 'meta', 'artifacts', 'summary', 'diagnostics'], (REPO_ROOT,)),
        ('evidenceops', module.build_lab_evidenceops_payload, ['ok', 'meta', 'summary', 'tools', 'actions', 'operations', 'telemetry', 'readiness'], (REPO_ROOT,)),
        ('evidenceops-search', lambda root: module.build_lab_evidenceops_search_payload(root, query='vendor'), ['ok', 'meta', 'query', 'repositoryRoot', 'results'], (REPO_ROOT,)),
    ]

    print('AI LAB builder smoke validation')
    print(f'Repo root: {REPO_ROOT}')
    failures: list[str] = []
    summary: dict[str, Any] = {
        'generated_at': _now_stamp(),
        'repo_root': str(REPO_ROOT),
        'mode': 'builder',
        'checks': [],
        'errors': [],
    }

    for name, builder, required_keys, args in builders:
        try:
            payload = builder(*args)
            if not isinstance(payload, dict):
                raise AssertionError(f'{name} builder returned {type(payload).__name__}, expected dict')
            assert_keys(name, payload, required_keys)
            payload_summary = summarize(payload)
            detail = {
                'summary': payload_summary,
                'required_keys': required_keys,
                'meta': payload.get('meta'),
            }
            _record_check(summary, name=name, status='passed', detail=detail)
            if output_dir is not None:
                write_json(output_dir / 'builders' / f'{_slugify(name)}.json', payload)
            print(f'[OK] {name}: {payload_summary}')
        except Exception as exc:  # pragma: no cover - smoke diagnostics
            failure = f'{name}: {exc}'
            failures.append(failure)
            _record_check(summary, name=name, status='failed', detail={'summary': str(exc)}, errors=[failure])
            print(f'[FAIL] {name}: {exc}')

    summary['status'] = 'passed' if not failures else 'failed'
    _write_summary(output_dir, summary)

    if failures:
        print('\nBuilder failures:')
        for failure in failures:
            print(f' - {failure}')
        return 1, summary

    print('\nAll AI LAB payload builders returned structured data from persisted project state.')
    return 0, summary


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url) as response:
        body = response.read().decode('utf-8')
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise AssertionError(f'{url} returned {type(payload).__name__}, expected dict')
    return payload


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urlopen(request) as response:
            body = response.read().decode('utf-8')
    except HTTPError as error:
        error_body = error.read().decode('utf-8', errors='replace')
        raise AssertionError(f'{url} returned HTTP {error.code}: {error_body}') from error
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise AssertionError(f'{url} returned {type(parsed).__name__}, expected dict')
    return parsed


def run_http_smoke(base_url: str, *, output_dir: Path | None = None, exercise_live: bool = False) -> tuple[int, dict[str, Any]]:
    base_url = base_url.rstrip('/')
    routes: list[tuple[str, str, list[str]]] = [
        ('overview', '/api/lab/overview', ['ok', 'meta', 'runtime', 'kpis', 'alerts', 'workflow_mix']),
        ('runtime', '/api/lab/runtime', ['ok', 'meta', 'runtime', 'generation_rows', 'retrieval_rows', 'vector_rows', 'diagnostics_rows']),
        ('chat', '/api/lab/chat', ['ok', 'meta', 'capabilities', 'messages', 'selected_documents', 'session_diagnostics']),
        ('workflow-inspector', '/api/lab/workflow-inspector', ['ok', 'meta', 'capabilities', 'summary', 'task_options', 'task_details', 'recent_cases']),
        ('benchmarks', '/api/lab/benchmarks', ['ok', 'meta', 'summary', 'models', 'presets', 'retrievalObservations']),
        ('evals', '/api/lab/evals', ['ok', 'meta', 'passRate', 'totals', 'suites', 'cases', 'diagnosis']),
        ('artifacts', '/api/lab/artifacts', ['ok', 'meta', 'artifacts', 'summary', 'diagnostics']),
        ('evidenceops', '/api/lab/evidenceops', ['ok', 'meta', 'summary', 'tools', 'actions', 'operations', 'telemetry', 'readiness']),
        ('evidenceops-search', f"/api/lab/evidenceops/search?q={quote('vendor')}", ['ok', 'meta', 'query', 'repositoryRoot', 'results']),
    ]

    print('\nAI LAB HTTP smoke validation')
    print(f'Base URL: {base_url}')
    failures: list[str] = []
    summary: dict[str, Any] = {
        'generated_at': _now_stamp(),
        'repo_root': str(REPO_ROOT),
        'mode': 'http',
        'base_url': base_url,
        'checks': [],
        'errors': [],
    }
    responses_by_name: dict[str, dict[str, Any]] = {}

    for name, route, required_keys in routes:
        url = f'{base_url}{route}'
        try:
            payload = _fetch_json(url)
            assert_keys(name, payload, required_keys)
            responses_by_name[name] = payload
            payload_summary = summarize(payload)
            _record_check(summary, name=name, status='passed', detail={'summary': payload_summary, 'route': route, 'required_keys': required_keys, 'meta': payload.get('meta')})
            if output_dir is not None:
                write_json(output_dir / 'http' / f'{_slugify(name)}.json', payload)
            print(f'[OK] {name}: {payload_summary}')
        except (HTTPError, URLError, json.JSONDecodeError, AssertionError) as exc:
            failure = f'{name}: {exc}'
            failures.append(failure)
            _record_check(summary, name=name, status='failed', detail={'summary': str(exc), 'route': route}, errors=[failure])
            print(f'[FAIL] {name}: {exc}')

    if exercise_live and not failures:
        print('\nAI LAB live exercise validation')
        try:
            chat_payload = responses_by_name.get('chat') or _fetch_json(f'{base_url}/api/lab/chat')
            selected_documents = chat_payload.get('selected_documents') if isinstance(chat_payload.get('selected_documents'), list) else []
            selected_document_ids = [str(item.get('document_id') or '').strip() for item in selected_documents if isinstance(item, dict) and str(item.get('document_id') or '').strip()]
            created = _post_json(f'{base_url}/api/lab/chat/sessions', {'document_ids': selected_document_ids[:3], 'title': 'Smoke validation session'})
            session_id = str((created.get('session') or {}).get('session_id') or '').strip()
            if not session_id:
                raise AssertionError('Chat session creation did not return a session_id.')
            sent = _post_json(
                f'{base_url}/api/lab/chat/sessions/{quote(session_id)}/messages',
                {
                    'content': 'Summarize the main evidence available in one short paragraph.',
                    'document_ids': selected_document_ids[:3],
                },
            )
            if output_dir is not None:
                write_json(output_dir / 'http' / 'chat_session_created.json', created)
                write_json(output_dir / 'http' / 'chat_message_sent.json', sent)
            _record_check(
                summary,
                name='chat-live',
                status='passed',
                detail={
                    'summary': f"session {session_id} / {len((sent.get('page') or {}).get('messages') or [])} messages",
                    'session_id': session_id,
                },
            )
            print(f'[OK] chat-live: session {session_id}')
        except Exception as exc:  # pragma: no cover - live diagnostics
            failure = f'chat-live: {exc}'
            failures.append(failure)
            _record_check(summary, name='chat-live', status='failed', detail={'summary': str(exc)}, errors=[failure])
            print(f'[FAIL] chat-live: {exc}')

        try:
            workflow_payload = responses_by_name.get('workflow-inspector') or _fetch_json(f'{base_url}/api/lab/workflow-inspector')
            task_options = workflow_payload.get('task_options') if isinstance(workflow_payload.get('task_options'), list) else []
            document_options = workflow_payload.get('document_options') if isinstance(workflow_payload.get('document_options'), list) else []
            task_id = str((task_options[0] if task_options else {}).get('id') or 'review_document_risks').strip() or 'review_document_risks'
            document_id = str((document_options[0] if document_options else {}).get('id') or '').strip() or None
            run_payload = {
                'task_id': task_id,
                'input_text': 'Run the selected workflow and summarize the operational outcome.',
            }
            if document_id:
                run_payload['document_id'] = document_id
            run_response = _post_json(f'{base_url}/api/lab/workflow-inspector/run', run_payload)
            run_id = str((run_response.get('run') or {}).get('run_id') or '').strip()
            if output_dir is not None:
                write_json(output_dir / 'http' / 'workflow_run.json', run_response)
            _record_check(
                summary,
                name='workflow-live',
                status='passed',
                detail={
                    'summary': f"run {run_id or 'unknown'} / task {task_id}",
                    'run_id': run_id,
                    'task_id': task_id,
                },
            )
            print(f'[OK] workflow-live: {run_id or task_id}')
        except Exception as exc:  # pragma: no cover - live diagnostics
            failure = f'workflow-live: {exc}'
            failures.append(failure)
            _record_check(summary, name='workflow-live', status='failed', detail={'summary': str(exc)}, errors=[failure])
            print(f'[FAIL] workflow-live: {exc}')

    summary['status'] = 'passed' if not failures else 'failed'
    _write_summary(output_dir, summary)

    if failures:
        print('\nHTTP failures:')
        for failure in failures:
            print(f' - {failure}')
        return 1, summary

    print('\nAll AI LAB HTTP endpoints returned structured payloads.')
    return 0, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Smoke test the AI LAB payload builders and optional HTTP endpoints.')
    parser.add_argument('--base-url', help='Optional Product API base URL, for example http://127.0.0.1:8000')
    parser.add_argument('--exercise-live', action='store_true', help='Exercise live chat and workflow execution when --base-url is provided.')
    parser.add_argument('--output-dir', help='Optional directory where JSON payloads and summaries should be written.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = ensure_output_dir(Path(args.output_dir).expanduser().resolve() if args.output_dir else None)
    builder_status, builder_summary = run_builder_smoke(output_dir / 'builder' if output_dir else None)
    if args.base_url:
        http_status, http_summary = run_http_smoke(args.base_url, output_dir=output_dir / 'http' if output_dir else None, exercise_live=bool(args.exercise_live))
        if output_dir is not None:
            combined = {
                'generated_at': _now_stamp(),
                'repo_root': str(REPO_ROOT),
                'builder': builder_summary,
                'http': http_summary,
                'status': 'passed' if builder_status == 0 and http_status == 0 else 'failed',
            }
            write_json(output_dir / 'summary.json', combined)
            write_text(
                output_dir / 'summary.md',
                '\n'.join(
                    [
                        '# AI LAB smoke validation',
                        '',
                        f"Generated at: {combined['generated_at']}",
                        f"Builder status: {builder_summary.get('status')}",
                        f"HTTP status: {http_summary.get('status')}",
                        '',
                        '## Builder checks',
                        *[f"- {item.get('name')}: {item.get('status')} — {item.get('summary')}" for item in builder_summary.get('checks', [])],
                        '',
                        '## HTTP checks',
                        *[f"- {item.get('name')}: {item.get('status')} — {item.get('summary')}" for item in http_summary.get('checks', [])],
                        '',
                    ]
                ) + '\n',
            )
        return 0 if builder_status == 0 and http_status == 0 else 1
    return builder_status


if __name__ == '__main__':
    raise SystemExit(main())
