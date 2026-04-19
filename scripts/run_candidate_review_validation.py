#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / 'frontend'
DEFAULT_OUTPUT_DIR = REPO_ROOT / '.tmp_candidate_review_validation'
DEFAULT_CORPUS_ROOT = REPO_ROOT / 'data' / 'corpus_revisado'
DEFAULT_CANDIDATE_DOC_NAME = 'Sarah Chen - Senior ML Engineer CV.pdf'
DEFAULT_SUPPORTING_DOC_NAMES = [
    'Hiring Scorecard - Sarah Chen.pdf',
    'Interview Feedback Memo - Sarah Chen.pdf',
    'Senior ML Engineer Role Brief.pdf',
]
API_ENDPOINTS = [
    ('health', '/health'),
    ('workflows', '/api/product/workflows'),
    ('document-library', '/api/product/document-library'),
    ('command-center', '/api/product/command-center'),
    ('run-history', '/api/product/run-history'),
    ('artifacts', '/api/product/artifacts'),
]
WORKFLOW_PAGES = [
    {
        'slug': 'candidate-review',
        'route': '/app/workflows/candidate-review',
        'title': 'Candidate Review',
        'file': 'frontend/src/pages/CandidateReviewPage.tsx',
    },
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


def append_text(path: Path, content: str) -> None:
    ensure_directory(path.parent)
    with path.open('a', encoding='utf-8') as handle:
        handle.write(content)


def tail_text(path: Path, line_count: int = 80) -> str:
    if not path.exists():
        return ''
    return '\n'.join(path.read_text(encoding='utf-8', errors='ignore').splitlines()[-line_count:])


def probe_http(url: str, timeout_s: float = 1.5) -> bool:
    try:
        with urllib_request.urlopen(url, timeout=timeout_s) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def request_json(
    url: str,
    *,
    method: str = 'GET',
    payload: dict[str, Any] | None = None,
    timeout_s: int = 120,
) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    request = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib_error.HTTPError as error:
        body = error.read().decode('utf-8', errors='ignore')
        raise ValidationError(f'HTTP {error.code} for {url}: {body}') from error


@contextmanager
def managed_processes(handles: list[ProcessHandle]):
    try:
        yield
    finally:
        for handle in reversed(handles):
            if handle.reused or handle.process.poll() is not None:
                continue
            try:
                if sys.platform != 'win32':
                    os.killpg(handle.process.pid, signal.SIGTERM)
                else:
                    handle.process.terminate()
            except Exception:
                pass


def start_background_process(
    *,
    name: str,
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    log_path: Path,
) -> ProcessHandle:
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
    return ProcessHandle(name=name, process=subprocess.Popen(cmd, **kwargs), log_path=log_path)


def wait_for_http_or_process_exit(url: str, *, handle: ProcessHandle, timeout_s: int = 240) -> None:
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


def classify_page_source(source_code: str) -> dict[str, Any]:
    uses_product_api = '@/lib/product-api' in source_code or 'useQuery' in source_code or 'fetch(' in source_code
    return {'uses_product_api': uses_product_api, 'effective_source': 'live' if uses_product_api else 'derived'}


def build_validation_manifest() -> dict[str, Any]:
    pages = []
    for entry in WORKFLOW_PAGES:
        source_code = (REPO_ROOT / entry['file']).read_text(encoding='utf-8')
        pages.append({**entry, **classify_page_source(source_code)})
    return {
        'generated_from': 'scripts/run_candidate_review_validation.py',
        'pages': pages,
        'required_artifacts': {
            'root': ['summary.json', 'summary.md', 'validation-manifest.json', 'run-meta.json'],
            'directories': ['api', 'browser', 'dom', 'logs', 'payloads', 'screenshots', 'status', 'traces', 'uploads'],
        },
        'api_endpoints': [{'name': name, 'route': route} for name, route in API_ENDPOINTS],
    }


def save_json_get(base_url: str, name: str, route: str, out_dir: Path, steps: list[dict[str, Any]]) -> None:
    target = out_dir / 'payloads' / f'{name}.json'
    try:
        payload = request_json(f'{base_url}{route}')
        write_json(target, payload)
        steps.append({'name': name, 'status': 'ok', 'output': str(target.relative_to(out_dir))})
    except Exception as error:
        write_json(target, {'ok': False, 'error': str(error)})
        steps.append(
            {
                'name': name,
                'status': 'error',
                'error': str(error),
                'output': str(target.relative_to(out_dir)),
            }
        )


def multipart_upload(url: str, files: list[Path]) -> dict[str, Any]:
    boundary = '----WorkflowSurfaceValidationBoundary'
    body = bytearray()
    for path in files:
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(
            (
                f'Content-Disposition: form-data; name="files"; filename="{path.name}"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n'
            ).encode('utf-8')
        )
        body.extend(path.read_bytes())
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    request = urllib_request.Request(
        url,
        data=bytes(body),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST',
    )
    with urllib_request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode('utf-8'))


