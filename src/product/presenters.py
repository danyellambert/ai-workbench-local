from __future__ import annotations

import re
from typing import Any

from src.structured.base import (
    CVAnalysisPayload,
    ChecklistPayload,
    DocumentAgentPayload,
    ExtractionPayload,
    SummaryPayload,
)

from .models import ProductWorkflowResult


def _clean_optional_text(value: object) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _title_from_finding_text(value: object, *, fallback: str = "Grounded finding") -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return fallback
    sentence = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0].strip()
    if len(sentence) <= 88:
        return sentence
    shortened = sentence[:85].rsplit(" ", 1)[0].strip()
    return f"{shortened}..." if shortened else fallback


def _infer_finding_category(*values: object) -> str:
    haystack = " ".join(_clean_text(value).lower() for value in values if _clean_text(value))
    if any(token in haystack for token in ("liability", "indemn", "jurisdiction", "clause", "contract", "legal")):
        return "Legal Risk"
    if any(token in haystack for token in ("gdpr", "privacy", "pii", "residency", "regulatory", "compliance")):
        return "Compliance"
    if any(token in haystack for token in ("security", "breach", "incident", "access control", "encryption")):
        return "Security"
    if any(token in haystack for token in ("sla", "uptime", "downtime", "operational", "availability", "latency")):
        return "Operational Risk"
    if any(token in haystack for token in ("renewal", "commercial", "payment", "pricing", "term")):
        return "Commercial"
    return "Grounded Finding"


def _infer_finding_severity(*values: object) -> str:
    haystack = " ".join(_clean_text(value).lower() for value in values if _clean_text(value))
    critical_tokens = (
        "unlimited liability",
        "uncapped",
        "material breach",
        "critical",
        "block approval",
        "regulatory violation",
        "non-compliance",
    )
    high_tokens = (
        "missing",
        "requires review",
        "breach",
        "violate",
        "violation",
        "weak",
        "high risk",
        "security",
        "gdpr",
        "compliance",
        "unclear",
        "risk",
    )
    low_tokens = ("minor", "optional", "nice to have")
    if any(token in haystack for token in critical_tokens):
        return "critical"
    if any(token in haystack for token in high_tokens):
        return "high"
    if any(token in haystack for token in low_tokens):
        return "low"
    return "medium"


def _normalize_confidence(value: object, *, severity: str) -> float:
    base = float(value) if isinstance(value, (int, float)) else 0.74
    if severity == "critical":
        base += 0.1
    elif severity == "high":
        base += 0.05
    return round(max(0.5, min(base, 0.98)), 3)


def _token_overlap_score(source: dict[str, object], probe: str) -> int:
    normalized_probe = _clean_text(probe).lower()
    if not normalized_probe:
        return 0
    tokens = {token for token in re.findall(r"[a-z0-9]{4,}", normalized_probe) if len(token) >= 4}
    if not tokens:
        return 0
    source_haystack = " ".join(
        _clean_text(value).lower()
        for value in (source.get("source"), source.get("snippet"), source.get("document_id"))
        if _clean_text(value)
    )
    return sum(1 for token in tokens if token in source_haystack)


def _best_source_match(raw_sources: list[dict[str, object]], *values: object) -> dict[str, object]:
    probe = " ".join(_clean_text(value) for value in values if _clean_text(value)).strip()
    if not raw_sources:
        return {}
    ranked = sorted(raw_sources, key=lambda source: _token_overlap_score(source, probe), reverse=True)
    return ranked[0] if ranked else {}


def _collect_document_agent_sources(payload: DocumentAgentPayload) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for source in payload.sources:
        if hasattr(source, "model_dump"):
            data = source.model_dump(mode="json")
        elif isinstance(source, dict):
            data = dict(source)
        else:
            continue
        normalized.append(
            {
                "source": _clean_optional_text(data.get("source")) or _clean_optional_text(data.get("document_id")) or "document",
                "document_id": _clean_optional_text(data.get("document_id")),
                "chunk_id": data.get("chunk_id"),
                "score": data.get("score") or data.get("vector_score"),
                "snippet": _clean_optional_text(data.get("snippet")) or "-",
            }
        )
    return normalized


