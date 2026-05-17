import importlib
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib import request as urllib_request

from src.config import ProductApiSettings


class AiLabValidationHarnessApiTests(unittest.TestCase):
    def _start_server(self):
        api_module = importlib.import_module('src.product.api')
        service_module = importlib.import_module('src.product.service')

        bootstrap = SimpleNamespace(
            workflow_catalog=service_module.build_product_workflow_catalog(),
            product_settings=SimpleNamespace(default_workflow='document_review', max_upload_files=5),
            rag_settings=SimpleNamespace(store_path=Path('.rag_store.json')),
            provider_registry={},
            presentation_export_settings=SimpleNamespace(enabled=False, local_artifact_dir=Path('artifacts')),
            workspace_root=Path('.'),
        )
        settings = ProductApiSettings(server_name='127.0.0.1', server_port=0, enable_web_frontend=True, allow_cors=True)
        server = api_module.build_product_api_server(bootstrap=bootstrap, settings=settings)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, api_module

    def _get_json(self, server, path: str) -> dict:
        url = f'http://127.0.0.1:{server.server_address[1]}{path}'
        with urllib_request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))

    def test_validation_harness_snapshot_endpoints(self) -> None:
        server, thread, api_module = self._start_server()
        try:
            with patch.object(api_module, 'build_product_document_library_payload', return_value={'ok': True, 'summary': {'total_documents': 0}, 'documents': []}), \
                 patch.object(api_module, 'build_product_command_center_payload', return_value={'ok': True, 'summary': {'total_runs': 1}, 'recent_runs': [], 'recent_artifacts': []}), \
                 patch.object(api_module, 'build_product_run_history_payload', return_value={'ok': True, 'summary': {'total_runs': 1, 'completed_runs': 1, 'error_runs': 0, 'workflow_counts': {'Document Review': 1}}, 'runs': []}), \
                 patch.object(api_module, 'build_product_artifact_payload', return_value={'ok': True, 'summary': {'total_artifacts': 0}, 'artifacts': []}), \
                 patch.object(api_module, 'build_runtime_controls_payload', return_value={'ok': True, 'active_profile': {'name': 'Test Runtime'}}), \
                 patch.object(api_module, 'build_lab_overview_payload', return_value={'meta': {'source': 'derived'}, 'runtime': {'generationProvider': 'ollama', 'generationModel': 'nemotron'}, 'kpis': [], 'alerts': [], 'workflow_mix': [], 'review_rate': 0}), \
                 patch.object(api_module, 'build_lab_evals_payload', return_value={'meta': {'source': 'derived'}, 'passRate': 80, 'totals': {'pass': 8, 'warn': 1, 'fail': 1, 'review': 2, 'total': 10}, 'suites': [], 'cases': [], 'diagnosis': {}}):
                self.assertTrue(self._get_json(server, '/health')['ok'])
                self.assertIn('workflow_count', self._get_json(server, '/api/product/workflows'))
                self.assertTrue(self._get_json(server, '/api/product/document-library')['ok'])
                self.assertTrue(self._get_json(server, '/api/runtime/controls')['ok'])
                self.assertTrue(self._get_json(server, '/api/product/command-center')['ok'])
                self.assertTrue(self._get_json(server, '/api/product/run-history')['ok'])
                self.assertTrue(self._get_json(server, '/api/product/artifacts')['ok'])
                self.assertEqual(self._get_json(server, '/api/lab/overview')['meta']['source'], 'derived')
                self.assertEqual(self._get_json(server, '/api/lab/evals')['passRate'], 80)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
