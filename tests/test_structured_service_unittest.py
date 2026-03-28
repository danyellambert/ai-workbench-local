import unittest
from unittest.mock import patch

from src.structured.base import SummaryPayload
from src.structured.envelope import StructuredResult, TaskExecutionRequest
from src.structured.service import StructuredOutputService


class _DummyStructuredHandler:
    def __init__(self) -> None:
        self.last_request = None

    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        self.last_request = request
        return StructuredResult(
            success=True,
            task_type=request.task_type,
            raw_output_text="{}",
            parsed_json={},
            validated_output=SummaryPayload(
                task_type="summary",
                topics=[],
                executive_summary="ok",
                key_insights=[],
                reading_time_minutes=1,
                completeness_score=0.8,
            ),
            execution_metadata={},
        )


class StructuredServiceTests(unittest.TestCase):
    def test_execute_task_records_effective_provider_metadata_and_defaults(self) -> None:
        service = StructuredOutputService()
        handler = _DummyStructuredHandler()

        with patch("src.structured.service.get_task_handler", return_value=handler), patch.object(
            service,
            "_resolve_provider_runtime_profile",
            return_value={
                "requested_provider": "missing_provider",
                "effective_provider": "ollama",
                "provider_entry": {
                    "default_model": "qwen2.5:7b",
                    "default_context_window": 8192,
                },
                "fallback_reason": "chat_provider_unavailable:missing_provider",
            },
        ):
            result = service.execute_task(
                TaskExecutionRequest(
                    task_type="summary",
                    input_text="x" * 90000,
                    provider="missing_provider",
                )
            )

        self.assertTrue(result.success)
        self.assertIsNotNone(handler.last_request)
        self.assertEqual(handler.last_request.model, "qwen2.5:7b")
        self.assertEqual(handler.last_request.context_window, 32768)
        self.assertEqual(result.execution_metadata["provider_requested"], "missing_provider")
        self.assertEqual(result.execution_metadata["provider_effective"], "ollama")
        self.assertEqual(result.execution_metadata["provider"], "ollama")
        self.assertEqual(
            result.execution_metadata["provider_fallback_reason"],
            "chat_provider_unavailable:missing_provider",
        )
        self.assertEqual(result.execution_metadata["context_window_cap"], 256000)

    def test_resolve_context_window_uses_effective_provider_cap(self) -> None:
        service = StructuredOutputService()
        request = TaskExecutionRequest(
            task_type="summary",
            input_text="x" * 90000,
            provider="missing_provider",
        )

        resolved = service.resolve_context_window(
            request,
            max_context_window=8192,
            effective_provider="ollama",
        )

        self.assertEqual(resolved, 32768)


if __name__ == "__main__":
    unittest.main()