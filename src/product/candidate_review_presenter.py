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
    gaps: list[object] = [*(getattr(payload, "improvement_areas", None) or [])]
    haystack = _candidate_haystack(payload)

    for item in (role_context.get("must_haves") or [])[:4]:
        if not _role_requirement_has_cv_support(item, haystack):
            gaps.append(f"Role requirement needs validation because it is not explicit in the CV evidence: {item}")

    if not gaps and not (getattr(payload, "skills", None) or []):
        gaps.append("Explicit skill evidence is limited in the current CV extraction.")

    if not gaps and (getattr(payload, "experience_entries", None) or []) and not _has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        gaps.append("Leadership and ownership evidence should be validated because it is not explicit in the extracted CV signals.")

    if not gaps and role_context.get("seniority"):
        gaps.append(f"Validate fit against the target seniority ({role_context.get('seniority')}) because no explicit gap was produced by the model.")

    return _dedupe(gaps, limit=6)

def _candidate_watchouts(payload: CVAnalysisPayload, role_context: dict[str, Any]) -> list[str]:
    watchouts: list[object] = [*(getattr(payload, "improvement_areas", None) or [])]
    if not (getattr(payload, "experience_entries", None) or []):
        watchouts.append("Experience history is sparse or weakly structured in the current CV grounding.")
    if not (getattr(payload, "skills", None) or []):
        watchouts.append("The CV exposes limited explicit skill evidence for a confident fit assessment.")
    if (getattr(payload, "experience_entries", None) or []) and not _has_keywords(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        watchouts.append("Leadership and ownership signals are not yet explicit in the current CV.")
    for item in (role_context.get("red_flags") or [])[:2]:
        watchouts.append(f"Validate against role-specific watchout: {item}")
    return _dedupe(watchouts, limit=5)


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


def _extract_role_context(result: ProductWorkflowResult) -> dict[str, Any]:
    input_text = ""
    if isinstance(result.debug_metadata, dict):
        raw_value = result.debug_metadata.get("query") or result.debug_metadata.get("effective_query") or result.debug_metadata.get("input_text")
        input_text = str(raw_value or "").strip()
    role_context = normalize_role_brief_text(input_text)
    return role_context.to_dict()


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
