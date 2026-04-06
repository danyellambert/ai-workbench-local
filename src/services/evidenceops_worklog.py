from __future__ import annotations

from datetime import datetime
from typing import Any

from ..structured.base import ComparisonFinding, DocumentAgentPayload


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _short_title(text: str, *, max_words: int = 8) -> str:
    cleaned = _clean_text(text).rstrip(".?!")
    if not cleaned:
        return "Finding"
    words = cleaned.split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


def _serialize_sources(payload: DocumentAgentPayload) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in payload.sources:
        if hasattr(item, "model_dump"):
            rows.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            rows.append(item)
    return rows


def _extract_action_items(structured_response: dict[str, Any]) -> list[dict[str, object]]:
    extraction_payload = structured_response.get("extraction_payload") if isinstance(structured_response.get("extraction_payload"), dict) else {}
    raw_action_items = extraction_payload.get("action_items") if isinstance(extraction_payload.get("action_items"), list) else []

    normalized: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in raw_action_items:
        if not isinstance(item, dict):
            continue
        description = _clean_text(item.get("description"))
        if not description:
            continue
        owner = _clean_text(item.get("owner")) or None
        due_date = _clean_text(item.get("due_date")) or None
        status = _clean_text(item.get("status")) or "suggested"
        evidence = _clean_text(item.get("evidence")) or None
        key = (description.casefold(), (owner or "").casefold(), (due_date or "").casefold())
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "description": description,
                "owner": owner,
                "due_date": due_date,
                "status": status,
                "evidence": evidence,
            }
        )
    return normalized


def _extract_findings(payload: DocumentAgentPayload, structured_response: dict[str, Any]) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []

    for item in payload.comparison_findings:
        if isinstance(item, ComparisonFinding):
            findings.append(
                {
                    "finding_type": item.finding_type,
                    "title": _clean_text(item.title) or _short_title(item.description),
                    "description": _clean_text(item.description),
                    "documents": list(item.documents or []),
                    "evidence": [
                        snippet
                        for snippet in [_clean_text(value) for value in (item.evidence or [])]
                        if snippet
                    ],
                }
            )

    extraction_payload = structured_response.get("extraction_payload") if isinstance(structured_response.get("extraction_payload"), dict) else {}
    raw_risks = extraction_payload.get("risks") if isinstance(extraction_payload.get("risks"), list) else []
    for risk in raw_risks:
        if not isinstance(risk, dict):
            continue
        description = _clean_text(risk.get("description"))
        if not description:
            continue
        findings.append(
            {
                "finding_type": "risk",
                "title": _short_title(description),
                "description": description,
                "documents": [],
                "evidence": [evidence for evidence in [_clean_text(risk.get("evidence"))] if evidence],
                "impact": _clean_text(risk.get("impact")) or None,
                "owner": _clean_text(risk.get("owner")) or None,
                "due_date": _clean_text(risk.get("due_date")) or None,
            }
        )

    for gap in structured_response.get("gaps") or structured_response.get("missing_information") or []:
        gap_text = _clean_text(gap)
        if not gap_text:
            continue
        findings.append(
            {
                "finding_type": "gap",
                "title": _short_title(gap_text),
                "description": gap_text,
                "documents": [],
                "evidence": [],
            }
        )

    restrictions = structured_response.get("restrictions") if isinstance(structured_response.get("restrictions"), list) else []
    for restriction in restrictions:
        restriction_text = _clean_text(restriction)
        if not restriction_text:
            continue
        findings.append(
            {
                "finding_type": "restriction",
                "title": _short_title(restriction_text),
                "description": restriction_text,
                "documents": [],
                "evidence": [],
            }
        )

    return findings


