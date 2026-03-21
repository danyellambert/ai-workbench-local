from __future__ import annotations

import re
from typing import Iterable

from .schemas import (
    CVExtractionResult,
    EducationEntry,
    EvidenceBlock,
    ExperienceEntry,
    LanguageEntry,
    SectionCandidate,
    StructuredField,
)


SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("summary", re.compile(r"^(summary|profile|about)$", re.I)),
    ("experience", re.compile(r"^(experience|work experience|professional experience)$", re.I)),
    ("education", re.compile(r"^(education|academic background)$", re.I)),
    ("skills", re.compile(r"^(skills|technical skills|core skills)$", re.I)),
    ("languages", re.compile(r"^(languages)$", re.I)),
    ("certifications", re.compile(r"^(certifications|certificates)$", re.I)),
    ("projects", re.compile(r"^(projects)$", re.I)),
]

DATE_RE = re.compile(r"(?:19|20)\d{2}|present|current|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec", re.I)
LANGUAGE_RE = re.compile(r"^(english|portuguese|spanish|french|german|italian|japanese|mandarin)\b", re.I)
HEADER_HINT_RE = re.compile(r"(?:@|linkedin|github|\+\d|curriculum|resume)", re.I)
BULLET_SPLIT_RE = re.compile(r"(?:(?<=\s)-\s+|(?<=\s)•\s+)")
SECTION_TOKEN_RE = re.compile(r"\b(summary|skills|experience|education|languages|projects|certifications)\b", re.I)


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").split()).strip()


def _pick_directly_usable_contact(product_consumption: dict[str, object], field_name: str) -> str | None:
    field = product_consumption.get(field_name)
    if isinstance(field, dict) and field.get("directly_usable") and field.get("value"):
        return str(field.get("value")).strip()
    return None


def _pick_directly_usable_list(product_consumption: dict[str, object], field_name: str) -> list[str]:
    values: list[str] = []
    entries = product_consumption.get(field_name)
    if not isinstance(entries, list):
        return values
    for item in entries:
        if not isinstance(item, dict):
            continue
        if item.get("directly_usable") and item.get("value"):
            cleaned = _clean_text(str(item.get("value")))
            if cleaned and cleaned not in values:
                values.append(cleaned)
    return values


def build_evidence_blocks(result: CVExtractionResult) -> list[EvidenceBlock]:
    blocks: list[EvidenceBlock] = []
    for page in result.pages:
        page_blocks = page.blocks or []
        if page_blocks:
            for idx, block in enumerate(page_blocks, start=1):
                text = (block.text or "").strip()
                if not text:
                    continue
                blocks.append(
                    EvidenceBlock(
                        id=f"p{page.page}_b{idx}",
                        text=text,
                        page=page.page,
                        bbox=block.bbox,
                        source_type="ocr" if page.ocr_text else "native_text",
                        probable_section="other",
                        confidence=block.confidence,
                    )
                )
        else:
            text = (page.native_text or page.ocr_text or "").strip()
            if not text:
                continue
            segmented = _segment_text_into_blocks(text)
            total_segments = max(len(segmented), 1)
            for idx, paragraph in enumerate(segmented, start=1):
                region_label = _infer_fallback_region_label(idx, total_segments, paragraph)
                blocks.append(
                    EvidenceBlock(
                        id=f"p{page.page}_fallback_{idx}",
                        text=paragraph,
                        page=page.page,
                        region_ref=region_label,
                        source_type="native_text+ocr",
                        probable_section="other",
                        notes="region_aware_fallback",
                    )
                )
    return blocks


