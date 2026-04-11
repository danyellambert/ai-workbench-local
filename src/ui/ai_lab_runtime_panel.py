from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st

from .ai_lab_common import (
    compact_rows,
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


def _build_runtime_watchouts(runtime_execution_summary: dict[str, Any]) -> list[str]:
    watchouts: list[str] = []
    error_rate = float(runtime_execution_summary.get("error_rate") or 0.0)
    needs_review_rate = float(runtime_execution_summary.get("needs_review_rate") or 0.0)
    avg_latency_s = float(runtime_execution_summary.get("avg_latency_s") or 0.0)
    context_pressure = float(runtime_execution_summary.get("avg_context_pressure_ratio") or 0.0)
    truncated_prompt_rate = float(runtime_execution_summary.get("truncated_prompt_rate") or 0.0)
    mcp_error_rate = float(runtime_execution_summary.get("mcp_error_rate") or 0.0)
    window_deltas = runtime_execution_summary.get("window_deltas") if isinstance(runtime_execution_summary.get("window_deltas"), dict) else {}

    if error_rate > 0.05:
        watchouts.append("A taxa agregada de erro está acima do conforto operacional; revisar execuções recentes com falha e bottlenecks dominantes.")
    if needs_review_rate > 0.10:
        watchouts.append("A taxa de `needs_review` está alta para o ritmo atual; vale revisar grounding, guardrails e rotas de workflow.")
    if avg_latency_s > 20.0:
        watchouts.append("A latência média já está acima do alvo confortável para operação recorrente; vale investigar retrieval, generation e custos de pipeline documental.")
    if context_pressure > 0.70:
        watchouts.append("A pressão média de contexto está alta; há risco de truncamento, custo excessivo ou auto-degrade mais frequente.")
    if truncated_prompt_rate > 0.15:
        watchouts.append("O truncamento de prompt está acontecendo com frequência; revisar top-k, context budget e estratégia de grounding.")
    if mcp_error_rate > 0.0:
        watchouts.append("Há erros recentes na trilha MCP; revisar EvidenceOps / MCP antes de confiar na operação multi-target.")

    if float(window_deltas.get("error_rate_delta") or 0.0) > 0.05:
        watchouts.append("A taxa de erro piorou na janela recente em relação à anterior.")
    if float(window_deltas.get("needs_review_rate_delta") or 0.0) > 0.05:
        watchouts.append("`needs_review` piorou na janela recente; isso sugere regressão operacional ou aumento de casos instáveis.")
    if float(window_deltas.get("avg_latency_delta_s") or 0.0) > 5.0:
        watchouts.append("A latência média aumentou perceptivelmente na janela recente.")

    return watchouts


def _build_runtime_problem_rows(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries[:10]:
        rows.append(
            {
                "timestamp": entry.get("timestamp"),
                "flow": entry.get("flow_type"),
                "task": entry.get("task_type"),
                "success": entry.get("success"),
                "needs_review": entry.get("needs_review"),
                "latency_s": entry.get("latency_s"),
                "total_tokens": entry.get("total_tokens"),
                "budget_alert_status": entry.get("budget_alert_status"),
                "mcp_error_calls": entry.get("mcp_error_call_count"),
                "error_message": entry.get("error_message"),
            }
        )
    return rows


def _build_document_inventory_rows(indexed_documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for document in indexed_documents:
        loader_metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
        routing_diagnostics = loader_metadata.get("routing_diagnostics") if isinstance(loader_metadata.get("routing_diagnostics"), dict) else {}
        vl_router = loader_metadata.get("vl_router") if isinstance(loader_metadata.get("vl_router"), dict) else {}
        file_type = str(document.get("file_type") or "-").lower()
        strategy_label = str(
            loader_metadata.get("strategy_label")
            or loader_metadata.get("loader_strategy_label")
            or loader_metadata.get("loader_strategy_used")
            or "-"
        )
        ocr_state = (
            "aplicado"
            if bool(loader_metadata.get("ocr_fallback_applied"))
            else "tentado"
            if bool(loader_metadata.get("ocr_fallback_attempted"))
            else "não"
        )
        suspicious_pages = int(loader_metadata.get("suspicious_pages") or 0)
        docling_mode = str(loader_metadata.get("docling_mode") or ("attempted" if loader_metadata.get("docling_attempted") else "not_used"))
        vl_decision = str(vl_router.get("decision") or "-")
        evidence_path = str(routing_diagnostics.get("decision") or "-")
        badges: list[str] = []
        if suspicious_pages > 0:
            badges.append("⚠️ suspicious")
        if ocr_state != "não":
            badges.append("OCR")
        if docling_mode not in {"not_used", "none", "-"}:
            badges.append("Docling")
        if vl_decision not in {"-", "none", "not_used"}:
            badges.append(f"VL:{vl_decision}")
        if evidence_path not in {"-", "", "none"}:
            badges.append(f"Path:{evidence_path}")
        recommended_action = (
            "Revisar parsing e considerar reindexação"
            if suspicious_pages > 0 or ocr_state == "tentado"
            else "Monitorar evidence path"
            if evidence_path not in {"-", "", "none"}
            else "Operação confortável"
        )
        rows.append(
            {
                "arquivo": str(document.get("name") or "documento"),
                "tipo": file_type or "-",
                "chars": int(document.get("char_count") or 0),
                "chunks": int(document.get("chunk_count") or 0),
                "indexado_em": str(document.get("indexed_at") or "-"),
                "extração_pdf": strategy_label if file_type == "pdf" else "-",
                "ocr": ocr_state if file_type == "pdf" else "-",
                "ocr_backend": str(loader_metadata.get("ocr_backend") or loader_metadata.get("evidence_ocr_backend") or "-") if file_type == "pdf" else "-",
                "docling": docling_mode if file_type == "pdf" else "-",
                "vl": vl_decision if file_type == "pdf" else "-",
                "evidence_path": evidence_path if file_type == "pdf" else "-",
                "flags_operacionais": " · ".join(badges) if badges else "🟢 normal",
                "ação_recomendada": recommended_action if file_type == "pdf" else "Operação confortável",
            }
        )
    return rows


def _build_pdf_diagnostics(indexed_documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int], int, int, int, int]:
    pdf_documents = [document for document in indexed_documents if str(document.get("file_type") or "").lower() == "pdf"]
    strategy_counts: Counter[str] = Counter()
    ocr_backend_counts: Counter[str] = Counter()
    suspicious_pages_total = 0
    docling_docs = 0
    ocr_docs = 0
    evidence_docs = 0
    rows: list[dict[str, Any]] = []

    for document in pdf_documents:
        loader_metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
        routing_diagnostics = loader_metadata.get("routing_diagnostics") if isinstance(loader_metadata.get("routing_diagnostics"), dict) else {}
        vl_router = loader_metadata.get("vl_router") if isinstance(loader_metadata.get("vl_router"), dict) else {}

        strategy_label = str(
            loader_metadata.get("strategy_label")
            or loader_metadata.get("loader_strategy_label")
            or loader_metadata.get("loader_strategy_used")
            or "-"
        )
        strategy_counts[strategy_label] += 1
        suspicious_pages = int(loader_metadata.get("suspicious_pages") or 0)
        suspicious_pages_total += suspicious_pages

        docling_attempted = bool(loader_metadata.get("docling_attempted"))
        if docling_attempted:
            docling_docs += 1

        ocr_fallback_applied = bool(loader_metadata.get("ocr_fallback_applied"))
        ocr_fallback_attempted = bool(loader_metadata.get("ocr_fallback_attempted"))
        if ocr_fallback_applied or ocr_fallback_attempted:
            ocr_docs += 1

        if bool(loader_metadata.get("evidence_pipeline_used")) or str(routing_diagnostics.get("decision") or "") == "evidence_path":
            evidence_docs += 1

        ocr_backend = str(loader_metadata.get("ocr_backend") or loader_metadata.get("evidence_ocr_backend") or "-")
        if ocr_backend and ocr_backend != "-":
            ocr_backend_counts[ocr_backend] += 1

        rows.append(
            {
                "arquivo": str(document.get("name") or "document.pdf"),
                "estrategia_pdf": strategy_label,
                "paginas_suspeitas": suspicious_pages,
                "docling_mode": str(loader_metadata.get("docling_mode") or ("attempted" if docling_attempted else "not_used")),
                "ocr_fallback": "aplicado" if ocr_fallback_applied else "tentado" if ocr_fallback_attempted else "nao",
                "ocr_backend": ocr_backend,
                "evidence_path": str(routing_diagnostics.get("decision") or "-"),
                "vl_decision": str(vl_router.get("decision") or "-"),
                "chars": int(document.get("char_count") or 0),
            }
        )

    return rows, dict(strategy_counts), dict(ocr_backend_counts), suspicious_pages_total, docling_docs, ocr_docs, evidence_docs


def _build_runtime_distribution_rows(counter_payload: dict[str, Any], *, key_name: str) -> list[dict[str, Any]]:
    if not isinstance(counter_payload, dict):
        return []
    return [
        {key_name: str(name), "count": int(count)}
        for name, count in counter_payload.items()
        if str(name).strip()
    ]


def _build_runtime_stage_share_rows(runtime_execution_summary: dict[str, Any]) -> list[dict[str, float | str]]:
    return [
        {"stage": "retrieval", "share": float(runtime_execution_summary.get("avg_retrieval_share") or 0.0)},
        {"stage": "generation", "share": float(runtime_execution_summary.get("avg_generation_share") or 0.0)},
        {"stage": "prompt_build", "share": float(runtime_execution_summary.get("avg_prompt_build_share") or 0.0)},
        {"stage": "other", "share": float(runtime_execution_summary.get("avg_other_latency_share") or 0.0)},
    ]


def _build_runtime_window_chart_rows(runtime_execution_summary: dict[str, Any]) -> list[dict[str, float | str]]:
    recent_window = runtime_execution_summary.get("recent_window_summary") if isinstance(runtime_execution_summary.get("recent_window_summary"), dict) else {}
    previous_window = runtime_execution_summary.get("previous_window_summary") if isinstance(runtime_execution_summary.get("previous_window_summary"), dict) else {}
    return [
        {
            "window": "previous",
            "avg_latency_s": float(previous_window.get("avg_latency_s") or 0.0),
            "error_rate": float(previous_window.get("error_rate") or 0.0),
            "needs_review_rate": float(previous_window.get("needs_review_rate") or 0.0),
            "avg_context_pressure_ratio": float(previous_window.get("avg_context_pressure_ratio") or 0.0),
        },
        {
            "window": "recent",
            "avg_latency_s": float(recent_window.get("avg_latency_s") or float(runtime_execution_summary.get("avg_latency_s") or 0.0)),
            "error_rate": float(recent_window.get("error_rate") or float(runtime_execution_summary.get("error_rate") or 0.0)),
            "needs_review_rate": float(recent_window.get("needs_review_rate") or float(runtime_execution_summary.get("needs_review_rate") or 0.0)),
            "avg_context_pressure_ratio": float(recent_window.get("avg_context_pressure_ratio") or float(runtime_execution_summary.get("avg_context_pressure_ratio") or 0.0)),
        },
    ]


def render_runtime_onboarding_panel(
    *,
    indexed_documents: list[dict[str, Any]],
    runtime_execution_summary: dict[str, Any],
    phase7_model_comparison_log_summary: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
) -> None:
    indexed_documents_count = len(indexed_documents)
    runtime_runs = int(runtime_execution_summary.get("total_runs") or 0)
    benchmark_runs = int(phase7_model_comparison_log_summary.get("total_runs") or 0)
    eval_runs = int(phase8_eval_summary.get("total_runs") or 0)
    if indexed_documents_count > 0 and runtime_runs > 0:
        return

    with st.container(border=True):
        st.markdown("#### Bootstrap técnico desta superfície")
        st.caption("Esta aba concentra ingestão documental, saúde vetorial e observabilidade operacional. Quando o lab ainda está vazio, siga esta ordem para gerar um primeiro ciclo útil de evidência.")
        st.markdown(
            "\n".join(
                [
                    "1. Faça upload e indexação do primeiro documento ou corpus de teste.",
                    "2. Gere uma primeira execução em `Document / Chat Experiments` ou `Workflow Inspector & Structured`.",
                    "3. Rode uma comparação em `Benchmarks & Model Comparison`.",
                    "4. Use `Evals & Diagnosis` para começar a leitura persistida de qualidade.",
                ]
            )
        )
        metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
        metric_col_1.metric("Docs indexados", indexed_documents_count)
        metric_col_2.metric("Runtime runs", runtime_runs)
        metric_col_3.metric("Benchmark runs", benchmark_runs)
        metric_col_4.metric("Eval runs", eval_runs)


def render_runtime_operational_summary(
    *,
    indexed_documents: list[dict[str, Any]],
    vector_backend_status: dict[str, Any],
    embedding_compatibility: dict[str, Any],
    runtime_execution_summary: dict[str, Any],
    phase6_document_agent_log_summary: dict[str, Any],
    phase7_model_comparison_log_summary: dict[str, Any],
    phase8_eval_summary: dict[str, Any],
) -> None:
    recent_window_summary = runtime_execution_summary.get("recent_window_summary") if isinstance(runtime_execution_summary.get("recent_window_summary"), dict) else {}
    previous_window_summary = runtime_execution_summary.get("previous_window_summary") if isinstance(runtime_execution_summary.get("previous_window_summary"), dict) else {}
    window_deltas = runtime_execution_summary.get("window_deltas") if isinstance(runtime_execution_summary.get("window_deltas"), dict) else {}
    problematic_entries = runtime_execution_summary.get("problematic_entries") if isinstance(runtime_execution_summary.get("problematic_entries"), list) else []

    with st.container(border=True):
        st.markdown("#### Saúde vetorial")
        st.caption("Leitura rápida do índice, compatibilidade de embeddings e estado operacional da base documental atual.")
        render_labeled_value_grid(
            [
                {"label": "Docs indexados", "value": len(indexed_documents)},
                {
                    "label": "Status do índice",
                    "value": str(vector_backend_status.get("status") or "n/a"),
                    "compact": True,
                    "show_full": True,
                    "max_chars": 42,
                },
                {
                    "label": "Backend vetorial",
                    "value": str(vector_backend_status.get("backend") or "n/a"),
                    "compact": True,
                    "show_full": True,
                    "max_chars": 42,
                },
                {"label": "Embedding compatível", "value": "sim" if embedding_compatibility.get("compatible", True) else "não"},
            ],
            columns=4,
        )
        st.caption(
            f"json_chunks={vector_backend_status.get('json_chunks')} · chroma_chunks={vector_backend_status.get('chroma_chunks')} · persist_dir={vector_backend_status.get('persist_dir')}"
        )
        if not embedding_compatibility.get("compatible", True):
            st.warning(str(embedding_compatibility.get("message") or "A configuração atual de embeddings não é compatível com o índice carregado."))
        else:
            status = str(vector_backend_status.get("status") or "")
            if status in {"dessincronizado", "out_of_sync"}:
                st.warning(str(vector_backend_status.get("message") or "Vector backend out of sync."))
            elif status in {"fallback_local", "local_fallback", "no_index"}:
                st.info(str(vector_backend_status.get("message") or "No canonical index is currently active."))

    with st.container(border=True):
        render_panel_header(
            "Economia de runtime & observabilidade",
            "Latência, confiabilidade, custo estimado, pressão de contexto e comparação entre janela recente e anterior.",
        )
        if int(recent_window_summary.get("total_runs") or 0) > 0:
            st.caption("Janela recente vs anterior")
            trend_col_1, trend_col_2, trend_col_3, trend_col_4 = st.columns(4)
            trend_col_1.metric("Recent runs", int(recent_window_summary.get("total_runs") or 0))
            trend_col_2.metric(
                "Recent error",
                _format_rate(recent_window_summary.get("error_rate")),
                delta=(f"{float(window_deltas.get('error_rate_delta') or 0.0) * 100:+.0f} pp" if window_deltas else None),
            )
            trend_col_3.metric(
                "Recent needs review",
                _format_rate(recent_window_summary.get("needs_review_rate")),
                delta=(f"{float(window_deltas.get('needs_review_rate_delta') or 0.0) * 100:+.0f} pp" if window_deltas else None),
            )
            trend_col_4.metric(
                "Recent latency",
                f"{float(recent_window_summary.get('avg_latency_s') or 0.0):.2f}s",
                delta=(f"{float(window_deltas.get('avg_latency_delta_s') or 0.0):+.2f}s" if window_deltas else None),
            )
            trend_col_5, trend_col_6, trend_col_7, trend_col_8 = st.columns(4)
            trend_col_5.metric(
                "Recent tokens",
                f"{float(recent_window_summary.get('avg_total_tokens') or 0.0):.0f}",
                delta=(f"{float(window_deltas.get('avg_total_tokens_delta') or 0.0):+.0f}" if window_deltas else None),
            )
            recent_cost = float(recent_window_summary.get("avg_cost_usd") or 0.0)
            previous_cost = float(previous_window_summary.get("avg_cost_usd") or 0.0)
            recent_cost_label = f"${recent_cost:.6f}" if recent_cost > 0 or previous_cost > 0 else "n/a"
            trend_col_6.metric(
                "Recent cost",
                recent_cost_label,
                delta=(f"${float(window_deltas.get('avg_cost_delta_usd') or 0.0):+.6f}" if window_deltas and (recent_cost > 0 or previous_cost > 0) else None),
            )
            trend_col_7.metric(
                "Recent pressure",
                f"{float(recent_window_summary.get('avg_context_pressure_ratio') or 0.0):.2f}",
                delta=(f"{float(window_deltas.get('avg_context_pressure_ratio_delta') or 0.0):+.2f}" if window_deltas else None),
            )
            trend_col_8.metric(
                "Recent MCP error",
                _format_rate(recent_window_summary.get("mcp_error_rate")),
                delta=(f"{float(window_deltas.get('mcp_error_rate_delta') or 0.0) * 100:+.0f} pp" if window_deltas else None),
            )

        runtime_watchouts = _build_runtime_watchouts(runtime_execution_summary)
        if runtime_watchouts:
            render_panel_header("Leitura operacional")
            render_message_list(runtime_watchouts)
        elif int(runtime_execution_summary.get("total_runs") or 0) > 0:
            st.success("Os sinais recentes de runtime permanecem dentro de uma zona confortável para esta etapa do AI Lab.")

        render_status_badges(
            [
                (f"error {_format_rate(runtime_execution_summary.get('error_rate'))}", "critical" if float(runtime_execution_summary.get("error_rate") or 0.0) > 0.05 else "healthy"),
                (f"needs_review {_format_rate(runtime_execution_summary.get('needs_review_rate'))}", "attention" if float(runtime_execution_summary.get("needs_review_rate") or 0.0) > 0.10 else "healthy"),
                (f"pressure {float(runtime_execution_summary.get('avg_context_pressure_ratio') or 0.0):.2f}", "attention" if float(runtime_execution_summary.get("avg_context_pressure_ratio") or 0.0) > 0.70 else "healthy"),
                (f"MCP {_format_rate(runtime_execution_summary.get('mcp_error_rate'))}", "attention" if float(runtime_execution_summary.get("mcp_error_rate") or 0.0) > 0.0 else "healthy"),
            ]
        )

        st.caption("Comfort zones de referência: latency < 20s · error rate = 0% · needs_review < 10% · context pressure < 0.70 · MCP error = 0%.")
        economy_col_1, economy_col_2, economy_col_3, economy_col_4 = st.columns(4)
        economy_col_1.metric("Runtime runs", int(runtime_execution_summary.get("total_runs") or 0))
        economy_col_2.metric("Avg latency", f"{float(runtime_execution_summary.get('avg_latency_s') or 0.0):.2f}s")
        economy_col_3.metric("Avg tokens", f"{float(runtime_execution_summary.get('avg_total_tokens') or 0.0):.0f}")
        avg_cost = runtime_execution_summary.get("avg_cost_usd")
        costed_runs = int(runtime_execution_summary.get("costed_runs") or 0)
        economy_col_4.metric("Avg cost", f"${float(avg_cost or 0.0):.6f}" if costed_runs > 0 else "n/a")
        render_labeled_value_grid(
            [
                {"label": "Context pressure", "value": f"{float(runtime_execution_summary.get('avg_context_pressure_ratio') or 0.0):.2f}"},
                {"label": "Prompt truncation", "value": f"{float(runtime_execution_summary.get('truncated_prompt_rate') or 0.0):.0%}"},
                {"label": "Auto-degrade", "value": f"{float(runtime_execution_summary.get('auto_degrade_rate') or 0.0):.0%}"},
                {
                    "label": "Último runtime",
                    "value": _format_timestamp(runtime_execution_summary.get("latest_timestamp")),
                    "detail": str(runtime_execution_summary.get("latest_timestamp") or "").replace("T", " ")[:19],
                },
            ],
            columns=4,
        )
        bottlenecks = runtime_execution_summary.get("bottleneck_stage_counts") if isinstance(runtime_execution_summary.get("bottleneck_stage_counts"), dict) else {}
        render_panel_header(
            "Camada visual do runtime",
            "Comparação visual da janela recente, distribuição por flow e peso relativo dos estágios de latência.",
        )
        chart_col_1, chart_col_2 = st.columns(2)
        with chart_col_1:
            st.caption("Janela recente vs anterior")
            render_line_chart_from_rows(
                _build_runtime_window_chart_rows(runtime_execution_summary),
                index_field="window",
                value_fields=["avg_latency_s", "avg_context_pressure_ratio"],
                height=240,
            )
        with chart_col_2:
            st.caption("Erro e revisão humana por janela")
            render_bar_chart_from_rows(
                _build_runtime_window_chart_rows(runtime_execution_summary),
                index_field="window",
                value_fields=["error_rate", "needs_review_rate"],
                height=240,
            )

        distribution_col_1, distribution_col_2, distribution_col_3 = st.columns(3)
        with distribution_col_1:
            st.caption("Distribuição por flow")
            render_bar_chart_from_rows(
                _build_runtime_distribution_rows(runtime_execution_summary.get("flow_counts") or {}, key_name="flow"),
                index_field="flow",
                value_fields=["count"],
                height=220,
            )
        with distribution_col_2:
            st.caption("Gargalo dominante")
            render_bar_chart_from_rows(
                _build_runtime_distribution_rows(bottlenecks, key_name="stage"),
                index_field="stage",
                value_fields=["count"],
                height=220,
            )
        with distribution_col_3:
            st.caption("Share médio de latência")
            render_bar_chart_from_rows(
                _build_runtime_stage_share_rows(runtime_execution_summary),
                index_field="stage",
                value_fields=["share"],
                height=220,
            )

        if bottlenecks:
            st.caption("Bottleneck dominante nas execuções recentes")
            st.dataframe(
                compact_rows(
                    [{"latency_stage": stage_name, "count": count} for stage_name, count in bottlenecks.items()],
                    field_limits={"latency_stage": 42},
                ),
                width="stretch",
            )
        flow_metric_rows = runtime_execution_summary.get("flow_metric_rows") if isinstance(runtime_execution_summary.get("flow_metric_rows"), list) else []
        if flow_metric_rows:
            render_panel_header(
                "Economia operacional por flow",
                "Leitura comparativa de latência, volume, custo e estabilidade por flow para reduzir dependência de tabela crua.",
            )
            flow_chart_col_1, flow_chart_col_2, flow_chart_col_3 = st.columns(3)
            with flow_chart_col_1:
                st.caption("Latência e volume médio por flow")
                render_bar_chart_from_rows(
                    flow_metric_rows,
                    index_field="flow",
                    value_fields=["avg_latency_s", "avg_total_tokens"],
                    height=240,
                )
            with flow_chart_col_2:
                st.caption("Custo e runs por flow")
                render_bar_chart_from_rows(
                    flow_metric_rows,
                    index_field="flow",
                    value_fields=["avg_cost_usd", "runs"],
                    height=240,
                )
            with flow_chart_col_3:
                st.caption("Erro e revisão humana por flow")
                render_bar_chart_from_rows(
                    flow_metric_rows,
                    index_field="flow",
                    value_fields=["error_rate", "needs_review_rate"],
                    height=240,
                )
            with st.expander("Abrir tabela comparativa por flow", expanded=False):
                st.dataframe(
                    compact_rows(
                        flow_metric_rows,
                        field_limits={"flow": 36},
                    ),
                    width="stretch",
                )
        if problematic_entries:
            with st.expander("Execuções recentes que merecem triagem", expanded=False):
                st.dataframe(
                    compact_rows(
                        _build_runtime_problem_rows(problematic_entries),
                        field_limits={
                            "flow": 28,
                            "task": 28,
                            "budget_alert_status": 36,
                            "error_message": 72,
                        },
                    ),
                    width="stretch",
                )

    with st.container(border=True):
        st.markdown("#### Routing / traces")
        st.caption("Leitura resumida dos sinais de qualidade, inspeção de workflow e profundidade diagnóstica que orbitam esta base operacional.")
        trace_col_1, trace_col_2, trace_col_3, trace_col_4 = st.columns(4)
        trace_col_1.metric("Doc-agent runs", int(phase6_document_agent_log_summary.get("total_runs") or 0))
        trace_col_2.metric("Benchmark runs", int(phase7_model_comparison_log_summary.get("total_runs") or 0))
        trace_col_3.metric("Eval PASS", f"{float(phase8_eval_summary.get('pass_rate') or 0.0):.0%}")
        trace_col_4.metric("Needs review", f"{float(runtime_execution_summary.get('needs_review_rate') or 0.0):.0%}")
        trace_payload: dict[str, Any] = {}
        flow_counts = runtime_execution_summary.get("flow_counts") if isinstance(runtime_execution_summary.get("flow_counts"), dict) else {}
        budget_modes = runtime_execution_summary.get("budget_mode_counts") if isinstance(runtime_execution_summary.get("budget_mode_counts"), dict) else {}
        if flow_counts:
            trace_payload["flow_counts"] = flow_counts
        if budget_modes:
            trace_payload["budget_modes"] = budget_modes
        if phase6_document_agent_log_summary.get("workflow_route_decision_counts"):
            trace_payload["doc_agent_route_decisions"] = phase6_document_agent_log_summary.get("workflow_route_decision_counts")
        if trace_payload:
            st.write(trace_payload)


def render_runtime_index_health_panel(
    *,
    indexed_documents: list[dict[str, Any]],
    vector_backend_status: dict[str, Any],
    embedding_compatibility: dict[str, Any],
) -> None:
    render_panel_header(
        "Corpus / index health",
        "Leitura por documento para indexação, parsing e sinais documentais relevantes ao runtime atual, incluindo flags operacionais e ações recomendadas.",
    )
    if not indexed_documents:
        st.info("Nenhum documento indexado ainda. Depois da primeira indexação, este bloco passa a mostrar o inventário operacional do índice e os sinais por documento.")
        return

    file_type_counts = Counter(str(document.get("file_type") or "-").lower() for document in indexed_documents)
    pdf_count = int(file_type_counts.get("pdf") or 0)
    inventory_rows = _build_document_inventory_rows(indexed_documents)
    docs_with_attention = [
        row for row in inventory_rows if "⚠️" in str(row.get("flags_operacionais") or "") or "OCR" in str(row.get("flags_operacionais") or "")
    ]
    docs_with_vl = [row for row in inventory_rows if "VL:" in str(row.get("flags_operacionais") or "")]
    docs_with_docling = [row for row in inventory_rows if "Docling" in str(row.get("flags_operacionais") or "")]
    docs_reindex_recommended = [
        row for row in inventory_rows if "reindexação" in str(row.get("ação_recomendada") or "").lower()
    ]

    inventory_col_1, inventory_col_2, inventory_col_3, inventory_col_4, inventory_col_5 = st.columns(5)
    inventory_col_1.metric("Documentos", len(indexed_documents))
    inventory_col_2.metric("PDFs", pdf_count)
    inventory_col_3.metric("Tipos de arquivo", len(file_type_counts))
    inventory_col_4.metric("Docs com atenção", len(docs_with_attention))
    inventory_col_5.metric("Embedding compatível", "sim" if embedding_compatibility.get("compatible", True) else "não")
    inventory_col_6, inventory_col_7, inventory_col_8 = st.columns(3)
    inventory_col_6.metric("Docs com Docling", len(docs_with_docling))
    inventory_col_7.metric("Docs com VL", len(docs_with_vl))
    inventory_col_8.metric("Reindex sugerido", len(docs_reindex_recommended))
    render_status_badges(
        [
            (f"{len(docs_with_attention)} docs com atenção", "attention" if docs_with_attention else "healthy"),
            (f"{len(docs_with_docling)} com Docling", "info"),
            (f"{len(docs_with_vl)} com VL", "info"),
            (f"{len(docs_reindex_recommended)} reindex sugerido", "attention" if docs_reindex_recommended else "healthy"),
        ]
    )
    st.caption(
        f"Backend={vector_backend_status.get('backend')} · status={vector_backend_status.get('status')} · json_chunks={vector_backend_status.get('json_chunks')} · chroma_chunks={vector_backend_status.get('chroma_chunks')}"
    )
    render_panel_header(
        "Composição do corpus",
        "Distribuição visual do corpus por tipo de arquivo e concentração de documentos com atenção operacional.",
    )
    corpus_chart_col_1, corpus_chart_col_2 = st.columns(2)
    with corpus_chart_col_1:
        render_bar_chart_from_rows(
            [{"file_type": str(file_type), "count": int(count)} for file_type, count in file_type_counts.items()],
            index_field="file_type",
            value_fields=["count"],
            height=220,
        )
    with corpus_chart_col_2:
        render_bar_chart_from_rows(
            [
                {"bucket": "atenção", "count": len(docs_with_attention)},
                {"bucket": "Docling", "count": len(docs_with_docling)},
                {"bucket": "VL", "count": len(docs_with_vl)},
                {"bucket": "reindex", "count": len(docs_reindex_recommended)},
            ],
            index_field="bucket",
            value_fields=["count"],
            height=220,
        )
    if docs_with_attention:
        render_panel_header("Anomalias documentais prioritárias")
        st.dataframe(
            compact_rows(
                docs_with_attention[:10],
                field_limits={
                    "arquivo": 56,
                    "extração_pdf": 40,
                    "evidence_path": 40,
                    "flags_operacionais": 52,
                    "ação_recomendada": 56,
                },
            ),
            width="stretch",
        )
    st.dataframe(
        compact_rows(
            inventory_rows,
            field_limits={
                "arquivo": 56,
                "extração_pdf": 40,
                "evidence_path": 40,
                "flags_operacionais": 52,
                "ação_recomendada": 56,
            },
        ),
        width="stretch",
    )


def render_runtime_observability_diagnostics(
    *,
    indexed_documents: list[dict[str, Any]],
    vector_backend_status: dict[str, Any],
    embedding_compatibility: dict[str, Any],
) -> None:
    render_panel_header(
        "Diagnóstico documental avançado",
        "Fecha a leitura de document intelligence com parsing documental, OCR, VLM, compatibilidade vetorial, suspicious pages e sinais de attention/reindexação.",
    )

    pdf_rows, strategy_counts, ocr_backend_counts, suspicious_pages_total, docling_docs, ocr_docs, evidence_docs = _build_pdf_diagnostics(indexed_documents)
    if not pdf_rows:
        st.info("Nenhum PDF indexado ainda. Quando houver PDFs no índice, este painel mostrará sinais de parsing, OCR, Docling e VLM.")
        return

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
    metric_col_1.metric("PDFs indexados", len(pdf_rows))
    metric_col_2.metric("Páginas suspeitas", suspicious_pages_total)
    metric_col_3.metric("Docs com Docling", docling_docs)
    metric_col_4.metric("Docs com OCR", ocr_docs)

    metric_col_5, metric_col_6 = st.columns(2)
    metric_col_5.metric("Docs no evidence path", evidence_docs)
    metric_col_6.metric("Embedding compatível", "sim" if embedding_compatibility.get("compatible", True) else "não")
    render_panel_header(
        "Diagnóstico visual de PDF / OCR / VLM",
        "Distribuição visual dos modos de parsing documental, OCR backend e footprint operacional da pipeline PDF.",
    )
    pdf_chart_col_1, pdf_chart_col_2, pdf_chart_col_3 = st.columns(3)
    with pdf_chart_col_1:
        render_bar_chart_from_rows(
            [{"strategy": key, "count": value} for key, value in strategy_counts.items()],
            index_field="strategy",
            value_fields=["count"],
            height=220,
        )
    with pdf_chart_col_2:
        render_bar_chart_from_rows(
            [{"backend": key, "count": value} for key, value in ocr_backend_counts.items()],
            index_field="backend",
            value_fields=["count"],
            height=220,
        )
    with pdf_chart_col_3:
        render_bar_chart_from_rows(
            [
                {"bucket": "Docling", "count": docling_docs},
                {"bucket": "OCR", "count": ocr_docs},
                {"bucket": "Evidence", "count": evidence_docs},
                {"bucket": "Suspicious pages", "count": suspicious_pages_total},
            ],
            index_field="bucket",
            value_fields=["count"],
            height=220,
        )

    diagnostic_watchouts: list[str] = []
    if suspicious_pages_total > 0:
        diagnostic_watchouts.append("Há páginas suspeitas no corpus PDF atual; priorize revisão dos documentos com parsing menos confiável.")
    if ocr_docs > 0:
        diagnostic_watchouts.append("OCR fallback já foi acionado em parte dos PDFs; isso pode indicar ganho de coverage, mas também maior custo e variabilidade de parsing.")
    if evidence_docs > 0:
        diagnostic_watchouts.append("Parte do corpus está passando pelo evidence/document path; monitore diferenças de parsing e grounding em relação ao caminho padrão.")
    if diagnostic_watchouts:
        render_message_list(diagnostic_watchouts, level="info")

    st.write(
        {
            "vector_backend_status": vector_backend_status.get("status"),
            "vector_backend_message": vector_backend_status.get("message"),
            "estrategias_pdf_observadas": strategy_counts,
            "ocr_backends_observados": ocr_backend_counts,
        }
    )
    st.dataframe(
        compact_rows(
            pdf_rows,
            field_limits={
                "arquivo": 56,
                "estrategia_pdf": 40,
                "ocr_backend": 28,
                "evidence_path": 40,
                "vl_decision": 28,
            },
        ),
        width="stretch",
    )