def _build_evidence_pack(
    *,
    review_type: str,
    summary: str,
    document_ids: list[str],
    serialized_sources: list[dict[str, object]],
    findings: list[dict[str, object]],
    action_items: list[dict[str, object]],
    recommended_actions: list[str],
    limitations: list[str],
    needs_review: bool,
    needs_review_reason: str | None,
) -> dict[str, object]:
    finding_type_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    due_date_counts: dict[str, int] = {}

    for finding in findings:
        if not isinstance(finding, dict):
            continue
        finding_type = _clean_text(finding.get("finding_type")) or "unclassified"
        finding_type_counts[finding_type] = int(finding_type_counts.get(finding_type, 0)) + 1

    for action in action_items:
        if not isinstance(action, dict):
            continue
        owner = _clean_text(action.get("owner"))
        status = _clean_text(action.get("status"))
        due_date = _clean_text(action.get("due_date"))
        if owner:
            owner_counts[owner] = int(owner_counts.get(owner, 0)) + 1
        if status:
            status_counts[status] = int(status_counts.get(status, 0)) + 1
        if due_date:
            due_date_counts[due_date] = int(due_date_counts.get(due_date, 0)) + 1

    source_documents = sorted(
        {
            _clean_text(item.get("source") or item.get("document_id") or "")
            for item in serialized_sources
            if isinstance(item, dict)
        }
        - {""}
    )

    return {
        "evidence_pack_version": "1.0",
        "review_type": review_type,
        "summary": summary,
        "document_ids": list(document_ids),
        "source_documents": source_documents,
        "source_count": len(serialized_sources),
        "findings_count": len(findings),
        "action_items_count": len(action_items),
        "recommended_actions_count": len(recommended_actions),
        "limitations_count": len(limitations),
        "finding_type_counts": finding_type_counts,
        "owner_counts": owner_counts,
        "status_counts": status_counts,
        "due_date_counts": due_date_counts,
        "needs_review": bool(needs_review),
        "needs_review_reason": needs_review_reason,
    }


def build_evidenceops_worklog_entry(
    *,
    payload: DocumentAgentPayload,
    query: str,
    document_ids: list[str],
    execution_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = execution_metadata if isinstance(execution_metadata, dict) else {}
    structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
    serialized_sources = _serialize_sources(payload)
    action_items = _extract_action_items(structured_response)
    findings = _extract_findings(payload, structured_response)
    recommended_actions = [
        text for text in [_clean_text(value) for value in payload.recommended_actions] if text
    ]
    limitations = [
        text for text in [_clean_text(value) for value in payload.limitations] if text
    ]
    related_documents = sorted(
        {
            str(value)
            for value in [*document_ids, *payload.compared_documents]
            if str(value or "").strip()
        }
    )
    review_type = _clean_text(structured_response.get("review_type")) or _clean_text(payload.tool_used)
    evidence_pack = _build_evidence_pack(
        review_type=review_type,
        summary=_clean_text(payload.summary),
        document_ids=related_documents,
        serialized_sources=serialized_sources,
        findings=findings,
        action_items=action_items,
        recommended_actions=recommended_actions,
        limitations=limitations,
        needs_review=bool(payload.needs_review),
        needs_review_reason=payload.needs_review_reason,
    )

    return {
        "timestamp": datetime.now().isoformat(),
        "query": _clean_text(query),
        "task_type": "document_agent",
        "review_type": review_type,
        "user_intent": payload.user_intent,
        "tool_used": payload.tool_used,
        "summary": _clean_text(payload.summary),
        "confidence": float(payload.confidence or 0.0),
        "needs_review": bool(payload.needs_review),
        "needs_review_reason": payload.needs_review_reason,
        "document_ids": related_documents,
        "source_count": len(serialized_sources),
        "source_document_count": len(evidence_pack.get("source_documents") or []),
        "source_documents": [
            _clean_text(item.get("source") or item.get("document_id") or "source")
            for item in serialized_sources
            if _clean_text(item.get("source") or item.get("document_id") or "")
        ],
        "finding_count": len(findings),
        "findings": findings,
        "action_item_count": len(action_items),
        "action_items": action_items,
        "recommended_actions": recommended_actions,
        "limitations": limitations,
        "guardrails_applied": [
            text for text in [_clean_text(value) for value in payload.guardrails_applied] if text
        ],
        "sources": serialized_sources,
        "evidence_pack": evidence_pack,
        "workflow_id": metadata.get("workflow_id"),
        "execution_strategy_used": metadata.get("execution_strategy_used"),
    }