def detect_sections(blocks: list[EvidenceBlock]) -> list[SectionCandidate]:
    sections: list[SectionCandidate] = []
    current_section = "header"
    relabeled_experience_blocks = 0
    experience_like_blocks_detected = 0
    summary_blocks_relabeled_from_experience = 0
    experience_like_blocks_rejected_at_section_labeling = 0
    section_header_indices = {
        section_name: [] for section_name, _ in SECTION_PATTERNS
    }
    for index, block in enumerate(blocks):
        normalized = " ".join(block.text.split()).strip().lower().rstrip(":")
        for section_name, pattern in SECTION_PATTERNS:
            if pattern.match(normalized):
                section_header_indices.setdefault(section_name, []).append(index)

    first_experience_header_index = (section_header_indices.get("experience") or [None])[0]
    for block in blocks:
        normalized = " ".join(block.text.split()).strip().lower().rstrip(":")
        matched = None
        for section_name, pattern in SECTION_PATTERNS:
            if pattern.match(normalized):
                matched = section_name
                break
        strong_experience = _is_strong_experience_block(block)
        if strong_experience:
            experience_like_blocks_detected += 1
        if matched is None and _is_section_coherent_block(block.text):
            matched = _infer_section_from_content(normalized, block.text)
        block_index = blocks.index(block)
        if matched == "experience" and _should_be_summary_not_experience(block, block_index, first_experience_header_index):
            matched = "summary"
            summary_blocks_relabeled_from_experience += 1
            experience_like_blocks_rejected_at_section_labeling += 1
        if strong_experience and matched in {None, "summary"}:
            if matched == "summary" and not _should_be_summary_not_experience(block, block_index, first_experience_header_index):
                relabeled_experience_blocks += 1
                matched = "experience"
        if matched:
            current_section = matched
            block.probable_section = matched
            if not sections or sections[-1].section_type != matched:
                sections.append(
                    SectionCandidate(
                        section_type=matched,
                        page=block.page,
                        title=block.text,
                        bbox=block.bbox,
                        evidence_text=block.text,
                        confidence=0.95,
                    )
                )
        else:
            block.probable_section = current_section if current_section else "other"
    for block in blocks:
        if getattr(block, "notes", None) == "region_aware_fallback":
            suffix = f" experience_like_blocks_detected={experience_like_blocks_detected};summary_to_experience_relabels={relabeled_experience_blocks};summary_blocks_relabeled_from_experience={summary_blocks_relabeled_from_experience};experience_like_blocks_rejected_at_section_labeling={experience_like_blocks_rejected_at_section_labeling}"
            block.notes = f"{block.notes};{suffix}" if suffix not in block.notes else block.notes
    return sections


def populate_structured_resume(result: CVExtractionResult) -> CVExtractionResult:
    blocks = result.evidence_blocks
    extraction_diagnostics: dict[str, object] = result.runtime_metadata.get("structured_extraction_diagnostics", {}) if isinstance(result.runtime_metadata, dict) else {}
    result.resume.experience = _extract_experience(blocks, extraction_diagnostics)
    result.resume.education = _extract_education(blocks, extraction_diagnostics)
    result.resume.structured_skills = _extract_skills(blocks)
    result.resume.structured_languages = _extract_languages(blocks, extraction_diagnostics)
    result.runtime_metadata["structured_extraction_diagnostics"] = extraction_diagnostics
    return result


def build_extraction_diagnostics(blocks: list[EvidenceBlock]) -> dict[str, object]:
    region_labels = [block.region_ref for block in blocks if block.region_ref]
    return {
        "evidence_block_count": len(blocks),
        "block_region_labels": list(dict.fromkeys(region_labels)),
        "region_based_fallback_used": any((block.notes or "") == "region_aware_fallback" for block in blocks),
    }


def serialize_for_indexing(result: CVExtractionResult) -> dict[str, object]:
    raw_text = "\n\n".join(block.text for block in result.evidence_blocks)
    product_consumption = result.product_consumption if isinstance(result.product_consumption, dict) else {}
    confirmed_name = result.resume.name.value if result.resume.name.status == "confirmed" else None
    confirmed_location = result.resume.location.value if result.resume.location.status == "confirmed" else None
    confirmed_emails = [item.value for item in result.resume.emails if item.status == "confirmed" and item.value]
    confirmed_phones = [item.value for item in result.resume.phones if item.status == "confirmed" and item.value]

    directly_usable_name = _pick_directly_usable_contact(product_consumption, "name")
    directly_usable_location = _pick_directly_usable_contact(product_consumption, "location")
    directly_usable_emails = _pick_directly_usable_list(product_consumption, "emails")
    directly_usable_phones = _pick_directly_usable_list(product_consumption, "phones")
    return {
        "document_id": result.document_id,
        "raw_text": raw_text,
        "confirmed_fields": {
            "name": confirmed_name or directly_usable_name,
            "location": confirmed_location or directly_usable_location,
            "emails": list(dict.fromkeys([item for item in (confirmed_emails + directly_usable_emails) if item])),
            "phones": list(dict.fromkeys([item for item in (confirmed_phones + directly_usable_phones) if item])),
        },
        "structured": {
            "experience": [entry.model_dump() for entry in result.resume.experience],
            "education": [entry.model_dump() for entry in result.resume.education],
            "skills": [item.model_dump() for item in result.resume.structured_skills],
            "languages": [item.model_dump() for item in result.resume.structured_languages],
        },
    }


