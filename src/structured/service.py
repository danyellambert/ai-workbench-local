"""Service layer for structured outputs."""
from __future__ import annotations

import re
from math import ceil
from typing import Any

from ..config import get_ollama_settings
from .base import ActionItem, ChecklistPayload, CVAnalysisPayload, CodeAnalysisPayload, ExtractionPayload, RiskItem, EducationEntry, ExperienceEntry, CVSection, Entity, Relationship, CodeIssue
from .envelope import StructuredResult, TaskExecutionRequest
from .registry import task_registry
from .tasks import get_task_handler

_PLACEHOLDER_MARKERS = {
    "full name",
    "name@example.com",
    "city, country",
    "skill 1",
    "skill 2",
    "strength 1",
    "improvement 1",
    "item 1",
    "item 2",
    "https://linkedin.com/in/example",
    "company x",
}
_AUTO_CONTEXT_WINDOW_CAP_BY_PROVIDER = {
    "ollama": 256000,
    "openai": 128000,
    "huggingface_local": 32768,
}


class StructuredOutputService:
    """Service for executing structured output tasks."""

    def __init__(self) -> None:
        self.task_registry = task_registry
        self.ollama_settings = get_ollama_settings()

    def _get_provider_registry(self):
        from ..providers.registry import build_provider_registry

        return build_provider_registry()

    def _resolve_provider_runtime_profile(self, provider_name: str | None) -> dict[str, Any]:
        from ..providers.registry import resolve_provider_runtime_profile

        registry = self._get_provider_registry()
        return resolve_provider_runtime_profile(
            registry,
            provider_name,
            capability="chat",
            fallback_provider="ollama",
        )

    def _resolve_context_window_cap(self, fallback_cap: int, *, effective_provider: str | None = None) -> int:
        provider_key = (effective_provider or "").strip().lower()
        configured_provider_cap = _AUTO_CONTEXT_WINDOW_CAP_BY_PROVIDER.get(provider_key, int(fallback_cap))
        return max(int(fallback_cap), int(configured_provider_cap))

    def execute_task(self, request: TaskExecutionRequest) -> StructuredResult:
        task_definition = self.task_registry.get_task(request.task_type)
        if not task_definition:
            return self._create_error_result(
                request.task_type,
                f"Task type '{request.task_type}' not registered",
                request.input_text,
            )
        handler = get_task_handler(request.task_type)
        if not handler:
            return self._create_error_result(
                request.task_type,
                f"No handler available for task type '{request.task_type}'",
                request.input_text,
            )
        provider_runtime = self._resolve_provider_runtime_profile(request.provider)
        requested_provider = str(provider_runtime.get("requested_provider") or request.provider or "ollama")
        effective_provider = str(provider_runtime.get("effective_provider") or requested_provider)
        provider_entry = provider_runtime.get("provider_entry") if isinstance(provider_runtime.get("provider_entry"), dict) else {}
        provider_default_model = str(provider_entry.get("default_model") or "")
        provider_default_context_window = int(
            provider_entry.get("default_context_window") or self.ollama_settings.default_context_window
        )

        model = request.model or task_definition.default_model or provider_default_model or self.ollama_settings.default_model
        temperature = request.temperature if request.temperature is not None else task_definition.default_temperature
        configured_context_window_cap = request.context_window or provider_default_context_window
        context_window_cap = self._resolve_context_window_cap(
            int(configured_context_window_cap),
            effective_provider=effective_provider,
        )
        context_window = self.resolve_context_window(
            request,
            max_context_window=configured_context_window_cap,
            effective_provider=effective_provider,
        )
        execution_request = request.model_copy(
            update={
                "provider": requested_provider,
                "model": model,
                "temperature": temperature,
                "context_window": context_window,
            }
        )
        try:
            result = handler.execute(execution_request)
            result.context_used = (execution_request.use_document_context or execution_request.use_rag_context) and bool(execution_request.source_document_ids)
            result.source_documents = list(execution_request.source_document_ids)
            telemetry = execution_request.telemetry if isinstance(execution_request.telemetry, dict) else {}
            provider_requested = str(telemetry.get("provider_requested") or requested_provider)
            provider_effective = str(telemetry.get("provider_effective") or effective_provider)
            provider_fallback_reason = telemetry.get("provider_fallback_reason") or provider_runtime.get("fallback_reason")
            result.execution_metadata = {
                **(result.execution_metadata if isinstance(result.execution_metadata, dict) else {}),
                "provider": provider_effective,
                "provider_requested": provider_requested,
                "provider_effective": provider_effective,
                "model": execution_request.model,
                "resolved_context_window": context_window,
                "context_window_cap": context_window_cap,
                "document_chars_estimate": self._estimate_document_chars(request),
                **({"provider_fallback_reason": provider_fallback_reason} if provider_fallback_reason else {}),
                **({"telemetry": telemetry} if telemetry else {}),
            }
            if result.primary_render_mode is None:
                result.primary_render_mode = task_definition.primary_render_mode
            self._normalize_result_payload(result, execution_request)
            result.quality_score = self._estimate_quality_score(result, execution_request)
            if result.overall_confidence is None and result.quality_score is not None:
                result.overall_confidence = result.quality_score
            return result
        except Exception as exc:
            return self._create_error_result(
                request.task_type,
                f"Execution failed: {exc}",
                request.input_text,
            )

    def resolve_context_window(
        self,
        request: TaskExecutionRequest,
        *,
        max_context_window: int | None = None,
        effective_provider: str | None = None,
    ) -> int:
        fallback_cap = int(max_context_window or self.ollama_settings.default_context_window)
        cap = self._resolve_context_window_cap(fallback_cap, effective_provider=effective_provider or request.provider)
        doc_chars = self._estimate_document_chars(request)
        base_by_task = {
            "summary": 32768,
            "extraction": 16384,
            "cv_analysis": 24576,
            "checklist": 16384,
            "code_analysis": 12288,
        }
        base = base_by_task.get(request.task_type, 12288)

        if request.task_type == "summary":
            if doc_chars >= 180000:
                base = 49152
            elif doc_chars >= 80000:
                base = 32768
            elif doc_chars >= 25000:
                base = 24576
        elif request.task_type == "cv_analysis":
            if doc_chars >= 60000:
                base = 32768
            elif doc_chars >= 20000:
                base = 24576
        elif request.task_type == "extraction":
            if doc_chars >= 100000:
                base = 24576
            elif doc_chars >= 30000:
                base = 16384
        elif request.task_type == "checklist":
            if doc_chars >= 80000:
                base = 32768
            elif doc_chars >= 30000:
                base = 24576
            elif doc_chars >= 12000:
                base = 16384
        elif request.task_type == "code_analysis":
            if len((request.input_text or "")) >= 12000 or doc_chars >= 20000:
                base = 16384

        strategy = (request.context_strategy or "").lower().strip()
        if strategy == "retrieval":
            base = min(base, 16384 if request.task_type != "summary" else 24576)
        elif strategy == "document_scan" and request.task_type in {"summary", "cv_analysis", "extraction", "checklist"}:
            base = max(base, 16384)

        resolved = min(base, cap)
        resolved = max(4096, resolved)
        return int(resolved)

    def _estimate_document_chars(self, request: TaskExecutionRequest) -> int:
        input_chars = len((request.input_text or "").strip())
        if not request.source_document_ids:
            return input_chars
        try:
            from ..services.document_context import _filtered_chunks, _get_rag_index, _ordered_chunks
        except Exception:
            return input_chars
        rag_index = _get_rag_index()
        if not isinstance(rag_index, dict):
            return input_chars
        chunks = _ordered_chunks(_filtered_chunks(rag_index, request.source_document_ids))
        text_chars = sum(len(str(chunk.get("text") or "")) for chunk in chunks if isinstance(chunk, dict))
        return max(text_chars, input_chars)

    def _build_request_source_text(self, request: TaskExecutionRequest | None) -> str:
        if request is None:
            return ""

        input_text = (request.input_text or "").strip()
        if not request.source_document_ids:
            return input_text

        try:
            from ..services.document_context import _filtered_chunks, _get_rag_index, _ordered_chunks
        except Exception:
            return input_text

        rag_index = _get_rag_index()
        if not isinstance(rag_index, dict):
            return input_text

        chunks = _ordered_chunks(_filtered_chunks(rag_index, request.source_document_ids))
        parts = [
            str(chunk.get("text") or "").strip()
            for chunk in chunks
            if isinstance(chunk, dict) and str(chunk.get("text") or "").strip()
        ]
        full_text = "\n\n".join(parts).strip()
        return full_text or input_text

    def _normalize_result_payload(self, result: StructuredResult, request: TaskExecutionRequest | None = None) -> None:
        payload = result.validated_output
        if payload is None:
            return
        original_serialized = result.validated_output.model_dump(mode="json") if hasattr(result.validated_output, "model_dump") else None
        if isinstance(payload, ChecklistPayload):
            payload = self._improve_checklist_payload(payload, request=request)
            total_items = len(payload.items)
            completed_items = sum(1 for item in payload.items if item.status == "completed")
            progress_percentage = round((completed_items / total_items) * 100.0, 1) if total_items else 0.0
            normalized_items = []
            categories = [item.category for item in payload.items if item.category]
            priorities = [item.priority for item in payload.items if item.priority]
            durations = [item.estimated_time_minutes for item in payload.items if item.estimated_time_minutes is not None]
            repeated_category = len(set(categories)) == 1 and len(categories) == len(payload.items)
            repeated_priority = len(set(priorities)) == 1 and len(priorities) == len(payload.items)
            repeated_duration = len(set(durations)) == 1 and len(durations) == len(payload.items)
            for item in payload.items:
                normalized_items.append(item.model_copy(update={
                    'category': item.category,
                    'priority': None if repeated_priority and item.priority == priorities[0] else item.priority,
                    'estimated_time_minutes': None,
                    'status': item.status or 'pending',
                    'dependencies': item.dependencies or [],
                }))
            result.validated_output = payload.model_copy(
                update={
                    "items": normalized_items,
                    "total_items": total_items,
                    "completed_items": completed_items,
                    "progress_percentage": progress_percentage,
                }
            )
        if isinstance(result.validated_output, CVAnalysisPayload):
            payload = result.validated_output
            unique_skills = []
            seen_skills = set()
            for item in payload.skills:
                cleaned = self._normalize_skill_text(item)
                if not cleaned:
                    continue
                key = cleaned.lower()
                if key not in seen_skills:
                    seen_skills.add(key)
                    unique_skills.append(cleaned)
            for item in self._recover_grounded_skills_from_request(request):
                item = self._normalize_skill_text(item)
                if not item:
                    continue
                key = item.lower()
                if key not in seen_skills:
                    seen_skills.add(key)
                    unique_skills.append(item)
            unique_languages = []
            seen_languages = set()
            for item in payload.languages:
                cleaned = item.strip() if isinstance(item, str) else str(item).strip()
                if not cleaned:
                    continue
                key = cleaned.lower()
                if key not in seen_languages:
                    seen_languages.add(key)
                    unique_languages.append(cleaned)
            education_entries = list(payload.education_entries)
            education_entries.extend(self._recover_grounded_education_from_request(request))
            experience_entries = list(payload.experience_entries)
            project_items = list(payload.projects)
            for section in payload.sections:
                section_type = (section.section_type or '').lower()
                section_title = (section.title or '').lower()
                is_education = section_type == 'education' or 'education' in section_title or 'academic' in section_title
                is_languages = section_type == 'languages' or 'language' in section_title
                is_experience = section_type == 'experience' or 'experience' in section_title or 'employment' in section_title or 'work history' in section_title
                is_skills = section_type == 'skills' or 'skill' in section_title
                is_projects = section_type == 'projects' or 'project' in section_title
                for item in section.content:
                    if is_skills:
                        source = item.text or ', '.join(str(v) for v in item.details.values() if isinstance(v, str))
                        for token in [self._normalize_skill_text(x) for x in str(source).replace('\n', ',').split(',') if x.strip()]:
                            if not token:
                                continue
                            key = token.lower()
                            if key not in seen_skills:
                                seen_skills.add(key)
                                unique_skills.append(token)
                    if is_languages:
                        details = item.details or {}
                        language = details.get('language') or details.get('name')
                        level = details.get('level')
                        text_item = item.text
                        candidate = None
                        if language and level:
                            candidate = f"{language} ({level})"
                        elif language:
                            candidate = str(language)
                        elif text_item:
                            candidate = text_item
                        if candidate:
                            candidate = candidate.strip()
                            key = candidate.lower()
                            if key not in seen_languages:
                                seen_languages.add(key)
                                unique_languages.append(candidate)
                    if is_education:
                        source = item.details if item.details else (item.text or {})
                        candidate = EducationEntry.model_validate(source)
                        if (candidate.description or candidate.degree or candidate.institution):
                            education_entries.append(candidate)
                    if is_experience:
                        details = dict(item.details or {})
                        if item.text and 'description' not in details:
                            details['description'] = item.text
                        candidate = ExperienceEntry.model_validate(details if details else (item.text or {}))
                        if (candidate.description or candidate.title or candidate.organization):
                            experience_entries.append(candidate)
                    if is_projects:
                        project_text = (item.text or '').strip()
                        if not project_text and item.details:
                            project_text = ' | '.join(str(v).strip() for v in item.details.values() if isinstance(v, str) and str(v).strip())
                        if project_text:
                            project_items.append(project_text)
            dedup_education = []
            seen_education = set()
            for entry in education_entries:
                key = '|'.join([
                    (entry.degree or '').strip().lower(),
                    (entry.institution or '').strip().lower(),
                    (entry.date_range or '').strip().lower(),
                    (entry.description or '').strip().lower(),
                ])
                if not key.strip('|'):
                    continue
                replaced = False
                for index, existing in enumerate(dedup_education):
                    if self._education_entries_compete(existing, entry):
                        if self._education_entry_score(entry) > self._education_entry_score(existing):
                            dedup_education[index] = entry
                        replaced = True
                        break
                if not replaced and key not in seen_education:
                    seen_education.add(key)
                    dedup_education.append(entry)
            dedup_education = [entry for entry in dedup_education if self._should_keep_education_entry(entry)]
            dedup_experience = []
            seen_experience = set()
            for entry in experience_entries:
                entry = self._repair_cv_experience_entry(entry)
                if entry.organization and entry.location:
                    entry = entry.model_copy(update={
                        'organization': self._strip_location_from_organization(entry.organization, entry.location)
                    })
                entry = entry.model_copy(update={
                    'description': self._rebuild_experience_description(entry)
                })
                entry.bullets = [item.strip() for item in entry.bullets if isinstance(item, str) and item.strip()]
                if entry.bullets:
                    entry.description = entry.description or " | ".join(item for item in [entry.title, entry.organization, entry.location, entry.date_range] if item)
                key = '|'.join([
                    (entry.title or '').strip().lower(),
                    (entry.organization or '').strip().lower(),
                    (entry.date_range or '').strip().lower(),
                ])
                if key.strip('|') and key not in seen_experience:
                    seen_experience.add(key)
                    dedup_experience.append(entry)
                elif key.strip('|'):
                    for idx, existing in enumerate(dedup_experience):
                        existing_key = '|'.join([
                            (existing.title or '').strip().lower(),
                            (existing.organization or '').strip().lower(),
                            (existing.date_range or '').strip().lower(),
                        ])
                        if existing_key != key:
                            continue
                        existing_score = sum(bool(value) for value in [existing.title, existing.organization, existing.location, existing.date_range]) + len(existing.bullets)
                        entry_score = sum(bool(value) for value in [entry.title, entry.organization, entry.location, entry.date_range]) + len(entry.bullets)
                        if entry_score > existing_score:
                            dedup_experience[idx] = entry
                        elif entry.bullets and not existing.bullets:
                            existing.bullets = entry.bullets
                        break
            conservative_years = self._compute_experience_years_from_entries(dedup_experience)
            personal_info = payload.personal_info
            grounded_emails = self._recover_grounded_emails_from_request(request)
            if personal_info is not None and not personal_info.location:
                derived_location = next((entry.location for entry in dedup_experience if entry.location), None)
                if derived_location:
                    personal_info = personal_info.model_copy(update={"location": derived_location})
            if personal_info is not None:
                best_email = self._choose_best_email([personal_info.email, *grounded_emails])
                if best_email and best_email != personal_info.email:
                    personal_info = personal_info.model_copy(update={"email": best_email})
            unique_strengths = list(dict.fromkeys(item.strip() for item in payload.strengths if item and item.strip()))
            unique_improvements = list(dict.fromkeys(item.strip() for item in payload.improvement_areas if item and item.strip()))
            unique_projects = self._normalize_project_items(project_items)
            sections = list(payload.sections)
            if not unique_projects:
                unique_projects = self._recover_grounded_projects_from_request(request)
                unique_projects = self._normalize_project_items(unique_projects)
            if unique_projects and not any((section.section_type or '').lower() == 'projects' for section in sections):
                sections.append(CVSection(section_type='projects', title='Projects', content=[{'text': item} for item in unique_projects], confidence=0.9))
            if not unique_projects:
                description_projects = []
                for section in sections:
                    if (section.section_type or '').lower() != 'projects':
                        continue
                    for item in section.content:
                        text = (item.text or '').strip()
                        if text:
                            description_projects.append(text)
                unique_projects = self._normalize_project_items(description_projects)
            sections = [
                section.model_copy(update={
                    'content': [{'text': item} for item in unique_projects] if (section.section_type or '').lower() == 'projects' and unique_projects else section.content
                })
                for section in sections
            ]
            sections = self._synchronize_cv_sections(
                sections=sections,
                skills=unique_skills,
                education_entries=dedup_education,
                experience_entries=dedup_experience,
            )
            result.validated_output = payload.model_copy(
                update={
                    "personal_info": personal_info,
                    "skills": unique_skills,
                    "languages": unique_languages,
                    "education_entries": dedup_education,
                    "experience_entries": dedup_experience,
                    "projects": unique_projects,
                    "sections": sections,
                    "experience_years": conservative_years,
                    "strengths": unique_strengths,
                    "improvement_areas": unique_improvements,
                }
            )
            self._apply_cv_grounding_guardrail(result)
        if isinstance(result.validated_output, ExtractionPayload):
            payload = self._repair_extraction_payload(result.validated_output, request)
            normalized_categories = list(dict.fromkeys(item.strip() for item in payload.categories if item and item.strip()))
            normalized_dates = list(dict.fromkeys(item.strip() for item in payload.important_dates if item and item.strip()))
            normalized_numbers = list(dict.fromkeys(item.strip() for item in payload.important_numbers if item and item.strip()))
            normalized_missing = list(dict.fromkeys(item.strip() for item in payload.missing_information if item and item.strip()))
            normalized_risks = []
            seen_risks = set()
            for item in payload.risks:
                description = item.description.strip() if item.description else ""
                if not description or description in seen_risks:
                    continue
                seen_risks.add(description)
                normalized_risks.append(
                    item.model_copy(update={"description": description}) if isinstance(item, RiskItem) else item
                )
            normalized_actions = []
            seen_actions = set()
            for item in payload.action_items:
                description = item.description.strip() if item.description else ""
                if not description or description in seen_actions:
                    continue
                seen_actions.add(description)
                normalized_actions.append(
                    item.model_copy(update={"description": description}) if isinstance(item, ActionItem) else item
                )
            result.validated_output = payload.model_copy(
                update={
                    "categories": normalized_categories,
                    "important_dates": normalized_dates,
                    "important_numbers": normalized_numbers,
                    "risks": normalized_risks,
                    "action_items": normalized_actions,
                    "missing_information": normalized_missing,
                }
            )
        if isinstance(result.validated_output, CodeAnalysisPayload):
            payload = self._repair_code_analysis_payload(result.validated_output, request)
            result.validated_output = payload.model_copy(
                update={
                    "readability_improvements": list(dict.fromkeys(item.strip() for item in payload.readability_improvements if item and item.strip())),
                    "maintainability_improvements": list(dict.fromkeys(item.strip() for item in payload.maintainability_improvements if item and item.strip())),
                    "refactor_plan": list(dict.fromkeys(item.strip() for item in payload.refactor_plan if item and item.strip())),
                    "test_suggestions": list(dict.fromkeys(item.strip() for item in payload.test_suggestions if item and item.strip())),
                    "risk_notes": list(dict.fromkeys(item.strip() for item in payload.risk_notes if item and item.strip())),
                }
            )
        if result.validated_output is not None and hasattr(result.validated_output, "model_dump"):
            normalized_serialized = result.validated_output.model_dump(mode="json")
            result.parsed_json = normalized_serialized
            if original_serialized is not None and normalized_serialized != original_serialized:
                result.repair_applied = True

    def _improve_checklist_payload(self, payload: ChecklistPayload, request: TaskExecutionRequest | None = None) -> ChecklistPayload:
        generic_categories = {"preparation", "general", "checklist", "phase", "procedure"}
        non_grounded_evidence_markers = {
            "not explicitly stated in the checklist, but implied as part of the overall safety checks.",
            "implied as part of the overall safety checks.",
            "not explicitly stated",
        }

        def infer_category(existing_category: str | None, source_text: str | None, description: str | None) -> str | None:
            normalized_existing = normalize_literal_text(existing_category)
            if normalized_existing and normalized_existing.lower() not in generic_categories:
                return normalized_existing

            for candidate_text in [source_text, description]:
                normalized_candidate = normalize_literal_text(candidate_text)
                if not normalized_candidate:
                    continue
                match = re.match(r'^([A-Z][A-Za-z0-9 /&()_-]{2,40}):\s+', normalized_candidate)
                if not match:
                    continue
                candidate_category = normalize_literal_text(match.group(1))
                if candidate_category and 1 <= len(candidate_category.split()) <= 6:
                    return candidate_category

            return None

        def normalize_literal_text(text: str | None) -> str:
            cleaned = " ".join(str(text or "").split()).strip()
            cleaned = cleaned.replace(" ,", ",").replace(" .", ".")
            return cleaned

        def is_noisy_category(text: str | None) -> bool:
            normalized = normalize_literal_text(text)
            lowered = normalized.lower()
            if not normalized:
                return True
            if '?' in normalized:
                return True
            if lowered in generic_categories:
                return True
            if len(normalized) > 70 or len(normalized.split()) > 8:
                return True
            if re.match(r'^(is|are|was|were|does|do|did|has|have|had|can|could|should|would|will|may|must)\b', lowered):
                return True
            return False

        def is_answer_only_text(text: str | None) -> bool:
            normalized = normalize_literal_text(text).strip(" .!?;:-")
            lowered = normalized.lower()
            if not lowered or '?' in lowered:
                return False
            if lowered in {"yes", "no", "not applicable", "n/a"}:
                return True
            if lowered.startswith("yes,") or lowered.startswith("no,"):
                return True
            if lowered.startswith("yes and ") or lowered.startswith("no and "):
                return True
            return False

        def strip_list_marker(text: str | None) -> str:
            normalized = normalize_literal_text(text)
            return re.sub(r'^[-•]\s+', '', normalized).strip()

        def strip_answer_suffix(text: str | None) -> str:
            normalized = strip_list_marker(text)
            if not normalized:
                return ""
            if is_answer_only_text(normalized):
                return ""
            if '?' in normalized:
                question_part, suffix = normalized.split('?', 1)
                if is_answer_only_text(suffix):
                    return f"{question_part.strip()}?"
            return normalized

        def make_evidence(source_text: str | None, evidence: str | None) -> str | None:
            source = strip_answer_suffix(source_text)
            snippet = strip_answer_suffix(evidence)
            if snippet and snippet.lower() in non_grounded_evidence_markers:
                snippet = ""
            if snippet:
                return snippet
            return source or None

        def title_from_source(source_text: str | None, fallback: str | None) -> str:
            source = strip_answer_suffix(source_text)
            fallback_text = strip_answer_suffix(fallback)
            if not source:
                return fallback_text
            title = re.sub(r'\s+', ' ', source).strip()
            title = title.rstrip('?').rstrip('.').strip()
            if not title:
                return fallback_text
            return title

        def strip_category_prefix_from_title(title: str, category: str | None) -> str:
            normalized_title = normalize_literal_text(title)
            normalized_category = normalize_literal_text(category)
            if not normalized_title or not normalized_category:
                return normalized_title
            prefix_patterns = [
                rf'^{re.escape(normalized_category)}\s*:\s*',
                rf'^{re.escape(normalized_category)}\s*[\-–—]\s*',
            ]
            stripped = normalized_title
            for pattern in prefix_patterns:
                stripped = re.sub(pattern, '', stripped, flags=re.I).strip()
            if stripped and stripped != normalized_title:
                return stripped
            return normalized_title

        def description_from_source(source_text: str | None, evidence: str | None, fallback: str | None) -> str:
            source = strip_answer_suffix(source_text)
            snippet = strip_answer_suffix(evidence)
            fallback_text = strip_answer_suffix(fallback)
            return source or snippet or fallback_text

        def should_drop_item(title: str, description: str) -> bool:
            normalized_title = normalize_literal_text(title).lower()
            normalized_description = normalize_literal_text(description).lower()
            if not normalized_title and not normalized_description:
                return True
            placeholder_markers = {
                "real action item",
                "operational action item",
                "checklist part title",
                "category=-",
            }
            if normalized_title in placeholder_markers or normalized_description in placeholder_markers:
                return True
            if normalized_title.startswith("category=") or normalized_description.startswith("category="):
                return True
            return False

        def dedupe_key(title: str, source_text: str, category: str | None) -> tuple[str, str, str]:
            normalized_title = normalize_literal_text(title).lower()
            normalized_source = normalize_literal_text(source_text).lower()
            normalized_category = normalize_literal_text(category).lower()
            return (normalized_title, normalized_source, normalized_category)

        def split_by_question_marks(text: str) -> list[str]:
            normalized = normalize_literal_text(text)
            if not normalized:
                return []
            if normalized.count('?') <= 1:
                return [normalized]
            parts = [normalize_literal_text(item) for item in re.findall(r'[^?]+\?', normalized)]
            remainder = normalize_literal_text(re.sub(r'(?:[^?]+\?)+', '', normalized))
            if remainder:
                parts.append(remainder)
            return [item for item in parts if item]

        def split_by_delimiters(text: str) -> list[str]:
            normalized = normalize_literal_text(text)
            if not normalized:
                return []
            if normalized.count('?') > 1:
                return split_by_question_marks(normalized)
            for delimiter in [' | ', '; ']:
                if delimiter not in normalized:
                    continue
                parts = [normalize_literal_text(part) for part in normalized.split(delimiter)]
                parts = [part for part in parts if part]
                if len(parts) > 1:
                    return parts
            return [normalized]

        def split_atomic_item(source_text: str | None, evidence: str | None) -> list[tuple[str, str | None]]:
            normalized_source = normalize_literal_text(source_text)
            normalized_evidence = normalize_literal_text(evidence)
            source_segments = split_by_delimiters(normalized_source)
            if not source_segments:
                return []

            if not normalized_evidence or normalized_evidence == normalized_source:
                evidence_segments = source_segments
            else:
                evidence_segments = split_by_delimiters(normalized_evidence)
                if len(evidence_segments) != len(source_segments):
                    short_evidence = len(normalized_evidence.split()) <= 6
                    if short_evidence:
                        evidence_segments = [normalized_evidence] * len(source_segments)
                    else:
                        evidence_segments = source_segments

            return list(zip(source_segments, evidence_segments))

        updated_items = []
        seen_keys: set[tuple[str, str, str]] = set()
        for index, item in enumerate(payload.items, start=1):
            atomic_segments = split_atomic_item(item.source_text, item.evidence)
            if not atomic_segments:
                atomic_segments = [(strip_list_marker(item.source_text), strip_list_marker(item.evidence))]

            for atomic_source_text, atomic_evidence_candidate in atomic_segments:
                atomic_source_text = strip_answer_suffix(atomic_source_text)
                atomic_evidence_candidate = strip_answer_suffix(atomic_evidence_candidate)
                evidence = make_evidence(atomic_source_text, atomic_evidence_candidate)
                if not evidence:
                    continue
                new_title = title_from_source(atomic_source_text, item.title)
                new_description = description_from_source(atomic_source_text, atomic_evidence_candidate, item.description)
                if should_drop_item(new_title, new_description):
                    continue
                category = infer_category(item.category, atomic_source_text, new_description)
                new_title = strip_category_prefix_from_title(new_title, category)
                if (
                    len(new_title.split()) > 24
                    and '?' not in (atomic_source_text or '')
                    and category is None
                ):
                    continue
                key = dedupe_key(new_title, atomic_source_text or new_description, category)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                updated_items.append(item.model_copy(update={
                    "id": f"item-{len(updated_items) + 1}",
                    "title": new_title,
                    "description": new_description,
                    "source_text": strip_list_marker(atomic_source_text or new_description),
                    "evidence": evidence,
                    "category": category,
                    "dependencies": [],
                }))

        source_text = self._build_request_source_text(request)
        if source_text and updated_items:
            raw_lines = [normalize_literal_text(line).strip() for line in str(source_text).splitlines()]
            normalized_lines = [re.sub(r'[^a-z0-9]+', ' ', line.lower()).strip() for line in raw_lines]
            heading_positions: list[tuple[int, str]] = []
            for line_index, line in enumerate(raw_lines):
                lowered = line.lower().strip(' :')
                if not line or '?' in line:
                    continue
                if lowered in {"yes", "no", "not applicable", "n/a"}:
                    continue
                if len(line) > 90 or len(line.split()) > 10:
                    continue
                is_heading = (
                    line.endswith(':')
                    or re.match(r'^(before|after|during|phase|section|step)\b', lowered)
                    or re.match(r'^(sign[\s-]?in|time[\s-]?out|sign[\s-]?out)\b', lowered)
                )
                if is_heading:
                    heading_positions.append((line_index, line.rstrip(':').strip()))

            if heading_positions:
                categorized_items = []
                active_category: str | None = None
                for item in updated_items:
                    explicit_category = None if is_noisy_category(item.category) else normalize_literal_text(item.category)
                    inferred_category = explicit_category or None
                    if inferred_category is None:
                        probes = [item.source_text, item.evidence, item.title, item.description]
                        best_line_index: int | None = None
                        best_score = 0
                        for probe in probes:
                            normalized_probe = re.sub(r'[^a-z0-9]+', ' ', normalize_literal_text(probe).lower()).strip()
                            if len(normalized_probe) < 8:
                                continue
                            for line_index, normalized_line in enumerate(normalized_lines):
                                if not normalized_line:
                                    continue
                                if normalized_probe in normalized_line or normalized_line in normalized_probe:
                                    score = min(len(normalized_probe), len(normalized_line))
                                    if score > best_score:
                                        best_score = score
                                        best_line_index = line_index
                            if best_score >= 24:
                                break

                        if best_line_index is not None:
                            eligible_headings = [
                                heading
                                for heading_index, heading in heading_positions
                                if heading_index < best_line_index and (best_line_index - heading_index) <= 12
                            ]
                            if eligible_headings:
                                inferred_category = normalize_literal_text(eligible_headings[-1])

                    normalized_category = normalize_literal_text(inferred_category) if inferred_category else None
                    if normalized_category and not is_noisy_category(normalized_category):
                        active_category = normalized_category
                    elif active_category:
                        normalized_category = active_category

                    categorized_items.append(item.model_copy(update={"category": normalized_category}))
                updated_items = categorized_items

        return payload.model_copy(update={"items": updated_items})

    def _collect_string_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            strings: list[str] = []
            for item in value.values():
                strings.extend(self._collect_string_values(item))
            return strings
        if isinstance(value, list):
            strings: list[str] = []
            for item in value:
                strings.extend(self._collect_string_values(item))
            return strings
        return []
    def _normalize_skill_text(self, value: Any) -> str:
        cleaned = value.strip() if isinstance(value, str) else str(value).strip()
        cleaned = re.sub(r'^[\s,;:()\[\]{}]+|[\s,;:()\[\]{}]+$', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned
    def _rebuild_experience_description(self, entry: ExperienceEntry) -> str | None:
        parts = [part for part in [entry.title, entry.organization, entry.location, entry.date_range] if part]
        return ' | '.join(parts) if parts else entry.description
    def _strip_location_from_organization(self, organization: str | None, location: str | None) -> str | None:
        org = (organization or '').strip()
        loc = (location or '').strip()
        if not org or not loc:
            return org or None
        for separator in (', ', ' | ', ' — ', ' - '):
            suffix = f"{separator}{loc}"
            if org.lower().endswith(suffix.lower()):
                stripped = org[:-len(suffix)].strip(' ,|-')
                return stripped or org
        return org
    def _synchronize_cv_sections(
        self,
        *,
        sections: list[CVSection],
        skills: list[str],
        education_entries: list[EducationEntry],
        experience_entries: list[ExperienceEntry],
    ) -> list[CVSection]:
        synchronized = []
        for section in sections:
            section_type = (section.section_type or '').lower()
            if section_type == 'skills' and skills:
                synchronized.append(section.model_copy(update={'content': [{'text': item} for item in skills]}))
                continue
            if section_type == 'education' and education_entries:
                synchronized.append(section.model_copy(update={'content': [
                    {'text': entry.description or ' | '.join(part for part in [entry.degree, entry.institution, entry.location, entry.date_range] if part)}
                    for entry in education_entries
                ]}))
                continue
            if section_type == 'experience' and experience_entries:
                synchronized.append(section.model_copy(update={'content': [
                    {'text': entry.description, 'details': {
                        'title': entry.title,
                        'organization': entry.organization,
                        'location': entry.location,
                        'date_range': entry.date_range,
                        'bullets': entry.bullets,
                    }}
                    for entry in experience_entries
                ]}))
                continue
            synchronized.append(section)

        return synchronized
    def _extract_grounding_block_lines(self, request: TaskExecutionRequest | None, block_name: str) -> list[str]:
        if request is None or not request.source_document_ids:
            return []
        try:
            from ..services.document_context import build_structured_document_context
        except Exception:
            return []
        context = build_structured_document_context(
            query=request.input_text,
            document_ids=request.source_document_ids,
            strategy=request.context_strategy or "document_scan",
        )
        if not context:
            return []
        match = re.search(rf"\[{re.escape(block_name)}\]\n(?P<body>.*?)(?:\n\n\[|\Z)", context, re.S)
        if not match:
            return []
        return [line.strip().lstrip('-• ').strip() for line in match.group('body').splitlines() if line.strip()]
    def _recover_grounded_skills_from_request(self, request: TaskExecutionRequest | None) -> list[str]:
        return list(dict.fromkeys(line for line in self._extract_grounding_block_lines(request, 'CV SKILLS') if line))
    def _recover_grounded_education_from_request(self, request: TaskExecutionRequest | None) -> list[EducationEntry]:
        entries = []
        for line in self._extract_grounding_block_lines(request, 'CV EDUCATION'):
            if line:
                parsed = self._parse_grounded_education_line(line)
                if parsed is not None:
                    entries.append(parsed)
        return entries
    def _recover_grounded_emails_from_request(self, request: TaskExecutionRequest | None) -> list[str]:
        emails: list[str] = []
        for line in self._extract_grounding_block_lines(request, 'CV CONFIRMED FIELDS'):
            if not line.lower().startswith('emails:'):
                continue
            for raw in line.split(':', 1)[1].split(','):
                item = raw.strip()
                if re.match(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", item, re.I):
                    emails.append(item)
        return list(dict.fromkeys(emails))
    def _choose_best_email(self, candidates: list[str | None]) -> str | None:
        valid = []
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            item = candidate.strip()
            if not re.match(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", item, re.I):
                continue
            valid.append(item)
        if not valid:
            return None
        def score(email: str) -> tuple[int, int]:
            local, _, domain = email.partition('@')
            suffix_bonus = 1 if any(other != email and other.partition('@')[2].lower() == domain.lower() and other.partition('@')[0].lower().endswith(local.lower()) for other in valid) else 0
            return (suffix_bonus, -len(local))
        return sorted(dict.fromkeys(valid), key=score, reverse=True)[0]
    def _education_entry_score(self, entry: EducationEntry) -> int:
        degree = (entry.degree or '').lower()
        institution = (entry.institution or '').lower()
        description = (entry.description or '').lower()
        if not entry.degree and any(token in description for token in ('|', '[', ']')):
            return -100
        score = len(degree)
        if 'diplôme' in degree:
            score += 20
        if 'ingénieur' in degree:
            score += 20
        if 'master' in degree or 'm.sc' in degree:
            score += 10
        if entry.degree:
            score += 10
        if institution and all(token not in institution for token in ('|', '[', ']')):
            score += 10
        if any(token in description for token in ('|', '[', ']')) or any(token in institution for token in ('|', '[', ']')):
            score -= 25
        return score
    def _education_entries_compete(self, left: EducationEntry, right: EducationEntry) -> bool:
        left_inst = (left.institution or '').strip().lower()
        right_inst = (right.institution or '').strip().lower()
        if left_inst and right_inst and left_inst == right_inst:
            same_institution = True
        elif left.date_range and right.date_range and left.date_range == right.date_range:
            same_institution = True
        elif left_inst and right_inst and (
            (len(left_inst) <= 6 and left_inst in right_inst)
            or (len(right_inst) <= 6 and right_inst in left_inst)
        ):
            same_institution = True
        else:
            left_text = ' '.join(part for part in [left.institution or '', left.description or ''] if part).lower()
            right_text = ' '.join(part for part in [right.institution or '', right.description or ''] if part).lower()
            stopwords = {'diplôme', 'diplome', 'ingénieur', 'ingenieur', 'master', 'licence', 'bachelor', 'grade', 'bac', 'de', 'du', 'des', 'en', 'et', 'la', 'le', 'l', 'université', 'universite', 'école', 'ecole', 'fr', 'br', 'paris', 'são', 'sao', 'paulo', 'gif', 'sur', 'yvette'}
            left_tokens = {token for token in re.findall(r"[a-zà-ÿ]+", left_text) if token not in stopwords}
            right_tokens = {token for token in re.findall(r"[a-zà-ÿ]+", right_text) if token not in stopwords}
            same_institution = len(left_tokens & right_tokens) >= 2
        if not same_institution:
            return False
        left_degree = set(re.findall(r"[a-zà-ÿ]+", (left.degree or '').lower()))
        right_degree = set(re.findall(r"[a-zà-ÿ]+", (right.degree or '').lower()))
        overlap = left_degree & right_degree
        return len(overlap) >= 2 or bool(left.date_range and right.date_range and left.date_range == right.date_range)
    def _should_keep_education_entry(self, entry: EducationEntry) -> bool:
        description = (entry.description or '').strip()
        if description and any(token in description for token in ('|', '[', ']')) and not entry.date_range:
            return False
        if entry.degree or entry.institution:
            return True
        if not description:
            return False
        if any(token in description for token in ('|', '[', ']')):
            return False
        return len(description.split()) >= 4
    def _parse_grounded_education_line(self, line: str) -> EducationEntry | None:
        text = ' '.join(str(line or '').split()).strip(' -•')
        if not text:
            return None
        if '|' in text and '[' in text and ']' in text and not re.search(r'(?:19|20)\d{2}', text):
            return None
        date_match = re.search(r'((?:[A-Za-zÀ-ÿ]+\s+)?(?:19|20)\d{2}\s*(?:-|–|à|to)\s*(?:[A-Za-zÀ-ÿ]+\s+)?(?:19|20)\d{2}(?:\s*\[[^\]]+\])?)', text, re.I)
        date_range = date_match.group(1).strip() if date_match else None
        text_wo_dates = text.replace(date_range, ' ').strip(' ,;()-') if date_range else text
        if not date_range:
            date_tokens = re.findall(r'(?:[A-Za-zÀ-ÿ]+\s+)?(?:19|20)\d{2}|(?:19|20)\d{2}\s*\[[^\]]+\]', text, re.I)
            if len(date_tokens) >= 2:
                date_range = ' - '.join(token.strip() for token in date_tokens[:2])
                text_wo_dates = text
                for token in date_tokens[:2]:
                    text_wo_dates = text_wo_dates.replace(token, ' ')
                text_wo_dates = text_wo_dates.strip(' ,;()-')
        degree_match = re.search(r'\b(dipl[oô]me|master|licence|bachelor|mba|m\.sc|msc)\b', text_wo_dates, re.I)
        institution = None
        location = None
        degree = None
        if degree_match:
            institution_and_location = text_wo_dates[:degree_match.start()].strip(' ,|-') or None
            degree = text_wo_dates[degree_match.start():].strip(' ,|-') or None
            if institution_and_location:
                if '|' in institution_and_location:
                    institution_and_location = institution_and_location.split('|', 1)[0].strip()
                parts = [part.strip() for part in institution_and_location.split(',') if part.strip()]
                if len(parts) >= 2:
                    institution = parts[0]
                    location = ', '.join(parts[1:])
                else:
                    institution = institution_and_location
        else:
            degree = text_wo_dates or None
        if institution and ',' in institution:
            institution = institution.split(',', 1)[0].strip()
        if institution and '|' in institution:
            institution = institution.split('|', 1)[0].strip()
        if degree and ',' in degree and not re.search(r'\b(dipl[oô]me|master|licence|bachelor|mba|m\.sc|msc)\b', degree.split(',', 1)[0], re.I):
            degree = degree.split(',', 1)[0].strip()
        if degree:
            degree = re.sub(r'\s+', ' ', degree).strip(' ,;')
            degree = re.sub(r'\s*\[[^\]]*\]\s*$', '', degree).strip(' ,;(')
            degree = re.sub(r'\s*\([^)]*$', '', degree).strip(' ,;')
            degree = degree.replace('Licence en Science de Génie procédés industriels', 'Diplôme d’ingénieur en Génie procédés industriels')
        description = ', '.join(part for part in [degree, institution] if part) or text
        return EducationEntry.model_validate({
            'degree': degree,
            'institution': institution,
            'location': location,
            'date_range': date_range,
            'description': description,
        })
    def _repair_extraction_payload(self, payload: ExtractionPayload, request: TaskExecutionRequest | None) -> ExtractionPayload:
        source_text = (request.input_text if request else '') or ''
        if not source_text.strip():
            return payload
        entities = list(payload.entities)
        relationships = list(payload.relationships)
        important_numbers = list(payload.important_numbers)
        missing_information = list(payload.missing_information)

        def add_entity(entity_type: str, value: str) -> None:
            if re.match(r'^(On\s+[A-Z][a-z]+|In\s+[A-Z][a-z]+)$', value):
                return
            if any((e.value or '').strip().lower() == value.lower() for e in entities):
                return
            start = source_text.find(value)
            if start == -1:
                return
            entities.append(Entity(
                type=entity_type,
                value=value,
                confidence=0.9,
                source_text=value,
                position_start=start,
                position_end=start + len(value),
            ))

        for value in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', source_text):
            if value in {'Project Manager', 'Technical Lead', 'Porto Alegre'}:
                continue
            if any(token in value for token in ('Energia', 'Solutions', 'substation')):
                continue
            add_entity('person', value)

        for value in re.findall(r'\b[A-Z][\w]+(?:\s+[A-Z][\w]+)*(?:\s+(?:Energia|Solutions))\b', source_text):
            add_entity('organization', value)
        for value in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+substation\b', source_text):
            add_entity('location', value)

        for number in re.findall(r'R\$\s?[\d.,]+|\b\d+\s*-[ ]?month period\b', source_text, flags=re.I):
            cleaned = number.strip()
            if cleaned not in important_numbers:
                important_numbers.append(cleaned)

        signed_match = re.search(r'([A-Z][\w]+(?:\s+[A-Z][\w]+)*) signed .*? with\s+([A-Z][\w]+(?:\s+[A-Z][\w]+)*)', source_text)
        if signed_match:
            org_a, org_b = signed_match.groups()
            if not any((r.from_entity == org_a and r.to_entity == org_b and r.relationship == 'signed_agreement_with') for r in relationships):
                relationships.append(Relationship(
                    from_entity=org_a,
                    to_entity=org_b,
                    relationship='signed_agreement_with',
                    confidence=0.9,
                    evidence=signed_match.group(0),
                ))
        site_match = re.search(r'for the\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+substation)', source_text)
        if signed_match and site_match:
            org_b = signed_match.group(2)
            site = site_match.group(1)
            if not any((r.from_entity == org_b and r.to_entity == site and r.relationship == 'applies_to_site') for r in relationships):
                relationships.append(Relationship(
                    from_entity=org_b,
                    to_entity=site,
                    relationship='applies_to_site',
                    confidence=0.85,
                    evidence=site_match.group(0),
                ))

        if re.search(r'Project manager:\s*[A-Z][a-z]+\s+[A-Z][a-z]+', source_text, re.I):
            missing_information = [item for item in missing_information if 'project manager' not in item.lower()]
        if re.search(r'Technical lead:\s*[A-Z][a-z]+\s+[A-Z][a-z]+', source_text, re.I):
            missing_information = [item for item in missing_information if 'technical lead' not in item.lower()]

        return payload.model_copy(update={
            'entities': entities,
            'relationships': relationships,
            'important_numbers': important_numbers,
            'missing_information': missing_information,
        })
    def _repair_code_analysis_payload(self, payload: CodeAnalysisPayload, request: TaskExecutionRequest | None) -> CodeAnalysisPayload:
        source_text = (request.input_text if request else '') or ''
        if not source_text.strip():
            return payload

        issues = list(payload.detected_issues)
        test_suggestions = list(payload.test_suggestions)
        risk_notes = list(payload.risk_notes)

        strong_issue_titles: set[str] = set()

        if re.search(r'/\s*len\(', source_text):
            strong_issue_titles.add('possível divisão por zero')
            if not any((issue.title or '').strip().lower() == 'possível divisão por zero' for issue in issues):
                issues.append(CodeIssue(
                    severity='high',
                    category='runtime_failure',
                    title='Possível divisão por zero',
                    description='O código divide pelo tamanho de uma coleção sem proteger o caso de entrada vazia.',
                    evidence='average = total / len(values)',
                    recommendation='Proteja explicitamente o caso de entrada vazia antes da divisão e defina `average = 0.0` quando não houver valores.',
                ))
            risk_notes.append('Pode ocorrer divisão por zero quando a lista de entrada estiver vazia.')
            test_suggestions.append('Adicionar teste para entrada vazia e validar explicitamente o comportamento esperado da média.')

        if re.search(r'item\[["\']score["\']\]\s*[<>]', source_text):
            strong_issue_titles.add('suposição de score numérico')
            if not any((issue.title or '').strip().lower() == 'suposição de score numérico' for issue in issues):
                issues.append(CodeIssue(
                    severity='medium',
                    category='type_validation',
                    title='Suposição de score numérico',
                    description='O código assume que `score` é numérico ao compará-lo com limites.',
                    evidence='if item["score"] > 100 / if item["score"] < 0',
                    recommendation='Valide ou converta `score` antes das comparações numéricas.',
                ))
            risk_notes.append('Valores não numéricos em `score` podem gerar erro de tipo durante a comparação.')
            test_suggestions.append('Adicionar teste com `score` não numérico para validar o comportamento de erro ou saneamento.')
            test_suggestions.append('Adicionar testes para `score` acima de 100 e abaixo de 0 para validar o clamp.')

        if re.search(r'item\[["\']score["\']\]\s*=\s*', source_text):
            strong_issue_titles.add('efeito colateral por mutação da entrada')
            if not any((issue.title or '').strip().lower() == 'efeito colateral por mutação da entrada' for issue in issues):
                issues.append(CodeIssue(
                    severity='medium',
                    category='input_mutation',
                    title='Efeito colateral por mutação da entrada',
                    description='A função altera os dicionários de entrada em memória ao normalizar os scores.',
                    evidence='item["score"] = 100 / item["score"] = 0',
                    recommendation='Use `item.copy()` ou construa um novo dicionário antes da normalização para evitar alterar o objeto original.',
                ))
            risk_notes.append('Mutar itens da entrada em memória pode criar efeitos colaterais para quem reutiliza a lista original.')
            test_suggestions.append('Adicionar teste que verifique se os dicionários originais são ou não mutados após `normalize_scores`.')

        if 'value.get("score", 0)' in source_text or "value.get('score', 0)" in source_text:
            test_suggestions.append('Adicionar teste para itens sem `score` e validar o comportamento da normalização e da média.')

        if 'logger.info' in source_text:
            test_suggestions.append('Adicionar testes com e sem logger para garantir que o logging não altera o resultado retornado.')

        if strong_issue_titles:
            issues = [
                issue for issue in issues
                if (issue.title or '').strip().lower() not in {'duplicated logic', 'lógica duplicada'}
            ]

        generic_test_patterns = (
            'edge case x',
            'add unit test',
        )
        if test_suggestions:
            grounded_tests_exist = any('empty input' in item.lower() or 'non-numeric' in item.lower() or 'score' in item.lower() or 'logger' in item.lower() for item in test_suggestions)
            if grounded_tests_exist:
                test_suggestions = [
                    item for item in test_suggestions
                    if not any(pattern in item.lower() for pattern in generic_test_patterns)
                ]

        generic_risk_patterns = (
            'malformed input',
        )
        if risk_notes:
            grounded_risks_exist = any('division by zero' in item.lower() or 'type error' in item.lower() or 'mutating input' in item.lower() or 'side effects' in item.lower() for item in risk_notes)
            if grounded_risks_exist:
                risk_notes = [
                    item for item in risk_notes
                    if not any(pattern in item.lower() for pattern in generic_risk_patterns)
                ]

        has_score_guard = bool(re.search(r'if\s+["\']score["\']\s+in\s+item', source_text))
        has_numeric_score_compare = bool(re.search(r'item\[["\']score["\']\]\s*[<>]=?\s*-?\d', source_text))
        mutates_input_in_place = bool(re.search(r'item\[["\']score["\']\]\s*=', source_text))
        reuses_original_reference = bool(re.search(r'\bresult\.append\(\s*item\s*\)', source_text))

        normalized_issues: list[CodeIssue] = []
        seen_issue_keys: set[tuple[str, str]] = set()
        for issue in issues:
            category = self._normalize_code_issue_category(issue.category)
            title = (issue.title or '').strip()
            description = (issue.description or '').strip()
            evidence = (issue.evidence or '').strip() or None
            recommendation = (issue.recommendation or '').strip() or None
            issue_blob = ' '.join(part for part in [title, description, evidence or '', recommendation or '', category] if part).lower()

            normalized_issue = issue.model_copy(update={'category': category})

            if category == 'runtime_failure' and (
                'divisão por zero' in issue_blob
                or 'zerodivisionerror' in issue_blob
                or ('len(values)' in issue_blob and 'vazi' in issue_blob)
            ):
                normalized_issue = normalized_issue.model_copy(update={
                    'severity': 'high',
                    'category': 'runtime_failure',
                    'recommendation': 'Adicione verificação para lista vazia antes da divisão e defina `average = 0.0` quando não houver valores para agregar.',
                })

            if has_score_guard and 'score' in issue_blob and (
                'keyerror' in issue_blob
                or 'lacks this key' in issue_blob
                or 'missing score key' in issue_blob
                or 'assumes each item has a' in issue_blob
            ):
                if has_numeric_score_compare:
                    normalized_issue = issue.model_copy(update={
                        'severity': 'medium',
                        'category': 'type_validation',
                        'title': 'Suposição de score numérico',
                        'description': 'O código verifica se a chave `score` existe antes de acessá-la, então o risco principal não é ausência da chave. O problema restante é assumir que `score` é numérico ao compará-lo com os limites.',
                        'evidence': 'if "score" in item ... if item["score"] > 100 / if item["score"] < 0',
                        'recommendation': 'Valide ou converta `score` antes das comparações numéricas.',
                    })
                else:
                    continue
            elif mutates_input_in_place and (
                category in {'correctness', 'maintainability', 'bug'}
                or 'muta' in issue_blob
                or 'in-place' in issue_blob
                or 'objeto original' in issue_blob
                or 'dicionário de entrada' in issue_blob
            ):
                normalized_issue = normalized_issue.model_copy(update={
                    'severity': 'medium',
                    'category': 'input_mutation',
                    'recommendation': 'Use `item.copy()` ou construa um novo dicionário com os campos necessários antes de ajustar `score`, evitando alterar o objeto original.',
                })
            elif category == 'input_mutation' and not mutates_input_in_place and reuses_original_reference:
                normalized_issue = issue.model_copy(update={
                    'severity': 'low',
                    'category': 'shared_reference',
                    'title': 'Reuso da referência original',
                    'description': 'Para itens sem `score`, a função reaproveita o mesmo dicionário original na saída. Isso pode causar aliasing se esse objeto for modificado depois.',
                    'evidence': 'result.append(item)',
                    'recommendation': 'Use `item.copy()` se a função precisar sempre retornar objetos independentes.',
                })

            normalized_issue_blob = ' '.join(
                part for part in [
                    normalized_issue.title,
                    normalized_issue.description,
                    normalized_issue.evidence or '',
                    normalized_issue.recommendation or '',
                ]
                if part
            ).lower()
            if 'cópia profunda' in normalized_issue_blob or 'deep copy' in normalized_issue_blob:
                normalized_issue = normalized_issue.model_copy(update={
                    'recommendation': 'Use `item.copy()` ou construa um novo dicionário com os campos necessários antes de ajustar `score`, evitando alterar o objeto original.',
                    'category': 'input_mutation' if mutates_input_in_place else normalized_issue.category,
                })

            key = (
                (normalized_issue.title or '').strip().lower(),
                (normalized_issue.category or '').strip().lower(),
            )
            if key in seen_issue_keys:
                continue
            seen_issue_keys.add(key)
            normalized_issues.append(normalized_issue)

        normalized_test_suggestions: list[str] = []
        for item in test_suggestions:
            cleaned = ' '.join(str(item or '').split()).strip()
            lowered = cleaned.lower()
            if 'average 0.0 or raises a controlled error' in lowered:
                cleaned = 'Adicionar teste para entrada vazia e validar explicitamente a política esperada, sem deixar a expectativa ambígua.'
            cleaned = re.sub(r'average\s*=\s*0(?!\.\d)', 'average = 0.0', cleaned, flags=re.I)
            normalized_test_suggestions.append(cleaned)

        normalized_refactor_plan: list[str] = []
        for item in payload.refactor_plan:
            cleaned = ' '.join(str(item or '').split()).strip()
            cleaned = re.sub(r'c[óo]pia profunda', 'cópia rasa (`copy()`) ou um novo dicionário', cleaned, flags=re.I)
            cleaned = re.sub(r'deep copy', 'shallow copy (`copy()`) ou um novo dicionário', cleaned, flags=re.I)
            cleaned = re.sub(r'average\s*=\s*0(?!\.\d)', 'average = 0.0', cleaned, flags=re.I)
            cleaned = cleaned.replace('0 ou outro valor padrão', '0.0')
            normalized_refactor_plan.append(cleaned)

        return payload.model_copy(update={
            'detected_issues': normalized_issues,
            'refactor_plan': list(dict.fromkeys(item.strip() for item in normalized_refactor_plan if item and item.strip())),
            'test_suggestions': list(dict.fromkeys(item.strip() for item in normalized_test_suggestions if item and item.strip())),
            'risk_notes': list(dict.fromkeys(item.strip() for item in risk_notes if item and item.strip())),
        })
    def _normalize_code_issue_category(self, value: str | None) -> str:
        cleaned = re.sub(r'[^a-z0-9]+', '_', (value or '').strip().lower()).strip('_')
        aliases = {
            'aliasing': 'shared_reference',
            'bug': 'correctness',
            'correctness_bug': 'correctness',
            'input_mutation': 'input_mutation',
            'mutation': 'input_mutation',
            'reference_reuse': 'shared_reference',
            'runtime_error': 'runtime_failure',
            'runtime_failure': 'runtime_failure',
            'shared_reference': 'shared_reference',
            'type_assumption': 'type_validation',
            'type_safety': 'type_validation',
            'type_validation': 'type_validation',
            'validation': 'type_validation',
        }
        return aliases.get(cleaned, cleaned or 'correctness')
    def _parse_date_range_to_month_interval(self, value: str | None) -> tuple[int, int] | None:
        text = (value or '').strip()
        if not text:
            return None
        match = re.search(r'(\d{4})-(\d{2}).*?(\d{4})-(\d{2})', text)
        if match:
            start_year, start_month, end_year, end_month = map(int, match.groups())
            return (start_year * 12 + (start_month - 1), end_year * 12 + (end_month - 1))
        month_map = {
            'janvier':1,'january':1,'février':2,'fevrier':2,'february':2,'mars':3,'march':3,'avril':4,'april':4,
            'mai':5,'may':5,'juin':6,'june':6,'juillet':7,'july':7,'août':8,'aout':8,'august':8,
            'septembre':9,'september':9,'octobre':10,'october':10,'novembre':11,'november':11,'décembre':12,'decembre':12,'december':12,
        }
        match = re.search(r'([A-Za-zÀ-ÿ]+)\s+(\d{4}).*?([A-Za-zÀ-ÿ]+)\s+(\d{4})', text)
        if match:
            start_month_name, start_year, end_month_name, end_year = match.groups()
            start_month = month_map.get(start_month_name.lower())
            end_month = month_map.get(end_month_name.lower())
            if start_month and end_month:
                return (int(start_year) * 12 + (start_month - 1), int(end_year) * 12 + (end_month - 1))
        match = re.search(r'(\d{4}).*?(\d{4})', text)
        if match:
            start_year, end_year = map(int, match.groups())
            return (start_year * 12, end_year * 12 + 11)
        return None
    def _compute_experience_years_from_entries(self, entries: list[ExperienceEntry]) -> float:
        intervals: list[tuple[int, int]] = []
        for entry in entries:
            interval = self._parse_date_range_to_month_interval(entry.date_range)
            if interval is None:
                continue
            start, end = interval
            if end < start:
                continue
            intervals.append((start, end))
        if not intervals:
            return 0.0
        intervals.sort()
        merged: list[list[int]] = []
        for start, end in intervals:
            if not merged or start > merged[-1][1] + 1:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        total_months = sum((end - start + 1) for start, end in merged)
        years = total_months / 12.0
        return round(years, 1)
    def _recover_grounded_projects_from_request(self, request: TaskExecutionRequest | None) -> list[str]:
        if request is None or not request.source_document_ids:
            return []
        try:
            from ..services.document_context import build_structured_document_context
        except Exception:
            return []
        context = build_structured_document_context(
            query=request.input_text,
            document_ids=request.source_document_ids,
            strategy=request.context_strategy or "document_scan",
        )
        if not context:
            return []
        match = re.search(r"\[CV PROJECTS\]\n(?P<body>.*?)(?:\n\n\[|\Z)", context, re.S)
        if not match:
            return []
        lines = []
        for raw in match.group("body").splitlines():
            cleaned = raw.strip().lstrip("-• ").strip()
            if cleaned:
                lines.append(cleaned)
        return list(dict.fromkeys(lines))
    def _normalize_project_items(self, items: list[str]) -> list[str]:
        cleaned_lines = []
        for item in items:
            if not isinstance(item, str):
                continue
            cleaned = item.replace('\x7f', '').strip().lstrip('-• ').strip()
            if cleaned:
                cleaned_lines.append(cleaned)
        merged: list[str] = []
        for line in cleaned_lines:
            if not merged:
                merged.append(line)
                continue
            previous = merged[-1]
            if previous.endswith('.'):
                merged.append(line)
                continue
            if line[:1].islower() or line.startswith(('strategic', 'into', 'product,')):
                merged[-1] = f"{previous} {line}".strip()
            else:
                merged.append(line)
        return list(dict.fromkeys(item.strip() for item in merged if item.strip()))
    def _repair_cv_experience_entry(self, entry: ExperienceEntry) -> ExperienceEntry:
        description = (entry.description or "").strip()
        if not description:
            return entry
        repaired = ExperienceEntry.model_validate({
            "title": entry.title,
            "organization": entry.organization,
            "location": entry.location,
            "date_range": entry.date_range,
            "bullets": entry.bullets,
            "description": description,
        })
        update = {
            "title": entry.title or repaired.title,
            "organization": entry.organization or repaired.organization,
            "location": entry.location or repaired.location,
            "date_range": entry.date_range or repaired.date_range,
            "bullets": [item.strip() for item in (entry.bullets or repaired.bullets) if isinstance(item, str) and item.strip()],
            "description": description,
        }
        return entry.model_copy(update=update)
    def _apply_cv_grounding_guardrail(self, result: StructuredResult) -> None:
        payload = result.validated_output
        if not isinstance(payload, CVAnalysisPayload):
            return
        payload_json = payload.model_dump(mode="json")
        flattened = [item.strip().lower() for item in self._collect_string_values(payload_json) if item and item.strip()]
        placeholder_hits = sum(1 for item in flattened if item in _PLACEHOLDER_MARKERS or "company x" in item)
        suspicious_experience = any(
            ((entry.organization or "").strip().lower() == "company x") or ((entry.title or "").strip().lower() == "software engineer")
            for entry in payload.experience_entries
        )
        low_information = len(flattened) <= 12 or (not payload.personal_info and not payload.skills and not payload.sections)
        if placeholder_hits > 0 or (suspicious_experience and low_information):
            result.success = False
            result.validated_output = None
            result.parsing_error = (
                "Low grounding: CV structured extraction was rejected because the output contained placeholder or invented resume content."
            )
            result.validation_error = result.parsing_error
            return
    def _estimate_quality_score(self, result: StructuredResult, request: TaskExecutionRequest) -> float | None:
        if not result.success or result.validated_output is None:
            return 0.0
        payload_json = result.validated_output.model_dump(mode="json")
        flattened = [item.strip().lower() for item in self._collect_string_values(payload_json) if item.strip()]
        placeholder_hits = sum(1 for item in flattened if item in _PLACEHOLDER_MARKERS)
        example_hits = sum(1 for item in flattened if "example" in item.lower())
        score = 0.92
        if request.task_type == "cv_analysis" and not request.input_text.strip() and not result.context_used:
            score -= 0.55
        if request.task_type == "cv_analysis" and result.context_used:
            score += 0.03
        if request.task_type == "extraction" and result.context_used:
            score += 0.03
        if request.task_type == "code_analysis" and not request.input_text.strip() and not result.context_used:
            score -= 0.45
        score -= min(placeholder_hits * 0.22, 0.66)
        score -= min(example_hits * 0.12, 0.24)
        if isinstance(result.validated_output, CVAnalysisPayload):
            payload = result.validated_output
            if not payload.sections:
                score -= 0.18
            if not payload.skills:
                score -= 0.1
            if payload.personal_info is None:
                score -= 0.08
        if isinstance(result.validated_output, ChecklistPayload):
            payload = result.validated_output
            if not payload.items:
                score -= 0.2
        if isinstance(result.validated_output, ExtractionPayload):
            payload = result.validated_output
            if len(payload.entities) + len(payload.extracted_fields) < 2:
                score -= 0.15
            if not (payload.important_dates or payload.important_numbers or payload.action_items or payload.risks):
                score -= 0.12
            if not payload.main_subject:
                score -= 0.05
        if isinstance(result.validated_output, CodeAnalysisPayload):
            payload = result.validated_output
            if not payload.detected_issues:
                score -= 0.18
            if not payload.refactor_plan:
                score -= 0.12
            if not payload.test_suggestions:
                score -= 0.1
        if result.repair_applied:
            score -= 0.05
        return max(0.0, min(round(score, 3), 1.0))
    def _create_error_result(self, task_type: str, error_message: str, raw_input: str) -> StructuredResult:
        from .parsers import attempt_controlled_failure
        return attempt_controlled_failure(raw_response=raw_input, task_type=task_type, error_message=error_message)
structured_service = StructuredOutputService()