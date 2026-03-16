"""Task registry for structured outputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Type

from .base import (
    BaseTaskPayload,
    ChecklistPayload,
    CVAnalysisPayload,
    ExtractionPayload,
    SummaryPayload,
)


@dataclass(frozen=True)
class TaskDefinition:
    """Definition of a structured task."""

    name: str
    description: str
    payload_schema: Type[BaseTaskPayload]
    requires_rag: bool = False
    default_temperature: float = 0.1
    default_model: Optional[str] = None
    render_modes: tuple[str, ...] = ("json", "friendly")
    primary_render_mode: str = "friendly"


class StructuredTaskRegistry:
    """Registry for structured output tasks."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskDefinition] = {}

    def register_task(
        self,
        name: str,
        description: str,
        payload_schema: Type[BaseTaskPayload],
        requires_rag: bool = False,
        default_temperature: float = 0.1,
        default_model: Optional[str] = None,
        render_modes: tuple[str, ...] = ("json", "friendly"),
        primary_render_mode: str = "friendly",
    ) -> None:
        self._tasks[name] = TaskDefinition(
            name=name,
            description=description,
            payload_schema=payload_schema,
            requires_rag=requires_rag,
            default_temperature=default_temperature,
            default_model=default_model,
            render_modes=render_modes,
            primary_render_mode=primary_render_mode,
        )

    def list_tasks(self) -> Dict[str, TaskDefinition]:
        """Return all registered task definitions."""
        return dict(self._tasks)

    def get_task(self, name: str) -> Optional[TaskDefinition]:
        return self._tasks.get(name)

    def get_available_tasks(self) -> Dict[str, str]:
        return {name: task.description for name, task in self._tasks.items()}

    def get_task_schema(self, name: str) -> Optional[Type[BaseTaskPayload]]:
        task = self.get_task(name)
        return task.payload_schema if task else None

    def requires_rag(self, name: str) -> bool:
        task = self.get_task(name)
        return task.requires_rag if task else False

    def get_default_model(self, name: str) -> Optional[str]:
        task = self.get_task(name)
        return task.default_model if task else None

    def get_default_temperature(self, name: str) -> float:
        task = self.get_task(name)
        return task.default_temperature if task else 0.1


def build_structured_task_registry() -> StructuredTaskRegistry:
    registry = StructuredTaskRegistry()
    registry.register_task(
        name="extraction",
        description="Extract structured information from text",
        payload_schema=ExtractionPayload,
        requires_rag=False,
        default_temperature=0.1,
        render_modes=("json", "friendly"),
        primary_render_mode="friendly",
    )
    registry.register_task(
        name="summary",
        description="Generate structured summary from text",
        payload_schema=SummaryPayload,
        requires_rag=True,
        default_temperature=0.2,
        render_modes=("json", "friendly"),
        primary_render_mode="friendly",
    )
    registry.register_task(
        name="checklist",
        description="Generate structured checklist from requirements",
        payload_schema=ChecklistPayload,
        requires_rag=False,
        default_temperature=0.1,
        render_modes=("json", "friendly", "checklist"),
        primary_render_mode="checklist",
    )
    registry.register_task(
        name="cv_analysis",
        description="Analyze and structure CV/resume information",
        payload_schema=CVAnalysisPayload,
        requires_rag=True,
        default_temperature=0.1,
        render_modes=("json", "friendly"),
        primary_render_mode="friendly",
    )
    return registry


task_registry = build_structured_task_registry()