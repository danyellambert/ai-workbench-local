"""Renderers for Phase 5 structured outputs."""
from __future__ import annotations

import json
from typing import Any

import streamlit as st

from ..structured.base import (
    ChecklistPayload,
    CVAnalysisPayload,
    CodeAnalysisPayload,
    ExtractionPayload,
    SummaryPayload,
)
from ..structured.envelope import StructuredResult


def _payload_to_json(payload: Any) -> dict[str, Any] | list[Any] | None:
    if payload is None:
        return None
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload


def _render_result_header(result: StructuredResult) -> None:
    status_label = "Validated" if result.success else "Failed"
    status_kind = "success" if result.success else "error"
    context_label = "with document context" if result.context_used else "without document context"
    repair_label = "repair applied" if result.repair_applied else "no repair"
    st.caption(
        f"Task: `{result.task_type}` · Execution: `{result.execution_id[:8]}` · {status_label} · {context_label} · {repair_label}"
    )
    if status_kind == "success":
        st.success("Structured output generated and validated.")
        if result.quality_score is not None and result.quality_score < 0.65:
            st.warning(
                f"This payload validated structurally, but its estimated quality is low ({result.quality_score:.0%}). Review grounding and placeholders before trusting it."
            )
    else:
        error_message = result.validation_error or result.parsing_error or (result.error.message if result.error else "Unknown error")
        st.error(error_message)


def _render_extraction(payload: ExtractionPayload) -> None:
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Entities", len(payload.entities))
    metric_2.metric("Fields", len(payload.extracted_fields))
    metric_3.metric("Risks", len(payload.risks))
    metric_4.metric("Actions", len(payload.action_items))

    if payload.main_subject:
        st.write("**Main subject**")
        st.info(payload.main_subject)

    if payload.categories:
        st.write("**Categories**")
        st.write(", ".join(payload.categories))

    if payload.important_dates or payload.important_numbers:
        cols = st.columns(2)
        with cols[0]:
            if payload.important_dates:
                st.write("**Important dates**")
                for item in payload.important_dates:
                    st.write(f"- {item}")
        with cols[1]:
            if payload.important_numbers:
                st.write("**Important numbers**")
                for item in payload.important_numbers:
                    st.write(f"- {item}")

    if payload.entities:
        entities_table = [
            {
                "type": entity.type,
                "value": entity.value,
                "confidence": entity.confidence,
                "source_text": entity.source_text,
                "position": f"{entity.position_start}-{entity.position_end}",
            }
            for entity in payload.entities
        ]
        st.write("**Entities**")
        st.dataframe(entities_table, width="stretch")

    if payload.extracted_fields:
        st.write("**Extracted fields**")
        st.dataframe(
            [
                {"name": field.name, "value": field.value, "evidence": field.evidence}
                for field in payload.extracted_fields
            ],
            width="stretch",
        )

    if payload.relationships:
        st.write("**Relationships**")
        st.dataframe(
            [
                {
                    "from": relationship.from_entity,
                    "to": relationship.to_entity,
                    "relationship": relationship.relationship,
                    "confidence": relationship.confidence,
                    "evidence": relationship.evidence,
                }
                for relationship in payload.relationships
            ],
            width="stretch",
        )

    if payload.risks:
        st.write("**Risks**")
        for item in payload.risks:
            if getattr(item, "impact", None) or getattr(item, "owner", None) or getattr(item, "due_date", None):
                with st.expander(item.description, expanded=False):
                    if item.impact:
                        st.write(f"Impact: {item.impact}")
                    meta = []
                    if item.owner:
                        meta.append(f"owner={item.owner}")
                    if item.due_date:
                        meta.append(f"due={item.due_date}")
                    if meta:
                        st.caption(" · ".join(meta))
            else:
                st.write(f"- {item.description}")

    if payload.action_items:
        st.write("**Action items**")
        for item in payload.action_items:
            line = item.description
            meta = []
            if item.owner:
                meta.append(f"owner={item.owner}")
            if item.due_date:
                meta.append(f"due={item.due_date}")
            if item.status:
                meta.append(f"status={item.status}")
            if meta:
                line += f" ({' · '.join(meta)})"
            st.write(f"- {line}")

    if payload.missing_information:
        st.write("**Missing information / ambiguities**")
        for item in payload.missing_information:
            st.write(f"- {item}")


