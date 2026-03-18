"""Service layer for structured outputs."""
from __future__ import annotations
from typing import Any
from ..config import get_ollama_settings
from .base import ActionItem, ChecklistPayload, CVAnalysisPayload, CodeAnalysisPayload, ExtractionPayload, RiskItem, EducationEntry, ExperienceEntry
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
class StructuredOutputService:
    """Service for executing structured output tasks."""
    def __init__(self) -> None:
        self.task_registry = task_registry
        self.ollama_settings = get_ollama_settings()
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
        model = request.model or task_definition.default_model or self.ollama_settings.default_model
        temperature = request.temperature if request.temperature is not None else task_definition.default_temperature
        context_window = request.context_window or self.ollama_settings.default_context_window
        execution_request = request.model_copy(
            update={
                "model": model,
                "temperature": temperature,
                "context_window": context_window,
            }
        )
        try:
            result = handler.execute(execution_request)
            result.context_used = (execution_request.use_document_context or execution_request.use_rag_context) and bool(execution_request.source_document_ids)
            result.source_documents = list(execution_request.source_document_ids)
            if result.primary_render_mode is None:
                result.primary_render_mode = task_definition.primary_render_mode
            self._normalize_result_payload(result)
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
    def _normalize_result_payload(self, result: StructuredResult) -> None:
        payload = result.validated_output
        if payload is None:
            return
        if isinstance(payload, ChecklistPayload):
            total_items = len(payload.items)
            completed_items = sum(1 for item in payload.items if item.status == "completed")
            progress_percentage = round((completed_items / total_items) * 100.0, 1) if total_items else 0.0
            result.validated_output = payload.model_copy(
                update={
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
                cleaned = item.strip() if isinstance(item, str) else str(item).strip()
                if not cleaned:
                    continue
                key = cleaned.lower()
                if key not in seen_skills:
                    seen_skills.add(key)
                    unique_skills.append(cleaned)
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
            experience_entries = list(payload.experience_entries)
            for section in payload.sections:
                section_type = (section.section_type or '').lower()
                section_title = (section.title or '').lower()
                is_education = section_type == 'education' or 'education' in section_title or 'academic' in section_title
                is_languages = section_type == 'languages' or 'language' in section_title
                is_experience = section_type == 'experience' or 'experience' in section_title or 'employment' in section_title or 'work history' in section_title
                is_skills = section_type == 'skills' or 'skill' in section_title
                for item in section.content:
                    if is_skills:
                        source = item.text or ', '.join(str(v) for v in item.details.values() if isinstance(v, str))
                        for token in [x.strip() for x in str(source).replace('\n', ',').split(',') if x.strip()]:
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
            dedup_education = []
            seen_education = set()
            for entry in education_entries:
                key = '|'.join([
                    (entry.degree or '').strip().lower(),
                    (entry.institution or '').strip().lower(),
                    (entry.date_range or '').strip().lower(),
                    (entry.description or '').strip().lower(),
                ])
                if key.strip('|') and key not in seen_education:
                    seen_education.add(key)
                    dedup_education.append(entry)
            dedup_experience = []
            seen_experience = set()
            for entry in experience_entries:
                key = '|'.join([
                    (entry.title or '').strip().lower(),
                    (entry.organization or '').strip().lower(),
                    (entry.date_range or '').strip().lower(),
                    (entry.description or '').strip().lower(),
                ])
                if key.strip('|') and key not in seen_experience:
                    seen_experience.add(key)
                    dedup_experience.append(entry)
            unique_strengths = list(dict.fromkeys(item.strip() for item in payload.strengths if item and item.strip()))
            unique_improvements = list(dict.fromkeys(item.strip() for item in payload.improvement_areas if item and item.strip()))
            result.validated_output = payload.model_copy(
                update={
                    "skills": unique_skills,
                    "languages": unique_languages,
                    "education_entries": dedup_education,
                    "experience_entries": dedup_experience,
                    "strengths": unique_strengths,
                    "improvement_areas": unique_improvements,
                }
            )
        if isinstance(result.validated_output, ExtractionPayload):
            payload = result.validated_output
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
            payload = result.validated_output
            result.validated_output = payload.model_copy(
                update={
                    "readability_improvements": list(dict.fromkeys(item.strip() for item in payload.readability_improvements if item and item.strip())),
                    "maintainability_improvements": list(dict.fromkeys(item.strip() for item in payload.maintainability_improvements if item and item.strip())),
                    "refactor_plan": list(dict.fromkeys(item.strip() for item in payload.refactor_plan if item and item.strip())),
                    "test_suggestions": list(dict.fromkeys(item.strip() for item in payload.test_suggestions if item and item.strip())),
                    "risk_notes": list(dict.fromkeys(item.strip() for item in payload.risk_notes if item and item.strip())),
                }
            )
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