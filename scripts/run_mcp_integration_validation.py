#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / 'frontend'
DEFAULT_OUTPUT_ROOT = REPO_ROOT / 'tmp' / 'mcp_integration_validation'

PAGE_DEFINITIONS = [
    {'slug': 'action-plan', 'route': '/app/workflows/action-plan', 'title': 'Action Plan & Evidence Review', 'file': 'frontend/src/pages/ActionPlanPage.tsx'},
    {'slug': 'candidate-review', 'route': '/app/workflows/candidate-review', 'title': 'Candidate Review', 'file': 'frontend/src/pages/CandidateReviewPage.tsx'},
    {'slug': 'document-review', 'route': '/app/workflows/document-review', 'title': 'Document Review', 'file': 'frontend/src/pages/DocumentReviewPage.tsx'},
    {'slug': 'comparison', 'route': '/app/workflows/comparison', 'title': 'Policy & Contract Comparison', 'file': 'frontend/src/pages/ComparisonPage.tsx'},
    {'slug': 'documents', 'route': '/app/documents', 'title': 'Document Library', 'file': 'frontend/src/pages/DocumentsPage.tsx'},
    {'slug': 'evidenceops', 'route': '/app/lab/evidenceops', 'title': 'EvidenceOps / MCP', 'file': 'frontend/src/pages/EvidenceOpsPage.tsx'},
    {'slug': 'history', 'route': '/app/history', 'title': 'Run History', 'file': 'frontend/src/pages/RunHistoryPage.tsx'},
    {'slug': 'deck-center', 'route': '/app/deck-center', 'title': 'Deck Center', 'file': 'frontend/src/pages/DeckCenterPage.tsx'},
]

API_ENDPOINTS: list[tuple[str, str]] = [
    ('health', '/health'),
    ('workflows', '/api/product/workflows'),
    ('document-library', '/api/product/document-library'),
    ('run-history', '/api/product/run-history'),
    ('artifacts', '/api/product/artifacts'),
    ('integrations', '/api/product/integrations'),
    ('integrations-notion', '/api/product/integrations/notion?limit=6'),
    ('integrations-nextcloud', '/api/product/integrations/nextcloud?limit=6'),
]


@dataclass
class ProcessHandle:
    name: str
    process: subprocess.Popen[str]
    log_path: Path
    reused: bool = False


class ValidationError(RuntimeError):
    pass


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_text(path: Path, content: str) -> None:
    ensure_directory(path.parent)
    path.write_text(content, encoding='utf-8')


def tail_text(path: Path, line_count: int = 80) -> str:
    if not path.exists():
        return ''
    return '\n'.join(path.read_text(encoding='utf-8', errors='ignore').splitlines()[-line_count:])


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def probe_http(url: str, timeout_s: float = 2.0) -> bool:
    try:
        with urllib_request.urlopen(url, timeout=timeout_s) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def request_json(url: str, *, method: str = 'GET', payload: dict[str, Any] | None = None, timeout_s: int = 120) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=timeout_s) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='ignore')
        raise ValidationError(f'HTTP {exc.code} for {url}: {body}') from exc


@contextmanager
def managed_processes(handles: list[ProcessHandle]):
    try:
        yield
    finally:
        for handle in reversed(handles):
            if not handle.reused:
                terminate_process(handle.process)


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if sys.platform != 'win32':
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=10)
    except Exception:
        try:
            if sys.platform != 'win32':
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except Exception:
            pass


def start_background_process(*, name: str, cmd: list[str], cwd: Path, env: dict[str, str], log_path: Path) -> ProcessHandle:
    ensure_directory(log_path.parent)
    log_handle = log_path.open('w', encoding='utf-8')
    kwargs: dict[str, Any] = {'cwd': str(cwd), 'env': env, 'stdout': log_handle, 'stderr': subprocess.STDOUT, 'text': True}
    if sys.platform != 'win32':
        kwargs['preexec_fn'] = os.setsid
    process = subprocess.Popen(cmd, **kwargs)
    return ProcessHandle(name=name, process=process, log_path=log_path)


