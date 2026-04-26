from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any


_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("title", "role title", "job title", "position"),
    "seniority": ("seniority", "level", "seniority level"),
    "must_haves": (
        "must have",
        "must-haves",
        "must haves",
        "required",
        "requirements",
        "required skills",
        "core requirements",
    ),
    "nice_to_haves": (
        "nice to have",
        "nice-to-have",
        "nice to haves",
        "preferred",
        "preferred qualifications",
        "bonus",
    ),
    "leadership_expectations": (
        "leadership",
        "leadership expectations",
        "ownership",
        "scope",
    ),
    "interview_focus": (
        "interview focus",
        "interview priorities",
        "assessment",
        "evaluation focus",
    ),
    "red_flags": (
        "red flags",
        "watchouts",
        "risks",
        "screen outs",
        "screen-outs",
    ),
}


@dataclass(slots=True)
class RoleBriefContext:
    title: str | None = None
    seniority: str | None = None
    must_haves: list[str] = field(default_factory=list)
    nice_to_haves: list[str] = field(default_factory=list)
    leadership_expectations: list[str] = field(default_factory=list)
    interview_focus: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    raw_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_source_decorators(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[source:[^\]]+\]", "", value, flags=re.IGNORECASE).replace('\n', ' ')).strip()


def _looks_like_document_label(value: str) -> bool:
    lowered = value.casefold()
    return bool(re.search(r"\.(pdf|doc|docx|txt|md)$", value, flags=re.IGNORECASE) or (("role brief" in lowered or "job description" in lowered or "hiring brief" in lowered) and any(token in lowered for token in ("pdf", "doc", "docx", "txt", "md"))))


def _clean_text(value: object) -> str | None:
    cleaned = _strip_source_decorators(str(value or ""))
    return cleaned or None


def _normalize_bullets(values: list[object], *, limit: int = 8) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        cleaned = re.sub(r"^[\-\*\u2022\d\.)\s]+", "", cleaned).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
        if len(normalized) >= limit:
            break
    return normalized


def _canonical_section_name(raw_name: str) -> str | None:
    lowered = _clean_text(raw_name)
    if not lowered:
        return None
    lowered = lowered.casefold().rstrip(":")
    for canonical, aliases in _SECTION_ALIASES.items():
        if lowered == canonical:
            return canonical
        if lowered in aliases:
            return canonical
    return None


def _extract_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        heading_match = re.match(r"^([A-Za-z][A-Za-z\s\-/]+):\s*(.*)$", line)
        if heading_match:
            maybe_section = _canonical_section_name(heading_match.group(1))
            if maybe_section:
                current = maybe_section
                trailing = _clean_text(heading_match.group(2))
                if trailing:
                    sections.setdefault(current, []).append(trailing)
                continue
        if current is not None:
            sections.setdefault(current, []).append(line)
    return sections


def _infer_title(text: str) -> str | None:
    title_patterns = [
        r"(?:role|job title|position)\s*:\s*(.+)",
        r"hiring for\s+(.+)",
        r"seeking\s+(.+)",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            title = _clean_text(match.group(1))
            if title and not _looks_like_document_label(title):
                return title
    for line in text.splitlines()[:6]:
        cleaned = _clean_text(line)
        if not cleaned:
            continue
        if len(cleaned) > 100 or _looks_like_document_label(cleaned):
            continue
        lowered = cleaned.casefold()
        if any(token in lowered for token in ("engineer", "manager", "designer", "analyst", "scientist", "counsel", "lead", "specialist")):
            return cleaned.rstrip(":")
    return None


def _infer_seniority(text: str) -> str | None:
    patterns = (
        "staff",
        "principal",
        "director",
        "lead",
        "senior",
        "mid",
        "junior",
        "entry level",
        "entry-level",
    )
    lowered = text.casefold()
    for pattern in patterns:
        if pattern in lowered:
            return pattern.replace("-", " ")
    return None


def normalize_role_brief_text(text: str | None) -> RoleBriefContext:
    raw_text = _clean_text(text)
    if not raw_text:
        return RoleBriefContext(raw_text=None)

    sections = _extract_sections(text or "")

    context = RoleBriefContext(
        title=(lambda explicit: explicit if explicit and not _looks_like_document_label(explicit) else None)(_clean_text((sections.get("title") or [None])[0])) or _infer_title(text or ""),
        seniority=_clean_text((sections.get("seniority") or [None])[0]) or _infer_seniority(text or ""),
        must_haves=_normalize_bullets(sections.get("must_haves") or []),
        nice_to_haves=_normalize_bullets(sections.get("nice_to_haves") or []),
        leadership_expectations=_normalize_bullets(sections.get("leadership_expectations") or []),
        interview_focus=_normalize_bullets(sections.get("interview_focus") or []),
        red_flags=_normalize_bullets(sections.get("red_flags") or []),
        raw_text=raw_text,
    )

    if not context.must_haves:
        inferred_required = re.findall(r"(?:required|must have|needs?)\s+([^\.;\n]+)", text or "", flags=re.IGNORECASE)
        context.must_haves = _normalize_bullets(inferred_required)
    if not context.nice_to_haves:
        inferred_preferred = re.findall(r"(?:preferred|bonus|nice to have)\s+([^\.;\n]+)", text or "", flags=re.IGNORECASE)
        context.nice_to_haves = _normalize_bullets(inferred_preferred)
    return context


def render_candidate_review_input_text(role_context: RoleBriefContext) -> str:
    """Render a deterministic, workflow-safe input_text for candidate_review.

    The current `candidate_review` workflow already accepts `input_text`, and the
    repository contract positions it as the place to pass hiring context.
    This renderer keeps the request stable and avoids free-form prompt generation.
    """

    lines = [
        "Evaluate the CV against the normalized hiring thesis below.",
        "Keep the same candidate_review output shape: candidate fit summary, strengths, gaps, seniority signals, watchouts and interview next steps.",
        "Do not attribute role requirements to the candidate unless the CV explicitly supports them.",
        "Prefer grounded evidence from the CV over assumptions.",
    ]

    if role_context.title:
        lines.append(f"Role title: {role_context.title}")
    if role_context.seniority:
        lines.append(f"Target seniority: {role_context.seniority}")
    if role_context.must_haves:
        lines.append("Must-have requirements:")
        lines.extend(f"- {item}" for item in role_context.must_haves)
    if role_context.nice_to_haves:
        lines.append("Nice-to-have signals:")
        lines.extend(f"- {item}" for item in role_context.nice_to_haves)
    if role_context.leadership_expectations:
        lines.append("Leadership / scope expectations:")
        lines.extend(f"- {item}" for item in role_context.leadership_expectations)
    if role_context.interview_focus:
        lines.append("Interview focus:")
        lines.extend(f"- {item}" for item in role_context.interview_focus)
    if role_context.red_flags:
        lines.append("Role-specific watchouts:")
        lines.extend(f"- {item}" for item in role_context.red_flags)

    lines.append("Final instruction: preserve the existing candidate_review output style and evaluate fit specifically for this role context.")
    return "\n".join(lines).strip()


def build_candidate_review_input_text(*, raw_role_brief_text: str | None = None, fallback_input_text: str | None = None) -> str | None:
    if _clean_text(fallback_input_text):
        return _clean_text(fallback_input_text)
    role_context = normalize_role_brief_text(raw_role_brief_text)
    if not role_context.raw_text:
        return None
    return render_candidate_review_input_text(role_context)
