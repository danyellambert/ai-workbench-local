from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


FieldStatus = Literal["confirmed", "visual_candidate", "needs_review", "not_found"]
SourceType = Literal["native_text", "ocr", "vl", "ocr+vl", "native_text+ocr", "unknown"]


class EvidenceRef(BaseModel):
    value: str | None = None
    status: FieldStatus = "not_found"
    evidence_text: str | None = None
    source_type: SourceType = "unknown"
    page: int | None = None
    bbox: list[float] | None = None
    confidence: float | None = None
    normalized_value: str | None = None
    notes: str | None = None


class OCRWord(BaseModel):
    text: str
    confidence: float | None = None
    bbox: list[float] | None = None


class OCRLine(BaseModel):
    text: str
    bbox: list[float] | None = None
    confidence: float | None = None
    words: list[OCRWord] = Field(default_factory=list)


class OCRBlock(BaseModel):
    text: str
    bbox: list[float] | None = None
    confidence: float | None = None
    lines: list[OCRLine] = Field(default_factory=list)


class PageExtraction(BaseModel):
    page: int
    native_text: str | None = None
    ocr_text: str | None = None
    blocks: list[OCRBlock] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SectionCandidate(BaseModel):
    section_type: str
    page: int
    title: str | None = None
    bbox: list[float] | None = None
    evidence_text: str | None = None
    confidence: float | None = None


CVSectionType = Literal[
    "header",
    "summary",
    "experience",
    "education",
    "skills",
    "languages",
    "certifications",
    "projects",
    "other",
]


class EvidenceBlock(BaseModel):
    id: str
    text: str
    page: int
    bbox: list[float] | None = None
    region_ref: str | None = None
    source_type: SourceType = "unknown"
    probable_section: CVSectionType = "other"
    confidence: float | None = None
    notes: str | None = None


class StructuredField(BaseModel):
    value: str | None = None
    status: FieldStatus = "not_found"
    evidence_text: str | None = None
    page: int | None = None
    bbox: list[float] | None = None
    block_ref: str | None = None
    source_type: SourceType = "unknown"
    confidence: float | None = None
    notes: str | None = None


class ExperienceEntry(BaseModel):
    company: StructuredField = Field(default_factory=StructuredField)
    title: StructuredField = Field(default_factory=StructuredField)
    date_range: StructuredField = Field(default_factory=StructuredField)
    location: StructuredField = Field(default_factory=StructuredField)
    description_or_bullets: list[StructuredField] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: StructuredField = Field(default_factory=StructuredField)
    degree: StructuredField = Field(default_factory=StructuredField)
    date_range: StructuredField = Field(default_factory=StructuredField)
    location: StructuredField = Field(default_factory=StructuredField)
    notes: list[StructuredField] = Field(default_factory=list)


class LanguageEntry(BaseModel):
    language: StructuredField = Field(default_factory=StructuredField)
    proficiency: StructuredField = Field(default_factory=StructuredField)


class ResumeExtraction(BaseModel):
    name: EvidenceRef = Field(default_factory=EvidenceRef)
    headline: EvidenceRef = Field(default_factory=EvidenceRef)
    location: EvidenceRef = Field(default_factory=EvidenceRef)
    summary: EvidenceRef = Field(default_factory=EvidenceRef)
    emails: list[EvidenceRef] = Field(default_factory=list)
    phones: list[EvidenceRef] = Field(default_factory=list)
    links: list[EvidenceRef] = Field(default_factory=list)
    skills: list[EvidenceRef] = Field(default_factory=list)
    languages: list[EvidenceRef] = Field(default_factory=list)
    certifications: list[EvidenceRef] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    structured_skills: list[StructuredField] = Field(default_factory=list)
    structured_languages: list[LanguageEntry] = Field(default_factory=list)


class CVExtractionResult(BaseModel):
    document_id: str
    document_type: Literal["cv_resume"] = "cv_resume"
    source_type: Literal["digital_pdf", "scanned_pdf", "mixed_pdf"] = "mixed_pdf"
    pages: list[PageExtraction] = Field(default_factory=list)
    evidence_blocks: list[EvidenceBlock] = Field(default_factory=list)
    sections: list[SectionCandidate] = Field(default_factory=list)
    resume: ResumeExtraction = Field(default_factory=ResumeExtraction)
    product_consumption: dict[str, object] = Field(default_factory=dict)
    runtime_metadata: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)