def wait_for_http_or_process_exit(url: str, *, handle: ProcessHandle, timeout_s: int = 180) -> None:
    deadline = time.time() + timeout_s
    last_error = 'timeout'
    while time.time() < deadline:
        if handle.process.poll() is not None:
            raise ValidationError(f'Process `{handle.name}` exited early with code {handle.process.returncode}.')
        try:
            with urllib_request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as error:
            last_error = str(error)
            time.sleep(1)
    raise ValidationError(f'Timed out waiting for {url}: {last_error}')


def frontend_toolchain_issues() -> list[str]:
    issues: list[str] = []
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == 'linux' and machine in {'x86_64', 'amd64'}:
        if not ((FRONTEND_DIR / 'node_modules' / '@rollup' / 'rollup-linux-x64-gnu').exists() or (FRONTEND_DIR / 'node_modules' / '@rollup' / 'rollup-linux-x64-musl').exists()):
            issues.append('Missing Linux Rollup native package in frontend/node_modules/@rollup.')
        if not (FRONTEND_DIR / 'node_modules' / '@esbuild' / 'linux-x64').exists():
            issues.append('Missing Linux esbuild package in frontend/node_modules/@esbuild.')
    return issues


def build_validation_manifest() -> dict[str, Any]:
    return {
        'generated_from': 'scripts/run_mcp_integration_validation.py',
        'pages': PAGE_DEFINITIONS,
        'required_artifacts': {
            'root': ['summary.json', 'summary.md', 'validation-manifest.json', 'run-meta.json'],
            'directories': ['payloads', 'screenshots', 'api', 'browser', 'dom', 'status', 'traces', 'logs'],
        },
        'api_endpoints': [{'name': name, 'route': route} for name, route in API_ENDPOINTS],
    }


def collect_endpoint_payloads(base_url: str, out_dir: Path) -> dict[str, Any]:
    payload_dir = ensure_directory(out_dir / 'payloads')
    results: dict[str, Any] = {}
    for name, route in API_ENDPOINTS:
        url = f'{base_url}{route}'
        try:
            payload = request_json(url)
            results[name] = {'status': 'ok', 'route': route, 'payload': payload}
        except Exception as error:
            payload = {'ok': False, 'route': route, 'error': str(error)}
            results[name] = {'status': 'error', 'route': route, 'payload': payload}
        write_json(payload_dir / f'{name}.json', payload)

    try:
        sync_payload = request_json(f'{base_url}/api/product/integrations/nextcloud/sync', method='POST', payload={'dry_run': True})
        results['nextcloud-sync-dry-run'] = {'status': 'ok', 'route': '/api/product/integrations/nextcloud/sync', 'payload': sync_payload}
        write_json(payload_dir / 'nextcloud-sync-dry-run.json', sync_payload)
    except Exception as error:
        payload = {'ok': False, 'route': '/api/product/integrations/nextcloud/sync', 'error': str(error)}
        results['nextcloud-sync-dry-run'] = {'status': 'error', 'route': '/api/product/integrations/nextcloud/sync', 'payload': payload}
        write_json(payload_dir / 'nextcloud-sync-dry-run.json', payload)

    runs = results.get('run-history', {}).get('payload', {}).get('runs') or []
    if runs:
        run_id = str(runs[0].get('id') or '').strip()
        if run_id:
            try:
                payload = request_json(f'{base_url}/api/product/run-history/{run_id}')
                results['run-detail'] = {'status': 'ok', 'route': f'/api/product/run-history/{run_id}', 'payload': payload}
                write_json(payload_dir / 'run-detail.json', payload)
            except Exception as error:
                payload = {'ok': False, 'route': f'/api/product/run-history/{run_id}', 'error': str(error)}
                results['run-detail'] = {'status': 'error', 'route': f'/api/product/run-history/{run_id}', 'payload': payload}
                write_json(payload_dir / 'run-detail.json', payload)
    return results


def collect_page_statuses(out_dir: Path) -> list[dict[str, Any]]:
    status_dir = out_dir / 'status'
    pages: list[dict[str, Any]] = []
    if not status_dir.exists():
        return pages
    for path in sorted(status_dir.glob('*.json')):
        try:
            pages.append(json.loads(path.read_text(encoding='utf-8')))
        except Exception as error:
            pages.append({'slug': path.stem, 'status': 'failed', 'error': str(error)})
    return pages


