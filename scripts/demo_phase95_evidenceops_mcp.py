#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from itertools import count
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.mcp.jsonrpc_stdio import read_message, write_message


SERVER_SCRIPT = PROJECT_ROOT / "scripts" / "run_evidenceops_mcp_server.py"


class DemoMcpClient:
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        self.process = process
        self._request_ids = count(1)

    def initialize(self) -> dict[str, Any]:
        response = self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "demo-phase95-evidenceops-client", "version": "0.1.0"},
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
            raise RuntimeError(f"No response received for method '{method}'.")
        if response.get("id") != request_id:
            raise RuntimeError(f"Unexpected response id for method '{method}': {response}")
        return response

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        write_message(
            self.process.stdin,
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
            },
        )

    def close(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
        except OSError:
            pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for stream_name in ("stdout", "stderr"):
            stream = getattr(self.process, stream_name, None)
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass


def _print_section(title: str, payload: object) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _build_demo_environment(base_dir: Path) -> dict[str, str]:
    repository_root = base_dir / "evidenceops_repo"
    snapshot_path = repository_root / ".phase95_evidenceops_repository_snapshot.json"
    action_store_path = base_dir / ".phase95_evidenceops_actions.sqlite3"
    worklog_path = base_dir / ".phase95_evidenceops_worklog.json"

    (repository_root / "policies").mkdir(parents=True)
    (repository_root / "contracts").mkdir(parents=True)
    (repository_root / "audit").mkdir(parents=True)
    (repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf").write_text("policy-v1", encoding="utf-8")
    (repository_root / "contracts" / "CTR-001_Master_Services_Agreement.txt").write_text("contract", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "EVIDENCEOPS_REPOSITORY_ROOT": str(repository_root),
            "EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH": str(snapshot_path),
            "EVIDENCEOPS_ACTION_STORE_PATH": str(action_store_path),
            "EVIDENCEOPS_WORKLOG_PATH": str(worklog_path),
        }
    )
    return env


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        demo_root = Path(tmp_dir)
        env = _build_demo_environment(demo_root)
        process = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("Could not open stdio pipes for the MCP demo server.")

        client = DemoMcpClient(process)
        try:
            initialize_response = client.initialize()
            _print_section("initialize", initialize_response)

            tools_list = client.request("tools/list")
            _print_section("tools/list", tools_list)

            list_documents = client.request(
                "tools/call",
                {"name": "list_documents", "arguments": {"limit": 10}},
            )
            _print_section("tools/call -> list_documents", list_documents)

            register_entry = client.request(
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
                                    "description": "Request a redline of the incident clause",
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
            _print_section("tools/call -> register_evidenceops_entry", register_entry)

            list_actions = client.request(
                "tools/call",
                {"name": "list_actions", "arguments": {"status": "open"}},
            )
            _print_section("tools/call -> list_actions", list_actions)

            first_compare = client.request(
                "tools/call",
                {"name": "compare_repository_state", "arguments": {}},
            )
            _print_section("tools/call -> compare_repository_state (baseline)", first_compare)

            repository_root = Path(env["EVIDENCEOPS_REPOSITORY_ROOT"])
            (repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf").write_text(
                "policy-v2",
                encoding="utf-8",
            )
            (repository_root / "audit" / "AUD-001_Control_Test.md").write_text("audit", encoding="utf-8")

            second_compare = client.request(
                "tools/call",
                {"name": "compare_repository_state", "arguments": {}},
            )
            _print_section("tools/call -> compare_repository_state (after drift)", second_compare)

            open_actions_payload = json.loads(list_actions["result"]["content"][0]["text"])
            open_action_id = int(open_actions_payload[0]["id"])
            update_action = client.request(
                "tools/call",
                {
                    "name": "update_action",
                    "arguments": {
                        "action_id": open_action_id,
                        "status": "closed",
                        "approval_status": "approved",
                        "approval_reason": "Closure validated by the responsible manager.",
                        "approved_by": "manager",
                    },
                },
            )
            _print_section("tools/call -> update_action", update_action)

            resource_summary = client.request(
                "resources/read",
                {"uri": "evidenceops://actions/summary"},
            )
            _print_section("resources/read -> evidenceops://actions/summary", resource_summary)
        finally:
            client.close()


if __name__ == "__main__":
    main()