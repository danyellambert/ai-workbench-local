import unittest
from unittest.mock import patch

from src.structured.base import ActionItem, AgentSource, CodeAnalysisPayload, CodeIssue, ExtractionPayload, RiskItem
from src.structured.envelope import StructuredResult, TaskExecutionRequest
from src.structured.document_agent import classify_document_agent_intent, list_document_agent_tools, select_document_agent_tool
from src.structured.tasks import DocumentAgentTaskHandler


class DocumentAgentIntentTests(unittest.TestCase):
    def test_classify_document_agent_intent_detects_comparison(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Compare estes dois contratos e destaque as diferenças principais.",
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

    def test_list_document_agent_tools_marks_comparison_unavailable_with_single_document(self) -> None:
        tools = list_document_agent_tools(document_count=1, use_document_context=True)
        compare_tool = next(item for item in tools if item["name"] == "compare_documents")
        self.assertFalse(compare_tool["available"])
        self.assertEqual(compare_tool["availability_reason"], "requires_at_least_2_documents")

    def test_classify_document_agent_intent_detects_policy_compliance_review(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Revise as cláusulas de confidencialidade e retenção para checar compliance.",
            document_count=1,
        )
        self.assertEqual(intent, "policy_compliance_review")
        self.assertEqual(reason, "policy_compliance_keywords_detected")

    def test_classify_document_agent_intent_detects_risk_review(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Liste os riscos, lacunas e red flags do contrato.",
            document_count=1,
        )
        self.assertEqual(intent, "document_risk_review")
        self.assertEqual(reason, "risk_review_keywords_detected")

    def test_classify_document_agent_intent_detects_operational_extraction(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Extraia os action items e próximas ações operacionais.",
            document_count=1,
        )
        self.assertEqual(intent, "operational_task_extraction")
        self.assertEqual(reason, "operational_task_keywords_detected")

    def test_classify_document_agent_intent_keeps_risk_question_as_document_question(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Quais são os principais riscos documentados?",
            document_count=1,
        )
        self.assertEqual(intent, "document_question")
        self.assertEqual(reason, "question_like_request_detected")

    def test_classify_document_agent_intent_detects_technical_assistance(self) -> None:
        intent, reason = classify_document_agent_intent(
            "Revise o código e a API para encontrar bugs e sugerir refatoração.",
            document_count=1,
        )
        self.assertEqual(intent, "technical_assistance")
        self.assertEqual(reason, "technical_keywords_detected")


class DocumentAgentHandlerTests(unittest.TestCase):
    def test_execute_document_agent_consult_documents_returns_grounded_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="Quais são os principais riscos documentados?",
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
                        snippet="Cláusula de risco operacional.",
                    )
                ],
                "context_text": "[Source: contrato_a.pdf]\nCláusula de risco operacional.",
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
            return_value="Há um risco operacional relevante.\n- risco operacional mapeado\n- revisão jurídica recomendada",
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

    def test_execute_document_agent_policy_compliance_returns_review_payload(self) -> None:
        handler = DocumentAgentTaskHandler()
        request = TaskExecutionRequest(
            task_type="document_agent",
            input_text="Revise as cláusulas de confidencialidade e retenção para checar compliance.",
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
                main_subject="Contrato mestre",
                extracted_fields=[
                    {"name": "confidentiality_clause", "value": "Dados devem permanecer confidenciais por 5 anos", "evidence": "confidential for five years"},
                    {"name": "retention_period", "value": "5 years", "evidence": "records must be retained for five years"},
                ],
                risks=[RiskItem(description="Risco de descumprimento de retenção documental", evidence="records must be retained for five years")],
                action_items=[ActionItem(description="Validar processo de retenção com o time jurídico", evidence="records must be retained for five years")],
                missing_information=["Não há owner explícito para o monitoramento contínuo."],
            ),
            quality_score=0.81,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [
                    AgentSource(
                        source="contrato_mestre.pdf",
                        document_id="doc-1",
                        file_type="pdf",
                        chunk_id=2,
                        score=0.91,
                        snippet="records must be retained for five years",
                    )
                ],
                "context_text": "[Source: contrato_mestre.pdf]\nrecords must be retained for five years",
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
            input_text="Liste os riscos, lacunas e red flags do contrato.",
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
                main_subject="Contrato de fornecimento",
                risks=[RiskItem(description="Multa contratual sem owner operacional claro", evidence="penalty applies if delivery misses deadline")],
                action_items=[ActionItem(description="Definir owner para o acompanhamento dos prazos", evidence="delivery deadline is binding")],
                missing_information=["O documento não explicita quem monitora o SLA."],
            ),
            quality_score=0.79,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [AgentSource(source="contrato_fornecimento.pdf", document_id="doc-1", file_type="pdf", chunk_id=1, score=0.9, snippet="penalty applies if delivery misses deadline")],
                "context_text": "[Source: contrato_fornecimento.pdf]\npenalty applies if delivery misses deadline",
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
            input_text="Extraia os action items e próximas ações operacionais.",
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
                main_subject="Plano operacional",
                important_dates=["2026-04-05"],
                risks=[RiskItem(description="Dependência de aprovação externa", evidence="approval required before launch")],
                action_items=[
                    ActionItem(description="Publicar comunicação interna", due_date="2026-04-05", evidence="send internal comms by April 5"),
                    ActionItem(description="Confirmar rollout com operações", evidence="confirm rollout with operations"),
                ],
            ),
            quality_score=0.8,
        )

        with patch.object(handler, "_resolve_provider", return_value=object()), patch.object(
            handler,
            "_build_document_agent_source_bundle",
            return_value={
                "sources": [AgentSource(source="plano_operacional.pdf", document_id="doc-1", file_type="pdf", chunk_id=3, score=0.89, snippet="send internal comms by April 5")],
                "context_text": "[Source: plano_operacional.pdf]\nsend internal comms by April 5",
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
            input_text="Revise o código e a API para encontrar bugs e sugerir refatoração.",
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
                snippet_summary="Trecho trata integração com API externa.",
                main_purpose="Enviar requisições para sincronizar dados.",
                detected_issues=[
                    CodeIssue(severity="high", category="runtime_failure", title="Timeout não tratado", description="A chamada pode falhar sem retry.", evidence="requests.get(...)", recommendation="Adicionar timeout e retry controlado."),
                ],
                refactor_plan=["Extrair cliente HTTP com timeout explícito."],
                test_suggestions=["Adicionar teste simulando timeout da API."],
                risk_notes=["Falha na integração pode interromper a sincronização."],
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