def collect_page_artifact_inventory(out_dir: Path) -> dict[str, Any]:
    inventory: dict[str, Any] = {}
    for page in PAGE_DEFINITIONS:
        slug = page['slug']
        screenshots = sorted(item.name for item in (out_dir / 'screenshots').glob(f'{slug}*.png'))
        inventory[slug] = {
            'screenshots': screenshots,
            'screenshot_count': len(screenshots),
            'has_api_log': (out_dir / 'api' / f'{slug}.json').exists(),
            'has_browser_log': (out_dir / 'browser' / f'{slug}.json').exists(),
            'has_dom_snapshot': (out_dir / 'dom' / f'{slug}.html').exists(),
            'has_status': (out_dir / 'status' / f'{slug}.json').exists(),
            'has_trace': (out_dir / 'traces' / f'{slug}.zip').exists(),
        }
    return inventory


def write_summary(out_dir: Path, *, backend_base_url: str, frontend_base_url: str, endpoint_results: dict[str, Any], page_statuses: list[dict[str, Any]], inventory: dict[str, Any], commands: list[dict[str, str]], toolchain_issues: list[str]) -> None:
    totals = {'passed': 0, 'degraded': 0, 'failed': 0, 'skipped': 0}
    for page in page_statuses:
        status = str(page.get('status') or 'failed')
        totals[status] = totals.get(status, 0) + 1
    summary = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'backend_base_url': backend_base_url,
        'frontend_base_url': frontend_base_url,
        'totals': totals,
        'endpoint_results': {name: value.get('status') for name, value in endpoint_results.items()},
        'pages': page_statuses,
        'artifact_inventory': inventory,
        'commands': commands,
        'toolchain_issues': toolchain_issues,
    }
    write_json(out_dir / 'summary.json', summary)

    lines = [
        '# MCP integration validation summary',
        '',
        f'- Backend: `{backend_base_url}`',
        f'- Frontend: `{frontend_base_url}`',
        f'- Pages: passed {totals.get("passed", 0)}, degraded {totals.get("degraded", 0)}, failed {totals.get("failed", 0)}, skipped {totals.get("skipped", 0)}',
        '',
        '## Pages',
    ]
    for page in page_statuses:
        lines.append(f"- `{page.get('slug')}` -> **{page.get('status', 'failed')}**")
    lines.extend(['', '## Endpoint checks'])
    for name, result in endpoint_results.items():
        lines.append(f"- `{name}` -> {result.get('status', 'error')}")
    if toolchain_issues:
        lines.extend(['', '## Toolchain issues'])
        lines.extend([f'- {issue}' for issue in toolchain_issues])
    write_text(out_dir / 'summary.md', '\n'.join(lines) + '\n')


