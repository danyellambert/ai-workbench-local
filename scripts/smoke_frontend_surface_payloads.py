#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import threading
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator
from urllib import error as urllib_error
from urllib import request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@contextmanager
def ephemeral_product_api(repo_root: Path) -> Iterator[str]:
    from src.app.product_bootstrap import build_product_bootstrap
    from src.config import ProductApiSettings
    from src.product.api import build_product_api_server

    bootstrap = replace(build_product_bootstrap(), workspace_root=repo_root)
    settings = ProductApiSettings(server_name='127.0.0.1', server_port=0, enable_web_frontend=True, allow_cors=True)
    server = build_product_api_server(bootstrap=bootstrap, settings=settings)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_address[1]}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request_json(base_url: str, path: str, *, method: str = 'GET', payload: dict[str, Any] | None = None, timeout_s: int = 120) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib_request.Request(f'{base_url}{path}', data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=timeout_s) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='ignore')
        return {'ok': False, 'status_code': exc.code, 'path': path, 'error': body}


def collect_payloads(base_url: str, *, attempt_rerun: bool = False) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    payloads['health'] = request_json(base_url, '/health')
    payloads['workflows'] = request_json(base_url, '/api/product/workflows')
    payloads['document_library'] = request_json(base_url, '/api/product/document-library')
    payloads['run_history'] = request_json(base_url, '/api/product/run-history')
    payloads['artifacts'] = request_json(base_url, '/api/product/artifacts')
    payloads['runtime_controls'] = request_json(base_url, '/api/runtime/controls')
    payloads['preferences'] = request_json(base_url, '/api/preferences')

    runs = payloads.get('run_history', {}).get('runs') or []
    artifacts = payloads.get('artifacts', {}).get('artifacts') or []

    if runs:
        first_run_id = str(runs[0].get('id') or '').strip()
        if first_run_id:
            payloads['run_detail'] = request_json(base_url, f'/api/product/run-history/{first_run_id}')
            if attempt_rerun and runs[0].get('can_rerun'):
                payloads['rerun_attempt'] = request_json(base_url, f'/api/product/run-history/{first_run_id}/rerun', method='POST', payload={})

    if artifacts:
        first_artifact_id = str(artifacts[0].get('id') or '').strip()
        if first_artifact_id:
            payloads['artifact_detail'] = request_json(base_url, f'/api/product/artifacts/{first_artifact_id}')

    summary = {
        'workflow_count': int(payloads.get('workflows', {}).get('workflow_count') or 0),
        'document_count': int(payloads.get('document_library', {}).get('summary', {}).get('total_documents') or 0),
        'run_count': int(payloads.get('run_history', {}).get('summary', {}).get('total_runs') or 0),
        'artifact_count': int(payloads.get('artifacts', {}).get('summary', {}).get('total_artifacts') or 0),
        'active_runtime_profile': payloads.get('runtime_controls', {}).get('active_profile', {}).get('name') if isinstance(payloads.get('runtime_controls', {}).get('active_profile'), dict) else None,
        'active_preferences_profile': payloads.get('preferences', {}).get('active_profile_id'),
        'has_run_detail': 'run_detail' in payloads,
        'has_artifact_detail': 'artifact_detail' in payloads,
        'has_rerun_attempt': 'rerun_attempt' in payloads,
    }
    payloads['summary'] = summary
    return payloads


def main() -> None:
    parser = argparse.ArgumentParser(description='Smoke-check the live frontend surface endpoints.')
    parser.add_argument('--base-url', help='Reuse an existing Product API base URL instead of starting an ephemeral server.')
    parser.add_argument('--output', help='Optional path to write the collected JSON payloads.')
    parser.add_argument('--attempt-rerun', action='store_true', help='Attempt a live rerun on the first rerunnable history entry.')
    args = parser.parse_args()

    if args.base_url:
        payloads = collect_payloads(args.base_url.rstrip('/'), attempt_rerun=args.attempt_rerun)
    else:
        with ephemeral_product_api(REPO_ROOT) as base_url:
            payloads = collect_payloads(base_url, attempt_rerun=args.attempt_rerun)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payloads, ensure_ascii=False, indent=2), encoding='utf-8')

    summary = payloads['summary']
    print(
        'frontend-surface smoke summary: '
        f"workflows={summary['workflow_count']} documents={summary['document_count']} runs={summary['run_count']} artifacts={summary['artifact_count']} "
        f"run_detail={summary['has_run_detail']} artifact_detail={summary['has_artifact_detail']} rerun_attempt={summary['has_rerun_attempt']}"
    )


if __name__ == '__main__':
    main()
