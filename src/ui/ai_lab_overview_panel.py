from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from .ai_lab_common import (
    render_bar_chart_from_rows,
    render_line_chart_from_rows,
    render_labeled_value_grid,
    render_message_list,
    render_panel_header,
    render_status_badges,
)
from .ai_lab_shell import AI_LAB_TAB_SPECS


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    simplified = text.replace("T", " ")
    for candidate, fmt in (
        (simplified[:19], "%Y-%m-%d %H:%M:%S"),
        (simplified[:16], "%Y-%m-%d %H:%M"),
        (simplified[:10], "%Y-%m-%d"),
    ):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def _format_timestamp(value: object, *, compact: bool = True) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        text = str(value or "").strip()
        return "n/a" if not text else text.replace("T", " ")[:16]

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone()
    return parsed.strftime("%d/%m %H:%M" if compact else "%d/%m/%Y %H:%M")


def _format_timestamp_recency(value: object) -> str | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None

    now = datetime.now(timezone.utc) if parsed.tzinfo is not None else datetime.now()
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc)
    elapsed_seconds = max(0, int((now - parsed).total_seconds()))

    if elapsed_seconds < 60:
        return "agora"
    if elapsed_seconds < 3600:
        return f"há {elapsed_seconds // 60} min"
    if elapsed_seconds < 86400:
        return f"há {elapsed_seconds // 3600} h"

    elapsed_days = elapsed_seconds // 86400
    if elapsed_days < 30:
        return f"há {elapsed_days} d"
    if elapsed_days < 365:
        return f"há {elapsed_days // 30} mês(es)"
    return f"há {elapsed_days // 365} ano(s)"


def _format_duration_seconds(value: object) -> str:
    try:
        seconds = float(value or 0.0)
    except (TypeError, ValueError):
        return "n/a"

    if seconds <= 0.0:
        return "n/a"
    if seconds < 60.0:
        return f"{seconds:.1f}s"

    rounded_seconds = int(round(seconds))
    minutes, remaining_seconds = divmod(rounded_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:02d}s"

    hours, remaining_minutes = divmod(minutes, 60)
    return f"{hours}h {remaining_minutes:02d}m"


def _format_rate(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.0%}"
    return "n/a"


def _status_label(level: str, label: str) -> str:
    icon = {
        "healthy": "🟢",
        "attention": "🟡",
        "critical": "🔴",
        "bootstrap": "⚪",
    }.get(level, "⚪")
    return f"{icon} {label}"


def _classify_index_status(vector_backend_status_preview: dict[str, Any], indexed_documents_count: int) -> str:
    status = str(vector_backend_status_preview.get("status") or "").strip().lower()
    if indexed_documents_count == 0:
        return _status_label("bootstrap", "Bootstrap")
    if status in {"dessincronizado", "out_of_sync"}:
        return _status_label("critical", "Fora de sync")
    if status in {"fallback_local", "local_fallback"}:
        return _status_label("attention", "Fallback local")
    return _status_label("healthy", "Saudável")


def _classify_quality_status(phase8_eval_summary: dict[str, Any], runtime_execution_summary: dict[str, Any]) -> str:
    fail_rate = float(phase8_eval_summary.get("fail_rate") or 0.0)
    needs_review_rate = float(runtime_execution_summary.get("needs_review_rate") or 0.0)
    pass_rate = float(phase8_eval_summary.get("pass_rate") or 0.0)
    if fail_rate > 0.1 or needs_review_rate > 0.2:
        return _status_label("critical", "Crítico")
    if fail_rate > 0.0 or needs_review_rate > 0.1 or pass_rate < 0.8:
        return _status_label("attention", "Atenção")
    return _status_label("healthy", "Confortável")


def _classify_runtime_status(runtime_execution_summary: dict[str, Any]) -> str:
    error_rate = float(runtime_execution_summary.get("error_rate") or 0.0)
    avg_latency_s = float(runtime_execution_summary.get("avg_latency_s") or 0.0)
    if error_rate > 0.1 or avg_latency_s > 60.0:
        return _status_label("critical", "Instável")
    if error_rate > 0.0 or avg_latency_s > 20.0:
        return _status_label("attention", "Monitorar")
    return _status_label("healthy", "Estável")


