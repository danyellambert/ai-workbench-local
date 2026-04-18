from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / 'frontend'
DEFAULT_OUTPUT_DIR = REPO_ROOT / '.tmp_ai_lab_e2e'

AI_LAB_PAGES: list[dict[str, str]] = [
    {'slug': 'overview', 'route': '/app/lab/overview', 'title': 'AI Engineering Operating Console', 'file': 'frontend/src/pages/LabOverviewPage.tsx'},
    {'slug': 'runtime', 'route': '/app/lab/runtime', 'title': 'Runtime & Observability', 'file': 'frontend/src/pages/RuntimeObservabilityPage.tsx'},
    {'slug': 'chat', 'route': '/app/lab/chat', 'title': 'Document / Chat Experiments', 'file': 'frontend/src/pages/ChatPage.tsx'},
    {'slug': 'workflow-inspector', 'route': '/app/lab/workflow-inspector', 'title': 'Workflow Inspector', 'file': 'frontend/src/pages/WorkflowInspectorPage.tsx'},
    {'slug': 'benchmarks', 'route': '/app/lab/benchmarks', 'title': 'Benchmarks', 'file': 'frontend/src/pages/BenchmarksPage.tsx'},
    {'slug': 'evals', 'route': '/app/lab/evals', 'title': 'Evals & Diagnosis', 'file': 'frontend/src/pages/EvalsDiagnosisPage.tsx'},
    {'slug': 'artifacts', 'route': '/app/lab/artifacts', 'title': 'Experiments & Artifacts', 'file': 'frontend/src/pages/AdvancedExperimentsPage.tsx'},
    {'slug': 'evidenceops', 'route': '/app/lab/evidenceops', 'title': 'EvidenceOps / MCP', 'file': 'frontend/src/pages/EvidenceOpsPage.tsx'},
]

PRODUCT_ENDPOINTS: list[tuple[str, str]] = [
    ('health', '/health'),
    ('workflows', '/api/product/workflows'),
    ('document-library', '/api/product/document-library'),
    ('runtime-controls', '/api/runtime/controls'),
    ('command-center', '/api/product/command-center'),
    ('run-history', '/api/product/run-history'),
    ('artifacts', '/api/product/artifacts'),
    ('lab-overview', '/api/lab/overview'),
    ('lab-runtime', '/api/lab/runtime'),
    ('lab-chat', '/api/lab/chat'),
    ('lab-workflow-inspector', '/api/lab/workflow-inspector'),
    ('lab-benchmarks', '/api/lab/benchmarks'),
    ('lab-evals', '/api/lab/evals'),
    ('lab-artifacts', '/api/lab/artifacts'),
    ('lab-evidenceops', '/api/lab/evidenceops'),
]

REQUIRED_BACKEND_ROUTES = [route for _, route in PRODUCT_ENDPOINTS]

CURATED_DOCUMENTS: list[Path] = [
    REPO_ROOT / 'data/corpus_revisado/frontend_demo_grounded_v1/audit/Access Review Evidence Log.pdf',
    REPO_ROOT / 'data/corpus_revisado/frontend_demo_grounded_v1/evidence/Privileged Account Approval Email.pdf',
    REPO_ROOT / 'data/corpus_revisado/frontend_demo_grounded_v1/audit/Governance Committee Minutes and Action Items.pdf',
    REPO_ROOT / 'data/corpus_revisado/frontend_demo_grounded_v1/audit/Nonconformance Report - Vendor Access Review.pdf',
    REPO_ROOT / 'data/corpus_revisado/frontend_demo_grounded_v1/contracts/Master Service Agreement v4.2.pdf',
]


@dataclass
class ProcessHandle:
    name: str
    process: subprocess.Popen[str]
    log_path: Path
    reused: bool = False


class ValidationError(RuntimeError):
    pass


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


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def write_text(path: Path, content: str) -> None:
    ensure_directory(path.parent)
    path.write_text(content, encoding='utf-8')


def append_text(path: Path, content: str) -> None:
    ensure_directory(path.parent)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(content)


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


