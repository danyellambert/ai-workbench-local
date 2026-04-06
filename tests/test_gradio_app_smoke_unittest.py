import importlib.util
import asyncio
import os
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
warnings.simplefilter("ignore", ResourceWarning)


GRADIO_AVAILABLE = importlib.util.find_spec("gradio") is not None


@unittest.skipUnless(GRADIO_AVAILABLE, "gradio is not installed in the current environment")
class GradioAppSmokeTests(unittest.TestCase):
    def test_build_gradio_product_app_returns_blocks(self) -> None:
        from src.gradio_ui.app import build_gradio_product_app
        from src.product.service import build_product_workflow_catalog, build_product_workflow_frontend_contract

        fake_provider = SimpleNamespace(list_available_models=lambda: ["qwen2.5:7b"])
        bootstrap = SimpleNamespace(
            product_settings=SimpleNamespace(
                app_name="AI Workbench Product",
                default_workflow="document_review",
                show_ai_lab_entry=True,
                accent_color="#6ae3ff",
                enable_deck_generation=True,
                max_upload_files=4,
            ),
            workflow_catalog=build_product_workflow_catalog(),
            rag_settings=SimpleNamespace(
                store_path=Path(".rag_store.json"),
                loader_strategy="manual",
                chunking_strategy="manual",
                retrieval_strategy="manual_hybrid",
                embedding_provider="ollama",
                embedding_model="embeddinggemma:300m",
                embedding_context_window=512,
                embedding_truncate=True,
                chunk_size=1200,
                chunk_overlap=80,
                top_k=4,
                chroma_path=Path(".chroma_rag"),
                rerank_pool_size=8,
                rerank_lexical_weight=0.35,
                context_budget_ratio=0.45,
                pdf_extraction_mode="hybrid",
                pdf_docling_enabled=True,
                pdf_docling_ocr_enabled=True,
                pdf_docling_force_full_page_ocr=False,
                pdf_docling_picture_description=False,
                pdf_ocr_fallback_enabled=True,
                pdf_ocr_fallback_languages="eng+por",
            ),
            provider_registry={
                "ollama": {
                    "label": "Ollama",
                    "instance": fake_provider,
                    "supports_chat": True,
                }
            },
            presentation_export_settings=SimpleNamespace(enabled=False),
            workspace_root=Path("."),
            workflow_frontend_contract=build_product_workflow_frontend_contract(),
        )

        app = build_gradio_product_app(bootstrap)

        try:
            self.assertIsNotNone(app)
            self.assertIn("AI Workbench Product", app.config.get("title", ""))
        finally:
            app.close()
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
            if loop is not None and not loop.is_closed():
                loop.close()
            asyncio.set_event_loop(None)


if __name__ == "__main__":
    unittest.main()