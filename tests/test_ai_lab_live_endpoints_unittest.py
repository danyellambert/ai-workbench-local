from __future__ import annotations

import json
import sqlite3
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib import request as urllib_request

from src.app.product_bootstrap import build_product_bootstrap
from src.config import ProductApiSettings
from src.product.api import build_product_api_server
from src.product.models import ProductDocumentRef, ProductWorkflowResult
from src.storage.runtime_paths import (
    get_lab_chat_sessions_path,
    get_lab_workflow_runs_path,
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_worklog_path,
)
from src.structured.envelope import StructuredResult


class _FakeProvider:
    def __init__(self) -> None:
        self._usage = {
            'prompt_tokens': 48,
            'completion_tokens': 22,
            'total_tokens': 70,
        }

    def stream_chat_completion(self, *, messages, model, **_: object):  # noqa: ANN001
        prompt = messages[-1]['content'] if messages else ''
        return [f'Grounded response for testing. Prompt length: {len(prompt)}.']

    def iter_stream_text(self, stream):
        yield from stream

    def get_last_usage_metrics(self) -> dict[str, object]:
        return dict(self._usage)


class AiLabLiveApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = TemporaryDirectory()
        self.workspace_root = Path(self._tempdir.name)
        self._write_workspace_state()
        bootstrap = replace(build_product_bootstrap(), workspace_root=self.workspace_root)
        settings = ProductApiSettings(server_name='127.0.0.1', server_port=0, enable_web_frontend=True, allow_cors=True)
        self.server = build_product_api_server(bootstrap=bootstrap, settings=settings)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self._tempdir.cleanup()

    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def _write_workspace_state(self) -> None:
        self._write_json(
            self.workspace_root / '.runtime/state/product/runtime_controls.json',
            {
                'updated_at': '2026-04-17T12:00:00+00:00',
                'profile': {
                    'primaryConnectionId': 'ollama',
                    'primaryModel': 'test-chat-model',
                    'embeddingConnectionId': 'ollama',
                    'embeddingModel': 'test-embedding-model',
                    'retrievalStrategy': 'hybrid',
                    'generation': {
                        'temperature': 0.2,
                        'topP': 0.95,
                        'maxOutputTokens': 512,
                        'contextWindow': '8k',
                        'promptProfile': 'neutro',
                    },
                    'retrieval': {
                        'topK': 4,
                        'chunkSize': 800,
                        'chunkOverlap': 80,
                        'rerankPoolSize': 8,
                        'rerankLexicalWeight': 0.35,
                    },
                    'docProcessing': {
                        'pdfExtractionMode': 'default',
                        'ocrBackend': 'none',
                        'vlmEnhancement': False,
                    },
                },
            },
        )
        self._write_json(
            self.workspace_root / '.runtime/state/rag/rag_store.json',
            {
                'documents': [
                    {
                        'document_id': 'doc-1',
                        'name': 'Test Policy.pdf',
                        'status': 'indexed',
                        'chunk_count': 1,
                        'char_count': 256,
                        'indexed_at': '2026-04-17T11:00:00+00:00',
                        'size_bytes': 1024,
                        'source_type': 'pdf',
                    }
                ],
                'chunks': [
                    {
                        'chunk_id': 'chunk-1',
                        'document_id': 'doc-1',
                        'chunk_index': 0,
                        'source': 'Test Policy.pdf',
                        'text': 'Evidence snippet for testing grounded chat and workflow execution.',
                        'snippet': 'Evidence snippet for testing grounded chat and workflow execution.',
                    }
                ],
            },
        )
        self._write_json(self.workspace_root / '.chat_history.json', [])
        self._write_json(self.workspace_root / '.runtime/logs/product/workflow_history.json', [])

    def _url(self, path: str) -> str:
        return f'http://127.0.0.1:{self.server.server_address[1]}{path}'

    def _get_json(self, path: str) -> dict:
        with urllib_request.urlopen(self._url(path), timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))

    def _post_json(self, path: str, payload: dict) -> dict:
        request = urllib_request.Request(
            self._url(path),
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib_request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))

    @staticmethod
    def _fake_runtime_profile(*_, capability: str, **__):
        provider = _FakeProvider()
        return {
            'requested_provider': 'fake_provider',
            'effective_provider': 'fake_provider',
            'provider_instance': provider,
            'provider_label': 'Fake Provider',
            'model': 'fake-model',
            'context_window': 8192 if capability == 'chat' else None,
            'temperature': 0.2,
            'top_p': 0.95,
            'max_tokens': 512,
            'fallback_reason': None,
            'available': True,
        }

    @staticmethod
    def _fake_retrieval(*_, **__):
        return {
            'chunks': [
                {
                    'document_id': 'doc-1',
                    'source': 'Test Policy.pdf',
                    'snippet': 'Evidence snippet for testing grounded chat and workflow execution.',
                    'score': 0.92,
                    'chunk_index': 0,
                }
            ],
            'backend_used': 'mock_retrieval',
            'retrieval_strategy_requested': 'hybrid',
            'retrieval_strategy_used': 'hybrid',
            'filtered_chunks_available': 1,
            'candidate_pool_size': 1,
            'reranking_applied': False,
        }

    @staticmethod
    def _fake_workflow_result(*_, **__) -> ProductWorkflowResult:
        structured_result = StructuredResult(
            success=True,
            task_type='risk_gap_review',
            raw_output_text='Structured response',
            parsed_json={
                'findings': [{'finding_type': 'risk', 'detail': 'Primary risk identified in the test document.'}],
                'action_items': [
                    {
                        'description': 'Confirm the blocking dependency with the document owner.',
                        'owner': 'Ops',
                        'due_date': '2026-04-20',
                        'status': 'suggested',
                        'evidence': 'Test Policy.pdf',
                    }
                ],
                'recommended_actions': ['Escalate the dependency before execution.'],
            },
            source_documents=['doc-1'],
            context_used=True,
            execution_metadata={
                'confidence': 0.84,
                'needs_review': False,
                'execution_strategy_used': 'retrieval',
                'context_chars': 128,
                'total_tokens': 90,
            },
            overall_confidence=0.84,
            quality_score=0.81,
        )
        return ProductWorkflowResult(
            workflow_id='document_review',
            workflow_label='Document Review',
            status='completed',
            summary='Structured review completed successfully.',
            highlights=['Primary risk identified.', 'Blocking dependency documented.'],
            recommendation='Escalate the dependency before execution.',
            structured_result=structured_result,
            warnings=[],
        )

    def test_chat_session_message_roundtrip_persists_runtime_state(self) -> None:
        from unittest.mock import patch

        with patch('src.product.lab._resolve_live_provider_profile', side_effect=self._fake_runtime_profile), patch(
            'src.product.lab.retrieve_relevant_chunks_detailed',
            side_effect=self._fake_retrieval,
        ), patch(
            'src.product.api.list_product_documents',
            return_value=[ProductDocumentRef(document_id='doc-1', name='Test Policy.pdf', file_type='pdf', char_count=256, chunk_count=1)],
        ):
            created = self._post_json('/api/lab/chat/sessions', {'document_ids': ['doc-1'], 'title': 'Test session'})
            self.assertTrue(created['ok'])
            session_id = created['session']['session_id']

            sent = self._post_json(
                f'/api/lab/chat/sessions/{session_id}/messages',
                {'content': 'What is the main risk?', 'document_ids': ['doc-1']},
            )
            self.assertTrue(sent['ok'])
            page = sent['page']
            self.assertEqual(page['active_session_id'], session_id)
            self.assertGreaterEqual(len(page['messages']), 2)
            self.assertEqual(page['messages'][-1]['role'], 'assistant')
            self.assertTrue(page['capabilities']['can_send'])

            stored_sessions = json.loads(get_lab_chat_sessions_path(self.workspace_root).read_text(encoding='utf-8'))
            self.assertEqual(len(stored_sessions), 1)
            self.assertEqual(stored_sessions[0]['session_id'], session_id)
            self.assertGreaterEqual(len(stored_sessions[0]['messages']), 2)

            evidenceops = self._get_json('/api/lab/evidenceops')
            self.assertTrue(evidenceops['ok'])
            self.assertGreaterEqual(evidenceops['summary']['operationsCount'], 1)
            self.assertTrue(get_phase95_evidenceops_worklog_path(self.workspace_root).exists())

    def test_workflow_run_roundtrip_persists_run_and_actions(self) -> None:
        from unittest.mock import patch

        with patch('src.product.lab._resolve_live_provider_profile', side_effect=self._fake_runtime_profile), patch(
            'src.product.lab.run_product_workflow',
            side_effect=self._fake_workflow_result,
        ), patch(
            'src.product.api.list_product_documents',
            return_value=[ProductDocumentRef(document_id='doc-1', name='Test Policy.pdf', file_type='pdf', char_count=256, chunk_count=1)],
        ), patch('src.product.api.build_document_review_view', return_value={'summary': 'ok'}):
            response = self._post_json(
                '/api/lab/workflow-inspector/run',
                {
                    'task_id': 'review_document_risks',
                    'document_id': 'doc-1',
                    'input_text': 'Review the main risks and blockers.',
                },
            )
            self.assertTrue(response['ok'])
            self.assertEqual(response['run']['task_id'], 'review_document_risks')
            self.assertIn('page', response)
            self.assertTrue(response['page']['capabilities']['can_execute'])

            workflow_runs = json.loads(get_lab_workflow_runs_path(self.workspace_root).read_text(encoding='utf-8'))
            self.assertEqual(len(workflow_runs), 1)
            self.assertEqual(workflow_runs[0]['task_id'], 'review_document_risks')

            action_store_path = get_phase95_evidenceops_action_store_path(self.workspace_root)
            self.assertTrue(action_store_path.exists())
            with sqlite3.connect(action_store_path) as connection:
                count = connection.execute('SELECT COUNT(*) FROM evidenceops_actions').fetchone()[0]
            self.assertGreaterEqual(count, 1)

            evidenceops = self._get_json('/api/lab/evidenceops')
            self.assertTrue(evidenceops['ok'])
            self.assertGreaterEqual(evidenceops['summary']['openActions'], 1)
            self.assertGreaterEqual(evidenceops['summary']['operationsCount'], 1)


if __name__ == '__main__':
    unittest.main()