def load_document_library(base_url: str) -> dict[str, Any]:
    return request_json(f'{base_url}/api/product/document-library')


def find_named_files(root: Path, filenames: list[str]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not root.exists():
        return found
    wanted = set(filenames)
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if path.name in wanted and path.name not in found:
            found[path.name] = path
            if len(found) == len(wanted):
                break
    return found


def resolve_candidate_documents(corpus_root: Path, candidate_doc_name: str, supporting_doc_names: list[str]) -> list[Path]:
    filenames = [candidate_doc_name, *supporting_doc_names]
    discovered = find_named_files(corpus_root, filenames)
    return [discovered[name] for name in filenames if name in discovered]


def wait_for_documents(base_url: str, target_names: list[str], out_dir: Path) -> dict[str, Any]:
    deadline = time.time() + 360
    while time.time() < deadline:
        library = load_document_library(base_url)
        write_json(out_dir / 'uploads' / 'document-library-latest.json', library)
        indexed_names = {
            str(item.get('name') or '')
            for item in library.get('documents') or []
            if str(item.get('status') or '').lower() in {'indexed', 'warning'}
        }
        if all(name in indexed_names for name in target_names):
            return library
        time.sleep(2)
    raise ValidationError('Timed out waiting for curated docs to index.')


def _pretty_repo_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def ensure_documents(
    base_url: str,
    out_dir: Path,
    steps: list[dict[str, Any]],
    *,
    corpus_root: Path,
    candidate_doc_name: str,
    supporting_doc_names: list[str],
) -> dict[str, Any]:
    library_before = load_document_library(base_url)
    write_json(out_dir / 'uploads' / 'document-library-before.json', library_before)
    available_names = {str(item.get('name') or '') for item in library_before.get('documents') or []}
    resolved_files = resolve_candidate_documents(corpus_root, candidate_doc_name, supporting_doc_names)
    resolved_names = [path.name for path in resolved_files]
    if candidate_doc_name not in resolved_names and candidate_doc_name not in available_names:
        raise ValidationError(
            f'Could not find `{candidate_doc_name}` under `{corpus_root}` and it is not already indexed in the document library.'
        )

    missing_files = [path for path in resolved_files if path.name not in available_names]
    fixture_info = {
        'corpus_root': str(corpus_root),
        'candidate_doc_name': candidate_doc_name,
        'supporting_doc_names': supporting_doc_names,
        'resolved_files': [_pretty_repo_path(path) for path in resolved_files],
        'missing_files': [_pretty_repo_path(path) for path in missing_files],
    }
    write_json(out_dir / 'uploads' / 'fixture-selection.json', fixture_info)

    if missing_files:
        upload_response = multipart_upload(f'{base_url}/api/product/upload-documents', missing_files)
        write_json(out_dir / 'uploads' / 'upload-response.json', upload_response)
        steps.append(
            {
                'name': 'upload-documents',
                'status': 'ok',
                'count': len(missing_files),
                'output': 'uploads/upload-response.json',
            }
        )
    else:
        write_json(
            out_dir / 'uploads' / 'upload-response.json',
            {'ok': True, 'uploaded_count': 0, 'message': 'No upload needed.'},
        )
        steps.append({'name': 'upload-documents', 'status': 'ok', 'count': 0, 'output': 'uploads/upload-response.json'})

    target_names = [candidate_doc_name, *[name for name in supporting_doc_names if name in resolved_names or name in available_names]]
    library_after = wait_for_documents(base_url, target_names, out_dir)
    write_json(out_dir / 'uploads' / 'document-library-after.json', library_after)
    return {
        'before': library_before,
        'after': library_after,
        'uploaded_files': [_pretty_repo_path(path) for path in missing_files],
        'candidate_doc_name': candidate_doc_name,
        'corpus_root': str(corpus_root),
        'resolved_files': fixture_info['resolved_files'],
    }


def find_document_id(library: dict[str, Any], document_name: str) -> str:
    for document in library.get('documents') or []:
        if str(document.get('name') or '') == document_name and str(document.get('status') or '').lower() in {'indexed', 'warning'}:
            return str(document.get('document_id') or '')
    raise ValidationError(f'Could not resolve document id for `{document_name}`.')


def maybe_generate_deck(base_url: str, out_dir: Path, workflow_slug: str, response: dict[str, Any], steps: list[dict[str, Any]]) -> None:
    result = response.get('result')
    if not isinstance(result, dict) or not result.get('deck_available'):
        return
    payload = {'result': result, 'run_id': response.get('run_id')}
    filename = out_dir / 'payloads' / f'{workflow_slug}-generate-deck.json'
    try:
        deck_response = request_json(f'{base_url}/api/product/generate-deck', method='POST', payload=payload, timeout_s=300)
        write_json(filename, deck_response)
        steps.append({'name': f'{workflow_slug}-generate-deck', 'status': 'ok', 'output': str(filename.relative_to(out_dir))})
    except Exception as error:
        write_json(filename, {'ok': False, 'error': str(error), 'request': payload})
        steps.append(
            {
                'name': f'{workflow_slug}-generate-deck',
                'status': 'error',
                'error': str(error),
                'output': str(filename.relative_to(out_dir)),
            }
        )


def exercise_live_workflows(
    base_url: str,
    out_dir: Path,
    library: dict[str, Any],
    steps: list[dict[str, Any]],
    *,
    candidate_doc_name: str,
) -> dict[str, Any]:
    candidate_doc_id = find_document_id(library, candidate_doc_name)
    candidate_preview = request_json(
        f'{base_url}/api/product/grounding-preview?'
        + urllib_parse.urlencode(
            {
                'workflow_id': 'candidate_review',
                'document_id': candidate_doc_id,
                'strategy': 'document_scan',
                'input_text': 'Evaluate this CV for a senior AI engineer role and highlight strengths, gaps and interview focus areas.',
            }
        )
    )
    write_json(out_dir / 'payloads' / 'candidate-review-grounding-preview.json', candidate_preview)
    candidate_payload = {
        'workflow_id': 'candidate_review',
        'document_ids': [candidate_doc_id],
        'input_text': 'Evaluate this CV for a senior AI engineer role and highlight strengths, watchouts, seniority signals and interview focus areas.',
        'context_strategy': 'document_scan',
        'context_window_mode': 'auto',
        'use_document_context': True,
    }
    candidate_response = request_json(f'{base_url}/api/product/run-workflow', method='POST', payload=candidate_payload, timeout_s=300)
    write_json(out_dir / 'payloads' / 'candidate-review-workflow.json', candidate_response)
    steps.append({'name': 'candidate-review-workflow', 'status': 'ok', 'output': 'payloads/candidate-review-workflow.json'})
    maybe_generate_deck(base_url, out_dir, 'candidate-review', candidate_response, steps)
    return {'candidate_review': candidate_response}


def run_playwright(
    frontend_url: str,
    out_dir: Path,
    env: dict[str, str],
    steps: list[dict[str, Any]],
    *,
    candidate_doc_name: str,
) -> None:
    log_path = out_dir / 'logs' / 'playwright.log'
    playwright_env = env | {
        'PLAYWRIGHT_BASE_URL': frontend_url,
        'CANDIDATE_REVIEW_OUTPUT_DIR': str(out_dir),
        'PLAYWRIGHT_ARTIFACT_DIR': str(out_dir / 'playwright-artifacts'),
        'WORKFLOW_SURFACE_CANDIDATE_DOC_NAME': candidate_doc_name,
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
        run_logged(['npx', 'playwright', 'test', 'tests/candidate-review-validation.spec.ts', '--config', 'playwright.config.ts', '--reporter=list'])
        steps.append({'name': 'playwright', 'status': 'ok', 'output': str(log_path.relative_to(out_dir))})
    except Exception as error:
        steps.append({'name': 'playwright', 'status': 'error', 'error': f'{error}\n{tail_text(log_path)}', 'output': str(log_path.relative_to(out_dir))})


def collect_page_statuses(out_dir: Path) -> list[dict[str, Any]]:
    statuses = []
    for path in sorted((out_dir / 'status').glob('*.json')):
        try:
            statuses.append(json.loads(path.read_text(encoding='utf-8')))
        except Exception as error:
            statuses.append({'slug': path.stem, 'status': 'failed', 'error': str(error)})
    return statuses


def collect_page_artifact_inventory(out_dir: Path) -> dict[str, Any]:
    inventory = {}
    for page in WORKFLOW_PAGES:
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


def derive_overall_status(steps: list[dict[str, Any]], page_statuses: list[dict[str, Any]]) -> str:
    if any(step.get('status') == 'error' for step in steps):
        return 'degraded'
    page_values = [str(page.get('status') or '').lower() for page in page_statuses]
    if any(value == 'failed' for value in page_values):
        return 'failed'
    if any(value == 'degraded' for value in page_values):
        return 'degraded'
    if page_values and all(value == 'passed' for value in page_values):
        return 'passed'
    return 'partial'


def build_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        '# Candidate Review validation summary',
        '',
        f"- overall_status: **{summary.get('overall_status', 'unknown')}**",
        f"- generated_at: `{summary.get('generated_at', 'unknown')}`",
        f"- frontend_url: `{summary.get('frontend_url', 'n/a')}`",
        f"- product_api_url: `{summary.get('product_api_url', 'n/a')}`",
        f"- ollama_model: `{summary.get('ollama_model', 'n/a')}`",
        f"- corpus_root: `{summary.get('corpus_root', 'n/a')}`",
        '',
        '## Pages',
    ]
    for page in summary.get('pages', []):
        lines.append(f"- `{page.get('slug', 'unknown')}`: **{page.get('status', 'unknown')}**")
    lines.append('')
    lines.append('## Step log')
    for step in summary.get('steps', []):
        suffix = f" — {step.get('output')}" if step.get('output') else ''
        if step.get('error'):
            suffix += f" — {step.get('error')}"
        lines.append(f"- {step.get('name')}: {step.get('status')}{suffix}")
    lines.append('')
    return '\n'.join(lines)


def zip_output_dir(out_dir: Path) -> Path:
    zip_path = out_dir.with_suffix('.zip')
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(out_dir.rglob('*')):
            if file.is_file():
                archive.write(file, arcname=str(file.relative_to(out_dir.parent)))
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate the Candidate Review surface and capture artifacts.')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument('--product-api-url', default=os.environ.get('VITE_PRODUCT_API_BASE_URL') or 'http://127.0.0.1:8011')
    parser.add_argument('--frontend-url', default=os.environ.get('PLAYWRIGHT_BASE_URL') or 'http://127.0.0.1:8080')
    parser.add_argument('--product-api-port', type=int, default=int(os.environ.get('PRODUCT_API_SERVER_PORT') or 8011))
    parser.add_argument('--frontend-port', type=int, default=int(os.environ.get('FRONTEND_DEV_PORT') or 8080))
    parser.add_argument('--start-product-api', action='store_true')
    parser.add_argument('--start-frontend', action='store_true')
    parser.add_argument('--run-playwright', action='store_true')
    parser.add_argument('--exercise-live', action='store_true')
    parser.add_argument('--python-bin', default=os.environ.get('PYTHON_BIN') or sys.executable)
    parser.add_argument('--corpus-root', default=os.environ.get('CANDIDATE_REVIEW_CORPUS_ROOT') or str(DEFAULT_CORPUS_ROOT))
    parser.add_argument('--candidate-doc-name', default=os.environ.get('CANDIDATE_REVIEW_CANDIDATE_DOC_NAME') or DEFAULT_CANDIDATE_DOC_NAME)
    parser.add_argument('--ollama-model', default=os.environ.get('OLLAMA_MODEL') or 'nemotron:30b')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir).resolve()
    corpus_root = Path(args.corpus_root).resolve()
    for child in [
        out_dir,
        out_dir / 'api',
        out_dir / 'browser',
        out_dir / 'dom',
        out_dir / 'logs',
        out_dir / 'payloads',
        out_dir / 'screenshots',
        out_dir / 'status',
        out_dir / 'traces',
        out_dir / 'uploads',
        out_dir / 'playwright-artifacts',
    ]:
        ensure_directory(child)

    base_url = args.product_api_url.rstrip('/')
    frontend_url = args.frontend_url.rstrip('/')
    env = os.environ.copy()
    env['VITE_PRODUCT_API_BASE_URL'] = base_url
    env['PRODUCT_API_SERVER_PORT'] = str(args.product_api_port)
    env['FRONTEND_DEV_PORT'] = str(args.frontend_port)
    env['CANDIDATE_REVIEW_CORPUS_ROOT'] = str(corpus_root)
    env['CANDIDATE_REVIEW_CANDIDATE_DOC_NAME'] = args.candidate_doc_name
    env['OLLAMA_MODEL'] = args.ollama_model
    env['OLLAMA_AVAILABLE_MODELS'] = env.get('OLLAMA_AVAILABLE_MODELS') or args.ollama_model

    steps: list[dict[str, Any]] = []
    handles: list[ProcessHandle] = []
    write_json(out_dir / 'validation-manifest.json', build_validation_manifest())
    write_json(
        out_dir / 'run-meta.json',
        {
            'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'cwd': os.getcwd(),
            'command': ' '.join(sys.argv),
            'ollama_model': args.ollama_model,
            'corpus_root': str(corpus_root),
            'candidate_doc_name': args.candidate_doc_name,
        },
    )

    with managed_processes(handles):
        if args.start_product_api:
            if probe_http(f'{base_url}/health'):
                handles.append(
                    ProcessHandle(
                        name='product-api',
                        process=subprocess.Popen(['true']),
                        log_path=out_dir / 'logs' / 'product-api-reused.log',
                        reused=True,
                    )
                )
                steps.append({'name': 'product-api', 'status': 'ok', 'detail': 'reused existing backend'})
            else:
                handle = start_background_process(
                    name='product-api',
                    cmd=[args.python_bin, 'main_product_api.py'],
                    cwd=REPO_ROOT,
                    env=env,
                    log_path=out_dir / 'logs' / 'backend.log',
                )
                handles.append(handle)
                wait_for_http_or_process_exit(f'{base_url}/health', handle=handle)
                steps.append({'name': 'product-api', 'status': 'ok', 'output': 'logs/backend.log'})

        if args.start_frontend:
            if probe_http(frontend_url):
                handles.append(
                    ProcessHandle(
                        name='frontend',
                        process=subprocess.Popen(['true']),
                        log_path=out_dir / 'logs' / 'frontend-reused.log',
                        reused=True,
                    )
                )
                steps.append({'name': 'frontend', 'status': 'ok', 'detail': 'reused existing frontend'})
            else:
                frontend_env = env.copy()
                frontend_env['PRODUCT_API_REUSE_EXISTING'] = '1'
                handle = start_background_process(
                    name='frontend',
                    cmd=['npm', 'run', 'dev'],
                    cwd=FRONTEND_DIR,
                    env=frontend_env,
                    log_path=out_dir / 'logs' / 'frontend.log',
                )
                handles.append(handle)
                wait_for_http_or_process_exit(frontend_url, handle=handle)
                steps.append({'name': 'frontend', 'status': 'ok', 'output': 'logs/frontend.log'})

        for name, route in API_ENDPOINTS:
            save_json_get(base_url, name, route, out_dir, steps)

        document_sync = ensure_documents(
            base_url,
            out_dir,
            steps,
            corpus_root=corpus_root,
            candidate_doc_name=args.candidate_doc_name,
            supporting_doc_names=DEFAULT_SUPPORTING_DOC_NAMES,
        )

        live_outputs: dict[str, Any] = {}
        if args.exercise_live:
            live_outputs = exercise_live_workflows(
                base_url,
                out_dir,
                document_sync['after'],
                steps,
                candidate_doc_name=document_sync['candidate_doc_name'],
            )

        if args.run_playwright:
            run_playwright(
                frontend_url,
                out_dir,
                env,
                steps,
                candidate_doc_name=document_sync['candidate_doc_name'],
            )

    page_statuses = collect_page_statuses(out_dir)
    summary = {
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'overall_status': derive_overall_status(steps, page_statuses),
        'product_api_url': base_url,
        'frontend_url': frontend_url,
        'toolchain_issues': [],
        'steps': steps,
        'pages': page_statuses,
        'artifact_inventory': collect_page_artifact_inventory(out_dir),
        'document_sync': {
            'uploaded_files': document_sync.get('uploaded_files', []),
            'document_count_after': len(document_sync.get('after', {}).get('documents') or []),
            'resolved_files': document_sync.get('resolved_files', []),
            'candidate_doc_name': document_sync.get('candidate_doc_name'),
        },
        'live_outputs': {'candidate_review_run_id': (live_outputs.get('candidate_review') or {}).get('run_id')},
        'ollama_model': args.ollama_model,
        'corpus_root': str(corpus_root),
    }
    write_json(out_dir / 'summary.json', summary)
    write_text(out_dir / 'summary.md', build_summary_markdown(summary))
    zip_path = zip_output_dir(out_dir)
    write_json(out_dir / 'status' / 'zip.json', {'zip_path': str(zip_path)})
    print(
        json.dumps(
            {
                'ok': True,
                'output_dir': str(out_dir),
                'zip_path': str(zip_path),
                'overall_status': summary['overall_status'],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