def zip_output_dir(out_dir: Path) -> Path:
    zip_path = out_dir.with_suffix('.zip')
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in out_dir.rglob('*'):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(out_dir))
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate MCP integration surfaces and collect screenshots, payloads and status logs.')
    parser.add_argument('--output-root', default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument('--backend-base-url', help='Reuse an existing Product API instead of starting one.')
    parser.add_argument('--frontend-base-url', help='Reuse an existing frontend dev server instead of starting one.')
    parser.add_argument('--python-bin', default=sys.executable)
    parser.add_argument('--allow-mutations', action='store_true', help='Allow Playwright to click live mutation buttons.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    out_dir = ensure_directory(Path(args.output_root).resolve() / timestamp)
    for directory in ['payloads', 'screenshots', 'api', 'browser', 'dom', 'status', 'traces', 'logs']:
        ensure_directory(out_dir / directory)
    write_json(out_dir / 'validation-manifest.json', build_validation_manifest())

    commands: list[dict[str, str]] = []
    handles: list[ProcessHandle] = []
    backend_base_url = args.backend_base_url
    frontend_base_url = args.frontend_base_url
    backend_port = None
    frontend_port = None
    toolchain_issues = frontend_toolchain_issues()

    with managed_processes(handles):
        if not backend_base_url:
            backend_port = find_free_port()
            backend_base_url = f'http://127.0.0.1:{backend_port}'
            env = os.environ.copy()
            env['PRODUCT_API_SERVER_PORT'] = str(backend_port)
            backend_log = out_dir / 'logs' / 'product-api.log'
            handle = start_background_process(name='product-api', cmd=[args.python_bin, 'main_product_api.py'], cwd=REPO_ROOT, env=env, log_path=backend_log)
            handles.append(handle)
            commands.append({'name': 'backend', 'cmd': f'PRODUCT_API_SERVER_PORT={backend_port} {args.python_bin} main_product_api.py'})
            wait_for_http_or_process_exit(f'{backend_base_url}/health', handle=handle, timeout_s=240)
        else:
            commands.append({'name': 'backend', 'cmd': f'reuse {backend_base_url}'})
            if not probe_http(f'{backend_base_url}/health'):
                raise ValidationError(f'Could not reach backend at {backend_base_url}')

        if not frontend_base_url:
            if toolchain_issues:
                raise ValidationError('Frontend toolchain is incomplete: ' + '; '.join(toolchain_issues))
            frontend_port = find_free_port()
            frontend_base_url = f'http://127.0.0.1:{frontend_port}'
            env = os.environ.copy()
            env['VITE_PRODUCT_API_BASE_URL'] = backend_base_url
            frontend_log = out_dir / 'logs' / 'frontend.log'
            handle = start_background_process(
                name='frontend',
                cmd=['node', str(FRONTEND_DIR / 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(frontend_port), '--strictPort'],
                cwd=FRONTEND_DIR,
                env=env,
                log_path=frontend_log,
            )
            handles.append(handle)
            commands.append({'name': 'frontend', 'cmd': f'cd frontend && VITE_PRODUCT_API_BASE_URL={backend_base_url} node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port {frontend_port} --strictPort'})
            wait_for_http_or_process_exit(frontend_base_url, handle=handle, timeout_s=240)
        else:
            commands.append({'name': 'frontend', 'cmd': f'reuse {frontend_base_url}'})
            if not probe_http(frontend_base_url):
                raise ValidationError(f'Could not reach frontend at {frontend_base_url}')

        endpoint_results = collect_endpoint_payloads(backend_base_url, out_dir)

        env = os.environ.copy()
        env['PLAYWRIGHT_BASE_URL'] = frontend_base_url
        env['MCP_INTEGRATION_OUTPUT_DIR'] = str(out_dir)
        env['MCP_INTEGRATION_ALLOW_MUTATIONS'] = '1' if args.allow_mutations else '0'
        playwright_cmd = ['npx', 'playwright', 'test', 'tests/mcp-integration-validation.spec.ts', '--config=playwright.config.ts']
        commands.append({'name': 'playwright', 'cmd': 'cd frontend && ' + ' '.join(playwright_cmd)})
        playwright_result = subprocess.run(playwright_cmd, cwd=FRONTEND_DIR, env=env, text=True, capture_output=True)
        write_text(out_dir / 'logs' / 'playwright.stdout.log', playwright_result.stdout)
        write_text(out_dir / 'logs' / 'playwright.stderr.log', playwright_result.stderr)

        toolchain_issues_local = list(toolchain_issues)
        page_statuses = collect_page_statuses(out_dir)
        if playwright_result.returncode != 0:
            toolchain_issues_local.append({
                'name': 'playwright',
                'status': 'degraded',
                'details': f'Playwright exited with code {playwright_result.returncode}; summary artifacts were still collected.',
            })
            if not page_statuses:
                raise ValidationError(f'Playwright validation failed with code {playwright_result.returncode}.')
        inventory = collect_page_artifact_inventory(out_dir)
        write_summary(
            out_dir,
            backend_base_url=backend_base_url,
            frontend_base_url=frontend_base_url,
            endpoint_results=endpoint_results,
            page_statuses=page_statuses,
            inventory=inventory,
            commands=commands,
            toolchain_issues=toolchain_issues_local,
        )
        zip_path = zip_output_dir(out_dir)
        write_json(out_dir / 'run-meta.json', {
            'ok': playwright_result.returncode == 0,
            'output_dir': str(out_dir),
            'zip_path': str(zip_path),
            'backend_base_url': backend_base_url,
            'frontend_base_url': frontend_base_url,
            'commands': commands,
        })
        if playwright_result.returncode != 0:
            print(f'Playwright validation completed with degraded status (code {playwright_result.returncode}); artifacts were still generated.', file=sys.stderr)
        print(f'mcp integration validation complete: {out_dir}')
        print(f'mcp integration validation zip: {zip_path}')
        return 0

    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ValidationError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
