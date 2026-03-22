"""Task handlers for structured outputs."""
from __future__ import annotations

from typing import Optional

from .base import ChecklistPayload, CVAnalysisPayload, CodeAnalysisPayload, ExtractionPayload, SummaryPayload
from .envelope import TaskExecutionRequest, StructuredResult
from .parsers import parse_structured_response


class TaskHandler:
    """Base class for structured task handlers."""

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

    def _build_optional_document_context(
        self,
        request: TaskExecutionRequest,
        *,
        strategy: str | None = None,
        max_chunks: int | None = None,
        max_chars: int | None = None,
    ) -> str:
        use_context = request.use_document_context or request.use_rag_context
        if not use_context or not request.source_document_ids:
            return ""

        from ..services.document_context import build_structured_document_context

        return build_structured_document_context(
            query=request.input_text,
            document_ids=request.source_document_ids,
            strategy=(strategy or request.context_strategy or "document_scan"),
            max_chunks=max_chunks,
            max_chars=max_chars,
        )

    def _build_optional_rag_context(
        self,
        request: TaskExecutionRequest,
        mode: str | None = None,
        max_chunks: int | None = None,
        max_chars: int | None = None,
    ) -> str:
        """Backward-compatible wrapper used by earlier Phase 5 code."""
        return self._build_optional_document_context(
            request,
            strategy=mode,
            max_chunks=max_chunks,
            max_chars=max_chars,
        )

    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        raise NotImplementedError


class ExtractionTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        provider = self._resolve_provider(request)
        context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=12)
        prompt = self._build_extraction_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, ExtractionPayload)

    def _build_extraction_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nDocument context:\n{context_text}\n" if context_text else ""
        return f"""
You are a precise information extractor.
Return only valid JSON.
Use only the information present in the input/context.
Do not invent information and do not copy example placeholder values.
If something is missing, return null or an empty list instead of making it up.
When risks or actions are present, return them as structured objects with description plus any available owner, due date, impact, or status.
Try to extract entities, main subject, important dates/numbers, risks, action items, and missing information when they are present.
- Extract all obvious grounded named entities, including organizations, people, and explicit locations/sites.
- Populate `important_numbers` with financially or operationally relevant numbers explicitly present in the source text.
- Extract explicit relationships when they are clearly stated.
- Never list something under `missing_information` if it is explicitly present in the source text.

Text to analyze:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "extraction",
  "main_subject": "short main subject derived from the source",
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
  ],
  "important_dates": ["2025-03-01"],
  "important_numbers": ["30%", "$2.4M"],
  "risks": [
    {{
      "description": "Potential rollout delay due to vendor dependency",
      "impact": "Delivery may slip by two weeks",
      "owner": null,
      "due_date": null
    }}
  ],
  "action_items": [
    {{
      "description": "Finalize integration plan",
      "owner": "Platform team",
      "due_date": "Friday",
      "status": "pending"
    }}
  ],
  "missing_information": ["No owner is named for the migration task"]
}}
"""


class SummaryTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        provider = self._resolve_provider(request)
        strategy = request.context_strategy or "retrieval"
        context_text = self._build_optional_document_context(request, strategy=strategy, max_chunks=8)
        prompt = self._build_summary_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, SummaryPayload)

    def _build_summary_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nContext:\n{context_text}\n" if context_text else ""
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
        context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=10)
        prompt = self._build_checklist_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, ChecklistPayload)

    def _build_checklist_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nContext:\n{context_text}\n" if context_text else ""
        return f"""
You are a checklist generator.
Convert the input into an operational checklist and return only valid JSON.
Use the actual instructions provided. Do not copy example placeholder values.
- Convert EACH explicit required action into its own checklist item.
- If one sentence contains multiple imperative actions joined by commas or `and`, split them into separate items.
- Preserve blocking or approval conditions as their own checklist items when explicitly stated.
- Do not collapse multiple grounded actions into one generic item.

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
        from ..services.document_context import (
            build_retrieval_context,
            get_document_grounding_profile,
        )
        from .parsers import attempt_controlled_failure

        grounding = get_document_grounding_profile(request.source_document_ids)
        use_full_cv_grounding = bool(grounding.get("single_cv_document"))
        primary_context = ""
        secondary_context = ""

        if use_full_cv_grounding:
            primary_context = str(grounding.get("full_cv_context") or "").strip()
            secondary_context = build_retrieval_context(
                query=request.input_text,
                document_ids=request.source_document_ids,
                max_chunks=4,
                max_chars=6000,
            ).strip()
        else:
            primary_context = self._build_optional_document_context(request, strategy="document_scan", max_chunks=16)

        if use_full_cv_grounding and self._is_low_grounding_cv_context(primary_context):
            return attempt_controlled_failure(
                raw_response="",
                task_type="cv_analysis",
                error_message="Low grounding: insufficient CV context. Full CV context is too short or structurally incomplete, so placeholder resume output was blocked.",
            )

        prompt = self._build_cv_analysis_prompt(
            request.input_text,
            primary_context,
            secondary_context=secondary_context,
            use_full_cv_grounding=use_full_cv_grounding,
        )
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, CVAnalysisPayload)

    def _is_low_grounding_cv_context(self, context_text: str) -> bool:
        cleaned = (context_text or "").strip()
        if len(cleaned) < 220:
            return True
        uppercase = cleaned.upper()
        structural_hits = sum(
            1 for marker in ("EXPERIENCE", "EDUCATION", "SKILLS", "LANGUAGES", "SUMMARY", "[CV ") if marker in uppercase
        )
        return structural_hits < 2

    def _build_cv_analysis_prompt(
        self,
        text: str,
        context_text: str,
        *,
        secondary_context: str = "",
        use_full_cv_grounding: bool = False,
    ) -> str:
        primary_label = "Full CV grounding context" if use_full_cv_grounding else "Resume/document context"
        context_block = f"\n{primary_label}:\n{context_text}\n" if context_text else ""
        secondary_block = f"\nSecondary retrieval support (use only to supplement the primary CV context, never to override it):\n{secondary_context}\n" if secondary_context else ""
        grounding_rules = """
