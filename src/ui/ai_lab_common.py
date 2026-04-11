from __future__ import annotations

from html import escape
import re
from typing import Any, Sequence

import pandas as pd
import streamlit as st


_WRAP_CSS_STATE_KEY = "_ai_lab_wrap_css_injected"


def ensure_streamlit_text_wrap_css() -> None:
    if st.session_state.get(_WRAP_CSS_STATE_KEY):
        return

    st.markdown(
        """
        <style>
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"],
        div[data-testid="stCaptionContainer"] p,
        div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stMarkdownContainer"] li,
        div[data-testid="stCodeBlock"] pre,
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
        }

        div[data-testid="stDataFrame"] [role="gridcell"],
        div[data-testid="stDataFrame"] [role="columnheader"] {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            word-break: break-word !important;
            line-height: 1.25 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state[_WRAP_CSS_STATE_KEY] = True


def compact_text(value: Any, *, max_chars: int = 72, middle: bool = False) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return "n/a"
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return "…"
    if middle:
        left = max(1, (max_chars - 1) // 2)
        right = max(1, max_chars - left - 1)
        return f"{text[:left].rstrip()}…{text[-right:].lstrip()}"
    return text[: max_chars - 1].rstrip() + "…"


def build_selectbox_options(
    values: Sequence[Any],
    *,
    max_chars: int = 72,
    middle: bool = False,
    formatter: callable | None = None,
) -> dict[str, str]:
    options: dict[str, str] = {}
    for index, raw_value in enumerate(values, start=1):
        value = str(raw_value or "").strip()
        if not value:
            continue
        display_value = str(formatter(raw_value) if callable(formatter) else value).strip() or value
        label = f"{index:02d} · {compact_text(display_value, max_chars=max_chars, middle=middle)}"
        deduped_label = label
        suffix = 2
        while deduped_label in options:
            deduped_label = f"{label} ({suffix})"
            suffix += 1
        options[deduped_label] = value
    return options


def compact_rows(
    rows: Sequence[dict[str, Any]],
    *,
    field_limits: dict[str, int] | None = None,
    middle_fields: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    normalized_limits = field_limits or {}
    normalized_middle_fields = set(middle_fields or [])
    compacted: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        next_row: dict[str, Any] = {}
        for key, value in row.items():
            if key in normalized_limits and isinstance(value, str):
                next_row[key] = compact_text(
                    value,
                    max_chars=int(normalized_limits[key]),
                    middle=key in normalized_middle_fields,
                )
            else:
                next_row[key] = value
        compacted.append(next_row)
    return compacted


_HUMANIZED_TOKEN_MAP = {
    "ai": "AI",
    "avg": "Avg",
    "cv": "CV",
    "doc": "Doc",
    "docs": "Docs",
    "eval": "Eval",
    "evals": "Evals",
    "f1": "F1",
    "fail": "FAIL",
    "json": "JSON",
    "langgraph": "LangGraph",
    "lora": "LoRA",
    "mcp": "MCP",
    "ocr": "OCR",
    "pass": "PASS",
    "pdf": "PDF",
    "peft": "PEFT",
    "rag": "RAG",
    "ui": "UI",
    "vl": "VL",
    "warn": "WARN",
}

_HUMANIZED_REASON_MAP = {
    "consider_targeted_adaptation_only_for_specific_tasks": "Considerar adaptação direcionada apenas para tasks específicas.",
    "prompt_rag_schema_iteration_still_sufficient_globally": "Prompt + RAG + schema ainda parecem suficientes globalmente.",
    "prompt_rag_stack_currently_sufficient": "A stack atual de prompt + RAG está suficiente para esta task.",
    "improve_checklist_decomposition_and_source_alignment": "Melhorar decomposição de checklist e alinhamento com a fonte.",
    "improve_ocr_router_contact_postprocessing_before_model_adaptation": "Melhorar OCR/router/pós-processamento de contatos antes de pensar em adaptação de modelo.",
    "improve_grounding_and_field_resolution_before_model_adaptation": "Melhorar grounding e resolução de campos antes de pensar em adaptação de modelo.",
    "consider_task_specific_model_adaptation_after_more_eval_cases": "Considerar adaptação específica por task depois de ampliar os casos de eval.",
    "continue_prompt_grounding_and_schema_iteration": "Continuar iterando prompt, grounding e schema.",
    "expand_eval_cases_and_iterate_prompt_rag_schema": "Expandir os casos de eval e seguir iterando prompt + RAG + schema.",
    "insufficient_eval_data": "Ainda não há dados suficientes de eval.",
    "manual_review_required": "Revisão manual obrigatória.",
    "prompt_rag_schema_sufficient": "Prompt + RAG + schema suficientes.",
}


def humanize_identifier(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"

    parts = re.split(r"([:_-])", text)
    normalized_parts: list[str] = []
    for part in parts:
        if part in {":", "-"}:
            normalized_parts.append(f" {part} ")
            continue
        if part == "_":
            normalized_parts.append(" ")
            continue
        tokens = [token for token in re.split(r"\s+", part) if token]
        formatted_tokens: list[str] = []
        for token in tokens:
            normalized_token = token.strip().lower()
            if normalized_token in _HUMANIZED_TOKEN_MAP:
                formatted_tokens.append(_HUMANIZED_TOKEN_MAP[normalized_token])
            elif normalized_token.isdigit():
                formatted_tokens.append(normalized_token)
            else:
                formatted_tokens.append(normalized_token.capitalize())
        normalized_parts.append(" ".join(formatted_tokens))

    normalized = "".join(normalized_parts)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or text


def humanize_reason_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"

    normalized = text.lower()
    if normalized in _HUMANIZED_REASON_MAP:
        return _HUMANIZED_REASON_MAP[normalized]

    if ":" in text:
        prefix, suffix = text.split(":", 1)
        return f"{humanize_identifier(prefix)}: {suffix.strip()}"

    return humanize_identifier(text)


def humanize_eval_recommendation(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"
    normalized = text.lower()
    return _HUMANIZED_REASON_MAP.get(normalized, humanize_reason_text(text))


def humanize_priority(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    mapping = {"high": "Alta", "medium": "Média", "low": "Baixa"}
    return mapping.get(normalized, humanize_identifier(value))


def humanize_task_type(value: Any) -> str:
    task_map = {
        "cv_contacts": "CV Contacts",
        "cv_analysis": "CV Analysis",
        "code_analysis": "Code Analysis",
        "document_agent": "Document Agent",
        "intent_classification": "Intent Classification",
    }
    normalized = str(value or "").strip().lower()
    return task_map.get(normalized, humanize_identifier(value))


def humanize_suite_name(value: Any) -> str:
    suite_map = {
        "phase8_agent_workflow_eval": "Phase 8 · Agent Workflow Eval",
        "phase8_agent_workflow_eval_cases": "Phase 8 · Agent Workflow Eval Cases",
        "phase8_5_code_embedding_questions": "Phase 8.5 · Code Embedding Questions",
    }
    normalized = str(value or "").strip().lower()
    return suite_map.get(normalized, humanize_identifier(value))


def render_labeled_value_grid(
    items: Sequence[dict[str, Any]],
    *,
    columns: int = 3,
    border: bool = True,
) -> None:
    normalized_items = [item for item in items if isinstance(item, dict)]
    if not normalized_items:
        return

    cols = st.columns(min(max(columns, 1), len(normalized_items)))
    for index, item in enumerate(normalized_items):
        label = str(item.get("label") or "").strip()
        raw_value = str(item.get("value") if item.get("value") is not None else "n/a").strip() or "n/a"
        display_value = (
            compact_text(
                raw_value,
                max_chars=int(item.get("max_chars") or 72),
                middle=bool(item.get("compact_middle")),
            )
            if bool(item.get("compact"))
            else raw_value
        )
        detail = str(item.get("detail") or "").strip()
        show_full_value = bool(item.get("show_full")) and display_value != raw_value

        with cols[index % len(cols)]:
            with st.container(border=border):
                if label:
                    st.caption(label)
                st.markdown(
                    (
                        "<div style='font-weight:600;font-size:1.02rem;line-height:1.35;"
                        "overflow-wrap:anywhere;word-break:break-word;'>"
                        f"{escape(display_value)}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
                if show_full_value:
                    st.caption(raw_value)
                if detail:
                    st.caption(detail)


def render_panel_header(title: str, description: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if description:
        st.caption(description)


def render_message_list(messages: Sequence[str], *, level: str = "warning") -> None:
    renderer = getattr(st, level, st.warning)
    for message in messages:
        renderer(str(message))


def render_metric_row(
    metrics: Sequence[tuple[str, Any, str | None]],
    *,
    columns: int = 4,
) -> None:
    if not metrics:
        return

    cols = st.columns(min(max(columns, 1), len(metrics)))
    for index, (label, value, delta) in enumerate(metrics):
        cols[index % len(cols)].metric(label, value, delta=delta)


def render_status_badges(items: Sequence[tuple[str, str]]) -> None:
    if not items:
        return

    palette = {
        "healthy": {"background": "#e8f5e9", "color": "#1b5e20", "border": "#a5d6a7"},
        "attention": {"background": "#fff8e1", "color": "#8d6e00", "border": "#ffe082"},
        "critical": {"background": "#ffebee", "color": "#b71c1c", "border": "#ef9a9a"},
        "info": {"background": "#e3f2fd", "color": "#0d47a1", "border": "#90caf9"},
        "neutral": {"background": "#f5f5f5", "color": "#424242", "border": "#e0e0e0"},
    }

    parts = ["<div style='display:flex;flex-wrap:wrap;gap:0.45rem;margin:0.35rem 0 0.85rem 0;'>"]
    for label, tone in items:
        style = palette.get(tone, palette["neutral"])
        parts.append(
            "<span style="
            f"display:inline-flex;align-items:center;padding:0.25rem 0.65rem;"
            f"border-radius:999px;font-size:0.82rem;font-weight:600;"
            f"background:{style['background']};color:{style['color']};border:1px solid {style['border']};"
            ">"
            f"{escape(str(label))}"
            "</span>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_bar_chart_from_rows(
    rows: Sequence[dict[str, Any]],
    *,
    index_field: str,
    value_fields: Sequence[str],
    height: int = 260,
) -> None:
    dataframe = pd.DataFrame(list(rows))
    available_fields = [field for field in value_fields if field in dataframe.columns]
    if dataframe.empty or index_field not in dataframe.columns or not available_fields:
        return

    chart_df = dataframe[[index_field, *available_fields]].copy().set_index(index_field)
    st.bar_chart(chart_df, height=height)


def render_line_chart_from_rows(
    rows: Sequence[dict[str, Any]],
    *,
    index_field: str,
    value_fields: Sequence[str],
    height: int = 260,
) -> None:
    dataframe = pd.DataFrame(list(rows))
    available_fields = [field for field in value_fields if field in dataframe.columns]
    if dataframe.empty or index_field not in dataframe.columns or not available_fields:
        return

    chart_df = dataframe[[index_field, *available_fields]].copy().set_index(index_field)
    st.line_chart(chart_df, height=height)


def render_scatter_chart_from_rows(
    rows: Sequence[dict[str, Any]],
    *,
    x_field: str,
    y_field: str,
    color_field: str | None = None,
    size_field: str | None = None,
    height: int = 280,
) -> None:
    dataframe = pd.DataFrame(list(rows))
    if dataframe.empty or x_field not in dataframe.columns or y_field not in dataframe.columns:
        return

    chart_fields = [x_field, y_field]
    if color_field and color_field in dataframe.columns:
        chart_fields.append(color_field)
    if size_field and size_field in dataframe.columns:
        chart_fields.append(size_field)

    chart_df = dataframe[chart_fields].copy()
    kwargs: dict[str, Any] = {"x": x_field, "y": y_field, "height": height}
    if color_field and color_field in chart_df.columns:
        kwargs["color"] = color_field
    if size_field and size_field in chart_df.columns:
        kwargs["size"] = size_field
    try:
        st.scatter_chart(chart_df, **kwargs)
    except Exception:
        st.dataframe(chart_df, width="stretch")


def render_heatmap_from_rows(
    rows: Sequence[dict[str, Any]],
    *,
    row_field: str,
    column_field: str,
    value_field: str,
    aggfunc: str = "mean",
) -> None:
    dataframe = pd.DataFrame(list(rows))
    if dataframe.empty or row_field not in dataframe.columns or column_field not in dataframe.columns or value_field not in dataframe.columns:
        return

    pivot = pd.pivot_table(
        dataframe,
        index=row_field,
        columns=column_field,
        values=value_field,
        aggfunc=aggfunc,
        fill_value=0.0,
    )
    if pivot.empty:
        return
    st.dataframe(pivot.style.background_gradient(cmap="YlOrRd"), width="stretch")