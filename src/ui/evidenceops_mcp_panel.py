from __future__ import annotations

from datetime import date, datetime
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
from src.storage.phase95_evidenceops_action_store import summarize_evidenceops_actions

from .ai_lab_common import (
    compact_rows,
    render_bar_chart_from_rows,
    render_labeled_value_grid,
    render_message_list,
    render_panel_header,
    render_status_badges,
)


def _collection_size(value: Any) -> int | None:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for field_name in [
            "tools",
            "actions",
            "results",
            "documents",
            "planned_uploads",
            "planned_cards",
            "planned_pages",
            "created_cards",
            "created_pages",
            "synced",
        ]:
            field_value = value.get(field_name)
            if isinstance(field_value, list):
                return len(field_value)
    return None


def _record_console_operation(console_state: dict[str, Any], *, action_name: str, status: str, detail: str) -> None:
    history = console_state.get("operation_history") if isinstance(console_state.get("operation_history"), list) else []
    history.append(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action_name,
            "status": status,
            "detail": detail,
        }
    )
    console_state["operation_history"] = history[-25:]


def _latest_operation_by_status(console_state: dict[str, Any], status: str) -> dict[str, Any] | None:
    history = console_state.get("operation_history") if isinstance(console_state.get("operation_history"), list) else []
    for entry in reversed(history):
        if isinstance(entry, dict) and str(entry.get("status") or "") == status:
            return entry
    return None


def _build_external_readiness_rows(external_status: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field_name, label in [("nextcloud", "Nextcloud"), ("trello", "Trello"), ("notion", "Notion")]:
        payload = external_status.get(field_name) if isinstance(external_status.get(field_name), dict) else {}
        rows.append(
            {
                "target": label,
                "configured": bool(payload.get("configured")),
                "missing": ", ".join(payload.get("missing") or []) if isinstance(payload.get("missing"), list) else "",
            }
        )
    return rows


def _build_console_status_badges(
    *,
    telemetry_status: str,
    configured_targets: int,
    latest_failure: dict[str, Any] | None,
) -> list[tuple[str, str]]:
    return [
        (f"MCP {telemetry_status}", "critical" if telemetry_status == "error" else "healthy" if telemetry_status == "success" else "neutral"),
        (f"targets {configured_targets}/3", "attention" if configured_targets < 3 else "healthy"),
        ("última falha presente" if isinstance(latest_failure, dict) else "sem falha recente", "attention" if isinstance(latest_failure, dict) else "healthy"),
    ]


def _build_operation_history_rows(console_state: dict[str, Any]) -> list[dict[str, Any]]:
    history = console_state.get("operation_history") if isinstance(console_state.get("operation_history"), list) else []
    status_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for entry in history:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "unknown")
        action = str(entry.get("action") or "unknown")
        status_counts[status] = int(status_counts.get(status, 0)) + 1
        action_counts[action] = int(action_counts.get(action, 0)) + 1
    return [
        {"status": key, "count": value} for key, value in status_counts.items()
    ], [
        {"action": key, "count": value} for key, value in action_counts.items()
    ]


def _build_action_distribution_rows(open_actions: Any) -> list[dict[str, Any]]:
    actions = open_actions.get("actions") if isinstance(open_actions, dict) else open_actions if isinstance(open_actions, list) else []
    status_counts: dict[str, int] = {}
    for action in actions:
        if not isinstance(action, dict):
            continue
        status = str(action.get("status") or "unknown")
        status_counts[status] = int(status_counts.get(status, 0)) + 1
    return [{"status": key, "count": value} for key, value in status_counts.items()]


