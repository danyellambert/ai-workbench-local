from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import streamlit as st

from .ai_lab_common import (
    compact_rows,
    render_bar_chart_from_rows,
    render_heatmap_from_rows,
    render_labeled_value_grid,
    render_message_list,
    render_panel_header,
    render_scatter_chart_from_rows,
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


def _pick_fastest_viable(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    viable_rows = [row for row in rows if float(row.get("success_rate") or 0.0) >= 0.8]
    if not viable_rows:
        return None
    return min(viable_rows, key=lambda row: float(row.get("avg_latency_s") or 10**9))


def _pick_best_quality(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            float(row.get("success_rate") or 0.0),
            float(row.get("avg_format_adherence") or 0.0),
            float(row.get("avg_use_case_fit_score") or 0.0),
            -float(row.get("avg_latency_s") or 10**9),
        ),
    )


def _candidate_label(candidate: dict[str, Any]) -> str:
    provider = str(candidate.get("provider_label") or candidate.get("provider_effective") or candidate.get("provider") or "provider")
    model = str(candidate.get("model_effective") or candidate.get("model_requested") or candidate.get("model") or "model")
    return f"{provider} · {model}"


def _truncate_response_preview(value: object, *, max_chars: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _flatten_model_comparison_candidates(
    entries: list[dict[str, Any]],
    *,
    runtime_bucket_labels: dict[str, str],
    quantization_labels: dict[str, str],
    use_case_presets: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in reversed(entries):
        use_case_key = str(entry.get("benchmark_use_case") or "ad_hoc")
        use_case_label = use_case_presets.get(use_case_key, {}).get("label", use_case_key)
        for candidate in entry.get("candidate_results") or []:
            if not isinstance(candidate, dict):
                continue
            runtime_bucket = str(candidate.get("runtime_bucket") or "")
            quantization_family = str(candidate.get("quantization_family") or "")
            rows.append(
                {
                    "timestamp": entry.get("timestamp"),
                    "use_case": use_case_label,
                    "prompt_profile": entry.get("prompt_profile"),
                    "response_format": entry.get("response_format"),
                    "provider": candidate.get("provider_effective") or candidate.get("provider_requested"),
                    "model": candidate.get("model_effective") or candidate.get("model_requested"),
                    "runtime_bucket": runtime_bucket_labels.get(runtime_bucket, runtime_bucket or "runtime"),
                    "quantization": quantization_labels.get(quantization_family, quantization_family or "quantization"),
                    "success": candidate.get("success"),
                    "latency_s": candidate.get("latency_s"),
                    "format_adherence": candidate.get("format_adherence"),
                    "groundedness": candidate.get("groundedness_score"),
                    "schema_adherence": candidate.get("schema_adherence"),
                    "use_case_fit": candidate.get("use_case_fit_score"),
                    "used_chunks": candidate.get("used_chunks"),
                }
            )
    return rows


def _build_candidate_execution_rows(candidate_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidate_results:
        if not isinstance(candidate, dict):
            continue
        rows.append(
            {
                "candidate": _candidate_label(candidate),
                "latency_s": float(candidate.get("latency_s") or 0.0),
                "format_adherence": float(candidate.get("format_adherence") or 0.0),
                "groundedness": float(candidate.get("groundedness_score") or 0.0),
                "schema_adherence": float(candidate.get("schema_adherence") or 0.0),
                "use_case_fit": float(candidate.get("use_case_fit_score") or 0.0),
            }
        )
    return rows


def _build_badges_for_benchmark_summary(summary: dict[str, Any]) -> list[tuple[str, str]]:
    success_rate = float(summary.get("success_rate") or 0.0)
    avg_latency = float(summary.get("avg_latency_s") or 0.0)
    avg_fit = float(summary.get("avg_use_case_fit_score") or 0.0)
    return [
        (f"success {success_rate:.0%}", "healthy" if success_rate >= 0.8 else "attention"),
        (f"latency {avg_latency:.2f}s", "attention" if avg_latency > 20.0 else "healthy"),
        (f"use-case-fit {avg_fit:.0%}", "healthy" if avg_fit >= 0.8 else "attention"),
    ]


def render_model_comparison_history_panel(
    *,
    phase7_model_comparison_log_path: Path,
    phase7_model_comparison_log_summary: dict[str, Any],
    phase7_model_comparison_log_entries: list[dict[str, Any]],
    runtime_bucket_labels: dict[str, str],
    quantization_labels: dict[str, str],
    use_case_presets: dict[str, dict[str, str]],
) -> bool:
    clear_requested = False
    with st.expander("Fase 7 · histórico local de comparação entre modelos", expanded=False):
        st.caption(f"Log local: `{phase7_model_comparison_log_path.name}`")
        if phase7_model_comparison_log_summary.get("total_candidates"):
            summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
            summary_col_1.metric("Runs", int(phase7_model_comparison_log_summary.get("total_runs") or 0))
            summary_col_2.metric("Candidatos", int(phase7_model_comparison_log_summary.get("total_candidates") or 0))
            summary_col_3.metric("Sucesso médio", f"{float(phase7_model_comparison_log_summary.get('success_rate', 0.0)):.0%}")
            summary_col_4.metric("Latência média", f"{float(phase7_model_comparison_log_summary.get('avg_latency_s', 0.0)):.2f}s")
            st.caption(
                f"Último benchmark registrado: {_format_timestamp(phase7_model_comparison_log_summary.get('latest_timestamp'))}"
            )

            top_provider = phase7_model_comparison_log_summary.get("top_provider") if isinstance(phase7_model_comparison_log_summary.get("top_provider"), dict) else None
            top_model = phase7_model_comparison_log_summary.get("top_model") if isinstance(phase7_model_comparison_log_summary.get("top_model"), dict) else None
            top_format = phase7_model_comparison_log_summary.get("top_format") if isinstance(phase7_model_comparison_log_summary.get("top_format"), dict) else None
            top_runtime_bucket = phase7_model_comparison_log_summary.get("top_runtime_bucket") if isinstance(phase7_model_comparison_log_summary.get("top_runtime_bucket"), dict) else None
            top_quantization_family = phase7_model_comparison_log_summary.get("top_quantization_family") if isinstance(phase7_model_comparison_log_summary.get("top_quantization_family"), dict) else None
            top_benchmark_use_case = phase7_model_comparison_log_summary.get("top_benchmark_use_case") if isinstance(phase7_model_comparison_log_summary.get("top_benchmark_use_case"), dict) else None

            if top_provider:
                st.caption(
                    f"Top provider agregado: {top_provider.get('provider')} · success={float(top_provider.get('success_rate', 0.0)):.0%} · latency={float(top_provider.get('avg_latency_s', 0.0)):.2f}s"
                )
            if top_model:
                st.caption(
                    f"Top model agregado: {top_model.get('model')} · success={float(top_model.get('success_rate', 0.0)):.0%} · adherence={float(top_model.get('avg_format_adherence', 0.0)):.0%}"
                )
            if top_format:
                st.caption(
                    f"Top formato agregado: {top_format.get('response_format')} · success={float(top_format.get('success_rate', 0.0)):.0%}"
                )
            if top_runtime_bucket:
                runtime_bucket_label = runtime_bucket_labels.get(
                    str(top_runtime_bucket.get("runtime_bucket") or ""),
                    str(top_runtime_bucket.get("runtime_bucket") or "runtime"),
                )
                st.caption(
                    f"Top bucket de runtime: {runtime_bucket_label} · success={float(top_runtime_bucket.get('success_rate', 0.0)):.0%} · latency={float(top_runtime_bucket.get('avg_latency_s', 0.0)):.2f}s"
                )
            if top_quantization_family:
                quantization_label = quantization_labels.get(
                    str(top_quantization_family.get("quantization_family") or ""),
                    str(top_quantization_family.get("quantization_family") or "quantization"),
                )
                st.caption(
                    f"Top família de quantização: {quantization_label} · success={float(top_quantization_family.get('success_rate', 0.0)):.0%} · latency={float(top_quantization_family.get('avg_latency_s', 0.0)):.2f}s"
                )
            if top_benchmark_use_case:
                use_case_key = str(top_benchmark_use_case.get("benchmark_use_case") or "ad_hoc")
                use_case_label = use_case_presets.get(use_case_key, {}).get("label", use_case_key)
                st.caption(
                    f"Top caso de uso agregado: {use_case_label} · success={float(top_benchmark_use_case.get('success_rate', 0.0)):.0%} · latency={float(top_benchmark_use_case.get('avg_latency_s', 0.0)):.2f}s"
                )

            benchmark_watchouts: list[str] = []
            if float(phase7_model_comparison_log_summary.get("success_rate") or 0.0) < 0.8:
                benchmark_watchouts.append("A taxa média de sucesso ainda está abaixo do ideal; vale revisar providers/modelos com falhas recorrentes.")
            if float(phase7_model_comparison_log_summary.get("avg_latency_s") or 0.0) > 30.0:
                benchmark_watchouts.append("A latência média do benchmark está alta; investigar buckets de runtime e quantizações mais leves.")
            if benchmark_watchouts:
                render_panel_header("Leitura diagnóstica do benchmark")
                render_message_list(benchmark_watchouts)

            render_status_badges(_build_badges_for_benchmark_summary(phase7_model_comparison_log_summary))

            render_panel_header(
                "Decision memo do benchmark",
                "Use este bloco para decidir o default recomendado, a alternativa mais rápida e a opção mais estável antes de abrir o drilldown bruto.",
            )
            best_quality_model = _pick_best_quality(
                phase7_model_comparison_log_summary.get("model_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("model_leaderboard"), list) else []
            )
            fastest_viable_model = _pick_fastest_viable(
                phase7_model_comparison_log_summary.get("model_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("model_leaderboard"), list) else []
            )
            safest_provider = _pick_best_quality(
                phase7_model_comparison_log_summary.get("provider_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("provider_leaderboard"), list) else []
            )
            render_labeled_value_grid(
                [
                    {
                        "label": "Default recomendado",
                        "value": str(best_quality_model.get("model") if isinstance(best_quality_model, dict) else "n/a"),
                        "compact": True,
                        "show_full": True,
                        "max_chars": 42,
                    },
                    {
                        "label": "Alternativa mais rápida",
                        "value": str(fastest_viable_model.get("model") if isinstance(fastest_viable_model, dict) else "n/a"),
                        "compact": True,
                        "show_full": True,
                        "max_chars": 42,
                    },
                    {
                        "label": "Provider mais estável",
                        "value": str(safest_provider.get("provider") if isinstance(safest_provider, dict) else "n/a"),
                        "compact": True,
                        "show_full": True,
                        "max_chars": 42,
                    },
                ],
                columns=3,
            )
            decision_notes: list[str] = []
            if isinstance(best_quality_model, dict):
                decision_notes.append(
                    f"Default recomendado agora: `{best_quality_model.get('model')}` com success={_format_rate(best_quality_model.get('success_rate'))}, adherence={_format_rate(best_quality_model.get('avg_format_adherence'))} e use-case-fit={_format_rate(best_quality_model.get('avg_use_case_fit_score'))}."
                )
            if isinstance(fastest_viable_model, dict):
                decision_notes.append(
                    f"Alternativa mais rápida mantendo viabilidade: `{fastest_viable_model.get('model')}` com latency={float(fastest_viable_model.get('avg_latency_s') or 0.0):.2f}s."
                )
            if isinstance(safest_provider, dict):
                decision_notes.append(
                    f"Provider mais estável agregado: `{safest_provider.get('provider')}` com success={_format_rate(safest_provider.get('success_rate'))}."
                )
            if top_benchmark_use_case:
                use_case_key = str(top_benchmark_use_case.get("benchmark_use_case") or "ad_hoc")
                decision_notes.append(
                    f"Caso de uso com melhor tração recente: `{use_case_presets.get(use_case_key, {}).get('label', use_case_key)}`; use-o como referência para defaults atuais."
                )
            if decision_notes:
                render_message_list(decision_notes, level="info")

            render_panel_header(
                "Benchmark visual decision layer",
                "Gráficos para comparar rapidamente defaults, alternativas rápidas e buckets mais fortes antes do drilldown tabular.",
            )
            provider_leaderboard = (
                phase7_model_comparison_log_summary.get("provider_leaderboard")
                if isinstance(phase7_model_comparison_log_summary.get("provider_leaderboard"), list)
                else []
            )
            model_leaderboard = (
                phase7_model_comparison_log_summary.get("model_leaderboard")
                if isinstance(phase7_model_comparison_log_summary.get("model_leaderboard"), list)
                else []
            )
            benchmark_use_case_leaderboard = (
                phase7_model_comparison_log_summary.get("benchmark_use_case_leaderboard")
                if isinstance(phase7_model_comparison_log_summary.get("benchmark_use_case_leaderboard"), list)
                else []
            )
            history_chart_col_1, history_chart_col_2 = st.columns(2)
            with history_chart_col_1:
                st.caption("Providers por sucesso e fit")
                render_bar_chart_from_rows(
                    [
                        {
                            "provider": str(item.get("provider") or "unknown"),
                            "success_rate": float(item.get("success_rate") or 0.0),
                            "avg_use_case_fit_score": float(item.get("avg_use_case_fit_score") or 0.0),
                        }
                        for item in provider_leaderboard[:8]
                    ],
                    index_field="provider",
                    value_fields=["success_rate", "avg_use_case_fit_score"],
                    height=230,
                )
            with history_chart_col_2:
                st.caption("Modelos por latência e aderência")
                render_bar_chart_from_rows(
                    [
                        {
                            "model": str(item.get("model") or "unknown"),
                            "avg_latency_s": float(item.get("avg_latency_s") or 0.0),
                            "avg_format_adherence": float(item.get("avg_format_adherence") or 0.0),
                        }
                        for item in model_leaderboard[:8]
                    ],
                    index_field="model",
                    value_fields=["avg_latency_s", "avg_format_adherence"],
                    height=230,
                )
            if benchmark_use_case_leaderboard:
                st.caption("Trails por caso de uso")
                render_bar_chart_from_rows(
                    [
                        {
                            "use_case": str(item.get("benchmark_use_case") or "unknown"),
                            "success_rate": float(item.get("success_rate") or 0.0),
                            "avg_latency_s": float(item.get("avg_latency_s") or 0.0),
                        }
                        for item in benchmark_use_case_leaderboard[:8]
                    ],
                    index_field="use_case",
                    value_fields=["success_rate", "avg_latency_s"],
                    height=230,
                )

            leaderboard_tab_1, leaderboard_tab_2, leaderboard_tab_3 = st.tabs(
                ["Providers e modelos", "Runtime e quantização", "Prompt e caso de uso"]
            )
            with leaderboard_tab_1:
                for title, rows in [
                    ("Leaderboard por provider", phase7_model_comparison_log_summary.get("provider_leaderboard")),
                    ("Leaderboard por model", phase7_model_comparison_log_summary.get("model_leaderboard")),
                ]:
                    if isinstance(rows, list) and rows:
                        st.write(f"**{title}**")
                        st.dataframe(
                            compact_rows(
                                rows[:5],
                                field_limits={"provider": 28, "model": 40},
                            ),
                            width="stretch",
                        )
            with leaderboard_tab_2:
                runtime_bucket_leaderboard = phase7_model_comparison_log_summary.get("runtime_bucket_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("runtime_bucket_leaderboard"), list) else []
                if runtime_bucket_leaderboard:
                    st.write("**Leaderboard por bucket de runtime**")
                    st.dataframe(
                        compact_rows(
                            [
                                {
                                    **item,
                                    "runtime_bucket_label": runtime_bucket_labels.get(
                                        str(item.get("runtime_bucket") or ""),
                                        str(item.get("runtime_bucket") or "runtime"),
                                    ),
                                }
                                for item in runtime_bucket_leaderboard[:5]
                            ],
                            field_limits={"runtime_bucket_label": 42},
                        ),
                        width="stretch",
                    )
                quantization_family_leaderboard = phase7_model_comparison_log_summary.get("quantization_family_leaderboard") if isinstance(phase7_model_comparison_log_summary.get("quantization_family_leaderboard"), list) else []
                if quantization_family_leaderboard:
                    st.write("**Leaderboard por família de quantização**")
                    st.dataframe(
                        compact_rows(
                            [
                                {
                                    **item,
                                    "quantization_family_label": quantization_labels.get(
                                        str(item.get("quantization_family") or ""),
                                        str(item.get("quantization_family") or "quantization"),
                                    ),
                                }
                                for item in quantization_family_leaderboard[:5]
                            ],
                            field_limits={"quantization_family_label": 42},
                        ),
                        width="stretch",
                    )
            with leaderboard_tab_3:
                for title, rows in [
                    ("Leaderboard por formato", phase7_model_comparison_log_summary.get("format_leaderboard")),
                    ("Leaderboard por retrieval strategy", phase7_model_comparison_log_summary.get("retrieval_strategy_leaderboard")),
                    ("Leaderboard por embedding provider", phase7_model_comparison_log_summary.get("embedding_provider_leaderboard")),
                    ("Leaderboard por embedding model", phase7_model_comparison_log_summary.get("embedding_model_leaderboard")),
                    ("Leaderboard por prompt profile", phase7_model_comparison_log_summary.get("prompt_profile_leaderboard")),
                    ("Leaderboard por uso de documentos", phase7_model_comparison_log_summary.get("document_usage_leaderboard")),
                    ("Leaderboard por caso de uso do benchmark", phase7_model_comparison_log_summary.get("benchmark_use_case_leaderboard")),
                ]:
                    if isinstance(rows, list) and rows:
                        st.write(f"**{title}**")
                        st.dataframe(
                            compact_rows(rows[:5], field_limits={"response_format": 28, "retrieval_strategy": 36, "embedding_provider": 28, "embedding_model": 40, "prompt_profile": 28, "document_usage": 28, "benchmark_use_case": 36}),
                            width="stretch",
                        )

        if phase7_model_comparison_log_entries:
            recent_entries = list(reversed(phase7_model_comparison_log_entries[-10:]))
            st.caption("Execuções recentes")
            st.dataframe(
                compact_rows(
                    [
                        {
                            "timestamp": entry.get("timestamp"),
                            "use_case": entry.get("benchmark_use_case"),
                            "profile": entry.get("prompt_profile"),
                            "format": entry.get("response_format"),
                            "docs": len(entry.get("document_ids") or []),
                            "candidates": len(entry.get("candidate_results") or []),
                            "success_rate": (entry.get("aggregate") or {}).get("success_rate") if isinstance(entry.get("aggregate"), dict) else None,
                            "avg_latency_s": (entry.get("aggregate") or {}).get("avg_latency_s") if isinstance(entry.get("aggregate"), dict) else None,
                            "prompt": entry.get("prompt_text"),
                        }
                        for entry in recent_entries
                    ],
                    field_limits={"use_case": 28, "profile": 24, "format": 18, "prompt": 72},
                ),
                width="stretch",
            )
            candidate_rows = _flatten_model_comparison_candidates(
                phase7_model_comparison_log_entries,
                runtime_bucket_labels=runtime_bucket_labels,
                quantization_labels=quantization_labels,
                use_case_presets=use_case_presets,
            )
            if candidate_rows:
                render_panel_header(
                    "Mapa visual avançado do benchmark",
                    "Use esta camada para enxergar trade-offs entre latência, fit, prompt profile e response format antes do drilldown tabular.",
                )
                advanced_chart_col_1, advanced_chart_col_2 = st.columns(2)
                with advanced_chart_col_1:
                    st.caption("Latência vs use-case-fit")
                    render_scatter_chart_from_rows(
                        candidate_rows[:60],
                        x_field="latency_s",
                        y_field="use_case_fit",
                        color_field="provider",
                        height=260,
                    )
                with advanced_chart_col_2:
                    st.caption("Heatmap · use case × prompt profile")
                    render_heatmap_from_rows(
                        candidate_rows,
                        row_field="use_case",
                        column_field="prompt_profile",
                        value_field="use_case_fit",
                    )
                st.caption("Heatmap · use case × response format")
                render_heatmap_from_rows(
                    candidate_rows,
                    row_field="use_case",
                    column_field="response_format",
                    value_field="format_adherence",
                )

                render_panel_header(
                    "Drilldown de candidatos recentes",
                    "Use os filtros para sair da visão agregada e investigar combinações específicas sem despejar toda a tabela de uma vez.",
                )
                filter_col_1, filter_col_2, filter_col_3, filter_col_4 = st.columns(4)
                provider_filter = filter_col_1.selectbox(
                    "Provider",
                    options=["all", *sorted({str(row.get('provider') or '') for row in candidate_rows if row.get('provider')})],
                    key="phase7_history_provider_filter",
                )
                model_filter = filter_col_2.selectbox(
                    "Model",
                    options=["all", *sorted({str(row.get('model') or '') for row in candidate_rows if row.get('model')})],
                    key="phase7_history_model_filter",
                )
                use_case_filter = filter_col_3.selectbox(
                    "Use case",
                    options=["all", *sorted({str(row.get('use_case') or '') for row in candidate_rows if row.get('use_case')})],
                    key="phase7_history_use_case_filter",
                )
                success_filter = filter_col_4.selectbox(
                    "Outcome",
                    options=["all", "success_only", "failures_only"],
                    key="phase7_history_success_filter",
                )
                filtered_candidate_rows = [
                    row
                    for row in candidate_rows
                    if (provider_filter == "all" or str(row.get("provider")) == provider_filter)
                    and (model_filter == "all" or str(row.get("model")) == model_filter)
                    and (use_case_filter == "all" or str(row.get("use_case")) == use_case_filter)
                    and (
                        success_filter == "all"
                        or (success_filter == "success_only" and bool(row.get("success")))
                        or (success_filter == "failures_only" and not bool(row.get("success")))
                    )
                ]
                st.caption(f"{len(filtered_candidate_rows)} linha(s) após os filtros ativos.")
                with st.expander("Abrir tabela detalhada de candidatos", expanded=False):
                    st.dataframe(
                        compact_rows(
                            filtered_candidate_rows[:30],
                            field_limits={
                                "use_case": 28,
                                "prompt_profile": 24,
                                "response_format": 18,
                                "provider": 24,
                                "model": 42,
                                "runtime_bucket": 28,
                                "quantization": 28,
                            },
                        ),
                        width="stretch",
                    )
            clear_requested = st.button(
                "Limpar histórico de comparação da Fase 7",
                key="phase7_clear_model_comparison_log_modular",
            )
        else:
            st.caption("Nenhuma comparação registrada ainda.")
    return clear_requested


def render_strategy_benchmark_panel(
    *,
    phase55_shadow_log_summary: dict[str, Any],
    phase55_langgraph_shadow_log_summary: dict[str, Any],
) -> None:
    with st.expander("Fase 7 · benchmark de estratégias adjacentes", expanded=False):
        retrieval_metric_col_1, retrieval_metric_col_2, retrieval_metric_col_3 = st.columns(3)
        retrieval_metric_col_1.metric("Retrieval shadow runs", int(phase55_shadow_log_summary.get("total_runs") or 0))
        retrieval_metric_col_2.metric("Same top-1", f"{float(phase55_shadow_log_summary.get('same_top_1_rate', 0.0)):.0%}")
        retrieval_metric_col_3.metric("Overlap médio", f"{float(phase55_shadow_log_summary.get('avg_overlap_ratio', 0.0)):.0%}")
        st.caption("Manual hybrid vs LangChain/Chroma: benchmark de recuperação reaproveitado como evidência comparativa da Fase 7.")
        if float(phase55_shadow_log_summary.get("same_top_1_rate") or 0.0) < 0.7:
            st.warning("A concordância de top-1 entre as estratégias de retrieval está baixa; vale investigar diferenças de ranking e grounding.")
        if phase55_shadow_log_summary.get("strategy_pairs"):
            st.write(
                {
                    "retrieval_strategy_pairs": phase55_shadow_log_summary.get("strategy_pairs"),
                    "retrieval_alternate_fallbacks": phase55_shadow_log_summary.get("alternate_fallbacks"),
                }
            )

        langgraph_metric_col_1, langgraph_metric_col_2, langgraph_metric_col_3, langgraph_metric_col_4 = st.columns(4)
        langgraph_metric_col_1.metric("LangGraph shadow runs", int(phase55_langgraph_shadow_log_summary.get("total_runs") or 0))
        langgraph_metric_col_2.metric("Same success", f"{float(phase55_langgraph_shadow_log_summary.get('same_success_rate', 0.0)):.0%}")
        langgraph_metric_col_3.metric("Δ latência média", f"{float(phase55_langgraph_shadow_log_summary.get('avg_latency_delta_s', 0.0)):.2f}s")
        langgraph_metric_col_4.metric("Δ qualidade média", f"{float(phase55_langgraph_shadow_log_summary.get('avg_quality_delta', 0.0)):.3f}")
        st.caption("Direct vs LangGraph context retry: benchmark estruturado reaproveitado como benchmark de estratégia da Fase 7.")
        if int(phase55_langgraph_shadow_log_summary.get("alternate_avoided_review_count") or 0) > 0:
            st.info("A estratégia alternativa já evitou revisão humana em parte dos casos; esses exemplos são bons candidatos para análise de promoção controlada.")
        if phase55_langgraph_shadow_log_summary.get("strategy_pairs"):
            st.write(
                {
                    "langgraph_strategy_pairs": phase55_langgraph_shadow_log_summary.get("strategy_pairs"),
                    "langgraph_alternate_fallbacks": phase55_langgraph_shadow_log_summary.get("alternate_fallbacks"),
                }
            )


def render_retrieval_embedding_experiments_panel(
    *,
    indexed_documents: list[dict[str, Any]],
    vector_backend_status: dict[str, Any],
    embedding_compatibility: dict[str, Any],
    rag_settings: Any,
    phase55_shadow_log_summary: dict[str, Any],
    phase7_model_comparison_log_summary: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
    runtime_execution_summary: dict[str, Any],
) -> None:
    st.info(
        "Esta superfície explicita as trilhas de embeddings, retrieval, reranking e strategy benchmark que já estavam espalhadas entre o benchmark local, shadow logs e runtime history."
    )

    file_type_counts: Counter[str] = Counter(
        str(document.get("file_type") or "unknown").lower()
        for document in indexed_documents
        if isinstance(document, dict)
    )

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
    metric_col_1.metric("Docs indexados", len(indexed_documents))
    metric_col_2.metric("Embedding compatível", "sim" if embedding_compatibility.get("compatible", True) else "não")
    metric_col_3.metric("Retrieval shadow runs", int(phase55_shadow_log_summary.get("total_runs") or 0))
    metric_col_4.metric("Benchmark runs", int(phase7_model_comparison_log_summary.get("total_runs") or 0))

    render_labeled_value_grid(
        [
            {"label": "Runtime runs", "value": int(runtime_execution_summary.get("total_runs") or 0)},
            {"label": "Eval PASS", "value": f"{float(phase8_eval_summary.get('pass_rate') or 0.0):.0%}"},
            {
                "label": "Vector backend",
                "value": str(vector_backend_status.get("backend") or "n/a"),
                "compact": True,
                "show_full": True,
                "max_chars": 42,
            },
        ],
        columns=3,
    )

    retrieval_watchouts: list[str] = []
    if not embedding_compatibility.get("compatible", True):
        retrieval_watchouts.append("O embedding ativo não está compatível com o índice; os leaderboards atuais podem não refletir a configuração operacional da sessão.")
    if float(phase55_shadow_log_summary.get("same_top_1_rate") or 0.0) < 0.7 and int(phase55_shadow_log_summary.get("total_runs") or 0) > 0:
        retrieval_watchouts.append("Há divergência relevante entre as estratégias de retrieval; investigar top-1 e overlap médio antes de consolidar defaults.")
    if retrieval_watchouts:
        for item in retrieval_watchouts:
            st.warning(item)

    st.write(
        {
            "embedding_provider": getattr(rag_settings, "embedding_provider", None),
            "embedding_model": getattr(rag_settings, "embedding_model", None),
            "embedding_context_window": getattr(rag_settings, "embedding_context_window", None),
            "embedding_truncate": getattr(rag_settings, "embedding_truncate", None),
            "retrieval_strategy": getattr(rag_settings, "retrieval_strategy", None),
            "chunking_strategy": getattr(rag_settings, "chunking_strategy", None),
            "chunk_size": getattr(rag_settings, "chunk_size", None),
            "chunk_overlap": getattr(rag_settings, "chunk_overlap", None),
            "top_k": getattr(rag_settings, "top_k", None),
            "rerank_pool_size": getattr(rag_settings, "rerank_pool_size", None),
            "rerank_lexical_weight": getattr(rag_settings, "rerank_lexical_weight", None),
            "vector_backend_status": vector_backend_status.get("status"),
            "vector_backend_message": vector_backend_status.get("message"),
            "embedding_message": embedding_compatibility.get("message"),
            "indexed_file_types": dict(file_type_counts),
        }
    )

    retrieval_shadow_snapshot = {
        "same_top_1_rate": phase55_shadow_log_summary.get("same_top_1_rate"),
        "avg_overlap_ratio": phase55_shadow_log_summary.get("avg_overlap_ratio"),
        "strategy_pairs": phase55_shadow_log_summary.get("strategy_pairs"),
        "alternate_fallbacks": phase55_shadow_log_summary.get("alternate_fallbacks"),
    }
    if any(value for value in retrieval_shadow_snapshot.values()):
        st.markdown("### Benchmark shadow de retrieval")
        st.write(retrieval_shadow_snapshot)

    retrieval_strategy_leaderboard = (
        phase7_model_comparison_log_summary.get("retrieval_strategy_leaderboard")
        if isinstance(phase7_model_comparison_log_summary.get("retrieval_strategy_leaderboard"), list)
        else []
    )
    embedding_provider_leaderboard = (
        phase7_model_comparison_log_summary.get("embedding_provider_leaderboard")
        if isinstance(phase7_model_comparison_log_summary.get("embedding_provider_leaderboard"), list)
        else []
    )
    embedding_model_leaderboard = (
        phase7_model_comparison_log_summary.get("embedding_model_leaderboard")
        if isinstance(phase7_model_comparison_log_summary.get("embedding_model_leaderboard"), list)
        else []
    )
    benchmark_use_case_leaderboard = (
        phase7_model_comparison_log_summary.get("benchmark_use_case_leaderboard")
        if isinstance(phase7_model_comparison_log_summary.get("benchmark_use_case_leaderboard"), list)
        else []
    )

    if retrieval_strategy_leaderboard:
        st.markdown("### Leaderboard por estratégia de retrieval")
        st.dataframe(compact_rows(retrieval_strategy_leaderboard[:10], field_limits={"retrieval_strategy": 36}), width="stretch")
    if embedding_provider_leaderboard:
        st.markdown("### Leaderboard por provider de embedding")
        st.dataframe(compact_rows(embedding_provider_leaderboard[:10], field_limits={"embedding_provider": 28, "provider": 28}), width="stretch")
    if embedding_model_leaderboard:
        st.markdown("### Leaderboard por modelo de embedding")
        st.dataframe(compact_rows(embedding_model_leaderboard[:10], field_limits={"embedding_model": 42, "model": 42}), width="stretch")
    if benchmark_use_case_leaderboard:
        st.markdown("### Trilhas de benchmark por caso de uso")
        st.dataframe(compact_rows(benchmark_use_case_leaderboard[:10], field_limits={"benchmark_use_case": 36}), width="stretch")

    if not any(
        [
            retrieval_strategy_leaderboard,
            embedding_provider_leaderboard,
            embedding_model_leaderboard,
            benchmark_use_case_leaderboard,
        ]
    ):
        st.caption("Ainda não há runs suficientes para preencher leaderboards explícitos de retrieval/embedding nesta superfície.")


def render_model_comparison_execution_result(
    *,
    stored_model_comparison_result: dict[str, Any] | None,
    comparison_use_documents: bool,
    comparison_response_format: str,
    runtime_bucket_labels: dict[str, str],
    quantization_labels: dict[str, str],
    use_case_presets: dict[str, dict[str, str]],
) -> None:
    if not isinstance(stored_model_comparison_result, dict):
        return

    aggregate = stored_model_comparison_result.get("aggregate") if isinstance(stored_model_comparison_result.get("aggregate"), dict) else {}
    candidate_results = stored_model_comparison_result.get("candidate_results") if isinstance(stored_model_comparison_result.get("candidate_results"), list) else []
    stored_use_case = str(stored_model_comparison_result.get("benchmark_use_case") or "ad_hoc")
    stored_use_case_label = use_case_presets.get(stored_use_case, {}).get("label", stored_use_case)

    render_panel_header(
        "Resultado da comparação",
        f"Caso de uso desta execução: {stored_use_case_label}",
    )
    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
    metric_col_1.metric("Candidatos", aggregate.get("total_candidates", 0))
    metric_col_2.metric("Taxa de sucesso", f"{float(aggregate.get('success_rate', 0.0)):.0%}")
    metric_col_3.metric("Latência média", f"{float(aggregate.get('avg_latency_s', 0.0)):.2f}s")
    metric_col_4.metric("Aderência média", f"{float(aggregate.get('avg_format_adherence', 0.0)):.0%}")
    if comparison_use_documents:
        st.caption(f"Groundedness média: {float(aggregate.get('avg_groundedness_score', 0.0)):.0%}")
    if comparison_response_format == "json":
        st.caption(f"Schema adherence média: {float(aggregate.get('avg_schema_adherence', 0.0)):.0%}")
    st.caption(f"Use-case fit médio: {float(aggregate.get('avg_use_case_fit_score', 0.0)):.0%}")
    render_status_badges(_build_badges_for_benchmark_summary(aggregate))

    best_latency = aggregate.get("best_latency_candidate") if isinstance(aggregate.get("best_latency_candidate"), dict) else None
    best_format = aggregate.get("best_format_candidate") if isinstance(aggregate.get("best_format_candidate"), dict) else None
    best_overall = aggregate.get("best_overall_candidate") if isinstance(aggregate.get("best_overall_candidate"), dict) else None
    if best_latency:
        st.caption(
            f"Melhor latência: {best_latency.get('provider')} · {best_latency.get('model')} · {best_latency.get('latency_s')}s"
        )
    if best_format:
        st.caption(
            f"Melhor aderência ao formato: {best_format.get('provider')} · {best_format.get('model')} · {float(best_format.get('format_adherence', 0.0)):.0%}"
        )
    if best_overall:
        st.caption(
            f"Melhor geral: {best_overall.get('provider')} · {best_overall.get('model')} · score={float(best_overall.get('comparison_score', 0.0)):.3f}"
        )

    viable_candidates = [candidate for candidate in candidate_results if isinstance(candidate, dict) and bool(candidate.get("success"))]
    fastest_candidate = min(
        viable_candidates,
        key=lambda candidate: float(candidate.get("latency_s") or 10**9),
    ) if viable_candidates else None
    safest_candidate = max(
        viable_candidates,
        key=lambda candidate: (
            float(candidate.get("format_adherence") or 0.0),
            float(candidate.get("use_case_fit_score") or 0.0),
            float(candidate.get("groundedness_score") or 0.0),
            float(candidate.get("schema_adherence") or 0.0),
        ),
    ) if viable_candidates else None
    render_panel_header(
        "Memorando de decisão da execução",
        "Esta execução já deve responder qual é o melhor default, qual é a alternativa mais rápida e qual combinação parece mais estável para o caso de uso atual.",
    )
    render_labeled_value_grid(
        [
            {
                "label": "Default desta execução",
                "value": _candidate_label(best_overall) if isinstance(best_overall, dict) else "n/a",
                "compact": True,
                "show_full": True,
                "max_chars": 52,
            },
            {
                "label": "Mais rápido viável",
                "value": _candidate_label(fastest_candidate) if isinstance(fastest_candidate, dict) else "n/a",
                "compact": True,
                "show_full": True,
                "max_chars": 52,
            },
            {
                "label": "Mais estável",
                "value": _candidate_label(safest_candidate) if isinstance(safest_candidate, dict) else "n/a",
                "compact": True,
                "show_full": True,
                "max_chars": 52,
            },
        ],
        columns=3,
    )
    execution_notes: list[str] = []
    if isinstance(best_overall, dict):
        execution_notes.append(
            f"Promova como default local desta execução: `{_candidate_label(best_overall)}` com score={float(best_overall.get('comparison_score', 0.0)):.3f}."
        )
    if isinstance(fastest_candidate, dict):
        execution_notes.append(
            f"Alternativa mais rápida: `{_candidate_label(fastest_candidate)}` com latency={float(fastest_candidate.get('latency_s') or 0.0):.2f}s."
        )
    if isinstance(safest_candidate, dict):
        execution_notes.append(
            f"Alternativa mais estável: `{_candidate_label(safest_candidate)}` com adherence={_format_rate(safest_candidate.get('format_adherence'))} e use-case-fit={_format_rate(safest_candidate.get('use_case_fit_score'))}."
        )
    if execution_notes:
        render_message_list(execution_notes, level="info")

    benchmark_watchouts: list[str] = []
    if float(aggregate.get("success_rate") or 0.0) < 0.8:
        benchmark_watchouts.append("Há falhas relevantes nesta execução; investigue os candidatos com erro antes de promover um default.")
    if float(aggregate.get("avg_latency_s") or 0.0) > 30.0:
        benchmark_watchouts.append("A latência média desta execução ficou alta; compare buckets de runtime e quantizações antes de consolidar a leitura.")
    if benchmark_watchouts:
        render_message_list(benchmark_watchouts)

    execution_chart_rows = _build_candidate_execution_rows(candidate_results)
    if execution_chart_rows:
        render_panel_header(
            "Comparação visual desta execução",
            "Use esta leitura para comparar rapidamente latência, aderência e fit dos candidatos antes de abrir as saídas completas.",
        )
        execution_chart_col_1, execution_chart_col_2 = st.columns(2)
        with execution_chart_col_1:
            st.caption("Latência por candidato")
            render_bar_chart_from_rows(
                execution_chart_rows,
                index_field="candidate",
                value_fields=["latency_s"],
                height=240,
            )
        with execution_chart_col_2:
            st.caption("Qualidade por candidato")
            render_bar_chart_from_rows(
                execution_chart_rows,
                index_field="candidate",
                value_fields=["format_adherence", "groundedness", "schema_adherence", "use_case_fit"],
                height=240,
            )
        st.caption("Scatter · latência vs use-case-fit")
        render_scatter_chart_from_rows(
            execution_chart_rows,
            x_field="latency_s",
            y_field="use_case_fit",
            color_field="candidate",
            height=260,
        )

    candidate_ranking = aggregate.get("candidate_ranking") if isinstance(aggregate.get("candidate_ranking"), list) else []
    if candidate_ranking:
        with st.expander("Ranking consolidado da execução", expanded=False):
            st.dataframe(
                compact_rows(
                    candidate_ranking,
                    field_limits={"provider": 24, "model": 42, "runtime_bucket": 28, "quantization_family": 28},
                ),
                width="stretch",
            )

    columns_count = min(3, max(1, len(candidate_results)))
    cols = st.columns(columns_count)
    for index, candidate in enumerate(candidate_results):
        with cols[index % columns_count]:
            with st.container(border=True):
                st.write(
                    f"**{candidate.get('provider_label') or candidate.get('provider_effective')} · {candidate.get('model_effective')}**"
                )
                st.caption(
                    f"{runtime_bucket_labels.get(str(candidate.get('runtime_bucket') or ''), str(candidate.get('runtime_bucket') or 'runtime'))} · {quantization_labels.get(str(candidate.get('quantization_family') or ''), str(candidate.get('quantization_family') or 'quantization'))} · success={candidate.get('success')} · latency={candidate.get('latency_s')}s · adherence={float(candidate.get('format_adherence', 0.0)):.0%}"
                )
                st.caption(
                    f"chars={candidate.get('output_chars')} · words={candidate.get('output_words')} · used_chunks={candidate.get('used_chunks')} · grounded={float(candidate.get('groundedness_score', 0.0)):.0%} · use-case-fit={float(candidate.get('use_case_fit_score', 0.0)):.0%}"
                )
                if isinstance(candidate.get("schema_adherence"), (int, float)):
                    st.caption(f"schema={float(candidate.get('schema_adherence', 0.0)):.0%}")
                preview_text = _truncate_response_preview(candidate.get("response_text"))
                if preview_text:
                    st.caption(f"Preview: {preview_text}")
                if candidate.get("error"):
                    st.error(str(candidate.get("error")))
                with st.expander("Ver saída completa", expanded=False):
                    st.text_area(
                        f"comparison_output_{index}",
                        value=str(candidate.get("response_text") or ""),
                        height=260,
                        disabled=True,
                        label_visibility="collapsed",
                    )