def _classify_workflow_status(phase6_document_agent_log_summary: dict[str, Any]) -> str:
    total_runs = int(phase6_document_agent_log_summary.get("total_runs") or 0)
    needs_review_rate = float(phase6_document_agent_log_summary.get("needs_review_rate") or 0.0)
    tool_errors = int(phase6_document_agent_log_summary.get("runs_with_tool_errors") or 0)
    if total_runs == 0:
        return _status_label("bootstrap", "Sem evidência")
    if tool_errors > 0 or needs_review_rate > 0.2:
        return _status_label("critical", "Intervir")
    if needs_review_rate > 0.1:
        return _status_label("attention", "Investigar")
    return _status_label("healthy", "Confiável")


def _classify_mcp_status(runtime_execution_summary: dict[str, Any]) -> str:
    mcp_runs = int(runtime_execution_summary.get("mcp_runs") or 0)
    mcp_error_rate = float(runtime_execution_summary.get("mcp_error_rate") or 0.0)
    if mcp_runs == 0:
        return _status_label("bootstrap", "Sem tráfego")
    if mcp_error_rate > 0.1:
        return _status_label("critical", "Erro")
    if mcp_error_rate > 0.0:
        return _status_label("attention", "Parcial")
    return _status_label("healthy", "Operacional")


def _classify_budget_status(runtime_execution_summary: dict[str, Any]) -> str:
    context_pressure = float(runtime_execution_summary.get("avg_context_pressure_ratio") or 0.0)
    truncated_prompt_rate = float(runtime_execution_summary.get("truncated_prompt_rate") or 0.0)
    auto_degrade_rate = float(runtime_execution_summary.get("auto_degrade_rate") or 0.0)
    if context_pressure > 0.9 or truncated_prompt_rate > 0.25:
        return _status_label("critical", "Sob pressão")
    if context_pressure > 0.7 or auto_degrade_rate > 0.15:
        return _status_label("attention", "Atenção")
    return _status_label("healthy", "Controlado")


def _build_operational_alerts(
    *,
    vector_backend_status_preview: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
    runtime_execution_summary: dict[str, Any],
    indexed_documents_count: int,
) -> list[str]:
    alerts: list[str] = []
    status = str(vector_backend_status_preview.get("status") or "")
    if status in {"dessincronizado", "out_of_sync"}:
        alerts.append("Backend vetorial fora de sincronização.")
    if status in {"fallback_local", "local_fallback"}:
        alerts.append("Backend vetorial operando em fallback local.")
    if status in {"no_index", "empty", "not_initialized"} and indexed_documents_count == 0:
        alerts.append("Ainda não há base documental indexada no AI Lab.")
    if float(phase8_eval_summary.get("fail_rate") or 0.0) > 0.0:
        alerts.append("Existem evals recentes com FAIL; revisar a guia de Evals & Diagnóstico.")
    if float(runtime_execution_summary.get("needs_review_rate") or 0.0) > 0.0:
        alerts.append("Há execuções recentes com `needs_review`; revisar `Inspector de Workflow & Structured` e `Runtime & Observabilidade`.")
    return alerts


def _build_next_actions(
    *,
    indexed_documents_count: int,
    runtime_runs: int,
    benchmark_runs: int,
    eval_runs: int,
    alerts: list[str],
) -> list[str]:
    actions: list[str] = []
    if indexed_documents_count == 0:
        actions.append("Abrir `Runtime & Observabilidade` e indexar o primeiro corpus documental do lab.")
    if indexed_documents_count > 0 and runtime_runs == 0:
        actions.append("Executar pelo menos uma rodada em `Experimentos de Chat e Documentos` ou `Inspector de Workflow & Structured` para gerar telemetria real.")
    if benchmark_runs == 0:
        actions.append("Rodar um benchmark em `Benchmarks & Comparação de Modelos` para começar a comparação defensável entre modelos/providers.")
    if eval_runs == 0:
        actions.append("Popular `Evals & Diagnóstico` com uma primeira rodada de suites persistidas para sair do modo puramente exploratório.")
    if alerts:
        actions.append("Priorizar os alertas operacionais ativos antes de expandir novas trilhas do AI Lab.")
    if not actions:
        actions.append("Seguir refinando benchmark, evals e observabilidade com foco em regressões, custo e qualidade por caso de uso.")
    return actions[:4]


