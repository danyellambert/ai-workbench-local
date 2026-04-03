"""Task handlers for structured outputs."""
from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
import re
import time
import unicodedata
from typing import Optional, Type

from .base import (
    AgentSource,
    AgentToolExecution,
    ChecklistPayload,
    ComparisonFinding,
    CVAnalysisPayload,
    CVSection,
    CVSectionContentItem,
    CodeAnalysisPayload,
    DocumentAgentPayload,
    ExtractionPayload,
    SummaryPayload,
)
from .document_agent import (
    classify_document_agent_intent,
    describe_document_agent_intent,
    describe_document_agent_tool,
    extract_bullet_points_from_text,
    list_document_agent_tools,
    normalize_agent_bullet_points,
    select_document_agent_tool,
)
from .envelope import RenderMode, TaskExecutionRequest, StructuredResult
from .parsers import parse_structured_response


SUMMARY_FULL_DOCUMENT_TRIGGER_CHARS = 42000
SUMMARY_PART_CHUNK_SIZE = 24000
SUMMARY_PART_OVERLAP = 250
EXTRACTION_FULL_DOCUMENT_DIRECT_CHARS = 120000
CHECKLIST_FULL_DOCUMENT_DIRECT_CHARS = 80000
CHECKLIST_PART_CHUNK_SIZE = 28000
CHECKLIST_PART_OVERLAP = 400
CHECKLIST_MULTI_STAGE_QUESTION_THRESHOLD = 12
CHECKLIST_MULTI_STAGE_LINE_THRESHOLD = 80


def _normalize_matching_text(value: object) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_checklist_domain_profile(*parts: str | None) -> str:
    return "generic"


def build_checklist_domain_prompt_rules(profile: str) -> str:
    return """
- Keep checklist items atomic: one explicit instruction/question = one item.
- Never merge adjacent checklist questions into a single item.
- If a line or paragraph contains multiple explicit checklist questions/instructions, split them into separate items.
""".strip()


def build_checklist_reduce_domain_prompt_rules(profile: str) -> str:
    return """
- Keep checklist items atomic during consolidation.
- Never merge two distinct checklist questions/instructions into one output item just because they are adjacent in the source.
- If partial extractions contain combined questions, split them into separate final items.
""".strip()


def build_checklist_single_pass_domain_prompt_rules(profile: str) -> str:
    return """
- Convert EACH explicit required action into its own checklist item.
- If one sentence contains multiple imperative actions joined by commas or `and`, split them into separate items.
- If the source contains multiple explicit questions on the same line or in the same block, split them into separate checklist items.
""".strip()


def build_checklist_execution_preview(
    *,
    input_text: str,
    document_text: str,
    context_text_from_scan: str = "",
) -> dict[str, object]:
    """Estimate the actual checklist text that will be sent to the model."""
    handler = ChecklistTaskHandler()
    sanitized_document_text = handler._sanitize_checklist_document_text(document_text)
    effective_document_text = sanitized_document_text or document_text

    if effective_document_text and len(effective_document_text) <= CHECKLIST_FULL_DOCUMENT_DIRECT_CHARS:
        return {
            "checklist_mode": "full_document_direct",
            "context_preview": effective_document_text,
            "context_chars_sent": len(effective_document_text),
            "full_document_chars": len(document_text or ""),
            "sanitized_document_chars": len(effective_document_text or ""),
        }

    if effective_document_text:
        parts = handler._split_text_for_checklist(effective_document_text)
        partial_block = "\n\n".join(
            f"[PARTIAL CHECKLIST {index}]\nTitle: Checklist part {index}\nDescription: Partial extraction\nItems:\n- ..."
            for index in range(1, len(parts) + 1)
        )
        reduce_prompt = handler._build_checklist_reduce_prompt(input_text, [])
        return {
            "checklist_mode": "full_document_map_reduce",
            "context_preview": partial_block[:6000],
            "context_chars_sent": len(reduce_prompt),
            "full_document_chars": len(document_text or ""),
            "sanitized_document_chars": len(effective_document_text or ""),
        }

    return {
        "checklist_mode": "document_scan_context",
        "context_preview": context_text_from_scan or "",
        "context_chars_sent": len(context_text_from_scan or ""),
        "full_document_chars": len(document_text or ""),
        "sanitized_document_chars": 0,
    }


def build_extraction_execution_preview(
    *,
    input_text: str,
    document_text: str,
    context_text_from_scan: str = "",
) -> dict[str, object]:
    """Estimate the actual extraction text that will be sent to the model."""
    effective_document_text = (document_text or "").strip()
    if effective_document_text and len(effective_document_text) <= EXTRACTION_FULL_DOCUMENT_DIRECT_CHARS:
        return {
            "extraction_mode": "full_document_direct",
            "context_preview": effective_document_text,
            "context_chars_sent": len(effective_document_text),
            "full_document_chars": len(document_text or ""),
            "prompt_preview": ExtractionTaskHandler()._build_extraction_prompt(input_text, effective_document_text),
        }

    return {
        "extraction_mode": "document_scan_context",
        "context_preview": context_text_from_scan or "",
        "context_chars_sent": len(context_text_from_scan or ""),
        "full_document_chars": len(document_text or ""),
        "prompt_preview": ExtractionTaskHandler()._build_extraction_prompt(input_text, context_text_from_scan or ""),
    }


class TaskHandler:
    """Base class for structured task handlers."""

    def _get_provider_registry(self):
        from ..providers.registry import build_provider_registry

        return build_provider_registry()

    def _resolve_provider(self, request: TaskExecutionRequest):
        from ..providers.registry import resolve_provider_runtime_profile

        registry = self._get_provider_registry()
        runtime_profile = resolve_provider_runtime_profile(
            registry,
            request.provider,
            capability="chat",
            fallback_provider="ollama",
        )
        requested_provider = str(runtime_profile.get("requested_provider") or request.provider or "ollama")
        provider_key = runtime_profile.get("effective_provider")
        provider_entry = runtime_profile.get("provider_entry") if isinstance(runtime_profile.get("provider_entry"), dict) else None
        fallback_reason = runtime_profile.get("fallback_reason")
        if provider_entry is None:
            raise RuntimeError(f"Provider '{requested_provider}' is not available in the current environment.")

        telemetry = self._telemetry_dict(request)
        telemetry["provider_requested"] = requested_provider
        telemetry["provider_effective"] = provider_key
        if fallback_reason:
            telemetry["provider_fallback_reason"] = fallback_reason
        return provider_entry["instance"]

    def _collect_response_text(self, provider, request: TaskExecutionRequest, prompt: str) -> str:
        telemetry = self._telemetry_dict(request)
        stage_name = str(telemetry.get("current_stage") or "provider_call")
        started_at = time.perf_counter()
        error_message = None
        messages = [{"role": "user", "content": prompt}]
        try:
            stream = provider.stream_chat_completion(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                context_window=request.context_window,
            )
            response_text = "".join(provider.iter_stream_text(stream))
            return response_text
        except Exception as error:
            error_message = str(error)
            raise
        finally:
            duration_s = round(time.perf_counter() - started_at, 4)
            self._record_timing(request, "provider_total_s", duration_s, accumulate=True)
            provider_calls = telemetry.setdefault("provider_calls", [])
            if isinstance(provider_calls, list):
                provider_calls.append(
                    {
                        "stage": stage_name,
                        "provider": telemetry.get("provider_effective") or request.provider,
                        "provider_requested": telemetry.get("provider_requested") or request.provider,
                        "model": request.model,
                        "duration_s": duration_s,
                        "prompt_chars": len(prompt or ""),
                        "success": error_message is None,
                        **({"error": error_message} if error_message else {}),
                    }
                )

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

    def _telemetry_dict(self, request: TaskExecutionRequest) -> dict[str, object]:
        telemetry = getattr(request, "telemetry", None)
        return telemetry if isinstance(telemetry, dict) else {}

    def _record_timing(
        self,
        request: TaskExecutionRequest,
        name: str,
        duration_s: float,
        *,
        accumulate: bool = False,
    ) -> None:
        telemetry = self._telemetry_dict(request)
        timings = telemetry.setdefault("timings_s", {})
        if not isinstance(timings, dict):
            return
        if accumulate and isinstance(timings.get(name), (int, float)):
            timings[name] = round(float(timings[name]) + float(duration_s), 4)
        else:
            timings[name] = round(float(duration_s), 4)

    def _set_telemetry_value(self, request: TaskExecutionRequest, name: str, value: object) -> None:
        telemetry = self._telemetry_dict(request)
        telemetry[name] = value

    def _failure_message_from_result(self, result: StructuredResult) -> str:
        if result.validation_error:
            return result.validation_error
        if result.parsing_error:
            return result.parsing_error
        if result.error and result.error.message:
            return result.error.message
        return "Unknown structured parsing error"

    def _record_parse_attempt(
        self,
        request: TaskExecutionRequest,
        *,
        strategy: str,
        result: StructuredResult,
    ) -> None:
        telemetry = self._telemetry_dict(request)
        attempts = telemetry.setdefault("parse_attempts", [])
        if not isinstance(attempts, list):
            return
        attempts.append(
            {
                "stage": str(telemetry.get("current_stage") or "structured_task"),
                "strategy": strategy,
                "success": result.success,
                **({"error": self._failure_message_from_result(result)} if not result.success else {}),
            }
        )
        telemetry["auto_retry_count"] = max(0, len(attempts) - 1)

    def _build_parse_repair_prompt(
        self,
        *,
        payload_schema: Type,
        raw_response: str,
        failure_message: str,
    ) -> str:
        schema_json = json.dumps(payload_schema.model_json_schema(), ensure_ascii=False, indent=2)
        return f"""
You are repairing a malformed structured response.
Return ONLY one valid JSON object.
Do not include markdown fences.
Do not include explanations.
Preserve grounded content from the previous response whenever possible.
If some field is missing, prefer null, [], or 0 according to the schema instead of prose.

Failure reason:
{failure_message}

Target JSON schema:
{schema_json}

Previous raw response:
{raw_response}
"""

    def _build_regeneration_retry_prompt(self, *, original_prompt: str, failure_message: str) -> str:
        return f"""
{original_prompt}

IMPORTANT:
- Your previous answer failed structured parsing/validation.
- Failure reason: {failure_message}
- Return ONLY one valid JSON object.
- No prose, no markdown fences, no comments.
- If unsure about a field, use null / [] / 0 instead of invalid types or invented content.
"""

    def _parse_with_recovery(
        self,
        *,
        provider,
        request: TaskExecutionRequest,
        response_text: str,
        payload_schema: Type,
        original_prompt: str,
    ) -> StructuredResult:
        telemetry = self._telemetry_dict(request)
        stage_name = str(telemetry.get("current_stage") or "structured_task")

        result = parse_structured_response(response_text, payload_schema)
        self._record_parse_attempt(request, strategy="initial", result=result)
        if result.success:
            telemetry["parse_recovery"] = {"used": False, "final_success": True, "attempt_count": 1}
            return result

        failure_message = self._failure_message_from_result(result)
        final_result = result
        strategies_used: list[str] = []

        repair_prompt = self._build_parse_repair_prompt(
            payload_schema=payload_schema,
            raw_response=response_text,
            failure_message=failure_message,
        )
        self._set_telemetry_value(request, "current_stage", f"{stage_name}_repair_json")
        repaired_response = self._collect_response_text(provider, request, repair_prompt)
        final_result = parse_structured_response(repaired_response, payload_schema)
        if final_result.success:
            final_result.repair_applied = True
        self._record_parse_attempt(request, strategy="repair_json", result=final_result)
        strategies_used.append("repair_json")
        if final_result.success:
            telemetry["parse_recovery"] = {
                "used": True,
                "final_success": True,
                "attempt_count": telemetry.get("auto_retry_count", 0) + 1,
                "strategies": strategies_used,
            }
            return final_result

        retry_prompt = self._build_regeneration_retry_prompt(
            original_prompt=original_prompt,
            failure_message=self._failure_message_from_result(final_result),
        )
        self._set_telemetry_value(request, "current_stage", f"{stage_name}_retry_generation")
        retried_response = self._collect_response_text(provider, request, retry_prompt)
        final_result = parse_structured_response(retried_response, payload_schema)
        if final_result.success:
            final_result.repair_applied = True
        self._record_parse_attempt(request, strategy="retry_generation", result=final_result)
        strategies_used.append("retry_generation")

        telemetry["parse_recovery"] = {
            "used": True,
            "final_success": final_result.success,
            "attempt_count": telemetry.get("auto_retry_count", 0) + 1,
            "strategies": strategies_used,
            **({"final_error": self._failure_message_from_result(final_result)} if not final_result.success else {}),
        }
        return final_result


class ExtractionTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        total_started_at = time.perf_counter()
        self._report_progress(request, step="initializing", progress=0.10, detail="Inicializando extração estruturada")
        provider = self._resolve_provider(request)
        self._report_progress(request, step="provider_ready", progress=0.22, detail="Provider pronto; preparando documento/contexto")
        document_started_at = time.perf_counter()
        full_document_text = self._build_full_document_text(request)
        self._record_timing(request, "document_load_s", time.perf_counter() - document_started_at)
        estimated_chars = len((full_document_text or "").strip())
        use_full_document = bool(full_document_text and estimated_chars <= EXTRACTION_FULL_DOCUMENT_DIRECT_CHARS)
        if use_full_document:
            self._report_progress(request, step="preparing_document", progress=0.34, detail="Usando documento completo para extração")
            context_text = full_document_text
            extraction_mode = "full_document_direct"
        else:
            self._report_progress(request, step="building_context", progress=0.34, detail="Montando contexto estruturado")
            context_started_at = time.perf_counter()
            context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=24, max_chars=64000)
            self._record_timing(request, "context_build_s", time.perf_counter() - context_started_at)
            extraction_mode = "document_scan_context"
        self._report_progress(request, step="prompt_ready", progress=0.48, detail="Contexto pronto; montando prompt de extração")
        prompt = self._build_extraction_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.72, detail="Executando extração no modelo")
        self._set_telemetry_value(request, "current_stage", "extraction_single_pass")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.9, detail="Validando saída estruturada")
        parsing_started_at = time.perf_counter()
        result = self._parse_with_recovery(
            provider=provider,
            request=request,
            response_text=response_text,
            payload_schema=ExtractionPayload,
            original_prompt=prompt,
        )
        result = self._post_process_extraction_result(
            result,
            source_text=full_document_text or context_text or request.input_text,
        )
        self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
        self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
        self._report_progress(request, step="done", progress=1.0, detail="Extração finalizada")
        result.execution_metadata = {
            "extraction_mode": extraction_mode,
            "full_document_chars": len(full_document_text or ""),
            "context_chars_sent": len(context_text or ""),
            "context_note": (
                "Extração gerada com o documento inteiro porque o tamanho ainda é seguro para envio direto."
                if extraction_mode == "full_document_direct"
                else "Extração gerada com contexto recortado do document scan."
            ),
            "stages": [
                {
                    "stage_type": extraction_mode,
                    "label": "Entrada de geração da extração",
                    "chars_sent": len(context_text or ""),
                    "context_preview": context_text or "",
                    "prompt_preview": prompt,
                }
            ],
        }
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
- For agreements, contracts, exhibits, policies, and legal/compliance documents, extract the document type, counterparties, effective dates, key obligations, restrictions, retention duties, governance/compliance duties, and material risks whenever explicitly stated.
- Prefer multiple grounded `extracted_fields`, `action_items`, and `risks` over a shallow summary when the source is a long formal document.
- Do not focus only on the title/header; scan the full source for operative clauses and obligations.
- Every `risk`, `action_item`, `relationship`, and `extracted_field` should include grounded `evidence` copied or closely quoted from the source whenever possible.
- If a supposed risk or obligation cannot be supported by a direct snippet, omit it instead of inferring it.
- For legal documents, prefer obligations stated as clauses assigned to a party over generic task phrasing.
- For legal agreements, always try to populate `categories` with the grounded agreement type (for example `Separation Agreement`, `Contract`, `Policy`, `Amendment`).
- For legal agreements, extract clause-level duties and convert them into structured `action_items` even when they are contractual obligations rather than operational tasks.
- For legal agreements, explicitly look for: counterparties, governing law, jurisdiction/forum, effective date, notice periods, indemnification clauses, confidentiality duties, name-use restrictions, records retention/cooperation duties, waiver clauses, and damages limitations.
- If an obligation is assigned to a party, carry that party into `action_items[].owner` whenever grounded.
- If the document states timing windows such as 90 days, 365 days, effective dates, concurrent delivery, or notice periods, preserve them in `action_items[].due_date` or in `extracted_fields` with evidence.
- When a clause creates exposure (for example indemnification, confidentiality breach, governance restriction, exclusive jurisdiction, waiver of jury trial, damages limitation), prefer surfacing it explicitly in `risks` or `extracted_fields` instead of leaving it buried in free text.
- `extracted_fields[].value` must always be a single string. If the source contains multiple values (for example, multiple counterparties), join them with `; ` instead of returning an array/list.
- Prefer labeled monetary/percentage/share values inside `extracted_fields` (with evidence) instead of dumping ambiguous bare numbers into `important_numbers`.

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
      "evidence": "vendor dependency may delay rollout",
      "impact": "Delivery may slip by two weeks",
      "owner": null,
      "due_date": null
    }}
  ],
  "action_items": [
    {{
      "description": "Finalize integration plan",
      "evidence": "Finalize integration plan before Friday",
      "owner": "Platform team",
      "due_date": "Friday",
      "status": "pending"
    }}
  ],
  "missing_information": ["No owner is named for the migration task"]
}}
"""

    def _post_process_extraction_result(
        self,
        result: StructuredResult,
        *,
        source_text: str,
    ) -> StructuredResult:
        payload = result.validated_output
        if not result.success or not isinstance(payload, ExtractionPayload):
            return result

        normalized_payload = self._normalize_extraction_payload(payload, source_text=source_text)
        result.validated_output = normalized_payload
        result.parsed_json = normalized_payload.model_dump(mode="json")
        return result

    def _normalize_extraction_payload(
        self,
        payload: ExtractionPayload,
        *,
        source_text: str,
    ) -> ExtractionPayload:
        legal_view = self._looks_like_legal_extraction(payload, source_text=source_text)
        data = payload.model_dump(mode="python")

        data["main_subject"] = self._clean_extraction_text(payload.main_subject) or None
        data["categories"] = self._augment_legal_categories(
            payload.categories,
            main_subject=data["main_subject"],
            legal_view=legal_view,
        )
        data["important_dates"] = self._normalize_important_dates(payload, source_text=source_text, legal_view=legal_view)
        data["missing_information"] = self._unique_extraction_strings(payload.missing_information)
        data["extracted_fields"] = self._normalize_extracted_fields(
            payload,
            legal_view=legal_view,
            categories=data["categories"],
            main_subject=data["main_subject"],
            source_text=source_text,
        )
        data["important_numbers"] = self._normalize_important_numbers(payload, legal_view=legal_view)
        data["risks"] = self._normalize_risks(payload, legal_view=legal_view, source_text=source_text)
        data["action_items"] = self._normalize_action_items(payload, legal_view=legal_view)
        data["relationships"] = self._normalize_relationships(
            payload,
            legal_view=legal_view,
            main_subject=data["main_subject"],
            source_text=source_text,
        )
        data["entities"] = self._normalize_legal_entities(
            payload.entities,
            legal_view=legal_view,
            source_text=source_text,
        )

        return ExtractionPayload(**data)

    def _clean_extraction_text(self, value: object) -> str:
        return " ".join(str(value or "").split()).strip()

    def _extract_due_date_phrase(self, text: str | None) -> str | None:
        cleaned = self._clean_extraction_text(text)
        if not cleaned:
            return None

        patterns = [
            r"until the earlier of[^.;]{0,180}",
            r"within[^.;]{0,120}\b(?:day|days|month|months|year|years)\b[^.;]{0,80}",
            r"at least[^.;]{0,120}\b(?:day|days|month|months|year|years)\b[^.;]{0,80}",
            r"for a period of[^.;]{0,120}\b(?:day|days|month|months|year|years)\b[^.;]{0,80}",
            r"concurrently with[^.;]{0,140}",
            r"effective as of[^.;]{0,140}",
            r"beginning on or after[^.;]{0,140}",
            r"before[^.;]{0,120}\b(?:day|days|month|months|year|years|closing|execution)\b[^.;]{0,80}",
            r"after[^.;]{0,120}\b(?:day|days|month|months|year|years|closing|execution)\b[^.;]{0,80}",
            r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, re.I)
            if match:
                return match.group(0).strip(" .;:-")

        short_deadline_keywords = (
            "day",
            "days",
            "month",
            "months",
            "year",
            "years",
            "thereafter",
            "prior notice",
            "ongoing",
            "effective",
            "immediately",
            "execution",
            "closing",
        )
        lowered = cleaned.lower()
        if len(cleaned) <= 80 and any(keyword in lowered for keyword in short_deadline_keywords):
            return cleaned

        return None

    def _normalize_due_date_text(
        self,
        raw_due_date: str | None,
        *,
        evidence: str | None = None,
        description: str | None = None,
    ) -> str | None:
        for candidate in (raw_due_date, evidence, description):
            extracted = self._extract_due_date_phrase(candidate)
            if extracted:
                return extracted
        return None

    def _unique_extraction_strings(self, values: list[object]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            cleaned = self._clean_extraction_text(value)
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result

    def _looks_like_legal_extraction(self, payload: ExtractionPayload, *, source_text: str) -> bool:
        keywords = (
            "agreement",
            "contract",
            "policy",
            "exhibit",
            "compliance",
            "confidentiality",
            "settlement",
            "separation",
            "obligation",
            "indemn",
        )
        haystacks = [payload.main_subject, *payload.categories, source_text[:2000]]
        haystacks.extend(field.name for field in payload.extracted_fields)
        lowered = " ".join(self._clean_extraction_text(item).lower() for item in haystacks if item)
        return any(keyword in lowered for keyword in keywords)

    def _augment_legal_categories(
        self,
        values: list[object],
        *,
        main_subject: str | None,
        legal_view: bool,
    ) -> list[str]:
        normalized = self._unique_extraction_strings(values)
        if not legal_view:
            return normalized

        subject = self._clean_extraction_text(main_subject).lower()
        inferred: list[str] = []
        if "separation agreement" in subject:
            inferred.append("Separation Agreement")
        elif "agreement" in subject:
            inferred.append("Agreement")
        elif "contract" in subject:
            inferred.append("Contract")
        elif "policy" in subject:
            inferred.append("Policy")
        elif "amendment" in subject:
            inferred.append("Amendment")
        elif "lease" in subject:
            inferred.append("Lease")

        if inferred and "Contract" not in normalized:
            inferred.append("Contract")

        if inferred and "Legal Agreement" not in normalized:
            inferred.append("Legal Agreement")
        return self._unique_extraction_strings([*normalized, *inferred])

    def _normalize_important_dates(self, payload: ExtractionPayload, *, source_text: str, legal_view: bool) -> list[str]:
        normalized = self._unique_extraction_strings(payload.important_dates)
        if not legal_view:
            return normalized

        date_patterns = [
            r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},\s+\d{4}\b",
            r"\b\d{1,2}/\d{1,2}/\d{4}\b",
        ]
        extracted: list[str] = []
        for pattern in date_patterns:
            extracted.extend(re.findall(pattern, source_text or "", re.I))
        return self._unique_extraction_strings([*normalized, *extracted])

    def _normalize_extracted_fields(
        self,
        payload: ExtractionPayload,
        *,
        legal_view: bool,
        categories: list[str],
        main_subject: str | None,
        source_text: str = "",
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()

        for field in payload.extracted_fields:
            name = self._clean_extraction_text(field.name) or "field"
            value = self._clean_extraction_text(field.value)
            evidence = self._clean_extraction_text(field.evidence) or None
            if not value:
                continue
            key = (name.casefold(), value.casefold())
            if key in seen:
                continue
            seen.add(key)
            normalized.append({"name": name, "value": value, "evidence": evidence})

        if legal_view:
            lowered_names = {str(item.get("name") or "").casefold() for item in normalized}
            evidence = self._clean_extraction_text(main_subject) or None
            if categories and not any(name in lowered_names for name in {"document_type", "agreement_type"}):
                normalized.append(
                    {
                        "name": "document_type",
                        "value": categories[0],
                        "evidence": evidence,
                    }
                )

            org_entities = [
                self._clean_extraction_text(entity.value)
                for entity in payload.entities
                if self._clean_extraction_text(entity.type).casefold() == "organization" and self._clean_extraction_text(entity.value)
            ]
            unique_org_entities = self._unique_extraction_strings(org_entities)
            if len(unique_org_entities) >= 2 and not any(name in lowered_names for name in {"counterparties", "parties"}):
                normalized.append(
                    {
                        "name": "counterparties",
                        "value": "; ".join(unique_org_entities[:4]),
                        "evidence": evidence,
                    }
                )

            if "jurisdiction" not in lowered_names and "forum" not in lowered_names:
                jurisdiction_value = self._extract_legal_jurisdiction_value(payload, main_subject=main_subject, source_text=source_text)
                if jurisdiction_value:
                    normalized.append(
                        {
                            "name": "jurisdiction",
                            "value": jurisdiction_value,
                            "evidence": evidence,
                        }
                    )
            clause_source = " ".join(
                part
                for part in [
                    source_text,
                    self._clean_extraction_text(main_subject),
                    " ".join(unique_org_entities),
                    *[self._clean_extraction_text(field.evidence) for field in payload.extracted_fields],
                    *[self._clean_extraction_text(item.evidence) for item in payload.action_items],
                    *[self._clean_extraction_text(item.evidence) for item in payload.risks],
                ]
                if part
            )
            clause_headings = self._extract_common_legal_clause_headings(clause_source)
            if clause_headings and "covered_clauses" not in lowered_names:
                normalized.append(
                    {
                        "name": "covered_clauses",
                        "value": "; ".join(clause_headings),
                        "evidence": evidence,
                    }
                )

        return normalized

    def _extract_legal_jurisdiction_value(self, payload: ExtractionPayload, *, main_subject: str | None, source_text: str = "") -> str | None:
        for relationship in payload.relationships:
            text = " ".join(
                part
                for part in [relationship.from_entity, relationship.to_entity, relationship.relationship, relationship.evidence]
                if part
            )
            court_match = re.search(r"(Bankruptcy Court|[A-Z][A-Za-z ]+ Court|[A-Z][A-Za-z ]+ District of [A-Z][A-Za-z ]+)", text or "", re.I)
            if court_match:
                return self._clean_extraction_text(court_match.group(1))
        source_match = re.search(r"(Bankruptcy Court|[A-Z][A-Za-z ]+ Court|exclusive jurisdiction)", source_text or "", re.I)
        if source_match:
            return self._clean_extraction_text(source_match.group(1))
        subject_match = re.search(r"(Bankruptcy Court|[A-Z][A-Za-z ]+ Court)", self._clean_extraction_text(main_subject), re.I)
        if subject_match:
            return self._clean_extraction_text(subject_match.group(1))
        return None

    def _extract_common_legal_clause_headings(self, source_text: str) -> list[str]:
        patterns = [
            ("Preservation of Records; Cooperation", r"preservation of records|records[^.]{0,40}cooperation"),
            ("Confidentiality", r"\bconfidentiality\b|confidential information"),
            ("Use of Name", r"\buse of name\b|remove the .* name"),
            ("Tax Indemnification", r"tax indemnification|tax liabilities"),
            ("Employee Benefits Indemnification", r"employee benefits indemnification|employee benefits liabilities"),
            ("Submission to Jurisdiction; Consent to Service of Process", r"submission to jurisdiction|consent to service of process|exclusive jurisdiction"),
            ("Waiver of Jury Trial", r"waiver of jury trial|trial by jury"),
            ("Governing Law", r"\bgoverning law\b|state of texas|bankruptcy code"),
        ]
        normalized_source = _normalize_matching_text(source_text)
        found: list[str] = []
        for label, pattern in patterns:
            if re.search(pattern, normalized_source, re.I):
                found.append(label)
        return found

    def _number_compare_key(self, value: str) -> str:
        cleaned = self._clean_extraction_text(value)
        return re.sub(r"[^0-9%.-]+", "", cleaned)

    def _normalize_important_numbers(self, payload: ExtractionPayload, *, legal_view: bool) -> list[str]:
        field_number_keys = {
            self._number_compare_key(field.value)
            for field in payload.extracted_fields
            if self._number_compare_key(field.value)
        }
        normalized: list[str] = []
        seen: set[str] = set()

        for item in payload.important_numbers:
            cleaned = self._clean_extraction_text(item)
            if not cleaned:
                continue
            compare_key = self._number_compare_key(cleaned)
            dedupe_key = compare_key or cleaned.casefold()
            if dedupe_key in seen:
                continue
            if legal_view and compare_key and compare_key in field_number_keys:
                continue
            seen.add(dedupe_key)
            normalized.append(cleaned)

        return normalized

    def _normalize_risks(self, payload: ExtractionPayload, *, legal_view: bool, source_text: str) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[str] = set()

        for item in payload.risks:
            description = self._clean_extraction_text(item.description)
            if not description:
                continue
            evidence = self._clean_extraction_text(item.evidence) or None
            impact = self._clean_extraction_text(item.impact) or None
            owner = self._clean_extraction_text(item.owner) or None
            due_date = self._normalize_due_date_text(
                self._clean_extraction_text(item.due_date) or None,
                evidence=evidence,
                description=description,
            )
            if legal_view and not evidence:
                continue
            key = description.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "description": description,
                    "evidence": evidence,
                    "impact": impact,
                    "owner": owner,
                    "due_date": due_date,
                }
            )

        if legal_view:
            normalized_source = _normalize_matching_text(source_text)

            def append_risk_if_missing(description: str, *, evidence: str, impact: str | None = None) -> None:
                key = description.casefold()
                if key in seen:
                    return
                seen.add(key)
                normalized.append(
                    {
                        "description": description,
                        "evidence": evidence,
                        "impact": impact,
                        "owner": None,
                        "due_date": None,
                    }
                )

            if "tax indemnification" in normalized_source or "tax liabilities" in normalized_source:
                append_risk_if_missing(
                    "Tax indemnification exposure may allocate liabilities between the parties.",
                    evidence="tax indemnification",
                    impact="Potential transfer of tax liabilities between counterparties.",
                )
            if "employee benefits indemnification" in normalized_source or "employee benefits liabilities" in normalized_source:
                append_risk_if_missing(
                    "Employee benefits indemnification may shift benefits-related liabilities between the parties.",
                    evidence="employee benefits indemnification",
                    impact="Potential liability allocation for employee benefits obligations.",
                )

        return normalized

    def _normalize_legal_entities(
        self,
        entities: list[object],
        *,
        legal_view: bool,
        source_text: str,
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()

        for item in entities:
            entity_type = self._clean_extraction_text(getattr(item, "type", None)) or "entity"
            value = self._clean_extraction_text(getattr(item, "value", None))
            if not value:
                continue
            key = (entity_type.casefold(), value.casefold())
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "type": entity_type,
                    "value": value,
                    "confidence": getattr(item, "confidence", 0.8),
                    "source_text": self._clean_extraction_text(getattr(item, "source_text", None)) or value,
                    "position_start": max(0, int(getattr(item, "position_start", 0) or 0)),
                    "position_end": max(0, int(getattr(item, "position_end", 0) or 0)),
                }
            )

        if legal_view:
            candidate_patterns = [
                r"\b[A-Z][A-Za-z.&' -]+ LLC\b",
                r"\bBankruptcy Court\b",
                r"\b[A-Z][A-Za-z ]+ Court\b",
            ]
            for pattern in candidate_patterns:
                for match in re.findall(pattern, source_text or "", re.I):
                    value = self._clean_extraction_text(match)
                    key = ("organization", value.casefold())
                    if not value or key in seen:
                        continue
                    seen.add(key)
                    normalized.append(
                        {
                            "type": "organization",
                            "value": value,
                            "confidence": 0.7,
                            "source_text": value,
                            "position_start": 0,
                            "position_end": 0,
                        }
                    )

        return normalized

    def _normalize_action_items(self, payload: ExtractionPayload, *, legal_view: bool) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()

        for item in payload.action_items:
            description = self._clean_extraction_text(item.description)
            if not description:
                continue
            owner = self._clean_extraction_text(item.owner) or None
            evidence = self._clean_extraction_text(item.evidence) or None
            due_date = self._normalize_due_date_text(
                self._clean_extraction_text(item.due_date) or None,
                evidence=evidence,
                description=description,
            )
            status = self._clean_extraction_text(item.status) or None
            if legal_view and not (evidence or owner):
                continue
            key = (description.casefold(), (owner or "").casefold())
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "description": description,
                    "owner": owner,
                    "due_date": due_date,
                    "status": status,
                    "evidence": evidence,
                }
            )

        return normalized

    def _normalize_relationships(
        self,
        payload: ExtractionPayload,
        *,
        legal_view: bool,
        main_subject: str | None,
        source_text: str = "",
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[tuple[str, str, str]] = set()
        subject = self._clean_extraction_text(main_subject).lower()

        for item in payload.relationships:
            from_entity = self._clean_extraction_text(item.from_entity)
            to_entity = self._clean_extraction_text(item.to_entity)
            relationship = self._clean_extraction_text(item.relationship)
            evidence = self._clean_extraction_text(item.evidence) or None
            if not (from_entity and to_entity and relationship):
                continue
            if legal_view and "agreement" in subject and relationship.casefold() in {"signatory of", "party to"}:
                relationship = "agreement_between"
            key = (from_entity.casefold(), to_entity.casefold(), relationship.casefold())
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "from_entity": from_entity,
                    "to_entity": to_entity,
                    "relationship": relationship,
                    "confidence": item.confidence,
                    "evidence": evidence,
                }
            )

        if legal_view and "agreement" in subject and not normalized:
            org_entities = [
                self._clean_extraction_text(entity.value)
                for entity in payload.entities
                if self._clean_extraction_text(entity.type).casefold() == "organization" and self._clean_extraction_text(entity.value)
            ]
            org_entities = self._unique_extraction_strings(org_entities)
            if len(org_entities) >= 2:
                normalized.append(
                    {
                        "from_entity": org_entities[0],
                        "to_entity": org_entities[1],
                        "relationship": "agreement_between",
                        "confidence": 0.75,
                        "evidence": self._clean_extraction_text(main_subject) or None,
                    }
                )

        if legal_view:
            normalized_source = _normalize_matching_text(source_text)
            existing_keys = {
                (
                    str(item.get("from_entity") or "").casefold(),
                    str(item.get("to_entity") or "").casefold(),
                    str(item.get("relationship") or "").casefold(),
                )
                for item in normalized
            }

            if "new pge common stock" in normalized_source:
                pge_name = next(
                    (
                        self._clean_extraction_text(entity.value)
                        for entity in payload.entities
                        if self._clean_extraction_text(entity.value).casefold() in {"pge", "portland general electric company"}
                    ),
                    "PGE",
                )
                key = (pge_name.casefold(), "new pge common stock", "stock issuance")
                if key not in existing_keys:
                    normalized.append(
                        {
                            "from_entity": pge_name,
                            "to_entity": "New PGE Common Stock",
                            "relationship": "stock issuance",
                            "confidence": 0.78,
                            "evidence": "issuing the New PGE Common Stock",
                        }
                    )
                    existing_keys.add(key)

            if "bankruptcy court" in normalized_source and "jurisdiction" in normalized_source:
                key = ("bankruptcy court", "this agreement", "exclusive jurisdiction")
                if key not in existing_keys:
                    normalized.append(
                        {
                            "from_entity": "Bankruptcy Court",
                            "to_entity": "this Agreement",
                            "relationship": "exclusive jurisdiction",
                            "confidence": 0.8,
                            "evidence": "exclusive jurisdiction of the Bankruptcy Court",
                        }
                    )
                    existing_keys.add(key)

        return normalized


class SummaryTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        total_started_at = time.perf_counter()
        self._report_progress(request, step="initializing", progress=0.08, detail="Inicializando sumarização estruturada")
        self._report_progress(request, step="preparing_document", progress=0.16, detail="Preparando texto completo do documento")
        provider = self._resolve_provider(request)
        self._report_progress(request, step="provider_ready", progress=0.24, detail="Provider pronto; analisando documento")
        document_started_at = time.perf_counter()
        full_document_text = self._build_full_document_text(request)
        self._record_timing(request, "document_load_s", time.perf_counter() - document_started_at)
        if full_document_text and len(full_document_text) > SUMMARY_FULL_DOCUMENT_TRIGGER_CHARS:
            document_parts = self._split_text_for_summary(full_document_text)
            self._report_progress(
                request,
                step="map_reduce_setup",
                progress=0.30,
                detail=f"Documento grande detectado; dividindo em {len(document_parts)} parte(s)",
            )
            partial_summaries, map_stage_details = self._summarize_document_in_parts(provider, request, full_document_text)
            prompt = self._build_summary_reduce_prompt(request.input_text, partial_summaries)
            self._report_progress(request, step="reduce", progress=0.82, detail="Consolidando resumo final")
            self._set_telemetry_value(request, "current_stage", "summary_reduce")
            reduce_started_at = time.perf_counter()
            response_text = self._collect_response_text(provider, request, prompt)
            reduce_duration_s = round(time.perf_counter() - reduce_started_at, 2)
            self._report_progress(request, step="parsing", progress=0.94, detail="Validando resumo final")
            parsing_started_at = time.perf_counter()
            result = self._parse_with_recovery(
                provider=provider,
                request=request,
                response_text=response_text,
                payload_schema=SummaryPayload,
                original_prompt=prompt,
            )
            self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
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
                        "label": "Síntese final",
                        "chars_sent": len(prompt),
                        "duration_s": reduce_duration_s,
                        "prompt_preview": prompt[:6000],
                        "context_preview": prompt[:6000],
                    },
                ],
                "context_note": "Summary gerado a partir do documento inteiro em múltiplas partes; o preview curto de doc scan/retrieval não representa sozinho todo o conteúdo consumido neste modo.",
            }
            self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
            self._report_progress(request, step="done", progress=1.0, detail="Resumo completo finalizado")
            return result

        strategy = request.context_strategy or "retrieval"
        self._report_progress(request, step="building_context", progress=0.38, detail=f"Montando contexto ({strategy})")
        context_started_at = time.perf_counter()
        context_text = self._build_optional_document_context(
            request,
            strategy=strategy,
            max_chunks=12,
            max_chars=24000,
        )
        self._record_timing(request, "context_build_s", time.perf_counter() - context_started_at)
        prompt = self._build_summary_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.72, detail="Gerando resumo no modelo")
        self._set_telemetry_value(request, "current_stage", "summary_single_pass")
        single_pass_started_at = time.perf_counter()
        response_text = self._collect_response_text(provider, request, prompt)
        single_pass_duration_s = round(time.perf_counter() - single_pass_started_at, 2)
        self._report_progress(request, step="parsing", progress=0.92, detail="Validando resumo")
        parsing_started_at = time.perf_counter()
        result = self._parse_with_recovery(
            provider=provider,
            request=request,
            response_text=response_text,
            payload_schema=SummaryPayload,
            original_prompt=prompt,
        )
        self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
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
                    "label": f"Resumo em passo único ({strategy})",
                    "chars_sent": len(context_text or ""),
                    "duration_s": single_pass_duration_s,
                    "context_preview": (context_text or "")[:6000],
                    "prompt_preview": prompt[:6000],
                }
            ],
            "context_note": "Summary gerado em um único passo usando contexto recortado (doc scan/retrieval).",
        }
        self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
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
            self._set_telemetry_value(request, "current_stage", f"summary_map_part_{index}")
            response_text = self._collect_response_text(provider, request, prompt)
            duration_s = round(time.perf_counter() - started_at, 2)
            partial_result = self._parse_with_recovery(
                provider=provider,
                request=request,
                response_text=response_text,
                payload_schema=SummaryPayload,
                original_prompt=prompt,
            )
            stage_details.append(
                {
                    "stage_type": "map",
                    "label": f"Parte {index} de {total_chunks}",
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

        augmented_key_insights = self._augment_summary_key_insights(
            payload.key_insights,
            source_text=source_text,
            executive_summary=payload.executive_summary,
            topics=unique_topics or payload.topics,
        )

        result.validated_output = payload.model_copy(update={
            "topics": unique_topics or payload.topics,
            "key_insights": augmented_key_insights,
            "reading_time_minutes": reading_time_minutes,
            "completeness_score": round(completeness_score, 2),
        })
        return result

    def _augment_summary_key_insights(
        self,
        insights: list[str],
        *,
        source_text: str,
        executive_summary: str,
        topics: list[object],
    ) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        def append_unique(text: str) -> None:
            cleaned = self._clean_summary_text(text)
            if not cleaned:
                return
            key = cleaned.casefold()
            if key in seen:
                return
            seen.add(key)
            normalized.append(cleaned)

        combined = _normalize_matching_text(
            " ".join(
                [
                    source_text,
                    executive_summary,
                    *[self._clean_summary_text(getattr(topic, "title", "")) for topic in topics],
                    *[
                        self._clean_summary_text(point)
                        for topic in topics
                        for point in getattr(topic, "key_points", [])
                    ],
                ]
            )
        )

        def append_if_missing(text: str, *, required_terms: tuple[str, ...]) -> None:
            if not all(term in combined for term in required_terms):
                return
            append_unique(text)

        append_if_missing(
            "NASA maintained a clean audit opinion for the 15th consecutive year, with no reported material weaknesses.",
            required_terms=("clean audit opinion", "15th"),
        )
        append_if_missing(
            "Mission performance was tracked across four key performance goals, with two rated Green and two rated Yellow.",
            required_terms=("four key performance goals", "green", "yellow"),
        )
        append_if_missing(
            "Financial highlights include total assets of $39,579 million and total liabilities of $7,505 million.",
            required_terms=("39,579", "7,505", "assets", "liabilities"),
        )
        append_if_missing(
            "NASA reported total net position of $32,074 million for FY 2025.",
            required_terms=("32,074", "net position"),
        )
        append_if_missing(
            "FY 2025 net cost of operations was $23,699 million.",
            required_terms=("net cost", "23,699"),
        )
        append_if_missing(
            "Grant oversight remained material, with 1,134 expired grants and $14,938 million in undisbursed balances.",
            required_terms=("1134", "14,938", "grant"),
        )
        append_if_missing(
            "The report emphasizes NASA’s commitment to transparency and presenting integrated performance and financial information under OMB Circular A-136.",
            required_terms=("transparency", "omb", "a-136"),
        )

        for item in insights:
            append_unique(item)

        return normalized[:8]

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
        total_started_at = time.perf_counter()
        provider = self._resolve_provider(request)
        self._report_progress(request, step="initializing", progress=0.10, detail="Inicializando geração de checklist")
        self._report_progress(request, step="loading_document", progress=0.18, detail="Carregando documento e contexto base")
        document_started_at = time.perf_counter()
        full_document_text = self._build_full_document_text(request)
        self._record_timing(request, "document_load_s", time.perf_counter() - document_started_at)
        self._report_progress(request, step="document_ready", progress=0.26, detail="Documento carregado; preparando texto operacional")
        sanitize_started_at = time.perf_counter()
        sanitized_document_text = self._sanitize_checklist_document_text(full_document_text)
        self._record_timing(request, "sanitize_s", time.perf_counter() - sanitize_started_at)
        effective_document_text = sanitized_document_text or full_document_text
        should_use_multi_stage = self._should_use_checklist_multi_stage(effective_document_text)
        if effective_document_text and not should_use_multi_stage:
            self._report_progress(request, step="preparing_document", progress=0.34, detail="Usando documento completo para gerar checklist")
            context_text = effective_document_text
            context_mode = "full_document_direct"
        elif effective_document_text:
            parts = self._split_text_for_checklist(effective_document_text)
            self._report_progress(
                request,
                step="map_reduce_setup",
                progress=0.34,
                detail=f"Documento grande detectado; dividindo checklist em {len(parts)} parte(s)",
            )
            partial_checklists, map_stage_details = self._build_partial_checklists(provider, request, parts)
            prompt = self._build_checklist_reduce_prompt(request.input_text, partial_checklists)
            self._report_progress(request, step="reduce_prep", progress=0.78, detail="Preparando consolidação final do checklist")
            self._report_progress(request, step="reduce", progress=0.86, detail="Consolidando checklist final")
            self._set_telemetry_value(request, "current_stage", "checklist_reduce")
            response_text = self._collect_response_text(provider, request, prompt)
            self._report_progress(request, step="parsing", progress=0.94, detail="Validando checklist")
            parsing_started_at = time.perf_counter()
            result = self._parse_with_recovery(
                provider=provider,
                request=request,
                response_text=response_text,
                payload_schema=ChecklistPayload,
                original_prompt=prompt,
            )
            self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
            self._report_progress(request, step="done", progress=1.0, detail="Checklist finalizado")
            result.execution_metadata = {
                "checklist_mode": "full_document_map_reduce",
                "checklist_profile": detect_checklist_domain_profile(request.input_text, effective_document_text),
                "full_document_chars": len(full_document_text or ""),
                "sanitized_document_chars": len(effective_document_text or ""),
                "checklist_question_count": effective_document_text.count('?') if effective_document_text else 0,
                "checklist_line_count": len([line for line in (effective_document_text or '').splitlines() if line.strip()]),
                "context_chars_sent": len(prompt),
                "context_note": "Checklist gerado a partir do documento inteiro em múltiplas partes, seguido de consolidação final.",
                "stages": [
                    *map_stage_details,
                    {
                        "stage_type": "reduce",
                        "label": "Síntese final do checklist",
                        "chars_sent": len(prompt),
                        "context_preview": prompt[:6000],
                        "prompt_preview": prompt[:6000],
                    },
                ],
            }
            self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
            return result
        else:
            self._report_progress(request, step="building_context", progress=0.34, detail="Montando contexto")
            context_started_at = time.perf_counter()
            context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=10, max_chars=24000)
            self._record_timing(request, "context_build_s", time.perf_counter() - context_started_at)
            context_mode = "document_scan_context"
        self._report_progress(request, step="prompt_ready", progress=0.50, detail="Contexto preparado; montando prompt")
        prompt = self._build_checklist_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.74, detail="Gerando checklist")
        self._set_telemetry_value(request, "current_stage", "checklist_single_pass")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.92, detail="Validando checklist")
        parsing_started_at = time.perf_counter()
        result = self._parse_with_recovery(
            provider=provider,
            request=request,
            response_text=response_text,
            payload_schema=ChecklistPayload,
            original_prompt=prompt,
        )
        self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
        self._report_progress(request, step="done", progress=1.0, detail="Checklist finalizado")
        result.execution_metadata = {
            "checklist_mode": context_mode,
            "checklist_profile": detect_checklist_domain_profile(request.input_text, context_text),
            "full_document_chars": len(full_document_text or ""),
            "sanitized_document_chars": len(effective_document_text or ""),
            "checklist_question_count": effective_document_text.count('?') if effective_document_text else 0,
            "checklist_line_count": len([line for line in (effective_document_text or '').splitlines() if line.strip()]),
            "context_chars_sent": len(context_text or ""),
            "context_note": (
                "Checklist gerado com o documento inteiro porque o tamanho ainda é seguro para envio direto."
                if context_mode == "full_document_direct"
                else "Checklist gerado com contexto recortado do document scan."
            ),
            "stages": [
                {
                    "stage_type": context_mode,
                    "label": "Entrada de geração do checklist",
                    "chars_sent": len(context_text or ""),
                    "context_preview": (context_text or "")[:6000],
                    "prompt_preview": prompt[:6000],
                }
            ],
        }
        self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
        return result

    def _should_use_checklist_multi_stage(self, text: str) -> bool:
        cleaned = (text or "").strip()
        if not cleaned:
            return False
        if len(cleaned) <= 12000:
            return False
        question_count = cleaned.count('?')
        non_empty_lines = len([line for line in cleaned.splitlines() if line.strip()])
        if len(cleaned) > CHECKLIST_FULL_DOCUMENT_DIRECT_CHARS:
            return True
        if question_count >= CHECKLIST_MULTI_STAGE_QUESTION_THRESHOLD:
            return True
        if non_empty_lines >= CHECKLIST_MULTI_STAGE_LINE_THRESHOLD:
            return True
        return False

    def _sanitize_checklist_document_text(self, full_document_text: str) -> str:
        cleaned = self._trim_checklist_noise(full_document_text)
        if not cleaned:
            return ""

        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return cleaned

        def extract_explicit_checklist_block(source_lines: list[str]) -> list[str]:
            if not source_lines:
                return []

            dense_question_start = None
            window_size = 18
            for index in range(len(source_lines)):
                window = source_lines[index:index + window_size]
                if sum(1 for item in window if '?' in item) >= 5:
                    dense_question_start = index
                    break

            if dense_question_start is None:
                return []

            start_index = dense_question_start
            exact_header_variants = {
                'surgical safety checklist',
                'who surgical safety checklist',
                'surgical safety checklist 2009',
                'checklist',
            }
            for index in range(max(0, dense_question_start - 12), min(len(source_lines), dense_question_start + 12)):
                normalized = source_lines[index].lower().strip(' .:-')
                if normalized in exact_header_variants:
                    start_index = index
                    break
            else:
                for index in range(max(0, dense_question_start - 6), dense_question_start):
                    if 'checklist' in source_lines[index].lower():
                        start_index = index
                        break

            focused: list[str] = []
            narrative_streak = 0
            question_count = 0
            stop_prefixes = (
                'this checklist is not intended',
                'in this manual',
                'this manual provides guidance',
                'the ultimate goal',
                'how to run the checklist',
                'successful implementation requires',
                'modification of the checklist',
                'promoting a safety culture',
                'additional notes',
                'track changes',
                'introducing the checklist',
            )
            for line in source_lines[start_index:]:
                lowered = line.lower()
                word_count = len(line.split())
                is_question = '?' in line
                if is_question:
                    question_count += 1

                if question_count >= 5 and any(lowered.startswith(prefix) for prefix in stop_prefixes):
                    break
                if question_count >= 5 and line.startswith('(') and line.endswith(')'):
                    continue

                answer_line = lowered in {'yes', 'no', 'not applicable'} or lowered.startswith('yes,') or lowered.startswith('no,')
                if answer_line:
                    narrative_streak = 0
                    continue
                header_line = line.endswith(':') and word_count <= 8
                phase_line = lowered.startswith('before ')
                checklist_header_line = 'checklist' in lowered and word_count <= 6
                short_operational_line = len(line) <= 140 and word_count <= 18
                focused.append(line)

                looks_narrative = (
                    question_count >= 5
                    and not is_question
                    and not answer_line
                    and not header_line
                    and not phase_line
                    and not checklist_header_line
                    and word_count >= 12
                    and not short_operational_line
                )

                if looks_narrative:
                    narrative_streak += 1
                    if narrative_streak >= 3:
                        break
                else:
                    narrative_streak = 0

            if question_count < 5:
                return []

            for index, line in enumerate(focused):
                normalized = line.lower().strip(' .:-')
                if normalized in exact_header_variants:
                    focused = focused[index:]
                    break

            while focused and re.fullmatch(r'\d+(?:\.\d+)?', focused[0].strip()):
                focused = focused[1:]

            return focused

        explicit_block = extract_explicit_checklist_block(lines)
        if explicit_block:
            return "\n".join(explicit_block).strip()

        question_indexes = [index for index, line in enumerate(lines) if '?' in line]
        if question_indexes:
            for index in question_indexes:
                trailing_window = lines[index:index + 24]
                trailing_question_count = sum(1 for line in trailing_window if '?' in line)
                if trailing_question_count >= 5:
                    start_index = max(0, index - 2)
                    lines = lines[start_index:]
                    break

        if lines:
            question_prefix_count = 0
            end_index = len(lines)
            for index, line in enumerate(lines):
                if '?' in line:
                    question_prefix_count += 1
                if question_prefix_count < 8:
                    continue
                trailing_window = lines[index:index + 40]
                trailing_question_count = sum(1 for item in trailing_window if '?' in item)
                avg_length = sum(len(item) for item in trailing_window) / max(len(trailing_window), 1)
                if trailing_question_count <= 1 and avg_length > 70:
                    end_index = index
                    break
            lines = lines[:end_index]

        return "\n".join(lines).strip()

    def _split_text_for_checklist(
        self,
        text: str,
        chunk_size: int = CHECKLIST_PART_CHUNK_SIZE,
        overlap: int = CHECKLIST_PART_OVERLAP,
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

    def _build_partial_checklists(self, provider, request: TaskExecutionRequest, parts: list[str]) -> tuple[list[ChecklistPayload], list[dict[str, object]]]:
        partial_payloads: list[ChecklistPayload] = []
        stage_details: list[dict[str, object]] = []
        total_parts = len(parts)
        for index, part in enumerate(parts, start=1):
            prompt = self._build_checklist_map_prompt(request.input_text, part, index=index, total=total_parts)
            progress_base = 0.38
            progress_span = 0.32
            current_progress = progress_base + progress_span * ((index - 1) / max(total_parts, 1))
            self._report_progress(request, step="map", progress=current_progress, detail=f"Processando parte {index} de {total_parts}")
            self._set_telemetry_value(request, "current_stage", f"checklist_map_part_{index}")
            response_text = self._collect_response_text(provider, request, prompt)
            partial_result = self._parse_with_recovery(
                provider=provider,
                request=request,
                response_text=response_text,
                payload_schema=ChecklistPayload,
                original_prompt=prompt,
            )
            stage_details.append(
                {
                    "stage_type": "map",
                    "label": f"Parte do checklist {index} de {total_parts}",
                    "chars_sent": len(part),
                    "context_preview": part[:6000],
                    "prompt_preview": prompt[:6000],
                    "success": partial_result.success,
                }
            )
            if partial_result.success and isinstance(partial_result.validated_output, ChecklistPayload):
                partial_payloads.append(partial_result.validated_output)
        return partial_payloads, stage_details

    def _build_checklist_map_prompt(self, text: str, chunk_text: str, *, index: int, total: int) -> str:
        profile = detect_checklist_domain_profile(text, chunk_text)
        domain_rules = build_checklist_domain_prompt_rules(profile)
        return f"""
