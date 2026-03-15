"""Structured output foundation for Phase 5."""
from .base import (
    BaseTaskPayload,
    Entity,
    Relationship,
    ExtractedField,
    ExtractionPayload,
    Topic,
    SummaryPayload,
    ChecklistItem,
    ChecklistPayload,
    ContactInfo,
    CVSection,
    CVAnalysisPayload,
    TaskPayload,
)
from .envelope import (
    StructuredResult,
    TaskExecutionRequest,
    RenderMode,
    ExecutionError,
)
from .registry import (
    task_registry,
    TaskDefinition,
    StructuredTaskRegistry,
    build_structured_task_registry,
)
from .parsers import (
    parse_structured_response,
    extract_json_from_response,
    sanitize_json_object,
    attempt_controlled_failure,
)
from .service import (
    StructuredOutputService,
    structured_service,
)
from .tasks import (
    get_task_handler,
    TASK_HANDLERS,
)

__all__ = [
    "BaseTaskPayload",
    "Entity",
    "Relationship",
    "ExtractedField",
    "ExtractionPayload",
    "Topic",
    "SummaryPayload",
    "ChecklistItem",
    "ChecklistPayload",
    "ContactInfo",
    "CVSection",
    "CVAnalysisPayload",
    "TaskPayload",
    "StructuredResult",
    "TaskExecutionRequest",
    "RenderMode",
    "ExecutionError",
    "task_registry",
    "TaskDefinition",
    "StructuredTaskRegistry",
    "build_structured_task_registry",
    "parse_structured_response",
    "extract_json_from_response",
    "sanitize_json_object",
    "attempt_controlled_failure",
    "StructuredOutputService",
    "structured_service",
    "get_task_handler",
    "TASK_HANDLERS",
]
