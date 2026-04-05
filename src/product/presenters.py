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


def build_product_result_sections(result: ProductWorkflowResult) -> dict[str, Any]:
    sections: dict[str, Any] = {
        "summary": result.summary,
        "highlights": list(result.highlights),
        "recommendation": result.recommendation,
        "warnings": list(result.warnings),
        "tables": [],
        "sources": [],
        "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
    }
    structured_result = result.structured_result
    payload = structured_result.validated_output if structured_result is not None else None
    if payload is None:
        return sections

    if isinstance(payload, DocumentAgentPayload):
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
        structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
        extraction_payload = structured_response.get("extraction_payload") if isinstance(structured_response.get("extraction_payload"), dict) else {}
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
        return sections

    if isinstance(payload, CVAnalysisPayload):
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
        if education_rows:
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