def _build_overview_trend_rows(
    *,
    runtime_execution_summary: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
    phase6_document_agent_log_summary: dict[str, Any],
) -> list[dict[str, float | str]]:
    recent_window = runtime_execution_summary.get("recent_window_summary") if isinstance(runtime_execution_summary.get("recent_window_summary"), dict) else {}
    previous_window = runtime_execution_summary.get("previous_window_summary") if isinstance(runtime_execution_summary.get("previous_window_summary"), dict) else {}
    return [
        {
            "window": "previous",
            "runtime_latency_s": float(previous_window.get("avg_latency_s") or 0.0),
            "runtime_error_rate": float(previous_window.get("error_rate") or 0.0),
            "runtime_needs_review_rate": float(previous_window.get("needs_review_rate") or 0.0),
            "context_pressure_ratio": float(previous_window.get("avg_context_pressure_ratio") or 0.0),
            "mcp_error_rate": float(previous_window.get("mcp_error_rate") or 0.0),
        },
        {
            "window": "recent",
            "runtime_latency_s": float(recent_window.get("avg_latency_s") or float(runtime_execution_summary.get("avg_latency_s") or 0.0)),
            "runtime_error_rate": float(recent_window.get("error_rate") or float(runtime_execution_summary.get("error_rate") or 0.0)),
            "runtime_needs_review_rate": float(recent_window.get("needs_review_rate") or float(runtime_execution_summary.get("needs_review_rate") or 0.0)),
            "context_pressure_ratio": float(recent_window.get("avg_context_pressure_ratio") or float(runtime_execution_summary.get("avg_context_pressure_ratio") or 0.0)),
            "mcp_error_rate": float(recent_window.get("mcp_error_rate") or float(runtime_execution_summary.get("mcp_error_rate") or 0.0)),
        },
    ]


def _build_alert_badges(alerts: list[str]) -> list[tuple[str, str]]:
    if not alerts:
        return [("Sem alertas críticos ativos", "healthy")]
    badges: list[tuple[str, str]] = []
    for alert in alerts[:4]:
        normalized = str(alert).lower()
        tone = "critical" if any(keyword in normalized for keyword in ["fail", "erro", "out of sync", "fora de sync"]) else "attention"
        badges.append((alert, tone))
    return badges


def _render_health_snapshot_cards(
    *,
    vector_backend_status_preview: dict[str, Any],
    phase6_document_agent_log_summary: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
    runtime_execution_summary: dict[str, Any],
    indexed_documents_count: int,
    runtime_runs: int,
    doc_agent_runs: int,
) -> None:
    backend = str(vector_backend_status_preview.get("backend") or "n/a")
    cards = [
        {
            "label": "Saúde do índice",
            "status": _classify_index_status(vector_backend_status_preview, indexed_documents_count),
            "support": f"{indexed_documents_count} docs · backend {backend}",
        },
        {
            "label": "Qualidade dos evals",
            "status": _classify_quality_status(phase8_eval_summary, runtime_execution_summary),
            "support": (
                f"PASS {_format_rate(phase8_eval_summary.get('pass_rate'))}"
                f" · FAIL {_format_rate(phase8_eval_summary.get('fail_rate'))}"
            ),
        },
        {
            "label": "Saúde de runtime",
            "status": _classify_runtime_status(runtime_execution_summary),
            "support": f"{runtime_runs} execs · latência {_format_duration_seconds(runtime_execution_summary.get('avg_latency_s'))}",
        },
        {
            "label": "Workflow & guardrails",
            "status": _classify_workflow_status(phase6_document_agent_log_summary),
            "support": f"{doc_agent_runs} execs · review {_format_rate(phase6_document_agent_log_summary.get('needs_review_rate'))}",
        },
        {
            "label": "MCP & ops",
            "status": _classify_mcp_status(runtime_execution_summary),
            "support": (
                f"{int(runtime_execution_summary.get('mcp_runs') or 0)} execs"
                f" · erro {_format_rate(runtime_execution_summary.get('mcp_error_rate'))}"
            ),
        },
        {
            "label": "Custo / budget",
            "status": _classify_budget_status(runtime_execution_summary),
            "support": (
                f"pressão {float(runtime_execution_summary.get('avg_context_pressure_ratio') or 0.0):.2f}"
                f" · auto-degrade {_format_rate(runtime_execution_summary.get('auto_degrade_rate'))}"
            ),
        },
    ]

    render_panel_header(
        "Leitura rápida por dimensão",
        "Seis sinais operacionais com nome explícito, status legível e contexto mínimo para evitar truncamento e ambiguidade.",
    )
    cols = st.columns(3)
    for index, card in enumerate(cards):
        with cols[index % len(cols)]:
            with st.container(border=True):
                st.caption(card["label"])
                st.markdown(f"**{card['status']}**")
                st.caption(card["support"])


