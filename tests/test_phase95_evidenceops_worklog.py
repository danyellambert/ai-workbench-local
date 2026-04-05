import tempfile
import unittest
from pathlib import Path

from src.services.evidenceops_worklog import build_evidenceops_worklog_entry
from src.storage.phase95_evidenceops_worklog import (
    append_evidenceops_worklog_entry,
    load_evidenceops_worklog,
    summarize_evidenceops_worklog,
)
from src.structured.base import (
    ActionItem,
    AgentSource,
    ComparisonFinding,
    DocumentAgentPayload,
)


class Phase95EvidenceOpsWorklogTests(unittest.TestCase):
    def test_build_evidenceops_worklog_entry_extracts_findings_and_actions(self) -> None:
        payload = DocumentAgentPayload(
            user_intent="document_risk_review",
            answer_mode="friendly",
            tool_used="review_document_risks",
            summary="Contrato analisado com riscos relevantes.",
            recommended_actions=["Atualizar cláusula de incidente", "Revisar subprocessor list"],
            limitations=["Falta evidência para um controle"],
            guardrails_applied=["Grounded only"],
            structured_response={
                "review_type": "risk_gap_review",
                "gaps": ["Prazo de deleção não está explícito"],
                "extraction_payload": {
                    "risks": [
                        {
                            "description": "Notificação de incidente está fraca",
                            "impact": "Resposta tardia",
                            "owner": "Legal",
                            "due_date": "2026-05-01",
                            "evidence": "notify within 10 business days",
                        }
                    ],
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
            },
            sources=[AgentSource(source="CTR-002", document_id="CTR-002", snippet="notify within 10 business days")],
            confidence=0.81,
            needs_review=False,
        )

        entry = build_evidenceops_worklog_entry(
            payload=payload,
            query="Liste os riscos do contrato",
            document_ids=["CTR-002"],
            execution_metadata={"workflow_id": "wf-123", "execution_strategy_used": "langgraph_context_retry"},
        )

        self.assertEqual(entry["review_type"], "risk_gap_review")
        self.assertEqual(len(entry["findings"]), 2)
        self.assertEqual(len(entry["action_items"]), 1)
        self.assertEqual(entry["finding_count"], 2)
        self.assertEqual(entry["action_item_count"], 1)
        self.assertEqual(entry["action_items"][0]["owner"], "Legal")
        self.assertEqual(entry["source_documents"][0], "CTR-002")
        self.assertEqual(entry["evidence_pack"]["findings_count"], 2)
        self.assertEqual(entry["evidence_pack"]["finding_type_counts"]["risk"], 1)
        self.assertEqual(entry["evidence_pack"]["status_counts"]["open"], 1)

    def test_summarize_evidenceops_worklog_aggregates_review_types_owners_and_statuses(self) -> None:
        entries = [
            {
                "timestamp": "2026-04-03T10:00:00",
                "review_type": "risk_gap_review",
                "tool_used": "review_document_risks",
                "confidence": 0.8,
                "needs_review": False,
                "document_ids": ["CTR-001", "CTR-002"],
                "source_count": 2,
                "findings": [{"finding_type": "risk"}, {"finding_type": "gap"}],
                "action_items": [{"owner": "Legal", "status": "open", "due_date": "2026-05-01"}],
                "recommended_actions": ["Do X", "Do Y"],
            },
            {
                "timestamp": "2026-04-03T10:05:00",
                "review_type": "operational_extraction",
                "tool_used": "extract_operational_tasks",
                "confidence": 0.7,
                "needs_review": True,
                "document_ids": ["CTR-002", "POL-009"],
                "source_count": 1,
                "findings": [{"finding_type": "risk"}],
                "action_items": [
                    {"owner": "Compliance", "status": "open", "due_date": "2026-05-01"},
                    {"owner": "Compliance", "status": "in_progress", "due_date": "2026-05-15"},
                ],
                "recommended_actions": ["Do Z"],
            },
        ]

        summary = summarize_evidenceops_worklog(entries)

        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["total_findings"], 3)
        self.assertEqual(summary["total_action_items"], 3)
        self.assertEqual(summary["total_recommended_actions"], 3)
        self.assertEqual(summary["unique_document_count"], 3)
        self.assertEqual(summary["review_type_counts"]["risk_gap_review"], 1)
        self.assertEqual(summary["finding_type_counts"]["risk"], 2)
        self.assertEqual(summary["owner_counts"]["Compliance"], 2)
        self.assertEqual(summary["status_counts"]["open"], 2)
        self.assertEqual(summary["due_date_counts"]["2026-05-01"], 2)

    def test_append_and_load_evidenceops_worklog_entry_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".phase95_evidenceops_worklog.json"
            append_evidenceops_worklog_entry(
                log_path,
                {
                    "timestamp": "2026-04-03T10:00:00",
                    "review_type": "contract_gap_detection",
                    "tool_used": "compare_documents",
                    "findings": [{"finding_type": "comparison"}],
                    "action_items": [],
                    "recommended_actions": ["Revisar cláusulas"],
                },
            )

            entries = load_evidenceops_worklog(log_path)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["tool_used"], "compare_documents")


if __name__ == "__main__":
    unittest.main()