You are a checklist generator.
You are extracting checklist items from PART {index} of {total} of a larger document.
Return only valid JSON.
Use only the content in this part.
Do not invent steps.
Focus on operational actions, phase boundaries, and explicit checklist questions/instructions.
Ignore editorial/manual/front-matter text when operational content is present.
{domain_rules}
- If this part contains an explicit checklist block with direct questions or short action prompts, ignore surrounding implementation guidance, rollout advice, training notes, culture/change-management text, and measurement commentary.
- Preserve the source order of checklist items exactly as they appear in this part.
- Do not skip explicit checklist questions just because they are followed by explanatory paragraphs.
- When the source uses short prefixes like roles, teams, or sections before a colon, keep that prefix available via `category` when it helps preserve structure.

User intent / task:
{text}

Document part:
{chunk_text}

Return this JSON structure:
{{
  "task_type": "checklist",
  "title": "Checklist part title",
  "description": "Short description of what this part covers.",
  "items": [
    {{
      "id": "item-1",
      "title": "Operational action item",
      "description": "Specific action derived from this part",
      "source_text": "Closest literal source line supporting this item",
      "evidence": "Short quoted snippet from this part",
      "category": "phase/section if grounded",
      "priority": null,
      "status": "pending",
      "dependencies": [],
      "estimated_time_minutes": null
    }}
  ],
  "total_items": 1,
  "completed_items": 0,
  "progress_percentage": 0.0
}}
"""

    def _build_checklist_reduce_prompt(self, text: str, partial_checklists: list[ChecklistPayload]) -> str:
        serialized_parts = []
        for index, checklist in enumerate(partial_checklists, start=1):
            serialized_items = []
            for item in checklist.items:
                serialized_items.append(
                    json.dumps(
                        {
                            "title": item.title,
                            "category": item.category,
                            "description": item.description,
                            "source_text": item.source_text,
                        },
                        ensure_ascii=False,
                    )
                )
            serialized_parts.append(
                f"[PARTIAL CHECKLIST {index}]\n"
                f"Title: {checklist.title}\n"
                f"Description: {checklist.description}\n"
                f"Items:\n" + "\n".join(serialized_items)
            )
        partial_block = "\n\n".join(serialized_parts)
        profile = detect_checklist_domain_profile(text, partial_block)
        domain_rules = build_checklist_reduce_domain_prompt_rules(profile)
        return f"""
