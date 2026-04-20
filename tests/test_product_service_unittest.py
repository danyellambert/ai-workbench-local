import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.product.models import GroundingPreview, ProductWorkflowRequest, ProductWorkflowResult
from src.product.service import (
    build_grounding_preview,
    build_product_workflow_catalog,
    build_product_workflow_frontend_contract,
    generate_product_workflow_deck,
    publish_product_workflow_to_trello,
    list_product_documents,
    run_product_workflow,
)
from src.structured.base import CVAnalysisPayload, ComparisonFinding, DocumentAgentPayload
from src.structured.envelope import StructuredResult


class ProductServiceTests(unittest.TestCase):
    def _sample_document_agent_result(self, *, comparison: bool = False) -> StructuredResult:
        payload = DocumentAgentPayload(
            task_type="document_agent",
            user_intent="document_comparison" if comparison else "document_review",
            intent_reason="Grounded document workflow requested.",
            answer_mode="review",
            tool_used="compare_documents" if comparison else "review_document_risks",
            summary=(
                "The comparison surfaces material policy deltas that still require final human validation."
                if comparison
                else "The document review highlights grounded risks, gaps and recommended follow-up actions."
            ),
            key_points=[
                "Main grounded signal captured.",
                "Operational follow-up is required.",
            ],
            limitations=[],
            recommended_actions=["Validate the findings with a final human review."],
            compared_documents=["Policy A", "Policy B"] if comparison else [],
            comparison_findings=(
                [
                    ComparisonFinding(
                        finding_type="obligation_change",
                        title="Formal approval became mandatory",
                        description="The new version requires formal approval before onboarding.",
                        documents=["Policy A", "Policy B"],
                        evidence=["Page 4"],
                    )
                ]
                if comparison
                else []
            ),
            structured_response={"review_type": "policy_compliance" if comparison else "document_review"},
        )
        source_documents = ["doc-1", "doc-2"] if comparison else ["doc-1"]
        return StructuredResult(success=True, task_type="document_agent", validated_output=payload, source_documents=source_documents)

    def test_build_product_workflow_catalog_exposes_four_core_workflows(self) -> None:
        catalog = build_product_workflow_catalog()

        self.assertEqual(set(catalog.keys()), {
            "document_review",
            "policy_contract_comparison",
            "action_plan_evidence_review",
            "candidate_review",
        })
        self.assertEqual(catalog["candidate_review"].default_export_kind, "candidate_review_deck")

    def test_build_product_workflow_frontend_contract_exposes_phase_10_25_metadata(self) -> None:
        contract = build_product_workflow_frontend_contract()

        self.assertEqual(contract["contract_version"], "product_workflows.v1")
        self.assertEqual(contract["product_headline"], "Decision workflows grounded in documents")
        self.assertEqual(contract["workflow_count"], 4)

        workflows = {item["workflow_id"]: item for item in contract["workflows"]}
        self.assertEqual(workflows["document_review"]["preferred_context_strategy"], "retrieval")
        self.assertTrue(workflows["policy_contract_comparison"]["example_prompts"])
        self.assertTrue(workflows["action_plan_evidence_review"]["expected_outputs"])
        self.assertEqual(workflows["candidate_review"]["workflow_contract"], "docs/EXECUTIVE_DECK_GENERATION_CANDIDATE_REVIEW_DECK_CONTRACT_V1.md")

    def test_build_grounding_preview_returns_context_metadata(self) -> None:
        with patch("src.product.service.build_structured_document_context", return_value="[Source: doc]\nhello world"):
            preview = build_grounding_preview(query="hello", document_ids=["doc-1"], strategy="document_scan")

        self.assertEqual(preview.context_chars, len("[Source: doc]\nhello world"))
        self.assertEqual(preview.source_block_count, 1)
        self.assertEqual(preview.document_ids, ["doc-1"])

    def test_run_product_workflow_candidate_review_uses_cv_analysis_engine(self) -> None:
        structured_result = StructuredResult(
            success=True,
            task_type="cv_analysis",
            validated_output=CVAnalysisPayload(
                personal_info={"full_name": "Ada Candidate", "location": "Remote"},
                skills=["Python", "LLM Ops"],
                strengths=["Strong product thinking"],
                improvement_areas=["Needs deeper stakeholder examples"],
                experience_years=7.0,
                experience_entries=[
                    {
                        "title": "Senior Applied AI Engineer",
                        "organization": "Acme",
                        "date_range": "2019-2026",
                        "bullets": ["Led applied AI delivery", "Worked with product stakeholders"],
                    }
                ],
            ),
        )
        request = ProductWorkflowRequest(
            workflow_id="candidate_review",
            document_ids=["cv-1"],
            provider="ollama",
            model="qwen2.5:7b",
        )

        with (
            patch("src.product.service.build_structured_document_context", return_value="[Source: cv-1]\nAda Candidate"),
            patch("src.product.service.run_structured_execution_workflow", return_value=structured_result) as workflow_mock,
        ):
            result = run_product_workflow(request)

        self.assertEqual(result.workflow_id, "candidate_review")
        self.assertEqual(result.workflow_label, "Candidate Review")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.deck_export_kind, "candidate_review_deck")
        self.assertTrue(result.deck_available)
        self.assertIn("Ada Candidate", result.summary)
        self.assertIn("Advance the candidate", result.recommendation or "")
        self.assertEqual(workflow_mock.call_args.kwargs["strategy"], "direct")
        self.assertEqual(workflow_mock.call_args.args[0].task_type, "cv_analysis")

    def test_run_product_workflow_document_review_uses_document_agent_workflow_and_retrieval(self) -> None:
        structured_result = self._sample_document_agent_result()
        request = ProductWorkflowRequest(
            workflow_id="document_review",
            document_ids=["doc-1"],
            provider="ollama",
            model="qwen2.5:7b",
        )

        with (
            patch("src.product.service.build_structured_document_context", return_value="[Source: doc-1]\nPolicy text"),
            patch("src.product.service.run_structured_execution_workflow", return_value=structured_result) as workflow_mock,
        ):
            result = run_product_workflow(request)

        execution_request = workflow_mock.call_args.args[0]
        self.assertEqual(result.workflow_id, "document_review")
        self.assertEqual(result.deck_export_kind, "document_review_deck")
        self.assertEqual(workflow_mock.call_args.kwargs["strategy"], "langgraph_context_retry")
        self.assertEqual(execution_request.task_type, "document_agent")
        self.assertEqual(execution_request.context_strategy, "retrieval")
        self.assertIn("top blockers", execution_request.input_text.lower())
        self.assertEqual(execution_request.telemetry["agent_intent"], "document_risk_review")
        self.assertEqual(execution_request.telemetry["agent_tool"], "review_document_risks")
        self.assertTrue(execution_request.telemetry["document_review_findings_synthesis_enabled"])
        self.assertEqual(execution_request.telemetry["document_review_findings_prompt_style"], "hybrid")
        self.assertEqual(result.debug_metadata["workflow_contract"], "docs/EXECUTIVE_DECK_GENERATION_DOCUMENT_REVIEW_DECK_CONTRACT_V1.md")
        self.assertIn("Document Review deck artifact", result.debug_metadata["expected_outputs"])

    def test_run_product_workflow_policy_comparison_uses_two_docs_and_comparison_deck(self) -> None:
        structured_result = self._sample_document_agent_result(comparison=True)
        request = ProductWorkflowRequest(
            workflow_id="policy_contract_comparison",
            document_ids=["doc-a", "doc-b"],
            provider="ollama",
            model="qwen2.5:7b",
        )

        with (
            patch("src.product.service.build_structured_document_context", return_value="[Source: doc-a]\nPolicy A\n[Source: doc-b]\nPolicy B"),
            patch("src.product.service.run_structured_execution_workflow", return_value=structured_result) as workflow_mock,
        ):
            result = run_product_workflow(request)

        execution_request = workflow_mock.call_args.args[0]
        self.assertEqual(result.workflow_id, "policy_contract_comparison")
        self.assertEqual(result.deck_export_kind, "policy_contract_comparison_deck")
        self.assertEqual(execution_request.context_strategy, "retrieval")
        self.assertEqual(execution_request.telemetry["agent_intent"], "document_comparison")
        self.assertEqual(execution_request.telemetry["agent_tool"], "compare_documents")
        self.assertEqual(result.debug_metadata["deck_export_label"], "Policy / Contract Comparison Deck")
        self.assertIn("Formal approval became mandatory", result.highlights)

    def test_run_product_workflow_action_plan_accepts_text_only_request(self) -> None:
        structured_result = self._sample_document_agent_result()
        request = ProductWorkflowRequest(
            workflow_id="action_plan_evidence_review",
            document_ids=[],
            input_text="Turn these findings into an execution plan.",
            provider="ollama",
            model="qwen2.5:7b",
        )

        with (
            patch("src.product.service.build_structured_document_context", return_value="[Source: memo]\nAction backlog"),
            patch("src.product.service.run_structured_execution_workflow", return_value=structured_result) as workflow_mock,
        ):
            result = run_product_workflow(request)

        execution_request = workflow_mock.call_args.args[0]
        self.assertEqual(result.workflow_id, "action_plan_evidence_review")
        self.assertEqual(result.deck_export_kind, "action_plan_deck")
        self.assertEqual(execution_request.context_strategy, "document_scan")
        self.assertEqual(execution_request.telemetry["agent_intent"], "operational_task_extraction")
        self.assertEqual(execution_request.telemetry["agent_tool"], "extract_operational_tasks")
        self.assertEqual(result.debug_metadata["preferred_context_strategy"], "document_scan")
        self.assertIn("Action Plan deck artifact", result.debug_metadata["expected_outputs"])


    def test_generate_product_workflow_deck_uses_current_action_plan_items_instead_of_global_action_store(self) -> None:
        payload = DocumentAgentPayload(
            task_type="document_agent",
            user_intent="action_plan_evidence_review",
            answer_mode="friendly",
            tool_used="extract_operational_tasks",
            summary="Governance Committee Minutes and Action Items: 0 actionable task(s), 0 deadline(s) and 0 operational risk(s) identified.",
            recommended_actions=["Open the cited source excerpts to confirm the interpretation before acting."],
            structured_response={
                "actions": [],
                "extraction_payload": {
                    "task_type": "extraction",
                    "main_subject": "Governance Committee Minutes and Action Items",
                    "action_items": [],
                    "risks": [],
                    "missing_information": [],
                },
            },
            sources=[
                {
                    "source": "Governance Committee Minutes and Action Items.pdf",
                    "document_id": "doc-minutes",
                    "chunk_id": 1,
                    "score": 0.94,
                    "snippet": "Negotiate liability cap with vendor legal Maria Santos 2024-03-22 In progress CTR-010 Section 7.3",
                }
            ],
            confidence=0.67,
            needs_review=True,
            needs_review_reason="operational_extraction_without_grounded_actions",
        )
        result = ProductWorkflowResult(
            workflow_id="action_plan_evidence_review",
            workflow_label="Action Plan / Evidence Review",
            status="warning",
            summary="Governance Committee Minutes and Action Items: 0 actionable task(s), 0 deadline(s) and 0 operational risk(s) identified.",
            recommendation="Open the cited source excerpts to confirm the interpretation before acting.",
            structured_result=StructuredResult(success=True, task_type="document_agent", validated_output=payload),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["doc-minutes"],
                context_chars=1200,
                source_block_count=1,
                preview_text="[Source: Governance Committee Minutes and Action Items.pdf] Action Register Action Item Owner Due Date Status Evidence / Source Negotiate liability cap with vendor legal Maria Santos 2024-03-22 In progress CTR-010 Section 7.3 unlimited liability clause",
            ),
            deck_export_kind="action_plan_deck",
            deck_available=True,
        )

        with patch("src.product.service.generate_executive_deck", return_value={"status": "completed", "local_pptx_path": "", "local_contract_path": "", "local_payload_path": "", "local_review_path": "", "local_preview_manifest_path": "", "local_thumbnail_sheet_path": ""}) as export_mock:
            generate_product_workflow_deck(result, settings=type("S", (), {"local_artifact_dir": "/tmp", "enabled": True, "base_url": "http://127.0.0.1:8787", "enabled_export_kinds": []})())

        kwargs = export_mock.call_args.kwargs
        explicit_entries = kwargs.get("evidenceops_action_entries")
        self.assertTrue(explicit_entries)
        self.assertEqual(explicit_entries[0]["description"], "Negotiate liability cap with vendor legal")
        self.assertEqual(explicit_entries[0]["owner"], "Maria Santos")
        self.assertEqual(explicit_entries[0]["kanban_stage"], "Doing")
        self.assertIn("Priority: Critical", explicit_entries[0]["trello_labels"])
        self.assertEqual(kwargs.get("phase95_evidenceops_action_store_path"), None)

    def test_publish_product_workflow_to_trello_uses_external_target_service(self) -> None:
        result = ProductWorkflowResult(
            workflow_id="action_plan_evidence_review",
            workflow_label="Action Plan / Evidence Review",
            status="warning",
            summary="Current run produced 2 actionable items.",
            recommendation="Publish the two critical actions to Trello.",
            deck_export_kind="action_plan_deck",
            deck_available=True,
        )

        with patch(
            "src.product.service.create_trello_cards_from_product_result",
            return_value={
                "status": "success",
                "dry_run": False,
                "created_card_count": 2,
                "target_board_id": "board-1",
                "message": "Published 2 card(s) to Trello — Open: 2",
            },
        ) as trello_mock:
            payload = publish_product_workflow_to_trello(result, dry_run=False)

        trello_mock.assert_called_once_with(result, dry_run=False, max_cards=8, preview_payload=None, selected_card_index=None)
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["created_card_count"], 2)
        self.assertIn("Published 2 card(s) to Trello", payload["message"])

    def test_run_product_workflow_candidate_review_surfaces_warning_when_cv_is_sparse(self) -> None:
        structured_result = StructuredResult(
            success=True,
            task_type="cv_analysis",
            validated_output=CVAnalysisPayload(
                personal_info={"location": "Remote"},
                skills=[],
                strengths=[],
                improvement_areas=[],
                experience_years=0.0,
                experience_entries=[],
            ),
        )
        request = ProductWorkflowRequest(
            workflow_id="candidate_review",
            document_ids=["cv-1"],
            provider="ollama",
            model="qwen2.5:7b",
        )

        with (
            patch("src.product.service.build_structured_document_context", return_value="[Source: cv-1]\nSparse CV"),
            patch("src.product.service.run_structured_execution_workflow", return_value=structured_result),
        ):
            result = run_product_workflow(request)

        self.assertEqual(result.status, "warning")
        self.assertTrue(result.warnings)
        self.assertTrue(any("experience" in item.lower() or "skill" in item.lower() for item in result.warnings))
        self.assertIn("Hold before advancing", result.recommendation or "")

    def test_list_product_documents_reads_current_rag_store(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            rag_store_path = temp_path / ".rag_store.json"
            rag_store_path.write_text(
                '{"documents":[{"document_id":"doc-1","name":"Policy A","file_type":"pdf","char_count":1200,"chunk_count":4,"indexed_at":"2026-04-05 19:00:00","loader_metadata":{"loader_strategy_label":"Manual local"}}],"chunks":[],"settings":{},"updated_at":"2026-04-05 19:00:00"}',
                encoding="utf-8",
            )

            class FakeRagSettings:
                store_path = rag_store_path
                chunk_size = 1200
                chunk_overlap = 80
                top_k = 4
                rerank_pool_size = 8
                rerank_lexical_weight = 0.35
                loader_strategy = "manual"
                chunking_strategy = "manual"
                retrieval_strategy = "manual_hybrid"
                embedding_provider = "ollama"
                embedding_model = "embeddinggemma:300m"
                embedding_context_window = 512
                embedding_truncate = True
                chroma_path = temp_path / ".chroma_rag"
                context_budget_ratio = 0.45
                pdf_extraction_mode = "hybrid"
                pdf_docling_enabled = True
                pdf_docling_ocr_enabled = True
                pdf_docling_force_full_page_ocr = False
                pdf_docling_picture_description = False
                pdf_ocr_fallback_enabled = True
                pdf_ocr_fallback_languages = "eng+por"

            documents = list_product_documents(FakeRagSettings())

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].document_id, "doc-1")
        self.assertEqual(documents[0].loader_strategy_label, "Manual local")


if __name__ == "__main__":
    unittest.main()