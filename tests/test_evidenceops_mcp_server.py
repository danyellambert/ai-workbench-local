import json
import os
import subprocess
import sys
import tempfile
import unittest
from itertools import count
from pathlib import Path
from typing import Any

from src.mcp.jsonrpc_stdio import read_message, write_message


SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_evidenceops_mcp_server.py"


class _McpTestClient:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process
        self._request_ids = count(1)

    def initialize(self) -> dict[str, Any]:
        response = self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "phase95-evidenceops-tests", "version": "0.1.0"},
                "capabilities": {},
            },
        )
        self.notify("notifications/initialized", {})
        return response

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = next(self._request_ids)
        write_message(
            self.process.stdin,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            },
        )
        response = read_message(self.process.stdout)
        if response is None:
            raise RuntimeError(f"No response for method {method}")
        return response

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        write_message(
            self.process.stdin,
            {"jsonrpc": "2.0", "method": method, "params": params or {}},
        )


def _shutdown_process(process: subprocess.Popen[bytes]) -> None:
    try:
        if process.stdin is not None:
            process.stdin.close()
    except OSError:
        pass
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    for stream_name in ("stdout", "stderr"):
        stream = getattr(process, stream_name, None)
        try:
            if stream is not None:
                stream.close()
        except OSError:
            pass


class Phase95EvidenceOpsMcpServerTests(unittest.TestCase):
    def _build_demo_env(self, tmp_dir: str) -> dict[str, str]:
        base_dir = Path(tmp_dir)
        repository_root = base_dir / "evidenceops_repo"
        snapshot_path = repository_root / ".phase95_evidenceops_repository_snapshot.json"
        action_store_path = base_dir / ".phase95_evidenceops_actions.sqlite3"
        worklog_path = base_dir / ".phase95_evidenceops_worklog.json"

        (repository_root / "policies").mkdir(parents=True)
        (repository_root / "contracts").mkdir(parents=True)
        (repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf").write_text("policy-v1", encoding="utf-8")
        (repository_root / "contracts" / "CTR-001_Master_Services_Agreement.txt").write_text("contract", encoding="utf-8")

        env = os.environ.copy()
        env.update(
            {
                "EVIDENCEOPS_REPOSITORY_ROOT": str(repository_root),
                "EVIDENCEOPS_REPOSITORY_BACKEND": "local",
                "EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH": str(snapshot_path),
                "EVIDENCEOPS_ACTION_STORE_PATH": str(action_store_path),
                "EVIDENCEOPS_WORKLOG_PATH": str(worklog_path),
            }
        )
        return env

    def test_server_initializes_and_lists_expected_tools(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._build_demo_env(tmp_dir)
            process = subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.addCleanup(_shutdown_process, process)
            client = _McpTestClient(process)

            initialize_response = client.initialize()
            tools_response = client.request("tools/list")

        self.assertEqual(initialize_response["result"]["serverInfo"]["name"], "evidenceops-local-mcp")
        tool_names = [item["name"] for item in tools_response["result"]["tools"]]
        self.assertIn("list_documents", tool_names)
        self.assertIn("update_action", tool_names)
        self.assertIn("compare_repository_state", tool_names)

    def test_server_calls_tools_and_resources_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            env = self._build_demo_env(tmp_dir)
            repository_root = Path(env["EVIDENCEOPS_REPOSITORY_ROOT"])
            process = subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            self.addCleanup(_shutdown_process, process)
            client = _McpTestClient(process)
            client.initialize()

            list_documents_response = client.request(
                "tools/call",
                {"name": "list_documents", "arguments": {"limit": 10}},
            )
            register_response = client.request(
                "tools/call",
                {
                    "name": "register_evidenceops_entry",
                    "arguments": {
                        "entry": {
                            "timestamp": "2026-04-04T10:00:00",
                            "task_type": "document_agent",
                            "review_type": "risk_gap_review",
                            "tool_used": "review_document_risks",
                            "query": "List the contract risks",
                            "confidence": 0.82,
                            "needs_review": False,
                            "document_ids": ["CTR-001"],
                            "source_count": 2,
                            "findings": [{"finding_type": "risk"}],
                            "action_items": [
                                {
                                    "description": "Request redline for the incident clause",
                                    "owner": "Legal",
                                    "due_date": "2026-05-01",
                                    "status": "open",
                                    "evidence": "notify within 10 business days",
                                }
                            ],
                            "recommended_actions": ["Update clause"],
                        }
                    },
                },
            )
            list_actions_response = client.request(
                "tools/call",
                {"name": "list_actions", "arguments": {"status": "open"}},
            )
            client.request(
                "tools/call",
                {"name": "compare_repository_state", "arguments": {}},
            )
            (repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf").write_text("policy-v2", encoding="utf-8")
            second_compare_response = client.request(
                "tools/call",
                {"name": "compare_repository_state", "arguments": {}},
            )

            open_actions_payload = json.loads(list_actions_response["result"]["content"][0]["text"])
            action_id = int(open_actions_payload[0]["id"])
            update_response = client.request(
                "tools/call",
                {
                    "name": "update_action",
                    "arguments": {
                        "action_id": action_id,
                        "status": "closed",
                        "approval_status": "approved",
                        "approval_reason": "Closure validated.",
                        "approved_by": "manager",
                    },
                },
            )
            resource_response = client.request(
                "resources/read",
                {"uri": "evidenceops://actions/summary"},
            )

        documents_payload = json.loads(list_documents_response["result"]["content"][0]["text"])
        register_payload = json.loads(register_response["result"]["content"][0]["text"])
        compare_payload = json.loads(second_compare_response["result"]["content"][0]["text"])
        update_payload = json.loads(update_response["result"]["content"][0]["text"])
        resource_payload = json.loads(resource_response["result"]["contents"][0]["text"])

        self.assertEqual(len(documents_payload), 2)
        self.assertEqual(register_payload["actions_inserted"], 2)
        self.assertEqual(compare_payload["changed_documents_count"], 1)
        self.assertEqual(update_payload["status"], "closed")
        self.assertEqual(update_payload["metadata"]["approval_status"], "approved")
        self.assertGreaterEqual(resource_payload["approved_actions"], 1)


if __name__ == "__main__":
    unittest.main()