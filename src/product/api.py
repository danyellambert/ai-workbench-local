from __future__ import annotations

import json
import mimetypes
from pathlib import Path
import re
import threading
import time
from dataclasses import dataclass, replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.app.product_bootstrap import ProductBootstrap, build_product_bootstrap
from src.config import ProductApiSettings, get_product_api_settings
from src.rag.loaders import load_document
from src.product.command_center import (
    build_product_artifact_payload,
    build_product_command_center_payload,
    build_product_document_library_payload,
    build_product_run_history_payload,
    build_product_workflow_history_entry,
)
from src.product.ingestion_jobs import (
    complete_product_upload_job,
    create_product_upload_job,
    fail_product_upload_job,
    get_product_upload_job,
    mark_product_upload_job_running,
    update_product_upload_job_stage,
)
from src.product.action_plan_presenter import build_action_plan_view
from src.product.models import ProductWorkflowRequest, ProductWorkflowResult
from src.product.presenters import build_document_review_view, build_policy_comparison_view
from src.product.service import (
    build_grounding_preview,
    build_product_workflow_frontend_contract,
    delete_product_documents,
    generate_product_workflow_deck,
    publish_product_workflow_to_trello,
    index_loaded_documents,
    list_product_documents,
    run_product_workflow,
)
from src.services.preferences import (
    apply_preferences_to_product_request,
    build_preferences_payload,
    test_preferences_connection,
    update_preferences_connection_credential,
    update_preferences_payload,
)
from src.services.runtime_controls import (
    apply_runtime_controls_to_product_request,
    build_effective_rag_settings,
    build_runtime_controls_payload,
    update_runtime_controls_payload,
)
from src.storage.product_workflow_history import append_product_workflow_history_entry
from src.storage.runtime_paths import get_artifact_root, get_product_workflow_history_path


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _html_bytes(content: str) -> bytes:
    return content.encode("utf-8")


def _resolve_product_artifact_path(*, bootstrap: ProductBootstrap, raw_path: str) -> Path:
    candidate = Path(str(raw_path or "").strip()).expanduser()
    if not str(candidate).strip():
        raise ValueError("Artifact path is required.")

    resolved = candidate.resolve(strict=False)
    allowed_roots = [
        get_artifact_root(bootstrap.workspace_root).resolve(strict=False),
        Path(bootstrap.presentation_export_settings.local_artifact_dir).resolve(strict=False),
    ]
    if not any(resolved.is_relative_to(root) for root in allowed_roots):
        raise ValueError("Artifact path is outside the allowed artifact roots.")
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"Artifact not found: {resolved}")
    return resolved


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length") or 0)
    if content_length <= 0:
        return {}
    raw = handler.rfile.read(content_length)
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON payload: {error}") from error
    return payload if isinstance(payload, dict) else {}


@dataclass(frozen=True)
class _ApiUploadedFile:
    name: str
    content: bytes

    def getvalue(self) -> bytes:
        return self.content


def _extract_multipart_boundary(content_type: str) -> str:
    for part in str(content_type or "").split(";"):
        normalized = part.strip()
        if normalized.lower().startswith("boundary="):
            return normalized.split("=", 1)[1].strip().strip('"')
    raise ValueError("Multipart boundary is missing from Content-Type header.")