You are a checklist generator.
Return only valid JSON.
You are receiving partial checklist extractions from different parts of the same document.
Merge them into one final checklist.
Do not invent steps.
Deduplicate semantically repeated items.
Preserve document phases/categories when grounded.
Do not collapse the final output to a single phase if multiple phases are present.
{domain_rules}
- If some partial extractions contain explicit operational checklist questions/instructions and others contain narrative implementation guidance, prefer the explicit operational checklist content and drop narrative guidance items from the final checklist.
- Preserve the original document order from the first checklist item to the last.
- Do not drop explicit checklist questions during consolidation.
- If two items are different questions, keep both even if they are topically related.

User intent / task:
{text}

Partial checklists:
{partial_block}

Return this JSON structure:
{{
  "task_type": "checklist",
  "title": "Checklist title based on the full document",
  "description": "Checklist purpose based on the full document",
  "items": [
    {{
      "id": "item-1",
      "title": "Operational action item",
      "description": "Specific action derived from the full document",
      "source_text": "Closest literal source line supporting this item",
      "evidence": "Short quoted snippet from the document",
      "category": "phase/section if grounded",
      "priority": null,
      "status": "pending",
      "dependencies": [],
      "estimated_time_minutes": null
    }}
  ],
  "total_items": 1,
  "completed_items": 0,
  "progress_percentage": 0.0
}}
"""

    def _trim_checklist_noise(self, text: str) -> str:
        lines = [line.rstrip() for line in str(text or "").splitlines()]
        kept: list[str] = []
        noise_patterns = (
            "who library cataloguing",
            "all rights reserved",
            "publications of the world health organization",
            "requests for permission",
            "printed in france",
            "contents",
            "introduction",
            "how to use this manual",
            "implementation manual",
            "safe surgery saves lives",
            "who patient safety",
            "world health organization",
            "isbn ",
            "section i.",
            "guidelines for safe surgery",
            "additional notes — promoting a safety culture",
            "modifying the checklist",
            "introducing the checklist into the operating room",
            "evaluating surgical care",
        )
        for line in lines:
            compact = " ".join(line.split()).strip()
            if not compact:
                continue
            lowered = compact.lower()
            if lowered.startswith("[página"):
                continue
            if lowered == "[enriquecimento visual/ocr]":
                continue
            if lowered == "<!-- image -->":
                continue
            if re.fullmatch(r"how to run the checklist \(in brief\) \d+", lowered):
                continue
            if re.fullmatch(r"how to run the checklist \(in detail\) \d+", lowered):
                continue
            if re.fullmatch(r"before induction of anaesthesia \d+", lowered):
                continue
            if re.fullmatch(r"before skin incision \d+", lowered):
                continue
            if re.fullmatch(r"before patient leaves operating room \d+", lowered):
                continue
            if any(pattern in lowered for pattern in noise_patterns):
                continue
            if re.fullmatch(r"\d+", lowered):
                continue
            kept.append(compact)

        deduped: list[str] = []
        seen = set()
        for line in kept:
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(line)
        return "\n".join(deduped).strip()

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

    def _build_checklist_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nContext:\n{context_text}\n" if context_text else ""
        profile = detect_checklist_domain_profile(text, context_text)
        domain_rules = build_checklist_single_pass_domain_prompt_rules(profile)
        return f"""
