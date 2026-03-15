"""Task handlers and stubs for structured outputs."""
from __future__ import annotations

from typing import Optional

from .base import ChecklistPayload, CVAnalysisPayload, ExtractionPayload, SummaryPayload
from .envelope import TaskExecutionRequest, StructuredResult
from .parsers import attempt_controlled_failure, parse_structured_response


class TaskHandler:
    """Base class for task handlers."""

    def _get_provider_registry(self):
        from ..providers.registry import build_provider_registry

        return build_provider_registry()

    def _resolve_provider(self, request: TaskExecutionRequest):
        registry = self._get_provider_registry()
        provider_entry = registry.get(request.provider)
        if provider_entry is None:
            raise RuntimeError(f"Provider '{request.provider}' is not available in the current environment.")
        return provider_entry["instance"]

    def _collect_response_text(self, provider, request: TaskExecutionRequest, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        stream = provider.stream_chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            context_window=request.context_window,
        )
        return "".join(provider.iter_stream_text(stream))

    def _build_optional_rag_context(self, request: TaskExecutionRequest) -> str:
        if not request.use_rag_context or not request.source_document_ids:
            return ""

        from ..config import get_rag_settings
        from ..providers.registry import build_provider_registry
        from ..rag.service import retrieve_relevant_chunks
        from ..services.rag_state import get_rag_index

        rag_index = get_rag_index()
        if not rag_index:
            return ""

        provider_registry = build_provider_registry()
        embedding_provider = provider_registry.get(request.provider, provider_registry.get("ollama"))["instance"]
        chunks = retrieve_relevant_chunks(
            query=request.input_text,
            rag_index=rag_index,
            settings=get_rag_settings(),
            embedding_provider=embedding_provider,
            document_ids=request.source_document_ids,
        )
        context_parts = []
        for chunk in chunks:
            source = chunk.get("source", "document")
            snippet = chunk.get("snippet") or str(chunk.get("text", ""))
            context_parts.append(f"[Source: {source}]\n{snippet}")
        return "\n\n".join(context_parts)

    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        raise NotImplementedError


class ExtractionTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        provider = self._resolve_provider(request)
        context_text = self._build_optional_rag_context(request)
        prompt = self._build_extraction_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, ExtractionPayload)

    def _build_extraction_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nSupplementary context:\n{context_text}\n" if context_text else ""
        return f"""
You are a precise information extractor. Return only valid JSON matching the requested schema.

Text to analyze:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "extraction",
  "entities": [
    {{
      "type": "entity_type",
      "value": "entity_value",
      "confidence": 0.95,
      "source_text": "supporting span",
      "position_start": 0,
      "position_end": 10
    }}
  ],
  "categories": ["category"],
  "relationships": [
    {{
      "from_entity": "entity_a",
      "to_entity": "entity_b",
      "relationship": "relationship_type",
      "confidence": 0.8,
      "evidence": "supporting evidence"
    }}
  ],
  "extracted_fields": [
    {{
      "name": "field_name",
      "value": "field_value",
      "evidence": "supporting evidence"
    }}
  ]
}}
"""


class SummaryTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        provider = self._resolve_provider(request)
        context_text = self._build_optional_rag_context(request)
        prompt = self._build_summary_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, SummaryPayload)

    def _build_summary_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nRetrieved context:\n{context_text}\n" if context_text else ""
        return f"""
You are a structured summarization assistant. Return only valid JSON.

Text to summarize:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "summary",
  "topics": [
    {{
      "title": "topic title",
      "key_points": ["point 1", "point 2"],
      "relevance_score": 0.9,
      "supporting_evidence": ["evidence"]
    }}
  ],
  "executive_summary": "short executive summary",
  "key_insights": ["insight 1", "insight 2"],
  "reading_time_minutes": 2,
  "completeness_score": 0.85
}}
"""


class ChecklistTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        provider = self._resolve_provider(request)
        context_text = self._build_optional_rag_context(request)
        prompt = self._build_checklist_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, ChecklistPayload)

    def _build_checklist_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nRetrieved context:\n{context_text}\n" if context_text else ""
        return f"""
You are a checklist generator. Convert the input into an operational checklist and return only valid JSON.

Requirements or instructions:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "checklist",
  "title": "Checklist title",
  "description": "Checklist purpose",
  "items": [
    {{
      "id": "item-1",
      "title": "Task title",
      "description": "Detailed description",
      "category": "category",
      "priority": "high",
      "status": "pending",
      "dependencies": [],
      "estimated_time_minutes": 10
    }}
  ],
  "total_items": 1,
  "completed_items": 0,
  "progress_percentage": 0.0
}}
"""


class CVAnalysisTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        provider = self._resolve_provider(request)
        prompt = self._build_cv_analysis_prompt(request.input_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, CVAnalysisPayload)

    def _build_cv_analysis_prompt(self, text: str) -> str:
        return f"""
You are a CV analysis assistant. Extract and structure the resume information below. Return only valid JSON.

Resume text:
{text}

Return this JSON structure:
{{
  "task_type": "cv_analysis",
  "personal_info": {{
    "full_name": "Full Name",
    "email": "name@example.com",
    "phone": "+55 11 99999-9999",
    "location": "City, Country",
    "links": ["https://linkedin.com/in/example"]
  }},
  "sections": [
    {{
      "section_type": "experience",
      "title": "Professional Experience",
      "content": ["item 1", "item 2"],
      "confidence": 0.9
    }}
  ],
  "skills": ["skill 1", "skill 2"],
  "experience_years": 3.0,
  "strengths": ["strength 1"],
  "improvement_areas": ["improvement 1"]
}}
"""


TASK_HANDLERS = {
    "extraction": ExtractionTaskHandler,
    "summary": SummaryTaskHandler,
    "checklist": ChecklistTaskHandler,
    "cv_analysis": CVAnalysisTaskHandler,
}


def get_task_handler(task_type: str) -> Optional[TaskHandler]:
    handler_class = TASK_HANDLERS.get(task_type)
    return handler_class() if handler_class else None
