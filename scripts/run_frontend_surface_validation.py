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
DEFAULT_OUTPUT_ROOT = REPO_ROOT / 'tmp' / 'frontend_surface_validation'

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PAGE_DEFINITIONS = [
    {'slug': 'run', 'route': '/app/run', 'title': 'Decision Workflows', 'file': 'frontend/src/pages/WorkflowCatalogPage.tsx'},
    {'slug': 'deck-center', 'route': '/app/deck-center', 'title': 'Deck Center', 'file': 'frontend/src/pages/DeckCenterPage.tsx'},
    {'slug': 'history', 'route': '/app/history', 'title': 'Run History', 'file': 'frontend/src/pages/RunHistoryPage.tsx'},
    {'slug': 'runtime-controls', 'route': '/app/settings/runtime', 'title': 'Runtime Controls', 'file': 'frontend/src/pages/RuntimeControlsPage.tsx'},
    {'slug': 'preferences', 'route': '/app/settings/preferences', 'title': 'Preferences', 'file': 'frontend/src/pages/PreferencesPage.tsx'},
]

API_ENDPOINTS: list[tuple[str, str]] = [
    ('health', '/health'),
    ('workflows', '/api/product/workflows'),
    ('document-library', '/api/product/document-library'),
    ('run-history', '/api/product/run-history'),
    ('artifacts', '/api/product/artifacts'),
    ('runtime-controls', '/api/runtime/controls'),
    ('preferences', '/api/preferences'),
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


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(('127.0.0.1', port)) == 0


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
    kwargs: dict[str, Any] = {
        'cwd': str(cwd),
        'env': env,
        'stdout': log_handle,
        'stderr': subprocess.STDOUT,
        'text': True,
    }
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
        except Exception as error:  # noqa: BLE001
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
        'generated_from': 'scripts/run_frontend_surface_validation.py',
        'pages': PAGE_DEFINITIONS,
        'required_artifacts': {
            'root': ['summary.json', 'summary.md', 'validation-manifest.json'],
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
        except Exception as error:  # noqa: BLE001
            payload = {'ok': False, 'route': route, 'error': str(error)}
            results[name] = {'status': 'error', 'route': route, 'payload': payload}
        write_json(payload_dir / f'{name}.json', payload)

    runs = results.get('run-history', {}).get('payload', {}).get('runs') or []
    artifacts = results.get('artifacts', {}).get('payload', {}).get('artifacts') or []

    if runs:
        run_id = str(runs[0].get('id') or '').strip()
        if run_id:
            payload = request_json(f'{base_url}/api/product/run-history/{run_id}')
            results['run-detail'] = {'status': 'ok', 'route': f'/api/product/run-history/{run_id}', 'payload': payload}
            write_json(payload_dir / 'run-detail.json', payload)

    if artifacts:
        artifact_id = str(artifacts[0].get('id') or '').strip()
        if artifact_id:
            payload = request_json(f'{base_url}/api/product/artifacts/{artifact_id}')
            results['artifact-detail'] = {'status': 'ok', 'route': f'/api/product/artifacts/{artifact_id}', 'payload': payload}
            write_json(payload_dir / 'artifact-detail.json', payload)

    return results


def collect_page_statuses(out_dir: Path) -> list[dict[str, Any]]:
    status_dir = out_dir / 'status'
    pages: list[dict[str, Any]] = []
    if not status_dir.exists():
        return pages
    for path in sorted(status_dir.glob('*.json')):
        try:
            pages.append(json.loads(path.read_text(encoding='utf-8')))
        except Exception as error:  # noqa: BLE001
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


def build_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        '# Frontend surface validation summary',
        '',
        f"- Generated at: {summary['generated_at']}",
        f"- Output dir: `{summary['output_dir']}`",
        f"- Backend: {summary.get('backend_base_url') or 'n/a'}",
        f"- Frontend: {summary.get('frontend_base_url') or 'n/a'}",
        '',
        '## Endpoint checks',
        '',
    ]
    for name, result in summary.get('endpoint_results', {}).items():
        lines.append(f"- `{name}`: {result.get('status', 'unknown')}")
    lines.append('')
    lines.append('## Page status')
    lines.append('')
    lines.append(f"- Playwright result: {summary.get('playwright_result', {}).get('status', 'unknown')}")
    if summary.get('playwright_result', {}).get('reason'):
        lines.append(f"- Playwright note: {summary['playwright_result']['reason']}")
    lines.append('')
    if summary.get('page_results'):
        for page in summary['page_results']:
            interactions = ', '.join(step.get('label', 'unknown') for step in page.get('steps', []) if step.get('status') == 'ok') or 'no scripted interaction'
            artifact_info = summary.get('page_artifacts', {}).get(page.get('slug', ''), {})
            lines.append(
                f"- `{page.get('slug')}`: {page.get('status')} · screenshots={artifact_info.get('screenshot_count', 0)} · trace={'yes' if artifact_info.get('has_trace') else 'no'} · {interactions}"
            )
    else:
        lines.append('- Playwright did not run or did not emit page status files.')
    if summary.get('blockers'):
        lines.append('')
        lines.append('## Blockers')
        lines.append('')
        for blocker in summary['blockers']:
            lines.append(f'- {blocker}')
    return '\n'.join(lines) + '\n'


def archive_output_dir(out_dir: Path) -> Path:
    zip_path = out_dir.with_suffix('.zip')
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in out_dir.rglob('*'):
            archive.write(file_path, file_path.relative_to(out_dir.parent))
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description='Run end-to-end validation for the Run/Deck/History/Runtime/Preferences frontend surfaces.')
    parser.add_argument('--output-dir', help='Optional explicit output directory. Defaults to tmp/frontend_surface_validation/<timestamp>.')
    parser.add_argument('--backend-base-url', help='Reuse an existing Product API backend instead of starting one.')
    parser.add_argument('--frontend-base-url', help='Reuse an existing frontend dev server instead of starting one.')
    parser.add_argument('--skip-playwright', action='store_true', help='Collect endpoint payloads only and skip browser validation.')
    parser.add_argument('--allow-mutations', action='store_true', help='Allow scripted write interactions on settings pages.')
    parser.add_argument('--allow-rerun', action='store_true', help='Allow the history page to trigger a rerun when possible.')
    args = parser.parse_args()

    timestamp = time.strftime('%Y%m%d_%H%M%S', time.gmtime())
    out_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_ROOT / timestamp
    logs_dir = ensure_directory(out_dir / 'logs')
    ensure_directory(out_dir)
    for name in ['payloads', 'screenshots', 'api', 'browser', 'dom', 'status', 'traces']:
        ensure_directory(out_dir / name)

    backend_port = find_free_port()
    frontend_port = find_free_port()
    blockers: list[str] = []
    commands: list[dict[str, Any]] = []
    manifest = build_validation_manifest()
    write_json(out_dir / 'validation-manifest.json', manifest)

    backend_base_url: str | None = None
    frontend_base_url: str | None = None
    endpoint_results: dict[str, Any] = {}
    page_results: list[dict[str, Any]] = []
    playwright_result: dict[str, Any] = {'status': 'not-started'}

    handles: list[ProcessHandle] = []
    with managed_processes(handles):
        backend_base_url = args.backend_base_url.rstrip('/') if args.backend_base_url else None
        if backend_base_url and probe_http(f'{backend_base_url}/health'):
            write_text(logs_dir / 'backend.log', f'Reusing backend at {backend_base_url}\n')
            commands.append({'name': 'backend', 'cmd': f'# reused existing backend {backend_base_url}'})
        else:
            backend_log = logs_dir / 'backend.log'
            backend_env = os.environ.copy()
            backend_env['PRODUCT_API_SERVER_NAME'] = '127.0.0.1'
            backend_env['PRODUCT_API_SERVER_PORT'] = str(backend_port)
            backend_handle = start_background_process(
                name='backend',
                cmd=[sys.executable, 'main_product_api.py'],
                cwd=REPO_ROOT,
                env=backend_env,
                log_path=backend_log,
            )
            handles.append(backend_handle)
            backend_base_url = f'http://127.0.0.1:{backend_port}'
            wait_for_http_or_process_exit(f'{backend_base_url}/health', handle=backend_handle)
            commands.append({'name': 'backend', 'cmd': f'PRODUCT_API_SERVER_PORT={backend_port} {sys.executable} main_product_api.py'})

        endpoint_results = collect_endpoint_payloads(backend_base_url, out_dir)

        frontend_base_url = args.frontend_base_url.rstrip('/') if args.frontend_base_url else None
        if args.skip_playwright:
            playwright_result = {'status': 'skipped', 'reason': 'skip-playwright flag enabled'}
        else:
            toolchain_issues = frontend_toolchain_issues()
            if frontend_base_url and probe_http(frontend_base_url):
                playwright_result = {'status': 'ready', 'reason': 'reusing existing frontend'}
            elif toolchain_issues:
                blockers.extend(toolchain_issues)
                playwright_result = {'status': 'blocked', 'reason': 'frontend toolchain is not runnable in this environment', 'details': toolchain_issues}
            else:
                frontend_log = logs_dir / 'frontend.log'
                frontend_env = os.environ.copy()
                frontend_env['VITE_PRODUCT_API_BASE_URL'] = backend_base_url
                frontend_handle = start_background_process(
                    name='frontend',
                    cmd=['node', './node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(frontend_port)],
                    cwd=FRONTEND_DIR,
                    env=frontend_env,
                    log_path=frontend_log,
                )
                handles.append(frontend_handle)
                frontend_base_url = f'http://127.0.0.1:{frontend_port}'
                wait_for_http_or_process_exit(frontend_base_url, handle=frontend_handle)
                commands.append({'name': 'frontend', 'cmd': f'cd frontend && VITE_PRODUCT_API_BASE_URL={backend_base_url} node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port {frontend_port}'})
                playwright_result = {'status': 'ready', 'reason': 'frontend started successfully for Playwright validation'}

            if frontend_base_url and playwright_result.get('status') == 'ready':
                playwright_log = logs_dir / 'playwright.log'
                playwright_env = os.environ.copy()
                playwright_env['PLAYWRIGHT_BASE_URL'] = frontend_base_url
                playwright_env['PLAYWRIGHT_ARTIFACT_DIR'] = str(out_dir / 'playwright-artifacts')
                playwright_env['FRONTEND_SURFACE_OUTPUT_DIR'] = str(out_dir)
                playwright_env['FRONTEND_SURFACE_ALLOW_MUTATIONS'] = '1' if args.allow_mutations else '0'
                playwright_env['FRONTEND_SURFACE_ALLOW_RERUN'] = '1' if args.allow_rerun else '0'
                with playwright_log.open('w', encoding='utf-8') as handle:
                    result = subprocess.run(
                        ['node', './node_modules/@playwright/test/cli.js', 'test', 'tests/frontend-surface-validation.spec.ts', '--config', './playwright.config.ts'],
                        cwd=FRONTEND_DIR,
                        env=playwright_env,
                        stdout=handle,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                commands.append({'name': 'playwright', 'cmd': 'cd frontend && node ./node_modules/@playwright/test/cli.js test tests/frontend-surface-validation.spec.ts --config ./playwright.config.ts'})
                playwright_result = {'status': 'ok' if result.returncode == 0 else 'failed', 'returncode': result.returncode, 'log_path': str(playwright_log.relative_to(out_dir))}
                page_results = collect_page_statuses(out_dir)
                if not page_results:
                    playwright_result['status'] = 'failed'
                    playwright_result['reason'] = 'Playwright finished but no page status files were emitted.'
                else:
                    page_artifacts = collect_page_artifact_inventory(out_dir)
                    missing = [slug for slug, artifact in page_artifacts.items() if not artifact['has_status']]
                    if missing:
                        playwright_result['status'] = 'failed'
                        playwright_result['reason'] = f"Playwright finished but missing page status files for: {', '.join(missing)}"

    page_artifacts = collect_page_artifact_inventory(out_dir)
    summary = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'output_dir': str(out_dir),
        'backend_base_url': backend_base_url,
        'frontend_base_url': frontend_base_url,
        'commands': commands,
        'validation_manifest': manifest,
        'endpoint_results': endpoint_results,
        'page_results': page_results,
        'page_statuses': {page.get('slug', f'page-{index}'): page.get('status', 'unknown') for index, page in enumerate(page_results)},
        'surfaces': {page.get('slug', f'page-{index}'): page for index, page in enumerate(page_results)},
        'page_artifacts': page_artifacts,
        'playwright_result': playwright_result,
        'blockers': blockers,
        'pages_expected': PAGE_DEFINITIONS,
        'backend_log_tail': tail_text(logs_dir / 'backend.log'),
        'frontend_log_tail': tail_text(logs_dir / 'frontend.log'),
        'playwright_log_tail': tail_text(logs_dir / 'playwright.log'),
    }
    write_json(out_dir / 'summary.json', summary)
    write_text(out_dir / 'summary.md', build_summary_markdown(summary))
    zip_path = archive_output_dir(out_dir)
    print(f'frontend surface validation complete: {out_dir}')
    print(f'archive: {zip_path}')


if __name__ == '__main__':
    main()