Grounding rules:
- If a full CV grounding context is present, use it as the primary source of truth.
- Treat retrieval snippets only as secondary support.
- Do not fabricate employers, schools, dates, or placeholder labels like Company X.
- If grounding is weak, incomplete, or ambiguous, leave fields null/empty instead of guessing.
""" if use_full_cv_grounding else ""
        return f"""
You are a CV analysis assistant.
Your job is to extract and structure the actual information present in the resume/context below.
Return only valid JSON.
Do not invent information.
Do not use placeholder values like "Full Name", "name@example.com", "skill 1", or similar.
If a value is missing, use null, 0, or an empty list depending on the field.
{grounding_rules}

Input text:
{text}
{context_block}
{secondary_block}

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
  "sections": [],
  "skills": [],
  "languages": [],
  "education_entries": [],
  "experience_entries": [],
  "experience_years": 0.0,
  "strengths": [],
  "improvement_areas": []
}}
Important rules:
- Extract languages explicitly to the top-level "languages" field.
- Extract education explicitly to the top-level "education_entries" field.
- Extract role titles and organizations explicitly to the top-level "experience_entries" field.
- For each experience entry, preserve grounded `date_range` whenever a date range is present in the context.
- For each experience entry, preserve grounded bullet lines in `bullets` whenever bullet lines are present under that experience in the context.
- Preserve grounded `location` in `personal_info.location` when a strong resume location is present in the context.
- Preserve grounded `location` for each experience entry whenever the experience header includes a location.
- Prefer copying grounded experience facts verbatim over summarizing them away.
- If a `CV EDUCATION` block is present, preserve each grounded education line into `education_entries` with separate `degree` and `institution` when they are explicitly available.
- If a `CV PROJECTS` block is present, preserve those grounded project items explicitly and do not drop them from the final payload.
- "skills" must be a list of strings only.
- You may also repeat the same information inside sections for flexibility, but top-level fields must be populated whenever information is present.
- Never output invented sample employers, schools, cities, or date ranges.
- If the only possible value would be a guessed placeholder, return null or [] instead.
"""


class CodeAnalysisTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        provider = self._resolve_provider(request)
        context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=12)
        prompt = self._build_code_analysis_prompt(request.input_text, context_text)
        response_text = self._collect_response_text(provider, request, prompt)
        return parse_structured_response(response_text, CodeAnalysisPayload)

    def _build_code_analysis_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nCode/document context:\n{context_text}\n" if context_text else ""
        return f"""
You are a code analysis assistant.
Return only valid JSON.
Use only the code/content provided.
Do not invent bugs or features that are not grounded in the code.
- Prioritize concrete correctness bugs, runtime failure risks, type/shape assumptions, input mutation side effects, and grounded test cases.
- Avoid generic/template issues unless they are directly supported by visible code evidence.
- Prefer the most important concrete bug over vague maintainability commentary.
- Test suggestions must be specific to the actual snippet, not placeholders like `edge case X`.
- Risk notes must be snippet-specific and grounded in visible code behavior.

Code or technical text to analyze:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "code_analysis",
  "snippet_summary": "Short summary of the code snippet",
  "main_purpose": "Main purpose of the code",
  "detected_issues": [
    {{
      "severity": "medium",
      "category": "maintainability",
      "title": "Duplicated logic",
      "description": "Similar logic appears in multiple places.",
      "evidence": "Repeated conditional branches in two methods.",
      "recommendation": "Extract a helper function."
    }}
  ],
  "readability_improvements": ["Rename unclear variables"],
  "maintainability_improvements": ["Extract shared logic"],
  "refactor_plan": ["Step 1", "Step 2"],
  "test_suggestions": ["Add unit test for edge case X"],
  "risk_notes": ["May fail on malformed input"]
}}
"""


def get_task_handler(task_type: str) -> Optional[TaskHandler]:
    mapping: dict[str, TaskHandler] = {
        "extraction": ExtractionTaskHandler(),
        "summary": SummaryTaskHandler(),
        "checklist": ChecklistTaskHandler(),
        "cv_analysis": CVAnalysisTaskHandler(),
        "code_analysis": CodeAnalysisTaskHandler(),
    }
    return mapping.get(task_type)
