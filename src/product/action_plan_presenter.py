from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any

from src.structured.base import DocumentAgentPayload, ExtractionPayload

from .models import ProductWorkflowResult
from .presenters import (
    _best_source_match,
    _clean_optional_text,
    _clean_text,
    _collect_document_agent_sources,
    _dedupe_texts,
    _infer_finding_severity,
)

_ACTION_STATUS_ALIASES = {
    "done": "done",
    "completed": "done",
    "complete": "done",
    "closed": "done",
    "resolved": "done",
    "finished": "done",
    "approved": "done",
    "in_progress": "in_progress",
    "in progress": "in_progress",
    "ongoing": "in_progress",
    "working": "in_progress",
    "started": "in_progress",
    "running": "in_progress",
    "blocked": "blocked",
    "waiting": "blocked",
    "awaiting": "blocked",
    "pending dependency": "blocked",
    "stalled": "blocked",
    "open": "open",
    "pending": "open",
    "todo": "open",
    "to do": "open",
    "planned": "open",
    "suggested": "open",
}

_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _coerce_extraction_payload(raw_value: object) -> ExtractionPayload | None:
    if isinstance(raw_value, ExtractionPayload):
        return raw_value
    if not isinstance(raw_value, dict) or not raw_value:
        return None
    try:
        return ExtractionPayload.model_validate(raw_value)
    except Exception:
        return None


def _normalize_status(value: object) -> str:
    cleaned = _clean_text(value).casefold().replace("-", " ").replace("/", " ")
    return _ACTION_STATUS_ALIASES.get(cleaned, "open")


def _normalize_priority(*signals: object) -> str:
    inferred = _infer_finding_severity(*signals)
    if inferred in _PRIORITY_RANK:
        return inferred
    return "medium"


def _document_ids_from_result(result: ProductWorkflowResult) -> list[str]:
    preview_ids = list(result.grounding_preview.document_ids) if result.grounding_preview is not None else []
    if preview_ids:
        return [str(item).strip() for item in preview_ids if str(item).strip()]
    if isinstance(result.debug_metadata, dict):
        return [str(item).strip() for item in (result.debug_metadata.get("source_documents") or []) if str(item).strip()]
    return []


def _title_from_text(value: object, *, fallback: str) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return fallback
    if len(cleaned) <= 96:
        return cleaned
    shortened = cleaned[:93].rsplit(" ", 1)[0].strip()
    return f"{shortened}..." if shortened else fallback


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        cleaned = _clean_optional_text(value)
        if cleaned:
            return cleaned
    return None


def _derive_objective(
    *,
    result: ProductWorkflowResult,
    payload: DocumentAgentPayload | None,
    extraction_payload: ExtractionPayload | None,
    document_ids: list[str],
) -> str:
    subject = _clean_optional_text(getattr(extraction_payload, "main_subject", None) if extraction_payload is not None else None)
    if not subject:
        payload_summary = _clean_optional_text(getattr(payload, "summary", None) if payload is not None else None)
        if payload_summary and ":" in payload_summary:
            prefix = _clean_optional_text(payload_summary.split(":", 1)[0])
            if prefix and prefix.casefold() not in {"operational extraction", "extraction"}:
                subject = prefix
    if subject:
        return f"Drive grounded follow-up actions for {subject}."
    recommendation = _clean_optional_text(result.recommendation)
    if recommendation:
        return recommendation
    if document_ids:
        document_count = len(document_ids)
        noun = "document" if document_count == 1 else "documents"
        return f"Convert grounded findings from {document_count} selected {noun} into tracked execution tasks."
    return "Convert grounded findings into tracked execution tasks."


def _due_sort_key(value: object) -> tuple[int, str]:
    cleaned = _clean_optional_text(value)
    if not cleaned:
        return (2, "")
    for parser in (
        lambda text: datetime.fromisoformat(text.replace("Z", "+00:00")).date(),
        lambda text: date.fromisoformat(text),
    ):
        try:
            parsed = parser(cleaned)
            return (0, parsed.isoformat())
        except Exception:
            continue
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if digits:
        return (1, cleaned)
    return (2, cleaned)


