import logging
import unittest

import streamlit.logger as streamlit_logger
import streamlit.runtime.scriptrunner_utils.script_run_context as script_run_context
from streamlit.testing.v1 import AppTest


streamlit_logger.set_log_level("error")
script_run_context._LOGGER.setLevel(logging.ERROR)
script_run_context._LOGGER.disabled = True


class StreamlitAppSmokeTests(unittest.TestCase):
    def test_main_openai_compatible_app_renders_and_handles_local_fallback_chat(self) -> None:
        app = AppTest.from_file("legacy/entrypoints/main_openai_streamlit.py")
        app.run(timeout=20)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.chat_input), 1)

        app.chat_input[0].set_value("hi").run(timeout=20)

        self.assertEqual(len(app.exception), 0)
        state = app.session_state.filtered_state
        messages = state.get("lista_mensagens") or []
        self.assertGreaterEqual(len(messages), 2)
        self.assertEqual(messages[-2]["role"], "user")
        self.assertEqual(messages[-2]["content"], "hi")
        self.assertEqual(messages[-1]["role"], "assistant")
        self.assertIn("OPENAI_API_KEY", messages[-1]["content"])

    def test_main_ai_lab_renders_core_tabs_and_operational_controls(self) -> None:
        app = AppTest.from_file("legacy/entrypoints/main_streamlit_lab.py")
        app.run(timeout=20)

        self.assertEqual(len(app.exception), 0)
        tab_labels = {getattr(tab, "label", None) for tab in app.tabs}
        self.assertTrue(
            {
                "🧭 Visão do Lab",
                "📡 Runtime & Observabilidade",
                "💬 Experimentos de Chat e Documentos",
                "🧠 Inspector de Workflow & Structured",
                "⚖️ Benchmarks & Comparação de Modelos",
                "📈 Evals & Diagnóstico",
                "🧪 Experimentos Avançados & Artefatos",
                "🧾 EvidenceOps / MCP",
            }.issubset(tab_labels)
        )
        self.assertEqual(len(app.chat_input), 1)

        button_labels = {button.label for button in app.button}
        self.assertIn("Run structured analysis", button_labels)
        self.assertIn("Run model comparison", button_labels)
        self.assertIn("Listar tools MCP", button_labels)

        heading_texts = [item.value for item in app.markdown if isinstance(getattr(item, "value", None), str)]
        expander_labels = {expander.label for expander in app.expander}
        self.assertTrue(any("AI Lab" in text for text in heading_texts))
        self.assertTrue(any("Split oficial da superfície" in text for text in heading_texts))
        self.assertTrue(any("Produto oficial em Gradio" in text for text in heading_texts))
        self.assertIn("Decision gate final do split", expander_labels)
        self.assertTrue(any("Diagnóstico de OCR / VLM / extração de PDF" in text for text in heading_texts))
        self.assertTrue(any("Experimentos de embeddings / retrieval / reranking" in text for text in heading_texts))

        select_labels = {selectbox.label for selectbox in app.selectbox}
        self.assertTrue("Generation provider" in select_labels or "Provider de geração" in select_labels)
        self.assertIn("Task", select_labels)


if __name__ == "__main__":
    unittest.main()