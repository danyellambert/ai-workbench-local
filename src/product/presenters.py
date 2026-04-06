from __future__ import annotations

from typing import Any

from src.structured.base import (
    CVAnalysisPayload,
    ChecklistPayload,
    DocumentAgentPayload,
    ExtractionPayload,
    SummaryPayload,
)

from .models import ProductWorkflowResult


def _source_rows(payload: DocumentAgentPayload) -> list[list[str]]:
    rows: list[list[str]] = []
    for source in payload.sources[:8]:
        if hasattr(source, "model_dump"):
            data = source.model_dump(mode="json")
        elif isinstance(source, dict):
            data = dict(source)
        else:
            continue
        rows.append(
            [
                str(data.get("source") or data.get("document_id") or "document"),
                str(data.get("chunk_id") or "-"),
                str(data.get("score") or data.get("vector_score") or "-"),
                str(data.get("snippet") or "-")[:220],
            ]
        )
    return rows


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _dedupe_texts(values: list[object], *, limit: int = 8) -> list[str]:
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


def _candidate_profile(payload: CVAnalysisPayload) -> dict[str, str]:
    name = _clean_text(getattr(payload.personal_info, "full_name", None) if payload.personal_info else None) or "Candidate"
    location = _clean_text(getattr(payload.personal_info, "location", None) if payload.personal_info else None) or "Location not explicit"
    primary_role = next((_clean_text(item.title) for item in payload.experience_entries if _clean_text(item.title)), "")
    skills = _dedupe_texts(list(payload.skills or []), limit=3)
    if primary_role and skills:
        headline = f"{primary_role} · {', '.join(skills[:2])}"
    else:
        headline = primary_role or ", ".join(skills) or "Profile under review"
    return {
        "name": name,
        "headline": headline,
        "location": location,
    }


def _candidate_haystack(payload: CVAnalysisPayload) -> str:
    parts: list[str] = []
    for values in (payload.skills, payload.languages, payload.strengths, payload.improvement_areas, payload.projects):
        parts.extend(str(item or "") for item in (values or []))
    for item in payload.experience_entries:
        parts.extend(
            [
                str(item.title or ""),
                str(item.organization or ""),
                str(item.location or ""),
                str(item.date_range or ""),
                str(item.description or ""),
                *(str(bullet or "") for bullet in (item.bullets or [])),
            ]
        )
    return " ".join(parts).lower()


def _candidate_has_signal(payload: CVAnalysisPayload, keywords: tuple[str, ...]) -> bool:
    haystack = _candidate_haystack(payload)
    return any(keyword in haystack for keyword in keywords)


def _candidate_strengths(payload: CVAnalysisPayload) -> list[str]:
    strengths = _dedupe_texts(list(payload.strengths or []), limit=4)
    if strengths:
        return strengths
    skills = _dedupe_texts(list(payload.skills or []), limit=3)
    if skills:
        return [f"Relevant skill evidence includes {', '.join(skills)}."]
    return []