def _serialize_action_item(
    *,
    index: int,
    title: str,
    owner: str | None,
    due_date: str | None,
    raw_status: object,
    evidence: str | None,
    raw_sources: list[dict[str, object]],
    notes: str | None = None,
) -> dict[str, Any]:
    matched_source = _best_source_match(raw_sources, title, evidence, notes)
    source_label = _clean_optional_text(matched_source.get("source"))
    source_document_id = _clean_optional_text(matched_source.get("document_id"))
    source_snippet = _clean_optional_text(matched_source.get("snippet"))
    rationale = _first_non_empty(evidence, source_snippet, notes)
    return {
        "id": f"action-item-{index}",
        "title": title,
        "owner": owner,
        "due_date": due_date,
        "priority": _normalize_priority(title, evidence, notes, source_label, source_snippet),
        "status": _normalize_status(raw_status),
        "source": source_label,
        "evidence": evidence,
        "rationale": rationale,
        "notes": notes,
        "document_id": source_document_id,
    }


def _fallback_action_items(
    *,
    payload: DocumentAgentPayload,
    raw_sources: list[dict[str, object]],
) -> list[dict[str, Any]]:
    structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
    candidate_titles = _dedupe_texts(
        [
            *(structured_response.get("actions") or []),
            *(payload.recommended_actions or []),
            *(payload.checklist_preview or []),
        ],
        limit=8,
    )
    normalized: list[dict[str, Any]] = []
    for index, title in enumerate(candidate_titles, start=1):
        normalized.append(
            _serialize_action_item(
                index=index,
                title=title,
                owner=None,
                due_date=None,
                raw_status="open",
                evidence=None,
                raw_sources=raw_sources,
            )
        )
    return normalized


_ACTION_SECTION_MARKERS = ("Action Register", "Corrective Actions")
_ACTION_STOP_MARKERS = (
    "4. Closure Criteria",
    "Next committee checkpoint",
    "Meeting Summary",
    "Quoted Thread Excerpt",
)
_ACTION_ROW_REGEX = re.compile(
    r"(?P<body>.+?)\s+(?P<due>\d{4}-\d{2}-\d{2})\s+(?P<status>In progress|Open|Done|Blocked|Pending|Recommended)",
    re.IGNORECASE | re.DOTALL,
)
_OWNER_CANDIDATE_REGEX = re.compile(
    r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}|IT Operations|Security Engineering|Vendor Management|Compliance Operations|Identity Ops|Security Governance|Audit PMO|Operations|Compliance|Procurement|Corporate Secretary)\b"
)


def _split_preview_sources(preview_text: str | None) -> list[tuple[str | None, str]]:
    text = str(preview_text or "")
    if not text.strip():
        return []
    parts = re.split(r"\[Source:\s*([^\]]+)\]", text)
    if len(parts) <= 1:
        return [(None, text)]
    blocks: list[tuple[str | None, str]] = []
    for index in range(1, len(parts), 2):
        source = _clean_optional_text(parts[index])
        body = parts[index + 1] if index + 1 < len(parts) else ""
        if body.strip():
            blocks.append((source, body))
    return blocks


def _owner_candidates_from_preview(preview_text: str | None) -> list[str]:
    candidates = {
        _clean_text(match.group(0))
        for match in _OWNER_CANDIDATE_REGEX.finditer(str(preview_text or ""))
        if _clean_text(match.group(0))
    }
    return sorted(candidates, key=lambda item: (-len(item), item.casefold()))


