"""Task handlers for structured outputs."""
from __future__ import annotations

import json
import math
import re
import time
from typing import Optional, Type

from .base import ChecklistPayload, CVAnalysisPayload, CodeAnalysisPayload, ExtractionPayload, SummaryPayload
from .envelope import TaskExecutionRequest, StructuredResult
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
        registry = self._get_provider_registry()
        provider_entry = registry.get(request.provider)
        if provider_entry is None:
            raise RuntimeError(f"Provider '{request.provider}' is not available in the current environment.")
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
                        "provider": request.provider,
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
                "Extraction gerada com o documento inteiro porque o tamanho ainda é seguro para envio direto."
                if extraction_mode == "full_document_direct"
                else "Extraction gerada com contexto recortado do document scan."
            ),
            "stages": [
                {
                    "stage_type": extraction_mode,
                    "label": "Extraction generation input",
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
        data["categories"] = self._unique_extraction_strings(payload.categories)
        data["important_dates"] = self._unique_extraction_strings(payload.important_dates)
        data["missing_information"] = self._unique_extraction_strings(payload.missing_information)
        data["extracted_fields"] = self._normalize_extracted_fields(payload)
        data["important_numbers"] = self._normalize_important_numbers(payload, legal_view=legal_view)
        data["risks"] = self._normalize_risks(payload, legal_view=legal_view)
        data["action_items"] = self._normalize_action_items(payload, legal_view=legal_view)
        data["relationships"] = self._normalize_relationships(payload)

        return ExtractionPayload(**data)

    def _clean_extraction_text(self, value: object) -> str:
        return " ".join(str(value or "").split()).strip()

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

    def _normalize_extracted_fields(self, payload: ExtractionPayload) -> list[dict[str, object]]:
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

        return normalized

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

    def _normalize_risks(self, payload: ExtractionPayload, *, legal_view: bool) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[str] = set()

        for item in payload.risks:
            description = self._clean_extraction_text(item.description)
            if not description:
                continue
            evidence = self._clean_extraction_text(item.evidence) or None
            impact = self._clean_extraction_text(item.impact) or None
            owner = self._clean_extraction_text(item.owner) or None
            due_date = self._clean_extraction_text(item.due_date) or None
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

        return normalized

    def _normalize_action_items(self, payload: ExtractionPayload, *, legal_view: bool) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()

        for item in payload.action_items:
            description = self._clean_extraction_text(item.description)
            if not description:
                continue
            owner = self._clean_extraction_text(item.owner) or None
            due_date = self._clean_extraction_text(item.due_date) or None
            status = self._clean_extraction_text(item.status) or None
            evidence = self._clean_extraction_text(item.evidence) or None
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

    def _normalize_relationships(self, payload: ExtractionPayload) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        seen: set[tuple[str, str, str]] = set()

        for item in payload.relationships:
            from_entity = self._clean_extraction_text(item.from_entity)
            to_entity = self._clean_extraction_text(item.to_entity)
            relationship = self._clean_extraction_text(item.relationship)
            evidence = self._clean_extraction_text(item.evidence) or None
            if not (from_entity and to_entity and relationship):
                continue
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
                        "label": "Final synthesis",
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
                    "label": f"Single-pass summary ({strategy})",
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
                        "label": "Final checklist synthesis",
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
                    "label": "Checklist generation input",
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
                    "label": f"Checklist part {index} of {total_parts}",
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
        self._record_timing(request, "parsing_s", time.perf_counter() - parsing_started_at)
        self._record_timing(request, "total_s", time.perf_counter() - total_started_at)
        self._report_progress(request, step="done", progress=1.0, detail="Análise de código finalizada")
        return result

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
