import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from src.structured.base import ActionItem, AgentSource, CodeAnalysisPayload, CodeIssue, ExtractionPayload, RiskItem
from src.structured.envelope import StructuredResult, TaskExecutionRequest
from src.structured.document_agent import classify_document_agent_intent, list_document_agent_tools, select_document_agent_tool
from src.structured.tasks import DocumentAgentTaskHandler
from src.storage.phase6_document_agent_log import load_document_agent_log


class DocumentAgentIntentTests(unittest.TestCase):
    def test_classify_document_agent_intent_detects_comparison(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Compare these two contracts and highlight the main differences.",
            document_count=2,
        )
        self.assertEqual(intent, "document_comparison")
        self.assertEqual(reason, "comparison_keywords_with_multiple_documents")

    def test_select_document_agent_tool_uses_checklist_tool(self) -> None:
        tool_name, answer_mode, reason = select_document_agent_tool(
            "operational_checklist",
            document_count=1,
        )
        self.assertEqual(tool_name, "generate_operational_checklist")
        self.assertEqual(answer_mode, "checklist")
        self.assertEqual(reason, "checklist_intent")

    def test_classify_document_agent_intent_detects_business_response_drafting(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Draft a response email to the client based on this contract.",
            document_count=1,
        )
        self.assertEqual(intent, "business_response_drafting")
        self.assertEqual(reason, "drafting_keywords_detected")

    def test_select_document_agent_tool_uses_business_response_drafting_tool(self) -> None:
        tool_name, answer_mode, reason = select_document_agent_tool(
            "business_response_drafting",
            document_count=1,
        )
        self.assertEqual(tool_name, "draft_business_response")
        self.assertEqual(answer_mode, "friendly")
        self.assertEqual(reason, "business_response_drafting_intent")

    def test_list_document_agent_tools_marks_comparison_unavailable_with_single_document(self) -> None:
        tools = list_document_agent_tools(document_count=1, use_document_context=True)
        compare_tool = next(item for item in tools if item["name"] == "compare_documents")
        self.assertFalse(compare_tool["available"])
        self.assertEqual(compare_tool["availability_reason"], "requires_at_least_2_documents")

    def test_classify_document_agent_intent_detects_policy_compliance_review(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Review the confidentiality and retention clauses to check compliance.",
            document_count=1,
        )
        self.assertEqual(intent, "policy_compliance_review")
        self.assertEqual(reason, "policy_compliance_keywords_detected")

    def test_classify_document_agent_intent_detects_risk_review(self) -> None:
        intent, reason = classify_document_agent_intent(
            "List the contract risks, gaps, and red flags.",
            document_count=1,
        )
        self.assertEqual(intent, "document_risk_review")
        self.assertEqual(reason, "risk_review_keywords_detected")

    def test_classify_document_agent_intent_detects_operational_extraction(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Extract the action items and next operational actions.",
            document_count=1,
        )
        self.assertEqual(intent, "operational_task_extraction")
        self.assertEqual(reason, "operational_task_keywords_detected")

    def test_classify_document_agent_intent_keeps_risk_question_as_document_question(self) -> None:
        intent, reason = classify_document_agent_intent(
            "What are the main documented risks?",
            document_count=1,
        )
        self.assertEqual(intent, "document_question")
        self.assertEqual(reason, "question_like_request_detected")

    def test_classify_document_agent_intent_detects_technical_assistance(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Review the code and API to find bugs and suggest refactoring.",
            document_count=1,
        )
        self.assertEqual(intent, "technical_assistance")
        self.assertEqual(reason, "technical_keywords_detected")


