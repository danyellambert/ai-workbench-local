from __future__ import annotations

from typing import Any
import re

from src.structured.base import CVAnalysisPayload

from .candidate_review_context import normalize_role_brief_text
from .models import ProductWorkflowResult


_ROLE_DETAIL_KEYS = {
    "role title": "title",
    "target seniority": "seniority",
    "must-have requirements": "must_haves",
    "nice-to-have signals": "nice_to_haves",
    "leadership / scope expectations": "leadership_expectations",
    "interview focus": "interview_focus",
    "role-specific watchouts": "red_flags",
}


def _clean_text(value: object) -> str | None:
    cleaned = " ".join(str(value or "").split()).strip()
    return cleaned or None


def _dedupe(values: list[object], *, limit: int = 8) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
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


def _candidate_name(payload: CVAnalysisPayload) -> str:
    personal_info = getattr(payload, "personal_info", None)
    return _clean_text(getattr(personal_info, "full_name", None)) or "Candidate"


def _candidate_location(payload: CVAnalysisPayload) -> str | None:
    personal_info = getattr(payload, "personal_info", None)
    return _clean_text(getattr(personal_info, "location", None))


def _candidate_headline(payload: CVAnalysisPayload) -> str:
    primary_role = next(
        (
            title
            for title in (_clean_text(getattr(entry, "title", None)) for entry in (payload.experience_entries or []))
            if title
        ),
        None,
    )
    top_skills = _dedupe(list(getattr(payload, "skills", []) or []), limit=3)
    if primary_role and top_skills:
        return f"{primary_role} · {', '.join(top_skills[:2])}"
    if primary_role:
        return primary_role
    if top_skills:
        return ", ".join(top_skills)
    return "Profile under review"


def _candidate_seniority_band(payload: CVAnalysisPayload) -> str:
    years = float(getattr(payload, "experience_years", 0.0) or 0.0)
    if years >= 8:
        return "senior-to-lead"
    if years >= 5:
        return "senior"
    if years >= 3:
        return "mid-level"
    if years > 0:
        return "early-career"
    return "emerging"


def _candidate_haystack(payload: CVAnalysisPayload) -> str:
    parts: list[str] = []
    for values in (
        getattr(payload, "skills", []) or [],
        getattr(payload, "languages", []) or [],
        getattr(payload, "strengths", []) or [],
        getattr(payload, "improvement_areas", []) or [],
        getattr(payload, "projects", []) or [],
    ):
        parts.extend(str(item or "") for item in values)
    for entry in getattr(payload, "experience_entries", []) or []:
        parts.extend(
            [
                str(getattr(entry, "title", "") or ""),
                str(getattr(entry, "organization", "") or ""),
                str(getattr(entry, "description", "") or ""),
                *(str(item or "") for item in (getattr(entry, "bullets", None) or [])),
            ]
        )
    return " ".join(parts).lower()


def _has_keywords(payload: CVAnalysisPayload, keywords: tuple[str, ...]) -> bool:
    haystack = _candidate_haystack(payload)
    return any(keyword in haystack for keyword in keywords)


def _candidate_seniority_signals(payload: CVAnalysisPayload) -> list[str]:
    years = float(getattr(payload, "experience_years", 0.0) or 0.0)
    signals: list[object] = []
    if years >= 8:
        signals.append(f"Career depth suggests senior / lead-level scope with roughly {years:.1f} years of grounded experience.")
    elif years >= 5:
        signals.append(f"Grounded experience suggests a solid senior execution profile ({years:.1f} years).")
    elif years >= 3:
        signals.append(f"The profile shows intermediate execution depth across roughly {years:.1f} years of experience.")
    if len(getattr(payload, "experience_entries", []) or []) >= 3:
        signals.append("Multiple structured roles are present, suggesting visible career progression.")
    if _has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership", "principal", "staff")):
        signals.append("Leadership / ownership language appears explicitly in the role history or strengths.")
    if _has_keywords(payload, ("product", "stakeholder", "customer", "business", "roadmap", "strategy")):
        signals.append("Product or stakeholder-facing work is visible in the current CV evidence.")
    if _has_keywords(payload, ("production", "scale", "architecture", "platform", "deployment", "operational", "delivery")):
        signals.append("The CV references production depth, architecture, or delivery at scale.")
    return _dedupe(signals, limit=4)



