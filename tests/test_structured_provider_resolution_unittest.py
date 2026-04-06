import unittest

from src.structured.envelope import TaskExecutionRequest
from src.structured.tasks import TaskHandler


class _DummyTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest):  # pragma: no cover - not needed in tests
        raise NotImplementedError


class StructuredProviderResolutionTests(unittest.TestCase):
    def test_resolve_provider_records_effective_provider_in_telemetry(self) -> None:
        request = TaskExecutionRequest(task_type="summary", input_text="teste", provider="ollama")
        handler = _DummyTaskHandler()

        registry = {
            "ollama": {"instance": object(), "supports_chat": True},
        }
        handler._get_provider_registry = lambda: registry  # type: ignore[method-assign]

        provider = handler._resolve_provider(request)
        self.assertIs(provider, registry["ollama"]["instance"])
        self.assertEqual(request.telemetry["provider_requested"], "ollama")
        self.assertEqual(request.telemetry["provider_effective"], "ollama")

    def test_resolve_provider_falls_back_to_ollama_and_records_reason(self) -> None:
        request = TaskExecutionRequest(task_type="summary", input_text="teste", provider="openai")
        handler = _DummyTaskHandler()

        registry = {
            "ollama": {"instance": object(), "supports_chat": True},
        }
        handler._get_provider_registry = lambda: registry  # type: ignore[method-assign]

        provider = handler._resolve_provider(request)
        self.assertIs(provider, registry["ollama"]["instance"])
        self.assertEqual(request.telemetry["provider_requested"], "openai")
        self.assertEqual(request.telemetry["provider_effective"], "ollama")
        self.assertEqual(request.telemetry["provider_fallback_reason"], "chat_provider_unavailable:openai")


if __name__ == "__main__":
    unittest.main()