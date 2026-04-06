from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from src.app.product_bootstrap import ProductBootstrap, build_product_bootstrap
from src.config import ProductApiSettings, get_product_api_settings
from src.product.models import ProductWorkflowRequest, ProductWorkflowResult
from src.product.service import (
    build_grounding_preview,
    build_product_workflow_frontend_contract,
    generate_product_workflow_deck,
    list_product_documents,
    run_product_workflow,
)


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _html_bytes(content: str) -> bytes:
    return content.encode("utf-8")


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
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _not_found(self) -> None:
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "Not found"})

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        if self.settings.allow_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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

        self._not_found()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            payload = _read_json_body(self)
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(error)})
            return

        if path == "/api/product/run-workflow":
            try:
                request = ProductWorkflowRequest.model_validate(payload)
                result = run_product_workflow(request)
                self._send_json(HTTPStatus.OK, {"ok": True, "result": result.model_dump(mode="json")})
            except Exception as error:  # pragma: no cover - defensive API surface
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
    return ThreadingHTTPServer((resolved_settings.server_name, resolved_settings.server_port), handler_class)


def serve_product_api(
    *,
    bootstrap: ProductBootstrap | None = None,
    settings: ProductApiSettings | None = None,
) -> ThreadingHTTPServer:
    server = build_product_api_server(bootstrap=bootstrap, settings=settings)
    server.serve_forever()
    return server