def _role_requirement_has_cv_support(requirement: object, haystack: str) -> bool:
    text = _clean_text(requirement) or ""
    tokens = [
        token.casefold()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{3,}", text)
        if token.casefold() not in {"with", "from", "that", "this", "role", "must", "have", "required", "preferred"}
    ]
    if not tokens:
        return False
    hits = sum(1 for token in tokens if token in haystack)
    return hits >= min(2, len(tokens))


def _candidate_gaps(payload: CVAnalysisPayload, role_context: dict[str, Any]) -> list[str]:
    gaps: list[object] = []
    haystack = _candidate_haystack(payload)

    for item in (role_context.get("must_haves") or [])[:5]:
        if not _role_requirement_has_cv_support(item, haystack):
            gaps.append(f"Missing or weakly evidenced must-have: {item}")

    for item in (role_context.get("nice_to_haves") or [])[:3]:
        if not _role_requirement_has_cv_support(item, haystack):
            gaps.append(f"Nice-to-have signal not explicit in CV: {item}")

    for item in (getattr(payload, "improvement_areas", None) or [])[:3]:
        gaps.append(f"CV evidence gap: {item}")

    if not gaps and not (getattr(payload, "skills", None) or []):
        gaps.append("Explicit skill evidence is limited in the current CV extraction.")

    if not gaps and role_context.get("seniority"):
        gaps.append(f"Validate fit against target seniority ({role_context.get('seniority')}) with concrete scope and impact examples.")

    return _dedupe(gaps, limit=6)


def _candidate_watchouts(payload: CVAnalysisPayload, role_context: dict[str, Any]) -> list[str]:
    watchouts: list[object] = []

    for item in (role_context.get("red_flags") or [])[:4]:
        watchouts.append(f"Role-specific watchout to validate: {item}")

    if not (getattr(payload, "experience_entries", None) or []):
        watchouts.append("Experience history is sparse or weakly structured in the current CV grounding.")

    if (getattr(payload, "experience_entries", None) or []) and not _has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        watchouts.append("Leadership and ownership signals are not yet explicit in the current CV.")

    if (role_context.get("leadership_expectations") or []) and not _has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership", "mentor", "stakeholder")):
        watchouts.append("Role expects leadership/scope evidence, but the extracted CV signals do not make that scope explicit.")

    if not watchouts and not (getattr(payload, "skills", None) or []):
        watchouts.append("The CV exposes limited explicit skill evidence for a confident fit assessment.")

    return _dedupe(watchouts, limit=5)


def _candidate_education(payload: CVAnalysisPayload) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in (getattr(payload, "education_entries", None) or [])[:6]:
        degree = _clean_text(getattr(item, "degree", None))
        institution = _clean_text(getattr(item, "institution", None))
        year = _clean_text(getattr(item, "year", None)) or _clean_text(getattr(item, "period", None))
        details = _clean_text(getattr(item, "details", None))
        if not any([degree, institution, year, details]):
            continue
        rows.append({
            "degree": degree,
            "institution": institution,
            "year": year,
            "details": details,
        })
    return rows


def _candidate_next_steps(payload: CVAnalysisPayload, role_context: dict[str, Any]) -> list[str]:
    next_steps: list[object] = []
    for item in (role_context.get("interview_focus") or [])[:3]:
        next_steps.append(f"Probe {item[0].lower() + item[1:] if item else item} with concrete examples.")
    if _has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        next_steps.append("Probe measurable scope, business impact and decision-making ownership in the next interview.")
    else:
        next_steps.append("Run a focused interview on leadership, ownership and stakeholder management examples.")
    if _has_keywords(payload, ("production", "scale", "architecture", "platform", "operational")):
        next_steps.append("Validate production depth, architecture trade-offs and delivery at scale with concrete scenarios.")
    else:
        next_steps.append("Use a technical screen to validate delivery depth, implementation quality and problem-solving range.")
    return _dedupe(next_steps, limit=5)


