import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib import request as urllib_request

from src.config import ProductApiSettings
from src.product.api import build_product_api_server
from src.product.service import build_product_workflow_catalog
from src.services import runtime_controls as runtime_controls_module


class _FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _hosted_settings(*, api_key: str = "", base_url: str = "https://ollama.com/api"):
    return SimpleNamespace(
        api_key=api_key,
        base_url=base_url,
        default_model="nemotron-3-super:cloud",
        default_context_window=8192,
        default_prompt_profile="neutro",
        default_top_p=None,
        default_max_tokens=None,
        default_temperature=0.2,
        available_models_env=[],
        available_embedding_models_env=[],
    )


class OllamaHostedModelDiscoveryTests(unittest.TestCase):
    def tearDown(self):
        runtime_controls_module._OLLAMA_HOSTED_MODEL_CACHE.clear()

    def test_extracts_cloud_models_without_requiring_colon_cloud(self):
        payload = {
            "models": [
                {"name": "qwen2.5:7b"},
                {"name": "nemotron-3-nano:30b-cloud"},
                {"name": "nemotron-3-super:cloud"},
                {"model": "gpt-oss:120b-cloud"},
                {"model_ref": "custom/CLOUD-preview"},
            ]
        }

        models = runtime_controls_module._extract_ollama_hosted_cloud_models(payload)

        self.assertEqual(models[0], "nemotron-3-super:cloud")
        self.assertEqual(models[1], "nemotron-3-nano:30b-cloud")
        self.assertIn("gpt-oss:120b-cloud", models)
        self.assertIn("custom/CLOUD-preview", models)
        self.assertNotIn("qwen2.5:7b", models)

    def test_discovery_uses_tags_endpoint_and_caches_success(self):
        calls = {"count": 0}

        def fake_urlopen(request, timeout=0):
            calls["count"] += 1
            self.assertIn("/api/tags", request.full_url)
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            return _FakeResponse({"models": [{"name": "gpt-oss:120b-cloud"}]})

        with patch("src.services.runtime_controls.get_ollama_hosted_settings", return_value=_hosted_settings(api_key="test-key")), patch(
            "src.services.runtime_controls.get_secret",
            return_value="",
        ), patch(
            "src.services.runtime_controls.urllib_request.urlopen",
            side_effect=fake_urlopen,
        ):
            first = runtime_controls_module.discover_ollama_hosted_cloud_models(force_refresh=True)
            second = runtime_controls_module.discover_ollama_hosted_cloud_models()

        self.assertTrue(first["ok"])
        self.assertIn(first["source"], {"ollama_hosted_tags", "ollama_hosted_tags+public_catalog"})
        self.assertEqual(first["default_model"], "nemotron-3-super:cloud")
        self.assertEqual(first["models"][0], "nemotron-3-super:cloud")
        self.assertEqual(first["models"][1], "nemotron-3-nano:30b-cloud")
        self.assertIn("gpt-oss:120b-cloud", first["models"])
        self.assertTrue(second["cached"])
        self.assertGreaterEqual(calls["count"], 1)

    def test_discovery_falls_back_when_api_key_missing(self):
        with patch("src.services.runtime_controls.get_ollama_hosted_settings", return_value=_hosted_settings(api_key="")), patch(
            "src.services.runtime_controls.get_secret",
            return_value="",
        ), patch.dict(
            "os.environ",
            {"OLLAMA_HOSTED_API_KEY": "", "OLLAMA_API_KEY": ""},
            clear=False,
        ):
            payload = runtime_controls_module.discover_ollama_hosted_cloud_models(force_refresh=True)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["source"], "fallback")
        self.assertEqual(payload["default_model"], "nemotron-3-super:cloud")
        self.assertEqual(payload["models"][:2], ["nemotron-3-super:cloud", "nemotron-3-nano:30b-cloud"])
        self.assertIn("API key", payload["error"])

    def test_discovery_falls_back_on_http_error(self):
        def fake_urlopen(*_, **__):
            raise HTTPError("https://ollama.com/api/tags", 403, "Forbidden", hdrs=None, fp=None)

        with patch("src.services.runtime_controls.get_ollama_hosted_settings", return_value=_hosted_settings(api_key="test-key")), patch(
            "src.services.runtime_controls.get_secret",
            return_value="",
        ), patch(
            "src.services.runtime_controls.urllib_request.urlopen",
            side_effect=fake_urlopen,
        ):
            payload = runtime_controls_module.discover_ollama_hosted_cloud_models(force_refresh=True)

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["source"], "fallback")
        self.assertIn("nemotron-3-super:cloud", payload["models"])
        self.assertIn("HTTP 403", payload["error"])

    def test_extracts_cloud_models_from_public_library_html(self):
        page_html = """
        <html>
          <body>
            <section class="model-card">
              <code>ollama run gemma4:31b-cloud</code>
              <a href="/library/nemotron-3-super">nemotron cloud</a>
            </section>
            <div>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</div>
            <section class="model-card">
              <a href="/library/local-only">local model</a>
              <span>local runtime only</span>
            </section>
          </body>
        </html>
        """

        tags = runtime_controls_module._extract_cloud_model_tags_from_ollama_library_html(page_html)
        families = runtime_controls_module._extract_cloud_families_from_ollama_search_html(page_html)

        self.assertIn("gemma4:31b-cloud", tags)
        self.assertNotIn("qwen2.5:7b", tags)
        self.assertIn("nemotron-3-super", families)
        self.assertNotIn("local-only", families)

    def test_discovery_merges_tags_api_with_public_catalog(self):
        def fake_urlopen(request, timeout=0):
            url = request.full_url
            if url.endswith("/api/tags"):
                return _FakeResponse({"models": [{"name": "nemotron-3-super:cloud"}]})
            if url == "https://ollama.com/search?c=cloud":
                return _FakeResponse({"html": '<a href="/library/gemma4">gemma4 vision cloud</a>'})
            if url == "https://ollama.com/library/gemma4":
                return _FakeResponse({"html": '<code>ollama run gemma4:31b-cloud</code>'})
            return _FakeResponse({"html": ""})

        with patch("src.services.runtime_controls.get_ollama_hosted_settings", return_value=_hosted_settings(api_key="test-key")), patch(
            "src.services.runtime_controls.get_secret",
            return_value="",
        ), patch(
            "src.services.runtime_controls.urllib_request.urlopen",
            side_effect=fake_urlopen,
        ):
            payload = runtime_controls_module.discover_ollama_hosted_cloud_models(force_refresh=True)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source"], "ollama_hosted_tags+public_catalog")
        self.assertIn("nemotron-3-super:cloud", payload["models"])
        self.assertIn("gemma4:31b-cloud", payload["models"])

    def test_product_api_route_returns_discovered_models(self):
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
            settings = ProductApiSettings(server_name="127.0.0.1", server_port=0, enable_web_frontend=True, allow_cors=True)
            server = build_product_api_server(bootstrap=bootstrap, settings=settings)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            try:
                with patch(
                    "src.product.api.discover_ollama_hosted_cloud_models",
                    return_value={
                        "ok": True,
                        "source": "ollama_hosted_tags",
                        "default_model": "nemotron-3-super:cloud",
                        "models": ["nemotron-3-super:cloud", "gpt-oss:120b-cloud"],
                        "fallback_models": ["nemotron-3-super:cloud", "nemotron-3-nano:30b-cloud"],
                        "cached": False,
                        "error": None,
                    },
                ):
                    url = f"http://127.0.0.1:{server.server_address[1]}/api/runtime/ollama-hosted/models"
                    with urllib_request.urlopen(url, timeout=5) as response:
                        payload = json.loads(response.read().decode("utf-8"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["default_model"], "nemotron-3-super:cloud")
        self.assertIn("gpt-oss:120b-cloud", payload["models"])


if __name__ == "__main__":
    unittest.main()
