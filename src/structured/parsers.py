"""Parser and sanitizer for structured outputs."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Type

from pydantic import ValidationError

from .base import BaseTaskPayload
from .envelope import ExecutionError, RenderMode, StructuredResult


def _render_modes_for_task(task_type: str) -> tuple[list[RenderMode], str]:
    base_modes = [
        RenderMode(mode="json", label="JSON", available=True, priority=1),
        RenderMode(mode="friendly", label="Friendly view", available=True, priority=2),
    ]
    if task_type == "checklist":
        base_modes.append(RenderMode(mode="checklist", label="Checklist", available=True, priority=0))
        return base_modes, "checklist"
    return base_modes, "friendly"


def _strip_code_fences(response_text: str) -> str:
    text = response_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _json_candidate_slices(response_text: str) -> list[str]:
    text = _strip_code_fences(response_text)
    candidates = [text]

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        sliced = text[start : end + 1]
        if sliced not in candidates:
            candidates.append(sliced)

    return candidates


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from a model response using safe heuristics."""
    for candidate in _json_candidate_slices(response_text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def sanitize_json_object(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize JSON object without inventing semantic content."""
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            sanitized[key] = sanitize_json_object(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_json_object(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    return sanitized


def parse_structured_response(raw_response: str, payload_schema: Type[BaseTaskPayload]) -> StructuredResult:
    """Parse raw response into a structured result with validation and controlled failure."""
    parsed_json = extract_json_from_response(raw_response)
    task_type = getattr(payload_schema, "model_fields", {}).get("task_type")
    task_default = getattr(task_type, "default", None) if task_type else None
    task_name = task_default or payload_schema.__name__.replace("Payload", "").lower()
    render_modes, primary_mode = _render_modes_for_task(task_name)

    if not parsed_json:
        return StructuredResult(
            success=False,
            task_type=task_name,
            raw_output_text=raw_response,
            parsing_error="No valid JSON object could be extracted from the model response.",
            error=ExecutionError(error_type="parsing_error", message="No valid JSON object could be extracted from the model response."),
            repair_applied=_strip_code_fences(raw_response) != raw_response.strip(),
            available_render_modes=[RenderMode(mode="json", label="JSON", available=True, priority=1)],
            primary_render_mode="json",
        )

    sanitized_json = sanitize_json_object(parsed_json)

    try:
        validated_payload = payload_schema(**sanitized_json)
        return StructuredResult(
            success=True,
            task_type=validated_payload.task_type,
            raw_output_text=raw_response,
            parsed_json=parsed_json,
            validated_output=validated_payload,
            repair_applied=sanitized_json != parsed_json or _strip_code_fences(raw_response) != raw_response.strip(),
            available_render_modes=render_modes,
            primary_render_mode=primary_mode,
        )
    except ValidationError as exc:
        message = f"Validation failed for {payload_schema.__name__}: {exc}"
        return StructuredResult(
            success=False,
            task_type=sanitized_json.get("task_type", task_name),
            raw_output_text=raw_response,
            parsed_json=parsed_json,
            validation_error=message,
            error=ExecutionError(error_type="validation_error", message=message),
            repair_applied=sanitized_json != parsed_json or _strip_code_fences(raw_response) != raw_response.strip(),
            available_render_modes=[RenderMode(mode="json", label="JSON", available=True, priority=1)],
            primary_render_mode="json",
        )


def attempt_controlled_failure(raw_response: str, task_type: str, error_message: str) -> StructuredResult:
    """Create a controlled failure result."""
    return StructuredResult(
        success=False,
        task_type=task_type,
        raw_output_text=raw_response,
        parsing_error=error_message,
        error=ExecutionError(error_type="execution_error", message=error_message),
        available_render_modes=[RenderMode(mode="json", label="JSON", available=True, priority=1)],
        primary_render_mode="json",
    )