def _read_multipart_files(handler: BaseHTTPRequestHandler, *, field_name: str = "files") -> list[_ApiUploadedFile]:
    content_type = str(handler.headers.get("Content-Type") or "")
    if "multipart/form-data" not in content_type.lower():
        raise ValueError("Expected multipart/form-data payload.")

    content_length = int(handler.headers.get("Content-Length") or 0)
    if content_length <= 0:
        return []

    raw_body = handler.rfile.read(content_length)
    boundary = _extract_multipart_boundary(content_type)
    delimiter = f"--{boundary}".encode("utf-8")
    allowed_field_names = {field_name, "file", "documents"}
    uploaded_files: list[_ApiUploadedFile] = []

    for part in raw_body.split(delimiter):
        candidate = part.strip()
        if not candidate or candidate == b"--":
            continue

        if candidate.endswith(b"--"):
            candidate = candidate[:-2]
        if candidate.startswith(b"\r\n"):
            candidate = candidate[2:]

        header_blob, separator, body = candidate.partition(b"\r\n\r\n")
        if not separator:
            continue

        body = body[:-2] if body.endswith(b"\r\n") else body
        headers: dict[str, str] = {}
        for line in header_blob.decode("utf-8", errors="ignore").split("\r\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

        disposition = headers.get("content-disposition", "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        filename_match = re.search(r'filename="([^"]+)"', disposition)
        field_value = name_match.group(1).strip() if name_match else ""
        filename = filename_match.group(1).strip() if filename_match else ""
        if field_value not in allowed_field_names or not filename:
            continue

        uploaded_files.append(_ApiUploadedFile(name=filename, content=body))
    return uploaded_files


def _run_product_upload_job(
    *,
    job_id: str,
    uploaded_files: list[_ApiUploadedFile],
    bootstrap: ProductBootstrap,
) -> None:
    try:
        mark_product_upload_job_running(job_id, message="Running ingestion pipeline.")
        total_documents = len(uploaded_files)
        loaded_documents = []
        effective_rag_settings = build_effective_rag_settings(default_settings=bootstrap.rag_settings, workspace_root=bootstrap.workspace_root)
        upload_rag_settings = replace(
            effective_rag_settings,
            pdf_extraction_mode="hybrid",
            pdf_docling_enabled=True,
            pdf_docling_ocr_enabled=True,
            pdf_docling_force_full_page_ocr=False,
            pdf_docling_picture_description=False,
            pdf_baseline_chars_per_page_threshold=40,
            pdf_min_text_coverage_ratio=0.1,
            pdf_suspicious_pages_trigger_full_docling_ratio=2.0,
            pdf_suspicious_pages_trigger_full_docling_min_count=999,
            pdf_max_selective_docling_pages=4,
            pdf_evidence_pipeline_enabled=False,
            pdf_evidence_pipeline_use_for_cv_like=False,
            pdf_evidence_pipeline_use_for_strong_scan_like=False,
            pdf_ocr_fallback_enabled=False,
            pdf_scan_image_ocr_enabled=False,
        )
        for index, uploaded in enumerate(uploaded_files, start=1):
            update_product_upload_job_stage(
                job_id,
                "extraction",
                status="running",
                detail=f"Extracting {uploaded.name} ({index}/{total_documents}).",
                metadata={
                    "document_name": uploaded.name,
                    "current_document": index,
                    "total_documents": total_documents,
                    "progress_pct": 0.0,
                },
            )
            def extraction_progress(payload: dict[str, object] | None, *, document_name: str = uploaded.name, current_document: int = index) -> None:
                metadata = dict(payload or {})
                detail = str(metadata.pop("detail", "")).strip() or f"Extracting {document_name} ({current_document}/{total_documents})."
                update_product_upload_job_stage(
                    job_id,
                    "extraction",
                    status="running",
                    detail=detail,
                    metadata={
                        "document_name": document_name,
                        "current_document": current_document,
                        "total_documents": total_documents,
                        **metadata,
                    },
                )

            loaded_document = load_document(uploaded, upload_rag_settings, progress_callback=extraction_progress)
            loaded_documents.append(loaded_document)
            update_product_upload_job_stage(
                job_id,
                "extraction",
                status="completed",
                detail=f"{index}/{total_documents} document(s) extracted.",
                metadata={
                    "document_name": uploaded.name,
                    "current_document": index,
                    "total_documents": total_documents,
                    "progress_pct": 100.0,
                },
            )

        indexed_documents, index_status = index_loaded_documents(
            loaded_documents,
            rag_settings=effective_rag_settings,
            provider_registry=bootstrap.provider_registry,
            progress_callback=lambda stage_key, payload: update_product_upload_job_stage(
                job_id,
                stage_key,
                status=str(payload.get("status") or "running"),
                detail=str(payload.get("detail") or "").strip() or None,
                metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
            ),
        )
        document_library = build_product_document_library_payload(bootstrap)
        message = index_status.get("message") if isinstance(index_status, dict) else None
        complete_product_upload_job(
            job_id,
            message=message or f"{len(uploaded_files)} document(s) indexed successfully.",
            indexed_documents=[item.model_dump(mode="json") for item in indexed_documents],
            document_library=document_library,
            index_status=index_status if isinstance(index_status, dict) else {},
        )
    except Exception as error:  # pragma: no cover - defensive background job handling
        fail_product_upload_job(job_id, error_message=str(error))


def start_product_upload_job(
    *,
    bootstrap: ProductBootstrap,
    uploaded_files: list[_ApiUploadedFile],
    ignored_count: int = 0,
) -> dict[str, Any]:
    job_payload = create_product_upload_job(uploaded_count=len(uploaded_files), ignored_count=ignored_count)
    thread = threading.Thread(
        target=_run_product_upload_job,
        kwargs={
            "job_id": str(job_payload.get("job_id") or ""),
            "uploaded_files": list(uploaded_files),
            "bootstrap": bootstrap,
        },
        daemon=True,
    )
    thread.start()
    return job_payload


class ProductApiHandler(BaseHTTPRequestHandler):
    bootstrap: ProductBootstrap
    settings: ProductApiSettings

    def _send_html(self, status: int, html: str) -> None:
        body = _html_bytes(html)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if getattr(self, "settings", None) and self.settings.allow_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: object) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if getattr(self, "settings", None) and self.settings.allow_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        body = path.read_bytes()
        content_type, _ = mimetypes.guess_type(str(path))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
        if getattr(self, "settings", None) and self.settings.allow_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        if self.settings.allow_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        if path == "/" and self.settings.enable_web_frontend:
            self._send_html(
                HTTPStatus.OK,
                """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AI Workbench Product API</title>
    <style>
      body { font-family: Inter, system-ui, sans-serif; background: #0b1321; color: #e5f2ff; margin: 0; padding: 32px; }
      .card { background: #111b2e; border: 1px solid #28415f; border-radius: 16px; padding: 20px; margin-bottom: 16px; }
      code { color: #8de2ff; }
      a { color: #8de2ff; }
      ul { line-height: 1.6; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>AI Workbench Product API</h1>
      <p>HTTP surface for <strong>Decision workflows grounded in documents</strong>.</p>
      <ul>
        <li><code>GET /health</code> — service health</li>
        <li><code>GET /api/product/workflows</code> — workflow catalog contract</li>
        <li><code>GET /api/product/documents</code> — indexed document catalog</li>
        <li><code>GET /api/product/document-library</code> — aggregated document library payload</li>
        <li><code>GET /api/product/upload-jobs/&lt;job_id&gt;</code> — ingestion pipeline progress for uploads</li>
        <li><code>POST /api/product/upload-documents</code> — upload and index documents into the product corpus</li>
        <li><code>POST /api/product/delete-documents</code> — remove indexed documents from the product corpus</li>
        <li><code>GET /api/product/command-center</code> — aggregated command center payload</li>
        <li><code>GET /api/product/run-history</code> — recent workflow execution history</li>
        <li><code>GET /api/product/artifacts</code> — recent generated artifacts</li>
        <li><code>GET /api/product/artifact?path=...</code> — serve a generated artifact via HTTP</li>
        <li><code>GET /api/product/grounding-preview</code> — preview grounded context</li>
        <li><code>POST /api/product/run-workflow</code> — execute a product workflow</li>
        <li><code>POST /api/product/generate-deck</code> — generate workflow executive deck</li>
      </ul>
      <p>Primary business UX remains the Gradio product surface. This HTTP layer prepares the split toward a more web-oriented app architecture.</p>
    </div>
  </body>
</html>
                """.strip(),
            )
            return

        if path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "product_api",
                    "product_headline": "Decision workflows grounded in documents",
                    "workflow_count": len(self.bootstrap.workflow_catalog),
                },
            )
            return

        if path == "/api/product/workflows":
            self._send_json(HTTPStatus.OK, build_product_workflow_frontend_contract())
            return

        if path == "/api/product/documents":
            documents = [item.model_dump(mode="json") for item in list_product_documents(self.bootstrap.rag_settings)]
            self._send_json(HTTPStatus.OK, {"ok": True, "documents": documents})
            return

        if path == "/api/product/document-library":
            self._send_json(HTTPStatus.OK, build_product_document_library_payload(self.bootstrap))
            return

        if path.startswith("/api/product/upload-jobs/"):
            job_id = path.rsplit("/", 1)[-1].strip()
            payload = get_product_upload_job(job_id)
            if payload is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Upload job not found."})
                return
            self._send_json(HTTPStatus.OK, payload)
            return

        if path == "/api/product/command-center":
            self._send_json(HTTPStatus.OK, build_product_command_center_payload(self.bootstrap))
            return

        if path == "/api/product/run-history":
            self._send_json(HTTPStatus.OK, build_product_run_history_payload(self.bootstrap, recent_limit=100))
            return

        if path == "/api/product/artifacts":
            self._send_json(HTTPStatus.OK, build_product_artifact_payload(self.bootstrap, recent_limit=100))
            return

        if path == "/api/product/artifact":
            try:
                raw_path = str((query.get("path") or [""])[0])
                artifact_path = _resolve_product_artifact_path(bootstrap=self.bootstrap, raw_path=raw_path)
                self._send_file(artifact_path)
            except FileNotFoundError as error:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": str(error)})
            except Exception as error:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/product/grounding-preview":
            workflow_id = str((query.get("workflow_id") or [self.bootstrap.product_settings.default_workflow])[0])
            strategy = str((query.get("strategy") or ["document_scan"])[0])
            document_ids = [item for item in (query.get("document_id") or []) if item]
            input_text = str((query.get("input_text") or [""])[0])
            workflow_definition = self.bootstrap.workflow_catalog.get(workflow_id)
            query_text = input_text.strip() or (workflow_definition.headline if workflow_definition else "workflow preview")
            preview = build_grounding_preview(query=query_text, document_ids=document_ids, strategy=strategy)
            self._send_json(HTTPStatus.OK, {"ok": True, "preview": preview.model_dump(mode="json")})
            return

        if path == "/api/runtime/controls":
            self._send_json(HTTPStatus.OK, build_runtime_controls_payload(self.bootstrap))
            return

        if path == "/api/preferences":
            self._send_json(HTTPStatus.OK, build_preferences_payload(self.bootstrap))
            return

        self._not_found()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/product/upload-documents":
            try:
                uploaded_files = _read_multipart_files(self)
                if not uploaded_files:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "No files were provided for upload."})
                    return

                max_upload_files = int(getattr(self.bootstrap.product_settings, "max_upload_files", 5) or 5)
                selected_files = uploaded_files[:max_upload_files]
                ignored_count = max(0, len(uploaded_files) - len(selected_files))
                job_payload = start_product_upload_job(
                    bootstrap=self.bootstrap,
                    uploaded_files=selected_files,
                    ignored_count=ignored_count,
                )
                self._send_json(HTTPStatus.OK, job_payload)
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        try:
            payload = _read_json_body(self)
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/product/delete-documents":
            try:
                raw_document_ids = payload.get("document_ids") if isinstance(payload.get("document_ids"), list) else []
                document_ids = [str(item).strip() for item in raw_document_ids if str(item).strip()]
                if not document_ids:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "No document ids were provided for deletion."})
                    return
                documents_after, delete_status = delete_product_documents(document_ids, rag_settings=self.bootstrap.rag_settings)
                document_library = build_product_document_library_payload(self.bootstrap)
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "removed_count": int(delete_status.get("removed_count") or 0),
                        "removed_document_ids": delete_status.get("removed_document_ids") or document_ids,
                        "message": delete_status.get("message") or "Document(s) removed successfully.",
                        "sync_status": delete_status.get("sync_status") if isinstance(delete_status, dict) else None,
                        "documents": [item.model_dump(mode="json") for item in documents_after],
                        "document_library": document_library,
                    },
                )
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/product/run-workflow":
            try:
                request = ProductWorkflowRequest.model_validate(payload)
                request = apply_runtime_controls_to_product_request(
                    request,
                    self.bootstrap,
                    explicit_fields=set(payload.keys()),
                )
                request = apply_preferences_to_product_request(
                    self.bootstrap,
                    request,
                    explicit_fields=set(payload.keys()),
                )
                try:
                    document_lookup = {
                        item.document_id: item.name
                        for item in list_product_documents(self.bootstrap.rag_settings)
                    }
                except Exception:
                    document_lookup = {}
                started_at = time.perf_counter()
                result = run_product_workflow(request)
                append_product_workflow_history_entry(
                    get_product_workflow_history_path(self.bootstrap.workspace_root),
                    build_product_workflow_history_entry(
                        request=request,
                        document_lookup=document_lookup,
                        result=result,
                        duration_s=time.perf_counter() - started_at,
                    ),
                )
                response_payload: dict[str, Any] = {"ok": True, "result": result.model_dump(mode="json")}
                if request.workflow_id == "document_review":
                    response_payload["result_view"] = build_document_review_view(result)
                if request.workflow_id == "policy_contract_comparison":
                    response_payload["comparison_view"] = build_policy_comparison_view(result)
                if request.workflow_id == "action_plan_evidence_review":
                    response_payload["action_plan_view"] = build_action_plan_view(result)
                self._send_json(HTTPStatus.OK, response_payload)
            except Exception as error:  # pragma: no cover - defensive API surface
                if "request" in locals():
                    try:
                        append_product_workflow_history_entry(
                            get_product_workflow_history_path(self.bootstrap.workspace_root),
                            build_product_workflow_history_entry(
                                request=request,
                                document_lookup=document_lookup if "document_lookup" in locals() else {},
                                result=None,
                                duration_s=time.perf_counter() - started_at if "started_at" in locals() else 0.0,
                                error_message=str(error),
                            ),
                        )
                    except Exception:
                        pass
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/product/generate-deck":
            try:
                result_payload = payload.get("result") if isinstance(payload.get("result"), dict) else payload
                product_result = ProductWorkflowResult.model_validate(result_payload)
                export_result, artifacts = generate_product_workflow_deck(
                    product_result,
                    settings=self.bootstrap.presentation_export_settings,
                    workspace_root=self.bootstrap.workspace_root,
                )
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "export_result": export_result,
                        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
                    },
                )
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/product/publish-trello":
            try:
                result_payload = payload.get("result") if isinstance(payload.get("result"), dict) else payload
                product_result = ProductWorkflowResult.model_validate(result_payload)
                trello_result = publish_product_workflow_to_trello(product_result, dry_run=False)
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        **trello_result,
                    },
                )
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path.startswith("/api/preferences/connections/") and path.endswith("/test"):
            try:
                connection_id = path.removeprefix("/api/preferences/connections/").removesuffix("/test").strip("/")
                if not connection_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Connection id is required."})
                    return
                self._send_json(HTTPStatus.OK, test_preferences_connection(self.bootstrap, connection_id))
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path.startswith("/api/preferences/connections/") and path.endswith("/credential"):
            try:
                connection_id = path.removeprefix("/api/preferences/connections/").removesuffix("/credential").strip("/")
                if not connection_id:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "Connection id is required."})
                    return
                api_key = str(payload.get("api_key") or "") if isinstance(payload, dict) else ""
                self._send_json(HTTPStatus.OK, update_preferences_connection_credential(self.bootstrap, connection_id, api_key))
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        self._not_found()

    def do_PATCH(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            payload = _read_json_body(self)
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/runtime/controls":
            try:
                self._send_json(HTTPStatus.OK, update_runtime_controls_payload(self.bootstrap, payload))
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/preferences":
            try:
                self._send_json(HTTPStatus.OK, update_preferences_payload(self.bootstrap, payload))
            except Exception as error:  # pragma: no cover - defensive API surface
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        self._not_found()


def build_product_api_server(
    *,
    bootstrap: ProductBootstrap | None = None,
    settings: ProductApiSettings | None = None,
) -> ThreadingHTTPServer:
    resolved_bootstrap = bootstrap or build_product_bootstrap()
    resolved_settings = settings or get_product_api_settings()

    handler_class = type(
        "ConfiguredProductApiHandler",
        (ProductApiHandler,),
        {"bootstrap": resolved_bootstrap, "settings": resolved_settings},
    )
    return ReusableThreadingHTTPServer((resolved_settings.server_name, resolved_settings.server_port), handler_class)


def serve_product_api(
    *,
    bootstrap: ProductBootstrap | None = None,
    settings: ProductApiSettings | None = None,
) -> ThreadingHTTPServer:
    server = build_product_api_server(bootstrap=bootstrap, settings=settings)
    server.serve_forever()
    return server