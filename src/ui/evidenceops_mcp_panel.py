from __future__ import annotations

from typing import Any

import streamlit as st

from src.services.app_errors import build_ui_error_message
from src.services.evidenceops_external_targets import (
    build_external_targets_status,
    build_notion_storyline_register_entries,
    build_phase95_corpus_mapping,
    build_trello_storyline_cards,
    list_nextcloud_repository_documents,
    sync_phase95_corpus_to_nextcloud,
)
from src.services.evidenceops_mcp_client import (
    EvidenceOpsMcpClient,
    EvidenceOpsMcpClientError,
    register_evidenceops_entry_via_mcp,
    update_evidenceops_action_via_mcp,
)


def render_evidenceops_mcp_panel(
    *,
    console_state_key: str,
    last_mcp_entry: Any,
    last_mcp_register_result: Any,
    last_mcp_telemetry: Any,
) -> None:
    st.caption("5. Operar a vertical EvidenceOps via MCP real dentro do app, sem depender do Cline como cliente.")
    st.info(
        "Este painel usa o cliente MCP do próprio projeto para conversar com o servidor local do EvidenceOps. "
        "Ele serve como demo end-to-end do fluxo repository + worklog + action store via MCP."
    )
    external_status = build_external_targets_status()
    corpus_mapping = build_phase95_corpus_mapping().to_dict()

    console_state = st.session_state.get(console_state_key)
    if not isinstance(console_state, dict):
        console_state = {}
        st.session_state[console_state_key] = console_state

    with st.expander("Último register automático do Document Operations Copilot", expanded=False):
        if last_mcp_entry:
            st.write(
                {
                    "registered_entry": last_mcp_entry,
                    "register_result": last_mcp_register_result,
                    "telemetry": last_mcp_telemetry,
                }
            )
        else:
            st.caption("Nenhuma execução recente do `document_agent` registrou EvidenceOps via MCP ainda.")

    with st.expander("Arquitetura externa alvo · Nextcloud + Trello + Notion", expanded=False):
        st.write(external_status)
        st.caption("`option_b_synthetic_premium` é o corpus principal oficial da demo 9.5. `option_a_public_corpus_v2` fica como corpus complementar/canônico.")
        st.write(corpus_mapping)

    col_a, col_b, col_c, col_d = st.columns(4)
    if col_a.button("Listar tools MCP", key="phase95_mcp_list_tools"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["tools"] = mcp_client.list_tools()
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Falha ao listar tools do MCP", error))
    if col_b.button("Resumo repository", key="phase95_mcp_repository_summary"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["repository_summary"] = mcp_client.read_resource("evidenceops://repository/summary")
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Falha ao ler summary do repository via MCP", error))
    if col_c.button("Drift repository", key="phase95_mcp_repository_drift"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["repository_drift"] = mcp_client.call_tool("compare_repository_state", {})
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Falha ao comparar drift do repository via MCP", error))
    if col_d.button("Listar open actions", key="phase95_mcp_list_actions"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["open_actions"] = mcp_client.call_tool("list_actions", {"status": "open"})
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Falha ao listar actions via MCP", error))

    external_col_1, external_col_2, external_col_3 = st.columns(3)
    if external_col_1.button("Planejar sync corpus -> Nextcloud", key="phase95_external_nextcloud_dry_run"):
        console_state["nextcloud_plan"] = sync_phase95_corpus_to_nextcloud(dry_run=True)
        st.session_state[console_state_key] = console_state
    if external_col_2.button("Planejar storylines -> Trello", key="phase95_external_trello_dry_run"):
        console_state["trello_plan"] = build_trello_storyline_cards(dry_run=True)
        st.session_state[console_state_key] = console_state
    if external_col_3.button("Planejar register -> Notion", key="phase95_external_notion_dry_run"):
        console_state["notion_plan"] = build_notion_storyline_register_entries(dry_run=True)
        st.session_state[console_state_key] = console_state

    remote_col_1, remote_col_2 = st.columns(2)
    if remote_col_1.button("Executar sync real -> Nextcloud", key="phase95_external_nextcloud_real_sync"):
        try:
            console_state["nextcloud_sync_result"] = sync_phase95_corpus_to_nextcloud(dry_run=False)
            st.session_state[console_state_key] = console_state
            st.success("Sync real para Nextcloud executado com sucesso.")
        except Exception as error:  # pragma: no cover - UI defensive handling
            st.error(build_ui_error_message("Falha ao executar sync real para o Nextcloud", error))
    if remote_col_2.button("Listar repository remoto (Nextcloud)", key="phase95_external_nextcloud_list_remote"):
        try:
            console_state["nextcloud_remote_documents"] = list_nextcloud_repository_documents(limit=25)
            st.session_state[console_state_key] = console_state
        except Exception as error:  # pragma: no cover - UI defensive handling
            st.error(build_ui_error_message("Falha ao listar documentos remotos do Nextcloud", error))

    search_query = st.text_input(
        "Buscar documentos via MCP",
        value=str(console_state.get("search_query") or ""),
        key="phase95_mcp_search_query",
        placeholder="Ex.: master services, policy, contract, POL-001",
    )
    if st.button("Executar busca documental via MCP", key="phase95_mcp_search_documents"):
        console_state["search_query"] = search_query
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["search_results"] = mcp_client.call_tool(
                    "search_documents",
                    {"query": search_query, "limit": 10},
                )
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Falha ao buscar documentos via MCP", error))

    with st.form("phase95_mcp_update_action_form", clear_on_submit=False):
        st.markdown("### Aprovar / atualizar ação via MCP")
        action_id_value = st.number_input(
            "Action ID",
            min_value=1,
            step=1,
            value=1,
            key="phase95_mcp_action_id_input",
        )
        action_status_value = st.selectbox(
            "Novo status",
            options=["open", "in_progress", "pending", "closed"],
            index=3,
            key="phase95_mcp_action_status_input",
        )
        approval_reason_value = st.text_input(
            "Motivo da aprovação",
            value="Encerramento validado manualmente.",
            key="phase95_mcp_approval_reason_input",
        )
        approved_by_value = st.text_input(
            "Aprovado por",
            value="manager",
            key="phase95_mcp_approved_by_input",
        )
        update_action_submitted = st.form_submit_button("Atualizar action via MCP", width="stretch")

        if update_action_submitted:
            try:
                update_result, update_telemetry = update_evidenceops_action_via_mcp(
                    action_id=int(action_id_value),
                    status=action_status_value,
                    approval_status="approved",
                    approval_reason=approval_reason_value,
                    approved_by=approved_by_value,
                )
                console_state["updated_action"] = update_result
                console_state["telemetry"] = update_telemetry
                st.session_state[console_state_key] = console_state
                st.success("Action atualizada via MCP com sucesso.")
            except EvidenceOpsMcpClientError as error:
                st.error(build_ui_error_message("Falha ao atualizar action via MCP", error))

    if last_mcp_entry and st.button("Reenviar última entrada do agente via MCP", key="phase95_mcp_reregister_last_entry"):
        try:
            register_result, register_telemetry = register_evidenceops_entry_via_mcp(last_mcp_entry)
            console_state["reregistered_entry"] = register_result
            console_state["telemetry"] = register_telemetry
            st.session_state[console_state_key] = console_state
            st.success("Última entrada do agente reenviada ao MCP com sucesso.")
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Falha ao reenviar entrada via MCP", error))

    if console_state:
        with st.expander("Console MCP · último estado", expanded=True):
            for label, field_name in [
                ("Tools disponíveis", "tools"),
                ("Resumo do repository", "repository_summary"),
                ("Drift do repository", "repository_drift"),
                ("Resultados da busca", "search_results"),
                ("Open actions", "open_actions"),
                ("Último update de action", "updated_action"),
                ("Último reenvio de entry", "reregistered_entry"),
                ("Plano de sync -> Nextcloud", "nextcloud_plan"),
                ("Resultado do sync real -> Nextcloud", "nextcloud_sync_result"),
                ("Repository remoto -> Nextcloud", "nextcloud_remote_documents"),
                ("Plano de storylines -> Trello", "trello_plan"),
                ("Plano de register -> Notion", "notion_plan"),
            ]:
                value = console_state.get(field_name)
                if value:
                    st.caption(label)
                    st.write(value)
            telemetry_value = console_state.get("telemetry")
            if telemetry_value:
                st.caption("Telemetria do cliente MCP")
                st.write(telemetry_value)