import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib import request as urllib_request

from src.config import ProductApiSettings
from src.product.api import build_product_api_server
from src.product.models import GroundingPreview, ProductArtifact, ProductDocumentRef, ProductWorkflowResult


class ProductApiTests(unittest.TestCase):
    def _start_server(self):
        from src.product.service import build_product_workflow_catalog

        bootstrap = SimpleNamespace(
            workflow_catalog=build_product_workflow_catalog(),
            product_settings=SimpleNamespace(default_workflow="document_review"),
            rag_settings=SimpleNamespace(store_path=Path(".rag_store.json")),
            presentation_export_settings=SimpleNamespace(enabled=False),
            workspace_root=Path("."),
        )
        settings = ProductApiSettings(server_name="127.0.0.1", server_port=0, enable_web_frontend=True, allow_cors=True)
        server = build_product_api_server(bootstrap=bootstrap, settings=settings)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def _url(self, server, path: str) -> str:
        return f"http://127.0.0.1:{server.server_address[1]}{path}"

    def _get_json(self, server, path: str) -> dict:
        with urllib_request.urlopen(self._url(server, path), timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_json(self, server, path: str, payload: dict) -> dict:
        request = urllib_request.Request(
            self._url(server, path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def test_product_api_exposes_root_health_and_workflow_catalog(self) -> None:
        server, thread = self._start_server()
        try:
            with urllib_request.urlopen(self._url(server, "/"), timeout=5) as response:
                body = response.read().decode("utf-8")
            self.assertIn("AI Workbench Product API", body)

            health = self._get_json(server, "/health")
            self.assertTrue(health["ok"])
            self.assertEqual(health["service"], "product_api")

            workflows = self._get_json(server, "/api/product/workflows")
            self.assertEqual(workflows["contract_version"], "product_workflows.v1")
            self.assertEqual(workflows["workflow_count"], 4)
            self.assertTrue(workflows["executive_deck_catalog"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_documents_and_grounding_preview_endpoints(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            with patch(
                "src.product.api.list_product_documents",
                return_value=[ProductDocumentRef(document_id="doc-1", name="Policy A", file_type="pdf", char_count=1200, chunk_count=4)],
            ), patch(
                "src.product.api.build_grounding_preview",
                return_value=GroundingPreview(
                    strategy="retrieval",
                    document_ids=["doc-1"],
                    context_chars=128,
                    source_block_count=1,
                    preview_text="[Source: doc-1] Example preview",
                ),
            ):
                documents = self._get_json(server, "/api/product/documents")
                self.assertTrue(documents["ok"])
                self.assertEqual(documents["documents"][0]["document_id"], "doc-1")

                preview = self._get_json(server, "/api/product/grounding-preview?workflow_id=document_review&document_id=doc-1&strategy=retrieval")
                self.assertTrue(preview["ok"])
                self.assertEqual(preview["preview"]["strategy"], "retrieval")
                self.assertEqual(preview["preview"]["document_ids"], ["doc-1"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_run_workflow_and_generate_deck_endpoints(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            fake_result = ProductWorkflowResult(
                workflow_id="document_review",
                workflow_label="Document Review",
                summary="Grounded summary",
                deck_export_kind="document_review_deck",
                deck_available=True,
            )
            fake_artifact = ProductArtifact(
                artifact_type="contract_json",
                label="Contract JSON",
                path="artifacts/export/contract.json",
                available=True,
            )

            with patch("src.product.api.run_product_workflow", return_value=fake_result), patch(
                "src.product.api.generate_product_workflow_deck",
                return_value=({"status": "completed", "export_kind": "document_review_deck"}, [fake_artifact]),
            ):
                workflow_response = self._post_json(
                    server,
                    "/api/product/run-workflow",
                    {
                        "workflow_id": "document_review",
                        "document_ids": ["doc-1"],
                        "provider": "ollama",
                        "model": "qwen2.5:7b",
                    },
                )
                self.assertTrue(workflow_response["ok"])
                self.assertEqual(workflow_response["result"]["workflow_id"], "document_review")

                deck_response = self._post_json(
                    server,
                    "/api/product/generate-deck",
                    fake_result.model_dump(mode="json"),
                )
                self.assertTrue(deck_response["ok"])
                self.assertEqual(deck_response["export_result"]["status"], "completed")
                self.assertEqual(deck_response["artifacts"][0]["artifact_type"], "contract_json")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()