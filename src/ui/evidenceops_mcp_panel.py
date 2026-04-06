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
    st.caption("5. Operate the EvidenceOps vertical through a real MCP flow inside the app, without depending on Cline as the client.")
    st.info(
        "This panel uses the project's own MCP client to communicate with the local EvidenceOps server. "
        "It acts as an end-to-end demo of the repository + worklog + action-store flow through MCP."
    )
    external_status = build_external_targets_status()
    corpus_mapping = build_phase95_corpus_mapping().to_dict()

    console_state = st.session_state.get(console_state_key)
    if not isinstance(console_state, dict):
        console_state = {}
        st.session_state[console_state_key] = console_state

    with st.expander("Latest automatic register from the Document Operations Copilot", expanded=False):
        if last_mcp_entry:
            st.write(
                {
                    "registered_entry": last_mcp_entry,
                    "register_result": last_mcp_register_result,
                    "telemetry": last_mcp_telemetry,
                }
            )
        else:
            st.caption("No recent `document_agent` execution has registered EvidenceOps through MCP yet.")

    with st.expander("External target architecture · Nextcloud + Trello + Notion", expanded=False):
        st.write(external_status)
        st.caption("`option_b_synthetic_premium` is the official primary corpus for the Phase 9.5 demo. `option_a_public_corpus_v2` remains the complementary/canonical corpus.")
        st.write(corpus_mapping)

    col_a, col_b, col_c, col_d = st.columns(4)
    if col_a.button("List MCP tools", key="phase95_mcp_list_tools"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["tools"] = mcp_client.list_tools()
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Failed to list MCP tools", error))
    if col_b.button("Repository summary", key="phase95_mcp_repository_summary"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["repository_summary"] = mcp_client.read_resource("evidenceops://repository/summary")
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Failed to read the repository summary through MCP", error))
    if col_c.button("Repository drift", key="phase95_mcp_repository_drift"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["repository_drift"] = mcp_client.call_tool("compare_repository_state", {})
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Failed to compare repository drift through MCP", error))
    if col_d.button("List open actions", key="phase95_mcp_list_actions"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["open_actions"] = mcp_client.call_tool("list_actions", {"status": "open"})
                console_state["telemetry"] = mcp_client.telemetry_summary()
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Failed to list actions through MCP", error))

    external_col_1, external_col_2, external_col_3 = st.columns(3)
    if external_col_1.button("Plan corpus sync -> Nextcloud", key="phase95_external_nextcloud_dry_run"):
        console_state["nextcloud_plan"] = sync_phase95_corpus_to_nextcloud(dry_run=True)
        st.session_state[console_state_key] = console_state
    if external_col_2.button("Plan storylines -> Trello", key="phase95_external_trello_dry_run"):
        console_state["trello_plan"] = build_trello_storyline_cards(dry_run=True)
        st.session_state[console_state_key] = console_state
    if external_col_3.button("Plan register -> Notion", key="phase95_external_notion_dry_run"):
        console_state["notion_plan"] = build_notion_storyline_register_entries(dry_run=True)
        st.session_state[console_state_key] = console_state

    remote_col_1, remote_col_2 = st.columns(2)
    if remote_col_1.button("Run real sync -> Nextcloud", key="phase95_external_nextcloud_real_sync"):
        try:
            console_state["nextcloud_sync_result"] = sync_phase95_corpus_to_nextcloud(dry_run=False)
            st.session_state[console_state_key] = console_state
            st.success("Real sync to Nextcloud completed successfully.")
        except Exception as error:  # pragma: no cover - UI defensive handling
            st.error(build_ui_error_message("Failed to run the real sync to Nextcloud", error))
    if remote_col_2.button("List remote repository (Nextcloud)", key="phase95_external_nextcloud_list_remote"):
        try:
            console_state["nextcloud_remote_documents"] = list_nextcloud_repository_documents(limit=25)
            st.session_state[console_state_key] = console_state
        except Exception as error:  # pragma: no cover - UI defensive handling
            st.error(build_ui_error_message("Failed to list remote Nextcloud documents", error))

    search_query = st.text_input(
        "Search documents through MCP",
        value=str(console_state.get("search_query") or ""),
        key="phase95_mcp_search_query",
        placeholder="Example: master services, policy, contract, POL-001",
    )
    if st.button("Run document search through MCP", key="phase95_mcp_search_documents"):
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
            st.error(build_ui_error_message("Failed to search documents through MCP", error))

    with st.form("phase95_mcp_update_action_form", clear_on_submit=False):
        st.markdown("### Approve / update action through MCP")
        action_id_value = st.number_input(
            "Action ID",
            min_value=1,
            step=1,
            value=1,
            key="phase95_mcp_action_id_input",
        )
        action_status_value = st.selectbox(
            "New status",
            options=["open", "in_progress", "pending", "closed"],
            index=3,
            key="phase95_mcp_action_status_input",
        )
        approval_reason_value = st.text_input(
            "Approval reason",
            value="Closure manually validated.",
            key="phase95_mcp_approval_reason_input",
        )
        approved_by_value = st.text_input(
            "Approved by",
            value="manager",
            key="phase95_mcp_approved_by_input",
        )
        update_action_submitted = st.form_submit_button("Update action through MCP", width="stretch")

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
                st.success("Action updated through MCP successfully.")
            except EvidenceOpsMcpClientError as error:
                st.error(build_ui_error_message("Failed to update the action through MCP", error))

    if last_mcp_entry and st.button("Resend the latest agent entry through MCP", key="phase95_mcp_reregister_last_entry"):
        try:
            register_result, register_telemetry = register_evidenceops_entry_via_mcp(last_mcp_entry)
            console_state["reregistered_entry"] = register_result
            console_state["telemetry"] = register_telemetry
            st.session_state[console_state_key] = console_state
            st.success("The latest agent entry was resent to MCP successfully.")
        except EvidenceOpsMcpClientError as error:
            st.error(build_ui_error_message("Failed to resend the entry through MCP", error))

    if console_state:
        with st.expander("MCP console · latest state", expanded=True):
            for label, field_name in [
                ("Available tools", "tools"),
                ("Repository summary", "repository_summary"),
                ("Repository drift", "repository_drift"),
                ("Search results", "search_results"),
                ("Open actions", "open_actions"),
                ("Latest action update", "updated_action"),
                ("Latest resent entry", "reregistered_entry"),
                ("Sync plan -> Nextcloud", "nextcloud_plan"),
                ("Real sync result -> Nextcloud", "nextcloud_sync_result"),
                ("Remote repository -> Nextcloud", "nextcloud_remote_documents"),
                ("Storyline plan -> Trello", "trello_plan"),
                ("Register plan -> Notion", "notion_plan"),
            ]:
                value = console_state.get(field_name)
                if value:
                    st.caption(label)
                    st.write(value)
            telemetry_value = console_state.get("telemetry")
            if telemetry_value:
                st.caption("MCP client telemetry")
                st.write(telemetry_value)