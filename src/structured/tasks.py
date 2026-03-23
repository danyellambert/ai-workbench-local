"""Task handlers for structured outputs."""
from __future__ import annotations

import math
import time
from typing import Optional

from .base import ChecklistPayload, CVAnalysisPayload, CodeAnalysisPayload, ExtractionPayload, SummaryPayload
from .envelope import TaskExecutionRequest, StructuredResult
from .parsers import parse_structured_response


SUMMARY_FULL_DOCUMENT_TRIGGER_CHARS = 42000
SUMMARY_PART_CHUNK_SIZE = 24000
SUMMARY_PART_OVERLAP = 250


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

    def _report_progress(self, request: TaskExecutionRequest, *, step: str, progress: float, detail: str = "") -> None:
        callback = getattr(request, "progress_callback", None)
        if callable(callback):
            try:
                callback(step=step, progress=progress, detail=detail)
            except Exception:
                pass


class ExtractionTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        self._report_progress(request, step="building_context", progress=0.15, detail="Montando contexto estruturado")
        provider = self._resolve_provider(request)
        context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=12)
        prompt = self._build_extraction_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.6, detail="Executando extração no modelo")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.9, detail="Validando saída estruturada")
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
        self._report_progress(request, step="preparing_document", progress=0.05, detail="Preparando texto completo do documento")
        provider = self._resolve_provider(request)
        full_document_text = self._build_full_document_text(request)
        if full_document_text and len(full_document_text) > SUMMARY_FULL_DOCUMENT_TRIGGER_CHARS:
            document_parts = self._split_text_for_summary(full_document_text)
            self._report_progress(
                request,
                step="map_reduce_setup",
                progress=0.12,
                detail=f"Documento grande detectado; dividindo em {len(document_parts)} parte(s)",
            )
            partial_summaries, map_stage_details = self._summarize_document_in_parts(provider, request, full_document_text)
            prompt = self._build_summary_reduce_prompt(request.input_text, partial_summaries)
            self._report_progress(request, step="reduce", progress=0.82, detail="Consolidando resumo final")
            reduce_started_at = time.perf_counter()
            response_text = self._collect_response_text(provider, request, prompt)
            reduce_duration_s = round(time.perf_counter() - reduce_started_at, 2)
            self._report_progress(request, step="parsing", progress=0.94, detail="Validando resumo final")
            result = parse_structured_response(response_text, SummaryPayload)
            result = self._post_process_summary_result(
                result,
                provider=provider,
                request=request,
                source_text=full_document_text,
                partial_summaries=partial_summaries,
            )
            result.execution_metadata = {
                "summary_mode": "full_document_map_reduce",
                "full_document_chars": len(full_document_text),
                "document_parts": len(document_parts),
                "partial_summaries_generated": len(partial_summaries),
                "total_map_time_s": round(sum(item.get("duration_s", 0.0) for item in map_stage_details), 2),
                "reduce_time_s": reduce_duration_s,
                "stages": [
                    *map_stage_details,
                    {
                        "stage_type": "reduce",
                        "label": "Final synthesis",
                        "chars_sent": len(prompt),
                        "duration_s": reduce_duration_s,
                        "prompt_preview": prompt[:6000],
                        "context_preview": prompt[:6000],
                    },
                ],
                "context_note": "Summary gerado a partir do documento inteiro em múltiplas partes; o preview curto de doc scan/retrieval não representa sozinho todo o conteúdo consumido neste modo.",
            }
            self._report_progress(request, step="done", progress=1.0, detail="Resumo completo finalizado")
            return result

        strategy = request.context_strategy or "retrieval"
        self._report_progress(request, step="building_context", progress=0.18, detail=f"Montando contexto ({strategy})")
        context_text = self._build_optional_document_context(
            request,
            strategy=strategy,
            max_chunks=12,
            max_chars=24000,
        )
        prompt = self._build_summary_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.65, detail="Gerando resumo no modelo")
        single_pass_started_at = time.perf_counter()
        response_text = self._collect_response_text(provider, request, prompt)
        single_pass_duration_s = round(time.perf_counter() - single_pass_started_at, 2)
        self._report_progress(request, step="parsing", progress=0.92, detail="Validando resumo")
        result = parse_structured_response(response_text, SummaryPayload)
        result = self._post_process_summary_result(
            result,
            provider=provider,
            request=request,
            source_text=full_document_text or request.input_text or context_text,
            partial_summaries=None,
        )
        result.execution_metadata = {
            "summary_mode": "single_pass_context",
            "full_document_chars": len(full_document_text or ""),
            "context_chars_sent": len(context_text or ""),
            "context_strategy": strategy,
            "single_pass_time_s": single_pass_duration_s,
            "stages": [
                {
                    "stage_type": "single_pass",
                    "label": f"Single-pass summary ({strategy})",
                    "chars_sent": len(context_text or ""),
                    "duration_s": single_pass_duration_s,
                    "context_preview": (context_text or "")[:6000],
                    "prompt_preview": prompt[:6000],
                }
            ],
            "context_note": "Summary gerado em um único passo usando contexto recortado (doc scan/retrieval).",
        }
        self._report_progress(request, step="done", progress=1.0, detail="Resumo finalizado")
        return result

    def _build_full_document_text(self, request: TaskExecutionRequest) -> str:
        if not request.source_document_ids:
            return request.input_text
        try:
            from ..services.document_context import _filtered_chunks, _get_rag_index, _ordered_chunks
        except Exception:
            return request.input_text

        rag_index = _get_rag_index()
        if not isinstance(rag_index, dict):
            return request.input_text

        chunks = _ordered_chunks(_filtered_chunks(rag_index, request.source_document_ids))
        parts = [str(chunk.get("text") or "").strip() for chunk in chunks if str(chunk.get("text") or "").strip()]
        full_text = "\n\n".join(parts).strip()
        return full_text or request.input_text

    def _split_text_for_summary(
        self,
        text: str,
        chunk_size: int = SUMMARY_PART_CHUNK_SIZE,
        overlap: int = SUMMARY_PART_OVERLAP,
    ) -> list[str]:
        cleaned = (text or "").strip()
        if not cleaned:
            return []
        chunks: list[str] = []
        start = 0
        step = max(chunk_size - overlap, 1)
        while start < len(cleaned):
            end = min(start + chunk_size, len(cleaned))
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(cleaned):
                break
            start += step
        return chunks

    def _summarize_document_in_parts(self, provider, request: TaskExecutionRequest, full_document_text: str) -> tuple[list[SummaryPayload], list[dict[str, object]]]:
        partial_payloads: list[SummaryPayload] = []
        stage_details: list[dict[str, object]] = []
        chunks = self._split_text_for_summary(full_document_text)
        total_chunks = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            prompt = self._build_summary_map_prompt(request.input_text, chunk, index=index, total=total_chunks)
            progress_base = 0.15
            progress_span = 0.6
            current_progress = progress_base + progress_span * ((index - 1) / max(total_chunks, 1))
            self._report_progress(
                request,
                step="map",
                progress=current_progress,
                detail=f"Processando parte {index} de {total_chunks}",
            )
            started_at = time.perf_counter()
            response_text = self._collect_response_text(provider, request, prompt)
            duration_s = round(time.perf_counter() - started_at, 2)
            partial_result = parse_structured_response(response_text, SummaryPayload)
            stage_details.append(
                {
                    "stage_type": "map",
                    "label": f"Part {index} of {total_chunks}",
                    "chars_sent": len(chunk),
                    "duration_s": duration_s,
                    "context_preview": chunk[:6000],
                    "prompt_preview": prompt[:6000],
                    "success": partial_result.success,
                }
            )
            if partial_result.success and isinstance(partial_result.validated_output, SummaryPayload):
                partial_payloads.append(partial_result.validated_output)
        return partial_payloads, stage_details

    def _post_process_summary_result(
        self,
        result: StructuredResult,
        *,
        provider,
        request: TaskExecutionRequest,
        source_text: str,
        partial_summaries: list[SummaryPayload] | None,
    ) -> StructuredResult:
        payload = result.validated_output
        if not result.success or not isinstance(payload, SummaryPayload):
            return result

        normalized_payload = self._normalize_summary_payload(payload, provider=provider, request=request)
        payload = normalized_payload

        unique_topics = []
        seen_titles = set()
        for topic in payload.topics:
            title = self._normalize_topic_title(topic.title)
            key = title.lower()
            if not title or key in seen_titles:
                continue
            seen_titles.add(key)
            cleaned_points = [self._clean_summary_text(point) for point in topic.key_points if self._clean_summary_text(point)]
            cleaned_evidence = [self._clean_summary_text(item) for item in topic.supporting_evidence if self._clean_summary_text(item)]
            unique_topics.append(topic.model_copy(update={
                "title": title,
                "key_points": cleaned_points,
                "supporting_evidence": cleaned_evidence,
            }))

        summary_text_units = [payload.executive_summary, *payload.key_insights]
        summary_text_units.extend(point for topic in payload.topics for point in topic.key_points)
        summary_word_count = len(" ".join(item for item in summary_text_units if item).split())
        reading_time_minutes = max(1, math.ceil(summary_word_count / 180)) if summary_word_count else payload.reading_time_minutes
        topic_count = len(unique_topics) if unique_topics else max(1, len(payload.key_insights) // 2)
        if partial_summaries:
            chunk_coverage = min(len(partial_summaries) / max(len(self._split_text_for_summary(source_text)), 1), 1.0)
            completeness_score = min(0.93, max(0.68, 0.70 + 0.14 * chunk_coverage + 0.02 * min(topic_count, 5)))
        else:
            completeness_score = min(0.90, max(0.58, 0.60 + 0.04 * min(topic_count, 5)))

        result.validated_output = payload.model_copy(update={
            "topics": unique_topics or payload.topics,
            "reading_time_minutes": reading_time_minutes,
            "completeness_score": round(completeness_score, 2),
        })
        return result

    def _clean_summary_text(self, text: str | None) -> str:
        cleaned = " ".join(str(text or "").split()).strip()
        if not cleaned:
            return ""
        cleaned = cleaned.replace(" ,", ",").replace(" .", ".")
        return cleaned

    def _normalize_topic_title(self, title: str | None) -> str:
        cleaned = self._clean_summary_text(title)
        lowered = cleaned.lower()
        generic_prefixes = [
            "overview of ",
            "summary of ",
            "highlights of ",
        ]
        for prefix in generic_prefixes:
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break
        return cleaned or "Untitled topic"

    def _normalize_summary_payload(self, payload: SummaryPayload, *, provider, request: TaskExecutionRequest) -> SummaryPayload:
        topics = list(payload.topics)
        if self._looks_like_overloaded_single_topic(payload):
            repaired = self._restructure_summary_topics_with_llm(payload, provider=provider, request=request)
            if repaired is not None:
                topics = repaired
        key_insights = list(dict.fromkeys(item.strip() for item in payload.key_insights if item and item.strip()))
        return payload.model_copy(update={
            "topics": topics,
            "key_insights": key_insights,
        })

    def _looks_like_overloaded_single_topic(self, payload: SummaryPayload) -> bool:
        if len(payload.topics) != 1:
            return False
        topic = payload.topics[0]
        key_points = [item for item in topic.key_points if item and item.strip()]
        long_topic = len(key_points) >= 6
        broad_insights = len(payload.key_insights) >= 3
        return long_topic or broad_insights

    def _restructure_summary_topics_with_llm(self, payload: SummaryPayload, *, provider, request: TaskExecutionRequest):
        prompt = f"""
You are repairing the structure of a summary JSON.
Do not add facts. Do not remove grounded facts.
Your only job is to reorganize an overloaded single-topic summary into 3 to 5 semantically distinct topics when the content is broad enough.
Topic titles must emerge from the content itself, not from fixed templates.
If the content is actually narrow, you may keep fewer topics.
Return only valid JSON using the same schema.

Current summary JSON:
{payload.model_dump_json(indent=2)}
"""
        response_text = self._collect_response_text(provider, request, prompt)
        repaired = parse_structured_response(response_text, SummaryPayload)
        if repaired.success and isinstance(repaired.validated_output, SummaryPayload):
            repaired_topics = repaired.validated_output.topics
            if len(repaired_topics) >= 2:
                return repaired_topics
        return None

    def _build_summary_map_prompt(self, text: str, chunk_text: str, *, index: int, total: int) -> str:
        return f"""
You are a structured summarization assistant.
You are summarizing PART {index} of {total} of a larger document.
Return only valid JSON.
Use only the information present in this part.
Do not invent facts.
Be compact and coverage-oriented.
Focus on preserving: names, dates, programs, financial facts, decisions, and operational highlights.
Avoid verbose prose. Prefer concise bullets and a small number of strong, grounded topics.

User intent / task:
{text}

Document part:
{chunk_text}

Return this JSON structure:
{{
  "task_type": "summary",
  "topics": [
    {{
      "title": "Topic title grounded in this part",
      "key_points": ["grounded point 1", "grounded point 2"],
      "relevance_score": 0.9,
      "supporting_evidence": ["short quote or exact snippet"]
    }}
  ],
  "executive_summary": "Very short factual summary of this part only.",
  "key_insights": ["important grounded insight from this part"],
  "reading_time_minutes": 1,
  "completeness_score": 0.9
}}
"""

    def _build_summary_reduce_prompt(self, text: str, partial_summaries: list[SummaryPayload]) -> str:
        serialized_parts = []
        for index, summary in enumerate(partial_summaries, start=1):
            serialized_parts.append(
                f"[PARTIAL SUMMARY {index}]\n"
                f"Executive summary: {summary.executive_summary}\n"
                f"Key insights: {'; '.join(summary.key_insights)}\n"
                f"Topics: {'; '.join(topic.title for topic in summary.topics)}\n"
                f"Evidence: {'; '.join(e for topic in summary.topics for e in topic.supporting_evidence[:2])}"
            )
        partial_block = "\n\n".join(serialized_parts)
        return f"""
You are a structured summarization assistant.
Return only valid JSON.
You are receiving partial summaries from different parts of the same document.
Your job is to produce a final, more complete summary of the whole document.
Do not invent facts. Merge repeated topics and preserve important named entities, dates, programs, numbers, and decisions.
Do not default to a single topic unless the document is truly narrow.
For broad reports, produce multiple macro-topics instead of collapsing everything into one giant topic.
Do not use a single catch-all topic for the whole document when finance, programs, governance, and operations are all present.
Topic titles must be specific and concise, not generic containers like "highlights" or "overview".
If a fragment looks OCR-noisy, truncated, or unreliable, do not promote it to a headline fact unless it is corroborated by the broader summary set.
Write an executive summary that reads like a real executive brief, not just a generic description of the document.

User intent / task:
{text}

Partial summaries from the full document:
{partial_block}

Return this JSON structure:
{{
  "task_type": "summary",
  "topics": [
    {{
      "title": "Merged topic title",
      "key_points": ["point 1", "point 2"],
      "relevance_score": 0.9,
      "supporting_evidence": ["snippet 1", "snippet 2"]
    }}
  ],
  "executive_summary": "A concise, factual executive summary of the whole document.",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "reading_time_minutes": 1,
  "completeness_score": 0.9
}}
"""

    def _build_summary_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nContext:\n{context_text}\n" if context_text else ""
        return f"""
You are a structured summarization assistant.
Return only valid JSON.
Use only the information present in the input/context.
Do not invent facts and do not copy the example values literally.
Do not default to a single topic unless the document is truly narrow.
Set reading time according to the likely reading effort of the summary itself, not the full source document.
Set completeness according to how much of the document appears covered, not a fixed default.
Topic titles must be specific and concise, not generic containers like "highlights" or "overview".
Avoid elevating OCR-noisy or truncated fragments into key facts when the wording appears unreliable.
Write an executive summary that feels executive and synthesized, not just a generic restatement.

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
        self._report_progress(request, step="building_context", progress=0.15, detail="Montando contexto")
        provider = self._resolve_provider(request)
        context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=10)
        prompt = self._build_checklist_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.65, detail="Gerando checklist")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.9, detail="Validando checklist")
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
        self._report_progress(request, step="grounding", progress=0.12, detail="Preparando grounding do CV/documento")
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
        self._report_progress(request, step="model_inference", progress=0.68, detail="Executando análise de CV")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.92, detail="Validando análise de CV")
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
        self._report_progress(request, step="building_context", progress=0.15, detail="Montando contexto")
        provider = self._resolve_provider(request)
        context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=12)
        prompt = self._build_code_analysis_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.68, detail="Executando análise de código")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.92, detail="Validando análise")
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