def _normalize_section_text(text: str) -> str:
    cleaned = re.sub(r"\[Page\s+\d+\]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_action_regions(preview_text: str | None) -> list[tuple[str | None, str]]:
    regions: list[tuple[str | None, str]] = []
    for source_label, body in _split_preview_sources(preview_text):
        normalized_body = _normalize_section_text(body)
        if not normalized_body:
            continue
        for marker in _ACTION_SECTION_MARKERS:
            marker_index = normalized_body.find(marker)
            if marker_index < 0:
                continue
            section = normalized_body[marker_index:]
            stop_positions = [section.find(stop_marker) for stop_marker in _ACTION_STOP_MARKERS if section.find(stop_marker) > len(marker)]
            if stop_positions:
                section = section[: min(stop_positions)]
            regions.append((source_label, section.strip()))
    return regions


def _split_title_and_owner(body: str, owner_candidates: list[str]) -> tuple[str, str | None]:
    cleaned = _clean_text(body)
    if not cleaned:
        return "", None
    for candidate in owner_candidates:
        if cleaned.endswith(f" {candidate}"):
            title = _clean_text(cleaned[: -len(candidate)]).strip()
            title = title[:-1].strip() if title.endswith((":", "-")) else title
            if len(title) >= 8:
                return title, candidate
    return cleaned, None


def _heuristic_action_items_from_preview(
    *,
    preview_text: str | None,
    raw_sources: list[dict[str, object]],
) -> list[dict[str, Any]]:
    owner_candidates = _owner_candidates_from_preview(preview_text)
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for source_label, section in _extract_action_regions(preview_text):
        matches = list(_ACTION_ROW_REGEX.finditer(section))
        for index, match in enumerate(matches):
            body = _clean_text(match.group("body"))
            if body.lower().startswith("action register"):
                body = _clean_text(body[len("Action Register") :])
            if body.lower().startswith("corrective actions"):
                body = _clean_text(body[len("Corrective Actions") :])
            body = re.sub(r"^Action Item Owner Due Date Status Evidence / Source\s+", "", body, flags=re.I)
            body = re.sub(r"^Action Owner Due Date Status\s+", "", body, flags=re.I)
            if not body:
                continue
            due_date = _clean_optional_text(match.group("due"))
            raw_status = _clean_optional_text(match.group("status")) or "open"
            evidence_start = match.end()
            evidence_end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
            evidence = _clean_optional_text(section[evidence_start:evidence_end])
            title, owner = _split_title_and_owner(body, owner_candidates)
            if not title or len(title) < 6:
                continue
            key = (title.casefold(), owner, due_date)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                _serialize_action_item(
                    index=len(normalized) + 1,
                    title=title,
                    owner=owner,
                    due_date=due_date,
                    raw_status=raw_status,
                    evidence=evidence,
                    raw_sources=[*raw_sources, {"source": source_label, "snippet": evidence}] if source_label else raw_sources,
                )
            )
    return normalized



def _action_card_summary_from_item(item: object) -> str | None:
    for key in ("card_summary", "summary", "short_summary", "action_summary", "narrative", "explanation"):
        value = getattr(item, key, None)
        if value is None and isinstance(item, dict):
            value = item.get(key)
        cleaned = _clean_optional_text(value)
        if cleaned:
            return cleaned
    return None

def _normalize_action_items(
    *,
    payload: DocumentAgentPayload,
    extraction_payload: ExtractionPayload | None,
    raw_sources: list[dict[str, object]],
    preview_text: str | None = None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    if extraction_payload is not None:
        for index, item in enumerate(extraction_payload.action_items, start=1):
            title = _title_from_text(item.description, fallback=f"Action item {index}")
            owner = _clean_optional_text(item.owner)
            due_date = _clean_optional_text(item.due_date)
            evidence = _clean_optional_text(item.evidence)
            key = (title.casefold(), owner, due_date)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                _serialize_action_item(
                    index=len(normalized) + 1,
                    title=title,
                    owner=owner,
                    due_date=due_date,
                    raw_status=item.status,
                    evidence=evidence,
                    raw_sources=raw_sources,
                )
            )
    if normalized:
        return normalized
    heuristic_items = _heuristic_action_items_from_preview(preview_text=preview_text, raw_sources=raw_sources)
    if heuristic_items:
        return heuristic_items
    return _fallback_action_items(payload=payload, raw_sources=raw_sources)


def _build_critical_path(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        item
        for item in items
        if str(item.get("status") or "") != "done"
        and (
            str(item.get("priority") or "") in {"critical", "high"}
            or str(item.get("status") or "") == "blocked"
        )
    ]
    ranked = sorted(
        candidates,
        key=lambda item: (
            0 if str(item.get("status") or "") == "blocked" else 1,
            _PRIORITY_RANK.get(str(item.get("priority") or "medium"), 2),
            _due_sort_key(item.get("due_date")),
            str(item.get("title") or ""),
        ),
    )
    return ranked[:5]