def _render_summary(payload: SummaryPayload) -> None:
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Topics", len(payload.topics))
    metric_2.metric("Reading time", f"{payload.reading_time_minutes} min")
    metric_3.metric("Completeness", f"{payload.completeness_score:.0%}")

    st.write("**Executive summary**")
    st.info(payload.executive_summary)

    if payload.key_insights:
        st.write("**Key insights**")
        for insight in payload.key_insights:
            st.write(f"- {insight}")

    if payload.topics:
        st.write("**Topics**")
        for topic in payload.topics:
            with st.expander(f"{topic.title} · relevance {topic.relevance_score:.0%}", expanded=False):
                for point in topic.key_points:
                    st.write(f"- {point}")
                if topic.supporting_evidence:
                    st.caption("Supporting evidence")
                    for evidence in topic.supporting_evidence:
                        st.write(f"- {evidence}")


def _render_checklist_friendly(payload: ChecklistPayload) -> None:
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Items", payload.total_items)
    metric_2.metric("Completed", payload.completed_items)
    metric_3.metric("Progress", f"{payload.progress_percentage:.0f}%")
    st.progress(min(max(payload.progress_percentage / 100.0, 0.0), 1.0))
    st.write(f"**{payload.title}**")
    st.caption(payload.description)

    if payload.items:
        checklist_table = [
            {
                "title": item.title,
                "category": item.category,
                "priority": item.priority,
                "status": item.status,
                "eta_min": item.estimated_time_minutes,
                "dependencies": ", ".join(item.dependencies) if item.dependencies else "",
            }
            for item in payload.items
        ]
        st.dataframe(checklist_table, width="stretch")


def _render_checklist_view(payload: ChecklistPayload) -> None:
    st.write(f"**{payload.title}**")
    st.caption(payload.description)
    st.progress(min(max(payload.progress_percentage / 100.0, 0.0), 1.0))
    for index, item in enumerate(payload.items, start=1):
        done = item.status == "completed"
        icon = "✅" if done else "⬜"
        st.markdown(f"{icon} **{index}. {item.title}** — {item.description}")
        st.caption(
            f"category={item.category} · priority={item.priority} · status={item.status} · eta={item.estimated_time_minutes} min"
        )
        if item.dependencies:
            st.caption(f"depends on: {', '.join(item.dependencies)}")


def _render_cv_analysis(payload: CVAnalysisPayload) -> None:
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Sections", len(payload.sections))
    metric_2.metric("Skills", len(payload.skills))
    metric_3.metric("Experience", f"{payload.experience_years:.1f} years")

    if payload.personal_info:
        st.write("**Personal info**")
        st.json(payload.personal_info.model_dump(mode="json"))

    if payload.skills:
        st.write("**Skills**")
        st.write(", ".join(payload.skills))

    if payload.languages:
        st.write("**Languages**")
        st.write(", ".join(payload.languages))

    if payload.education_entries:
        st.write("**Education**")
        for entry in payload.education_entries:
            line = entry.description or " | ".join(
                part for part in [entry.degree, entry.institution, entry.location, entry.date_range] if part
            )
            if line:
                st.write(f"- {line}")

    if payload.experience_entries:
        st.write("**Experience entries**")
        for entry in payload.experience_entries:
            title_line = " | ".join(part for part in [entry.title, entry.organization, entry.location, entry.date_range] if part)
            if title_line:
                st.write(f"- {title_line}")
            if entry.bullets:
                for bullet in entry.bullets:
                    st.caption(f"• {bullet}")

    if payload.strengths:
        st.write("**Strengths**")
        for item in payload.strengths:
            st.write(f"- {item}")

    if payload.improvement_areas:
        st.write("**Improvement areas**")
        for item in payload.improvement_areas:
            st.write(f"- {item}")

    if payload.sections:
        st.write("**Sections**")
        for section in payload.sections:
            with st.expander(
                f"{section.title} · {section.section_type} · confidence {section.confidence:.0%}",
                expanded=False,
            ):
                for item in section.content:
                    if item.text:
                        st.write(f"- {item.text}")
                    if item.details:
                        st.json(item.details)


