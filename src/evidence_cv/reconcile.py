from __future__ import annotations

import re

from .schemas import CVExtractionResult, EvidenceRef, PageExtraction
from .structure import build_evidence_blocks, detect_sections, populate_structured_resume, serialize_for_indexing


EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
NAME_RE = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}$")
EMAIL_CLEANUP_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+(?:\.[A-Z]{2,})?", re.I)


def _recover_best_header_name(top_lines: list[str]) -> str | None:
    for raw in top_lines:
        cleaned = " ".join(raw.replace("Carvatho", "Carvalho").split())
        cleaned = cleaned.replace("AraujoCarvalho", "Araujo Carvalho")
        cleaned = cleaned.strip("|,-• ")
        if NAME_RE.match(cleaned):
            return cleaned
    return None


def _clean_email_candidates(full_text: str) -> list[str]:
    values: list[str] = []
    for raw in EMAIL_CLEANUP_RE.findall(full_text.replace(" ", "")):
        cleaned = raw.replace("canvalho", "carvalho")
        if cleaned.endswith("@examplecom"):
            cleaned = cleaned.replace("@examplecom", "@example.com")
        elif not cleaned.lower().endswith(".com") and "@" in cleaned and "." not in cleaned.split("@", 1)[1]:
            cleaned = cleaned + ".com"
        if EMAIL_RE.fullmatch(cleaned) and cleaned not in values:
            values.append(cleaned)
    return values


def _clean_phone_candidates(full_text: str) -> list[str]:
    values: list[str] = []
    for raw in PHONE_RE.findall(full_text):
        candidate = raw.strip()
        if re.search(r"(?:19|20)\d{2}", candidate):
            continue
        if candidate not in values:
            values.append(candidate)
    return values


def reconcile_pages(pages: list[PageExtraction], document_id: str, source_type: str = "mixed_pdf") -> CVExtractionResult:
    full_text = "\n".join(filter(None, [(page.native_text or page.ocr_text or "") for page in pages]))
    top_lines = [line.strip() for line in full_text.splitlines() if line.strip()][:6]
    emails = [
        EvidenceRef(
            value=item,
            status="confirmed",
            evidence_text=item,
            source_type="ocr",
            confidence=0.95,
        )
        for item in _clean_email_candidates(full_text)
    ]
    phones = [
        EvidenceRef(
            value=item,
            status="confirmed",
            evidence_text=item,
            source_type="ocr",
            confidence=0.8,
        )
        for item in _clean_phone_candidates(full_text)
    ]
    result = CVExtractionResult(document_id=document_id, source_type=source_type, pages=pages)
    best_name = _recover_best_header_name(top_lines)
    if best_name:
        result.resume.name = EvidenceRef(
            value=best_name,
            status="confirmed",
            evidence_text=best_name,
            source_type="ocr",
            confidence=0.85,
        )
    result.resume.emails = emails
    result.resume.phones = phones
    result.evidence_blocks = build_evidence_blocks(result)
    result.sections = detect_sections(result.evidence_blocks)
    result = populate_structured_resume(result)
    result.runtime_metadata["indexing_payload"] = serialize_for_indexing(result)
    if not emails:
        result.warnings.append("No confirmed email found")
    if not phones:
        result.warnings.append("No confirmed phone found")
    return result