def _item_gap_status(item: dict[str, Any]) -> tuple[str, list[str]]:
    missing_fields: list[str] = []
    if not _clean_optional_text(item.get("evidence")) and not _clean_optional_text(item.get("rationale")):
        missing_fields.append("supporting evidence")
    if not _clean_optional_text(item.get("owner")):
        missing_fields.append("owner")
    if not _clean_optional_text(item.get("due_date")):
        missing_fields.append("due date")
    if not _clean_optional_text(item.get("source")) and not _clean_optional_text(item.get("document_id")):
        return "missing", missing_fields or ["source trace"]
    if missing_fields:
        return "partial", missing_fields
    return "sufficient", []


def _build_evidence_gaps(
    *,
    items: list[dict[str, Any]],
    payload: DocumentAgentPayload,
    extraction_payload: ExtractionPayload | None,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        status, missing_fields = _item_gap_status(item)
        base_detail = _first_non_empty(item.get("evidence"), item.get("rationale"), item.get("notes"), item.get("source"))
        if status == "sufficient":
            detail = base_detail or "Grounded action includes supporting source coverage."
        else:
            missing_text = ", ".join(missing_fields)
            if base_detail:
                detail = f"{base_detail} Missing explicit {missing_text}."
            else:
                detail = f"Missing explicit {missing_text} for this action item."
        gaps.append(
            {
                "id": f"evidence-gap-item-{index}",
                "item_id": item.get("id"),
                "title": str(item.get("title") or f"Action item {index}"),
                "detail": detail,
                "status": status,
                "source": _clean_optional_text(item.get("source")),
                "notes": _clean_optional_text(item.get("notes")),
            }
        )

    explicit_gap_texts = _dedupe_texts(
        [
            *(extraction_payload.missing_information if extraction_payload is not None else []),
            *(payload.limitations or []),
            payload.needs_review_reason,
        ],
        limit=8,
    )
    for index, detail in enumerate(explicit_gap_texts, start=1):
        gaps.append(
            {
                "id": f"evidence-gap-explicit-{index}",
                "item_id": None,
                "title": _title_from_text(detail, fallback=f"Evidence gap {index}"),
                "detail": detail,
                "status": "missing",
                "source": None,
                "notes": "Workflow limitation",
            }
        )
    return gaps


def _run_state(
    *,
    result: ProductWorkflowResult,
    document_ids: list[str],
    items: list[dict[str, Any]],
    artifacts_count: int,
) -> dict[str, Any]:
    has_result = bool(result.structured_result and result.structured_result.success)
    steps: list[dict[str, str]] = [
        {"key": "select", "label": "Select", "status": "completed" if document_ids else "pending"},
        {"key": "ground", "label": "Ground", "status": "completed" if (result.grounding_preview is not None or document_ids) else "pending"},
        {"key": "analyze", "label": "Analyze", "status": "error" if result.status == "error" else ("completed" if has_result else "pending")},
        {"key": "review", "label": "Review", "status": "completed" if has_result else "pending"},
        {"key": "export", "label": "Export", "status": "completed" if artifacts_count > 0 else "pending"},
    ]
    current_step = "select"
    for step in reversed(steps):
        if step["status"] in {"completed", "error", "running"}:
            current_step = step["key"]
            break
    return {"current_step": current_step, "steps": steps}


def _summary_counts(items: list[dict[str, Any]], evidence_gaps: list[dict[str, Any]], document_ids: list[str], artifacts_count: int, critical_path_count: int) -> dict[str, int]:
    counts = {"open": 0, "in_progress": 0, "blocked": 0, "done": 0}
    for item in items:
        status = str(item.get("status") or "open")
        if status not in counts:
            status = "open"
        counts[status] += 1
    return {
        "total": len(items),
        "open": counts["open"],
        "in_progress": counts["in_progress"],
        "blocked": counts["blocked"],
        "done": counts["done"],
        "completed": counts["done"],
        "critical_path": critical_path_count,
        "evidence_gaps": sum(1 for item in evidence_gaps if str(item.get("status") or "") != "sufficient"),
        "documents": len(document_ids),
        "artifacts": artifacts_count,
    }


def _default_view(result: ProductWorkflowResult) -> dict[str, Any]:
    document_ids = _document_ids_from_result(result)
    run_state = _run_state(result=result, document_ids=document_ids, items=[], artifacts_count=len(result.artifacts))
    return {
        "objective": _derive_objective(result=result, payload=None, extraction_payload=None, document_ids=document_ids),
        "summary": _summary_counts([], [], document_ids, len(result.artifacts), 0),
        "items": [],
        "critical_path": [],
        "evidence_gaps": [],
        "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
        "document_ids": document_ids,
        "run_metadata": {
            "workflow_id": result.workflow_id,
            "workflow_label": result.workflow_label,
            "status": result.status,
            "provider": str(result.debug_metadata.get("provider") or "") if isinstance(result.debug_metadata, dict) else None,
            "model": str(result.debug_metadata.get("model") or "") if isinstance(result.debug_metadata, dict) else None,
            "context_strategy": result.grounding_preview.strategy if result.grounding_preview is not None else (str(result.debug_metadata.get("context_strategy") or "") if isinstance(result.debug_metadata, dict) else None),
            "deck_available": bool(result.deck_available),
            "deck_export_kind": result.deck_export_kind,
            "warning_count": len(result.warnings),
            "warnings": list(result.warnings),
            "source_block_count": result.grounding_preview.source_block_count if result.grounding_preview is not None else 0,
            "highlights": list(result.highlights),
            "summary": result.summary,
            "recommendation": result.recommendation,
            "run_state": run_state,
        },
    }


def build_action_plan_view(result: ProductWorkflowResult) -> dict[str, Any]:
    structured_result = result.structured_result
    payload = structured_result.validated_output if structured_result is not None else None
    if not isinstance(payload, DocumentAgentPayload):
        return _default_view(result)

    raw_sources = _collect_document_agent_sources(payload)
    structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
    extraction_payload = _coerce_extraction_payload(structured_response.get("extraction_payload"))
    items = _normalize_action_items(
        payload=payload,
        extraction_payload=extraction_payload,
        raw_sources=raw_sources,
        preview_text=(result.grounding_preview.preview_text if result.grounding_preview is not None else None),
    )
    critical_path = _build_critical_path(items)
    document_ids = _document_ids_from_result(result)
    evidence_gaps = _build_evidence_gaps(items=items, payload=payload, extraction_payload=extraction_payload)
    run_state = _run_state(result=result, document_ids=document_ids, items=items, artifacts_count=len(result.artifacts))

    return {
        "objective": _derive_objective(result=result, payload=payload, extraction_payload=extraction_payload, document_ids=document_ids),
        "summary": _summary_counts(items, evidence_gaps, document_ids, len(result.artifacts), len(critical_path)),
        "items": items,
        "critical_path": critical_path,
        "evidence_gaps": evidence_gaps,
        "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
        "document_ids": document_ids,
        "run_metadata": {
            "workflow_id": result.workflow_id,
            "workflow_label": result.workflow_label,
            "status": result.status,
            "provider": str(result.debug_metadata.get("provider") or "") if isinstance(result.debug_metadata, dict) else None,
            "model": str(result.debug_metadata.get("model") or "") if isinstance(result.debug_metadata, dict) else None,
            "context_strategy": result.grounding_preview.strategy if result.grounding_preview is not None else (str(result.debug_metadata.get("context_strategy") or "") if isinstance(result.debug_metadata, dict) else None),
            "deck_available": bool(result.deck_available),
            "deck_export_kind": result.deck_export_kind,
            "warning_count": len(result.warnings),
            "warnings": _dedupe_texts([*result.warnings, *(payload.limitations or []), payload.needs_review_reason], limit=8),
            "source_block_count": result.grounding_preview.source_block_count if result.grounding_preview is not None else len(raw_sources),
            "highlights": _dedupe_texts([*result.highlights, *(payload.key_points or []), *(payload.recommended_actions or [])], limit=6),
            "summary": result.summary,
            "recommendation": result.recommendation,
            "run_state": run_state,
        },
    }
