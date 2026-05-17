from __future__ import annotations

import unittest

from src.product.lab import _build_lab_chat_task_request, _render_chat_assistant_content
from src.structured.base import AgentSource, DocumentAgentPayload
from src.structured.envelope import StructuredResult


class _ChatResult:
    def __init__(self, structured_result: StructuredResult) -> None:
        self.structured_result = structured_result
        self.summary = None
        self.recommendation = None



class LabChatTests(unittest.TestCase):
    def test_build_lab_chat_task_request_forces_direct_document_question_answering(self) -> None:
        request = _build_lab_chat_task_request(
            content='Qual a importância do documento Governance Committee?',
            document_ids=['doc-1', 'doc-2'],
            provider='ollama',
            model='qwen2.5:14b',
        )

        self.assertEqual(request.task_type, 'document_agent')
        self.assertEqual(request.input_text, 'Qual a importância do documento Governance Committee?')
        self.assertEqual(request.context_strategy, 'retrieval')
        self.assertEqual(request.source_document_ids, ['doc-1', 'doc-2'])
        self.assertTrue(request.use_document_context)
        self.assertEqual(request.telemetry['surface'], 'lab_chat')
        self.assertEqual(request.telemetry['chat_mode'], 'grounded_question_answering')
        self.assertEqual(request.telemetry['agent_intent'], 'document_question')
        self.assertEqual(request.telemetry['agent_tool'], 'consult_documents')
        self.assertEqual(request.telemetry['agent_answer_mode'], 'friendly')

    def test_render_chat_assistant_content_preserves_direct_consult_answer(self) -> None:
        payload = DocumentAgentPayload(
            user_intent='document_question',
            intent_reason='lab_chat_question_mode',
            answer_mode='friendly',
            tool_used='consult_documents',
            summary='Resposta direta ao usuário.\n\n- Ponto 1\n- Ponto 2',
            key_points=['Ponto 1', 'Ponto 2'],
            sources=[AgentSource(source='Governance Committee Minutes.pdf', snippet='Approved NCR-2024-011.')],
            confidence=0.84,
        )
        structured_result = StructuredResult(success=True, task_type='document_agent', validated_output=payload)
        result = _ChatResult(structured_result)

        self.assertEqual(
            _render_chat_assistant_content(result),
            'Resposta direta ao usuário.\n\n- Ponto 1\n- Ponto 2',
        )

    def test_render_chat_assistant_content_keeps_structured_sections_for_non_consult_tools(self) -> None:
        payload = DocumentAgentPayload(
            user_intent='operational_checklist',
            intent_reason='checklist_intent',
            answer_mode='checklist',
            tool_used='generate_operational_checklist',
            summary='Operational checklist generated with 2 item(s).',
            key_points=['Define owner', 'Confirm deadline'],
            limitations=['Evidence is partial.'],
            confidence=0.8,
        )
        structured_result = StructuredResult(success=True, task_type='document_agent', validated_output=payload)
        result = _ChatResult(structured_result)

        rendered = _render_chat_assistant_content(result)
        self.assertIn('Operational checklist generated with 2 item(s).', rendered)
        self.assertIn('Evidence:\n- Define owner\n- Confirm deadline', rendered)
        self.assertIn('Caveats:\n- Evidence is partial.', rendered)


if __name__ == '__main__':
    unittest.main()
