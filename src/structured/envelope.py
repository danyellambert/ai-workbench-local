"""Execution envelope for structured outputs."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from pydantic import BaseModel, Field

from .base import TaskPayload


class RenderMode(BaseModel):
    """Information about available render modes for a structured output."""

    mode: str = Field(description="Render mode identifier")
    label: str = Field(description="Human-readable label")
    available: bool = Field(description="Whether this render mode is available")
    priority: int = Field(description="Rendering priority (lower = higher priority)")


class ExecutionError(BaseModel):
    """Structured error information for failed executions."""

    error_type: str = Field(description="Type of error that occurred")
    message: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="When error occurred")


class StructuredResult(BaseModel):
    """Envelope for structured output execution results."""

    success: bool = Field(description="Whether the structured task was successful")
    task_type: str = Field(description="Type of task executed")
    execution_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique execution ID")
    executed_at: datetime = Field(default_factory=datetime.now, description="When the task was executed")

    raw_output_text: Optional[str] = Field(default=None, description="Raw output from LLM")
    parsed_json: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON from raw output")
    validated_output: Optional[TaskPayload] = Field(default=None, description="Validated structured payload")

    error: Optional[ExecutionError] = Field(default=None, description="Structured execution error")
    validation_error: Optional[str] = Field(default=None, description="Validation error if validation failed")
    parsing_error: Optional[str] = Field(default=None, description="Parsing error if parsing failed")
    repair_applied: bool = Field(default=False, description="Whether raw-response repair/sanitization was applied")

    source_documents: List[str] = Field(default_factory=list, description="Source documents used")
    context_used: bool = Field(default=False, description="Whether RAG context was used")
    execution_metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional execution metadata for UI/debug")

    available_render_modes: List[RenderMode] = Field(default_factory=list, description="Available render modes")
    primary_render_mode: Optional[str] = Field(default=None, description="Primary render mode to use")

    overall_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Optional overall confidence score")
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Optional quality assessment score")

    model_config = {"arbitrary_types_allowed": True}


class TaskExecutionRequest(BaseModel):
    """Request for executing a structured task."""

    task_type: str = Field(description="Type of task to execute")
    input_text: str = Field(description="Input text to process")
    use_rag_context: bool = Field(default=False, description="Legacy compatibility flag for document context")
    use_document_context: bool = Field(default=False, description="Whether to use the structured document-context pipeline")
    source_document_ids: List[str] = Field(default_factory=list, description="Document IDs available to the structured document-context pipeline")
    context_strategy: str = Field(default="document_scan", description="Context strategy for structured tasks: document_scan or retrieval")
    provider: str = Field(default="ollama", description="Provider to use")
    model: Optional[str] = Field(default=None, description="Model to use; falls back to task/app default when omitted")
    temperature: Optional[float] = Field(default=None, description="Temperature setting")
    context_window: Optional[int] = Field(default=None, description="Context window size")
    progress_callback: Any = Field(default=None, description="Optional callback for UI progress updates during execution")

    model_config = {"arbitrary_types_allowed": True}