def _serialize_native_document_review_findings(payload: DocumentAgentPayload) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, item in enumerate(payload.document_review_findings, start=1):
        title = _clean_optional_text(item.title) or _title_from_finding_text(item.description or item.evidence, fallback=f"Grounded finding {index}")
        description = _clean_optional_text(item.description) or _clean_optional_text(item.impact) or title
        evidence = _clean_optional_text(item.evidence) or description
        key = (
            str(item.severity or "medium"),
            title.casefold(),
            evidence.casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "id": f"finding-{index}",
                "severity": str(item.severity or "medium"),
                "category": _clean_optional_text(item.category) or "Grounded Finding",
                "title": title,
                "description": description,
                "source": _clean_optional_text(item.source_label) or "Grounded corpus",
                "chunkId": f"chunk_{item.chunk_id}" if isinstance(item.chunk_id, int) else "chunk_n/a",
                "confidence": max(0.0, min(float(item.confidence or 0.0), 0.98)),
                "recommendation": _clean_optional_text(item.recommendation) or _clean_optional_text(item.impact) or "Review this finding before approval.",
                "snippet": evidence,
                "source_document_id": _clean_optional_text(item.source_document_id),
            }
        )
    return normalized


def _serialize_native_top_blockers(payload: DocumentAgentPayload, findings: list[dict[str, object]]) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in payload.document_review_top_blockers:
        cleaned = _clean_optional_text(item)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        matched_finding = next(
            (
                finding
                for finding in findings
                if cleaned.casefold() in str(finding.get("title") or "").casefold()
                or str(finding.get("title") or "").casefold() in cleaned.casefold()
            ),
            None,
        )
        blockers.append(
            {
                "title": matched_finding.get("title") if matched_finding else cleaned,
                "severity": matched_finding.get("severity") if matched_finding else None,
                "recommendation": matched_finding.get("recommendation") if matched_finding else None,
            }
        )
        if len(blockers) >= 4:
            break
    return blockers


def _serialize_native_business_impact(payload: DocumentAgentPayload) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(payload.document_review_business_impact, start=1):
        cleaned = _clean_optional_text(item)
        if not cleaned:
            continue
        normalized.append({"label": f"Impact {index}", "detail": cleaned})
        if len(normalized) >= 4:
            break
    return normalized


