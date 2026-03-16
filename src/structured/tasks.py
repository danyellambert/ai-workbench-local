"""Task handlers and stubs for structured outputs."""
from __future__ import annotations

from typing import Optional

from .base import ChecklistPayload, CVAnalysisPayload, ExtractionPayload, SummaryPayload
from .envelope import TaskExecutionRequest, StructuredResult
from .parsers import parse_structured_response


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
        from ..services.rag_state import get_rag_index

        rag_index = get_rag_index()
        if not rag_index:
            return ""

        chunks = [chunk for chunk in rag_index.get("chunks", []) if isinstance(chunk, dict)]
        chunks = [
            chunk for chunk in chunks
            if str(chunk.get("document_id") or chunk.get("file_hash") or "") in set(request.source_document_ids)
        ]
        if not chunks:
            return ""

        if request.input_text.strip():
            from ..rag.service import retrieve_relevant_chunks

            provider_registry = build_provider_registry()
            embedding_provider = provider_registry.get(request.provider, provider_registry.get("ollama"))["instance"]
            retrieved = retrieve_relevant_chunks(
                query=request.input_text,
                rag_index=rag_index,
                settings=get_rag_settings(),
                embedding_provider=embedding_provider,
                document_ids=request.source_document_ids,
            )
            if retrieved:
                chunks = retrieved

        selected_chunks = chunks[:6]
        context_parts = []
        for chunk in selected_chunks:
            source = chunk.get("source", "document")
            snippet = chunk.get("snippet") or str(chunk.get("text", ""))
            if not snippet.strip():
                continue
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
You are a precise information extractor.
Return only valid JSON.
Do not invent information and do not copy example placeholder values.
If something is missing, return an empty list instead of making it up.

Text to analyze:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "extraction",
  "entities": [
    {{
      "type": "organization",
      "value": "OpenAI",
      "confidence": 0.95,
      "source_text": "OpenAI announced...",
      "position_start": 0,
      "position_end": 6
    }}
  ],
  "categories": ["company announcement"],
  "relationships": [
    {{
      "from_entity": "OpenAI",
      "to_entity": "GPT-4",
      "relationship": "announced",
      "confidence": 0.8,
      "evidence": "OpenAI announced GPT-4"
    }}
  ],
  "extracted_fields": [
    {{
      "name": "announcement_date",
      "value": "2025-03-01",
      "evidence": "announced on March 1, 2025"
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
You are a structured summarization assistant.
Return only valid JSON.
Use only the information present in the input/context.
Do not invent facts and do not copy the example values literally.

Text to summarize:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "summary",
  "topics": [
    {{
      "title": "Main topic",
      "key_points": ["point A", "point B"],
      "relevance_score": 0.9,
      "supporting_evidence": ["short quote or snippet"]
    }}
  ],
  "executive_summary": "A concise, factual executive summary.",
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
You are a checklist generator.
Convert the input into an operational checklist and return only valid JSON.
Use the actual instructions provided. Do not copy example placeholder values.

Requirements or instructions:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "checklist",
  "title": "Checklist title based on the input",
  "description": "Checklist purpose based on the input",
  "items": [
    {{
      "id": "item-1",
      "title": "Real action item",
      "description": "Specific action derived from the input",
      "category": "preparation",
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
        context_text = self._build_optional_rag_context(request)
        prompt = self._build_cv_analysis_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, CVAnalysisPayload)

    def _build_cv_analysis_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nResume/document context:\n{context_text}\n" if context_text else ""
        return f"""
You are a CV analysis assistant.
Your job is to extract and structure the actual information present in the resume/context below.
Return only valid JSON.
Do not invent information.
Do not use placeholder values like "Full Name", "name@example.com", "skill 1", or similar.
If a value is missing, use null, 0, or an empty list depending on the field.

Input text:
{text}
{context_block}

Return this JSON structure:
{{
  "task_type": "cv_analysis",
  "personal_info": {{
    "full_name": null,
    "email": null,
    "phone": null,
    "location": null,
    "links": []
  }},
  "sections": [
    {{
      "section_type": "experience",
      "title": "Professional Experience",
      "content": [
        {{
          "text": "Software Engineer at Company X (2023-2024)",
          "details": {{
            "role": "Software Engineer",
            "organization": "Company X",
            "duration": "2023-2024"
          }}
        }}
      ],
      "confidence": 0.9
    }}
  ],
  "skills": [],
  "experience_years": 0.0,
  "strengths": [],
  "improvement_areas": []
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