def _render_code_analysis(payload: CodeAnalysisPayload) -> None:
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Issues", len(payload.detected_issues))
    metric_2.metric("Refactor steps", len(payload.refactor_plan))
    metric_3.metric("Test suggestions", len(payload.test_suggestions))

    st.write("**Snippet summary**")
    st.info(payload.snippet_summary)
    st.write("**Main purpose**")
    st.write(payload.main_purpose)

    if payload.detected_issues:
        st.write("**Detected issues**")
        for issue in payload.detected_issues:
            with st.expander(f"{issue.severity.upper()} · {issue.category} · {issue.title}", expanded=False):
                st.write(issue.description)
                if issue.evidence:
                    st.caption(f"Evidence: {issue.evidence}")
                if issue.recommendation:
                    st.write(f"Recommendation: {issue.recommendation}")

    for heading, items in [
        ("Readability improvements", payload.readability_improvements),
        ("Maintainability improvements", payload.maintainability_improvements),
        ("Refactor plan", payload.refactor_plan),
        ("Test suggestions", payload.test_suggestions),
        ("Risk notes", payload.risk_notes),
    ]:
        if items:
            st.write(f"**{heading}**")
            for item in items:
                st.write(f"- {item}")


def _render_friendly_payload(payload: Any) -> None:
    if isinstance(payload, ExtractionPayload):
        _render_extraction(payload)
    elif isinstance(payload, SummaryPayload):
        _render_summary(payload)
    elif isinstance(payload, ChecklistPayload):
        _render_checklist_friendly(payload)
    elif isinstance(payload, CVAnalysisPayload):
        _render_cv_analysis(payload)
    elif isinstance(payload, CodeAnalysisPayload):
        _render_code_analysis(payload)
    else:
        st.json(_payload_to_json(payload))


def render_structured_result(result: StructuredResult, requested_mode: str | None = None) -> None:
    """Render a structured result using the requested mode when available."""
    _render_result_header(result)

    available_modes = sorted(
        [mode for mode in result.available_render_modes if mode.available],
        key=lambda mode: mode.priority,
    )
    available_mode_names = [mode.mode for mode in available_modes]
    mode = requested_mode or result.primary_render_mode or (available_mode_names[0] if available_mode_names else "json")
    if mode not in available_mode_names and available_mode_names:
        mode = available_mode_names[0]

    payload_json = _payload_to_json(result.validated_output) if result.validated_output is not None else result.parsed_json

    if mode == "checklist" and isinstance(result.validated_output, ChecklistPayload):
        _render_checklist_view(result.validated_output)
    elif mode == "friendly" and result.validated_output is not None:
        _render_friendly_payload(result.validated_output)
    else:
        if payload_json is not None:
            st.json(payload_json)
        elif result.raw_output_text:
            st.code(result.raw_output_text)

    if result.source_documents:
        st.caption(f"Source documents: {', '.join(result.source_documents)}")

    export_payload = payload_json or {"raw_output_text": result.raw_output_text, "task_type": result.task_type}
    st.download_button(
        "Download structured JSON",
        data=json.dumps(export_payload, ensure_ascii=False, indent=2),
        file_name=f"structured_{result.task_type}_{result.execution_id[:8]}.json",
        mime="application/json",
        width="stretch",
    )
