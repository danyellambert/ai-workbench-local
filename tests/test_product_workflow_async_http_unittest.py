import json
import os
import threading
import time
import unittest
from http.cookiejar import CookieJar
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from urllib import request as urllib_request
from urllib.error import HTTPError
from unittest.mock import patch

from src.config import ProductApiSettings
from src.product.api import build_product_api_server
from src.product.service import build_product_workflow_catalog


class ProductWorkflowAsyncHttpTests(unittest.TestCase):
    def _start_server(self, workspace_root: Path):
        bootstrap = SimpleNamespace(
            workflow_catalog=build_product_workflow_catalog(),
            product_settings=SimpleNamespace(
                default_workflow="document_review",
                max_upload_files=5,
                allow_direct_uploads=True,
            ),
            rag_settings=SimpleNamespace(store_path=workspace_root / ".rag_store.json"),
            provider_registry={},
            presentation_export_settings=SimpleNamespace(enabled=False),
            workspace_root=workspace_root,
        )
        settings = ProductApiSettings(
            server_name="127.0.0.1",
            server_port=0,
            enable_web_frontend=True,
            allow_cors=True,
        )
        server = build_product_api_server(bootstrap=bootstrap, settings=settings)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def _url(self, server, path: str) -> str:
        return f"http://127.0.0.1:{server.server_address[1]}{path}"

    def _json_request(self, opener, server, path: str, *, method: str = "GET", payload: dict | None = None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib_request.Request(
            self._url(server, path),
            data=data,
            headers=headers,
            method=method,
        )
        with opener.open(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def _workflow_payload(self) -> dict:
        return {
            "workflow_id": "document_review",
            "document_ids": ["doc-1"],
            "context_strategy": "retrieval",
            "use_document_context": True,
        }

    def _fake_response_payload(self, run_id: str = "run_async_http_test") -> dict:
        return {
            "ok": True,
            "run_id": run_id,
            "trace_id": f"trace_{run_id}",
            "surface": "product_api_public_overlay",
            "write_scope": "session_overlay",
            "history_entry": {
                "id": run_id,
                "trace_id": f"trace_{run_id}",
                "surface": "product_api_public_overlay",
            },
            "result": {
                "workflow_id": "document_review",
                "workflow_label": "Document Review",
                "status": "completed",
                "summary": "Async workflow completed via HTTP test.",
                "findings": [],
                "recommendation": "Approve",
                "artifacts": [],
                "deck_available": False,
                "deck_export_kind": "document_review",
            },
            "result_sections": {
                "summary": "Async workflow completed via HTTP test.",
                "highlights": [],
                "recommendation": "Approve",
                "warnings": [],
                "tables": [],
                "sources": [],
                "artifacts": [],
                "strengths": [],
                "watchouts": [],
                "next_steps": [],
                "evidence_highlights": [],
            },
        }

    def test_async_workflow_job_can_be_polled_only_by_owner_session(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            users_root = Path(tmp) / "users"
            workspace_root.mkdir(parents=True, exist_ok=True)
            users_root.mkdir(parents=True, exist_ok=True)

            server, thread = self._start_server(workspace_root)
            owner_cookie_jar = CookieJar()
            owner_opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(owner_cookie_jar))
            other_opener = urllib_request.build_opener()

            try:
                with patch.dict(
                    os.environ,
                    {
                        "AI_DECISION_STUDIO_USERS_ROOT": str(users_root),
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_ENABLED": "0",
                    },
                    clear=False,
                ), patch(
                    "src.product.api.list_product_documents",
                    return_value=[SimpleNamespace(document_id="doc-1", name="Policy A")],
                ), patch(
                    "src.product.api._execute_product_workflow_for_identity",
                    return_value=self._fake_response_payload(),
                ) as execute_mock:
                    status, queued = self._json_request(
                        owner_opener,
                        server,
                        "/api/product/run-workflow-async",
                        method="POST",
                        payload=self._workflow_payload(),
                    )

                    self.assertEqual(status, 202)
                    self.assertTrue(queued["ok"])
                    self.assertIn(queued["status"], {"queued", "running", "completed"})
                    self.assertEqual(queued["write_scope"], "session_overlay")
                    self.assertTrue(str(queued["job_id"]).startswith("workflow_job_"))
                    self.assertGreaterEqual(len(owner_cookie_jar), 1)

                    job_id = queued["job_id"]

                    completed = None
                    for _ in range(40):
                        poll_status, payload = self._json_request(
                            owner_opener,
                            server,
                            f"/api/product/workflow-jobs/{job_id}",
                        )
                        self.assertEqual(poll_status, 200)
                        if payload["status"] == "completed":
                            completed = payload
                            break
                        time.sleep(0.05)

                    self.assertIsNotNone(completed)
                    self.assertEqual(completed["run_id"], "run_async_http_test")
                    self.assertEqual(completed["response"]["result"]["workflow_id"], "document_review")
                    self.assertEqual(completed["response"]["write_scope"], "session_overlay")
                    execute_mock.assert_called_once()

                    with self.assertRaises(HTTPError) as other_session_error:
                        self._json_request(
                            other_opener,
                            server,
                            f"/api/product/workflow-jobs/{job_id}",
                        )

                    self.assertEqual(other_session_error.exception.code, 403)
                    forbidden_payload = json.loads(other_session_error.exception.read().decode("utf-8"))
                    self.assertFalse(forbidden_payload["ok"])
                    self.assertIn("not available for this session", forbidden_payload["error"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_slow_async_workflow_stays_running_blocks_second_run_then_releases_gate(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            users_root = Path(tmp) / "users"
            workspace_root.mkdir(parents=True, exist_ok=True)
            users_root.mkdir(parents=True, exist_ok=True)

            server, thread = self._start_server(workspace_root)
            owner_cookie_jar = CookieJar()
            owner_opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(owner_cookie_jar))

            first_started = threading.Event()
            allow_first_to_finish = threading.Event()
            call_count = {"value": 0}

            def slow_execute(*args, **kwargs):
                call_count["value"] += 1
                if call_count["value"] == 1:
                    first_started.set()
                    self.assertTrue(allow_first_to_finish.wait(timeout=5), "slow workflow was not released by the test")
                    return self._fake_response_payload("run_async_http_slow")
                return self._fake_response_payload(f"run_async_http_after_release_{call_count['value']}")

            try:
                with patch.dict(
                    os.environ,
                    {
                        "AI_DECISION_STUDIO_USERS_ROOT": str(users_root),
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_ENABLED": "0",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_ENABLED": "1",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_PER_SESSION": "1",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_GLOBAL": "2",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_TTL_SECONDS": "30",
                    },
                    clear=False,
                ), patch(
                    "src.product.api.list_product_documents",
                    return_value=[SimpleNamespace(document_id="doc-1", name="Policy A")],
                ), patch(
                    "src.product.api._execute_product_workflow_for_identity",
                    side_effect=slow_execute,
                ):
                    status, queued = self._json_request(
                        owner_opener,
                        server,
                        "/api/product/run-workflow-async",
                        method="POST",
                        payload=self._workflow_payload(),
                    )
                    self.assertEqual(status, 202)
                    job_id = queued["job_id"]
                    self.assertTrue(first_started.wait(timeout=2), "background workflow did not start")

                    running_payload = None
                    for _ in range(40):
                        poll_status, payload = self._json_request(
                            owner_opener,
                            server,
                            f"/api/product/workflow-jobs/{job_id}",
                        )
                        self.assertEqual(poll_status, 200)
                        if payload["status"] == "running":
                            running_payload = payload
                            break
                        time.sleep(0.05)

                    self.assertIsNotNone(running_payload)
                    self.assertEqual(running_payload["write_scope"], "session_overlay")
                    self.assertNotIn("response", running_payload)

                    with self.assertRaises(HTTPError) as blocked_second_run:
                        self._json_request(
                            owner_opener,
                            server,
                            "/api/product/run-workflow-async",
                            method="POST",
                            payload=self._workflow_payload(),
                        )

                    self.assertEqual(blocked_second_run.exception.code, 429)
                    blocked_payload = json.loads(blocked_second_run.exception.read().decode("utf-8"))
                    self.assertFalse(blocked_payload["ok"])
                    self.assertIn("execution_gate", blocked_payload)
                    self.assertIn("session_in_flight", blocked_payload["execution_gate"].get("blocked_by", []))

                    allow_first_to_finish.set()

                    completed = None
                    for _ in range(80):
                        poll_status, payload = self._json_request(
                            owner_opener,
                            server,
                            f"/api/product/workflow-jobs/{job_id}",
                        )
                        self.assertEqual(poll_status, 200)
                        if payload["status"] == "completed":
                            completed = payload
                            break
                        time.sleep(0.05)

                    self.assertIsNotNone(completed)
                    self.assertEqual(completed["run_id"], "run_async_http_slow")
                    self.assertEqual(completed["response"]["write_scope"], "session_overlay")

                    status_after_release, queued_after_release = self._json_request(
                        owner_opener,
                        server,
                        "/api/product/run-workflow-async",
                        method="POST",
                        payload=self._workflow_payload(),
                    )
                    self.assertEqual(status_after_release, 202)
                    self.assertTrue(queued_after_release["ok"])
                    self.assertTrue(str(queued_after_release["job_id"]).startswith("workflow_job_"))
                    self.assertGreaterEqual(call_count["value"], 2)
            finally:
                allow_first_to_finish.set()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_unknown_workflow_job_returns_404(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            users_root = Path(tmp) / "users"
            workspace_root.mkdir(parents=True, exist_ok=True)
            users_root.mkdir(parents=True, exist_ok=True)

            server, thread = self._start_server(workspace_root)
            owner_opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(CookieJar()))

            try:
                with patch.dict(os.environ, {"AI_DECISION_STUDIO_USERS_ROOT": str(users_root)}, clear=False):
                    with self.assertRaises(HTTPError) as error_context:
                        self._json_request(
                            owner_opener,
                            server,
                            "/api/product/workflow-jobs/workflow_job_missing",
                        )

                    self.assertEqual(error_context.exception.code, 404)
                    payload = json.loads(error_context.exception.read().decode("utf-8"))
                    self.assertFalse(payload["ok"])
                    self.assertIn("not found or expired", payload["error"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_background_error_marks_job_error_and_releases_gate(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            users_root = Path(tmp) / "users"
            workspace_root.mkdir(parents=True, exist_ok=True)
            users_root.mkdir(parents=True, exist_ok=True)

            server, thread = self._start_server(workspace_root)
            owner_cookie_jar = CookieJar()
            owner_opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(owner_cookie_jar))

            first_started = threading.Event()
            allow_first_to_fail = threading.Event()
            call_count = {"value": 0}

            def failing_then_success(*args, **kwargs):
                call_count["value"] += 1
                if call_count["value"] == 1:
                    first_started.set()
                    self.assertTrue(allow_first_to_fail.wait(timeout=5), "failing workflow was not released by the test")
                    raise RuntimeError("provider exploded")
                return self._fake_response_payload(f"run_after_error_release_{call_count['value']}")

            try:
                with patch.dict(
                    os.environ,
                    {
                        "AI_DECISION_STUDIO_USERS_ROOT": str(users_root),
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_ENABLED": "0",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_ENABLED": "1",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_PER_SESSION": "1",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_GLOBAL": "2",
                        "AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_TTL_SECONDS": "30",
                    },
                    clear=False,
                ), patch(
                    "src.product.api.list_product_documents",
                    return_value=[SimpleNamespace(document_id="doc-1", name="Policy A")],
                ), patch(
                    "src.product.api._execute_product_workflow_for_identity",
                    side_effect=failing_then_success,
                ):
                    status, queued = self._json_request(
                        owner_opener,
                        server,
                        "/api/product/run-workflow-async",
                        method="POST",
                        payload=self._workflow_payload(),
                    )
                    self.assertEqual(status, 202)
                    job_id = queued["job_id"]
                    self.assertTrue(first_started.wait(timeout=2), "background workflow did not start")

                    with self.assertRaises(HTTPError) as blocked_second_run:
                        self._json_request(
                            owner_opener,
                            server,
                            "/api/product/run-workflow-async",
                            method="POST",
                            payload=self._workflow_payload(),
                        )

                    self.assertEqual(blocked_second_run.exception.code, 429)

                    allow_first_to_fail.set()

                    errored = None
                    for _ in range(80):
                        poll_status, payload = self._json_request(
                            owner_opener,
                            server,
                            f"/api/product/workflow-jobs/{job_id}",
                        )
                        self.assertEqual(poll_status, 200)
                        if payload["status"] == "error":
                            errored = payload
                            break
                        time.sleep(0.05)

                    self.assertIsNotNone(errored)
                    self.assertFalse(errored["ok"])
                    self.assertIn("provider exploded", errored["error"])
                    self.assertNotIn("owner", errored)
                    self.assertNotIn("execution_gate", errored)

                    status_after_error, queued_after_error = self._json_request(
                        owner_opener,
                        server,
                        "/api/product/run-workflow-async",
                        method="POST",
                        payload=self._workflow_payload(),
                    )
                    self.assertEqual(status_after_error, 202)
                    self.assertTrue(queued_after_error["ok"])
                    self.assertTrue(str(queued_after_error["job_id"]).startswith("workflow_job_"))
                    self.assertGreaterEqual(call_count["value"], 2)
            finally:
                allow_first_to_fail.set()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
