import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.services.evidenceops_mcp_client import (
    EvidenceOpsMcpClientConfig,
    build_evidenceops_mcp_server_entry,
    install_evidenceops_mcp_server_in_cline_settings,
    register_evidenceops_entry_via_mcp,
)


SERVER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_evidenceops_mcp_server.py"


class Phase95EvidenceOpsMcpClientTests(unittest.TestCase):
    def test_register_evidenceops_entry_via_mcp_returns_summary_and_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            repository_root = base_dir / "evidenceops_repo"
            (repository_root / "policies").mkdir(parents=True)
            (repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf").write_text("policy", encoding="utf-8")
            config = EvidenceOpsMcpClientConfig(
                command=sys.executable,
                args=[str(SERVER_SCRIPT)],
                env={
                    "EVIDENCEOPS_REPOSITORY_ROOT": str(repository_root),
                    "EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH": str(repository_root / ".phase95_evidenceops_repository_snapshot.json"),
                    "EVIDENCEOPS_ACTION_STORE_PATH": str(base_dir / ".phase95_evidenceops_actions.sqlite3"),
                    "EVIDENCEOPS_WORKLOG_PATH": str(base_dir / ".phase95_evidenceops_worklog.json"),
                },
            )

            result, telemetry = register_evidenceops_entry_via_mcp(
                {
                    "timestamp": "2026-04-04T10:00:00",
                    "task_type": "document_agent",
                    "review_type": "risk_gap_review",
                    "tool_used": "review_document_risks",
                    "query": "Liste os riscos do contrato",
                    "confidence": 0.82,
                    "needs_review": False,
                    "document_ids": ["POL-001"],
                    "source_count": 1,
                    "findings": [{"finding_type": "risk"}],
                    "action_items": [
                        {
                            "description": "Solicitar redline da cláusula de incidente",
                            "owner": "Legal",
                            "due_date": "2026-05-01",
                            "status": "open",
                            "evidence": "notify within 10 business days",
                        }
                    ],
                    "recommended_actions": ["Atualizar cláusula"],
                },
                config=config,
            )

        self.assertEqual(result["actions_inserted"], 2)
        self.assertEqual(result["worklog_total_runs"], 1)
        self.assertEqual(telemetry["tool_call_count"], 1)
        self.assertEqual(telemetry["write_call_count"], 1)
        self.assertEqual(telemetry["status"], "success")
        self.assertEqual(telemetry["tool_names"], ["register_evidenceops_entry"])

    def test_install_evidenceops_mcp_server_in_cline_settings_writes_expected_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings_path = Path(tmp_dir) / "cline_mcp_settings.json"
            config = EvidenceOpsMcpClientConfig(
                command="/usr/bin/python3",
                args=["/tmp/run_evidenceops_mcp_server.py"],
                env={"EVIDENCEOPS_REPOSITORY_ROOT": "/tmp/evidenceops_repo"},
            )
            payload = install_evidenceops_mcp_server_in_cline_settings(
                settings_path=settings_path,
                config=config,
            )
            persisted = json.loads(settings_path.read_text(encoding="utf-8"))

        expected_entry = build_evidenceops_mcp_server_entry(config)
        self.assertEqual(payload["mcpServers"]["evidenceops_local"], expected_entry)
        self.assertEqual(persisted["mcpServers"]["evidenceops_local"], expected_entry)
        self.assertFalse(persisted["mcpServers"]["evidenceops_local"]["disabled"])
        self.assertEqual(persisted["mcpServers"]["evidenceops_local"]["autoApprove"], [])


if __name__ == "__main__":
    unittest.main()