def probe_http(url: str, timeout_s: float = 1.0) -> bool:
    try:
        with urllib_request.urlopen(url, timeout=timeout_s) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def backend_is_compatible(base_url: str) -> bool:
    return all(probe_http(f'{base_url}{route}', timeout_s=1.0) for route in REQUIRED_BACKEND_ROUTES)


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


def wait_for_http_or_process_exit(url: str, *, handle: ProcessHandle, timeout_s: int = 150) -> None:
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
    except urllib_error.HTTPError as error:
        body = error.read().decode('utf-8', errors='ignore')
        raise ValidationError(f'HTTP {error.code} for {url}: {body}') from error


def multipart_upload(url: str, files: list[Path]) -> dict[str, Any]:
    boundary = '----AiLabValidationBoundary'
    body = bytearray()
    for path in files:
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend((f'Content-Disposition: form-data; name="files"; filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode('utf-8'))
        body.extend(path.read_bytes())
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    req = urllib_request.Request(url, data=bytes(body), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}, method='POST')
    with urllib_request.urlopen(req, timeout=300) as response:
        return json.loads(response.read().decode('utf-8'))


def classify_page_source(source_code: str) -> dict[str, Any]:
    uses_product_api = '@/lib/product-api' in source_code or 'useQuery' in source_code or 'fetch(' in source_code
    if 'source="mock"' in source_code or 'dataSource="mock"' in source_code:
        effective = 'mock'
    elif uses_product_api:
        effective = 'live'
    else:
        effective = 'derived'
    return {'uses_product_api': uses_product_api, 'effective_source': effective}


def build_ai_lab_manifest() -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    for entry in AI_LAB_PAGES:
        source_code = (REPO_ROOT / entry['file']).read_text(encoding='utf-8')
        pages.append({**entry, **classify_page_source(source_code)})
    return {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'pages': pages,
    }


def save_json_get(base_url: str, name: str, route: str, out_dir: Path, steps: list[dict[str, Any]]) -> None:
    target = out_dir / f'{name}.json'
    url = f'{base_url}{route}'
    try:
        payload = request_json(url)
        write_json(target, payload)
        write_json(out_dir / 'api' / f'{name}.json', payload)
        steps.append({'name': name, 'status': 'ok', 'output': str(target.relative_to(out_dir))})
    except Exception as error:  # noqa: BLE001
        failure = {'ok': False, 'url': url, 'error': str(error)}
        write_json(target, failure)
        write_json(out_dir / 'api' / f'{name}.json', failure)
        steps.append({'name': name, 'status': 'error', 'error': str(error), 'output': str(target.relative_to(out_dir))})


def choose_documents(document_library: dict[str, Any]) -> list[dict[str, Any]]:
    documents = document_library.get('documents') or []
    indexed = [item for item in documents if str(item.get('status') or '').lower() == 'indexed']
    return indexed if indexed else documents


def ensure_documents(base_url: str, out_dir: Path) -> dict[str, Any]:
    library = request_json(f'{base_url}/api/product/document-library')
    if choose_documents(library):
        return library
    candidates = [path for path in CURATED_DOCUMENTS if path.exists()]
    if not candidates:
        return library
    upload_response = multipart_upload(f'{base_url}/api/product/upload-documents', candidates[:4])
    write_json(out_dir / 'upload-response.json', upload_response)
    deadline = time.time() + 300
    last_payload = library
    while time.time() < deadline:
        payload = request_json(f'{base_url}/api/product/document-library')
        last_payload = payload
        if choose_documents(payload):
            return payload
        time.sleep(2)
    return last_payload


def maybe_generate_deck(base_url: str, out_dir: Path, workflow_response: dict[str, Any], file_stem: str, steps: list[dict[str, Any]]) -> None:
    result = workflow_response.get('result') or {}
    if not result.get('deck_available'):
        return
    response = request_json(f'{base_url}/api/product/generate-deck', method='POST', payload={'result': result}, timeout_s=120)
    write_json(out_dir / f'deck-response-{file_stem}.json', response)
    steps.append({'name': f'deck-{file_stem}', 'status': 'ok', 'output': f'deck-response-{file_stem}.json'})


def exercise_workflows(base_url: str, out_dir: Path, steps: list[dict[str, Any]]) -> None:
    library = ensure_documents(base_url, out_dir)
    write_json(out_dir / 'document-library.json', library)
    documents = choose_documents(library)
    write_json(out_dir / 'selection-state.json', {
        'document_count': len(documents),
        'document_ids': [item.get('document_id') for item in documents],
        'document_names': [item.get('name') for item in documents],
    })
    if not documents:
        steps.append({'name': 'exercise-live', 'status': 'skipped', 'reason': 'No indexed documents available.'})
        return

    provider = os.getenv('AI_LAB_WORKFLOW_PROVIDER', 'ollama')
    model = os.getenv('AI_LAB_WORKFLOW_MODEL') or os.getenv('OLLAMA_MODEL', 'nemotron-3-nano:30b-cloud')
    timeout_s = int(os.getenv('AI_LAB_WORKFLOW_TIMEOUT_SECONDS', '45'))

    workflow_jobs: list[tuple[str, dict[str, Any], str]] = [
        ('document-review', {
            'workflow_id': 'document_review',
            'document_ids': [documents[0].get('document_id')],
            'input_text': 'Summarize the main risks and next actions grounded in this document.',
            'provider': provider,
            'model': model,
        }, 'workflow-response-document-review.json'),
    ]
    if len(documents) >= 2:
        pair_ids = [documents[0].get('document_id'), documents[1].get('document_id')]
        workflow_jobs.extend([
            ('policy-comparison', {
                'workflow_id': 'policy_contract_comparison',
                'document_ids': pair_ids,
                'input_text': 'Compare the selected documents and highlight the most material business differences.',
                'provider': provider,
                'model': model,
            }, 'workflow-response-policy-comparison.json'),
            ('action-plan', {
                'workflow_id': 'action_plan_evidence_review',
                'document_ids': pair_ids,
                'input_text': 'Build a grounded action plan with evidence gaps, owners and due dates.',
                'provider': provider,
                'model': model,
            }, 'workflow-response-action-plan.json'),
        ])

    for label, payload, filename in workflow_jobs:
        try:
            query = urllib_parse.urlencode({'workflow_id': payload['workflow_id'], 'document_id': payload['document_ids'][0], 'strategy': 'document_scan', 'input_text': payload['input_text']})
            grounding = request_json(f'{base_url}/api/product/grounding-preview?{query}')
            write_json(out_dir / f'grounding-preview-{label}.json', grounding)
        except Exception as error:  # noqa: BLE001
            write_json(out_dir / f'grounding-preview-{label}.json', {'ok': False, 'error': str(error)})
        try:
            response = request_json(f'{base_url}/api/product/run-workflow', method='POST', payload=payload, timeout_s=timeout_s)
            write_json(out_dir / filename, response)
            steps.append({'name': f'workflow-{label}', 'status': 'ok', 'output': filename})
            maybe_generate_deck(base_url, out_dir, response, label, steps)
        except Exception as error:  # noqa: BLE001
            write_json(out_dir / filename, {'ok': False, 'error': str(error), 'request': payload})
            steps.append({'name': f'workflow-{label}', 'status': 'error', 'error': str(error), 'output': filename})

    for name, route in [('run-history', '/api/product/run-history'), ('artifacts', '/api/product/artifacts'), ('command-center', '/api/product/command-center')]:
        save_json_get(base_url, name, route, out_dir, steps)


def run_playwright(frontend_url: str, out_dir: Path, env: dict[str, str], steps: list[dict[str, Any]]) -> None:
    log_path = out_dir / 'playwright.log'
    playwright_env = env | {
        'PLAYWRIGHT_BASE_URL': frontend_url,
        'AI_LAB_OUTPUT_DIR': str(out_dir),
        'PLAYWRIGHT_ARTIFACT_DIR': str(out_dir / 'playwright-artifacts'),
    }

    def run_logged(cmd: list[str], check: bool = True) -> None:
        append_text(log_path, f"$ {' '.join(cmd)}\n")
        completed = subprocess.run(cmd, cwd=str(FRONTEND_DIR), env=playwright_env, text=True, capture_output=True, check=False)
        append_text(log_path, completed.stdout or '')
        append_text(log_path, completed.stderr or '')
        if check and completed.returncode != 0:
            raise ValidationError(f"Command failed ({completed.returncode}): {' '.join(cmd)}")

    try:
        run_logged(['npx', 'playwright', 'install', 'chromium'])
        run_logged(['npx', 'playwright', 'test', 'tests/ai-lab-validation.spec.ts', '--config', 'playwright.config.ts', '--reporter=list'])
        steps.append({'name': 'playwright', 'status': 'ok', 'output': str(log_path.relative_to(out_dir))})
    except Exception as error:  # noqa: BLE001
        steps.append({'name': 'playwright', 'status': 'error', 'error': f'{error}\n{tail_text(log_path)}', 'output': str(log_path.relative_to(out_dir))})


def build_summary(*, out_dir: Path, manifest: dict[str, Any], steps: list[dict[str, Any]], base_url: str, frontend_url: str) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for step in steps:
        counts[step['status']] = counts.get(step['status'], 0) + 1
    return {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'base_url': base_url,
        'frontend_url': frontend_url,
        'output_dir': str(out_dir),
        'steps': steps,
        'step_counts': counts,
        'ai_lab_manifest': manifest,
        'return_to_chat': [
            'run-meta.json', 'frontend-smoke.log', 'summary.json', 'summary.md', 'ai-lab-manifest.json', 'health.json', 'workflows.json',
            'document-library.json', 'runtime-controls.json', 'command-center.json', 'run-history.json', 'artifacts.json',
            'lab-overview.json', 'lab-runtime.json', 'lab-chat.json', 'lab-workflow-inspector.json', 'lab-benchmarks.json',
            'lab-evals.json', 'lab-artifacts.json', 'lab-evidenceops.json', 'backend.log', 'frontend.log', 'playwright.log',
            'screenshots/', 'api/', 'browser/', 'dom/'
        ],
    }


def build_summary_markdown(summary: dict[str, Any]) -> str:
    lines = ['# AI Lab validation summary', '', f"- Generated at: {summary['generated_at']}", f"- Product API: {summary['base_url']}", f"- Frontend: {summary['frontend_url']}", '', '## Steps']
    for step in summary['steps']:
        suffix = f" — {step.get('error')}" if step.get('error') else ''
        lines.append(f"- `{step['name']}`: **{step['status']}**{suffix}")
    lines.extend(['', '## Return these files', *[f'- {item}' for item in summary['return_to_chat']]])
    return '\n'.join(lines) + '\n'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run reproducible AI Lab validation.')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument('--api-url', default=None)
    parser.add_argument('--frontend-url', default=None)
    parser.add_argument('--start-product-api', action='store_true')
    parser.add_argument('--start-frontend', action='store_true')
    parser.add_argument('--run-playwright', action='store_true')
    parser.add_argument('--exercise-live', action='store_true')
    parser.add_argument('--skip-http-smoke', action='store_true')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ensure_directory(Path(args.output_dir).resolve())
    ensure_directory(out_dir / 'screenshots')
    ensure_directory(out_dir / 'api')
    ensure_directory(out_dir / 'browser')
    ensure_directory(out_dir / 'dom')

    requested_backend_host = os.environ.get('PRODUCT_API_SERVER_NAME', '127.0.0.1')
    requested_backend_port = int(os.environ.get('PRODUCT_API_SERVER_PORT', '8011'))
    requested_frontend_port = int(os.environ.get('FRONTEND_DEV_PORT', '8080'))
    reuse_backend = os.environ.get('PRODUCT_API_REUSE_EXISTING', '0') == '1'
    reuse_frontend = os.environ.get('FRONTEND_REUSE_EXISTING', '0') == '1'

    backend_host = requested_backend_host
    backend_port = requested_backend_port
    frontend_port = requested_frontend_port

    base_url = (args.api_url or f'http://{backend_host}:{backend_port}').rstrip('/')
    frontend_url = (args.frontend_url or f'http://127.0.0.1:{frontend_port}').rstrip('/')

    env = os.environ.copy()
    steps: list[dict[str, Any]] = []
    manifest = build_ai_lab_manifest()
    write_json(out_dir / 'ai-lab-manifest.json', manifest)
    handles: list[ProcessHandle] = []

    with managed_processes(handles):
        if args.start_product_api:
            backend_log = out_dir / 'backend.log'
            if reuse_backend and backend_is_compatible(base_url):
                write_text(backend_log, f'Reusing existing compatible Product API at {base_url}\n')
                steps.append({'name': 'start-product-api', 'status': 'ok', 'output': str(backend_log.relative_to(out_dir)), 'reused': True})
            else:
                if port_in_use(backend_port):
                    backend_port = find_free_port()
                    base_url = f'http://{backend_host}:{backend_port}'
                env['PRODUCT_API_SERVER_NAME'] = backend_host
                env['PRODUCT_API_SERVER_PORT'] = str(backend_port)
                env['VITE_PRODUCT_API_BASE_URL'] = base_url
                try:
                    handle = start_background_process(name='product-api', cmd=[sys.executable, str(REPO_ROOT / 'main_product_api.py')], cwd=REPO_ROOT, env=env, log_path=backend_log)
                    handles.append(handle)
                    wait_for_http_or_process_exit(f'{base_url}/health', handle=handle, timeout_s=90)
                    steps.append({'name': 'start-product-api', 'status': 'ok', 'output': str(backend_log.relative_to(out_dir)), 'reused': False, 'base_url': base_url})
                except Exception as error:  # noqa: BLE001
                    steps.append({'name': 'start-product-api', 'status': 'error', 'error': f'{error}\n{tail_text(backend_log)}', 'output': str(backend_log.relative_to(out_dir))})

        if args.start_frontend:
            frontend_log = out_dir / 'frontend.log'
            frontend_url = f'http://127.0.0.1:{frontend_port}' if not args.frontend_url else args.frontend_url.rstrip('/')
            if reuse_frontend and probe_http(frontend_url, timeout_s=1.0):
                write_text(frontend_log, f'Reusing existing frontend at {frontend_url}\n')
                steps.append({'name': 'start-frontend', 'status': 'ok', 'output': str(frontend_log.relative_to(out_dir)), 'reused': True})
            else:
                if port_in_use(frontend_port):
                    frontend_port = find_free_port()
                    frontend_url = f'http://127.0.0.1:{frontend_port}'
                env['FRONTEND_DEV_PORT'] = str(frontend_port)
                env['VITE_PRODUCT_API_BASE_URL'] = base_url
                try:
                    handle = start_background_process(
                        name='frontend',
                        cmd=['node', str(FRONTEND_DIR / 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(frontend_port), '--strictPort'],
                        cwd=FRONTEND_DIR,
                        env=env,
                        log_path=frontend_log,
                    )
                    handles.append(handle)
                    wait_for_http_or_process_exit(frontend_url, handle=handle, timeout_s=45)
                    steps.append({'name': 'start-frontend', 'status': 'ok', 'output': str(frontend_log.relative_to(out_dir)), 'reused': False, 'frontend_url': frontend_url})
                except Exception as error:  # noqa: BLE001
                    steps.append({'name': 'start-frontend', 'status': 'error', 'error': f'{error}\n{tail_text(frontend_log)}', 'output': str(frontend_log.relative_to(out_dir))})

        if not args.skip_http_smoke:
            for name, route in PRODUCT_ENDPOINTS:
                save_json_get(base_url, name, route, out_dir, steps)

        if args.exercise_live:
            try:
                exercise_workflows(base_url, out_dir, steps)
            except Exception as error:  # noqa: BLE001
                steps.append({'name': 'exercise-live', 'status': 'error', 'error': str(error)})

        if args.run_playwright:
            frontend_started_ok = any(step['name'] == 'start-frontend' and step['status'] == 'ok' for step in steps)
            if frontend_started_ok:
                run_playwright(frontend_url, out_dir, env | {'VITE_PRODUCT_API_BASE_URL': base_url}, steps)
            else:
                steps.append({'name': 'playwright', 'status': 'skipped', 'reason': 'Frontend not available.'})

    summary = build_summary(out_dir=out_dir, manifest=manifest, steps=steps, base_url=base_url, frontend_url=frontend_url)
    write_json(out_dir / 'summary.json', summary)
    write_text(out_dir / 'summary.md', build_summary_markdown(summary))
    print(f'AI Lab validation complete. Output directory: {out_dir}')
    for item in summary['return_to_chat']:
        print(f'- {out_dir / item}')


if __name__ == '__main__':
    main()
