import unittest
from unittest.mock import patch

from src.services import runtime_controls as runtime_controls_module


class _RawResponse:
    def __init__(self, text: str):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.text.encode("utf-8")


class OllamaHostedPublicCatalogTests(unittest.TestCase):
    def test_extracts_direct_cloud_tag_links_and_run_examples(self):
        page_html = """
        <html>
          <body>
            <code>ollama run gemma4:31b-cloud</code>
            <a href="/library/qwen3.5:122b-cloud">qwen cloud tag</a>
            <code>ollama run qwen2.5:7b</code>
          </body>
        </html>
        """

        tags = runtime_controls_module._extract_cloud_model_tags_from_ollama_library_html(page_html)

        self.assertIn("gemma4:31b-cloud", tags)
        self.assertIn("qwen3.5:122b-cloud", tags)
        self.assertNotIn("qwen2.5:7b", tags)

    def test_public_catalog_discovery_uses_paginated_search_and_family_pages(self):
        calls = []

        def fake_urlopen(request, timeout=0):
            url = request.full_url
            calls.append(url)
            if url == "https://ollama.com/search?c=cloud":
                return _RawResponse('<a href="/library/gemma4">gemma4 vision cloud</a>')
            if url == "https://ollama.com/search?c=cloud&page=2":
                return _RawResponse('<a href="/library/gpt-oss:120b-cloud">gpt oss cloud direct tag</a>')
            if url == "https://ollama.com/library/gemma4":
                return _RawResponse('<code>ollama run gemma4:31b-cloud</code>')
            return _RawResponse("No models found")

        with patch("src.services.runtime_controls.urllib_request.urlopen", side_effect=fake_urlopen):
            models = runtime_controls_module.discover_ollama_public_cloud_library_models(max_family_pages=10, max_search_pages=2)

        self.assertIn("gemma4:31b-cloud", models)
        self.assertIn("gpt-oss:120b-cloud", models)
        self.assertIn("https://ollama.com/search?c=cloud&page=2", calls)


if __name__ == "__main__":
    unittest.main()
