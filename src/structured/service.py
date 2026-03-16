"""Service layer for structured outputs."""
from __future__ import annotations

from typing import Any

from ..config import get_ollama_settings
from .base import ChecklistPayload, CVAnalysisPayload
from .envelope import StructuredResult, TaskExecutionRequest
from .registry import task_registry
from .tasks import get_task_handler


_PLACEHOLDER_MARKERS = {
    "full name",
    "name@example.com",
    "city, country",
    "skill 1",
    "skill 2",
    "strength 1",
    "improvement 1",
    "item 1",
    "item 2",
    "https://linkedin.com/in/example",
}


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

        execution_request = request.model_copy(
            update={
                "model": model,
                "temperature": temperature,
                "context_window": context_window,
            }
        )

        try:
            result = handler.execute(execution_request)
            result.context_used = execution_request.use_rag_context and bool(execution_request.source_document_ids)
            result.source_documents = list(execution_request.source_document_ids)
            if result.primary_render_mode is None:
                result.primary_render_mode = task_definition.primary_render_mode
            self._normalize_result_payload(result)
            result.quality_score = self._estimate_quality_score(result, execution_request)
            if result.overall_confidence is None and result.quality_score is not None:
                result.overall_confidence = result.quality_score
            return result
        except Exception as exc:
            return self._create_error_result(
                request.task_type,
                f"Execution failed: {exc}",
                request.input_text,
            )

    def _normalize_result_payload(self, result: StructuredResult) -> None:
        payload = result.validated_output
        if payload is None:
            return

        if isinstance(payload, ChecklistPayload):
            total_items = len(payload.items)
            completed_items = sum(1 for item in payload.items if item.status == "completed")
            progress_percentage = round((completed_items / total_items) * 100.0, 1) if total_items else 0.0
            result.validated_output = payload.model_copy(
                update={
                    "total_items": total_items,
                    "completed_items": completed_items,
                    "progress_percentage": progress_percentage,
                }
            )

        if isinstance(result.validated_output, CVAnalysisPayload):
            payload = result.validated_output
            unique_skills = list(dict.fromkeys(item.strip() for item in payload.skills if item and item.strip()))
            unique_strengths = list(dict.fromkeys(item.strip() for item in payload.strengths if item and item.strip()))
            unique_improvements = list(
                dict.fromkeys(item.strip() for item in payload.improvement_areas if item and item.strip())
            )
            result.validated_output = payload.model_copy(
                update={
                    "skills": unique_skills,
                    "strengths": unique_strengths,
                    "improvement_areas": unique_improvements,
                }
            )

    def _collect_string_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            strings: list[str] = []
            for item in value.values():
                strings.extend(self._collect_string_values(item))
            return strings
        if isinstance(value, list):
            strings: list[str] = []
            for item in value:
                strings.extend(self._collect_string_values(item))
            return strings
        return []

    def _estimate_quality_score(self, result: StructuredResult, request: TaskExecutionRequest) -> float | None:
        if not result.success or result.validated_output is None:
            return 0.0

        payload_json = result.validated_output.model_dump(mode="json")
        flattened = [item.strip().lower() for item in self._collect_string_values(payload_json) if item.strip()]
        placeholder_hits = sum(1 for item in flattened if item in _PLACEHOLDER_MARKERS)
        example_hits = sum(1 for item in flattened if "example" in item.lower())

        score = 0.92
        if request.task_type == "cv_analysis" and not request.input_text.strip() and not result.context_used:
            score -= 0.55
        if request.task_type == "cv_analysis" and result.context_used:
            score += 0.03

        score -= min(placeholder_hits * 0.22, 0.66)
        score -= min(example_hits * 0.12, 0.24)

        if isinstance(result.validated_output, CVAnalysisPayload):
            payload = result.validated_output
            if not payload.sections:
                score -= 0.18
            if not payload.skills:
                score -= 0.1
            if payload.personal_info is None:
                score -= 0.08

        if isinstance(result.validated_output, ChecklistPayload):
            payload = result.validated_output
            if not payload.items:
                score -= 0.2

        if result.repair_applied:
            score -= 0.05

        return max(0.0, min(round(score, 3), 1.0))

    def _create_error_result(self, task_type: str, error_message: str, raw_input: str) -> StructuredResult:
        from .parsers import attempt_controlled_failure

        return attempt_controlled_failure(raw_response=raw_input, task_type=task_type, error_message=error_message)


structured_service = StructuredOutputService()