def build_document_review_view(result: ProductWorkflowResult) -> dict[str, Any]:
    sections = build_product_result_sections(result)
    structured_result = result.structured_result
    payload = structured_result.validated_output if structured_result is not None else None

    raw_sources: list[dict[str, object]] = []
    extraction_payload: dict[str, object] = {}
    recommended_actions: list[str] = []
    overall_confidence: float | None = None
    needs_review_reason: str | None = None
    limitations: list[str] = []
    native_findings: list[dict[str, object]] = []
    native_top_blockers: list[dict[str, object]] = []
    native_business_impact: list[dict[str, str]] = []
    native_decision_summary = None

    if isinstance(payload, DocumentAgentPayload):
        raw_sources = _collect_document_agent_sources(payload)
        structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
        extraction_payload = structured_response.get("extraction_payload") if isinstance(structured_response.get("extraction_payload"), dict) else {}
        recommended_actions = [_clean_text(item) for item in (payload.recommended_actions or []) if _clean_text(item)]
        overall_confidence = float(payload.confidence or 0.0) if isinstance(payload.confidence, (int, float)) else None
        needs_review_reason = _clean_optional_text(payload.needs_review_reason)
        limitations = [_clean_text(item) for item in (payload.limitations or []) if _clean_text(item)]
        native_findings = _serialize_native_document_review_findings(payload)
        native_top_blockers = _serialize_native_top_blockers(payload, native_findings)
        native_business_impact = _serialize_native_business_impact(payload)
        native_decision_summary = payload.document_review_decision_summary

    risk_items = [item for item in extraction_payload.get("risks", []) if isinstance(item, dict)]
    action_items = [item for item in extraction_payload.get("action_items", []) if isinstance(item, dict)]

    findings: list[dict[str, object]] = list(native_findings)
    confidence_seed = overall_confidence
    if confidence_seed is None and structured_result is not None and isinstance(structured_result.overall_confidence, (int, float)):
        confidence_seed = float(structured_result.overall_confidence)
    if confidence_seed is None and structured_result is not None and isinstance(structured_result.quality_score, (int, float)):
        confidence_seed = float(structured_result.quality_score)

    if not findings:
        for index, risk in enumerate(risk_items, start=1):
            description = _clean_optional_text(risk.get("description")) or f"Grounded risk {index}"
            impact = _clean_optional_text(risk.get("impact"))
            evidence = _clean_optional_text(risk.get("evidence"))
            paired_action = action_items[index - 1] if index - 1 < len(action_items) else {}
            recommendation = _clean_optional_text(paired_action.get("description")) or _clean_optional_text(result.recommendation) or "Review this finding before approval."
            severity = _infer_finding_severity(description, impact, evidence, recommendation)
            category = _infer_finding_category(description, impact, evidence)
            best_source = _best_source_match(raw_sources, evidence, description, impact)
            findings.append(
                {
                    "id": f"finding-{index}",
                    "severity": severity,
                    "category": category,
                    "title": _title_from_finding_text(description),
                    "description": impact or description,
                    "source": best_source.get("source") or "Grounded corpus",
                    "chunkId": f"chunk_{best_source.get('chunk_id')}" if isinstance(best_source.get("chunk_id"), int) else "chunk_n/a",
                    "confidence": _normalize_confidence(confidence_seed, severity=severity),
                    "recommendation": recommendation,
                    "snippet": _clean_optional_text(best_source.get("snippet")) or evidence or impact or description,
                }
            )

    if not findings:
        fallback_highlights = [item for item in (result.highlights or []) if _clean_text(item)]
        for index, highlight in enumerate(fallback_highlights[:6], start=1):
            best_source = raw_sources[min(index - 1, len(raw_sources) - 1)] if raw_sources else {}
            severity = _infer_finding_severity(highlight, result.recommendation, result.summary)
            findings.append(
                {
                    "id": f"finding-{index}",
                    "severity": severity,
                    "category": _infer_finding_category(highlight, result.summary),
                    "title": _title_from_finding_text(highlight),
                    "description": _clean_optional_text(result.summary) or highlight,
                    "source": best_source.get("source") or "Grounded corpus",
                    "chunkId": f"chunk_{best_source.get('chunk_id')}" if isinstance(best_source.get("chunk_id"), int) else "chunk_n/a",
                    "confidence": _normalize_confidence(confidence_seed, severity=severity),
                    "recommendation": _clean_optional_text(result.recommendation) or "Run a grounded review before approval.",
                    "snippet": _clean_optional_text(best_source.get("snippet")) or _clean_optional_text(result.summary) or highlight,
                }
            )

    severity_counts = {level: 0 for level in ("critical", "high", "medium", "low")}
    for finding in findings:
        severity = str(finding.get("severity") or "medium")
        if severity not in severity_counts:
            severity = "medium"
        severity_counts[severity] += 1

    top_blockers = list(native_top_blockers)

    if not top_blockers:
        top_blockers = [
            {
                "title": finding.get("title"),
                "severity": finding.get("severity"),
                "recommendation": finding.get("recommendation"),
            }
            for finding in findings
            if str(finding.get("severity")) in {"critical", "high"}
        ][:4]

    if not top_blockers:
        top_blockers = [
            {
                "title": finding.get("title"),
                "severity": finding.get("severity"),
                "recommendation": finding.get("recommendation"),
            }
            for finding in findings[:3]
        ]

    business_impact: list[dict[str, str]] = list(native_business_impact)
    if not business_impact:
        used_categories: set[str] = set()
        for finding in findings:
            category = str(finding.get("category") or "Business impact")
            if category in used_categories:
                continue
            used_categories.add(category)
            business_impact.append(
                {
                    "label": category,
                    "detail": _clean_optional_text(finding.get("description")) or _clean_optional_text(finding.get("recommendation")) or _clean_optional_text(result.summary) or "Grounded impact available in the workflow output.",
                }
            )
            if len(business_impact) >= 3:
                break

    if not business_impact and _clean_optional_text(result.summary):
        business_impact.append({"label": "Review summary", "detail": _clean_text(result.summary)})

    evidence_trail = [
        {
            "id": finding.get("id"),
            "severity": finding.get("severity"),
            "title": finding.get("title"),
            "chunkId": finding.get("chunkId"),
            "source": finding.get("source"),
            "snippet": finding.get("snippet"),
        }
        for finding in findings[:6]
    ]

    next_owner = None
    due_date = None
    for item in [*action_items, *risk_items]:
        if next_owner is None:
            next_owner = _clean_optional_text(item.get("owner"))
        if due_date is None:
            due_date = _clean_optional_text(item.get("due_date"))
        if next_owner and due_date:
            break

    if severity_counts["critical"] > 0 or severity_counts["high"] >= 2:
        decision_label = "Renegotiate"
        status_label = "Requires Legal Review"
    elif severity_counts["high"] > 0 or limitations or needs_review_reason:
        decision_label = "Approve with changes"
        status_label = "Requires Review"
    elif findings:
        decision_label = "Proceed with caution"
        status_label = "Grounded Review Ready"
    else:
        decision_label = "Review completed"
        status_label = "No material blockers"

    if native_decision_summary is not None:
        decision_label = _clean_optional_text(native_decision_summary.label) or decision_label
        status_label = _clean_optional_text(native_decision_summary.status) or status_label

    run_steps = [
        {"key": "select", "label": "Select", "status": "completed"},
        {"key": "ground", "label": "Ground", "status": "completed" if result.grounding_preview is not None else "pending"},
        {"key": "analyze", "label": "Analyze", "status": "completed" if result.status in {"completed", "warning"} else ("error" if result.status == "error" else "pending")},
        {"key": "review", "label": "Review", "status": "completed" if findings or _clean_optional_text(result.summary) else "pending"},
        {"key": "export", "label": "Export", "status": "completed" if result.artifacts else ("running" if result.deck_available else "pending")},
    ]

    current_step = "export" if result.artifacts else "review" if findings else "analyze" if result.status in {"completed", "warning", "error"} else "ground" if result.grounding_preview else "select"

    return {
        "decision_summary": {
            "label": decision_label,
            "status": status_label,
            "summary": _clean_optional_text(getattr(native_decision_summary, "rationale", None)) or _clean_optional_text(result.summary) or "Run a grounded review to generate a decision summary.",
            "severity_counts": severity_counts,
            "next_owner": next_owner,
            "due_date": due_date,
        },
        "document_metrics": {
            "strategy": result.grounding_preview.strategy if result.grounding_preview is not None else result.debug_metadata.get("context_strategy") if isinstance(result.debug_metadata, dict) else None,
            "document_ids": list(result.grounding_preview.document_ids) if result.grounding_preview is not None else list(result.debug_metadata.get("source_documents") or []) if isinstance(result.debug_metadata, dict) else [],
            "context_chars": int(result.grounding_preview.context_chars or 0) if result.grounding_preview is not None else 0,
            "source_block_count": int(result.grounding_preview.source_block_count or 0) if result.grounding_preview is not None else 0,
        },
        "watchouts": list(sections.get("watchouts") or []),
        "next_steps": list(sections.get("next_steps") or []),
        "top_blockers": top_blockers,
        "business_impact": business_impact,
        "findings": findings,
        "evidence_trail": evidence_trail,
        "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
        "sources": list(sections.get("sources") or []),
        "run_state": {
            "current_step": current_step,
            "steps": run_steps,
        },
    }


