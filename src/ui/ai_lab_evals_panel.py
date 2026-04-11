from __future__ import annotations

from typing import Any

import streamlit as st

from src.storage.phase8_eval_diagnosis import build_eval_diagnosis

from .ai_lab_common import (
    build_selectbox_options,
    compact_rows,
    humanize_eval_recommendation,
    humanize_identifier,
    humanize_priority,
    humanize_reason_text,
    humanize_suite_name,
    humanize_task_type,
    render_bar_chart_from_rows,
    render_line_chart_from_rows,
    render_labeled_value_grid,
    render_message_list,
    render_panel_header,
    render_status_badges,
)


def _format_timestamp(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"
    return text.replace("T", " ")[:19]


def _format_rate(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.0%}"
    return "n/a"


def _humanize_recommendation(value: object) -> str:
    return humanize_eval_recommendation(value)


def _humanize_priority(value: object) -> str:
    return humanize_priority(value)


def _humanize_task(value: object) -> str:
    return humanize_task_type(value)


def _humanize_suite(value: object) -> str:
    return humanize_suite_name(value)


def _humanize_reason(value: object) -> str:
    return humanize_reason_text(value)


def _humanize_case_name(value: object) -> str:
    return humanize_identifier(value)


def _quality_gate_label(phase8_eval_summary: dict[str, Any]) -> str:
    fail_rate = float(phase8_eval_summary.get("fail_rate") or 0.0)
    needs_review_rate = float(phase8_eval_summary.get("needs_review_rate") or 0.0)
    pass_rate = float(phase8_eval_summary.get("pass_rate") or 0.0)
    if fail_rate > 0.10 or needs_review_rate > 0.15:
        return "🔴 Crítico"
    if fail_rate > 0.0 or needs_review_rate > 0.10 or pass_rate < 0.80:
        return "🟡 Atenção"
    return "🟢 Saudável"


def _build_eval_window_summary(entries: list[dict[str, Any]]) -> dict[str, float | int]:
    total_runs = len(entries)
    if total_runs == 0:
        return {
            "total_runs": 0,
            "pass_rate": 0.0,
            "warn_rate": 0.0,
            "fail_rate": 0.0,
            "needs_review_rate": 0.0,
            "avg_latency_s": 0.0,
        }

    pass_count = 0
    warn_count = 0
    fail_count = 0
    needs_review_count = 0
    latencies: list[float] = []
    for entry in entries:
        status = str(entry.get("status") or "").upper()
        if status == "PASS":
            pass_count += 1
        elif status == "WARN":
            warn_count += 1
        elif status == "FAIL":
            fail_count += 1
        if bool(entry.get("needs_review")):
            needs_review_count += 1
        latency_value = entry.get("latency_s")
        if isinstance(latency_value, (int, float)):
            latencies.append(float(latency_value))

    return {
        "total_runs": total_runs,
        "pass_rate": pass_count / total_runs,
        "warn_rate": warn_count / total_runs,
        "fail_rate": fail_count / total_runs,
        "needs_review_rate": needs_review_count / total_runs,
        "avg_latency_s": (sum(latencies) / len(latencies)) if latencies else 0.0,
    }


def _build_eval_trend_windows(
    entries: list[dict[str, Any]],
    *,
    window_size: int = 10,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_entries = sorted(
        [entry for entry in entries if isinstance(entry, dict)],
        key=lambda entry: str(entry.get("created_at") or ""),
        reverse=True,
    )
    recent_window = ordered_entries[:window_size]
    previous_window = ordered_entries[window_size : window_size * 2]
    return recent_window, previous_window


def _build_eval_trend_chart_rows(
    *,
    recent_window_summary: dict[str, float | int],
    previous_window_summary: dict[str, float | int],
) -> list[dict[str, float | str]]:
    return [
        {
            "window": "previous",
            "pass_rate": float(previous_window_summary.get("pass_rate") or 0.0),
            "fail_rate": float(previous_window_summary.get("fail_rate") or 0.0),
            "needs_review_rate": float(previous_window_summary.get("needs_review_rate") or 0.0),
            "avg_latency_s": float(previous_window_summary.get("avg_latency_s") or 0.0),
        },
        {
            "window": "recent",
            "pass_rate": float(recent_window_summary.get("pass_rate") or 0.0),
            "fail_rate": float(recent_window_summary.get("fail_rate") or 0.0),
            "needs_review_rate": float(recent_window_summary.get("needs_review_rate") or 0.0),
            "avg_latency_s": float(recent_window_summary.get("avg_latency_s") or 0.0),
        },
    ]


def _build_quality_signal_rows(phase8_eval_summary: dict[str, Any]) -> list[dict[str, float | str]]:
    return [
        {"signal": "PASS", "value": float(phase8_eval_summary.get("pass_rate") or 0.0)},
        {"signal": "WARN", "value": float(phase8_eval_summary.get("warn_rate") or 0.0)},
        {"signal": "FAIL", "value": float(phase8_eval_summary.get("fail_rate") or 0.0)},
        {"signal": "Needs review", "value": float(phase8_eval_summary.get("needs_review_rate") or 0.0)},
    ]


def _classify_regression_severity(item: dict[str, Any]) -> tuple[str, str]:
    fail_rate = float(item.get("fail_rate") or 0.0)
    recent_fail_rate = float(item.get("recent_fail_rate") or 0.0)
    priority = str(item.get("adaptation_priority") or "").strip().lower()
    if recent_fail_rate >= 0.5 or fail_rate >= 0.5 or priority == "high":
        return "Crítica", "critical"
    if recent_fail_rate >= 0.2 or fail_rate >= 0.2 or priority == "medium":
        return "Alta atenção", "attention"
    return "Monitorar", "info"


def render_evals_diagnosis_panel(
    *,
    phase8_eval_entries: list[dict[str, Any]],
    phase8_eval_summary: dict[str, Any],
) -> None:
    if not phase8_eval_entries:
        st.info("Nenhuma run de eval registrada ainda. Use os scripts/suites da Fase 8 para alimentar esta visão diagnóstica.")
        return

    diagnosis = build_eval_diagnosis(phase8_eval_entries)
    decision_summary = diagnosis.get("decision_summary") if isinstance(diagnosis.get("decision_summary"), dict) else {}
    top_failure_reasons = diagnosis.get("top_failure_reasons") if isinstance(diagnosis.get("top_failure_reasons"), list) else []
    persistent_failure_tasks = diagnosis.get("persistent_failure_tasks") if isinstance(diagnosis.get("persistent_failure_tasks"), list) else []
    adaptation_candidates = diagnosis.get("adaptation_candidates") if isinstance(diagnosis.get("adaptation_candidates"), list) else []
    healthy_tasks = diagnosis.get("healthy_tasks") if isinstance(diagnosis.get("healthy_tasks"), list) else []
    next_eval_priorities = decision_summary.get("next_eval_priorities") if isinstance(decision_summary.get("next_eval_priorities"), list) else []
    iteration_before_adaptation_tasks = decision_summary.get("iteration_before_adaptation_tasks") if isinstance(decision_summary.get("iteration_before_adaptation_tasks"), list) else []
    global_recommendation = _humanize_recommendation(decision_summary.get("global_recommendation"))

    eval_metric_col_1, eval_metric_col_2, eval_metric_col_3, eval_metric_col_4 = st.columns(4)
    eval_metric_col_1.metric("Eval runs", int(phase8_eval_summary.get("total_runs") or 0))
    eval_metric_col_2.metric("PASS", f"{float(phase8_eval_summary.get('pass_rate') or 0.0):.0%}")
    eval_metric_col_3.metric("WARN", f"{float(phase8_eval_summary.get('warn_rate') or 0.0):.0%}")
    eval_metric_col_4.metric("FAIL", f"{float(phase8_eval_summary.get('fail_rate') or 0.0):.0%}")

    eval_metric_col_5, eval_metric_col_6, eval_metric_col_7 = st.columns(3)
    eval_metric_col_5.metric("Needs review", f"{float(phase8_eval_summary.get('needs_review_rate') or 0.0):.0%}")
    eval_metric_col_6.metric("Avg score ratio", f"{float(phase8_eval_summary.get('avg_score_ratio') or 0.0):.0%}")
    eval_metric_col_7.metric("Avg latency", f"{float(phase8_eval_summary.get('avg_latency_s') or 0.0):.2f}s")
    st.caption(f"Última eval registrada: {_format_timestamp(phase8_eval_summary.get('latest_created_at'))}")

    render_panel_header(
        "Resumo do gate de qualidade",
        "Leitura de topo da disciplina de qualidade: status global, tasks em regressão e onde priorizar a próxima intervenção de engenharia.",
    )
    render_labeled_value_grid(
        [
            {"label": "Quality gate", "value": _quality_gate_label(phase8_eval_summary)},
            {"label": "Tasks críticas", "value": len(persistent_failure_tasks)},
            {"label": "Adaptation candidates", "value": len(adaptation_candidates)},
            {"label": "Tasks saudáveis", "value": len(healthy_tasks)},
            {"label": "Top failure reasons", "value": len(top_failure_reasons)},
        ],
        columns=5,
    )
    if global_recommendation:
        st.info(global_recommendation)
    st.caption("Comfort zones de referência: PASS >= 80% · FAIL = 0% · needs_review < 10% · recent regressions devem ser tratadas antes de expandir o escopo experimental.")
    render_status_badges(
        [
            (f"PASS {_format_rate(phase8_eval_summary.get('pass_rate'))}", "healthy" if float(phase8_eval_summary.get("pass_rate") or 0.0) >= 0.8 else "attention"),
            (f"FAIL {_format_rate(phase8_eval_summary.get('fail_rate'))}", "critical" if float(phase8_eval_summary.get("fail_rate") or 0.0) > 0.0 else "healthy"),
            (f"needs_review {_format_rate(phase8_eval_summary.get('needs_review_rate'))}", "attention" if float(phase8_eval_summary.get("needs_review_rate") or 0.0) > 0.1 else "healthy"),
            (f"avg latency {float(phase8_eval_summary.get('avg_latency_s') or 0.0):.2f}s", "info"),
        ]
    )
    if persistent_failure_tasks:
        render_panel_header(
            "Triage visual de regressões",
            "Cards para decidir rapidamente quais tasks merecem intervenção imediata antes do drilldown tabular.",
        )
        triage_cards = persistent_failure_tasks[:4]
        triage_cols = st.columns(min(4, len(triage_cards)))
        for index, item in enumerate(triage_cards):
            severity_label, severity_tone = _classify_regression_severity(item if isinstance(item, dict) else {})
            with triage_cols[index % len(triage_cols)]:
                with st.container(border=True):
                    st.caption(_humanize_task(item.get("task_type") or "task"))
                    render_status_badges([(severity_label, severity_tone)])
                    st.metric("Fail rate", _format_rate(item.get("fail_rate")))
                    st.metric("Recent fail", _format_rate(item.get("recent_fail_rate")))
                    st.caption(f"Avg score ratio: {_format_rate(item.get('avg_score_ratio'))}")
                    st.caption(_humanize_recommendation(item.get("recommended_action")))
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        render_bar_chart_from_rows(
            _build_quality_signal_rows(phase8_eval_summary),
            index_field="signal",
            value_fields=["value"],
            height=220,
        )
    with chart_col_2:
        if top_failure_reasons:
            render_bar_chart_from_rows(
                [
                    {"reason": _humanize_reason(item.get("reason") or "unknown"), "count": int(item.get("count") or 0)}
                    for item in top_failure_reasons[:8]
                ],
                index_field="reason",
                value_fields=["count"],
                height=220,
            )

    if top_failure_reasons:
        with st.expander("Top failure reasons", expanded=False):
            st.dataframe(
                compact_rows(
                    [
                        {**item, "reason": _humanize_reason(item.get("reason"))}
                        for item in top_failure_reasons[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"reason": 64},
                ),
                width="stretch",
            )

    recent_window, previous_window = _build_eval_trend_windows(phase8_eval_entries)
    recent_window_summary = _build_eval_window_summary(recent_window)
    previous_window_summary = _build_eval_window_summary(previous_window)
    if int(recent_window_summary.get("total_runs") or 0) > 0:
        render_panel_header(
            "Snapshot de tendência",
            "Compare a janela recente de evals com a imediatamente anterior para detectar regressões operacionais cedo.",
        )
        trend_chart_col_1, trend_chart_col_2 = st.columns(2)
        trend_chart_rows = _build_eval_trend_chart_rows(
            recent_window_summary=recent_window_summary,
            previous_window_summary=previous_window_summary,
        )
        with trend_chart_col_1:
            render_line_chart_from_rows(
                trend_chart_rows,
                index_field="window",
                value_fields=["pass_rate", "fail_rate", "needs_review_rate"],
                height=230,
            )
        with trend_chart_col_2:
            render_bar_chart_from_rows(
                trend_chart_rows,
                index_field="window",
                value_fields=["avg_latency_s"],
                height=230,
            )
        trend_col_1, trend_col_2, trend_col_3, trend_col_4 = st.columns(4)
        trend_col_1.metric("Recent cases", int(recent_window_summary.get("total_runs") or 0))
        pass_delta = (
            float(recent_window_summary.get("pass_rate") or 0.0) - float(previous_window_summary.get("pass_rate") or 0.0)
            if int(previous_window_summary.get("total_runs") or 0) > 0
            else None
        )
        fail_delta = (
            float(recent_window_summary.get("fail_rate") or 0.0) - float(previous_window_summary.get("fail_rate") or 0.0)
            if int(previous_window_summary.get("total_runs") or 0) > 0
            else None
        )
        latency_delta = (
            float(recent_window_summary.get("avg_latency_s") or 0.0) - float(previous_window_summary.get("avg_latency_s") or 0.0)
            if int(previous_window_summary.get("total_runs") or 0) > 0
            else None
        )
        trend_col_2.metric(
            "Recent PASS",
            f"{float(recent_window_summary.get('pass_rate') or 0.0):.0%}",
            delta=(f"{pass_delta * 100:+.0f} pp" if pass_delta is not None else None),
        )
        trend_col_3.metric(
            "Recent FAIL",
            f"{float(recent_window_summary.get('fail_rate') or 0.0):.0%}",
            delta=(f"{fail_delta * 100:+.0f} pp" if fail_delta is not None else None),
        )
        with trend_col_4:
            render_labeled_value_grid(
                [
                    {
                        "label": "Recent latency",
                        "value": f"{float(recent_window_summary.get('avg_latency_s') or 0.0):.2f}s",
                        "detail": f"Δ {latency_delta:+.2f}s" if latency_delta is not None else "sem delta anterior",
                    }
                ],
                columns=1,
            )

        trend_watchouts: list[str] = []
        if pass_delta is not None and pass_delta < -0.05:
            trend_watchouts.append("A taxa de PASS caiu na janela mais recente em relação à janela anterior.")
        if fail_delta is not None and fail_delta > 0.05:
            trend_watchouts.append("A taxa de FAIL subiu na janela mais recente; vale investigar regressões ou mudanças de ambiente.")
        recent_needs_review = float(recent_window_summary.get("needs_review_rate") or 0.0)
        previous_needs_review = float(previous_window_summary.get("needs_review_rate") or 0.0)
        if int(previous_window_summary.get("total_runs") or 0) > 0 and recent_needs_review > previous_needs_review + 0.05:
            trend_watchouts.append("A taxa de `needs_review` piorou na janela recente, sinalizando instabilidade operacional.")
        if latency_delta is not None and latency_delta > 5.0:
            trend_watchouts.append("A latência média da janela mais recente aumentou perceptivelmente.")

        if trend_watchouts:
            render_message_list(trend_watchouts)
        elif int(previous_window_summary.get("total_runs") or 0) > 0:
            st.success("Não há regressões fortes na janela mais recente de evals em relação à anterior.")

    suite_leaderboard = phase8_eval_summary.get("suite_leaderboard") if isinstance(phase8_eval_summary.get("suite_leaderboard"), list) else []
    task_leaderboard = phase8_eval_summary.get("task_leaderboard") if isinstance(phase8_eval_summary.get("task_leaderboard"), list) else []

    eval_watchouts: list[str] = []
    if float(phase8_eval_summary.get("fail_rate") or 0.0) > 0.0:
        eval_watchouts.append("Existem casos FAIL recentes; a camada de eval já aponta gaps reais do sistema e deve orientar a próxima rodada de melhoria.")
    if float(phase8_eval_summary.get("needs_review_rate") or 0.0) > 0.1:
        eval_watchouts.append("A taxa de `needs_review` nas evals está acima do conforto operacional; vale investigar tasks com baixa estabilidade.")
    if persistent_failure_tasks:
        eval_watchouts.append("Há tasks com falha persistente; trate essas regressões antes de abrir novas frentes experimentais.")
    if eval_watchouts:
        render_panel_header("Leitura operacional")
        render_message_list(eval_watchouts)

    leaderboard_tab, investigation_tab, recommendation_tab = st.tabs(
        ["Cobertura", "Controle de regressão", "Saudáveis / próximos passos"]
    )
    with leaderboard_tab:
        if suite_leaderboard:
            st.markdown("### Suite leaderboard")
            render_bar_chart_from_rows(
                [
                    {
                        "suite_name": _humanize_suite(item.get("suite_name") or "unknown"),
                        "pass_rate": float(item.get("pass_rate") or 0.0),
                        "fail_rate": float(item.get("fail_rate") or 0.0),
                    }
                    for item in suite_leaderboard[:10]
                ],
                index_field="suite_name",
                value_fields=["pass_rate", "fail_rate"],
                height=240,
            )
            st.dataframe(
                compact_rows(
                    [
                        {**item, "suite_name": _humanize_suite(item.get("suite_name"))}
                        for item in suite_leaderboard[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"suite_name": 42},
                ),
                width="stretch",
            )
        if task_leaderboard:
            st.markdown("### Task leaderboard")
            render_bar_chart_from_rows(
                [
                    {
                        "task_type": _humanize_task(item.get("task_type") or "unknown"),
                        "pass_rate": float(item.get("pass_rate") or 0.0),
                        "fail_rate": float(item.get("fail_rate") or 0.0),
                    }
                    for item in task_leaderboard[:10]
                ],
                index_field="task_type",
                value_fields=["pass_rate", "fail_rate"],
                height=240,
            )
            st.dataframe(
                compact_rows(
                    [
                        {**item, "task_type": _humanize_task(item.get("task_type"))}
                        for item in task_leaderboard[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"task_type": 42},
                ),
                width="stretch",
            )
        if not suite_leaderboard and not task_leaderboard:
            st.caption("Ainda não há cobertura suficiente para montar leaderboards agregados nesta superfície.")

    with investigation_tab:
        if persistent_failure_tasks:
            st.markdown("### Tasks para investigar primeiro")
            st.dataframe(
                compact_rows(
                    [
                        {
                            "task_type": _humanize_task(item.get("task_type")),
                            "fail_rate": _format_rate(item.get("fail_rate")),
                            "recent_fail_rate": _format_rate(item.get("recent_fail_rate")),
                            "avg_score_ratio": _format_rate(item.get("avg_score_ratio")),
                            "adaptation_priority": _humanize_priority(item.get("adaptation_priority")),
                            "recommended_action": _humanize_recommendation(item.get("recommended_action")),
                        }
                        for item in persistent_failure_tasks[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"task_type": 36, "recommended_action": 76},
                ),
                width="stretch",
            )
        else:
            st.success("Nenhuma task crítica apareceu como prioridade imediata nesta leitura agregada.")

        if next_eval_priorities:
            st.markdown("### O que mudou e o que reavaliar agora")
            st.dataframe(
                compact_rows(
                    [
                        {
                            "task_type": _humanize_task(item.get("task_type")),
                            "fail_rate": _format_rate(item.get("fail_rate")),
                            "recent_fail_rate": _format_rate(item.get("recent_fail_rate")),
                            "recommended_action": _humanize_recommendation(item.get("recommended_action")),
                        }
                        for item in next_eval_priorities[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"task_type": 36, "recommended_action": 76},
                ),
                width="stretch",
            )

    with recommendation_tab:
        if healthy_tasks:
            st.markdown("### Tasks saudáveis no momento")
            st.dataframe(
                compact_rows(
                    [
                        {
                            "task_type": _humanize_task(item.get("task_type")),
                            "pass_rate": _format_rate(item.get("pass_rate")),
                            "avg_score_ratio": _format_rate(item.get("avg_score_ratio")),
                            "recommended_action": _humanize_recommendation(item.get("recommended_action")),
                        }
                        for item in healthy_tasks[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"task_type": 36, "recommended_action": 76},
                ),
                width="stretch",
            )
        if iteration_before_adaptation_tasks:
            st.markdown("### Iterar antes de pensar em adaptação")
            st.dataframe(
                compact_rows(
                    [
                        {
                            "task_type": _humanize_task(item.get("task_type")),
                            "fail_rate": _format_rate(item.get("fail_rate")),
                            "avg_score_ratio": _format_rate(item.get("avg_score_ratio")),
                            "recommended_action": _humanize_recommendation(item.get("recommended_action")),
                        }
                        for item in iteration_before_adaptation_tasks[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"task_type": 36, "recommended_action": 76},
                ),
                width="stretch",
            )
        if adaptation_candidates:
            st.markdown("### Candidatas a adaptação futura")
            st.dataframe(
                compact_rows(
                    [
                        {
                            "task_type": _humanize_task(item.get("task_type")),
                            "priority": _humanize_priority(item.get("adaptation_priority")),
                            "fail_rate": _format_rate(item.get("fail_rate")),
                            "avg_score_ratio": _format_rate(item.get("avg_score_ratio")),
                            "recommended_action": _humanize_recommendation(item.get("recommended_action")),
                        }
                        for item in adaptation_candidates[:10]
                        if isinstance(item, dict)
                    ],
                    field_limits={"task_type": 36, "recommended_action": 76},
                ),
                width="stretch",
            )
        if not healthy_tasks and not iteration_before_adaptation_tasks and not adaptation_candidates:
            st.caption("Ainda não há recomendações ou tarefas claramente saudáveis suficientes para esta leitura resumida.")

    filter_col_1, filter_col_2, filter_col_3 = st.columns(3)
    suite_options = {"all": "all", **build_selectbox_options(sorted({str(entry.get('suite_name') or '') for entry in phase8_eval_entries if entry.get('suite_name')}), max_chars=54, formatter=_humanize_suite)}
    suite_filter_label = filter_col_1.selectbox(
        "Filtrar por suite",
        options=list(suite_options.keys()),
        key="phase8_eval_suite_filter",
    )
    suite_filter = suite_options[suite_filter_label]
    task_options = {"all": "all", **build_selectbox_options(sorted({str(entry.get('task_type') or '') for entry in phase8_eval_entries if entry.get('task_type')}), max_chars=54, formatter=_humanize_task)}
    task_filter_label = filter_col_2.selectbox(
        "Filtrar por task",
        options=list(task_options.keys()),
        key="phase8_eval_task_filter",
    )
    task_filter = task_options[task_filter_label]
    status_filter = filter_col_3.selectbox(
        "Filtrar por status",
        options=["all", "FAIL", "WARN", "PASS"],
        key="phase8_eval_status_filter",
    )

    recent_eval_rows = [
        {
            "created_at": entry.get("created_at"),
            "suite_name": _humanize_suite(entry.get("suite_name")),
            "task_type": _humanize_task(entry.get("task_type")),
            "case_name": _humanize_case_name(entry.get("case_name")),
            "status": entry.get("status"),
            "score": entry.get("score"),
            "max_score": entry.get("max_score"),
            "needs_review": entry.get("needs_review"),
            "latency_s": entry.get("latency_s"),
        }
        for entry in phase8_eval_entries
        if (suite_filter == "all" or str(entry.get("suite_name") or "") == suite_filter)
        and (task_filter == "all" or str(entry.get("task_type") or "") == task_filter)
        and (status_filter == "all" or str(entry.get("status") or "") == status_filter)
    ]
    if recent_eval_rows:
        render_panel_header("Casos recentes de eval", f"{len(recent_eval_rows)} caso(s) após os filtros ativos.")
        st.dataframe(
            compact_rows(
                recent_eval_rows[:30],
                field_limits={"suite_name": 36, "task_type": 36, "case_name": 64},
            ),
            width="stretch",
        )