def _paragraphs(text: str) -> Iterable[str]:
    for item in re.split(r"\n\s*\n", text):
        cleaned = item.strip()
        if cleaned:
            yield cleaned


def _segment_text_into_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    seeded_lines: list[str] = []
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            seeded_lines.append("")
            continue
        split_parts = [part.strip() for part in BULLET_SPLIT_RE.split(line) if part.strip()]
        if len(split_parts) > 1:
            seeded_lines.extend(split_parts)
        else:
            seeded_lines.append(line)

    blocks: list[str] = []
    current: list[str] = []
    for line in seeded_lines:
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        if _looks_like_section_header(stripped):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            blocks.append(stripped)
            continue
        if current and (_looks_like_role_or_org_line(stripped) or _looks_like_date_line(stripped)):
            blocks.append("\n".join(current).strip())
            current = [stripped]
            continue
        current.append(stripped)
        if len(current) >= 2 and (_looks_like_date_line(stripped) or _looks_like_list_item(stripped)):
            blocks.append("\n".join(current).strip())
            current = []
            continue
        if len(current) >= 3:
            blocks.append("\n".join(current).strip())
            current = []
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block and _clean_text(block)]


def _looks_like_section_header(text: str) -> bool:
    lowered = text.lower().rstrip(":")
    if any(pattern.match(lowered) for _, pattern in SECTION_PATTERNS):
        return True
    return lowered in {"summary", "experience", "education", "skills", "languages", "certifications", "projects"}


def _infer_section_from_content(normalized: str, raw_text: str) -> str | None:
    if not _is_section_coherent_block(raw_text):
        return None
    if _is_experience_pattern_text(raw_text):
        return "experience"
    if HEADER_HINT_RE.search(raw_text):
        return "header"
    if any(keyword in normalized for keyword in ["experience", "worked", "responsible", "project manager"]):
        return "experience"
    if any(keyword in normalized for keyword in ["university", "bachelor", "master", "degree", "education"]):
        return "education"
    if any(keyword in normalized for keyword in ["python", "sql", "java", "aws", "skills", "docker", "kubernetes"]):
        return "skills"
    if any(keyword in normalized for keyword in ["english", "portuguese", "spanish", "french", "languages"]):
        return "languages"
    if any(keyword in normalized for keyword in ["certified", "certification", "certificate"]):
        return "certifications"
    if any(keyword in normalized for keyword in ["project", "portfolio"]):
        return "projects"
    if len(normalized.split()) > 20:
        return "summary"
    return None