def _humanize_comparison_finding_type(value: object) -> str:
    normalized = _clean_text(value).replace("_", " ").strip()
    if not normalized:
        return "Comparison finding"
    mapping = {
        "document summary": "Document summary",
        "cross document observation": "Cross-document observation",
        "obligation change": "Obligation change",
        "risk change": "Risk change",
        "policy delta": "Policy delta",
        "contract delta": "Contract delta",
    }
    return mapping.get(normalized.casefold(), normalized.title())


def _infer_comparison_impact(*values: object) -> str:
    haystack = " ".join(_clean_text(value).lower() for value in values if _clean_text(value))
    breaking_tokens = (
        "mandatory",
        "mandatory approval",
        "approval became mandatory",
        "must be approved",
        "must approve",
        "non-negotiable",
        "uncapped",
        "unlimited liability",
        "waiver of jury trial",
        "termination",
        "material breach",
        "prohibited",
        "cannot",
    )
    significant_tokens = (
        "required",
        "approval",
        "liability",
        "indemn",
        "security",
        "privacy",
        "gdpr",
        "compliance",
        "data residency",
        "governing law",
        "jurisdiction",
        "confidentiality",
        "repurchase",
        "custodial",
        "escrow",
        "operational",
        "risk",
    )
    minor_tokens = ("format", "wording", "editorial", "stylistic", "minor")
    if any(token in haystack for token in breaking_tokens):
        return "breaking"
    if any(token in haystack for token in significant_tokens):
        return "significant"
    if any(token in haystack for token in minor_tokens):
        return "minor"
    return "significant"


def _truncate_ui_text(value: object, *, max_chars: int = 280) -> str:
    cleaned = _clean_text(value)
    if len(cleaned) <= max_chars:
        return cleaned
    shortened = cleaned[: max_chars - 3].rsplit(" ", 1)[0].strip()
    return f"{shortened or cleaned[: max_chars - 3].strip()}..."


