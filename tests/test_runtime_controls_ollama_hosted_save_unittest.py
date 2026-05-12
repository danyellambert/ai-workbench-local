import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from src.product.service import build_product_workflow_catalog
from src.services.runtime_controls import build_runtime_controls_payload, update_runtime_controls_payload


class RuntimeControlsOllamaHostedSaveTests(unittest.TestCase):
    def test_save_preserves_dynamic_ollama_hosted_cloud_model(self):
        with TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            bootstrap = SimpleNamespace(
                workflow_catalog=build_product_workflow_catalog(),
                product_settings=SimpleNamespace(default_workflow="document_review", max_upload_files=5, allow_direct_uploads=True),
                rag_settings=SimpleNamespace(store_path=workspace_root / ".rag_store.json"),
                provider_registry={},
                presentation_export_settings=SimpleNamespace(enabled=False),
                workspace_root=workspace_root,
            )

            initial = build_runtime_controls_payload(bootstrap)
            profile = dict(initial["active_profile"])
            profile["primaryConnectionId"] = "ollama_hosted"
            profile["primaryModel"] = "deepseek-v4-flash:cloud"

            updated = update_runtime_controls_payload(bootstrap, {"profile": profile})
            self.assertEqual(updated["active_profile"]["primaryModel"], "deepseek-v4-flash:cloud")

            reloaded = build_runtime_controls_payload(bootstrap)
            self.assertEqual(reloaded["active_profile"]["primaryModel"], "deepseek-v4-flash:cloud")


if __name__ == "__main__":
    unittest.main()