def _is_experience_pattern_text(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    lines = [line.strip("•- ") for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    date_hits = sum(1 for line in lines if _looks_like_date_line(line))
    pipe_hits = sum(1 for line in lines[:3] if "|" in line)
    location_hits = sum(1 for line in lines[:4] if _looks_like_location(line))
    bullet_hits = sum(1 for line in lines if len(line.split()) > 4 and not _looks_like_date_line(line))
    title_company_combo = _looks_like_title(lines[0]) and (_looks_like_company(lines[1]) or pipe_hits > 0)
    return bool((title_company_combo and date_hits >= 1) or (pipe_hits >= 1 and date_hits >= 1) or (date_hits >= 1 and location_hits >= 1 and bullet_hits >= 1))


def _is_strong_experience_block(block: EvidenceBlock) -> bool:
    if not _is_section_coherent_block(block.text):
        return False
    if _looks_like_summary_or_skills_text(block.text):
        return False
    return _is_experience_pattern_text(block.text)


def _should_be_summary_not_experience(block: EvidenceBlock, block_index: int, first_experience_header_index: int | None) -> bool:
    if first_experience_header_index is not None and block_index < first_experience_header_index:
        return _looks_like_summary_or_skills_text(block.text) or not _is_experience_pattern_text(block.text)
    return False


def _looks_like_date_line(text: str) -> bool:
    return bool(DATE_RE.search(text))


def _looks_like_list_item(text: str) -> bool:
    return text.startswith(("-", "•")) or len(text.split()) <= 6


def _looks_like_role_or_org_line(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    if "," in cleaned or "|" in cleaned:
        return True
    words = cleaned.split()
    return 1 <= len(words) <= 6 and cleaned[:1].isupper()


def _is_section_coherent_block(text: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    token_hits = set(match.group(1).lower() for match in SECTION_TOKEN_RE.finditer(cleaned))
    if len(token_hits) >= 3:
        return False
    return True


def _is_plausible_experience_block(block: EvidenceBlock, lines: list[str]) -> bool:
    cleaned = _clean_text(block.text)
    token_hits = set(match.group(1).lower() for match in SECTION_TOKEN_RE.finditer(cleaned))
    if len(token_hits) >= 2:
        return False
    if len(lines) >= 2 and any(_looks_like_date_line(line) for line in lines):
        return True
    return any("|" in line for line in lines[:3]) and len(lines) >= 2


def _is_plausible_education_block(block: EvidenceBlock, lines: list[str]) -> bool:
    cleaned = _clean_text(block.text)
    token_hits = set(match.group(1).lower() for match in SECTION_TOKEN_RE.finditer(cleaned))
    if len(token_hits) >= 2:
        return False
    return len(lines) >= 1 and any(keyword in cleaned.lower() for keyword in ["university", "degree", "bachelor", "master", "education", "school"])


def _has_strong_experience_header(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    first = _safe_line(lines, 0)
    second = _safe_line(lines, 1)
    has_date = any(_looks_like_date_line(line) for line in lines[:4])
    has_location = any(_looks_like_location(line) for line in lines[:4])
    pipe_header = any("|" in line for line in lines[:2])
    title_company_date = bool(_looks_like_title(first) and _looks_like_company(second) and has_date)
    company_date_location = bool(_looks_like_company(first) and has_date and has_location)
    return title_company_date or company_date_location or (pipe_header and has_date)


def _is_plausible_education_entry(institution: str | None, degree: str | None, date_line: str | None, location_line: str | None) -> bool:
    if institution and institution.lower() in {"education", "academic background"}:
        return False
    if degree and degree.lower() in {"education", "academic background"}:
        return False
    return bool(institution or degree or (date_line and location_line))


def _is_noisy_education_value(text: str | None) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    if len(cleaned) > 120:
        return True
    if sum(1 for token in ["summary", "skills", "experience", "languages", "projects"] if token in cleaned.lower()) >= 2:
        return True
    return False


def _block_lines(block: EvidenceBlock) -> list[str]:
    return [line.strip("•- ") for line in block.text.splitlines() if line.strip()]


def _safe_line(lines: list[str], index: int) -> str | None:
    if 0 <= index < len(lines):
        value = _clean_text(lines[index])
        return value or None
    return None


def _looks_like_location(text: str | None) -> bool:
    cleaned = _clean_text(text)
    if not cleaned or _looks_like_date_line(cleaned):
        return False
    if "," in cleaned or "|" in cleaned:
        return True
    words = cleaned.split()
    return 2 <= len(words) <= 4 and all(word[:1].isupper() for word in words if word)


def _looks_like_title(text: str | None) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    if _looks_like_date_line(cleaned) or _looks_like_location(cleaned):
        return False
    words = cleaned.split()
    return 1 <= len(words) <= 8


def _clean_experience_title(text: str | None) -> str | None:
    cleaned = _clean_text(text)
    if not cleaned:
        return None
    cleaned = re.sub(r"^[^A-Za-z]+", "", cleaned).strip()
    return cleaned or None


def _looks_like_company(text: str | None) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    if _looks_like_date_line(cleaned):
        return False
    return "|" in cleaned or "," in cleaned or 1 <= len(cleaned.split()) <= 6


def _looks_like_summary_or_skills_text(text: str | None) -> bool:
    cleaned = _clean_text(text).lower()
    if not cleaned:
        return False
    summary_terms = ["summary", "profile", "experience in", "interest in", "exposure to", "opportunities", "recommendations"]
    skills_terms = ["skills", "python", "sql", "docker", "aws", "ml", "machine learning"]
    if any(term in cleaned for term in summary_terms):
        return True
    return sum(1 for term in skills_terms if term in cleaned) >= 2


def _split_language_line(text: str) -> tuple[str | None, str | None]:
    cleaned = _clean_text(text)
    if not cleaned:
        return None, None
    cleaned = _recover_ocr_language_prefix(cleaned)
    match = re.match(r"^(English|Portuguese|Spanish|French|German|Italian|Japanese|Mandarin)\s*(?:\(([^)]+)\)|[-–:]\s*(.+))?$", cleaned, re.I)
    if not match:
        return None, None
    language = match.group(1)
    proficiency = match.group(2) or match.group(3)
    return language, _clean_text(proficiency) or None


def _extract_inline_language_candidates(text: str) -> list[tuple[str, str | None]]:
    candidates: list[tuple[str, str | None]] = []
    pattern = re.compile(r"(English|Portuguese|Spanish|French|German|Italian|Japanese|Mandarin)\s*(?:\(([^)]+)\)|[-–:]\s*([A-Za-z ]+))?", re.I)
    normalized_text = _recover_ocr_language_prefix(text)
    for match in pattern.finditer(normalized_text):
        language = _clean_text(match.group(1))
        proficiency = _clean_text(match.group(2) or match.group(3)) or None
        if language:
            candidates.append((language, proficiency))
    return candidates


def _recover_ocr_language_prefix(text: str) -> str:
    cleaned = _clean_text(text)
    lowered = cleaned.lower().lstrip("-•+ /")
    recoveries = {
        "talian": "Italian",
        "-talian": "Italian",
        "spanish": "Spanish",
        "portuguese": "Portuguese",
        "french": "French",
        "german": "German",
    }
    for bad, good in recoveries.items():
        if lowered.startswith(bad):
            prefix_trim = len(cleaned) - len(lowered)
            suffix = cleaned[prefix_trim + len(bad):]
            return f"{good}{suffix}"
    return cleaned


def _parse_experience_header(lines: list[str]) -> tuple[str | None, str | None, str | None, str | None]:
    header_candidates = [line for line in lines[:3] if line and "|" in line]
    if header_candidates:
        parts = [part.strip() for part in header_candidates[0].split("|") if part.strip()]
        title_candidate = _clean_experience_title(parts[0]) if len(parts) >= 1 else None
        title = title_candidate if title_candidate else None
        company = parts[1] if len(parts) >= 2 and _looks_like_company(parts[1]) else None
        location = next((part for part in parts[2:] if _looks_like_location(part)), None)
        date_range = next((part for part in parts[1:] if _looks_like_date_line(part)), None)
        return title, company, location, date_range
    title_candidate = _clean_experience_title(_safe_line(lines, 0))
    title = title_candidate if _looks_like_title(title_candidate) else None
    company = _safe_line(lines, 1) if _looks_like_company(_safe_line(lines, 1)) else None
    location = next((line for line in lines[:4] if _looks_like_location(line)), None)
    date_range = next((line for line in lines[:4] if _looks_like_date_line(line)), None)
    return title, company, location, date_range


def _parse_education_line(line: str) -> tuple[str | None, str | None]:
    cleaned = _clean_text(line)
    if not cleaned or cleaned.lower() in {"education", "academic background"}:
        return None, None
    degree_markers = ["bsc", "b.sc", "bachelor", "msc", "m.sc", "master", "phd", "degree", "engineering", "certificate"]
    if "," in cleaned and any(marker in cleaned.lower() for marker in degree_markers):
        left, right = [part.strip() for part in cleaned.split(",", 1)]
        return left or None, right or None
    return (cleaned, None) if any(marker in cleaned.lower() for marker in degree_markers) else (None, cleaned)


def _split_language_candidates_from_text(text: str) -> list[tuple[str, str | None]]:
    normalized = _recover_ocr_language_prefix(text).replace('+', ' ')
    pattern = re.compile(
        r"(?:^|[\n;,•\-\/]\s*)(English|Portuguese|Spanish|French|German|Italian|Japanese|Mandarin)\s*(?:\(([^)]+)\)|[-–:]\s*([A-Za-z ]+))?",
        re.I,
    )
    candidates: list[tuple[str, str | None]] = []
    for match in pattern.finditer(normalized):
        language = _clean_text(match.group(1))
        proficiency = _clean_text(match.group(2) or match.group(3)) or None
        if language:
            candidates.append((language, proficiency))
    return candidates


def _collect_local_neighbor_blocks(blocks: list[EvidenceBlock], index: int, section_names: set[str]) -> list[EvidenceBlock]:
    neighbors: list[EvidenceBlock] = [blocks[index]]
    for offset in (1, 2):
        next_index = index + offset
        if next_index >= len(blocks):
            break
        candidate = blocks[next_index]
        if candidate.probable_section not in section_names:
            break
        neighbors.append(candidate)
    return neighbors


def _collect_local_language_blocks(blocks: list[EvidenceBlock], index: int) -> list[EvidenceBlock]:
    neighbors: list[EvidenceBlock] = [blocks[index]]
    for offset in (1, 2):
        next_index = index + offset
        if next_index >= len(blocks):
            break
        candidate = blocks[next_index]
        if candidate.probable_section != "languages":
            break
        neighbors.append(candidate)
    return neighbors


def _make_language_field(value: str | None, block: EvidenceBlock, evidence_text: str | None, *, confirmed: bool = True) -> StructuredField:
    return StructuredField(
        value=value,
        status="confirmed" if (confirmed and value) else ("not_found" if not value else "needs_review"),
        evidence_text=evidence_text if value else None,
        page=block.page,
        bbox=block.bbox,
        block_ref=block.id,
        source_type=block.source_type,
        confidence=block.confidence,
    )


def _find_language_evidence_block(local_blocks: list[EvidenceBlock], language: str) -> tuple[EvidenceBlock, str | None]:
    for candidate in local_blocks:
        recovered = _recover_ocr_language_prefix(candidate.text)
        if language.lower() in recovered.lower() and _clean_text(candidate.text).lower() != "languages":
            return candidate, candidate.text
    return local_blocks[-1], None


def _infer_fallback_region_label(index: int, total_segments: int, text: str) -> str:
    cleaned = _clean_text(text).lower()
    if index == 1 or HEADER_HINT_RE.search(text):
        return "header_top_zone"
    if any(token in cleaned for token in ["linkedin", "github", "@", "+55", "+1", "+44"]):
        return "contact_zone"
    if any(token in cleaned for token in ["summary", "profile", "about"]):
        return "summary_zone"
    if any(token in cleaned for token in ["skills", "python", "sql", "aws", "docker"]):
        return "skills_zone"
    if any(token in cleaned for token in ["languages", "english", "spanish", "italian", "french"]):
        return "languages_zone"
    if any(token in cleaned for token in ["education", "university", "bachelor", "master"]):
        return "education_zone"
    if any(token in cleaned for token in ["experience", "worked", "company", "present"]):
        return "experience_zone"
    if index <= max(2, total_segments // 3):
        return "upper_page_zone"
    if index >= max(1, total_segments - 1):
        return "lower_page_zone"
    return "middle_page_zone"


def _make_field(value: str | None, block: EvidenceBlock, status: str = "confirmed", notes: str | None = None) -> StructuredField:
    return StructuredField(
        value=value,
        status=status if value else "not_found",
        evidence_text=block.text if value else None,
        page=block.page,
        bbox=block.bbox,
        block_ref=block.id,
        source_type=block.source_type,
        confidence=block.confidence,
        notes=notes,
    )


def _extract_experience(blocks: list[EvidenceBlock], diagnostics: dict[str, object] | None = None) -> list[ExperienceEntry]:
    entries: list[ExperienceEntry] = []
    section_header_indices = [
        index for index, block in enumerate(blocks)
        if _clean_text(block.text).lower().rstrip(":") in {"experience", "work experience", "professional experience"}
    ]
    first_experience_header_index = section_header_indices[0] if section_header_indices else None
    relevant_indices = [
        index for index, block in enumerate(blocks)
        if block.probable_section == "experience" and (first_experience_header_index is None or index > first_experience_header_index)
    ]
    if diagnostics is not None:
        diagnostics["experience_section_headers_seen"] = len(section_header_indices)
        diagnostics["experience_blocks_seen"] = len(relevant_indices)
        diagnostics["summary_blocks_blocked_from_experience"] = 0
        diagnostics["experience_entry_headers_seen"] = 0
    for index in relevant_indices:
        local_blocks = _collect_local_neighbor_blocks(blocks, index, {"experience", "summary"})
        block = local_blocks[0]
        if index <= (first_experience_header_index or -1):
            if diagnostics is not None:
                diagnostics["summary_blocks_blocked_from_experience"] += 1
                diagnostics.setdefault("experience_rejections", []).append(f"{block.id}: before_experience_section_header")
            continue
        if block.probable_section == "summary" or _looks_like_summary_or_skills_text(block.text):
            if diagnostics is not None:
                diagnostics["summary_blocks_blocked_from_experience"] += 1
                diagnostics.setdefault("experience_rejections", []).append(f"{block.id}: summary_or_skills_like_block")
            continue
        lines: list[str] = []
        for candidate in local_blocks:
            if candidate.probable_section == "summary" and candidate is not block:
                break
            lines.extend(_block_lines(candidate))
        if not lines or not _is_plausible_experience_block(block, lines):
            if diagnostics is not None:
                diagnostics.setdefault("experience_rejections", []).append(f"{block.id}: insufficient_header_evidence")
            continue
        strong_header = _has_strong_experience_header(lines)
        if not strong_header:
            if diagnostics is not None:
                diagnostics.setdefault("experience_rejections", []).append(f"{block.id}: weak_experience_signature")
            continue
        if diagnostics is not None:
            diagnostics["experience_entry_headers_seen"] += 1
        title, company, location_line, date_line = _parse_experience_header(lines)
        header_lines = {line for line in lines[:3] if "|" in line}
        bullets = [line for line in lines if line not in {title, company, date_line, location_line} and line not in header_lines]
        bullets = [
            line for line in bullets
            if len(_clean_text(line).split()) > 3 and not _looks_like_summary_or_skills_text(line)
        ]
        if header_lines and diagnostics is not None:
            diagnostics["experience_header_lines_removed_from_bullets"] = diagnostics.get("experience_header_lines_removed_from_bullets", 0) + len(header_lines)
        if location_line and diagnostics is not None:
            diagnostics["experience_locations_recovered"] = diagnostics.get("experience_locations_recovered", 0) + 1
        if not any([title, company, date_line, location_line, bullets]):
            if diagnostics is not None:
                diagnostics.setdefault("experience_field_split_failures", []).append(f"{block.id}: empty_after_header_split")
            continue
        entry = ExperienceEntry(
            company=_make_field(company, block, notes="First-pass company guess"),
            title=_make_field(title, block, status="needs_review" if title else "not_found", notes="First-pass title guess"),
            date_range=_make_field(date_line, block, status="needs_review" if date_line else "not_found"),
            location=_make_field(location_line, block, status="needs_review" if location_line else "not_found"),
            description_or_bullets=[_make_field(item, block, status="confirmed") for item in bullets],
        )
        entries.append(entry)
    if diagnostics is not None:
        diagnostics["experience_entries_created"] = len(entries)
        diagnostics["experience_headers_split"] = len(entries)
    return entries


def _extract_education(blocks: list[EvidenceBlock], diagnostics: dict[str, object] | None = None) -> list[EducationEntry]:
    entries: list[EducationEntry] = []
    relevant_indices = [index for index, block in enumerate(blocks) if block.probable_section == "education"]
    if diagnostics is not None:
        diagnostics["education_blocks_seen"] = len(relevant_indices)
    for index in relevant_indices:
        local_blocks = _collect_local_neighbor_blocks(blocks, index, {"education"})
        block = local_blocks[0]
        if _clean_text(block.text).lower().rstrip(":") in {"education", "academic background"}:
            if diagnostics is not None:
                diagnostics["education_section_header_blocks_skipped"] = diagnostics.get("education_section_header_blocks_skipped", 0) + 1
            continue
        lines: list[str] = []
        for candidate in local_blocks:
            lines.extend(_block_lines(candidate))
        if not lines or not _is_plausible_education_block(block, lines):
            continue
        degree = None
        institution = None
        for line in lines:
            parsed_degree, parsed_institution = _parse_education_line(line)
            degree = degree or parsed_degree
            institution = institution or parsed_institution
        if degree and institution and diagnostics is not None:
            diagnostics["education_lines_split"] = diagnostics.get("education_lines_split", 0) + 1
        date_line = next((line for line in lines if DATE_RE.search(line)), None)
        location_line = next((line for line in lines if _looks_like_location(line) and line not in {institution, degree, block.text}), None)
        notes = [line for line in lines if line not in {institution, degree, date_line, location_line}]
        if _is_noisy_education_value(institution) or _is_noisy_education_value(degree):
            if diagnostics is not None:
                diagnostics.setdefault("education_rejections", []).append(f"{block.id}: noisy_education_value")
            continue
        if not _is_plausible_education_entry(institution, degree, date_line, location_line):
            if diagnostics is not None:
                diagnostics.setdefault("education_rejections", []).append(f"{block.id}: implausible_education_fields")
            continue
        entry = EducationEntry(
            institution=_make_field(institution, block, notes="First-pass institution guess"),
            degree=_make_field(degree, block, status="needs_review" if degree else "not_found"),
            date_range=_make_field(date_line, block, status="needs_review" if date_line else "not_found"),
            location=_make_field(location_line, block, status="needs_review" if location_line else "not_found"),
            notes=[_make_field(item, block, status="confirmed") for item in notes],
        )
        duplicate = next((existing for existing in entries if (existing.institution.value == entry.institution.value and existing.degree.value == entry.degree.value and existing.date_range.value == entry.date_range.value)), None)
        if duplicate is not None:
            if diagnostics is not None:
                diagnostics["education_dedup_dropped"] = diagnostics.get("education_dedup_dropped", 0) + 1
            continue
        entries.append(entry)
    if diagnostics is not None:
        diagnostics["education_entries_created"] = len(entries)
    return entries


def _extract_skills(blocks: list[EvidenceBlock]) -> list[StructuredField]:
    skills: list[StructuredField] = []
    relevant = [block for block in blocks if block.probable_section == "skills"]
    for block in relevant:
        if not _is_section_coherent_block(block.text):
            continue
        parts = re.split(r"[,;\n•]", block.text)
        for part in parts:
            item = part.strip()
            if len(item) < 2:
                continue
            skills.append(_make_field(item, block, status="confirmed"))
    return skills


def _extract_languages(blocks: list[EvidenceBlock], diagnostics: dict[str, object] | None = None) -> list[LanguageEntry]:
    languages: list[LanguageEntry] = []
    relevant = [block for block in blocks if block.probable_section == "languages"]
    if diagnostics is not None:
        diagnostics["languages_blocks_seen"] = len(relevant)
    for index, block in enumerate(relevant):
        if not _is_section_coherent_block(block.text):
            if diagnostics is not None:
                diagnostics.setdefault("language_rejections", []).append(f"{block.id}: incoherent_block")
            continue
        local_blocks = _collect_local_language_blocks(relevant, index)
        combined_text = "\n".join(candidate.text for candidate in local_blocks)
        parts = [part.strip() for part in re.split(r"[;\n•]", combined_text) if part.strip() and _clean_text(part).lower() != 'languages']
        seen_in_block = 0
        for item in parts:
            candidates = _split_language_candidates_from_text(item)
            for language, proficiency in candidates:
                seen_in_block += 1
                evidence_text = item
                languages.append(
                    LanguageEntry(
                        language=_make_language_field(language, block, evidence_text, confirmed=True),
                        proficiency=_make_language_field(proficiency or None, block, evidence_text, confirmed=bool(proficiency)),
                    )
                )
        if seen_in_block == 0:
            inline_candidates = _extract_inline_language_candidates(combined_text)
            for language, proficiency in inline_candidates:
                seen_in_block += 1
                evidence_text = next((part for part in parts if language.lower() in _recover_ocr_language_prefix(part).lower()), None)
                if not evidence_text:
                    if diagnostics is not None:
                        diagnostics["language_header_only_evidence_blocked"] = diagnostics.get("language_header_only_evidence_blocked", 0) + 1
                    continue
                languages.append(
                    LanguageEntry(
                        language=_make_language_field(language, block, evidence_text, confirmed=True),
                        proficiency=_make_language_field(proficiency or None, block, evidence_text, confirmed=bool(proficiency)),
                    )
                )
        if seen_in_block > 1 and diagnostics is not None:
            diagnostics["languages_multi_item_extracted"] = diagnostics.get("languages_multi_item_extracted", 0) + 1
        if "Italian" in combined_text or "talian" in combined_text:
            if diagnostics is not None and any((entry.language.value or "") == "Italian" for entry in languages):
                diagnostics["language_ocr_recoveries"] = diagnostics.get("language_ocr_recoveries", 0) + 1
        if seen_in_block == 0 and diagnostics is not None:
            diagnostics.setdefault("language_rejections", []).append(f"{block.id}: no_explicit_language_pattern")
    if diagnostics is not None:
        pass
    deduped: list[LanguageEntry] = []
    seen_keys: set[str] = set()
    for entry in languages:
        key = f"{(entry.language.value or '').lower()}|{(entry.proficiency.value or '').lower()}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(entry)
    if diagnostics is not None:
        diagnostics["languages_entries_created"] = len(deduped)
    return deduped