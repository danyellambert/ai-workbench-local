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
            product_settings=SimpleNamespace(default_workflow="document_review", max_upload_files=5),
            rag_settings=SimpleNamespace(store_path=Path(".rag_store.json")),
            provider_registry={},
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
        with urllib_request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _patch_json(self, server, path: str, payload: dict) -> dict:
        request = urllib_request.Request(
            self._url(server, path),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="PATCH",
        )
        with urllib_request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post_multipart(self, server, path: str, files: list[tuple[str, str, bytes]]) -> dict:
        boundary = "----WorkbenchBoundaryTest"
        body = bytearray()
        for field_name, filename, content in files:
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
                    "Content-Type: application/octet-stream\r\n\r\n"
                ).encode("utf-8")
            )
            body.extend(content)
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        request = urllib_request.Request(
            self._url(server, path),
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib_request.urlopen(request, timeout=30) as response:
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

    def test_product_api_runtime_controls_get_and_patch_endpoints(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            base_payload = {
                "ok": True,
                "contract_version": "runtime_controls.v1",
                "data_source": "live",
                "updated_at": "2026-04-16T12:00:00+00:00",
                "active_profile": {
                    "id": "runtime-controls-live",
                    "name": "Current Product Runtime",
                    "primaryConnectionId": "ollama",
                    "primaryModel": "qwen2.5:7b",
                    "fallbackChain": [],
                    "executionPolicy": "local_only",
                    "retrievalStrategy": "hybrid",
                    "embeddingConnectionId": "ollama",
                    "embeddingModel": "embeddinggemma:300m",
                    "rerankingEnabled": True,
                    "docProcessingPreset": "standard",
                    "qualityPosture": "balanced",
                    "intendedWorkflows": ["document-review"],
                    "isActive": True,
                    "isDefault": True,
                    "summary": "Runtime summary.",
                    "generation": {
                        "temperature": 0.2,
                        "contextWindow": "auto",
                        "promptProfile": "neutro",
                        "streaming": True,
                        "maxOutputTokens": 4096,
                        "topP": 0.95,
                        "structuredOutput": False,
                    },
                    "retrieval": {
                        "topK": 6,
                        "chunkSize": 1200,
                        "chunkOverlap": 80,
                        "rerankPoolSize": 16,
                        "rerankLexicalWeight": 0.35,
                        "groundingStrictness": "balanced",
                    },
                    "docProcessing": {
                        "pdfExtractionMode": "hybrid",
                        "ocrBackend": "ocrmypdf",
                        "vlmEnhancement": False,
                        "tableExtractionMode": "auto",
                        "ocrFailoverEnabled": True,
                        "scannedDocumentThreshold": 0.8,
                    },
                    "workflowFit": [
                        {"workflowId": "document-review", "label": "Document Review", "compatibility": "recommended"},
                    ],
                },
                "available_connections": [],
                "catalogs": {
                    "executionPolicies": [],
                    "qualityPostures": [],
                    "docPresets": [],
                    "retrievalStrategies": [],
                    "groundingStrictness": [],
                    "contextWindows": [],
                    "pdfExtractionModes": [],
                    "ocrBackends": [],
                    "tableExtractionModes": [],
                    "promptProfiles": [],
                },
                "options": {
                    "modelsByConnection": {},
                    "embeddingModelsByConnection": {},
                },
            }
            patched_payload = {
                **base_payload,
                "updated_at": "2026-04-16T12:05:00+00:00",
                "active_profile": {
                    **base_payload["active_profile"],
                    "generation": {
                        **base_payload["active_profile"]["generation"],
                        "temperature": 0.4,
                    },
                },
            }

            with patch("src.product.api.build_runtime_controls_payload", return_value=base_payload), patch(
                "src.product.api.update_runtime_controls_payload",
                return_value=patched_payload,
            ) as update_mock:
                runtime_controls = self._get_json(server, "/api/runtime/controls")
                self.assertTrue(runtime_controls["ok"])
                self.assertEqual(runtime_controls["contract_version"], "runtime_controls.v1")
                self.assertEqual(runtime_controls["active_profile"]["primaryConnectionId"], "ollama")

                patch_response = self._patch_json(
                    server,
                    "/api/runtime/controls",
                    {"profile": {"generation": {"temperature": 0.4}}},
                )
                self.assertTrue(patch_response["ok"])
                self.assertEqual(patch_response["active_profile"]["generation"]["temperature"], 0.4)
                update_mock.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_preferences_get_patch_and_connection_test_endpoints(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            base_payload = {
                "ok": True,
                "contract_version": "preferences.v1",
                "updated_at": "2026-04-16T12:00:00+00:00",
                "active_profile_id": "workspace-default",
                "provider_connections": [
                    {
                        "id": "ollama",
                        "name": "Ollama (local)",
                        "providerFamily": "ollama",
                        "mode": "local",
                        "baseUrl": "http://127.0.0.1:11434",
                        "authMethod": "none",
                        "apiKeyConfigured": False,
                        "status": "connected",
                        "preferredModel": "qwen2.5:7b",
                        "lastChecked": "2026-04-16T12:00:00+00:00",
                        "description": "Primary local runtime.",
                        "capabilities": {
                            "generation": True,
                            "embeddings": True,
                            "reranking": False,
                            "structuredOutputs": True,
                            "vision": False,
                            "toolCalling": False,
                            "streaming": True,
                        },
                        "role": "production",
                    }
                ],
                "runtime_profiles": [],
                "workflow_defaults": [],
                "connection_policy_rules": [],
                "operator_preferences": {
                    "reducedMotion": False,
                    "defaultEvidencePanelOpen": True,
                    "defaultExportFormat": "pdf",
                    "defaultBenchmarkBaseline": "workspace-default",
                    "showSourceBadges": True,
                    "autoOpenInspectorDetails": False,
                },
                "catalogs": {
                    "executionPolicies": [],
                    "qualityPostures": [],
                    "docPresets": [],
                    "retrievalStrategies": [],
                    "groundingStrictness": [],
                    "contextWindows": [],
                    "pdfExtractionModes": [],
                    "ocrBackends": [],
                    "tableExtractionModes": [],
                    "promptProfiles": [],
                },
                "options": {
                    "modelsByConnection": {},
                    "embeddingModelsByConnection": {},
                },
                "credential_policy": {
                    "mode": "env_only",
                    "can_update_from_ui": False,
                    "notes": ["Secrets remain managed outside the UI."],
                },
            }
            patched_payload = {
                **base_payload,
                "active_profile_id": "deep-review",
                "updated_at": "2026-04-16T12:05:00+00:00",
            }
            test_payload = {
                "ok": True,
                "connection_id": "ollama",
                "result": {
                    "status": "connected",
                    "checked_at": "2026-04-16T12:06:00+00:00",
                    "latency_ms": 23.5,
                    "error_message": None,
                },
            }

            with patch("src.product.api.build_preferences_payload", return_value=base_payload), patch(
                "src.product.api.update_preferences_payload",
                return_value=patched_payload,
            ) as update_mock, patch(
                "src.product.api.test_preferences_connection",
                return_value=test_payload,
            ) as test_mock:
                preferences = self._get_json(server, "/api/preferences")
                self.assertTrue(preferences["ok"])
                self.assertEqual(preferences["contract_version"], "preferences.v1")
                self.assertEqual(preferences["provider_connections"][0]["id"], "ollama")

                patch_response = self._patch_json(
                    server,
                    "/api/preferences",
                    {"active_profile_id": "deep-review"},
                )
                self.assertTrue(patch_response["ok"])
                self.assertEqual(patch_response["active_profile_id"], "deep-review")
                update_mock.assert_called_once()

                test_response = self._post_json(server, "/api/preferences/connections/ollama/test", {})
                self.assertTrue(test_response["ok"])
                self.assertEqual(test_response["connection_id"], "ollama")
                self.assertEqual(test_response["result"]["status"], "connected")
                test_mock.assert_called_once()
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
            ), patch(
                "src.product.api.append_product_workflow_history_entry",
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
                self.assertIn("result_view", workflow_response)

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

    def test_product_api_run_workflow_returns_comparison_view_for_policy_comparison(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            fake_result = ProductWorkflowResult(
                workflow_id="policy_contract_comparison",
                workflow_label="Policy / Contract Comparison",
                status="warning",
                summary="Policy B introduces stricter approval and governance controls than Policy A.",
                deck_export_kind="policy_contract_comparison_deck",
                deck_available=True,
            )

            with patch("src.product.api.run_product_workflow", return_value=fake_result), patch(
                "src.product.api.build_policy_comparison_view",
                return_value={
                    "executive_summary": {
                        "narrative": "Policy B introduces stricter approval and governance controls than Policy A.",
                        "counts": {"breaking": 1, "significant": 2, "minor": 0},
                        "status": "Requires Review",
                        "documents": ["Policy A.pdf", "Policy B.pdf"],
                    },
                    "must_fix_items": [{"title": "Formal approval became mandatory"}],
                    "negotiation_priorities": ["Validate the approval gate delta with legal before rollout."],
                    "differences": [],
                    "recommendation": {"summary": "Use Policy B as the baseline.", "handoff": "Legal / policy review"},
                    "artifacts": [],
                    "watchouts": [],
                    "next_steps": [],
                    "run_state": {"current_step": "review", "steps": []},
                },
            ) as comparison_view_mock, patch(
                "src.product.api.append_product_workflow_history_entry",
            ):
                workflow_response = self._post_json(
                    server,
                    "/api/product/run-workflow",
                    {
                        "workflow_id": "policy_contract_comparison",
                        "document_ids": ["doc-a", "doc-b"],
                        "provider": "ollama",
                        "model": "qwen2.5:7b",
                    },
                )
                self.assertTrue(workflow_response["ok"])
                self.assertEqual(workflow_response["result"]["workflow_id"], "policy_contract_comparison")
                self.assertIn("comparison_view", workflow_response)
                self.assertEqual(workflow_response["comparison_view"]["executive_summary"]["counts"]["breaking"], 1)
                comparison_view_mock.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_run_workflow_returns_action_plan_view_for_action_plan_workflow(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            fake_result = ProductWorkflowResult(
                workflow_id="action_plan_evidence_review",
                workflow_label="Action Plan / Evidence Review",
                status="warning",
                summary="Vendor access remediation: 3 actionable task(s) and 2 evidence gaps identified.",
                deck_export_kind="action_plan_deck",
                deck_available=True,
            )

            with patch("src.product.api.run_product_workflow", return_value=fake_result), patch(
                "src.product.api.build_action_plan_view",
                return_value={
                    "objective": "Drive grounded follow-up actions for vendor access remediation.",
                    "summary": {
                        "total": 3,
                        "open": 1,
                        "in_progress": 1,
                        "blocked": 1,
                        "done": 0,
                        "completed": 0,
                        "critical_path": 2,
                        "evidence_gaps": 2,
                        "documents": 2,
                        "artifacts": 0,
                    },
                    "items": [
                        {
                            "id": "action-item-1",
                            "title": "Collect missing privileged-access approvals.",
                            "owner": "Identity Ops",
                            "due_date": "2024-03-22",
                            "priority": "high",
                            "status": "in_progress",
                            "source": "Privileged Account Approval Email.pdf",
                            "evidence": "Approval email is missing for two privileged administrators.",
                            "rationale": "Approval email is missing for two privileged administrators.",
                            "notes": None,
                            "document_id": "doc-1",
                        }
                    ],
                    "critical_path": [
                        {
                            "id": "action-item-1",
                            "title": "Collect missing privileged-access approvals.",
                            "owner": "Identity Ops",
                            "due_date": "2024-03-22",
                            "priority": "high",
                            "status": "in_progress",
                            "source": "Privileged Account Approval Email.pdf",
                            "evidence": "Approval email is missing for two privileged administrators.",
                            "rationale": "Approval email is missing for two privileged administrators.",
                            "notes": None,
                            "document_id": "doc-1",
                        }
                    ],
                    "evidence_gaps": [
                        {
                            "id": "gap-1",
                            "item_id": "action-item-1",
                            "title": "Collect missing privileged-access approvals.",
                            "detail": "Missing explicit owner sign-off artifact for the remaining administrators.",
                            "status": "partial",
                            "source": "Privileged Account Approval Email.pdf",
                            "notes": None,
                        }
                    ],
                    "artifacts": [],
                    "document_ids": ["doc-1", "doc-2"],
                    "run_metadata": {
                        "workflow_id": "action_plan_evidence_review",
                        "workflow_label": "Action Plan / Evidence Review",
                        "status": "warning",
                        "provider": "ollama",
                        "model": "qwen2.5:7b",
                        "context_strategy": "document_scan",
                        "deck_available": True,
                        "deck_export_kind": "action_plan_deck",
                        "warning_count": 1,
                        "warnings": ["Awaiting final governance sign-off."],
                        "source_block_count": 2,
                        "highlights": ["Collect missing privileged-access approvals."],
                        "summary": "Vendor access remediation: 3 actionable task(s) and 2 evidence gaps identified.",
                        "recommendation": "Close the access-control evidence gaps before the next committee checkpoint.",
                        "run_state": {"current_step": "review", "steps": []},
                    },
                },
            ) as action_plan_view_mock, patch(
                "src.product.api.append_product_workflow_history_entry",
            ):
                workflow_response = self._post_json(
                    server,
                    "/api/product/run-workflow",
                    {
                        "workflow_id": "action_plan_evidence_review",
                        "document_ids": ["doc-1", "doc-2"],
                        "provider": "ollama",
                        "model": "qwen2.5:7b",
                    },
                )
                self.assertTrue(workflow_response["ok"])
                self.assertEqual(workflow_response["result"]["workflow_id"], "action_plan_evidence_review")
                self.assertIn("action_plan_view", workflow_response)
                self.assertEqual(workflow_response["action_plan_view"]["summary"]["critical_path"], 2)
                self.assertEqual(workflow_response["action_plan_view"]["items"][0]["owner"], "Identity Ops")
                action_plan_view_mock.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_publish_trello_preview_preserves_dry_run_without_publish_options(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            fake_result = ProductWorkflowResult(
                workflow_id="action_plan_evidence_review",
                workflow_label="Action Plan / Evidence Review",
                status="warning",
                summary="Current run produced 2 actionable items.",
                deck_export_kind="action_plan_deck",
                deck_available=True,
            )

            with patch(
                "src.product.api.publish_product_workflow_to_trello",
                return_value={"status": "planned", "dry_run": True, "planned_card_count": 1},
            ) as publish_mock:
                response = self._post_json(
                    server,
                    "/api/product/publish-trello",
                    {
                        "result": fake_result.model_dump(mode="json"),
                        "dry_run": True,
                    },
                )

                self.assertTrue(response["ok"])
                self.assertTrue(response["dry_run"])
                publish_mock.assert_called_once()
                self.assertTrue(publish_mock.call_args.kwargs["dry_run"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_publish_notion_preview_preserves_dry_run_without_publish_options(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            fake_result = ProductWorkflowResult(
                workflow_id="document_review",
                workflow_label="Document Review",
                status="warning",
                summary="Current run produced 2 findings.",
                deck_export_kind="document_review_deck",
                deck_available=True,
            )

            with patch(
                "src.product.api.publish_product_workflow_to_notion",
                return_value={"status": "planned", "dry_run": True, "template_id": "review_summary"},
            ) as publish_mock:
                response = self._post_json(
                    server,
                    "/api/product/publish-notion",
                    {
                        "result": fake_result.model_dump(mode="json"),
                        "dry_run": True,
                        "template_id": "review_summary",
                    },
                )

                self.assertTrue(response["ok"])
                self.assertTrue(response["dry_run"])
                publish_mock.assert_called_once()
                self.assertTrue(publish_mock.call_args.kwargs["dry_run"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_publish_trello_endpoint(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            fake_result = ProductWorkflowResult(
                workflow_id="action_plan_evidence_review",
                workflow_label="Action Plan / Evidence Review",
                status="warning",
                summary="Current run produced 2 actionable items.",
                deck_export_kind="action_plan_deck",
                deck_available=True,
            )
            publish_payload = {
                "status": "success",
                "dry_run": False,
                "created_card_count": 2,
                "target_board_id": "board-1",
                "message": "Published 2 card(s) to Trello.",
            }

            with patch(
                "src.product.api.publish_product_workflow_to_trello",
                return_value=publish_payload,
            ) as publish_mock:
                response = self._post_json(
                    server,
                    "/api/product/publish-trello",
                    {
                        "result": fake_result.model_dump(mode="json"),
                    },
                )

                self.assertTrue(response["ok"])
                self.assertEqual(response["status"], "success")
                self.assertEqual(response["created_card_count"], 2)
                publish_mock.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_upload_documents_endpoint(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            upload_job_payload = {
                "ok": True,
                "job_id": "job-1",
                "status": "queued",
                "message": "Upload accepted. Preparing ingestion pipeline.",
                "uploaded_count": 1,
                "ignored_count": 0,
                "steps": [
                    {"key": "extraction", "label": "Extraction", "status": "pending"},
                    {"key": "chunking", "label": "Chunking", "status": "pending"},
                    {"key": "embeddings", "label": "Embeddings", "status": "pending"},
                    {"key": "index_sync", "label": "Index Sync", "status": "pending"},
                ],
            }

            with patch(
                "src.product.api.start_product_upload_job",
                return_value=upload_job_payload,
            ), patch(
                "src.product.api.get_product_upload_job",
                return_value={
                    **upload_job_payload,
                    "status": "completed",
                    "message": "1 document(s) indexed successfully.",
                    "indexed_documents": [{"document_id": "hash-1", "name": "notes.md", "status": "indexed"}],
                },
            ):
                upload_response = self._post_multipart(
                    server,
                    "/api/product/upload-documents",
                    [("files", "notes.md", b"# Notes\n\nHello world")],
                )
                self.assertTrue(upload_response["ok"])
                self.assertEqual(upload_response["job_id"], "job-1")
                self.assertEqual(upload_response["status"], "queued")

                upload_status = self._get_json(server, "/api/product/upload-jobs/job-1")
                self.assertTrue(upload_status["ok"])
                self.assertEqual(upload_status["status"], "completed")
                self.assertEqual(upload_status["indexed_documents"][0]["document_id"], "hash-1")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_delete_documents_endpoint(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            with patch(
                "src.product.api.delete_product_documents",
                return_value=(
                    [],
                    {
                        "ok": True,
                        "removed_count": 1,
                        "removed_document_ids": ["doc-1"],
                        "message": "1 document(s) removed successfully.",
                        "sync_status": {"ok": True},
                    },
                ),
            ), patch(
                "src.product.api.build_product_document_library_payload",
                return_value={
                    "ok": True,
                    "summary": {"total_documents": 0, "indexed_documents": 0, "total_chunks": 0, "total_chars": 0},
                    "documents": [],
                },
            ):
                delete_response = self._post_json(
                    server,
                    "/api/product/delete-documents",
                    {"document_ids": ["doc-1"]},
                )
                self.assertTrue(delete_response["ok"])
                self.assertEqual(delete_response["removed_count"], 1)
                self.assertEqual(delete_response["removed_document_ids"], ["doc-1"])
                self.assertEqual(delete_response["document_library"]["summary"]["total_documents"], 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_command_center_run_history_and_artifacts_endpoints(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            with patch(
                "src.product.api.build_product_command_center_payload",
                return_value={
                    "ok": True,
                    "summary": {
                        "indexed_documents": 3,
                        "total_chunks": 42,
                        "completed_runs": 5,
                        "artifacts_generated": 4,
                    },
                    "recent_runs": [{"id": "run-1", "workflow_label": "Document Review"}],
                    "recent_artifacts": [{"id": "artifact-1", "name": "Document Review Deck"}],
                },
            ), patch(
                "src.product.api.build_product_run_history_payload",
                return_value={
                    "ok": True,
                    "summary": {"total_runs": 5, "completed_runs": 4},
                    "runs": [{"id": "run-1", "workflow_label": "Document Review"}],
                },
            ), patch(
                "src.product.api.build_product_artifact_payload",
                return_value={
                    "ok": True,
                    "summary": {"total_artifacts": 4, "completed_artifacts": 4},
                    "artifacts": [{"id": "artifact-1", "name": "Document Review Deck"}],
                },
            ), patch(
                "src.product.api.build_product_document_library_payload",
                return_value={
                    "ok": True,
                    "summary": {"total_documents": 3, "indexed_documents": 3, "total_chunks": 42, "total_chars": 9000},
                    "documents": [{"document_id": "doc-1", "name": "Policy A", "status": "indexed"}],
                },
            ):
                command_center = self._get_json(server, "/api/product/command-center")
                self.assertTrue(command_center["ok"])
                self.assertEqual(command_center["summary"]["completed_runs"], 5)
                self.assertEqual(command_center["recent_runs"][0]["workflow_label"], "Document Review")

                document_library = self._get_json(server, "/api/product/document-library")
                self.assertTrue(document_library["ok"])
                self.assertEqual(document_library["summary"]["total_documents"], 3)
                self.assertEqual(document_library["documents"][0]["status"], "indexed")

                run_history = self._get_json(server, "/api/product/run-history")
                self.assertTrue(run_history["ok"])
                self.assertEqual(run_history["summary"]["total_runs"], 5)

                artifacts = self._get_json(server, "/api/product/artifacts")
                self.assertTrue(artifacts["ok"])
                self.assertEqual(artifacts["summary"]["completed_artifacts"], 4)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


    def test_product_api_run_history_detail_and_artifact_detail_endpoints(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            with patch(
                "src.product.api.build_product_run_detail_payload",
                return_value={
                    "ok": True,
                    "source": "history_file",
                    "run": {
                        "id": "run-42",
                        "workflow_id": "document_review",
                        "workflow_label": "Document Review",
                        "status": "completed",
                        "documents": ["Policy A.pdf"],
                        "request_payload": {"workflow_id": "document_review", "document_ids": ["doc-1"]},
                        "response_payload": {"workflow_id": "document_review", "status": "completed"},
                        "result_sections": {"summary": "Grounded summary", "highlights": ["One highlight"], "warnings": [], "tables": [], "sources": [], "artifacts": [], "strengths": [], "watchouts": [], "next_steps": [], "evidence_highlights": []},
                        "can_rerun": True,
                    },
                },
            ), patch(
                "src.product.api.build_product_artifact_detail_payload",
                return_value={
                    "ok": True,
                    "artifact": {
                        "id": "artifact-9",
                        "name": "Document Review Deck",
                        "workflow_label": "Document Review",
                        "type": "pptx",
                        "status": "ready",
                        "size": "128 KB",
                        "available_assets": [{"artifact_type": "pptx", "label": "Deck", "path": "artifacts/document-review.pptx", "available": True}],
                    },
                    "detail": {
                        "notes": ["Review sidecar present"],
                        "assets": [{"artifact_type": "pptx", "label": "Deck", "path": "artifacts/document-review.pptx", "available": True}],
                    },
                },
            ):
                run_detail = self._get_json(server, "/api/product/run-history/run-42")
                self.assertTrue(run_detail["ok"])
                self.assertEqual(run_detail["run"]["id"], "run-42")
                self.assertTrue(run_detail["run"]["can_rerun"])

                artifact_detail = self._get_json(server, "/api/product/artifacts/artifact-9")
                self.assertTrue(artifact_detail["ok"])
                self.assertEqual(artifact_detail["artifact"]["id"], "artifact-9")
                self.assertEqual(artifact_detail["detail"]["assets"][0]["artifact_type"], "pptx")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_product_api_rerun_endpoint_replays_source_run(self) -> None:
        from unittest.mock import patch

        server, thread = self._start_server()
        try:
            fake_result = ProductWorkflowResult(
                workflow_id="document_review",
                workflow_label="Document Review",
                summary="Grounded summary from rerun",
                deck_export_kind="document_review_deck",
                deck_available=True,
            )

            source_run = {
                "id": "run-source",
                "workflow_id": "document_review",
                "workflow_label": "Document Review",
                "status": "completed",
                "documents": ["Policy A.pdf"],
                "request_payload": {
                    "workflow_id": "document_review",
                    "document_ids": ["doc-1"],
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                },
                "can_rerun": True,
            }

            with patch("src.product.api.build_product_run_detail_payload", return_value={"ok": True, "run": source_run}), patch(
                "src.product.api.run_product_workflow",
                return_value=fake_result,
            ), patch(
                "src.product.api.list_product_documents",
                return_value=[],
            ), patch(
                "src.product.api.append_product_workflow_history_entry",
            ) as append_history:
                payload = self._post_json(server, "/api/product/run-history/run-source/rerun", {})
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["reran_from_run_id"], "run-source")
                self.assertEqual(payload["result"]["workflow_id"], "document_review")
                self.assertTrue(append_history.called)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()