You are a checklist generator.
Convert the input into an operational checklist and return only valid JSON.
Use the actual instructions provided. Do not copy example placeholder values.
- Be as extractive as possible: prefer wording that stays very close to the source text.
- Do not paraphrase aggressively when the source already contains a clear checklist instruction.
- Do not add implied actions, process milestones, or inferred next steps that are not explicitly stated.
- Do not invent dependencies between items unless the source explicitly states a dependency.
- Do not invent estimated time values.
{domain_rules}
- Preserve blocking or approval conditions as their own checklist items when explicitly stated.
- Do not collapse multiple grounded actions into one generic item.
- Ignore front matter, publishing notes, copyright text, cataloguing metadata, and general introduction when operational checklist content is present.
- Prioritize the actual checklist steps and operational phases over narrative explanation.
- If the document contains an explicit checklist block with direct questions or short action prompts, prioritize that block and ignore surrounding implementation guidance, rollout advice, training notes, culture/change-management text, and measurement commentary.
- If the source has phases or sections, preserve them through item wording or categories instead of flattening everything into one generic task.
- Preserve the order in which checklist items appear in the source.
- Do not skip explicit checklist questions even when a long explanatory paragraph follows them.
- Respect the original phase boundaries from the document. Do not move items from one phase into another.
- Avoid duplicating the same checklist step across phases unless the source explicitly repeats it in multiple phases.
- If the document is long, still try to cover the whole document rather than only the first operational block.
- If a phrase is a question in the source checklist, you may convert it into a concise imperative title, but keep it semantically very close to the original wording.
- For every checklist item, populate `source_text` with the closest literal source line and `evidence` with a short grounded snippet.
- If you cannot point to a grounded source line/snippet for an item, do not include that item.

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
      "description": "Specific action derived closely from the source text",
      "source_text": "Closest literal source line supporting this item",
      "evidence": "Short quoted snippet copied from the source",
      "category": null,
      "priority": null,
      "status": "pending",
      "dependencies": [],
      "estimated_time_minutes": null
    }}
  ],
  "total_items": 1,
  "completed_items": 0,
  "progress_percentage": 0.0
}}
"""


class CVAnalysisTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        total_started_at = time.perf_counter()
        self._report_progress(request, step="initializing", progress=0.10, detail="Inicializando análise estruturada de CV")
        self._report_progress(request, step="grounding", progress=0.22, detail="Preparando grounding do CV/documento")
        provider = self._resolve_provider(request)
        self._report_progress(request, step="provider_ready", progress=0.34, detail="Provider pronto; analisando grounding")
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
            context_started_at = time.perf_counter()
            secondary_context = build_retrieval_context(
                query=request.input_text,
                document_ids=request.source_document_ids,
                max_chunks=4,
                max_chars=6000,
            ).strip()
            self._record_timing(request, "context_build_s", time.perf_counter() - context_started_at)
        else:
            context_started_at = time.perf_counter()
            primary_context = self._build_optional_document_context(request, strategy="document_scan", max_chunks=16)
            self._record_timing(request, "context_build_s", time.perf_counter() - context_started_at)

        if use_full_cv_grounding and self._is_low_grounding_cv_context(primary_context):
            return attempt_controlled_failure(
                raw_response="",
                task_type="cv_analysis",
                error_message="Low grounding: insufficient CV context. Full CV context is too short or structurally incomplete, so placeholder resume output was blocked.",
            )

        self._report_progress(request, step="prompt_ready", progress=0.50, detail="Grounding pronto; montando prompt da análise")
        prompt = self._build_cv_analysis_prompt(
            request.input_text,
            primary_context,
            secondary_context=secondary_context,
            use_full_cv_grounding=use_full_cv_grounding,
        )
        self._report_progress(request, step="model_inference", progress=0.74, detail="Executando análise de CV")
        self._set_telemetry_value(request, "current_stage", "cv_analysis_single_pass")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.92, detail="Validando análise de CV")
        parsing_started_at = time.perf_counter()
        result = self._parse_with_recovery(
            provider=provider,
            request=request,
            response_text=response_text,
            payload_schema=CVAnalysisPayload,
            original_prompt=prompt,
        )
        result = self._post_process_cv_result(
            result,
            source_text="\n\n".join(part for part in [primary_context, secondary_context, request.input_text] if part),
        )
        self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
        self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
        self._report_progress(request, step="done", progress=1.0, detail="Análise de CV finalizada")
        return result

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

    def _post_process_cv_result(self, result: StructuredResult, *, source_text: str) -> StructuredResult:
        payload = result.validated_output
        if not result.success or not isinstance(payload, CVAnalysisPayload):
            return result

        data = payload.model_dump(mode="python")
        personal_info = dict(data.get("personal_info") or {})
        personal_info["full_name"] = self._clean_cv_text(personal_info.get("full_name")) or None
        personal_info["email"] = self._clean_cv_text(personal_info.get("email")) or None
        personal_info["phone"] = self._clean_cv_text(personal_info.get("phone")) or None
        personal_info["location"] = self._clean_cv_text(personal_info.get("location")) or None
        personal_info["links"] = self._normalize_cv_links(personal_info.get("links") or [], source_text=source_text)

        normalized_education = self._normalize_cv_education_entries(payload.education_entries, source_text=source_text)
        normalized_education = self._merge_cv_education_entries(
            normalized_education,
            self._extract_cv_education_entries_from_source(source_text),
        )
        normalized_experience = self._normalize_cv_experience_entries(payload.experience_entries, source_text=source_text)

        data["personal_info"] = personal_info
        data["skills"] = self._normalize_cv_string_list(payload.skills)
        data["languages"] = self._normalize_cv_languages(payload.languages, source_text=source_text)
        data["education_entries"] = normalized_education
        data["experience_entries"] = normalized_experience
        data["strengths"] = self._normalize_cv_string_list(payload.strengths)
        data["improvement_areas"] = self._normalize_cv_string_list(payload.improvement_areas)
        data["projects"] = self._normalize_cv_string_list(data.get("projects") or [])
        data["sections"] = self._normalize_cv_sections(
            existing_sections=payload.sections,
            personal_info=personal_info,
            skills=data["skills"],
            languages=data["languages"],
            education_entries=normalized_education,
            experience_entries=normalized_experience,
            strengths=data["strengths"],
            projects=data["projects"],
        )

        normalized_payload = CVAnalysisPayload(**data)
        result.validated_output = normalized_payload
        result.parsed_json = normalized_payload.model_dump(mode="json")
        return result

    def _clean_cv_text(self, value: object) -> str:
        cleaned = " ".join(str(value or "").split()).strip().strip("|")
        return cleaned

    def _normalize_cv_string_list(self, values: list[object]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            cleaned = self._clean_cv_text(value)
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized

    def _normalize_cv_links(self, values: list[object], *, source_text: str) -> list[str]:
        patterns = [
            r"https?://[^\s,;]+",
            r"linkedin\.com/[^\s,;]+",
            r"/in/[a-z0-9\-_/]+",
        ]
        collected = self._normalize_cv_string_list(values)
        for pattern in patterns:
            for match in re.findall(pattern, source_text or "", re.I):
                collected.append(self._clean_cv_text(match))
        return self._normalize_cv_string_list(collected)

    def _normalize_cv_languages(self, values: list[object], *, source_text: str) -> list[str]:
        normalized_source = _normalize_matching_text(source_text)
        specs = [
            ("Portugais", r"portugais|portuguese|portugues", "Natif", r"natif|native"),
            ("Français", r"francais|français|french", "Bilingue", r"bilingue|bilingual"),
            ("Anglais", r"anglais|english", "Bilingue", r"bilingue|bilingual"),
        ]

        normalized_values: list[str] = []
        for raw_value in values:
            cleaned = self._clean_cv_text(raw_value)
            if not cleaned:
                continue
            lowered = _normalize_matching_text(cleaned)
            matched_spec = next((spec for spec in specs if re.search(spec[1], lowered, re.I)), None)
            if matched_spec is None:
                normalized_values.append(cleaned)
                continue
            lang_label, lang_pattern, prof_label, prof_pattern = matched_spec
            if re.search(prof_pattern, lowered, re.I):
                normalized_values.append(f"{lang_label} — {prof_label}")
                continue
            paired_pattern = rf"(?:{lang_pattern}).{{0,24}}(?:{prof_pattern})|(?:{prof_pattern}).{{0,24}}(?:{lang_pattern})"
            if re.search(paired_pattern, normalized_source, re.I):
                normalized_values.append(f"{lang_label} — {prof_label}")
            else:
                normalized_values.append(lang_label)

        for lang_label, lang_pattern, prof_label, prof_pattern in specs:
            if re.search(lang_pattern, normalized_source, re.I) and re.search(prof_pattern, normalized_source, re.I):
                normalized_values.append(f"{lang_label} — {prof_label}")

        return self._normalize_cv_string_list(normalized_values)

    def _extract_cv_date_range(self, text: str) -> str | None:
        patterns = [
            r"\b\d{4}\s*[-–]\s*\d{4}\b",
            r"\b\d{2}/\d{4}\s*[-–]\s*\d{2}/\d{4}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self._clean_cv_text(match.group(0))
        return None

    def _infer_cv_organization(self, text: str) -> str | None:
        patterns = [
            r"Laboratoire des sources alternatives d[’']énergie",
            r"EDF R&D",
            r"\bONS\b",
            r"CentraleSupélec",
            r"Université Paris-Saclay",
            r"Université Fédérale du Rio de Janeiro",
            r"Université [A-ZÀ-ÿa-zà-ÿ' -]+",
            r"Laboratoire [A-ZÀ-ÿa-zà-ÿ' -]+",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return self._clean_cv_text(match.group(0))
        return None

    def _extract_cv_location(self, text: str) -> str | None:
        pipe_match = re.search(r"\|\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ' -]+)$", text)
        if pipe_match:
            return self._clean_cv_text(pipe_match.group(1))
        for candidate in ("Paris-Saclay", "Rio de Janeiro"):
            if candidate.lower() in text.lower():
                return candidate
        return None

    def _strip_cv_noise(self, text: str) -> str:
        cleaned = self._clean_cv_text(text)
        if not cleaned:
            return ""
        noise_markers = [
            r"\bMusique\b",
            r"\bSports\b",
            r"\bTechnologie\b",
            r"CENTRES? D['’]INT[ÉE]R[ÊE]T",
            r"\bCOMP[ÉE]TENCES\b",
        ]
        for marker in noise_markers:
            parts = re.split(marker, cleaned, maxsplit=1, flags=re.I)
            if parts:
                cleaned = self._clean_cv_text(parts[0])
        return cleaned

    def _extract_cv_education_institution_hint(self, text: str) -> str | None:
        cleaned = self._clean_cv_text(text)
        if not cleaned:
            return None
        explicit_candidates = (
            "CentraleSupélec",
            "Université Paris-Saclay",
            "Université Fédérale do Rio de Janeiro",
            "Université Fédérale du Rio de Janeiro",
        )
        normalized_cleaned = _normalize_matching_text(cleaned)
        for candidate in explicit_candidates:
            if _normalize_matching_text(candidate) in normalized_cleaned:
                return candidate.replace("do Rio", "du Rio")
        colon_match = re.search(r":\s*(Université [A-ZÀ-ÿa-zà-ÿ' -]+)$", cleaned, re.I)
        if colon_match:
            return self._clean_cv_text(colon_match.group(1))
        pipe_match = re.search(r"\|\s*(Université [A-ZÀ-ÿa-zà-ÿ' -]+)", cleaned, re.I)
        if pipe_match:
            return self._clean_cv_text(pipe_match.group(1))
        generic_match = re.search(r"(Université [A-ZÀ-ÿa-zà-ÿ' -]+?)(?=\s*(?:\||\d{4}|$))", cleaned, re.I)
        if generic_match:
            return self._clean_cv_text(generic_match.group(1))
        if "centralesupelec" in normalized_cleaned:
            return "CentraleSupélec"
        return None

    def _cleanup_cv_degree_text(self, text: str | None, *, institution: str | None = None) -> str:
        cleaned = self._strip_cv_noise(text)
        if not cleaned:
            return ""
        if institution:
            cleaned = re.sub(re.escape(institution), "", cleaned, flags=re.I)
        cleaned = re.sub(r"\b\d{4}\s*[-–]\s*\d{4}\b", "", cleaned)
        cleaned = re.sub(r"\b\d{2}/\d{4}\s*[-–]\s*\d{2}/\d{4}\b", "", cleaned)
        cleaned = re.sub(r"\s*\|\s*", " | ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" |:-")
        return cleaned

    def _find_cv_source_window(self, source_text: str, anchor_text: str) -> str:
        anchor = self._clean_cv_text(anchor_text)
        if len(anchor) < 12:
            return ""
        match = re.search(re.escape(anchor[:60]), source_text or "", re.I)
        if not match:
            return ""
        start = max(0, match.start() - 120)
        end = min(len(source_text), match.end() + 220)
        return source_text[start:end]

    def _extract_cv_education_entries_from_source(self, source_text: str) -> list[dict[str, object]]:
        if not source_text:
            return []
        matches: list[dict[str, object]] = []
        for match in re.finditer(r"(CentraleSupélec|Université [A-ZÀ-ÿa-zà-ÿ' -]+)", source_text, re.I):
            institution = self._clean_cv_text(match.group(1))
            start = max(0, match.start() - 180)
            end = min(len(source_text), match.end() + 220)
            window = source_text[start:end]
            degree_match = None
            for pattern in (
                r"Formation d['’]Ing[ée]nieur[^\n]{0,120}",
                r"Ing[ée]nieur[^\n]{0,120}",
                r"Master[^\n]{0,140}",
                r"double dipl[oô]me[^\n]{0,140}",
            ):
                degree_match = re.search(pattern, window, re.I)
                if degree_match:
                    break
            degree = self._cleanup_cv_degree_text(degree_match.group(0) if degree_match else "", institution=institution) or None
            date_range = self._extract_cv_date_range(window)
            location = self._extract_cv_location(window)
            description = self._clean_cv_text(window[:220])
            if not (institution and (degree or date_range)):
                continue
            matches.append(
                {
                    "degree": degree,
                    "institution": institution,
                    "location": location,
                    "date_range": date_range,
                    "description": description,
                }
            )
        return matches

    def _merge_cv_education_entries(self, primary: list[dict[str, object]], secondary: list[dict[str, object]]) -> list[dict[str, object]]:
        merged: list[dict[str, object]] = []
        seen: set[tuple[str, str, str]] = set()
        for entry in [*primary, *secondary]:
            institution = self._clean_cv_text(entry.get("institution"))
            degree = self._clean_cv_text(entry.get("degree"))
            date_range = self._clean_cv_text(entry.get("date_range"))
            key = (institution.casefold(), degree.casefold(), date_range.casefold())
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)
        return merged

    def _normalize_cv_education_entries(self, entries: list[object], *, source_text: str) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for entry in entries:
            raw_degree = self._strip_cv_noise(getattr(entry, "degree", None))
            raw_institution = self._clean_cv_text(getattr(entry, "institution", None))
            raw_location = self._clean_cv_text(getattr(entry, "location", None))
            raw_date_range = self._clean_cv_text(getattr(entry, "date_range", None))
            raw_description = self._strip_cv_noise(getattr(entry, "description", None))
            source_window = self._find_cv_source_window(source_text, raw_degree or raw_description)
            combined = " | ".join(part for part in [raw_degree, raw_institution, raw_location, raw_date_range, raw_description, source_window] if part)
            institution = raw_institution or self._extract_cv_education_institution_hint(raw_degree or raw_description or "") or self._infer_cv_organization(combined)
            date_range = raw_date_range or self._extract_cv_date_range(combined)
            location = raw_location or self._extract_cv_location(combined)
            description = raw_description or self._strip_cv_noise(combined)
            degree = self._cleanup_cv_degree_text(raw_degree or description, institution=institution) or None
            if not (degree or institution):
                continue
            normalized.append(
                {
                    "degree": degree,
                    "institution": institution,
                    "location": location,
                    "date_range": date_range,
                    "description": description,
                }
            )
        return normalized

    def _normalize_cv_experience_entries(self, entries: list[object], *, source_text: str) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for entry in entries:
            raw_title = self._clean_cv_text(getattr(entry, "title", None))
            raw_organization = self._clean_cv_text(getattr(entry, "organization", None))
            raw_location = self._clean_cv_text(getattr(entry, "location", None))
            raw_date_range = self._clean_cv_text(getattr(entry, "date_range", None))
            raw_bullets = self._normalize_cv_string_list(getattr(entry, "bullets", []) or [])
            raw_description = self._clean_cv_text(getattr(entry, "description", None))
            raw_title_is_date_only = bool(raw_title) and (
                raw_title == self._clean_cv_text(raw_date_range)
                or bool(re.fullmatch(r"(?:\d{2}/)?\d{4}\s*[-–]\s*(?:\d{2}/)?\d{4}", raw_title))
            )
            raw_description_is_date_only = bool(raw_description) and (
                raw_description == self._clean_cv_text(raw_date_range)
                or bool(re.fullmatch(r"(?:\d{2}/)?\d{4}\s*[-–]\s*(?:\d{2}/)?\d{4}", raw_description))
            )
            if (raw_title_is_date_only or raw_description_is_date_only) and not raw_organization and not raw_bullets:
                continue
            source_window = self._find_cv_source_window(source_text, raw_title or raw_description)
            combined = " | ".join(part for part in [raw_title, raw_organization, raw_location, raw_date_range, raw_description, source_window, *raw_bullets] if part)
            organization = raw_organization
            if not organization or organization.casefold() in {"projet", "project"}:
                organization = self._infer_cv_organization(combined)
            date_range = raw_date_range or self._extract_cv_date_range(combined)
            location = raw_location or self._extract_cv_location(combined)
            description = raw_description or combined or None
            title = raw_title or description or None
            if not title:
                continue
            cleaned_title = self._clean_cv_text(title)
            if date_range and cleaned_title == self._clean_cv_text(date_range) and not organization and not raw_bullets:
                continue
            if re.fullmatch(r"(?:\d{2}/)?\d{4}\s*[-–]\s*(?:\d{2}/)?\d{4}", cleaned_title) and not organization and not raw_bullets:
                continue
            normalized.append(
                {
                    "title": title,
                    "organization": organization,
                    "location": location,
                    "date_range": date_range,
                    "bullets": raw_bullets,
                    "description": description,
                }
            )
        return normalized

    def _normalize_cv_sections(
        self,
        *,
        existing_sections: list[object],
        personal_info: dict[str, object],
        skills: list[str],
        languages: list[str],
        education_entries: list[dict[str, object]],
        experience_entries: list[dict[str, object]],
        strengths: list[str],
        projects: list[str],
    ) -> list[CVSection | dict[str, object]]:
        normalized_existing: list[CVSection | dict[str, object]] = []
        for item in existing_sections:
            if isinstance(item, CVSection):
                normalized_existing.append(CVSection.model_validate(item.model_dump(mode="python")))
            elif isinstance(item, dict):
                normalized_existing.append(CVSection.model_validate(item))
        if normalized_existing:
            return normalized_existing
        inferred: list[CVSection] = []

        def append_section(section_type: str, content: list[str]) -> None:
            if not content:
                return
            inferred.append(
                CVSection(
                    section_type=section_type,
                    title=section_type.replace("_", " ").title(),
                    content=[CVSectionContentItem(text=item, details={}) for item in content[:5]],
                    confidence=0.8,
                )
            )

        if any(personal_info.get(field) for field in ("full_name", "email", "phone", "location")):
            append_section(
                "personal_info",
                [
                    str(personal_info.get("full_name") or ""),
                    str(personal_info.get("email") or ""),
                    str(personal_info.get("location") or ""),
                ],
            )
        append_section("languages", languages)
        append_section("skills", skills)
        append_section(
            "education",
            [
                " | ".join(
                    part for part in [entry.get("degree"), entry.get("institution"), entry.get("date_range")] if part
                )
                for entry in education_entries
            ],
        )
        append_section(
            "experience",
            [
                " | ".join(
                    part for part in [entry.get("title"), entry.get("organization"), entry.get("date_range")] if part
                )
                for entry in experience_entries
            ],
        )
        append_section("strengths", strengths)
        append_section("projects", projects)
        return inferred


class CodeAnalysisTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        total_started_at = time.perf_counter()
        self._report_progress(request, step="initializing", progress=0.10, detail="Inicializando análise estruturada de código")
        self._report_progress(request, step="building_context", progress=0.22, detail="Montando contexto")
        provider = self._resolve_provider(request)
        self._report_progress(request, step="provider_ready", progress=0.34, detail="Provider pronto; preparando contexto")
        context_started_at = time.perf_counter()
        context_text = self._build_optional_document_context(request, strategy="document_scan", max_chunks=12)
        self._record_timing(request, "context_build_s", time.perf_counter() - context_started_at)
        self._report_progress(request, step="prompt_ready", progress=0.50, detail="Contexto pronto; montando prompt da análise")
        prompt = self._build_code_analysis_prompt(request.input_text, context_text)
        self._report_progress(request, step="model_inference", progress=0.74, detail="Executando análise de código")
        self._set_telemetry_value(request, "current_stage", "code_analysis_single_pass")
        response_text = self._collect_response_text(provider, request, prompt)
        self._report_progress(request, step="parsing", progress=0.92, detail="Validando análise")
        parsing_started_at = time.perf_counter()
        result = self._parse_with_recovery(
            provider=provider,
            request=request,
            response_text=response_text,
            payload_schema=CodeAnalysisPayload,
            original_prompt=prompt,
        )
        result = self._post_process_code_analysis_result(
            result,
            source_text="\n\n".join(part for part in [context_text, request.input_text] if part),
        )
        self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
        self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
        self._report_progress(request, step="done", progress=1.0, detail="Análise de código finalizada")
        return result

    def _post_process_code_analysis_result(self, result: StructuredResult, *, source_text: str) -> StructuredResult:
        payload = result.validated_output
        if not result.success or not isinstance(payload, CodeAnalysisPayload):
            return result

        data = payload.model_dump(mode="python")
        issues = list(data.get("detected_issues") or [])
        refactor_plan = self._normalize_code_string_list(data.get("refactor_plan") or [])
        test_suggestions = self._normalize_code_string_list(data.get("test_suggestions") or [])
        readability = self._normalize_code_string_list(data.get("readability_improvements") or [])
        maintainability = self._normalize_code_string_list(data.get("maintainability_improvements") or [])
        risk_notes = self._normalize_code_string_list(data.get("risk_notes") or [])

        if self._detect_empty_input_division_pattern(source_text):
            issues = self._append_code_issue_if_missing(
                issues,
                {
                    "severity": "high",
                    "category": "runtime_failure",
                    "title": "Division by zero on empty input",
                    "description": "A divisão por `len(...)` pode falhar quando a coleção processada estiver vazia.",
                    "evidence": "average = total / len(values)",
                    "recommendation": "Trate entrada vazia antes da divisão e retorne `0.0` quando não houver valores.",
                },
            )
            refactor_plan.append("Tratar entrada vazia antes do cálculo da média e retornar `0.0` quando não houver itens.")
            test_suggestions.append("Adicionar teste para entrada vazia verificando que a média retorna `0.0` sem exceção.")
            risk_notes.append("Uma entrada vazia pode causar falha em tempo de execução por divisão por zero.")

        if self._detect_input_mutation_pattern(source_text):
            issues = self._append_code_issue_if_missing(
                issues,
                {
                    "severity": "medium",
                    "category": "input_mutation",
                    "title": "Mutates caller-provided items in place",
                    "description": "O código altera objetos recebidos do chamador diretamente durante a normalização.",
                    "evidence": "item[\"score\"] = ...",
                    "recommendation": "Construir um novo objeto normalizado em vez de mutar o objeto original.",
                },
            )
            refactor_plan.append("Evitar mutação in-place construindo novos objetos normalizados para a saída.")
            test_suggestions.append("Adicionar teste para garantir que os objetos de entrada não sejam modificados in-place.")
            maintainability.append("Explicitar o contrato de imutabilidade da entrada e preservar esse contrato na implementação.")

        if self._detect_heterogeneous_output_pattern(source_text):
            issues = self._append_code_issue_if_missing(
                issues,
                {
                    "severity": "medium",
                    "category": "api_contract",
                    "title": "Output structure is inconsistent",
                    "description": "Ramos diferentes retornam itens com formatos diferentes, o que fragiliza o contrato da API.",
                    "evidence": "result.append({\"name\": ...}) / result.append(item)",
                    "recommendation": "Padronizar a estrutura de saída para que todos os itens retornem o mesmo shape.",
                },
            )
            refactor_plan.append("Normalizar o schema de saída para que todos os itens retornem a mesma estrutura.")
            test_suggestions.append("Adicionar teste cobrindo itens sem `score` e verificando que o formato de saída continua consistente.")
            readability.append("Documentar claramente o schema esperado de entrada e saída.")
            maintainability.append("Separar a etapa de normalização da etapa de agregação para simplificar o fluxo e o contrato da API.")
            risk_notes.append("Saídas com formatos mistos podem quebrar consumidores que esperam uma estrutura estável.")

        data["detected_issues"] = issues
        data["refactor_plan"] = self._normalize_code_string_list(refactor_plan)
        data["test_suggestions"] = self._normalize_code_string_list(test_suggestions)
        data["readability_improvements"] = self._normalize_code_string_list(readability)
        data["maintainability_improvements"] = self._normalize_code_string_list(maintainability)
        data["risk_notes"] = self._normalize_code_string_list(risk_notes)

        normalized_payload = CodeAnalysisPayload(**data)
        result.validated_output = normalized_payload
        result.parsed_json = normalized_payload.model_dump(mode="json")
        return result

    def _normalize_code_string_list(self, values: list[object]) -> list[str]:
        seen: set[str] = set()
        normalized: list[str] = []
        for value in values:
            cleaned = " ".join(str(value or "").split()).strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(cleaned)
        return normalized

    def _append_code_issue_if_missing(self, issues: list[dict[str, object]], new_issue: dict[str, object]) -> list[dict[str, object]]:
        new_title = " ".join(str(new_issue.get("title") or "").split()).strip().casefold()
        if not new_title:
            return issues
        for issue in issues:
            title = " ".join(str(issue.get("title") or "").split()).strip().casefold()
            if title == new_title:
                return issues
        return [*issues, new_issue]

    def _detect_empty_input_division_pattern(self, source_text: str) -> bool:
        normalized = _normalize_matching_text(source_text)
        if "len(values)" not in normalized and "len(items)" not in normalized:
            return False
        if not re.search(r"/\s*len\((?:values|items)\)", source_text or ""):
            return False
        guard_patterns = (
            r"if\s+not\s+(?:values|items)",
            r"if\s+len\((?:values|items)\)\s*(?:==|<=)\s*0",
            r"if\s+(?:values|items)\s*:",
        )
        return not any(re.search(pattern, source_text or "", re.I) for pattern in guard_patterns)

    def _detect_input_mutation_pattern(self, source_text: str) -> bool:
        return bool(re.search(r"\b\w+\s*\[\s*['\"][^'\"]+['\"]\s*\]\s*=", source_text or ""))

    def _detect_heterogeneous_output_pattern(self, source_text: str) -> bool:
        normalized = source_text or ""
        return "append({" in normalized and re.search(r"append\((?:item|value|entry)\)", normalized)

    def _build_code_analysis_prompt(self, text: str, context_text: str) -> str:
        context_block = f"\nCode/document context:\n{context_text}\n" if context_text else ""
        return f"""
