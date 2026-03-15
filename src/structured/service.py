"""Service layer for structured outputs."""
from __future__ import annotations

from .envelope import TaskExecutionRequest, StructuredResult
from .registry import task_registry
from .tasks import get_task_handler
from ..config import get_ollama_settings


class StructuredOutputService:
    """Service for executing structured output tasks."""

    def __init__(self) -> None:
        self.task_registry = task_registry
        self.ollama_settings = get_ollama_settings()

    def execute_task(self, request: TaskExecutionRequest) -> StructuredResult:
        """Execute a structured task with the given request."""
        task_definition = self.task_registry.get_task(request.task_type)
        if not task_definition:
            return self._create_error_result(
                request.task_type,
                f"Task type '{request.task_type}' not registered",
                request.input_text,
            )

        handler = get_task_handler(request.task_type)
        if not handler:
            return self._create_error_result(
                request.task_type,
                f"No handler available for task type '{request.task_type}'",
                request.input_text,
            )

        model = request.model or task_definition.default_model or self.ollama_settings.default_model
        temperature = request.temperature if request.temperature is not None else task_definition.default_temperature
        context_window = request.context_window or self.ollama_settings.default_context_window

        execution_request = request.model_copy(update={
            "model": model,
            "temperature": temperature,
            "context_window": context_window,
        })

        try:
            result = handler.execute(execution_request)
            result.context_used = execution_request.use_rag_context and bool(execution_request.source_document_ids)
            result.source_documents = list(execution_request.source_document_ids)
            if result.primary_render_mode is None:
                result.primary_render_mode = task_definition.primary_render_mode
            return result
        except Exception as exc:
            return self._create_error_result(
                request.task_type,
                f"Execution failed: {exc}",
                request.input_text,
            )

    def _create_error_result(self, task_type: str, error_message: str, raw_input: str) -> StructuredResult:
        from .parsers import attempt_controlled_failure

        return attempt_controlled_failure(raw_response=raw_input, task_type=task_type, error_message=error_message)


structured_service = StructuredOutputService()
