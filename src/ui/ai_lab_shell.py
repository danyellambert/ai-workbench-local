from __future__ import annotations

import streamlit as st

from .ai_lab_common import render_status_badges


AI_LAB_TAB_SPECS: list[dict[str, str]] = [
    {
        "key": "overview",
        "label": "🧭 Visão do Lab",
        "title": "Visão do Lab",
        "description": "Cockpit executivo do AI Lab com saúde, alertas e próximo foco operacional.",
        "operator_question": "O que exige atenção agora no sistema e qual deve ser a próxima ação de engenharia?",
        "console_stage": "Comando & triagem",
        "related_tabs": "Runtime & Observabilidade · Evals & Diagnóstico · EvidenceOps / MCP",
    },
    {
        "key": "runtime",
        "label": "📡 Runtime & Observabilidade",
        "title": "Runtime & Observabilidade",
        "description": "Base documental, ingestão, indexação, compatibilidade vetorial e sinais operacionais do runtime.",
        "operator_question": "O runtime, o índice e o pipeline documental estão saudáveis, confiáveis e economicamente controlados?",
        "console_stage": "Saúde operacional",
        "related_tabs": "Visão do Lab · Experimentos de Chat e Documentos · Evals & Diagnóstico",
    },
    {
        "key": "chat",
        "label": "💬 Experimentos de Chat e Documentos",
        "title": "Experimentos de Chat e Documentos",
        "description": "Chat com RAG tratado como superfície experimental e diagnóstica.",
        "operator_question": "O chat experimental está gerando grounding útil ou apenas custo, ruído e contexto mal aproveitado?",
        "console_stage": "Exploração guiada",
        "related_tabs": "Runtime & Observabilidade · Inspector de Workflow & Structured",
    },
    {
        "key": "workflow_inspector",
        "label": "🧠 Inspector de Workflow & Structured",
        "title": "Inspector de Workflow & Structured",
        "description": "Structured outputs, histórico de direct vs LangGraph e inspeção do Document Operations Copilot.",
        "operator_question": "Por que o workflow escolheu esta rota, quais guardrails dispararam e o que está gerando `needs_review`?",
        "console_stage": "Execução & guardrails",
        "related_tabs": "Experimentos de Chat e Documentos · Runtime & Observabilidade · Evals & Diagnóstico",
    },
    {
        "key": "benchmarks",
        "label": "⚖️ Benchmarks & Comparação de Modelos",
        "title": "Benchmarks & Comparação de Modelos",
        "description": "Comparação entre modelos/providers, leaderboards e deck exports do AI Lab.",
        "operator_question": "Qual provider/modelo é o default recomendado hoje para cada caso de uso e qual é a melhor alternativa?",
        "console_stage": "Decisão de stack",
        "related_tabs": "Evals & Diagnóstico · Runtime & Observabilidade · Experimentos Avançados & Artefatos",
    },
    {
        "key": "evals",
        "label": "📈 Evals & Diagnóstico",
        "title": "Evals & Diagnóstico",
        "description": "Suites, tendências pass/warn/fail e leitura operacional da qualidade.",
        "operator_question": "Onde a qualidade regrediu, o que mudou recentemente e qual task merece intervenção imediata?",
        "console_stage": "Controle de regressão",
        "related_tabs": "Benchmarks & Comparação de Modelos · Runtime & Observabilidade · Inspector de Workflow & Structured",
    },
    {
        "key": "advanced",
        "label": "🧪 Experimentos Avançados & Artefatos",
        "title": "Experimentos Avançados & Artefatos",
        "description": "OCR/VLM diagnostics, benchmark artifacts e explorador de relatórios versionados.",
        "operator_question": "Quais experimentos e artefatos explicam o comportamento atual do sistema e onde está a evidência técnica relevante?",
        "console_stage": "Evidência & rastreabilidade",
        "related_tabs": "Benchmarks & Comparação de Modelos · Evals & Diagnóstico · EvidenceOps / MCP",
    },
    {
        "key": "evidenceops",
        "label": "🧾 EvidenceOps / MCP",
        "title": "EvidenceOps / MCP",
        "description": "Console operacional de MCP, worklogs, action store e integrações avançadas.",
        "operator_question": "O fluxo MCP/EvidenceOps está saudável, governável e pronto para operação local/externa?",
        "console_stage": "Governança & operações",
        "related_tabs": "Visão do Lab · Runtime & Observabilidade · Experimentos Avançados & Artefatos",
    },
]


def build_ai_lab_tab_labels() -> list[str]:
    return [item["label"] for item in AI_LAB_TAB_SPECS]


def build_ai_lab_tab_specs_by_key() -> dict[str, dict[str, str]]:
    return {item["key"]: item for item in AI_LAB_TAB_SPECS}


def render_ai_lab_shell_banner() -> None:
    st.markdown("### Split oficial da superfície")
    st.markdown("#### Produto oficial em Gradio")
    col_1, col_2 = st.columns(2)
    with col_1:
        st.info(
            "**Você está no AI Lab em Streamlit**\n\n"
            "Use esta superfície para benchmark, evals, observabilidade, tracing, MCP, runtime economics, OCR/VLM diagnostics e experimentação controlada. "
            "Esta não é a homepage de produto do ecossistema."
        )
    with col_2:
        st.success(
            "**Produto oficial em Gradio**\n\n"
            "Os workflows de negócio, findings, recomendações, handoff e ações finais ficam concentrados na leitura de produto: `Decision workflows grounded in documents`."
        )
    st.caption(
        "Mapa oficial do AI Lab: "
        + " → ".join(item["title"] for item in AI_LAB_TAB_SPECS)
    )
    st.caption(
        "Decision gate atual do split: manter o Streamlit atual como AI Lab continua suficiente nesta fase; um novo app Streamlit dedicado só passa a fazer sentido se a superfície de engenharia crescer além do shell atual."
    )
    st.caption(
        "Leitura operacional desta rodada: o Streamlit deve evoluir como `AI Engineering Operating Console`, priorizando observability, reliability, quality control e decisões de engenharia antes do drilldown bruto."
    )


def render_ai_lab_tab_intro(tab_key: str) -> None:
    spec = build_ai_lab_tab_specs_by_key().get(tab_key)
    if not spec:
        return
    st.markdown(f"### {spec['title']}")
    st.caption(spec["description"])
    render_status_badges(
        [
            (str(spec.get("console_stage") or "AI Lab"), "info"),
            ("resumo primeiro", "healthy"),
            ("drilldown depois", "neutral"),
        ]
    )
    operator_question = str(spec.get("operator_question") or "").strip()
    if operator_question:
        st.markdown(f"**Pergunta operacional desta aba:** {operator_question}")
    related_tabs = str(spec.get("related_tabs") or "").strip()
    if related_tabs:
        st.caption(f"Conexões principais desta leitura: {related_tabs}")
    st.caption(
        "Modelo mental do console: comando → saúde operacional → exploração guiada → execução & guardrails → decisão de stack → controle de regressão → evidência → governança."
    )