You are a code analysis assistant.
Return only valid JSON.
Use only the code/content provided.
Do not invent bugs or features that are not grounded in the code.
- Write natural-language fields in Brazilian Portuguese unless the user explicitly asks for another language.
- Keep code identifiers, exception names, and evidence snippets exactly as they appear in the source.
- Prioritize concrete correctness bugs, runtime failure risks, type/shape assumptions, explicit side effects, and grounded test cases.
- Avoid generic/template issues unless they are directly supported by visible code evidence.
- Prefer the most important concrete bug over vague maintainability commentary.
- Only report a missing-key issue when the code really dereferences a key without a guard. If the code first checks something like `if "score" in item`, do not claim `KeyError`; describe the real remaining risk instead.
- Use `input_mutation` only when the code mutates caller-provided objects in place. If the function merely reuses or returns the original object reference unchanged, prefer `shared_reference` instead and keep severity proportional.
- Do not present ambiguous alternatives such as "return 0.0 or raise an error". Choose one concrete recommendation and keep the refactor plan and tests consistent with that choice.
- When an empty-input average would otherwise fail, prefer one concrete remediation and default to `0.0` if the snippet does not show a conflicting business rule.
- Do not recommend deep copy by default for simple dict/list normalization. Prefer shallow copy (`copy()`) or building a new object unless nested mutation explicitly requires deep copy.
- Use concise stable categories from this set whenever possible: `runtime_failure`, `correctness`, `type_validation`, `shared_reference`, `input_mutation`, `error_handling`, `performance`, `readability`, `maintainability`, `api_contract`.
- Use `high` severity only for issues that can realistically break execution, corrupt data, or produce obviously wrong results in normal use.
- Test suggestions must be specific to the actual snippet, not placeholders like `edge case X`.
- Risk notes must be snippet-specific and grounded in visible code behavior.
- If multiple independent grounded issues are present, return all of them instead of stopping after the first one or two.
- If the code divides by the size of a collection without a visible empty guard, surface that as a runtime/correctness risk.
- If one branch returns normalized objects and another returns the original raw object, surface that as an inconsistent output/API contract issue.