def _candidate_watchouts(payload: CVAnalysisPayload, result_warnings: list[str]) -> list[str]:
    watchouts: list[object] = [*result_warnings, *(payload.improvement_areas or [])]
    if not payload.experience_entries:
        watchouts.append("Experience history is sparse or weakly structured in the current CV.")
    if not payload.skills:
        watchouts.append("The CV exposes limited explicit skill evidence.")
    if payload.experience_entries and not _candidate_has_signal(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        watchouts.append("Leadership and ownership signals are not explicit in the current CV.")
    if payload.experience_entries and not _candidate_has_signal(payload, ("product", "stakeholder", "customer", "business", "roadmap", "strategy")):
        watchouts.append("Product thinking / stakeholder management should be validated in interview.")
    return _dedupe_texts(watchouts, limit=5)


def _candidate_next_steps(payload: CVAnalysisPayload, watchouts: list[str]) -> list[str]:
    next_steps: list[object] = []
    for item in watchouts[:2]:
        normalized = _clean_text(item).rstrip(".")
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered.startswith(("validate", "confirm", "probe", "assess", "review")):
            next_steps.append(normalized)
        else:
            next_steps.append(f"Validate {normalized[0].lower() + normalized[1:]}")
    if _candidate_has_signal(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        next_steps.append("Probe measurable scope, business impact and cross-functional ownership.")
    else:
        next_steps.append("Run a focused interview on leadership, ownership and stakeholder management.")
    next_steps.append("Validate delivery depth with concrete examples of architecture, execution and business outcomes.")
    return _dedupe_texts(next_steps, limit=4)


def _candidate_signal_highlights(payload: CVAnalysisPayload) -> list[str]:
    highlights: list[object] = []
    if float(payload.experience_years or 0.0) > 0:
        highlights.append(f"{payload.experience_years:.1f} grounded year(s) of experience identified in the CV.")
    if len(payload.experience_entries or []) >= 3:
        highlights.append("Multiple structured roles suggest visible progression over time.")
    if _candidate_has_signal(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        highlights.append("Leadership / ownership language is visible in the role history.")
    if _candidate_has_signal(payload, ("production", "scale", "architecture", "platform", "rag", "mlops", "eval")):
        highlights.append("The CV references technical depth, platform work or production-scale delivery.")
    return _dedupe_texts(highlights, limit=4)


def _candidate_evidence_rows(payload: CVAnalysisPayload) -> list[list[str]]:
    rows: list[list[str]] = []
    if float(payload.experience_years or 0.0) > 0 or payload.experience_entries:
        rows.append(
            [
                "Experience",
                f"{float(payload.experience_years or 0.0):.1f} years" if float(payload.experience_years or 0.0) > 0 else "Not explicit",
                f"{len(payload.experience_entries or [])} structured role(s)",
                "Grounded seniority depth",
            ]
        )
    skills = _dedupe_texts(list(payload.skills or []), limit=3)
    if skills:
        rows.append(["Core skills", ", ".join(skills), f"{len(payload.skills or [])} mapped skill(s)", "Relevant capability coverage"])
    if payload.languages:
        languages = _dedupe_texts(list(payload.languages or []), limit=2)
        rows.append(["Languages", ", ".join(languages), f"{len(payload.languages or [])} language(s)", "Communication breadth"])
    if payload.experience_entries:
        latest = payload.experience_entries[0]
        rows.append(
            [
                "Recent anchor",
                _clean_text(latest.title) or "-",
                _clean_text(latest.organization) or _clean_text(latest.date_range) or "-",
                "Most recent grounded role evidence",
            ]
        )
    elif payload.education_entries:
        latest_education = payload.education_entries[0]
        rows.append(
            [
                "Education",
                _clean_text(latest_education.degree) or "-",
                _clean_text(latest_education.institution) or "-",
                "Latest grounded education evidence",
            ]
        )
    if not rows:
        rows.append(
            [
                "Grounding status",
                "Sparse CV evidence",
                "Few explicit candidate signals were extracted",
                "Manual review required before a confident hiring decision",
            ]
        )
    return rows[:4]


def build_product_result_sections(result: ProductWorkflowResult) -> dict[str, Any]:
    sections: dict[str, Any] = {
        "summary": result.summary,
        "highlights": list(result.highlights),
        "recommendation": result.recommendation,
        "warnings": list(result.warnings),
        "tables": [],
        "sources": [],
        "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
        "candidate_profile": None,
        "strengths": [],
        "watchouts": [],
        "next_steps": [],
        "evidence_highlights": [],
    }
    structured_result = result.structured_result
    payload = structured_result.validated_output if structured_result is not None else None
    if payload is None:
        return sections

    if isinstance(payload, DocumentAgentPayload):
        structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
        extraction_payload = structured_response.get("extraction_payload") if isinstance(structured_response.get("extraction_payload"), dict) else {}
        sections["watchouts"] = _dedupe_texts([*result.warnings, *(payload.limitations or []), payload.needs_review_reason], limit=5)
        sections["next_steps"] = _dedupe_texts(
            [
                *(payload.recommended_actions or []),
                *(item.get("description") for item in extraction_payload.get("action_items", []) if isinstance(item, dict)),
                result.recommendation,
            ],
            limit=4,
        )
        comparison_rows = [
            [
                finding.finding_type,
                finding.title,
                ", ".join(finding.documents or []) or "-",
                " | ".join(finding.evidence[:2]) or finding.description,
            ]
            for finding in payload.comparison_findings[:8]
        ]
        if comparison_rows:
            sections["tables"].append(
                {
                    "title": "Comparison findings",
                    "headers": ["Type", "Finding", "Documents", "Evidence"],
                    "rows": comparison_rows,
                }
            )
        risk_rows = [
            [
                str(item.get("description") or "risk"),
                str(item.get("owner") or "-"),
                str(item.get("due_date") or "-"),
                str(item.get("evidence") or item.get("impact") or "-"),
            ]
            for item in extraction_payload.get("risks", [])[:8]
            if isinstance(item, dict)
        ]
        if risk_rows:
            sections["tables"].append(
                {
                    "title": "Risk review",
                    "headers": ["Finding", "Owner", "Due", "Evidence"],
                    "rows": risk_rows,
                }
            )
        action_rows = [
            [
                str(item.get("description") or "action"),
                str(item.get("owner") or "-"),
                str(item.get("due_date") or "-"),
                str(item.get("status") or "suggested"),
            ]
            for item in extraction_payload.get("action_items", [])[:8]
            if isinstance(item, dict)
        ]
        if action_rows:
            sections["tables"].append(
                {
                    "title": "Action plan",
                    "headers": ["Action", "Owner", "Due", "Status"],
                    "rows": action_rows,
                }
            )
        sections["sources"] = _source_rows(payload)
        sections["evidence_highlights"] = sections["sources"][:4]
        return sections

    if isinstance(payload, CVAnalysisPayload):
        strengths = _candidate_strengths(payload)
        watchouts = _candidate_watchouts(payload, list(result.warnings))
        next_steps = _candidate_next_steps(payload, watchouts)
        evidence_rows = _candidate_evidence_rows(payload)
        sections["candidate_profile"] = _candidate_profile(payload)
        sections["strengths"] = strengths
        sections["watchouts"] = watchouts
        sections["next_steps"] = next_steps
        sections["evidence_highlights"] = evidence_rows
        sections["highlights"] = _dedupe_texts([*strengths, *_candidate_signal_highlights(payload), *(payload.skills or [])], limit=6)
        sections["warnings"] = watchouts
        if evidence_rows:
            sections["tables"].append(
                {
                    "title": "Evidence highlights",
                    "headers": ["Signal", "Value", "Detail", "Why it matters"],
                    "rows": evidence_rows,
                }
            )
        experience_rows = [
            [
                item.title or "-",
                item.organization or "-",
                item.date_range or "-",
                " | ".join(item.bullets[:2]) or item.description or "-",
            ]
            for item in payload.experience_entries[:8]
        ]
        if experience_rows:
            sections["tables"].append(
                {
                    "title": "Experience highlights",
                    "headers": ["Role", "Organization", "Date", "Evidence"],
                    "rows": experience_rows,
                }
            )
        education_rows = [
            [item.degree or "-", item.institution or "-", item.date_range or "-", item.location or "-"]
            for item in payload.education_entries[:6]
        ]
        if education_rows and len(sections["tables"]) < 2:
            sections["tables"].append(
                {
                    "title": "Education snapshot",
                    "headers": ["Degree", "Institution", "Date", "Location"],
                    "rows": education_rows,
                }
            )
        return sections

    if isinstance(payload, ChecklistPayload):
        sections["tables"].append(
            {
                "title": "Checklist actions",
                "headers": ["Status", "Priority", "Action", "Category"],
                "rows": [
                    [item.status, item.priority or "-", item.title, item.category or "-"]
                    for item in payload.items[:10]
                ],
            }
        )
        return sections

    if isinstance(payload, SummaryPayload):
        sections["tables"].append(
            {
                "title": "Topic map",
                "headers": ["Topic", "Relevance", "Key points"],
                "rows": [
                    [topic.title, f"{topic.relevance_score:.0%}", " | ".join(topic.key_points[:2]) or "-"]
                    for topic in payload.topics[:8]
                ],
            }
        )
        return sections

    if isinstance(payload, ExtractionPayload):
        sections["tables"].append(
            {
                "title": "Risk review",
                "headers": ["Finding", "Owner", "Due", "Evidence"],
                "rows": [
                    [item.description, item.owner or "-", item.due_date or "-", item.evidence or item.impact or "-"]
                    for item in payload.risks[:8]
                ],
            }
        )
        sections["tables"].append(
            {
                "title": "Action plan",
                "headers": ["Action", "Owner", "Due", "Status"],
                "rows": [
                    [item.description, item.owner or "-", item.due_date or "-", item.status or "suggested"]
                    for item in payload.action_items[:8]
                ],
            }
        )
    return sections