from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from .ai_lab_common import compact_rows, render_labeled_value_grid, render_message_list, render_panel_header


def _format_timestamp(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"
    return text.replace("T", " ")[:19]


def _format_rate(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.0%}"
    return "n/a"


def _top_label(counter_payload: object) -> str:
    if not isinstance(counter_payload, dict) or not counter_payload:
        return "n/a"
    name, count = max(counter_payload.items(), key=lambda item: int(item[1] or 0))
    return f"{name} ({count})"


def _build_langgraph_recent_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in list(reversed(entries[-15:])):
        quality_delta = float(entry.get("quality_delta") or 0.0) if isinstance(entry.get("quality_delta"), (int, float)) else 0.0
        latency_delta = float(entry.get("latency_delta_s") or 0.0) if isinstance(entry.get("latency_delta_s"), (int, float)) else 0.0
        rows.append(
            {
                "timestamp": entry.get("timestamp"),
                "task": entry.get("task_type"),
                "primary": entry.get("primary_strategy_used"),
                "alternate": entry.get("alternate_strategy_used"),
                "same_success": entry.get("same_success"),
                "quality_delta": quality_delta,
                "quality_winner": "alternate" if quality_delta > 0.01 else "primary" if quality_delta < -0.01 else "empate",
                "latency_delta_s": latency_delta,
                "latency_winner": "alternate" if latency_delta < -0.05 else "primary" if latency_delta > 0.05 else "empate",
                "alternate_avoided_review": entry.get("alternate_avoided_review"),
                "query": entry.get("query"),
            }
        )
    return rows


def _build_document_agent_recent_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "timestamp": entry.get("timestamp"),
            "intent": entry.get("user_intent"),
            "tool": entry.get("tool_used"),
            "confidence": entry.get("confidence"),
            "needs_review": entry.get("needs_review"),
            "needs_review_reason": entry.get("needs_review_reason"),
            "source_count": entry.get("source_count"),
            "query": entry.get("query"),
        }
        for entry in list(reversed(entries[-15:]))
    ]


