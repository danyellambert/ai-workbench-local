from __future__ import annotations

import re

from .schemas import CVExtractionResult, EvidenceRef, PageExtraction


EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def reconcile_pages(pages: list[PageExtraction], document_id: str, source_type: str = "mixed_pdf") -> CVExtractionResult:
    full_text = "\n".join(filter(None, [(page.native_text or page.ocr_text or "") for page in pages]))
    emails = [
        EvidenceRef(
            value=item,
            status="confirmed",
            evidence_text=item,
            source_type="ocr",
            confidence=0.95,
        )
        for item in dict.fromkeys(EMAIL_RE.findall(full_text))
    ]
    phones = [
        EvidenceRef(
            value=item,
            status="confirmed",
            evidence_text=item,
            source_type="ocr",
            confidence=0.8,
        )
        for item in dict.fromkeys(PHONE_RE.findall(full_text))
    ]
    result = CVExtractionResult(document_id=document_id, source_type=source_type, pages=pages)
    result.resume.emails = emails
    result.resume.phones = phones
    if not emails:
        result.warnings.append("No confirmed email found")
    if not phones:
        result.warnings.append("No confirmed phone found")
    return result