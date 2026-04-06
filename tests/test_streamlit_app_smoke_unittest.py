import unittest

from streamlit.testing.v1 import AppTest


class StreamlitAppSmokeTests(unittest.TestCase):
    def test_main_openai_compatible_app_renders_and_handles_local_fallback_chat(self) -> None:
        app = AppTest.from_file("main_openai.py")
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
        app = AppTest.from_file("main.py")
        app.run(timeout=20)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.tabs), 7)
        self.assertEqual(len(app.chat_input), 1)

        button_labels = {button.label for button in app.button}
        self.assertIn("Run structured analysis", button_labels)
        self.assertIn("Run model comparison", button_labels)
        self.assertIn("List MCP tools", button_labels)

        heading_texts = [item.value for item in app.markdown if isinstance(getattr(item, "value", None), str)]
        self.assertTrue(any("AI Lab" in text for text in heading_texts))

        select_labels = {selectbox.label for selectbox in app.selectbox}
        self.assertIn("Generation provider", select_labels)
        self.assertIn("Task", select_labels)


if __name__ == "__main__":
    unittest.main()