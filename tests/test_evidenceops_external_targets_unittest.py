from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path

from src.config import (
    EvidenceOpsExternalSettings,
    NextcloudWebDavSettings,
    NotionSettings,
    TrelloSettings,
)
from src.product.models import GroundingPreview, ProductWorkflowResult
from src.services.evidenceops_external_targets import create_trello_cards_from_product_result
from src.services.evidenceops_external_targets import (
    create_notion_page_from_product_result,
    create_notion_smoke_page,
    list_notion_database_entries,
)
from src.structured.base import ContactInfo, CVAnalysisPayload, DocumentAgentPayload
from src.structured.envelope import StructuredResult


def _fake_external_settings() -> EvidenceOpsExternalSettings:
    return EvidenceOpsExternalSettings(
        repository_backend="local",
        external_sync_enabled=True,
        corpus_primary_root=Path("data"),
        corpus_public_root=Path("data"),
        nextcloud=NextcloudWebDavSettings(
            base_url="",
            username="",
            app_password="",
            root_path="/documents",
        ),
        trello=TrelloSettings(
            api_key="key",
            token="token",
            board_id="board",
            list_open_id="open-list",
            list_review_id="review-list",
            list_approved_id="approved-list",
            list_done_id="done-list",
        ),
        notion=NotionSettings(
            api_key="",
            database_id="",
            parent_page_id="",
        ),
    )


