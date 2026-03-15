"""Base schemas and types for structured outputs."""
from __future__ import annotations

from typing import List, Optional, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field


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


class ExtractionPayload(BaseTaskPayload):
    """Payload for information extraction tasks."""

    task_type: Literal["extraction"] = "extraction"
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    categories: List[str] = Field(default_factory=list, description="Identified categories")
    relationships: List[Relationship] = Field(default_factory=list, description="Entity relationships")
    extracted_fields: List[ExtractedField] = Field(default_factory=list, description="Named fields extracted")


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


class CVSection(BaseModel):
    """Section of a CV/resume."""

    section_type: str = Field(description="Type of section (experience, education, skills, projects, etc.)")
    title: str = Field(description="Section title")
    content: List[str] = Field(default_factory=list, description="Content items in this section")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this section")


class CVAnalysisPayload(BaseTaskPayload):
    """Payload for CV analysis tasks."""

    task_type: Literal["cv_analysis"] = "cv_analysis"
    personal_info: Optional[ContactInfo] = Field(default=None, description="Personal information extracted")
    sections: List[CVSection] = Field(default_factory=list, description="Structured CV sections")
    skills: List[str] = Field(default_factory=list, description="Skills identified")
    experience_years: float = Field(ge=0.0, description="Years of experience")
    strengths: List[str] = Field(default_factory=list, description="Strengths identified")
    improvement_areas: List[str] = Field(default_factory=list, description="Areas for improvement")


TaskPayload = Union[ExtractionPayload, SummaryPayload, ChecklistPayload, CVAnalysisPayload]
