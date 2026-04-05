import tempfile
import unittest
from pathlib import Path

from src.services.evidenceops_local_ops import (
    compare_evidenceops_repository_state,
    get_evidenceops_repository_document,
    list_evidenceops_action_items,
    list_evidenceops_repository_entries,
    search_evidenceops_repository_entries,
    summarize_evidenceops_action_items,
    summarize_evidenceops_repository_entries,
    update_evidenceops_action_item,
)
from src.services.evidenceops_repository import summarize_evidenceops_repository_documents
from src.storage.phase95_evidenceops_action_store import append_evidenceops_actions_from_worklog_entry


class Phase95EvidenceOpsLocalOpsTests(unittest.TestCase):
    def test_repository_entries_can_be_listed_filtered_and_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository_root = Path(tmp_dir) / "evidenceops_repo"
            (repository_root / "policies").mkdir(parents=True)
            (repository_root / "contracts").mkdir(parents=True)
            (repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf").write_text("policy", encoding="utf-8")
            (repository_root / "contracts" / "CTR-001_Master_Services_Agreement.txt").write_text("contract", encoding="utf-8")

            documents = list_evidenceops_repository_entries(repository_root)
            policy_documents = list_evidenceops_repository_entries(repository_root, category="policies")
            search_documents = list_evidenceops_repository_entries(repository_root, query="master services")
            suffix_documents = list_evidenceops_repository_entries(repository_root, suffix="txt")
            search_by_document_id = search_evidenceops_repository_entries(repository_root, query="POL-001")
            filtered_summary = summarize_evidenceops_repository_entries(repository_root, category="contracts")
            summary = summarize_evidenceops_repository_documents(documents)
            resolved_by_id = get_evidenceops_repository_document(repository_root, document_id="POL-001")
            resolved_by_path = get_evidenceops_repository_document(
                repository_root,
                relative_path="contracts/CTR-001_Master_Services_Agreement.txt",
            )

        self.assertEqual(len(documents), 2)
        self.assertEqual(len(policy_documents), 1)
        self.assertEqual(policy_documents[0]["category"], "policies")
        self.assertEqual(len(search_documents), 1)
        self.assertEqual(search_documents[0]["document_id"], "CTR-001")
        self.assertEqual(summary["total_documents"], 2)
        self.assertEqual(summary["category_counts"]["policies"], 1)
        self.assertEqual(summary["category_counts"]["contracts"], 1)
        self.assertEqual(len(suffix_documents), 1)
        self.assertEqual(suffix_documents[0]["suffix"], ".txt")
        self.assertEqual(search_by_document_id[0]["document_id"], "POL-001")
        self.assertEqual(filtered_summary["total_documents"], 1)
        self.assertEqual(resolved_by_id["title"], "Information Security Policy v1")
        self.assertEqual(resolved_by_path["document_id"], "CTR-001")

    def test_repository_state_comparison_detects_new_changed_and_removed_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repository_root = Path(tmp_dir) / "evidenceops_repo"
            snapshot_path = repository_root / ".phase95_evidenceops_repository_snapshot.json"
            (repository_root / "policies").mkdir(parents=True)
            (repository_root / "contracts").mkdir(parents=True)
            policy_path = repository_root / "policies" / "POL-001_Information_Security_Policy_v1.pdf"
            contract_path = repository_root / "contracts" / "CTR-001_Master_Services_Agreement.txt"
            policy_path.write_text("policy-v1", encoding="utf-8")
            contract_path.write_text("contract", encoding="utf-8")

            first_diff = compare_evidenceops_repository_state(repository_root, snapshot_path=snapshot_path)
            policy_path.write_text("policy-v2", encoding="utf-8")
            contract_path.unlink()
            (repository_root / "audit").mkdir(parents=True)
            (repository_root / "audit" / "AUD-001_Control_Test.md").write_text("audit", encoding="utf-8")
            second_diff = compare_evidenceops_repository_state(repository_root, snapshot_path=snapshot_path)

        self.assertFalse(first_diff["has_previous_snapshot"])
        self.assertEqual(second_diff["changed_documents_count"], 1)
        self.assertEqual(second_diff["removed_documents_count"], 1)
        self.assertEqual(second_diff["new_documents_count"], 1)
        self.assertEqual(second_diff["changed_documents"][0]["document_id"], "POL-001")
        self.assertEqual(second_diff["removed_documents"][0]["document_id"], "CTR-001")
        self.assertEqual(second_diff["new_documents"][0]["document_id"], "AUD-001")

    def test_action_items_can_be_listed_and_updated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / ".phase95_evidenceops_actions.sqlite3"
            append_evidenceops_actions_from_worklog_entry(
                store_path,
                {
                    "timestamp": "2026-04-03T10:00:00",
                    "task_type": "document_agent",
                    "review_type": "risk_gap_review",
                    "tool_used": "review_document_risks",
                    "query": "Liste os riscos",
                    "confidence": 0.81,
                    "needs_review": False,
                    "document_ids": ["CTR-002"],
                    "source_count": 2,
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
            )

            open_actions = list_evidenceops_action_items(store_path, status="open")
            recommended_actions = list_evidenceops_action_items(store_path, status="recommended")
            updated_action = update_evidenceops_action_item(
                store_path,
                action_id=int(open_actions[0]["id"]),
                status="in_progress",
                metadata_patch={"approved_by": "manager"},
            )
            in_progress_actions = list_evidenceops_action_items(store_path, status="in_progress")
            summary = summarize_evidenceops_action_items(store_path)

        self.assertEqual(len(open_actions), 1)
        self.assertEqual(len(recommended_actions), 1)
        self.assertEqual(updated_action["status"], "in_progress")
        self.assertEqual(updated_action["owner"], "Legal")
        self.assertEqual(updated_action["due_date"], "2026-05-01")
        self.assertEqual(updated_action["metadata"]["approved_by"], "manager")
        self.assertEqual(len(in_progress_actions), 1)
        self.assertEqual(summary["total_actions"], 2)
        self.assertEqual(summary["pending_approval_actions"], 0)

    def test_sensitive_action_updates_require_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store_path = Path(tmp_dir) / ".phase95_evidenceops_actions.sqlite3"
            append_evidenceops_actions_from_worklog_entry(
                store_path,
                {
                    "timestamp": "2026-04-03T10:00:00",
                    "task_type": "document_agent",
                    "review_type": "risk_gap_review",
                    "tool_used": "review_document_risks",
                    "query": "Liste os riscos",
                    "confidence": 0.81,
                    "needs_review": False,
                    "document_ids": ["CTR-002"],
                    "source_count": 2,
                    "action_items": [
                        {
                            "description": "Solicitar redline da cláusula de incidente",
                            "owner": "Legal",
                            "due_date": "2026-05-01",
                            "status": "open",
                            "evidence": "notify within 10 business days",
                        }
                    ],
                },
            )
            open_actions = list_evidenceops_action_items(store_path, status="open")

            with self.assertRaises(PermissionError):
                update_evidenceops_action_item(
                    store_path,
                    action_id=int(open_actions[0]["id"]),
                    status="closed",
                )

            approved_action = update_evidenceops_action_item(
                store_path,
                action_id=int(open_actions[0]["id"]),
                status="closed",
                approval_status="approved",
                approval_reason="Encerramento validado pelo gestor responsável.",
                approved_by="manager",
            )
            summary = summarize_evidenceops_action_items(store_path)

        self.assertEqual(approved_action["status"], "closed")
        self.assertEqual(approved_action["metadata"]["approval_status"], "approved")
        self.assertEqual(approved_action["metadata"]["approved_by"], "manager")
        self.assertEqual(approved_action["metadata"]["last_update_sensitivity"], "review_required")
        self.assertEqual(summary["review_required_actions"], 1)
        self.assertEqual(summary["approved_actions"], 1)
        self.assertEqual(summary["sensitive_update_count"], 1)


if __name__ == "__main__":
    unittest.main()