def _build_exec_scan_rows(
    *,
    phase8_eval_summary: dict[str, Any],
    runtime_execution_summary: dict[str, Any],
    phase6_document_agent_log_summary: dict[str, Any],
) -> list[dict[str, float | str]]:
    return [
        {
            "signal": "PASS em evals",
            "current": float(phase8_eval_summary.get("pass_rate") or 0.0),
        },
        {
            "signal": "Erro de runtime",
            "current": float(runtime_execution_summary.get("error_rate") or 0.0),
        },
        {
            "signal": "Needs review",
            "current": float(runtime_execution_summary.get("needs_review_rate") or 0.0),
        },
        {
            "signal": "Review do doc-agent",
            "current": float(phase6_document_agent_log_summary.get("needs_review_rate") or 0.0),
        },
        {
            "signal": "Pressão de budget",
            "current": float(runtime_execution_summary.get("avg_context_pressure_ratio") or 0.0),
        },
    ]


def render_lab_overview_panel(
    *,
    indexed_documents_preview: list[dict[str, Any]],
    vector_backend_status_preview: dict[str, Any],
    phase6_document_agent_log_summary: dict[str, Any],
    phase7_model_comparison_log_summary: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
    runtime_execution_summary: dict[str, Any],
) -> None:
    indexed_documents_count = len(indexed_documents_preview)
    benchmark_runs = int(phase7_model_comparison_log_summary.get("total_runs") or 0)
    eval_runs = int(phase8_eval_summary.get("total_runs") or 0)
    runtime_runs = int(runtime_execution_summary.get("total_runs") or 0)
    doc_agent_runs = int(phase6_document_agent_log_summary.get("total_runs") or 0)
    alerts = _build_operational_alerts(
        vector_backend_status_preview=vector_backend_status_preview,
        phase8_eval_summary=phase8_eval_summary,
        runtime_execution_summary=runtime_execution_summary,
        indexed_documents_count=indexed_documents_count,
    )
    overall_status = "Bootstrap" if indexed_documents_count == 0 else "Atenção" if alerts else "Estável"
    next_focus = (
        "Indexar corpus"
        if indexed_documents_count == 0
        else "Investigar FAILs"
        if float(phase8_eval_summary.get("fail_rate") or 0.0) > 0.0
        else "Reduzir needs_review"
        if float(runtime_execution_summary.get("needs_review_rate") or 0.0) > 0.0
        else "Expandir benchmark/evals"
    )

    render_panel_header(
        "AI Lab · centro de comando operacional",
        "Leia esta home como o cockpit executivo do sistema: saúde, regressões, custo, workflow e próximas ações antes do drilldown nas abas técnicas.",
    )
    st.info(
        "Esta home do AI Lab não é landing page de produto: ela resume o estado do sistema enquanto o produto em Gradio concentra os workflows de negócio. "
        "Use as guias abaixo para inspecionar benchmark/evals, runtime economics, workflow traces, OCR/VLM diagnostics e operações EvidenceOps."
    )

    _render_health_snapshot_cards(
        vector_backend_status_preview=vector_backend_status_preview,
        phase6_document_agent_log_summary=phase6_document_agent_log_summary,
        phase8_eval_summary=phase8_eval_summary,
        runtime_execution_summary=runtime_execution_summary,
        indexed_documents_count=indexed_documents_count,
        runtime_runs=runtime_runs,
        doc_agent_runs=doc_agent_runs,
    )

    render_status_badges(_build_alert_badges(alerts))

    st.markdown("### Cockpit operacional")
    render_labeled_value_grid(
        [
            {"label": "Status do lab", "value": overall_status},
            {"label": "Próximo foco", "value": next_focus},
            {"label": "Docs indexados", "value": indexed_documents_count},
            {"label": "Backend vetorial", "value": str(vector_backend_status_preview.get("backend") or "n/a")},
        ],
        columns=4,
    )

    render_labeled_value_grid(
        [
            {
                "label": "Último runtime",
                "value": _format_timestamp(runtime_execution_summary.get("latest_timestamp"), compact=False),
                "detail": _format_timestamp_recency(runtime_execution_summary.get("latest_timestamp")) or "sem recência disponível",
            },
            {
                "label": "Último eval",
                "value": _format_timestamp(phase8_eval_summary.get("latest_created_at"), compact=False),
                "detail": _format_timestamp_recency(phase8_eval_summary.get("latest_created_at")) or "sem recência disponível",
            },
            {
                "label": "Último benchmark",
                "value": _format_timestamp(phase7_model_comparison_log_summary.get("latest_timestamp"), compact=False),
                "detail": _format_timestamp_recency(phase7_model_comparison_log_summary.get("latest_timestamp")) or "sem recência disponível",
            },
            {
                "label": "Último doc-agent",
                "value": _format_timestamp(phase6_document_agent_log_summary.get("latest_timestamp"), compact=False),
                "detail": _format_timestamp_recency(phase6_document_agent_log_summary.get("latest_timestamp")) or "sem recência disponível",
            },
        ],
        columns=4,
    )

    render_labeled_value_grid(
        [
            {"label": "Benchmarks", "value": benchmark_runs},
            {"label": "PASS em evals", "value": f"{float(phase8_eval_summary.get('pass_rate') or 0.0):.0%}"},
            {"label": "Execuções runtime", "value": runtime_runs},
            {"label": "Execuções doc-agent", "value": doc_agent_runs},
        ],
        columns=4,
    )

    render_labeled_value_grid(
        [
            {"label": "Revisão humana", "value": f"{float(runtime_execution_summary.get('needs_review_rate') or 0.0):.0%}"},
            {"label": "Latência média", "value": _format_duration_seconds(runtime_execution_summary.get('avg_latency_s'))},
            {"label": "Docs indexados", "value": indexed_documents_count},
            {"label": "Backend vetorial", "value": str(vector_backend_status_preview.get("backend") or "n/a")},
        ],
        columns=4,
    )

    render_panel_header(
        "Tendências rápidas do command center",
        "Comparação rápida entre janela recente e anterior para qualidade, estabilidade e necessidade de revisão.",
    )
    trend_rows = _build_overview_trend_rows(
        runtime_execution_summary=runtime_execution_summary,
        phase8_eval_summary=phase8_eval_summary,
        phase6_document_agent_log_summary=phase6_document_agent_log_summary,
    )
    trend_chart_col_1, trend_chart_col_2 = st.columns(2)
    with trend_chart_col_1:
        st.caption("Latência e pressão de contexto")
        render_line_chart_from_rows(
            trend_rows,
            index_field="window",
            value_fields=["runtime_latency_s", "context_pressure_ratio"],
            height=240,
        )
    with trend_chart_col_2:
        st.caption("Erro, revisão humana e MCP")
        render_bar_chart_from_rows(
            trend_rows,
            index_field="window",
            value_fields=["runtime_error_rate", "runtime_needs_review_rate", "mcp_error_rate"],
            height=240,
        )

    render_panel_header(
        "Sinais executivos prioritários",
        "Leitura condensada do que mais importa agora: qualidade, falhas, revisão humana e pressão operacional.",
    )
    render_bar_chart_from_rows(
        _build_exec_scan_rows(
            phase8_eval_summary=phase8_eval_summary,
            runtime_execution_summary=runtime_execution_summary,
            phase6_document_agent_log_summary=phase6_document_agent_log_summary,
        ),
        index_field="signal",
        value_fields=["current"],
        height=220,
    )

    if alerts:
        render_panel_header("Alertas operacionais atuais")
        render_message_list(alerts)

    st.markdown("### Triage operacional")
    triage_cards = [
        {
            "title": "Qualidade & regressões",
            "summary": f"PASS={_format_rate(phase8_eval_summary.get('pass_rate'))} · FAIL={_format_rate(phase8_eval_summary.get('fail_rate'))}",
            "details": [
                f"needs_review recente: {_format_rate(runtime_execution_summary.get('needs_review_rate'))}",
                f"última eval: {_format_timestamp(phase8_eval_summary.get('latest_created_at'))}",
            ],
            "action": "Abrir `Evals & Diagnóstico` para investigar regressões e quality gates.",
        },
        {
            "title": "Latência & custo",
            "summary": f"avg_latency={float(runtime_execution_summary.get('avg_latency_s') or 0.0):.2f}s · avg_tokens={float(runtime_execution_summary.get('avg_total_tokens') or 0.0):.0f}",
            "details": [
                f"context pressure: {float(runtime_execution_summary.get('avg_context_pressure_ratio') or 0.0):.2f}",
                f"avg_cost: {'$' + format(float(runtime_execution_summary.get('avg_cost_usd') or 0.0), '.6f') if int(runtime_execution_summary.get('costed_runs') or 0) > 0 else 'n/a'}",
            ],
            "action": "Abrir `Runtime & Observabilidade` para analisar gargalos e budget routing.",
        },
        {
            "title": "Workflow & guardrails",
            "summary": f"doc-agent={doc_agent_runs} run(s) · needs_review={_format_rate(phase6_document_agent_log_summary.get('needs_review_rate'))}",
            "details": [
                f"tool errors: {int(phase6_document_agent_log_summary.get('runs_with_tool_errors') or 0)}",
                f"último doc-agent: {_format_timestamp(phase6_document_agent_log_summary.get('latest_timestamp'))}",
            ],
            "action": "Abrir `Inspector de Workflow & Structured` para revisar routing, guardrails e revisão humana.",
        },
        {
            "title": "Document intelligence",
            "summary": f"docs={indexed_documents_count} · backend={vector_backend_status_preview.get('backend') or 'n/a'}",
            "details": [
                f"status do índice: {vector_backend_status_preview.get('status') or 'n/a'}",
                f"evidence pipeline runs: {int(runtime_execution_summary.get('evidence_pipeline_runs') or 0)}",
            ],
            "action": "Abrir `Runtime & Observabilidade` para validar corpus, índice e pipeline documental.",
        },
        {
            "title": "MCP & operações",
            "summary": f"mcp_runs={int(runtime_execution_summary.get('mcp_runs') or 0)} · mcp_error={_format_rate(runtime_execution_summary.get('mcp_error_rate'))}",
            "details": [
                f"tool calls: {int(runtime_execution_summary.get('total_mcp_tool_calls') or 0)}",
                f"avg mcp latency: {float(runtime_execution_summary.get('avg_mcp_total_latency_s') or 0.0):.2f}s",
            ],
            "action": "Abrir `EvidenceOps / MCP` para revisar o console operacional e readiness das integrações.",
        },
        {
            "title": "Benchmark & decisões",
            "summary": f"benchmark_runs={benchmark_runs} · último benchmark={_format_timestamp(phase7_model_comparison_log_summary.get('latest_timestamp'))}",
            "details": [
                f"top provider agregado: {((phase7_model_comparison_log_summary.get('top_provider') or {}).get('provider') if isinstance(phase7_model_comparison_log_summary.get('top_provider'), dict) else 'n/a')}",
                f"top use case agregado: {((phase7_model_comparison_log_summary.get('top_benchmark_use_case') or {}).get('benchmark_use_case') if isinstance(phase7_model_comparison_log_summary.get('top_benchmark_use_case'), dict) else 'n/a')}",
            ],
            "action": "Abrir `Benchmarks & Comparação de Modelos` para definir defaults e alternativas por caso de uso.",
        },
    ]
    triage_cols = st.columns(3)
    for index, card in enumerate(triage_cards):
        with triage_cols[index % 3]:
            with st.container(border=True):
                st.write(f"**{card['title']}**")
                st.caption(card["summary"])
                for detail in card["details"]:
                    st.caption(detail)
                st.markdown(f"- {card['action']}")

    render_panel_header("Próximas ações recomendadas agora")
    next_actions = _build_next_actions(
        indexed_documents_count=indexed_documents_count,
        runtime_runs=runtime_runs,
        benchmark_runs=benchmark_runs,
        eval_runs=eval_runs,
        alerts=alerts,
    )
    action_cols = st.columns(min(2, len(next_actions))) if next_actions else []
    for index, action in enumerate(next_actions):
        with action_cols[index % len(action_cols)]:
            with st.container(border=True):
                st.caption(f"Ação {index + 1}")
                st.write(action)

    if indexed_documents_count == 0 or runtime_runs == 0:
        with st.container(border=True):
            st.markdown("#### Bootstrap rápido do AI Lab")
            st.caption("Quando o ambiente está vazio ou recém-subido, siga esta ordem para sair do zero com evidência operacional real.")
            st.markdown(
                "\n".join(
                    [
                        "1. Abra `Runtime & Observabilidade` e carregue o primeiro documento ou corpus de teste.",
                        "2. Gere a primeira execução em `Experimentos de Chat e Documentos` ou `Inspector de Workflow & Structured`.",
                        "3. Rode uma comparação em `Benchmarks & Comparação de Modelos`.",
                        "4. Use `Evals & Diagnóstico` para começar a leitura persistida de qualidade.",
                    ]
                )
            )

    with st.expander("Leitura oficial do AI Lab", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(
                {
                    "Missão": "Desenvolver, inspecionar, validar, comparar, auditar e operar o sistema.",
                    "Linguagem dominante": "Benchmark, evals, observabilidade, tracing, MCP, runtime economics, OCR/VLM e experimentação controlada.",
                    "Público-alvo": "builder, operador técnico e mantenedor do sistema.",
                }
            )
        with col_b:
            st.write(
                {
                    "Não é homepage de produto": "hero flows de produto e CTA de workflow de negócio ficam fora do Streamlit.",
                    "Produto oficial": "Gradio como superfície de Decision workflows grounded in documents.",
                    "Backend compartilhado": "ingestão documental, structured outputs, document agent, EvidenceOps e deck generation.",
                }
            )

    with st.expander("Decision gate final do split", expanded=False):
        st.success(
            "Decisão atual: o Streamlit adaptado continua suficiente como AI Lab dashboard. Não há necessidade de abrir um novo app Streamlit dedicado nesta fase."
        )
        st.write(
            {
                "Leitura dominante do AI Lab": "benchmark, evals, runtime & observability, workflow inspector, MCP/EvidenceOps e experimentação avançada.",
                "Leitura dominante do produto": "Decision workflows grounded in documents seguem concentrados na superfície em Gradio.",
                "Quando reconsiderar": "Somente se o laboratório ganhar novas superfícies independentes, nova navegação própria ou volume de operação que justifique outro app dedicado.",
            }
        )

    with st.expander("Mapa oficial de navegação", expanded=False):
        st.write({item["title"]: item["description"] for item in AI_LAB_TAB_SPECS})

    with st.expander("Trilhas de engenharia já refletidas na UI", expanded=False):
        st.write(
            {
                "Benchmark e comparação": "model comparison, strategy benchmarks e leaderboard local.",
                "Qualidade": "eval store, diagnóstico e quality gates.",
                "Runtime": "latência, budget-aware routing, compatibilidade vetorial e execution history.",
                "Inspeção de workflow": "structured execution, direct vs LangGraph, document agent e needs_review.",
                "Operações": "EvidenceOps MCP, worklog, action store e export executivo do AI Lab.",
            }
        )