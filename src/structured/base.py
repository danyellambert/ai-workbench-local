"""Base schemas and types for structured outputs."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class BaseTaskPayload(BaseModel):
    """Base class for task-specific payload schemas containing only business content."""

    task_type: str = Field(description="Type of the structured task")
    schema_version: str = Field(default="1.0", description="Schema version")


class Entity(BaseModel):
    """Entity extracted with type and evidence."""

    type: str = Field(description="Type of entity (e.g., person, date, organization)")
    value: str = Field(description="Extracted entity value")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence of the entity extraction")
    source_text: str = Field(description="Source text where entity was found")
    position_start: int = Field(ge=0, description="Start position in source text")
    position_end: int = Field(ge=0, description="End position in source text")


class Relationship(BaseModel):
    """Relationship between entities."""

    from_entity: str = Field(description="Source entity ID or value")
    to_entity: str = Field(description="Target entity ID or value")
    relationship: str = Field(description="Type of relationship")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence of the relationship")
    evidence: Optional[str] = Field(default=None, description="Optional evidence supporting the relationship")


class ExtractedField(BaseModel):
    """Named field extracted from the source."""

    name: str = Field(description="Field name")
    value: str = Field(description="Field value")
    evidence: Optional[str] = Field(default=None, description="Optional evidence supporting this field")

    @staticmethod
    def _stringify_value(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            seen: set[str] = set()
            parts: list[str] = []
            for item in value:
                cleaned = ExtractedField._stringify_value(item)
                if not cleaned:
                    continue
                key = cleaned.casefold()
                if key in seen:
                    continue
                seen.add(key)
                parts.append(cleaned)
            return "; ".join(parts)
        if isinstance(value, dict):
            if "value" in value and len(value) == 1:
                return ExtractedField._stringify_value(value.get("value"))
            parts = []
            for key, item_value in value.items():
                cleaned = ExtractedField._stringify_value(item_value)
                if cleaned:
                    parts.append(f"{key}: {cleaned}")
            return "; ".join(parts)
        return str(value).strip()

    @model_validator(mode="before")
    @classmethod
    def normalize_item(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"name": "field", "value": value}
        if isinstance(value, dict):
            data = dict(value)
            if "name" not in data:
                data["name"] = data.get("field") or data.get("label") or "field"
            if "value" not in data:
                fallback = data.get("text") or data.get("content")
                if fallback is not None:
                    data["value"] = fallback
            data["value"] = cls._stringify_value(data.get("value"))
            evidence = cls._stringify_value(data.get("evidence"))
            data["evidence"] = evidence or None
            return data
        return value


class RiskItem(BaseModel):
    """A structured risk identified in the source."""

    description: str = Field(description="Risk description")
    impact: Optional[str] = Field(default=None, description="Potential impact of the risk")
    owner: Optional[str] = Field(default=None, description="Risk owner if mentioned")
    due_date: Optional[str] = Field(default=None, description="Due date if mentioned")
    evidence: Optional[str] = Field(default=None, description="Short grounded snippet supporting the risk")

    @model_validator(mode="before")
    @classmethod
    def normalize_item(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"description": value}
        if isinstance(value, dict) and "description" not in value:
            text = value.get("text") or value.get("risk") or value.get("title")
            if text:
                value = dict(value)
                value["description"] = text
        return value


class ActionItem(BaseModel):
    """A structured action item identified in the source."""

    description: str = Field(description="Action description")
    owner: Optional[str] = Field(default=None, description="Assigned owner if mentioned")
    due_date: Optional[str] = Field(default=None, description="Due date if mentioned")
    status: Optional[str] = Field(default=None, description="Optional action status")
    evidence: Optional[str] = Field(default=None, description="Short grounded snippet supporting the action item")

    @model_validator(mode="before")
    @classmethod
    def normalize_item(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"description": value}
        if isinstance(value, dict) and "description" not in value:
            text = value.get("text") or value.get("action") or value.get("title")
            if text:
                value = dict(value)
                value["description"] = text
        return value


class ExtractionPayload(BaseTaskPayload):
    """Payload for information extraction tasks."""

    task_type: Literal["extraction"] = "extraction"
    main_subject: Optional[str] = Field(default=None, description="Main subject or topic of the source")
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    categories: List[str] = Field(default_factory=list, description="Identified categories")
    relationships: List[Relationship] = Field(default_factory=list, description="Entity relationships")
    extracted_fields: List[ExtractedField] = Field(default_factory=list, description="Named fields extracted")
    important_dates: List[str] = Field(default_factory=list, description="Important dates explicitly found in the text")
    important_numbers: List[str] = Field(default_factory=list, description="Important numeric values, budgets, counts or percentages")
    risks: List[RiskItem] = Field(default_factory=list, description="Risks or concerns explicitly mentioned")
    action_items: List[ActionItem] = Field(default_factory=list, description="Concrete actions or next steps found in the source")
    missing_information: List[str] = Field(default_factory=list, description="Notable gaps or ambiguities in the source")


class Topic(BaseModel):
    """Topic with key points and relevance."""

    title: str = Field(description="Topic title")
    key_points: List[str] = Field(default_factory=list, description="Key points under this topic")
    relevance_score: float = Field(ge=0.0, le=1.0, description="Relevance score of the topic")
    supporting_evidence: List[str] = Field(default_factory=list, description="Supporting evidence for the topic")


class SummaryPayload(BaseTaskPayload):
    """Payload for summary tasks."""

    task_type: Literal["summary"] = "summary"
    topics: List[Topic] = Field(default_factory=list, description="Main topics identified")
    executive_summary: str = Field(description="Executive summary")
    key_insights: List[str] = Field(default_factory=list, description="Key insights")
    reading_time_minutes: int = Field(ge=0, description="Estimated reading time in minutes")
    completeness_score: float = Field(ge=0.0, le=1.0, description="Completeness score")


class ChecklistItem(BaseModel):
    """Individual checklist item."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique item ID")
    title: str = Field(description="Item title")
    description: str = Field(description="Detailed description")
    source_text: Optional[str] = Field(default=None, description="Closest grounded source text supporting this item")
    evidence: Optional[str] = Field(default=None, description="Short evidence snippet quoted or copied from the source")
    category: Optional[str] = Field(default=None, description="Category of the item when explicitly grounded")
    priority: Optional[Literal["high", "medium", "low"]] = Field(default=None, description="Priority level when explicitly grounded")
    status: Literal["pending", "completed", "skipped"] = Field(default="pending", description="Current status")
    dependencies: List[str] = Field(default_factory=list, description="IDs of dependent items")
    estimated_time_minutes: Optional[int] = Field(default=None, ge=0, description="Estimated time in minutes when explicitly grounded")