def _comparison_document_summary_lookup(payload: DocumentAgentPayload) -> dict[str, dict[str, Any]]:
    structured_response = payload.structured_response if isinstance(payload.structured_response, dict) else {}
    raw_summaries = structured_response.get("document_summaries") if isinstance(structured_response.get("document_summaries"), list) else []
    lookup: dict[str, dict[str, Any]] = {}
    for item in raw_summaries:
        if not isinstance(item, dict):
            continue
        label = _clean_optional_text(item.get("label")) or _clean_optional_text(item.get("document_id")) or f"Document {len(lookup) + 1}"
        summary = _clean_optional_text(item.get("summary")) or "Summary unavailable."
        key_points = _dedupe_texts(item.get("key_points") if isinstance(item.get("key_points"), list) else [], limit=4)
        lookup[label] = {
            "label": label,
            "summary": summary,
            "key_points": key_points,
        }
    return lookup


def _comparison_document_text(label: str, lookup: dict[str, dict[str, Any]], *, fallback: str | None = None) -> str:
    item = lookup.get(label) or {}
    parts: list[str] = []
    if item.get("summary"):
        parts.append(str(item["summary"]))
    for key_point in item.get("key_points") or []:
        parts.append(str(key_point))
        if len(parts) >= 3:
            break
    if fallback:
        parts.append(fallback)
    return _truncate_ui_text(" ".join(part for part in parts if part) or "No grounded comparison excerpt available.")