def _build_action_owner_rows(action_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = summarize_evidenceops_actions(action_entries)
    owner_counts = summary.get("owner_counts") if isinstance(summary.get("owner_counts"), dict) else {}
    return [
        {"owner": str(owner or "Não atribuído"), "count": int(count)}
        for owner, count in owner_counts.items()
    ]


def _build_action_due_bucket_rows(action_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = date.today()
    buckets = {
        "Atrasadas": 0,
        "Até 7 dias": 0,
        "Até 30 dias": 0,
        "Sem prazo": 0,
    }
    for entry in action_entries:
        due_date_raw = str(entry.get("due_date") or "").strip()
        if not due_date_raw:
            buckets["Sem prazo"] += 1
            continue
        try:
            due_value = date.fromisoformat(due_date_raw)
        except ValueError:
            buckets["Sem prazo"] += 1
            continue
        delta_days = (due_value - today).days
        if delta_days < 0:
            buckets["Atrasadas"] += 1
        elif delta_days <= 7:
            buckets["Até 7 dias"] += 1
        else:
            buckets["Até 30 dias"] += 1
    return [{"due_bucket": bucket, "count": count} for bucket, count in buckets.items()]


def _build_operation_timeline_rows(console_state: dict[str, Any]) -> list[dict[str, Any]]:
    history = console_state.get("operation_history") if isinstance(console_state.get("operation_history"), list) else []
    rows: list[dict[str, Any]] = []
    for entry in reversed(history[-12:]):
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "unknown")
        rows.append(
            {
                "timestamp": str(entry.get("timestamp") or "n/a"),
                "action": str(entry.get("action") or "unknown"),
                "status": status,
                "highlight": "🔴 falha" if status == "error" else "🟢 ok" if status == "success" else "⚪ evento",
                "detail": str(entry.get("detail") or ""),
            }
        )
    return rows


def render_evidenceops_mcp_panel(
    *,
    console_state_key: str,
    last_mcp_entry: Any,
    last_mcp_register_result: Any,
    last_mcp_telemetry: Any,
    action_store_entries: Any = None,
) -> None:
    render_panel_header(
        "EvidenceOps / MCP",
        "Opere a vertical EvidenceOps por um fluxo MCP real dentro do app, usando o cliente MCP do próprio projeto como console operacional do AI Lab.",
    )
    external_status = build_external_targets_status()
    corpus_mapping = build_phase95_corpus_mapping().to_dict()

    console_state = st.session_state.get(console_state_key)
    if not isinstance(console_state, dict):
        console_state = {}
        st.session_state[console_state_key] = console_state

    telemetry_snapshot = last_mcp_telemetry if isinstance(last_mcp_telemetry, dict) else (console_state.get("telemetry") if isinstance(console_state.get("telemetry"), dict) else {})
    telemetry_status = str(telemetry_snapshot.get("status") or "idle")
    action_store_entries = action_store_entries if isinstance(action_store_entries, list) else []
    action_store_summary = summarize_evidenceops_actions(action_store_entries)
    latest_success = _latest_operation_by_status(console_state, "success")
    latest_failure = _latest_operation_by_status(console_state, "error")
    configured_targets = sum(
        1
        for field_name in ["nextcloud", "trello", "notion"]
        if isinstance(external_status.get(field_name), dict) and bool(external_status[field_name].get("configured"))
    )
    render_panel_header(
        "Resumo de saúde",
        "Resumo rápido do cliente MCP, do estado atual do console e do readiness das integrações externas.",
    )
    render_labeled_value_grid(
        [
            {"label": "MCP status", "value": telemetry_status},
            {"label": "Tool calls", "value": int(telemetry_snapshot.get("tool_call_count") or 0)},
            {"label": "Erro MCP", "value": int(telemetry_snapshot.get("error_call_count") or 0)},
            {"label": "Targets configurados", "value": f"{configured_targets}/3"},
            {"label": "Latency total", "value": f"{float(telemetry_snapshot.get('total_latency_s') or 0.0):.2f}s"},
            {"label": "Open actions", "value": _collection_size(console_state.get("open_actions")) or 0},
            {"label": "Resultados de busca", "value": _collection_size(console_state.get("search_results")) or 0},
            {"label": "Ações auditáveis", "value": int(action_store_summary.get("total_actions") or 0)},
        ],
        columns=4,
    )

    render_labeled_value_grid(
        [
            {
                "label": "Última operação OK",
                "value": str(latest_success.get("action") if isinstance(latest_success, dict) else "n/a"),
                "detail": str(latest_success.get("timestamp") if isinstance(latest_success, dict) else ""),
                "compact": True,
                "show_full": True,
                "max_chars": 42,
            },
            {
                "label": "Última falha",
                "value": str(latest_failure.get("action") if isinstance(latest_failure, dict) else "n/a"),
                "detail": str(latest_failure.get("timestamp") if isinstance(latest_failure, dict) else ""),
                "compact": True,
                "show_full": True,
                "max_chars": 42,
            },
            {
                "label": "Governance status",
                "value": "🔴 Intervir" if telemetry_status == "error" or configured_targets < 3 else "🟢 Controlado",
            },
        ],
        columns=3,
    )
    render_status_badges(
        _build_console_status_badges(
            telemetry_status=telemetry_status,
            configured_targets=configured_targets,
            latest_failure=latest_failure if isinstance(latest_failure, dict) else None,
        )
    )

    health_notes: list[str] = []
    if telemetry_status == "error":
        health_notes.append("A telemetria MCP mais recente indica erro. Vale revisar a conexão com o servidor local e o resultado da última operação antes de continuar.")
    missing_targets = [
        field_name
        for field_name in ["nextcloud", "trello", "notion"]
        if isinstance(external_status.get(field_name), dict) and not bool(external_status[field_name].get("configured"))
    ]
    if missing_targets:
        health_notes.append(
            f"Integrações externas ainda incompletas: {', '.join(missing_targets)}. O console continua útil localmente, mas a leitura multi-target permanece parcial."
        )
    if health_notes:
        render_message_list(health_notes, level="info")

    render_panel_header(
        "Matriz de readiness",
        "Leia separadamente o health do cliente MCP, o readiness dos targets externos e a governança operacional do console.",
    )
    st.dataframe(
        compact_rows(
            _build_external_readiness_rows(external_status),
            field_limits={"missing": 72},
        ),
        width="stretch",
    )
    readiness_chart_rows = [
        {
            "target": str(row.get("target") or "target"),
            "configured": 1 if bool(row.get("configured")) else 0,
            "missing_count": len(str(row.get("missing") or "").split(", ")) if str(row.get("missing") or "").strip() else 0,
        }
        for row in _build_external_readiness_rows(external_status)
    ]
    readiness_col_1, readiness_col_2 = st.columns(2)
    with readiness_col_1:
        st.caption("Readiness por target")
        render_bar_chart_from_rows(
            readiness_chart_rows,
            index_field="target",
            value_fields=["configured"],
            height=220,
        )
    with readiness_col_2:
        st.caption("Campos faltantes por target")
        render_bar_chart_from_rows(
            readiness_chart_rows,
            index_field="target",
            value_fields=["missing_count"],
            height=220,
        )
    governance_notes: list[str] = []
    if isinstance(latest_success, dict):
        governance_notes.append(
            f"Último sucesso observado: `{latest_success.get('action')}` em {latest_success.get('timestamp')}.")
    if isinstance(latest_failure, dict):
        governance_notes.append(
            f"Última falha observada: `{latest_failure.get('action')}` em {latest_failure.get('timestamp')} · {latest_failure.get('detail')}.")
    if configured_targets < 3:
        governance_notes.append("O readiness externo ainda é parcial; trate Nextcloud/Trello/Notion como trilha em maturação, mantendo o baseline local auditável.")
    if governance_notes:
        render_message_list(governance_notes, level="info")

    with st.expander("Último registro automático do Document Operations Copilot", expanded=False):
        if last_mcp_entry:
            register_snapshot = {
                "status": telemetry_snapshot.get("status"),
                "tool_calls": telemetry_snapshot.get("tool_call_count"),
                "write_calls": telemetry_snapshot.get("write_call_count"),
                "error_calls": telemetry_snapshot.get("error_call_count"),
            }
            st.write(register_snapshot)
            st.write(
                {
                    "registered_entry": last_mcp_entry,
                    "register_result": last_mcp_register_result,
                    "telemetry": last_mcp_telemetry,
                }
            )
        else:
            st.caption("No recent `document_agent` execution has registered EvidenceOps through MCP yet.")

    with st.expander("Arquitetura dos targets externos · Nextcloud + Trello + Notion", expanded=False):
        status_col_1, status_col_2, status_col_3 = st.columns(3)
        for col, label, field_name in [
            (status_col_1, "Nextcloud", "nextcloud"),
            (status_col_2, "Trello", "trello"),
            (status_col_3, "Notion", "notion"),
        ]:
            target_payload = external_status.get(field_name) if isinstance(external_status.get(field_name), dict) else {}
            col.metric(label, "configured" if target_payload.get("configured") else "pending")
            if target_payload.get("missing"):
                col.caption(f"missing: {', '.join(target_payload.get('missing') or [])}")
        st.write(external_status)
        st.caption("`option_b_synthetic_premium` is the official primary corpus for the Phase 9.5 demo. `option_a_public_corpus_v2` remains the complementary/canonical corpus.")
        st.write(corpus_mapping)

    render_panel_header(
        "Operações do cliente",
        "Operações locais do cliente MCP para inspecionar tools, estado do repositório, drift e ações abertas.",
    )
    col_a, col_b, col_c, col_d = st.columns(4)
    if col_a.button("Listar tools MCP", key="phase95_mcp_list_tools"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["tools"] = mcp_client.list_tools()
                console_state["telemetry"] = mcp_client.telemetry_summary()
                _record_console_operation(console_state, action_name="list_mcp_tools", status="success", detail="Listed available MCP tools.")
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            _record_console_operation(console_state, action_name="list_mcp_tools", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to list MCP tools", error))
    if col_b.button("Resumo do repositório", key="phase95_mcp_repository_summary"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["repository_summary"] = mcp_client.read_resource("evidenceops://repository/summary")
                console_state["telemetry"] = mcp_client.telemetry_summary()
                _record_console_operation(console_state, action_name="repository_summary", status="success", detail="Read repository summary through MCP.")
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            _record_console_operation(console_state, action_name="repository_summary", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to read the repository summary through MCP", error))
    if col_c.button("Drift do repositório", key="phase95_mcp_repository_drift"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["repository_drift"] = mcp_client.call_tool("compare_repository_state", {})
                console_state["telemetry"] = mcp_client.telemetry_summary()
                _record_console_operation(console_state, action_name="repository_drift", status="success", detail="Compared repository drift through MCP.")
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            _record_console_operation(console_state, action_name="repository_drift", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to compare repository drift through MCP", error))
    if col_d.button("Listar ações abertas", key="phase95_mcp_list_actions"):
        try:
            with EvidenceOpsMcpClient() as mcp_client:
                console_state["open_actions"] = mcp_client.call_tool("list_actions", {"status": "open"})
                console_state["telemetry"] = mcp_client.telemetry_summary()
                _record_console_operation(console_state, action_name="list_open_actions", status="success", detail="Listed open actions through MCP.")
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            _record_console_operation(console_state, action_name="list_open_actions", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to list actions through MCP", error))

    render_panel_header(
        "Planejamento de readiness externo",
        "Planejamento e execução das trilhas Nextcloud, Trello e Notion para sair do console local e evoluir para governança multi-target.",
    )
    external_col_1, external_col_2, external_col_3 = st.columns(3)
    if external_col_1.button("Planejar sync do corpus -> Nextcloud", key="phase95_external_nextcloud_dry_run"):
        console_state["nextcloud_plan"] = sync_phase95_corpus_to_nextcloud(dry_run=True)
        _record_console_operation(console_state, action_name="plan_nextcloud_sync", status="success", detail="Generated Nextcloud dry-run sync plan.")
        st.session_state[console_state_key] = console_state
    if external_col_2.button("Planejar storylines -> Trello", key="phase95_external_trello_dry_run"):
        console_state["trello_plan"] = build_trello_storyline_cards(dry_run=True)
        _record_console_operation(console_state, action_name="plan_trello_storylines", status="success", detail="Generated Trello dry-run storyline plan.")
        st.session_state[console_state_key] = console_state
    if external_col_3.button("Planejar registro -> Notion", key="phase95_external_notion_dry_run"):
        console_state["notion_plan"] = build_notion_storyline_register_entries(dry_run=True)
        _record_console_operation(console_state, action_name="plan_notion_register", status="success", detail="Generated Notion dry-run register plan.")
        st.session_state[console_state_key] = console_state

    remote_col_1, remote_col_2 = st.columns(2)
    if remote_col_1.button("Executar sync real -> Nextcloud", key="phase95_external_nextcloud_real_sync"):
        try:
            console_state["nextcloud_sync_result"] = sync_phase95_corpus_to_nextcloud(dry_run=False)
            _record_console_operation(console_state, action_name="run_nextcloud_sync", status="success", detail="Executed real Nextcloud sync.")
            st.session_state[console_state_key] = console_state
            st.success("Real sync to Nextcloud completed successfully.")
        except Exception as error:  # pragma: no cover - UI defensive handling
            _record_console_operation(console_state, action_name="run_nextcloud_sync", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to run the real sync to Nextcloud", error))
    if remote_col_2.button("Listar repositório remoto (Nextcloud)", key="phase95_external_nextcloud_list_remote"):
        try:
            console_state["nextcloud_remote_documents"] = list_nextcloud_repository_documents(limit=25)
            _record_console_operation(console_state, action_name="list_nextcloud_remote_documents", status="success", detail="Listed remote Nextcloud repository documents.")
            st.session_state[console_state_key] = console_state
        except Exception as error:  # pragma: no cover - UI defensive handling
            _record_console_operation(console_state, action_name="list_nextcloud_remote_documents", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to list remote Nextcloud documents", error))

    render_panel_header(
        "Busca e inspeção",
        "Busque documentos via MCP e use o console como superfície de inspeção operacional antes de acionar governança ou sync real.",
    )
    search_query = st.text_input(
        "Buscar documentos via MCP",
        value=str(console_state.get("search_query") or ""),
        key="phase95_mcp_search_query",
        placeholder="Example: master services, policy, contract, POL-001",
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
                _record_console_operation(console_state, action_name="search_documents", status="success", detail=f"Search executed for query: {search_query}")
                st.session_state[console_state_key] = console_state
        except EvidenceOpsMcpClientError as error:
            _record_console_operation(console_state, action_name="search_documents", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to search documents through MCP", error))

    render_panel_header(
        "Ações de governança",
        "Ações sensíveis e de governança devem ficar claramente separadas da inspeção/consulta: update de action, reenvio de entry e aprovação manual.",
    )
    with st.form("phase95_mcp_update_action_form", clear_on_submit=False):
        st.markdown("### Aprovar / atualizar ação via MCP")
        action_id_value = st.number_input(
            "ID da ação",
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
            value="Closure manually validated.",
            key="phase95_mcp_approval_reason_input",
        )
        approved_by_value = st.text_input(
            "Aprovado por",
            value="manager",
            key="phase95_mcp_approved_by_input",
        )
        update_action_submitted = st.form_submit_button("Atualizar ação via MCP", width="stretch")

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
                _record_console_operation(console_state, action_name="update_action", status="success", detail=f"Updated action {int(action_id_value)} to status {action_status_value}.")
                st.session_state[console_state_key] = console_state
                st.success("Action updated through MCP successfully.")
            except EvidenceOpsMcpClientError as error:
                _record_console_operation(console_state, action_name="update_action", status="error", detail=str(error))
                st.error(build_ui_error_message("Failed to update the action through MCP", error))

    if last_mcp_entry and st.button("Reenviar a última entry do agente via MCP", key="phase95_mcp_reregister_last_entry"):
        try:
            register_result, register_telemetry = register_evidenceops_entry_via_mcp(last_mcp_entry)
            console_state["reregistered_entry"] = register_result
            console_state["telemetry"] = register_telemetry
            _record_console_operation(console_state, action_name="reregister_latest_entry", status="success", detail="Resent latest agent entry through MCP.")
            st.session_state[console_state_key] = console_state
            st.success("The latest agent entry was resent to MCP successfully.")
        except EvidenceOpsMcpClientError as error:
            _record_console_operation(console_state, action_name="reregister_latest_entry", status="error", detail=str(error))
            st.error(build_ui_error_message("Failed to resend the entry through MCP", error))

    if console_state:
        with st.expander("Console MCP · estado mais recente", expanded=False):
            console_summary = {
                "available_tools": _collection_size(console_state.get("tools")) or 0,
                "open_actions": _collection_size(console_state.get("open_actions")) or 0,
                "search_results": _collection_size(console_state.get("search_results")) or 0,
                "nextcloud_plan_uploads": _collection_size(console_state.get("nextcloud_plan")) or 0,
                "trello_plan_cards": _collection_size(console_state.get("trello_plan")) or 0,
                "notion_plan_pages": _collection_size(console_state.get("notion_plan")) or 0,
                "telemetry_status": telemetry_snapshot.get("status"),
                "last_success": latest_success,
                "last_failure": latest_failure,
            }
            st.write(console_summary)
            status_rows, action_rows = _build_operation_history_rows(console_state)
            chart_col_1, chart_col_2 = st.columns(2)
            with chart_col_1:
                st.caption("Distribuição de status das operações")
                render_bar_chart_from_rows(
                    status_rows,
                    index_field="status",
                    value_fields=["count"],
                    height=220,
                )
            with chart_col_2:
                st.caption("Distribuição por tipo de operação")
                render_bar_chart_from_rows(
                    action_rows,
                    index_field="action",
                    value_fields=["count"],
                    height=220,
                )
            action_distribution_rows = _build_action_distribution_rows(console_state.get("open_actions"))
            if action_distribution_rows:
                st.caption("Status das actions abertas")
                render_bar_chart_from_rows(
                    action_distribution_rows,
                    index_field="status",
                    value_fields=["count"],
                    height=220,
                )
            if action_store_entries:
                action_chart_col_1, action_chart_col_2 = st.columns(2)
                with action_chart_col_1:
                    st.caption("Distribuição por owner")
                    render_bar_chart_from_rows(
                        _build_action_owner_rows(action_store_entries),
                        index_field="owner",
                        value_fields=["count"],
                        height=220,
                    )
                with action_chart_col_2:
                    st.caption("Distribuição por due date")
                    render_bar_chart_from_rows(
                        _build_action_due_bucket_rows(action_store_entries),
                        index_field="due_bucket",
                        value_fields=["count"],
                        height=220,
                    )
                timeline_rows = _build_operation_timeline_rows(console_state)
                if timeline_rows:
                    st.caption("Timeline resumida das operações recentes")
                    st.dataframe(
                        compact_rows(
                            timeline_rows,
                            field_limits={"action": 36, "detail": 72},
                        ),
                        width="stretch",
                    )
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
            operation_history = console_state.get("operation_history") if isinstance(console_state.get("operation_history"), list) else []
            if operation_history:
                st.caption("Operation history")
                st.dataframe(
                    compact_rows(
                        operation_history[-10:],
                        field_limits={"action": 36, "detail": 72},
                    ),
                    width="stretch",
                )