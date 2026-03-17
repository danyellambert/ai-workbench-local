"""Base schemas and types for structured outputs."""
from __future__ import annotations

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


class RiskItem(BaseModel):
    """A structured risk identified in the source."""

    description: str = Field(description="Risk description")
    impact: Optional[str] = Field(default=None, description="Potential impact of the risk")
    owner: Optional[str] = Field(default=None, description="Risk owner if mentioned")
    due_date: Optional[str] = Field(default=None, description="Due date if mentioned")

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
    category: str = Field(description="Category of the item")
    priority: Literal["high", "medium", "low"] = Field(description="Priority level")
    status: Literal["pending", "completed", "skipped"] = Field(default="pending", description="Current status")
    dependencies: List[str] = Field(default_factory=list, description="IDs of dependent items")
    estimated_time_minutes: int = Field(ge=0, description="Estimated time in minutes")


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
    experience_years: float = Field(default=0.0, ge=0.0, description="Years of experience")
    strengths: List[str] = Field(default_factory=list, description="Strengths identified")
    improvement_areas: List[str] = Field(default_factory=list, description="Areas for improvement")


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