class EvidenceOpsExternalTargetsTests(unittest.TestCase):
    def test_create_trello_cards_from_product_result_uses_action_plan_items_for_document_agent(self) -> None:
        payload = DocumentAgentPayload(
            user_intent="operational_task_extraction",
            answer_mode="friendly",
            tool_used="extract_operational_tasks",
            summary="Two operational follow-ups were identified.",
            recommended_actions=["Coordinate the follow-up with finance."],
            needs_review=True,
            needs_review_reason="Approval owner should validate the next action.",
            structured_response={
                "review_type": "operational_task_extraction",
                "extraction_payload": {
                    "action_items": [
                        {
                            "description": "Contact finance team about missing approval",
                            "owner": "Ana",
                            "due_date": "2026-04-20",
                            "status": "suggested",
                            "evidence": "Budget line item is missing an approval signature.",
                        },
                        {
                            "description": "Contact finance team about missing approval",
                            "owner": "Ana",
                            "due_date": "2026-04-20",
                        },
                    ]
                },
            },
        )
        result = ProductWorkflowResult(
            workflow_id="action_plan_evidence_review",
            workflow_label="Action Plan / Evidence Review",
            status="warning",
            summary="Prepare an action plan for the missing approval workflow.",
            recommendation="Coordinate the approval follow-up with finance.",
            structured_result=StructuredResult(
                success=True,
                task_type="document_agent",
                validated_output=payload,
            ),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["DOC-001"],
                context_chars=1200,
                source_block_count=3,
                preview_text="Grounded context preview",
            ),
            highlights=["Approval signature missing in the source document."],
            warnings=["Human approval is recommended before execution."],
        )

        response = create_trello_cards_from_product_result(
            result,
            settings=_fake_external_settings(),
            dry_run=True,
        )

        self.assertEqual(response["status"], "planned")
        self.assertEqual(response["card_mode"], "action_plan_items")
        self.assertEqual(response["planned_card_count"], 1)
        self.assertEqual(response["planned_cards"][0]["list_id"], "open-list")
        self.assertIn("Contact finance team about missing approval", response["planned_cards"][0]["name"])
        self.assertIn("Owner: Ana", response["planned_cards"][0]["description"])
        self.assertIn("Documents: DOC-001", response["planned_cards"][0]["description"])


    @patch("src.services.evidenceops_external_targets.build_action_plan_view")
    def test_create_trello_cards_from_action_plan_view_maps_statuses_to_matching_lists(self, build_view_mock) -> None:
        build_view_mock.return_value = {
            "items": [
                {"title": "Collect missing approvals", "owner": "Ana", "due_date": "2026-04-20", "status": "open", "source": "Approval Email.pdf", "evidence": "Approval email missing."},
                {"title": "Close temporary exception", "owner": "Bruno", "due_date": "2026-04-21", "status": "in_progress", "source": "Evidence Log.pdf", "evidence": "Exception is being closed."},
                {"title": "Obtain governance sign-off", "owner": "Clara", "due_date": "2026-04-22", "status": "blocked", "source": "Committee Minutes.pdf", "evidence": "Pending committee decision."},
                {"title": "Archive closure note", "owner": "Diego", "due_date": "2026-04-23", "status": "done", "source": "Closure Note.pdf", "evidence": "Closure note filed."},
            ]
        }
        result = ProductWorkflowResult(
            workflow_id="action_plan_evidence_review",
            workflow_label="Action Plan / Evidence Review",
            status="warning",
            summary="Operational follow-up actions were identified.",
            recommendation="Publish the grounded action plan to Trello.",
            structured_result=StructuredResult(success=True, task_type="document_agent", validated_output=None),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["DOC-001", "DOC-002"],
                context_chars=1200,
                source_block_count=3,
                preview_text="Grounded context preview",
            ),
        )

        response = create_trello_cards_from_product_result(result, settings=_fake_external_settings(), dry_run=True)

        self.assertEqual(response["card_mode"], "action_plan_items")
        self.assertEqual(response["planned_card_count"], 4)
        self.assertEqual([card["list_id"] for card in response["planned_cards"]], ["open-list", "approved-list", "review-list", "done-list"])
        self.assertEqual(response["list_breakdown"], [
            {"list_id": "open-list", "list_label": "Open", "count": 1},
            {"list_id": "review-list", "list_label": "Review", "count": 1},
            {"list_id": "approved-list", "list_label": "Approved", "count": 1},
            {"list_id": "done-list", "list_label": "Done", "count": 1},
        ])
        self.assertIn("Open: 1", response["message"])
        self.assertIn("Approved: 1", response["message"])
        self.assertIn("Done: 1", response["message"])

    def test_create_trello_cards_from_product_result_falls_back_to_summary_for_candidate_review(self) -> None:
        payload = CVAnalysisPayload(
            personal_info=ContactInfo(full_name="Maria Silva", location="São Paulo"),
            skills=["Python", "LLMs"],
            strengths=["Strong applied AI delivery background"],
        )
        result = ProductWorkflowResult(
            workflow_id="candidate_review",
            workflow_label="Candidate Review",
            status="completed",
            summary="Candidate shows strong experience in applied AI delivery.",
            recommendation="Advance to the next stage with a focused technical interview.",
            structured_result=StructuredResult(
                success=True,
                task_type="cv_analysis",
                validated_output=payload,
            ),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["CV-001"],
                context_chars=800,
                source_block_count=2,
                preview_text="Candidate grounding preview",
            ),
            highlights=["Applied AI and Python experience detected."],
        )

        response = create_trello_cards_from_product_result(
            result,
            settings=_fake_external_settings(),
            dry_run=True,
        )

        self.assertEqual(response["status"], "planned")
        self.assertEqual(response["card_mode"], "summary")
        self.assertEqual(response["planned_card_count"], 1)
        self.assertIn("Maria Silva", response["planned_cards"][0]["name"])
        self.assertEqual(response["planned_cards"][0]["list_id"], "open-list")

    def test_create_notion_smoke_page_dry_run_returns_plan(self) -> None:
        settings = _fake_external_settings()
        settings = settings.__class__(
            repository_backend=settings.repository_backend,
            external_sync_enabled=settings.external_sync_enabled,
            corpus_primary_root=settings.corpus_primary_root,
            corpus_public_root=settings.corpus_public_root,
            nextcloud=settings.nextcloud,
            trello=settings.trello,
            notion=NotionSettings(
                api_key="notion-key",
                database_id="database-123",
                parent_page_id="",
            ),
        )
        response = create_notion_smoke_page(
            settings=settings,
            dry_run=True,
        )

        self.assertEqual(response["status"], "planned")
        self.assertTrue(response["dry_run"])
        self.assertEqual(response["database_id"], "database-123")

    @patch("src.services.evidenceops_external_targets.NotionClient.query_database")
    def test_list_notion_database_entries_normalizes_response(self, query_database_mock) -> None:
        query_database_mock.return_value = {
            "results": [
                {
                    "id": "page-123",
                    "url": "https://www.notion.so/page-123",
                    "created_time": "2026-04-16T00:00:00.000Z",
                    "last_edited_time": "2026-04-16T00:05:00.000Z",
                    "properties": {
                        "Name": {
                            "title": [
                                {"plain_text": "Smoke page"},
                            ]
                        }
                    },
                }
            ]
        }
        settings = _fake_external_settings()
        settings = settings.__class__(
            repository_backend=settings.repository_backend,
            external_sync_enabled=settings.external_sync_enabled,
            corpus_primary_root=settings.corpus_primary_root,
            corpus_public_root=settings.corpus_public_root,
            nextcloud=settings.nextcloud,
            trello=settings.trello,
            notion=NotionSettings(
                api_key="notion-key",
                database_id="database-123",
                parent_page_id="",
            ),
        )

        response = list_notion_database_entries(settings=settings, limit=5)

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["entry_count"], 1)
        self.assertEqual(response["entries"][0]["title"], "Smoke page")
        self.assertEqual(response["entries"][0]["page_url"], "https://www.notion.so/page-123")

    def test_create_notion_page_from_product_result_dry_run_uses_workflow_result(self) -> None:
        payload = CVAnalysisPayload(
            personal_info=ContactInfo(full_name="Maria Silva", location="São Paulo"),
            skills=["Python", "LLMs"],
        )
        result = ProductWorkflowResult(
            workflow_id="candidate_review",
            workflow_label="Candidate Review",
            status="completed",
            summary="Candidate shows strong experience in applied AI delivery.",
            recommendation="Advance to the next stage with a focused technical interview.",
            structured_result=StructuredResult(
                success=True,
                task_type="cv_analysis",
                validated_output=payload,
            ),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["CV-001"],
                context_chars=800,
                source_block_count=2,
                preview_text="Candidate grounding preview",
            ),
            highlights=["Applied AI and Python experience detected."],
        )
        settings = _fake_external_settings()
        settings = settings.__class__(
            repository_backend=settings.repository_backend,
            external_sync_enabled=settings.external_sync_enabled,
            corpus_primary_root=settings.corpus_primary_root,
            corpus_public_root=settings.corpus_public_root,
            nextcloud=settings.nextcloud,
            trello=settings.trello,
            notion=NotionSettings(
                api_key="notion-key",
                database_id="database-123",
                parent_page_id="",
            ),
        )

        response = create_notion_page_from_product_result(
            result,
            settings=settings,
            dry_run=True,
        )

        self.assertEqual(response["status"], "planned")
        self.assertEqual(response["workflow_id"], "candidate_review")
        self.assertIn("Maria Silva", response["title"])


if __name__ == "__main__":
    unittest.main()