class DocumentAgentHandlerTests(unittest.TestCase):
    def test_execute_document_agent_consult_documents_returns_grounded_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="What are the main documented risks?",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="retrieval",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [
                    AgentSource(
                        source="contrato_a.pdf",
                        document_id="doc-1",
                        file_type="pdf",
                        chunk_id=1,
                        score=0.92,
                        snippet="Operational risk clause.",
                    )
                ],
                "context_text": "[Source: contract_a.pdf]\nOperational risk clause.",
                "retrieval_details": {
                    "backend_used": "chroma",
                    "backend_message": "ok",
                    "retrieval_strategy_used": "manual_hybrid",
                    "retrieval_strategy_requested": "manual_hybrid",
                },
            },
        ), patch.object(
            handler,
            "_collect_response_text",
            return_value="There is a relevant operational risk.\n- operational risk identified\n- legal review recommended",
        ):
            result = handler.execute(request)

        self.assertTrue(result.success)
        self.assertEqual(result.task_type, "document_agent")
        self.assertEqual(result.validated_output.tool_used, "consult_documents")
        self.assertEqual(result.validated_output.user_intent, "document_question")
        self.assertGreaterEqual(len(result.validated_output.sources), 1)
        self.assertGreaterEqual(len(result.validated_output.recommended_actions), 1)
        self.assertGreaterEqual(len(result.validated_output.guardrails_applied), 1)
        self.assertGreaterEqual(len(result.validated_output.available_tools), 1)
        self.assertIn("agent_tool", result.execution_metadata)
        self.assertEqual(result.execution_metadata["agent_tool"], "consult_documents")
        self.assertIn("agent_available_tools", result.execution_metadata)
        self.assertIn("agent_limitations", result.execution_metadata)
        self.assertIn("agent_guardrails_applied", result.execution_metadata)

    def test_execute_document_agent_business_response_drafting_returns_review_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="Draft a response email to the client based on this contract.",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="retrieval",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [
                    AgentSource(
                        source="contract_response.pdf",
                        document_id="doc-1",
                        file_type="pdf",
                        chunk_id=1,
                        score=0.95,
                        snippet="Reply to the client within 5 business days with schedule confirmation.",
                    )
                ],
                "context_text": "[Source: contract_response.pdf]\nReply to the client within 5 business days with schedule confirmation.",
                "retrieval_details": {
                    "backend_used": "chroma",
                    "retrieval_strategy_used": "manual_hybrid",
                    "retrieval_strategy_requested": "manual_hybrid",
                },
            },
        ), patch.object(
            handler,
            "_collect_response_text",
            return_value="Hello, we confirm receipt and will return with the schedule within 5 business days. Before the final send, validate the recipient and internal approval.",
        ):
            result = handler.execute(request)

        self.assertTrue(result.success)
        self.assertEqual(result.validated_output.tool_used, "draft_business_response")
        self.assertEqual(result.validated_output.user_intent, "business_response_drafting")
        self.assertTrue(result.validated_output.needs_review)
        self.assertEqual(result.validated_output.needs_review_reason, "business_response_draft_requires_human_approval")
        self.assertEqual(result.execution_metadata["agent_context_strategy"], "retrieval")
        self.assertIn("approval", result.validated_output.summary.lower())

    def test_execute_document_agent_consult_documents_appends_phase6_log_entry(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="What are the main documented risks?",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="retrieval",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".phase6_document_agent_log.json"
            with patch.object(handler, "_get_document_agent_log_path", return_value=log_path), patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
                handler,
                "_build_document_agent_source_bundle",
                return_value={
                    "sources": [
                        AgentSource(
                            source="contract_a.pdf",
                            document_id="doc-1",
                            file_type="pdf",
                            chunk_id=1,
                            score=0.92,
                            snippet="Operational risk clause.",
                        )
                    ],
                    "context_text": "[Source: contract_a.pdf]\nOperational risk clause.",
                    "retrieval_details": {
                        "backend_used": "chroma",
                        "retrieval_strategy_used": "manual_hybrid",
                        "retrieval_strategy_requested": "manual_hybrid",
                    },
                },
            ), patch.object(
                handler,
                "_collect_response_text",
                return_value="There is a relevant operational risk.\n- operational risk identified\n- legal review recommended",
            ):
                result = handler.execute(request)

            self.assertTrue(result.success)
            entries = load_document_agent_log(log_path)

        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["success"])
        self.assertEqual(entries[0]["user_intent"], "document_question")
        self.assertEqual(entries[0]["tool_used"], "consult_documents")
        self.assertEqual(entries[0]["answer_mode"], "friendly")
        self.assertEqual(entries[0]["source_count"], 1)
        self.assertEqual(entries[0]["retrieval_strategy_used"], "manual_hybrid")
        self.assertEqual(entries[0]["available_tools_count"], len(result.validated_output.available_tools))
        self.assertEqual(entries[0]["error_tool_runs"], 0)

    def test_execute_document_agent_logs_failure_when_tool_execution_raises(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="What are the main documented risks?",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="document_scan",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / ".phase6_document_agent_log.json"
            with patch.object(handler, "_get_document_agent_log_path", return_value=log_path), patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
                handler,
                "_build_document_agent_source_bundle",
                return_value={
                    "sources": [
                        AgentSource(
                            source="contract_a.pdf",
                            document_id="doc-1",
                            file_type="pdf",
                            chunk_id=1,
                            score=0.92,
                            snippet="Operational risk clause.",
                        )
                    ],
                    "context_text": "[Source: contract_a.pdf]\nOperational risk clause.",
                    "retrieval_details": {
                        "backend_used": "chroma",
                        "retrieval_strategy_used": "document_scan",
                        "retrieval_strategy_requested": "document_scan",
                    },
                },
            ), patch.object(
                handler,
                "_run_consult_documents_tool",
                side_effect=RuntimeError("boom during consult"),
            ):
                result = handler.execute(request)

            entries = load_document_agent_log(log_path)

        self.assertFalse(result.success)
        self.assertEqual(len(entries), 1)
        self.assertFalse(entries[0]["success"])
        self.assertEqual(entries[0]["user_intent"], "document_question")
        self.assertEqual(entries[0]["tool_used"], "consult_documents")
        self.assertTrue(entries[0]["needs_review"])
        self.assertEqual(entries[0]["needs_review_reason"], "document_agent_execution_failed")
        self.assertIn("boom during consult", entries[0]["error_message"])

    def test_execute_document_agent_policy_compliance_returns_review_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="Review the confidentiality and retention clauses to check compliance.",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="document_scan",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        extraction_result = StructuredResult(
            success=True,
            task_type="extraction",
            parsed_json={},
            validated_output=ExtractionPayload(
                task_type="extraction",
                main_subject="Master contract",
                extracted_fields=[
                    {"name": "confidentiality_clause", "value": "Data must remain confidential for 5 years", "evidence": "confidential for five years"},
                    {"name": "retention_period", "value": "5 years", "evidence": "records must be retained for five years"},
                ],
                risks=[RiskItem(description="Risk of non-compliance with document retention", evidence="records must be retained for five years")],
                action_items=[ActionItem(description="Validate the retention process with the legal team", evidence="records must be retained for five years")],
                missing_information=["There is no explicit owner for continuous monitoring."],
            ),
            quality_score=0.81,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [
                    AgentSource(
                        source="master_contract.pdf",
                        document_id="doc-1",
                        file_type="pdf",
                        chunk_id=2,
                        score=0.91,
                        snippet="records must be retained for five years",
                    )
                ],
                "context_text": "[Source: master_contract.pdf]\nrecords must be retained for five years",
                "retrieval_details": {},
            },
        ), patch.object(handler, "_run_nested_structured_task", return_value=extraction_result):
            result = handler.execute(request)

        self.assertTrue(result.success)
        self.assertEqual(result.validated_output.tool_used, "review_policy_compliance")
        self.assertEqual(result.validated_output.user_intent, "policy_compliance_review")
        self.assertEqual(result.validated_output.structured_response.get("review_type"), "policy_compliance")
        self.assertGreaterEqual(len(result.validated_output.key_points), 1)

    def test_execute_document_agent_risk_review_returns_review_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="List the contract risks, gaps, and red flags.",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="document_scan",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        extraction_result = StructuredResult(
            success=True,
            task_type="extraction",
            parsed_json={},
            validated_output=ExtractionPayload(
                task_type="extraction",
                main_subject="Supply contract",
                risks=[RiskItem(description="Contract penalty without a clear operational owner", evidence="penalty applies if delivery misses deadline")],
                action_items=[ActionItem(description="Define an owner to track deadlines", evidence="delivery deadline is binding")],
                missing_information=["The document does not specify who monitors the SLA."],
            ),
            quality_score=0.79,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [AgentSource(source="supply_contract.pdf", document_id="doc-1", file_type="pdf", chunk_id=1, score=0.9, snippet="penalty applies if delivery misses deadline")],
                "context_text": "[Source: supply_contract.pdf]\npenalty applies if delivery misses deadline",
                "retrieval_details": {},
            },
        ), patch.object(handler, "_run_nested_structured_task", return_value=extraction_result):
            result = handler.execute(request)

        self.assertTrue(result.success)
        self.assertEqual(result.validated_output.tool_used, "review_document_risks")
        self.assertEqual(result.validated_output.user_intent, "document_risk_review")
        self.assertEqual(result.validated_output.structured_response.get("review_type"), "risk_gap_review")
        self.assertGreaterEqual(len(result.validated_output.key_points), 1)

    def test_execute_document_agent_operational_extraction_returns_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="Extract the action items and next operational actions.",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="document_scan",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        extraction_result = StructuredResult(
            success=True,
            task_type="extraction",
            parsed_json={},
            validated_output=ExtractionPayload(
                task_type="extraction",
                main_subject="Operational plan",
                important_dates=["2026-04-05"],
                risks=[RiskItem(description="Dependency on external approval", evidence="approval required before launch")],
                action_items=[
                    ActionItem(description="Publish internal communication", due_date="2026-04-05", evidence="send internal comms by April 5"),
                    ActionItem(description="Confirm rollout with operations", evidence="confirm rollout with operations"),
                ],
            ),
            quality_score=0.8,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [AgentSource(source="operational_plan.pdf", document_id="doc-1", file_type="pdf", chunk_id=3, score=0.89, snippet="send internal comms by April 5")],
                "context_text": "[Source: operational_plan.pdf]\nsend internal comms by April 5",
                "retrieval_details": {},
            },
        ), patch.object(handler, "_run_nested_structured_task", return_value=extraction_result):
            result = handler.execute(request)

        self.assertTrue(result.success)
        self.assertEqual(result.validated_output.tool_used, "extract_operational_tasks")
        self.assertEqual(result.validated_output.user_intent, "operational_task_extraction")
        self.assertEqual(result.validated_output.structured_response.get("review_type"), "operational_extraction")
        self.assertGreaterEqual(len(result.validated_output.checklist_preview), 1)

    def test_execute_document_agent_technical_assistance_returns_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="Review the code and API to find bugs and suggest refactoring.",
            use_document_context=True,
            source_document_ids=["doc-1"],
            context_strategy="retrieval",
            provider="ollama",
            model="qwen2.5:7b",
            temperature=0.1,
            context_window=8192,
        )

        technical_result = StructuredResult(
            success=True,
            task_type="code_analysis",
            parsed_json={},
            validated_output=CodeAnalysisPayload(
                task_type="code_analysis",
                snippet_summary="This snippet handles integration with an external API.",
                main_purpose="Send requests to synchronize data.",
                detected_issues=[
                    CodeIssue(severity="high", category="runtime_failure", title="Unhandled timeout", description="The call may fail without retry.", evidence="requests.get(...)", recommendation="Add timeout handling and controlled retry."),
                ],
                refactor_plan=["Extract an HTTP client with explicit timeout."],
                test_suggestions=["Add a test that simulates an API timeout."],
                risk_notes=["An integration failure can interrupt synchronization."],
            ),
            quality_score=0.8,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [AgentSource(source="api_client.py", document_id="doc-1", file_type="py", chunk_id=1, score=0.95, snippet="requests.get(...)")],
                "context_text": "[Source: api_client.py]\nrequests.get(...)",
                "retrieval_details": {},
            },
        ), patch.object(handler, "_run_nested_structured_task", return_value=technical_result):
            result = handler.execute(request)

        self.assertTrue(result.success)
        self.assertEqual(result.validated_output.tool_used, "assist_technical_document")
        self.assertEqual(result.validated_output.user_intent, "technical_assistance")
        self.assertEqual(result.validated_output.structured_response.get("review_type"), "technical_review")
        self.assertTrue(result.validated_output.needs_review)


if __name__ == "__main__":
    unittest.main()