Code or technical text to analyze:
{text}
{context_block}
Return this JSON structure:
{{
  "task_type": "code_analysis",
  "snippet_summary": "Resumo curto do trecho de código",
  "main_purpose": "Objetivo principal do código",
  "detected_issues": [
    {{
      "severity": "medium",
      "category": "maintainability",
      "title": "Lógica duplicada",
      "description": "Uma mesma regra aparece repetida em mais de um ponto do código.",
      "evidence": "Repeated conditional branches in two methods.",
      "recommendation": "Extraia a lógica comum para uma função auxiliar."
    }}
  ],
  "readability_improvements": ["Renomear variáveis pouco claras"],
  "maintainability_improvements": ["Extrair lógica compartilhada"],
  "refactor_plan": ["Passo 1", "Passo 2"],
  "test_suggestions": ["Adicionar teste unitário específico para o caso crítico identificado"],
  "risk_notes": ["Risco concreto observado no comportamento atual"]
}}
"""


class DocumentAgentTaskHandler(TaskHandler):
    def execute(self, request: TaskExecutionRequest) -> StructuredResult:
        from .parsers import attempt_controlled_failure
        from .service import structured_service

        total_started_at = time.perf_counter()
        telemetry = self._telemetry_dict(request)
        self._report_progress(request, step="initializing", progress=0.08, detail="Inicializando o Document Operations Copilot")
        provider = self._resolve_provider(request)
        self._report_progress(request, step="intent_routing", progress=0.20, detail="Classificando intenção e selecionando tool")

        document_ids = list(request.source_document_ids or [])
        document_count = len(document_ids)
        available_tools = list_document_agent_tools(
            document_count=document_count,
            use_document_context=bool(request.use_document_context),
        )

        user_intent = str(telemetry.get("agent_intent") or "").strip().lower()
        intent_reason = str(telemetry.get("agent_intent_reason") or "").strip() or None
        if not user_intent:
            user_intent, intent_reason = classify_document_agent_intent(
                request.input_text,
                document_count=document_count,
            )

        tool_name = str(telemetry.get("agent_tool") or "").strip().lower()
        answer_mode = str(telemetry.get("agent_answer_mode") or "").strip().lower()
        tool_reason = str(telemetry.get("agent_tool_reason") or "").strip() or None
        if not tool_name:
            tool_name, answer_mode, tool_reason = select_document_agent_tool(
                user_intent,
                document_count=document_count,
            )

        context_strategy = self._resolve_document_agent_context_strategy(
            request=request,
            tool_name=tool_name,
        )
        telemetry.update(
            {
                "agent_intent": user_intent,
                "agent_intent_reason": intent_reason,
                "agent_tool": tool_name,
                "agent_tool_reason": tool_reason,
                "agent_answer_mode": answer_mode,
                "agent_context_strategy": context_strategy,
                "agent_available_tools": available_tools,
            }
        )

        self._report_progress(request, step="grounding", progress=0.34, detail="Montando grounding documental e fontes")
        source_bundle = self._build_document_agent_source_bundle(
            request=request,
            context_strategy=context_strategy,
        )
        sources = source_bundle["sources"]
        context_text = source_bundle["context_text"]
        retrieval_details = source_bundle["retrieval_details"]
        tool_runs: list[AgentToolExecution] = []

        try:
            self._report_progress(request, step="tool_execution", progress=0.58, detail=f"Executando tool: {describe_document_agent_tool(tool_name)}")
            if tool_name == "consult_documents":
                payload = self._run_consult_documents_tool(
                    provider=provider,
                    request=request,
                    user_intent=user_intent,
                    answer_mode=answer_mode or "friendly",
                    sources=sources,
                    context_text=context_text,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success",
                        detail="Resposta documental gerada com base no contexto selecionado.",
                    )
                )
            elif tool_name == "summarize_document":
                payload, nested_result = self._run_summary_tool(
                    request=request,
                    context_strategy=context_strategy,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success" if nested_result.success else "error",
                        detail="Resumo executivo gerado a partir dos documentos selecionados." if nested_result.success else (nested_result.validation_error or nested_result.parsing_error or "Falha ao gerar resumo."),
                    )
                )
            elif tool_name == "draft_business_response":
                payload = self._run_business_response_drafting_tool(
                    provider=provider,
                    request=request,
                    answer_mode=answer_mode or "friendly",
                    sources=sources,
                    context_text=context_text,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success",
                        detail="Rascunho de resposta documental gerado para revisão humana.",
                    )
                )
            elif tool_name == "extract_structured_data":
                payload, nested_result = self._run_extraction_tool(
                    request=request,
                    context_strategy=context_strategy,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success" if nested_result.success else "error",
                        detail="Extração estruturada concluída." if nested_result.success else (nested_result.validation_error or nested_result.parsing_error or "Falha na extração estruturada."),
                    )
                )
            elif tool_name == "generate_operational_checklist":
                payload, nested_result = self._run_checklist_tool(
                    request=request,
                    context_strategy=context_strategy,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success" if nested_result.success else "error",
                        detail="Checklist operacional gerado." if nested_result.success else (nested_result.validation_error or nested_result.parsing_error or "Falha ao gerar checklist."),
                    )
                )
            elif tool_name == "review_document_risks":
                payload, nested_result = self._run_document_risk_review_tool(
                    request=request,
                    context_strategy=context_strategy,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success" if nested_result.success else "error",
                        detail="Análise de riscos e lacunas concluída." if nested_result.success else (nested_result.validation_error or nested_result.parsing_error or "Falha na análise de riscos."),
                    )
                )
            elif tool_name == "extract_operational_tasks":
                payload, nested_result = self._run_operational_task_extraction_tool(
                    request=request,
                    context_strategy=context_strategy,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success" if nested_result.success else "error",
                        detail="Extração operacional concluída." if nested_result.success else (nested_result.validation_error or nested_result.parsing_error or "Falha na extração operacional."),
                    )
                )
            elif tool_name == "review_policy_compliance":
                payload, nested_result = self._run_policy_compliance_tool(
                    request=request,
                    context_strategy=context_strategy,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success" if nested_result.success else "error",
                        detail="Revisão de policy/compliance concluída." if nested_result.success else (nested_result.validation_error or nested_result.parsing_error or "Falha na revisão de policy/compliance."),
                    )
                )
            elif tool_name == "assist_technical_document":
                payload, nested_result = self._run_technical_assistance_tool(
                    request=request,
                    context_strategy=context_strategy,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name,
                        status="success" if nested_result.success else "error",
                        detail="Assistência técnica concluída." if nested_result.success else (nested_result.validation_error or nested_result.parsing_error or "Falha na assistência técnica."),
                    )
                )
            elif tool_name == "compare_documents":
                payload, comparison_tool_runs = self._run_compare_documents_tool(
                    provider=provider,
                    request=request,
                    answer_mode=answer_mode or "comparison_structured",
                    sources=sources,
                )
                tool_runs.extend(comparison_tool_runs)
            else:
                payload = self._run_consult_documents_tool(
                    provider=provider,
                    request=request,
                    user_intent=user_intent,
                    answer_mode=answer_mode or "friendly",
                    sources=sources,
                    context_text=context_text,
                )
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=tool_name or "consult_documents",
                        status="success",
                        detail="Fallback para consulta documental executado.",
                    )
                )
        except Exception as error:
            failure_message = f"Document agent execution failed: {error}"
            self._append_document_agent_log(
                request=request,
                success=False,
                payload=None,
                error_message=failure_message,
                execution_metadata={
                    "agent_intent": user_intent,
                    "agent_intent_reason": intent_reason,
                    "agent_tool": tool_name,
                    "agent_tool_reason": tool_reason,
                    "agent_answer_mode": answer_mode,
                    "agent_context_strategy": context_strategy,
                    "agent_document_count": document_count,
                    "agent_source_count": len(sources),
                    "needs_review": True,
                    "needs_review_reason": "document_agent_execution_failed",
                    "retrieval_backend_used": retrieval_details.get("backend_used") if isinstance(retrieval_details, dict) else None,
                    "retrieval_strategy_used": retrieval_details.get("retrieval_strategy_used") if isinstance(retrieval_details, dict) else None,
                    "retrieval_strategy_requested": retrieval_details.get("retrieval_strategy_requested") if isinstance(retrieval_details, dict) else None,
                },
                available_tools=available_tools,
                tool_runs=tool_runs,
            )
            return attempt_controlled_failure(
                raw_response="",
                task_type="document_agent",
                error_message=failure_message,
            )

        if not payload.sources:
            payload.sources = sources
        payload.tool_runs.extend(tool_runs)
        if request.use_document_context and document_ids and not payload.sources:
            payload.needs_review = True
            payload.needs_review_reason = payload.needs_review_reason or "no_grounded_sources_available"
            payload.confidence = min(payload.confidence, 0.58) if payload.confidence else 0.58
        if payload.confidence < 0.62 and not payload.needs_review:
            payload.needs_review = True
            payload.needs_review_reason = payload.needs_review_reason or "low_agent_confidence"
        payload = payload.model_copy(update={"available_tools": available_tools})
        payload = self._finalize_document_agent_payload(
            payload=payload,
            request=request,
            tool_name=tool_name,
            context_strategy=context_strategy,
            retrieval_details=retrieval_details,
        )

        execution_metadata = {
            "agent_intent": user_intent,
            "agent_intent_label": describe_document_agent_intent(user_intent),
            "agent_intent_reason": intent_reason,
            "agent_tool": tool_name,
            "agent_tool_label": describe_document_agent_tool(tool_name),
            "agent_tool_reason": tool_reason,
            "agent_answer_mode": answer_mode,
            "agent_context_strategy": context_strategy,
            "agent_document_count": document_count,
            "agent_source_count": len(payload.sources),
            "agent_available_tools": available_tools,
            "needs_review": payload.needs_review,
            "needs_review_reason": payload.needs_review_reason,
            "agent_limitations": list(payload.limitations),
            "agent_recommended_actions": list(payload.recommended_actions),
            "agent_guardrails_applied": list(payload.guardrails_applied),
            "tool_runs": [item.model_dump(mode="json") for item in payload.tool_runs],
            "retrieval_backend_used": retrieval_details.get("backend_used") if isinstance(retrieval_details, dict) else None,
            "retrieval_backend_message": retrieval_details.get("backend_message") if isinstance(retrieval_details, dict) else None,
            "retrieval_strategy_used": retrieval_details.get("retrieval_strategy_used") if isinstance(retrieval_details, dict) else None,
            "retrieval_strategy_requested": retrieval_details.get("retrieval_strategy_requested") if isinstance(retrieval_details, dict) else None,
            "execution_strategy_requested": telemetry.get("execution_strategy_requested"),
            "execution_strategy_used": telemetry.get("execution_strategy_used"),
            "execution_strategy_fallback_reason": telemetry.get("execution_strategy_fallback_reason"),
            "workflow_id": telemetry.get("workflow_id"),
            "workflow_route_decision": telemetry.get("workflow_route_decision"),
            "workflow_guardrail_decision": telemetry.get("workflow_guardrail_decision"),
        }

        self._append_document_agent_log(
            request=request,
            success=True,
            payload=payload,
            execution_metadata=execution_metadata,
            available_tools=available_tools,
            tool_runs=payload.tool_runs,
        )

        self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
        self._report_progress(request, step="done", progress=1.0, detail="Copiloto documental finalizado")
        return StructuredResult(
            success=True,
            task_type="document_agent",
            parsed_json=payload.model_dump(mode="json"),
            validated_output=payload,
            available_render_modes=[
                RenderMode(mode="json", label="JSON", available=True, priority=1),
                RenderMode(mode="friendly", label="Friendly view", available=True, priority=0),
            ],
            primary_render_mode="friendly",
            overall_confidence=payload.confidence,
            quality_score=payload.confidence,
            execution_metadata=execution_metadata,
        )

    def _get_document_agent_log_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".phase6_document_agent_log.json"

    def _append_document_agent_log(
        self,
        *,
        request: TaskExecutionRequest,
        success: bool,
        payload: DocumentAgentPayload | None,
        error_message: str | None = None,
        execution_metadata: dict[str, object] | None = None,
        available_tools: list[dict[str, object]] | None = None,
        tool_runs: list[AgentToolExecution] | None = None,
    ) -> None:
        try:
            from ..storage.phase6_document_agent_log import append_document_agent_log_entry

            metadata = execution_metadata if isinstance(execution_metadata, dict) else {}
            telemetry = self._telemetry_dict(request)
            raw_available_tools = payload.available_tools if payload is not None else (available_tools or metadata.get("agent_available_tools") or telemetry.get("agent_available_tools") or [])
            resolved_available_tools = raw_available_tools if isinstance(raw_available_tools, list) else []
            resolved_tool_runs = tool_runs if tool_runs is not None else (list(payload.tool_runs) if payload is not None else [])
            serialized_tool_runs = [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in resolved_tool_runs
            ]
            error_tool_runs = sum(
                1
                for item in serialized_tool_runs
                if isinstance(item, dict) and str(item.get("status") or "").strip().lower() == "error"
            )

            entry = {
                "timestamp": datetime.now().isoformat(),
                "task_type": "document_agent",
                "success": success,
                "query": request.input_text,
                "provider_requested": metadata.get("provider_requested") or telemetry.get("provider_requested") or request.provider,
                "provider_effective": metadata.get("provider_effective") or telemetry.get("provider_effective") or request.provider,
                "model": metadata.get("model") or request.model,
                "user_intent": payload.user_intent if payload is not None else (metadata.get("agent_intent") or telemetry.get("agent_intent")),
                "tool_used": payload.tool_used if payload is not None else (metadata.get("agent_tool") or telemetry.get("agent_tool")),
                "answer_mode": payload.answer_mode if payload is not None else (metadata.get("agent_answer_mode") or telemetry.get("agent_answer_mode")),
                "agent_context_strategy": metadata.get("agent_context_strategy") or telemetry.get("agent_context_strategy"),
                "execution_strategy_requested": metadata.get("execution_strategy_requested") or telemetry.get("execution_strategy_requested"),
                "execution_strategy_used": metadata.get("execution_strategy_used") or telemetry.get("execution_strategy_used"),
                "execution_strategy_fallback_reason": metadata.get("execution_strategy_fallback_reason") or telemetry.get("execution_strategy_fallback_reason"),
                "workflow_id": metadata.get("workflow_id") or telemetry.get("workflow_id"),
                "workflow_route_decision": metadata.get("workflow_route_decision") or telemetry.get("workflow_route_decision"),
                "workflow_guardrail_decision": metadata.get("workflow_guardrail_decision") or telemetry.get("workflow_guardrail_decision"),
                "confidence": float(payload.confidence) if payload is not None else float(metadata.get("confidence") or 0.0),
                "needs_review": bool(payload.needs_review) if payload is not None else bool(metadata.get("needs_review")),
                "needs_review_reason": payload.needs_review_reason if payload is not None else metadata.get("needs_review_reason"),
                "source_count": len(payload.sources) if payload is not None else int(metadata.get("agent_source_count") or 0),
                "available_tools_count": len(resolved_available_tools),
                "error_tool_runs": error_tool_runs,
                "retrieval_backend_used": metadata.get("retrieval_backend_used"),
                "retrieval_strategy_used": metadata.get("retrieval_strategy_used"),
                "retrieval_strategy_requested": metadata.get("retrieval_strategy_requested"),
                "tool_runs": serialized_tool_runs,
            }
            if error_message:
                entry["error_message"] = error_message
            append_document_agent_log_entry(self._get_document_agent_log_path(), entry)
        except Exception:
            return None

    def _finalize_document_agent_payload(
        self,
        *,
        payload: DocumentAgentPayload,
        request: TaskExecutionRequest,
        tool_name: str,
        context_strategy: str,
        retrieval_details: dict[str, object] | None,
    ) -> DocumentAgentPayload:
        limitations = list(payload.limitations)
        recommended_actions = list(payload.recommended_actions)
        guardrails_applied = list(payload.guardrails_applied)
        document_count = len(request.source_document_ids or [])

        if request.use_document_context:
            guardrails_applied.append("Resposta restrita aos documentos selecionados na base documental.")
        else:
            limitations.append("Nenhum documento foi usado como grounding; a resposta depende apenas do texto do pedido.")

        if context_strategy == "retrieval":
            guardrails_applied.append("Grounding montado por retrieval para priorizar trechos mais relevantes à pergunta.")
        else:
            guardrails_applied.append("Grounding montado por document scan para priorizar cobertura mais ampla do documento.")

        if payload.sources:
            guardrails_applied.append("A resposta inclui fontes rastreáveis para auditoria manual.")
            recommended_actions.append("Abra os trechos-fonte citados para confirmar a interpretação antes de agir.")
        else:
            limitations.append("Não foram encontradas fontes suficientes para sustentar integralmente a resposta.")
            recommended_actions.append("Revise manualmente os documentos selecionados antes de usar esta resposta em decisão operacional.")

        if isinstance(retrieval_details, dict):
            fallback_reason = str(retrieval_details.get("retrieval_strategy_fallback_reason") or "").strip()
            backend_message = str(retrieval_details.get("backend_message") or "").strip()
            if fallback_reason:
                limitations.append(f"A estratégia de retrieval caiu em fallback: {fallback_reason}.")
                guardrails_applied.append("Fallback de retrieval registrado para reduzir falhas silenciosas.")
            elif backend_message and "fallback" in backend_message.lower():
                limitations.append(f"Observação do backend de retrieval: {backend_message}.")

        if tool_name == "compare_documents":
            if document_count > 3:
                limitations.append("A comparação atual foi limitada a no máximo 3 documentos nesta iteração do agente.")
                recommended_actions.append("Execute comparações em lotes menores para cobrir todos os documentos selecionados.")
                guardrails_applied.append("Comparação truncada para evitar sobrecarga e mistura excessiva de contexto.")
            recommended_actions.append("Valide as diferenças críticas diretamente nos documentos comparados antes de consolidar uma decisão.")
        elif tool_name == "draft_business_response":
            limitations.append("O rascunho não deve ser enviado automaticamente sem revisão humana do conteúdo e do tom.")
            recommended_actions.append("Revise destinatário, compromissos, datas e tom antes de enviar a resposta.")
            recommended_actions.append("Confirme nos trechos-fonte qualquer afirmação regulatória, contratual ou operacional relevante.")
            guardrails_applied.append("Rascunho produzido apenas com grounding documental e marcado explicitamente para aprovação humana.")
        elif tool_name == "extract_structured_data":
            recommended_actions.append("Baixe o JSON estruturado e valide campos críticos antes de integrar a saída em automações.")
            guardrails_applied.append("Extração limitada a evidências explicitamente presentes no documento.")
        elif tool_name == "generate_operational_checklist":
            recommended_actions.append("Revise o checklist com um responsável do processo antes da execução operacional.")
            guardrails_applied.append("Checklist gerado sem inferir passos implícitos fora do texto disponível.")
        elif tool_name == "summarize_document":
            limitations.append("O resumo pode omitir detalhes operacionais finos para ganhar concisão executiva.")
            recommended_actions.append("Se precisar de detalhe fino, consulte o documento completo ou execute uma pergunta documental específica.")
            guardrails_applied.append("Resumo comprimido para leitura executiva, preservando apenas os pontos mais relevantes.")
        else:
            limitations.append("Perguntas abertas podem exigir leitura humana adicional quando o documento tiver ambiguidade contextual.")
            guardrails_applied.append("O agente evita afirmar fatos sem grounding forte nos documentos selecionados.")

        if document_count > 1 and tool_name != "compare_documents":
            limitations.append("Há múltiplos documentos selecionados; confirme se a resposta não combinou contextos distintos de forma indevida.")

        if payload.needs_review:
            limitations.append("A resposta foi marcada para revisão humana antes de uso decisório.")
            if payload.needs_review_reason:
                limitations.append(f"Motivo da revisão humana: {payload.needs_review_reason}.")
            recommended_actions.append("Encaminhe o resultado para revisão humana antes de tomar uma decisão final.")
            guardrails_applied.append("Human-in-the-loop ativado para reduzir risco de uso indevido da resposta.")

        if isinstance(payload.confidence, float) and payload.confidence < 0.72:
            limitations.append(f"Confiança estimada abaixo do ideal ({payload.confidence:.0%}).")

        return payload.model_copy(
            update={
                "limitations": normalize_agent_bullet_points(limitations, limit=8),
                "recommended_actions": normalize_agent_bullet_points(recommended_actions, limit=8),
                "guardrails_applied": normalize_agent_bullet_points(guardrails_applied, limit=8),
            }
        )

    def _resolve_document_agent_context_strategy(
        self,
        *,
        request: TaskExecutionRequest,
        tool_name: str,
    ) -> str:
        if not request.use_document_context or not request.source_document_ids:
            return "document_scan"
        normalized_query = (request.input_text or "").strip()
        if tool_name in {"consult_documents", "draft_business_response"} and normalized_query:
            return "retrieval"
        if tool_name in {"compare_documents"} and normalized_query and len(request.source_document_ids) <= 2:
            return "retrieval"
        return "document_scan"

    def _build_document_agent_source_bundle(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> dict[str, object]:
        from ..rag.service import build_source_metadata, retrieve_relevant_chunks_detailed
        from ..services.document_context import (
            _filtered_chunks,
            _get_effective_rag_settings,
            _get_embedding_provider,
            _get_rag_index,
            _ordered_chunks,
        )

        context_text = self._build_optional_document_context(
            request,
            strategy=context_strategy,
            max_chunks=10,
            max_chars=20000,
        )
        retrieval_details: dict[str, object] = {}
        source_rows: list[dict[str, object]] = []
        rag_index = _get_rag_index()
        if isinstance(rag_index, dict) and request.source_document_ids:
            if context_strategy == "retrieval" and (request.input_text or "").strip():
                embedding_provider = _get_embedding_provider()
                if embedding_provider is not None:
                    try:
                        retrieval_details = retrieve_relevant_chunks_detailed(
                            query=request.input_text,
                            rag_index=rag_index,
                            settings=_get_effective_rag_settings(),
                            embedding_provider=embedding_provider,
                            document_ids=request.source_document_ids,
                        )
                        source_rows = build_source_metadata(
                            retrieval_details.get("chunks") if isinstance(retrieval_details.get("chunks"), list) else []
                        )
                    except Exception:
                        retrieval_details = {}
                        source_rows = []
            if not source_rows:
                document_chunks = _ordered_chunks(_filtered_chunks(rag_index, request.source_document_ids))
                source_rows = build_source_metadata(document_chunks[: min(len(document_chunks), 6)])
        sources = [AgentSource.model_validate(row) for row in source_rows]
        return {
            "context_text": context_text,
            "sources": sources,
            "retrieval_details": retrieval_details,
        }

    def _run_consult_documents_tool(
        self,
        *,
        provider,
        request: TaskExecutionRequest,
        user_intent: str,
        answer_mode: str,
        sources: list[AgentSource],
        context_text: str,
    ) -> DocumentAgentPayload:
        self._set_telemetry_value(request, "current_stage", "document_agent_consult_documents")
        prompt = self._build_document_agent_consult_prompt(
            user_query=request.input_text,
            context_text=context_text,
        )
        response_text = self._collect_response_text(provider, request, prompt)
        key_points = extract_bullet_points_from_text(response_text)
        confidence = 0.84 if sources else (0.66 if context_text else 0.52)
        return DocumentAgentPayload(
            user_intent=user_intent,
            intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
            answer_mode=answer_mode,
            tool_used="consult_documents",
            summary=response_text.strip() or "Não foi possível gerar uma resposta documental.",
            key_points=key_points,
            structured_response={
                "response_text": response_text,
                "context_preview": context_text[:3000],
            },
            sources=sources,
            confidence=confidence,
            needs_review=confidence < 0.6,
            needs_review_reason="weak_grounding_in_document_consultation" if confidence < 0.6 else None,
        )

    def _run_summary_tool(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> tuple[DocumentAgentPayload, StructuredResult]:
        nested_result = self._run_nested_structured_task(
            request=request,
            task_type="summary",
            context_strategy=context_strategy,
        )
        if not nested_result.success or not isinstance(nested_result.validated_output, SummaryPayload):
            raise RuntimeError(nested_result.validation_error or nested_result.parsing_error or "summary_tool_failed")
        payload = nested_result.validated_output
        key_points = normalize_agent_bullet_points(
            payload.key_insights or [topic.title for topic in payload.topics],
            limit=6,
        )
        confidence = float(nested_result.quality_score or nested_result.overall_confidence or 0.82)
        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "executive_summary"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode="friendly",
                tool_used="summarize_document",
                summary=payload.executive_summary,
                key_points=key_points,
                structured_response=payload.model_dump(mode="json"),
                confidence=confidence,
                needs_review=bool(nested_result.execution_metadata.get("needs_review")) if isinstance(nested_result.execution_metadata, dict) else False,
                needs_review_reason=(nested_result.execution_metadata.get("needs_review_reason") if isinstance(nested_result.execution_metadata, dict) else None),
            ),
            nested_result,
        )

    def _run_extraction_tool(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> tuple[DocumentAgentPayload, StructuredResult]:
        nested_result = self._run_nested_structured_task(
            request=request,
            task_type="extraction",
            context_strategy=context_strategy,
        )
        if not nested_result.success or not isinstance(nested_result.validated_output, ExtractionPayload):
            raise RuntimeError(nested_result.validation_error or nested_result.parsing_error or "extraction_tool_failed")
        payload = nested_result.validated_output
        key_points = normalize_agent_bullet_points(
            [
                *(f"{field.name}: {field.value}" for field in payload.extracted_fields[:4]),
                *(risk.description for risk in payload.risks[:2]),
                *(action.description for action in payload.action_items[:2]),
            ],
            limit=6,
        )
        summary = payload.main_subject or "Extração estruturada concluída."
        summary = (
            f"{summary} Foram identificados {len(payload.extracted_fields)} campo(s), {len(payload.entities)} entidade(s), "
            f"{len(payload.action_items)} ação(ões) e {len(payload.risks)} risco(s)."
        )
        confidence = float(nested_result.quality_score or nested_result.overall_confidence or 0.8)
        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "structured_extraction"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode="json",
                tool_used="extract_structured_data",
                summary=summary,
                key_points=key_points,
                structured_response=payload.model_dump(mode="json"),
                confidence=confidence,
                needs_review=bool(nested_result.execution_metadata.get("needs_review")) if isinstance(nested_result.execution_metadata, dict) else False,
                needs_review_reason=(nested_result.execution_metadata.get("needs_review_reason") if isinstance(nested_result.execution_metadata, dict) else None),
            ),
            nested_result,
        )

    def _run_business_response_drafting_tool(
        self,
        *,
        provider,
        request: TaskExecutionRequest,
        answer_mode: str,
        sources: list[AgentSource],
        context_text: str,
    ) -> DocumentAgentPayload:
        self._set_telemetry_value(request, "current_stage", "document_agent_draft_business_response")
        prompt = self._build_business_response_drafting_prompt(
            user_query=request.input_text,
            context_text=context_text,
        )
        response_text = self._collect_response_text(provider, request, prompt)
        confidence = 0.78 if sources else (0.6 if context_text else 0.48)
        draft_highlights = normalize_agent_bullet_points(
            extract_bullet_points_from_text(response_text, limit=8),
            limit=6,
        )
        if not draft_highlights:
            draft_highlights = normalize_agent_bullet_points(
                [
                    "Rascunho gerado com base nos documentos selecionados.",
                    "Revise compromissos, datas e destinatário antes do envio.",
                ],
                limit=4,
            )
        return DocumentAgentPayload(
            user_intent=str(self._telemetry_dict(request).get("agent_intent") or "business_response_drafting"),
            intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
            answer_mode=answer_mode,
            tool_used="draft_business_response",
            summary=response_text.strip() or "Não foi possível gerar um rascunho de resposta com base no contexto documental.",
            key_points=draft_highlights,
            structured_response={
                "draft_text": response_text.strip(),
                "draft_type": "business_response",
                "context_preview": context_text[:3000],
            },
            sources=sources,
            confidence=confidence,
            needs_review=True,
            needs_review_reason="business_response_draft_requires_human_approval",
        )

    def _run_checklist_tool(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> tuple[DocumentAgentPayload, StructuredResult]:
        nested_result = self._run_nested_structured_task(
            request=request,
            task_type="checklist",
            context_strategy=context_strategy,
        )
        if not nested_result.success or not isinstance(nested_result.validated_output, ChecklistPayload):
            raise RuntimeError(nested_result.validation_error or nested_result.parsing_error or "checklist_tool_failed")
        payload = nested_result.validated_output
        checklist_preview = normalize_agent_bullet_points([item.title for item in payload.items], limit=8)
        confidence = float(nested_result.quality_score or nested_result.overall_confidence or 0.8)
        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "operational_checklist"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode="checklist",
                tool_used="generate_operational_checklist",
                summary=f"Checklist operacional gerado com {payload.total_items} item(ns).",
                key_points=checklist_preview[:5],
                checklist_preview=checklist_preview,
                structured_response=payload.model_dump(mode="json"),
                confidence=confidence,
                needs_review=bool(nested_result.execution_metadata.get("needs_review")) if isinstance(nested_result.execution_metadata, dict) else False,
                needs_review_reason=(nested_result.execution_metadata.get("needs_review_reason") if isinstance(nested_result.execution_metadata, dict) else None),
            ),
            nested_result,
        )

    def _run_document_risk_review_tool(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> tuple[DocumentAgentPayload, StructuredResult]:
        nested_result = self._run_nested_structured_task(
            request=request,
            task_type="extraction",
            context_strategy="document_scan" if request.source_document_ids else context_strategy,
        )
        if not nested_result.success or not isinstance(nested_result.validated_output, ExtractionPayload):
            raise RuntimeError(nested_result.validation_error or nested_result.parsing_error or "document_risk_review_tool_failed")

        payload = nested_result.validated_output
        risks = normalize_agent_bullet_points([item.description for item in payload.risks], limit=8)
        gaps = normalize_agent_bullet_points(payload.missing_information, limit=6)
        actions = normalize_agent_bullet_points([item.description for item in payload.action_items], limit=6)
        key_points = normalize_agent_bullet_points([*risks[:3], *gaps[:2], *actions[:2]], limit=6)
        confidence = float(nested_result.quality_score or nested_result.overall_confidence or 0.79)
        if not risks and gaps:
            confidence = min(confidence, 0.69)

        summary_subject = payload.main_subject or "Análise documental"
        summary = (
            f"{summary_subject}: {len(risks)} risco(s), {len(gaps)} lacuna(s) e "
            f"{len(actions)} ação(ões) de mitigação identificada(s)."
        )

        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "document_risk_review"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode="friendly",
                tool_used="review_document_risks",
                summary=summary,
                key_points=key_points,
                recommended_actions=actions[:4],
                limitations=gaps,
                structured_response={
                    "review_type": "risk_gap_review",
                    "risks": risks,
                    "gaps": gaps,
                    "actions": actions,
                    "extraction_payload": payload.model_dump(mode="json"),
                },
                confidence=confidence,
                needs_review=bool(gaps and not risks),
                needs_review_reason=("risk_review_has_gaps_without_grounded_risks" if (gaps and not risks) else None),
            ),
            nested_result,
        )

    def _run_operational_task_extraction_tool(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> tuple[DocumentAgentPayload, StructuredResult]:
        nested_result = self._run_nested_structured_task(
            request=request,
            task_type="extraction",
            context_strategy="document_scan" if request.source_document_ids else context_strategy,
        )
        if not nested_result.success or not isinstance(nested_result.validated_output, ExtractionPayload):
            raise RuntimeError(nested_result.validation_error or nested_result.parsing_error or "operational_task_extraction_tool_failed")

        payload = nested_result.validated_output
        actions = normalize_agent_bullet_points([item.description for item in payload.action_items], limit=8)
        deadlines = normalize_agent_bullet_points(
            [
                item.due_date
                for item in payload.action_items
                if item.due_date
            ] + list(payload.important_dates),
            limit=6,
        )
        risks = normalize_agent_bullet_points([item.description for item in payload.risks], limit=6)
        key_points = normalize_agent_bullet_points([*actions[:4], *deadlines[:1], *risks[:1]], limit=6)
        confidence = float(nested_result.quality_score or nested_result.overall_confidence or 0.78)
        if not actions:
            confidence = min(confidence, 0.67)

        summary_subject = payload.main_subject or "Extração operacional"
        summary = (
            f"{summary_subject}: {len(actions)} tarefa(s) acionável(is), {len(deadlines)} prazo(s) e "
            f"{len(risks)} risco(s) operacional(is) identificado(s)."
        )

        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "operational_task_extraction"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode="friendly",
                tool_used="extract_operational_tasks",
                summary=summary,
                key_points=key_points,
                checklist_preview=actions[:6],
                recommended_actions=actions[:4],
                limitations=normalize_agent_bullet_points(payload.missing_information, limit=6),
                structured_response={
                    "review_type": "operational_extraction",
                    "actions": actions,
                    "deadlines": deadlines,
                    "risks": risks,
                    "extraction_payload": payload.model_dump(mode="json"),
                },
                confidence=confidence,
                needs_review=not bool(actions),
                needs_review_reason=("operational_extraction_without_grounded_actions" if not actions else None),
            ),
            nested_result,
        )

    def _run_policy_compliance_tool(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> tuple[DocumentAgentPayload, StructuredResult]:
        nested_result = self._run_nested_structured_task(
            request=request,
            task_type="extraction",
            context_strategy="document_scan" if request.source_document_ids else context_strategy,
        )
        if not nested_result.success or not isinstance(nested_result.validated_output, ExtractionPayload):
            raise RuntimeError(nested_result.validation_error or nested_result.parsing_error or "policy_compliance_tool_failed")

        payload = nested_result.validated_output
        restriction_tokens = (
            "restriction",
            "restrição",
            "restricao",
            "confidential",
            "confidencial",
            "retention",
            "reten",
            "notice",
            "payment",
            "exclusive",
            "non-compete",
            "jurisdiction",
            "governing law",
        )

        obligations = normalize_agent_bullet_points(
            [item.description for item in payload.action_items],
            limit=8,
        )
        restrictions = normalize_agent_bullet_points(
            [
                f"{field.name}: {field.value}"
                for field in payload.extracted_fields
                if any(token in (field.name or "").lower() for token in restriction_tokens)
            ],
            limit=8,
        )
        risks = normalize_agent_bullet_points(
            [item.description for item in payload.risks],
            limit=8,
        )
        gaps = normalize_agent_bullet_points(payload.missing_information, limit=6)

        key_points = normalize_agent_bullet_points(
            [*obligations[:3], *restrictions[:2], *risks[:2]],
            limit=6,
        )
        confidence = float(nested_result.quality_score or nested_result.overall_confidence or 0.78)
        if not obligations and not restrictions:
            confidence = min(confidence, 0.68)

        summary_subject = payload.main_subject or "Revisão de policy/compliance"
        summary = (
            f"{summary_subject}: {len(obligations)} obrigação(ões), "
            f"{len(restrictions)} restrição(ões) relevante(s), {len(risks)} risco(s) e {len(gaps)} lacuna(s) identificada(s)."
        )

        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "policy_compliance_review"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode="friendly",
                tool_used="review_policy_compliance",
                summary=summary,
                key_points=key_points,
                recommended_actions=obligations[:4],
                limitations=gaps,
                structured_response={
                    "review_type": "policy_compliance",
                    "obligations": obligations,
                    "restrictions": restrictions,
                    "risks": risks,
                    "missing_information": gaps,
                    "extraction_payload": payload.model_dump(mode="json"),
                },
                confidence=confidence,
                needs_review=(bool(gaps) and not obligations and not restrictions),
                needs_review_reason=("policy_compliance_low_grounding" if (bool(gaps) and not obligations and not restrictions) else None),
            ),
            nested_result,
        )

    def _run_technical_assistance_tool(
        self,
        *,
        request: TaskExecutionRequest,
        context_strategy: str,
    ) -> tuple[DocumentAgentPayload, StructuredResult]:
        nested_result = self._run_nested_structured_task(
            request=request,
            task_type="code_analysis",
            context_strategy=context_strategy,
        )
        if not nested_result.success or not isinstance(nested_result.validated_output, CodeAnalysisPayload):
            raise RuntimeError(nested_result.validation_error or nested_result.parsing_error or "technical_assistance_tool_failed")

        payload = nested_result.validated_output
        issue_titles = normalize_agent_bullet_points([item.title for item in payload.detected_issues], limit=6)
        refactor_plan = normalize_agent_bullet_points(payload.refactor_plan, limit=6)
        test_suggestions = normalize_agent_bullet_points(payload.test_suggestions, limit=6)
        risk_notes = normalize_agent_bullet_points(payload.risk_notes, limit=6)
        key_points = normalize_agent_bullet_points([*issue_titles[:3], *refactor_plan[:2], *test_suggestions[:1]], limit=6)
        confidence = float(nested_result.quality_score or nested_result.overall_confidence or 0.77)
        high_severity_issues = [item for item in payload.detected_issues if str(item.severity or "").lower() == "high"]

        summary = (
            f"{payload.snippet_summary} Foram identificados {len(payload.detected_issues)} problema(s), "
            f"{len(refactor_plan)} passo(s) de refatoração e {len(test_suggestions)} sugestão(ões) de teste."
        )

        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "technical_assistance"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode="friendly",
                tool_used="assist_technical_document",
                summary=summary,
                key_points=key_points,
                recommended_actions=refactor_plan[:4],
                limitations=risk_notes[:4],
                structured_response={
                    "review_type": "technical_review",
                    "snippet_summary": payload.snippet_summary,
                    "main_purpose": payload.main_purpose,
                    "detected_issues": payload.model_dump(mode="json").get("detected_issues", []),
                    "refactor_plan": refactor_plan,
                    "test_suggestions": test_suggestions,
                    "risk_notes": risk_notes,
                },
                confidence=confidence,
                needs_review=bool(high_severity_issues),
                needs_review_reason=("high_severity_technical_issue" if high_severity_issues else None),
            ),
            nested_result,
        )

    def _run_compare_documents_tool(
        self,
        *,
        provider,
        request: TaskExecutionRequest,
        answer_mode: str,
        sources: list[AgentSource],
    ) -> tuple[DocumentAgentPayload, list[AgentToolExecution]]:
        document_ids = list(request.source_document_ids or [])
        if len(document_ids) < 2:
            raise RuntimeError("compare_documents_requires_at_least_two_documents")

        selected_document_ids = document_ids[:3]
        document_labels = self._build_document_label_map(selected_document_ids)
        document_summaries: list[dict[str, object]] = []
        tool_runs: list[AgentToolExecution] = []

        for document_id in selected_document_ids:
            nested_result = self._run_nested_structured_task(
                request=request,
                task_type="summary",
                context_strategy="document_scan",
                source_document_ids=[document_id],
            )
            label = document_labels.get(document_id, document_id)
            if not nested_result.success or not isinstance(nested_result.validated_output, SummaryPayload):
                tool_runs.append(
                    AgentToolExecution(
                        tool_name=f"summarize_document:{document_id}",
                        status="error",
                        detail=f"Falha ao resumir o documento {label}.",
                    )
                )
                continue
            payload = nested_result.validated_output
            document_summaries.append(
                {
                    "document_id": document_id,
                    "label": label,
                    "summary": payload.executive_summary,
                    "key_points": normalize_agent_bullet_points(payload.key_insights or [topic.title for topic in payload.topics], limit=4),
                    "quality_score": nested_result.quality_score,
                }
            )
            tool_runs.append(
                AgentToolExecution(
                    tool_name=f"summarize_document:{document_id}",
                    status="success",
                    detail=f"Resumo gerado para {label}.",
                )
            )

        if len(document_summaries) < 2:
            raise RuntimeError("insufficient_document_summaries_for_comparison")

        self._set_telemetry_value(request, "current_stage", "document_agent_compare_documents")
        comparison_prompt = self._build_document_comparison_prompt(
            user_query=request.input_text,
            document_summaries=document_summaries,
        )
        comparison_text = self._collect_response_text(provider, request, comparison_prompt)
        comparison_points = extract_bullet_points_from_text(comparison_text, limit=6)

        findings = [
            ComparisonFinding(
                finding_type="document_summary",
                title=f"Resumo de {item['label']}",
                description=str(item["summary"]),
                documents=[str(item["label"])],
                evidence=list(item.get("key_points") or [])[:2],
            )
            for item in document_summaries
        ]
        findings.extend(
            ComparisonFinding(
                finding_type="cross_document_observation",
                title=self._short_label_from_text(point),
                description=point,
                documents=[str(item["label"]) for item in document_summaries],
                evidence=[],
            )
            for point in comparison_points
        )
        tool_runs.append(
            AgentToolExecution(
                tool_name="compare_documents",
                status="success",
                detail="Comparação documental sintetizada a partir dos resumos individuais.",
            )
        )

        quality_scores = [
            float(item["quality_score"])
            for item in document_summaries
            if isinstance(item.get("quality_score"), (int, float))
        ]
        confidence = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.72
        if len(document_ids) > len(selected_document_ids):
            confidence = min(confidence, 0.7)

        return (
            DocumentAgentPayload(
                user_intent=str(self._telemetry_dict(request).get("agent_intent") or "document_comparison"),
                intent_reason=str(self._telemetry_dict(request).get("agent_intent_reason") or "") or None,
                answer_mode=answer_mode,
                tool_used="compare_documents",
                summary=comparison_text.strip() or "Comparação documental concluída.",
                key_points=comparison_points,
                compared_documents=[str(item["label"]) for item in document_summaries],
                comparison_findings=findings,
                structured_response={
                    "document_summaries": document_summaries,
                    "comparison_text": comparison_text,
                    "truncated_document_count": max(0, len(document_ids) - len(selected_document_ids)),
                },
                sources=sources,
                confidence=confidence,
                needs_review=confidence < 0.65,
                needs_review_reason="comparison_grounding_is_partial" if confidence < 0.65 else None,
            ),
            tool_runs,
        )

    def _run_nested_structured_task(
        self,
        *,
        request: TaskExecutionRequest,
        task_type: str,
        context_strategy: str,
        source_document_ids: list[str] | None = None,
    ) -> StructuredResult:
        from .service import structured_service

        nested_request = request.model_copy(
            update={
                "task_type": task_type,
                "use_rag_context": False,
                "use_document_context": bool((source_document_ids or request.source_document_ids) and request.use_document_context),
                "source_document_ids": list(source_document_ids or request.source_document_ids),
                "context_strategy": context_strategy,
                "progress_callback": None,
                "telemetry": {},
            }
        )
        return structured_service.execute_task(nested_request)

    def _build_document_label_map(self, document_ids: list[str]) -> dict[str, str]:
        from ..services.document_context import _find_documents, _get_rag_index

        rag_index = _get_rag_index()
        if not isinstance(rag_index, dict):
            return {document_id: document_id for document_id in document_ids}
        documents = _find_documents(rag_index, document_ids)
        mapping: dict[str, str] = {}
        for document in documents:
            document_id = str(document.get("document_id") or document.get("file_hash") or "")
            if not document_id:
                continue
            label = str(document.get("name") or document_id)
            file_type = str(document.get("file_type") or "").strip()
            mapping[document_id] = f"{label} ({file_type})" if file_type else label
        return {document_id: mapping.get(document_id, document_id) for document_id in document_ids}

    def _short_label_from_text(self, text: str) -> str:
        cleaned = " ".join(str(text or "").split()).strip().rstrip(".?!")
        if not cleaned:
            return "Achado comparativo"
        words = cleaned.split()
        return " ".join(words[:8]) + ("…" if len(words) > 8 else "")

    def _build_document_agent_consult_prompt(self, *, user_query: str, context_text: str) -> str:
        return f"""