def render_workflow_inspector_history_panel(
    *,
    phase55_langgraph_shadow_log_path: Path,
    phase55_langgraph_shadow_log_summary: dict[str, Any],
    phase55_langgraph_shadow_log_entries: list[dict[str, Any]],
    phase6_document_agent_log_path: Path,
    phase6_document_agent_log_summary: dict[str, Any],
    phase6_document_agent_log_entries: list[dict[str, Any]],
) -> dict[str, bool]:
    actions = {
        "clear_langgraph_shadow_log": False,
        "clear_document_agent_log": False,
    }

    render_panel_header(
        "Diagnóstico operacional de execução",
        "Compare direct vs LangGraph, leia o comportamento recente do Document Operations Copilot e comece pelos casos que exigiram revisão humana.",
    )
    render_labeled_value_grid(
        [
            {
                "label": "Workflow health",
                "value": (
                    "🔴 Intervir"
                    if float(phase6_document_agent_log_summary.get("needs_review_rate") or 0.0) > 0.15
                    or int(phase6_document_agent_log_summary.get("runs_with_tool_errors") or 0) > 0
                    else "🟢 Confortável"
                ),
            },
            {
                "label": "Dominant route",
                "value": _top_label(phase6_document_agent_log_summary.get("workflow_route_decision_counts")),
                "compact": True,
                "show_full": True,
                "max_chars": 42,
            },
            {
                "label": "Top guardrail",
                "value": _top_label(phase6_document_agent_log_summary.get("workflow_guardrail_decision_counts")),
                "compact": True,
                "show_full": True,
                "max_chars": 42,
            },
            {
                "label": "Top review reason",
                "value": _top_label(phase6_document_agent_log_summary.get("review_reasons")),
                "compact": True,
                "show_full": True,
                "max_chars": 42,
            },
        ],
        columns=4,
    )

    overview_col_1, overview_col_2, overview_col_3, overview_col_4 = st.columns(4)
    overview_col_1.metric("Shadow runs", int(phase55_langgraph_shadow_log_summary.get("total_runs") or 0))
    overview_col_2.metric("Review evitado", int(phase55_langgraph_shadow_log_summary.get("alternate_avoided_review_count") or 0))
    overview_col_3.metric("Doc-agent runs", int(phase6_document_agent_log_summary.get("total_runs") or 0))
    overview_col_4.metric("Needs review", f"{float(phase6_document_agent_log_summary.get('needs_review_rate') or 0.0):.0%}")

    overview_col_5, overview_col_6, overview_col_7, overview_col_8 = st.columns(4)
    overview_col_5.metric("Δ qualidade média", f"{float(phase55_langgraph_shadow_log_summary.get('avg_quality_delta') or 0.0):.3f}")
    overview_col_6.metric("Δ latência média", f"{float(phase55_langgraph_shadow_log_summary.get('avg_latency_delta_s') or 0.0):.2f}s")
    overview_col_7.metric("Sucesso do agente", f"{float(phase6_document_agent_log_summary.get('success_rate') or 0.0):.0%}")
    overview_col_8.metric("Erros de tool", int(phase6_document_agent_log_summary.get("runs_with_tool_errors") or 0))

    workflow_watchouts: list[str] = []
    if int(phase55_langgraph_shadow_log_summary.get("alternate_avoided_review_count") or 0) > 0:
        workflow_watchouts.append("A estratégia alternativa já evitou `needs_review` em parte dos casos; vale inspecionar esses exemplos no histórico shadow.")
    if float(phase55_langgraph_shadow_log_summary.get("avg_quality_delta") or 0.0) < -0.05:
        workflow_watchouts.append("O caminho alternativo vem perdendo qualidade em média; revisar guardrails e estratégia de contexto antes de promovê-lo.")
    if int(phase6_document_agent_log_summary.get("runs_with_tool_errors") or 0) > 0:
        workflow_watchouts.append("Há execuções recentes do agente com erro de tool; revisar roteamento, disponibilidade e fallback das ferramentas.")
    if float(phase6_document_agent_log_summary.get("needs_review_rate") or 0.0) > 0.15:
        workflow_watchouts.append("A taxa de `needs_review` do agente está acima do conforto operacional; investigar motivos de revisão humana e gaps de grounding.")
    if workflow_watchouts:
        render_panel_header("Leitura diagnóstica")
        render_message_list(workflow_watchouts)

    render_panel_header(
        "Decision memo · direct vs LangGraph",
        "Leia esta comparação como uma decisão de engenharia: quando o alternate path agrega segurança/qualidade e quando ele só adiciona latência operacional.",
    )
    memo_col_1, memo_col_2, memo_col_3 = st.columns(3)
    memo_col_1.metric(
        "Review avoided",
        int(phase55_langgraph_shadow_log_summary.get("alternate_avoided_review_count") or 0),
    )
    memo_col_2.metric(
        "Avg quality delta",
        f"{float(phase55_langgraph_shadow_log_summary.get('avg_quality_delta') or 0.0):.3f}",
    )
    memo_col_3.metric(
        "Avg latency delta",
        f"{float(phase55_langgraph_shadow_log_summary.get('avg_latency_delta_s') or 0.0):.2f}s",
    )
    decision_notes: list[str] = []
    if int(phase55_langgraph_shadow_log_summary.get("alternate_avoided_review_count") or 0) > 0:
        decision_notes.append("O caminho alternativo já evitou revisão humana em parte dos casos; bons candidatos para promoção controlada ou guardrail específico.")
    if float(phase55_langgraph_shadow_log_summary.get("avg_quality_delta") or 0.0) > 0.03:
        decision_notes.append("O caminho alternativo está agregando qualidade média; priorize investigar quais intents/tasks concentram esse ganho.")
    if float(phase55_langgraph_shadow_log_summary.get("avg_latency_delta_s") or 0.0) > 5.0:
        decision_notes.append("O caminho alternativo está adicionando latência relevante; trate-o como ferramenta cirúrgica, não como default automático.")
    if not decision_notes:
        decision_notes.append("No momento, direct vs LangGraph parecem próximos; continue comparando por task e por motivo de `needs_review` antes de mudar defaults.")
    render_message_list(decision_notes, level="info")

    if phase6_document_agent_log_entries:
        recent_entries = _build_document_agent_recent_rows(phase6_document_agent_log_entries)
        problematic_rows = [
            row
            for row in recent_entries
            if row.get("needs_review") or str(row.get("needs_review_reason") or "").strip() or not row.get("tool")
        ]
        if problematic_rows:
            with st.expander("Casos prioritários para inspeção humana", expanded=False):
                st.dataframe(
                    compact_rows(
                        problematic_rows[:10],
                        field_limits={"query": 72, "needs_review_reason": 48, "tool": 28, "intent": 28},
                    ),
                    width="stretch",
                )

    with st.expander("Fase 5.5 · histórico direct vs LangGraph", expanded=False):
        st.caption(f"Log local: `{phase55_langgraph_shadow_log_path.name}`")
        summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
        summary_col_1.metric("Runs", int(phase55_langgraph_shadow_log_summary.get("total_runs") or 0))
        summary_col_2.metric("Same success", f"{float(phase55_langgraph_shadow_log_summary.get('same_success_rate') or 0.0):.0%}")
        summary_col_3.metric("Δ qualidade", f"{float(phase55_langgraph_shadow_log_summary.get('avg_quality_delta') or 0.0):.3f}")
        summary_col_4.metric("Δ latência", f"{float(phase55_langgraph_shadow_log_summary.get('avg_latency_delta_s') or 0.0):.2f}s")
        st.caption(
            f"Última execução shadow: {_format_timestamp(phase55_langgraph_shadow_log_entries[-1].get('timestamp') if phase55_langgraph_shadow_log_entries else None)}"
        )
        if phase55_langgraph_shadow_log_summary.get("strategy_pairs"):
            st.caption("Pares de estratégia observados")
            st.dataframe(
                compact_rows(
                    [
                        {"strategy_pair": name, "count": count}
                        for name, count in dict(phase55_langgraph_shadow_log_summary.get("strategy_pairs") or {}).items()
                    ],
                    field_limits={"strategy_pair": 56},
                ),
                width="stretch",
            )
        if phase55_langgraph_shadow_log_summary.get("alternate_fallbacks"):
            st.caption("Fallbacks observados na estratégia alternativa")
            st.dataframe(
                compact_rows(
                    [
                        {"fallback_reason": name, "count": count}
                        for name, count in dict(phase55_langgraph_shadow_log_summary.get("alternate_fallbacks") or {}).items()
                    ],
                    field_limits={"fallback_reason": 56},
                ),
                width="stretch",
            )
        if phase55_langgraph_shadow_log_entries:
            recent_entries = _build_langgraph_recent_rows(phase55_langgraph_shadow_log_entries)
            st.caption("Casos recentes para investigação")
            st.dataframe(
                compact_rows(
                    recent_entries,
                    field_limits={"query": 72, "primary": 28, "alternate": 28},
                ),
                width="stretch",
            )
            actions["clear_langgraph_shadow_log"] = st.button(
                "Limpar histórico direct vs LangGraph",
                key="phase55_clear_langgraph_shadow_log_modular",
            )
        else:
            st.caption("Nenhuma comparação direct vs LangGraph registrada ainda.")

    with st.expander("Fase 6 · histórico do Document Operations Copilot", expanded=False):
        st.caption(f"Log local: `{phase6_document_agent_log_path.name}`")
        summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
        summary_col_1.metric("Runs", int(phase6_document_agent_log_summary.get("total_runs") or 0))
        summary_col_2.metric("Success", f"{float(phase6_document_agent_log_summary.get('success_rate') or 0.0):.0%}")
        summary_col_3.metric("Needs review", f"{float(phase6_document_agent_log_summary.get('needs_review_rate') or 0.0):.0%}")
        summary_col_4.metric("Confidence", f"{float(phase6_document_agent_log_summary.get('avg_confidence') or 0.0):.0%}")
        st.caption(
            f"Última execução do agente: {_format_timestamp(phase6_document_agent_log_summary.get('latest_timestamp'))} · runs com erro de tool: {int(phase6_document_agent_log_summary.get('runs_with_tool_errors') or 0)}"
        )
        for label, field_name, key_name in [
            ("Distribuição por intenção", "intent_counts", "intent"),
            ("Distribuição por tool", "tool_counts", "tool"),
            ("Decisões de rota", "workflow_route_decision_counts", "route_decision"),
            ("Decisões de guardrail", "workflow_guardrail_decision_counts", "guardrail_decision"),
            ("Motivos de revisão humana", "review_reasons", "needs_review_reason"),
        ]:
            rows = phase6_document_agent_log_summary.get(field_name)
            if isinstance(rows, dict) and rows:
                st.caption(label)
                st.dataframe(
                    compact_rows(
                        [{key_name: name, "count": count} for name, count in rows.items()],
                        field_limits={key_name: 56},
                    ),
                    width="stretch",
                )
        if phase6_document_agent_log_entries:
            recent_entries = _build_document_agent_recent_rows(phase6_document_agent_log_entries)
            needs_review_rows = [row for row in recent_entries if row.get("needs_review")]
            if needs_review_rows:
                st.caption("Casos recentes com revisão humana")
                st.dataframe(
                    compact_rows(
                        needs_review_rows[:10],
                        field_limits={"query": 72, "needs_review_reason": 48, "tool": 28, "intent": 28},
                    ),
                    width="stretch",
                )
            st.caption("Execuções recentes do agente documental")
            st.dataframe(
                compact_rows(
                    recent_entries,
                    field_limits={"query": 72, "needs_review_reason": 48, "tool": 28, "intent": 28},
                ),
                width="stretch",
            )
            actions["clear_document_agent_log"] = st.button(
                "Limpar histórico do agente documental",
                key="phase6_clear_document_agent_log_modular",
            )
        else:
            st.caption("Nenhuma execução auditável do Document Operations Copilot registrada ainda.")

    return actions