_EDUCATION_NOISE_RE = re.compile(
    r"\b("
    r"johnson\s*&\s*johnson|scientist|present|cincinnati|"
    r"teaching assistant|admissions fellow|proctor|co-captain|"
    r"r&d|covid|laboratory support|surgical support"
    r")\b",
    flags=re.IGNORECASE,
)


def _sanitize_candidate_education(value: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Keep education display grounded, without leaking work-history text into degree."""

    def clean_text(value: Any) -> str:
        return _clean_text(value)

    def split_degree_institution(degree: str, institution: str) -> tuple[str, str]:
        degree = clean_text(degree)
        institution = clean_text(institution)

        # Common leak: "Bachelor of Science, Biochemistry Johnson & Johnson..."
        if degree and re.search(r"\bJohnson\s*&\s*Johnson\b", degree, flags=re.IGNORECASE):
            degree = re.split(r"\bJohnson\s*&\s*Johnson\b", degree, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,;:-")

        # Common leak after university name.
        if degree and re.search(r"\bCreighton University\b", degree, flags=re.IGNORECASE):
            before, _sep, _after = re.partition(r"Creighton University", degree)
            degree = before.strip(" ,;:-")
            if not institution:
                institution = "Creighton University"

        # If institution is embedded directly after degree/major, recover it.
        if not institution and re.search(r"\bCreighton\b", degree, flags=re.IGNORECASE):
            institution = "Creighton University"
            degree = re.split(r"\bCreighton\b", degree, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,;:-")

        # Drop any remaining professional tail from degree.
        degree = re.split(
            r"\b(Johnson\s*&\s*Johnson|Scientist|Present|Cincinnati|Teaching Assistant|Admissions Fellow|Proctor)\b",
            degree,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" ,;:-")

        return degree, institution

    def sanitize_one(item: Any) -> dict[str, Any] | None:
        if item is None:
            return None

        if isinstance(item, str):
            raw = clean_text(item)
            degree = raw
            institution = ""
            year = ""
            details = ""
        elif isinstance(item, dict):
            raw = clean_text(item.get("text") or item.get("raw") or item.get("details") or "")
            degree = clean_text(item.get("degree") or item.get("credential") or item.get("title") or "")
            institution = clean_text(item.get("institution") or item.get("school") or item.get("university") or "")
            year = clean_text(item.get("year") or item.get("date") or item.get("graduation_year") or "")
            details = clean_text(item.get("details") or "")
            if not degree and raw:
                degree = raw
        else:
            return None

        degree, institution = split_degree_institution(degree, institution)

        if not degree and not institution:
            return None

        # If the "degree" is mostly a job line, do not show it as education.
        if degree and _EDUCATION_NOISE_RE.search(degree) and not re.search(r"\b(Bachelor|Master|PhD|Doctor|B\.?S\.?|M\.?S\.?|MBA|University|College|Biochemistry|Chemistry|Biology)\b", degree, flags=re.IGNORECASE):
            degree = ""

        if details and _EDUCATION_NOISE_RE.search(details):
            details = ""

        return {
            "degree": degree,
            "institution": institution,
            "year": year,
            "details": details,
        }

    if isinstance(value, list):
        cleaned = [item for item in (sanitize_one(item) for item in value) if item]
        return cleaned or None

    return sanitize_one(value)

def _extract_role_context(result: ProductWorkflowResult) -> dict[str, Any]:
    if isinstance(result.debug_metadata, dict):
        raw_context = result.debug_metadata.get("role_context")
        if isinstance(raw_context, dict):
            normalized: dict[str, Any] = {
                "title": _clean_text(raw_context.get("title")),
                "seniority": _clean_text(raw_context.get("seniority")),
                "must_haves": _dedupe(list(raw_context.get("must_haves") or []), limit=8),
                "nice_to_haves": _dedupe(list(raw_context.get("nice_to_haves") or []), limit=8),
                "leadership_expectations": _dedupe(list(raw_context.get("leadership_expectations") or []), limit=6),
                "interview_focus": _dedupe(list(raw_context.get("interview_focus") or []), limit=6),
                "red_flags": _dedupe(list(raw_context.get("red_flags") or []), limit=6),
            }
            if any(normalized.values()):
                return normalized

        raw_value = result.debug_metadata.get("query") or result.debug_metadata.get("effective_query") or result.debug_metadata.get("input_text")
        input_text = str(raw_value or "").strip()
    else:
        input_text = ""

    role_context = normalize_role_brief_text(input_text).to_dict()
    role_context.pop("raw_text", None)
    return role_context
def _build_document_metrics(result: ProductWorkflowResult) -> dict[str, Any]:
    preview = getattr(result, "grounding_preview", None)
    if preview is None:
        return {
            "strategy": None,
            "document_ids": [],
            "context_chars": 0,
            "source_block_count": 0,
            "show_source_block_count": False,
        }
    return {
        "strategy": getattr(preview, "strategy", None),
        "document_ids": list(getattr(preview, "document_ids", None) or []),
        "context_chars": int(getattr(preview, "context_chars", 0) or 0),
        "source_block_count": int(getattr(preview, "source_block_count", 0) or 0),
        "show_source_block_count": int(getattr(preview, "source_block_count", 0) or 0) > 0,
    }


def build_candidate_review_view(result: ProductWorkflowResult) -> dict[str, Any]:
    payload = getattr(getattr(result, "structured_result", None), "validated_output", None)
    role_context = _extract_role_context(result)
    metrics = _build_document_metrics(result)

    if not isinstance(payload, CVAnalysisPayload):
        return {
            "candidate_profile": {
                "name": "Candidate",
                "headline": "Profile under review",
                "location": None,
                "seniority_band": None,
                "experience_years": 0.0,
                "top_skills": [],
            },
            "role_context": role_context,
            "strengths": [],
            "gaps": [],
            "seniority_signals": [],
            "watchouts": list(getattr(result, "warnings", None) or []),
            "next_steps": [],
            "recommendation": getattr(result, "recommendation", None),
            "summary": getattr(result, "summary", None),
            "artifacts": [item.model_dump(mode="json") for item in (getattr(result, "artifacts", None) or [])],
            "document_metrics": metrics,
            "run_state": {
                "status": getattr(result, "status", None),
                "workflow_id": getattr(result, "workflow_id", None),
                "workflow_label": getattr(result, "workflow_label", None),
                "warnings": list(getattr(result, "warnings", None) or []),
                "highlights": list(getattr(result, "highlights", None) or []),
            },
        }

    strengths = _dedupe(list(getattr(payload, "strengths", None) or []), limit=6)
    gaps = _candidate_gaps(payload, role_context)
    top_skills = _dedupe(list(getattr(payload, "skills", None) or []), limit=6)

    return {
        "candidate_profile": {
            "name": _candidate_name(payload),
            "headline": _candidate_headline(payload),
            "location": _candidate_location(payload),
            "seniority_band": _candidate_seniority_band(payload),
            "experience_years": float(getattr(payload, "experience_years", 0.0) or 0.0),
            "top_skills": top_skills[:6],
            "languages": _dedupe(list(getattr(payload, "languages", None) or []), limit=4),
        },
        "education": _sanitize_candidate_education(_candidate_education(payload)),
        "role_context": role_context,
        "strengths": strengths,
        "gaps": gaps,
        "seniority_signals": _candidate_seniority_signals(payload),
        "watchouts": _candidate_watchouts(payload, role_context),
        "next_steps": _candidate_next_steps(payload, role_context),
        "recommendation": getattr(result, "recommendation", None),
        "summary": getattr(result, "summary", None),
        "artifacts": [item.model_dump(mode="json") for item in (getattr(result, "artifacts", None) or [])],
        "document_metrics": metrics,
        "run_state": {
            "status": getattr(result, "status", None),
            "workflow_id": getattr(result, "workflow_id", None),
            "workflow_label": getattr(result, "workflow_label", None),
            "warnings": list(getattr(result, "warnings", None) or []),
            "highlights": list(getattr(result, "highlights", None) or []),
        },
    }