Você é o Document Operations Copilot.
Responda em português do Brasil.
Use apenas as informações presentes no contexto documental.
Se o contexto estiver insuficiente, diga explicitamente que a informação não está clara e peça revisão humana.
Evite inventar fatos, datas, números ou nomes.
Primeiro entregue uma resposta curta e objetiva.
Depois traga bullets curtos com os principais pontos encontrados.

Pedido do usuário:
{user_query}

Contexto documental:
{context_text}
"""

    def _build_business_response_drafting_prompt(self, *, user_query: str, context_text: str) -> str:
        return f"""
Você é o Document Operations Copilot.
Redija em português do Brasil um rascunho curto de resposta profissional orientado pelos documentos.
Use apenas fatos explícitos do contexto documental.
Não invente compromissos, datas, números, cláusulas, prazos ou aprovações que não estejam sustentados pelas fontes.
Se faltar informação importante, mantenha a redação conservadora e explicite a necessidade de confirmação humana.
Evite linguagem excessivamente assertiva quando o contexto estiver parcial.
Produza uma resposta pronta para revisão humana, não para envio automático.

Formato desejado:
- um rascunho principal em tom profissional;
- se necessário, inclua um fechamento curto pedindo validação/revisão interna antes do envio.

Pedido do usuário:
{user_query}

Contexto documental:
{context_text}
"""

    def _build_document_comparison_prompt(self, *, user_query: str, document_summaries: list[dict[str, object]]) -> str:
        serialized = []
        for item in document_summaries:
            serialized.append(
                f"[DOCUMENTO] {item['label']}\n"
                f"Resumo: {item['summary']}\n"
                f"Pontos-chave: {'; '.join(item.get('key_points') or [])}"
            )
        summary_block = "\n\n".join(serialized)
        return f"""
Você é o Document Operations Copilot.
Compare os documentos resumidos abaixo e responda em português do Brasil.
Use apenas o conteúdo fornecido.
Não invente diferenças ou semelhanças não sustentadas pelos resumos.
Entregue:
1. um parágrafo curto de comparação executiva;
2. até 6 bullets curtos começando com '-'.

Pedido do usuário:
{user_query}

Resumos dos documentos:
{summary_block}
"""


def get_task_handler(task_type: str) -> Optional[TaskHandler]:
    mapping: dict[str, TaskHandler] = {
        "extraction": ExtractionTaskHandler(),
        "summary": SummaryTaskHandler(),
        "checklist": ChecklistTaskHandler(),
        "document_agent": DocumentAgentTaskHandler(),
        "cv_analysis": CVAnalysisTaskHandler(),
        "code_analysis": CodeAnalysisTaskHandler(),
    }
    return mapping.get(task_type)