class ChecklistPayload(BaseTaskPayload):
    """Payload for checklist generation tasks."""

    task_type: Literal["checklist"] = "checklist"
    title: str = Field(description="Checklist title")
    description: str = Field(description="Purpose description")
    items: List[ChecklistItem] = Field(default_factory=list, description="Checklist items")
    total_items: int = Field(ge=0, description="Total number of items")
    completed_items: int = Field(ge=0, description="Number of completed items")
    progress_percentage: float = Field(ge=0.0, le=100.0, description="Progress percentage")


class ContactInfo(BaseModel):
    """Top-level contact information extracted from a CV."""

    full_name: Optional[str] = Field(default=None, description="Full name")
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Location")
    links: List[str] = Field(default_factory=list, description="Relevant links such as LinkedIn or portfolio")

    @model_validator(mode="before")
    @classmethod
    def normalize_contact_info(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        email_value = data.get("email")
        if isinstance(email_value, list):
            picked = next((str(item).strip() for item in email_value if isinstance(item, str) and re.match(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", item.strip(), re.I)), None)
            data["email"] = picked
        return data


class EducationEntry(BaseModel):
    """Structured education entry extracted from a resume."""

    degree: Optional[str] = Field(default=None, description="Degree or program name")
    institution: Optional[str] = Field(default=None, description="Institution or school")
    location: Optional[str] = Field(default=None, description="Location if mentioned")
    date_range: Optional[str] = Field(default=None, description="Date range if mentioned")
    description: Optional[str] = Field(default=None, description="Free-form human-readable description")

    @staticmethod
    def _normalize_date_range(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, dict):
            start = str(value.get("start_date") or value.get("start") or value.get("start_year") or "").strip()
            end = str(value.get("end_date") or value.get("end") or value.get("end_year") or "").strip()
            if start and end:
                return f"{start} - {end}"
            return start or end or None
        return str(value).strip() or None

    @model_validator(mode="before")
    @classmethod
    def normalize_item(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"description": value}
        if isinstance(value, dict):
            data = dict(value)
            data["date_range"] = cls._normalize_date_range(data.get("date_range"))
            raw_description = str(data.get("description") or data.get("text") or "").strip()
            if raw_description and "," in raw_description and not data.get("degree"):
                left, right = [part.strip() for part in raw_description.split(",", 1)]
                if left and right:
                    data.setdefault("degree", left)
                    data.setdefault("institution", right)
            if "degree" not in data:
                data["degree"] = data.get("program") or data.get("title")
            if "institution" not in data:
                data["institution"] = data.get("school") or data.get("organization")
            if "date_range" not in data:
                data["date_range"] = cls._normalize_date_range(data.get("duration") or data.get("dates"))
            if "description" not in data:
                parts = [
                    str(data.get("degree") or "").strip(),
                    str(data.get("institution") or "").strip(),
                    str(data.get("location") or "").strip(),
                    str(data.get("date_range") or "").strip(),
                ]
                parts = [p for p in parts if p]
                if parts:
                    data["description"] = " | ".join(parts)
            for key in ("degree", "institution", "location", "date_range", "description"):
                if isinstance(data.get(key), str):
                    data[key] = data[key].strip()
            return data
        return value


class ExperienceEntry(BaseModel):
    """Structured experience entry extracted from a resume."""

    title: Optional[str] = Field(default=None, description="Role title")
    organization: Optional[str] = Field(default=None, description="Company or organization")
    location: Optional[str] = Field(default=None, description="Location if mentioned")
    date_range: Optional[str] = Field(default=None, description="Date range if mentioned")
    bullets: List[str] = Field(default_factory=list, description="Bullet points or responsibilities")
    description: Optional[str] = Field(default=None, description="Free-form human-readable description")

    @staticmethod
    def _looks_like_date_range(text: str | None) -> bool:
        cleaned = str(text or "").strip()
        return bool(re.search(r"(?:19|20)\d{2}|present|current", cleaned, re.I))

    @staticmethod
    def _looks_like_fragment_line(text: str | None) -> bool:
        cleaned = str(text or "").strip().lower()
        if not cleaned:
            return True
        fragment_starts = ("and ", "or ", "with ", "for ", "to ", "of ")
        return cleaned.endswith(".") and (cleaned.startswith(fragment_starts) or len(cleaned.split()) <= 3)

    @staticmethod
    def _split_org_location(text: str | None) -> tuple[Optional[str], Optional[str]]:
        cleaned = str(text or "").strip()
        if "|" not in cleaned:
            return (cleaned or None, None)
        parts = [part.strip() for part in cleaned.split("|") if part.strip()]
        if not parts:
            return None, None
        organization = parts[0]
        location = " | ".join(parts[1:]) if len(parts) > 1 else None
        return organization or None, location or None

    @staticmethod
    def _parse_multiline_experience(text: str) -> dict[str, Any]:
        lines = [line.strip("•- ").strip() for line in str(text or "").splitlines() if line.strip()]
        if len(lines) < 3:
            return {"description": text}
        first, second, third = lines[0], lines[1], lines[2]
        details: dict[str, Any] = {"description": text}

        if "|" in first and "|" not in second:
            organization, location = ExperienceEntry._split_org_location(first)
            title = second
        else:
            title = first
            organization, location = ExperienceEntry._split_org_location(second)

        if title and not ExperienceEntry._looks_like_fragment_line(title):
            details["title"] = title
        if organization and not ExperienceEntry._looks_like_fragment_line(organization):
            details["organization"] = organization
        if location and not ExperienceEntry._looks_like_fragment_line(location):
            details["location"] = location
        if ExperienceEntry._looks_like_date_range(third):
            details["date_range"] = third
        else:
            return {"description": text}

        if not details.get("title") or not details.get("organization"):
            return {"description": text}

        bullets = [line for line in lines[3:] if line]
        if bullets:
            details["bullets"] = [line for line in bullets if not ExperienceEntry._looks_like_fragment_line(line)]
        return details

    @staticmethod
    def _recover_date_and_bullets_from_description(data: dict[str, Any]) -> dict[str, Any]:
        description = str(data.get("description") or data.get("text") or "").strip()
        if not description:
            return data
        lines = [line.strip() for line in description.splitlines() if line.strip()]
        header = lines[0] if lines else description
        if not data.get("date_range") and "|" in header:
            parts = [part.strip() for part in header.split("|") if part.strip()]
            for part in parts:
                if ExperienceEntry._looks_like_date_range(part):
                    data["date_range"] = part
                    break
        if not data.get("bullets"):
            bullet_lines = [
                line.strip("•- ").strip()
                for line in lines[1:]
                if line.strip() and not ExperienceEntry._looks_like_fragment_line(line)
            ]
            if bullet_lines:
                data["bullets"] = bullet_lines
        return data

    @model_validator(mode="before")
    @classmethod
    def normalize_item(cls, value: Any) -> Any:
        if isinstance(value, str):
            return cls._parse_multiline_experience(value)
        if isinstance(value, dict):
            data = dict(value)
            if "title" not in data:
                data["title"] = data.get("role_title") or data.get("role") or data.get("position")
            raw_date_range = data.get("date_range")
            if isinstance(raw_date_range, dict):
                start_year = raw_date_range.get("start_year")
                start_month = raw_date_range.get("start_month")
                end_year = raw_date_range.get("end_year")
                end_month = raw_date_range.get("end_month")
                start = None
                end = None
                if start_year:
                    start = f"{int(start_year):04d}" + (f"-{int(start_month):02d}" if start_month else "")
                if end_year:
                    end = f"{int(end_year):04d}" + (f"-{int(end_month):02d}" if end_month else "")
                elif raw_date_range.get("is_current"):
                    end = "Present"
                data["date_range"] = f"{start} to {end}" if start and end else (start or end)
            multiline_source = data.get("description") or data.get("text")
            if isinstance(multiline_source, str) and "\n" in multiline_source and not any(data.get(key) for key in ("title", "organization", "date_range", "bullets")):
                parsed = cls._parse_multiline_experience(multiline_source)
                for key, item in parsed.items():
                    data.setdefault(key, item)
            if "organization" not in data:
                data["organization"] = data.get("company") or data.get("institution") or data.get("organization")
            if "date_range" not in data:
                data["date_range"] = data.get("duration") or data.get("dates")
            bullets = data.get("bullets")
            if isinstance(bullets, str):
                data["bullets"] = [x.strip() for x in bullets.replace("\n", ";").split(";") if x.strip()]
            elif bullets is None:
                data["bullets"] = []
            data = cls._recover_date_and_bullets_from_description(data)
            if "description" not in data:
                parts = [
                    str(data.get("title") or "").strip(),
                    str(data.get("organization") or "").strip(),
                    str(data.get("location") or "").strip(),
                    str(data.get("date_range") or "").strip(),
                ]
                parts = [p for p in parts if p]
                if parts:
                    data["description"] = " | ".join(parts)
            return data
        return value


class CVSectionContentItem(BaseModel):
    """Flexible content item inside a CV section."""

    text: Optional[str] = Field(default=None, description="Human-readable text for this item")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured details when available")

    @model_validator(mode="before")
    @classmethod
    def normalize_item(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"text": value, "details": {}}

        if isinstance(value, dict):
            if "text" in value:
                details = dict(value.get("details") or {})
                for key, item_value in value.items():
                    if key not in {"text", "details"}:
                        details[key] = item_value
                return {
                    "text": value.get("text"),
                    "details": details,
                }

            compact_parts = []
            for key, item_value in value.items():
                if item_value in (None, "", [], {}):
                    continue
                compact_parts.append(f"{key}: {item_value}")

            return {
                "text": " · ".join(compact_parts) if compact_parts else None,
                "details": value,
            }

        return value


class CVSection(BaseModel):
    """Section of a CV/resume."""

    section_type: str = Field(description="Type of section (experience, education, skills, projects, etc.)")
    title: Optional[str] = Field(default=None, description="Section title")
    content: List[CVSectionContentItem] = Field(default_factory=list, description="Content items in this section")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this section")

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @model_validator(mode="after")
    def fill_missing_title(self) -> "CVSection":
        if not self.title:
            self.title = self.section_type.replace("_", " ").title()
        return self


class CVAnalysisPayload(BaseTaskPayload):
    """Payload for CV analysis tasks."""

    task_type: Literal["cv_analysis"] = "cv_analysis"
    personal_info: Optional[ContactInfo] = Field(default=None, description="Personal information extracted")
    sections: List[CVSection] = Field(default_factory=list, description="Structured CV sections")
    skills: List[str] = Field(default_factory=list, description="Skills identified")
    languages: List[str] = Field(default_factory=list, description="Languages identified")
    education_entries: List[EducationEntry] = Field(default_factory=list, description="Structured education entries")
    experience_entries: List[ExperienceEntry] = Field(default_factory=list, description="Structured experience entries")
    experience_years: float = Field(default=0.0, ge=0.0, description="Years of experience")
    strengths: List[str] = Field(default_factory=list, description="Strengths identified")
    improvement_areas: List[str] = Field(default_factory=list, description="Areas for improvement")
    projects: List[str] = Field(default_factory=list, description="Project items identified")

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [x.strip() for x in value.replace("\n", ",").split(",") if x.strip()]
        if isinstance(value, list):
            normalized = []
            for item in value:
                if isinstance(item, str):
                    normalized.extend([x.strip() for x in item.replace("\n", ",").split(",") if x.strip()])
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("skill") or item.get("name") or item.get("value")
                    if isinstance(text, str) and text.strip():
                        normalized.extend([x.strip() for x in text.replace("\n", ",").split(",") if x.strip()])
                    else:
                        for v in item.values():
                            if isinstance(v, str) and v.strip():
                                normalized.extend([x.strip() for x in v.replace("\n", ",").split(",") if x.strip()])
                else:
                    normalized.append(str(item))
            return normalized
        return value

    @field_validator("languages", mode="before")
    @classmethod
    def normalize_languages(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            return [x.strip() for x in value.replace("\n", ",").split(",") if x.strip()]
        if isinstance(value, list):
            normalized = []
            for item in value:
                if isinstance(item, str):
                    normalized.extend([x.strip() for x in item.replace("\n", ",").split(",") if x.strip()])
                elif isinstance(item, dict):
                    language = item.get("language") or item.get("name") or item.get("text")
                    level = item.get("level") or item.get("proficiency")
                    if not level and isinstance(language, str):
                        match = re.match(r"^(.*?)\s*\(([^)]+)\)$", language)
                        if match:
                            language = match.group(1).strip()
                            level = match.group(2).strip()
                    if language and level:
                        normalized.append(f"{language} ({level})")
                    elif language:
                        normalized.append(str(language).strip())
                else:
                    normalized.append(str(item))
            return normalized
        return value


class CodeIssue(BaseModel):
    """A structured issue found in a code snippet or file."""

    severity: Literal["high", "medium", "low"] = Field(description="Issue severity")
    category: str = Field(description="Issue category, such as bug, readability, performance or maintainability")
    title: str = Field(description="Short issue title")
    description: str = Field(description="Detailed issue description")
    evidence: Optional[str] = Field(default=None, description="Code evidence or line hint supporting the issue")
    recommendation: Optional[str] = Field(default=None, description="Recommended fix or mitigation")


class CodeAnalysisPayload(BaseTaskPayload):
    """Payload for code explanation and refactor-advice tasks."""

    task_type: Literal["code_analysis"] = "code_analysis"
    snippet_summary: str = Field(description="Short summary of the snippet or file")
    main_purpose: str = Field(description="Main purpose of the code")
    detected_issues: List[CodeIssue] = Field(default_factory=list, description="Issues detected in the code")
    readability_improvements: List[str] = Field(default_factory=list, description="Suggestions to improve readability")
    maintainability_improvements: List[str] = Field(default_factory=list, description="Suggestions to improve maintainability")
    refactor_plan: List[str] = Field(default_factory=list, description="Step-by-step refactor plan")
    test_suggestions: List[str] = Field(default_factory=list, description="Tests that should be added or improved")
    risk_notes: List[str] = Field(default_factory=list, description="Operational or correctness risks to highlight")


TaskPayload = Union[ExtractionPayload, SummaryPayload, ChecklistPayload, CVAnalysisPayload, CodeAnalysisPayload]