def build_policy_comparison_view(result: ProductWorkflowResult) -> dict[str, Any]:
    sections = build_product_result_sections(result)
    structured_result = result.structured_result
    payload = structured_result.validated_output if structured_result is not None else None

    compared_documents: list[str] = []
    comparison_findings: list[Any] = []
    document_lookup: dict[str, dict[str, Any]] = {}
    recommended_actions: list[str] = []
    limitations: list[str] = []

    if isinstance(payload, DocumentAgentPayload):
        compared_documents = _dedupe_texts(list(payload.compared_documents or []), limit=3)
        comparison_findings = list(payload.comparison_findings or [])
        document_lookup = _comparison_document_summary_lookup(payload)
        recommended_actions = _dedupe_texts(list(payload.recommended_actions or []), limit=6)
        limitations = _dedupe_texts(list(payload.limitations or []), limit=6)

    if not compared_documents:
        compared_documents = list(document_lookup.keys())
    if not compared_documents and isinstance(result.debug_metadata, dict):
        compared_documents = _dedupe_texts(list(result.debug_metadata.get("source_documents") or []), limit=3)

    primary_document = compared_documents[0] if compared_documents else "Document A"
    secondary_document = compared_documents[1] if len(compared_documents) > 1 else next(
        (label for label in document_lookup.keys() if label != primary_document),
        "Document B",
    )

    raw_differences = [
        item
        for item in comparison_findings
        if _clean_text(getattr(item, "finding_type", None)).replace("_", " ").casefold() != "document summary"
    ]

    differences: list[dict[str, Any]] = []
    for index, item in enumerate(raw_differences[:8], start=1):
        title = _clean_optional_text(getattr(item, "title", None)) or _title_from_finding_text(getattr(item, "description", None), fallback=f"Difference {index}")
        description = _clean_optional_text(getattr(item, "description", None)) or title
        evidence = _dedupe_texts(list(getattr(item, "evidence", []) or []), limit=3)
        documents = _dedupe_texts(list(getattr(item, "documents", []) or []), limit=3)
        left_label = documents[0] if documents else primary_document
        right_label = documents[1] if len(documents) > 1 else secondary_document
        impact = _infer_comparison_impact(title, description, *evidence, result.recommendation)
        category = _humanize_comparison_finding_type(getattr(item, "finding_type", None))
        differences.append(
            {
                "id": f"comparison-diff-{index}",
                "clause": title,
                "impact": impact,
                "category": category,
                "doc_a_label": left_label,
                "doc_a_text": _comparison_document_text(left_label, document_lookup, fallback=(evidence[0] if evidence else None)),
                "doc_b_label": right_label,
                "doc_b_text": _comparison_document_text(
                    right_label,
                    document_lookup,
                    fallback=(evidence[1] if len(evidence) > 1 else (evidence[0] if evidence else None)),
                ),
                "business_impact": _truncate_ui_text(description),
                "recommendation": _clean_optional_text(result.recommendation) or (recommended_actions[0] if recommended_actions else None),
                "evidence": evidence,
            }
        )

    if not differences:
        fallback_points = _dedupe_texts([*(result.highlights or []), result.summary], limit=4)
        for index, point in enumerate(fallback_points, start=1):
            differences.append(
                {
                    "id": f"comparison-diff-{index}",
                    "clause": _title_from_finding_text(point, fallback=f"Difference {index}"),
                    "impact": _infer_comparison_impact(point, result.recommendation),
                    "category": "Comparison summary",
                    "doc_a_label": primary_document,
                    "doc_a_text": _comparison_document_text(primary_document, document_lookup),
                    "doc_b_label": secondary_document,
                    "doc_b_text": _comparison_document_text(secondary_document, document_lookup),
                    "business_impact": _truncate_ui_text(point),
                    "recommendation": _clean_optional_text(result.recommendation) or (recommended_actions[0] if recommended_actions else None),
                    "evidence": [],
                }
            )

    impact_counts = {"breaking": 0, "significant": 0, "minor": 0}
    for diff in differences:
        impact = str(diff.get("impact") or "significant")
        if impact not in impact_counts:
            impact = "significant"
        impact_counts[impact] += 1

    must_fix_candidates = [diff for diff in differences if str(diff.get("impact")) == "breaking"]
    if not must_fix_candidates:
        must_fix_candidates = [diff for diff in differences if str(diff.get("impact")) == "significant"]
    must_fix_items = [
        {
            "title": diff.get("clause"),
            "detail": diff.get("business_impact"),
            "impact": diff.get("impact"),
            "recommendation": diff.get("recommendation"),
        }
        for diff in must_fix_candidates[:4]
    ]

    negotiation_priorities = _dedupe_texts(
        [
            *recommended_actions,
            *(sections.get("next_steps") or []),
            *(sections.get("watchouts") or []),
            *(diff.get("recommendation") for diff in differences if diff.get("recommendation")),
        ],
        limit=5,
    )
    if not negotiation_priorities and result.recommendation:
        negotiation_priorities = [_clean_text(result.recommendation)]

    watchouts = _dedupe_texts([*(sections.get("watchouts") or []), *limitations, *(result.warnings or [])], limit=6)
    next_steps = _dedupe_texts([*(sections.get("next_steps") or []), *recommended_actions], limit=6)

    run_steps = [
        {"key": "select", "label": "Select", "status": "completed"},
        {"key": "ground", "label": "Ground", "status": "completed" if result.grounding_preview is not None or compared_documents else "pending"},
        {"key": "analyze", "label": "Analyze", "status": "completed" if result.status in {"completed", "warning"} else ("error" if result.status == "error" else "pending")},
        {"key": "review", "label": "Review", "status": "completed" if differences or _clean_optional_text(result.summary) else "pending"},
        {"key": "export", "label": "Export", "status": "completed" if result.artifacts else ("running" if result.deck_available else "pending")},
    ]
    current_step = "export" if result.artifacts else "review" if differences else "analyze" if result.status in {"completed", "warning", "error"} else "select"

    artifact_label = next(
        (
            artifact.download_name or artifact.label
            for artifact in result.artifacts
            if getattr(artifact, "available", False)
        ),
        None,
    )
    if artifact_label is None and result.deck_available:
        artifact_label = f"{result.workflow_label} deck available for generation"

    return {
        "compared_documents": [item for item in [primary_document, secondary_document] if item],
        "executive_summary": {
            "narrative": _clean_optional_text(result.summary) or "Run the comparison to generate a grounded executive summary.",
            "counts": impact_counts,
            "status": "Requires Review" if watchouts or result.status in {"warning", "error"} else "Comparison Ready",
            "documents": [item for item in [primary_document, secondary_document] if item],
        },
        "must_fix_items": must_fix_items,
        "negotiation_priorities": negotiation_priorities,
        "differences": differences,
        "recommendation": {
            "summary": _clean_optional_text(result.recommendation) or (negotiation_priorities[0] if negotiation_priorities else "Validate the critical differences with a final human review before making the decision."),
            "handoff": "Legal / policy review" if must_fix_items else "Human document review",
            "artifact_label": artifact_label,
        },
        "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
        "watchouts": watchouts,
        "next_steps": next_steps,
        "run_state": {
            "current_step": current_step,
            "steps": run_steps,
        },
    }


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