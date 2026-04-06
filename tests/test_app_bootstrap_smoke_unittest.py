import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.app.bootstrap import build_app_bootstrap


class AppBootstrapSmokeTests(unittest.TestCase):
    def test_build_app_bootstrap_wires_core_runtime_objects(self) -> None:
        fake_settings = SimpleNamespace(project_name="AI Workbench Local")
        fake_rag_settings = SimpleNamespace(chunk_size=1200)
        fake_evidence_config = SimpleNamespace(vl_model="demo-vlm", ocr_backend="ocrmypdf")
        fake_registry = {
            "ollama": {
                "label": "Ollama (local)",
                "instance": object(),
                "supports_chat": True,
                "supports_embeddings": True,
            }
        }
        fake_prompt_profiles = {"neutro": {"label": "Neutro"}}
        fake_task_registry = SimpleNamespace()
        fake_embedding_state = {
            "available_registry": {"ollama": fake_registry["ollama"]},
            "available_options": {"ollama": "Ollama (local)"},
            "available_models_by_provider": {"ollama": ["embeddinggemma:300m"]},
            "unavailable_items": [],
        }

        with (
            patch("src.app.bootstrap.get_ollama_settings", return_value=fake_settings),
            patch("src.app.bootstrap.get_rag_settings", return_value=fake_rag_settings),
            patch("src.app.bootstrap.build_evidence_config_from_rag_settings", return_value=fake_evidence_config),
            patch("src.app.bootstrap.build_provider_registry", return_value=fake_registry),
            patch("src.app.bootstrap.get_prompt_profiles", return_value=fake_prompt_profiles),
            patch("src.app.bootstrap.build_structured_task_registry", return_value=fake_task_registry),
            patch("src.app.bootstrap.build_embedding_provider_sidebar_state", return_value=fake_embedding_state),
        ):
            bootstrap = build_app_bootstrap()

        self.assertIs(bootstrap.settings, fake_settings)
        self.assertIs(bootstrap.rag_settings, fake_rag_settings)
        self.assertIs(bootstrap.evidence_config, fake_evidence_config)
        self.assertIs(bootstrap.provider_registry, fake_registry)
        self.assertIs(bootstrap.prompt_profiles, fake_prompt_profiles)
        self.assertIs(bootstrap.structured_task_registry, fake_task_registry)
        self.assertEqual(bootstrap.embedding_sidebar_state["available_options"]["ollama"], "Ollama (local)")


if __name__ == "__main__":
    unittest.main()