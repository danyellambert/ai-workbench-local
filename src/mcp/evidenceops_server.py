from __future__ import annotations

import json
import os
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .jsonrpc_stdio import (
    MCP_PROTOCOL_VERSION,
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    build_error_response,
    build_success_response,
    read_message,
    sanitize_json_like,
    write_message,
)
from ..services.evidenceops_local_ops import (
    compare_evidenceops_repository_state,
    get_evidenceops_repository_document,
    list_evidenceops_action_items,
    list_evidenceops_repository_entries,
    register_evidenceops_entry,
    search_evidenceops_repository_entries,
    summarize_evidenceops_action_items,
    summarize_evidenceops_repository_entries,
    summarize_evidenceops_worklog_entries,
    update_evidenceops_action_item,
)


SERVER_NAME = "evidenceops-local-mcp"
SERVER_VERSION = "0.1.0"


@dataclass(frozen=True)
class EvidenceOpsPaths:
    repository_root: Path
    repository_snapshot_path: Path
    action_store_path: Path
    worklog_path: Path
    repository_backend: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_evidenceops_paths() -> EvidenceOpsPaths:
    project_root = _project_root()
    repository_backend = os.getenv("EVIDENCEOPS_REPOSITORY_BACKEND", "local").strip().lower() or "local"
    repository_root = Path(
        os.getenv(
            "EVIDENCEOPS_REPOSITORY_ROOT",
            str(project_root / "data" / "corpus_revisado" / "option_b_synthetic_premium"),
        )
    )
    repository_snapshot_path = Path(
        os.getenv(
            "EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH",
            str(repository_root / ".phase95_evidenceops_repository_snapshot.json"),
        )
    )
    action_store_path = Path(
        os.getenv(
            "EVIDENCEOPS_ACTION_STORE_PATH",
            str(project_root / ".phase95_evidenceops_actions.sqlite3"),
        )
    )
    worklog_path = Path(
        os.getenv(
            "EVIDENCEOPS_WORKLOG_PATH",
            str(project_root / ".phase95_evidenceops_worklog.json"),
        )
    )
    return EvidenceOpsPaths(
        repository_root=repository_root,
        repository_snapshot_path=repository_snapshot_path,
        action_store_path=action_store_path,
        worklog_path=worklog_path,
        repository_backend=repository_backend,
    )


class EvidenceOpsMcpServer:
    def __init__(self, *, paths: EvidenceOpsPaths | None = None) -> None:
        self.paths = paths or resolve_evidenceops_paths()
        self.tool_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "list_documents": self._tool_list_documents,
            "search_documents": self._tool_search_documents,
            "get_document": self._tool_get_document,
            "summarize_repository": self._tool_summarize_repository,
            "compare_repository_state": self._tool_compare_repository_state,
            "register_evidenceops_entry": self._tool_register_evidenceops_entry,
            "list_actions": self._tool_list_actions,
            "summarize_actions": self._tool_summarize_actions,
            "update_action": self._tool_update_action,
            "summarize_worklog": self._tool_summarize_worklog,
        }
        self.resource_handlers: dict[str, Callable[[], Any]] = {
            "evidenceops://repository/summary": self._resource_repository_summary,
            "evidenceops://repository/drift": self._resource_repository_drift,
            "evidenceops://actions/summary": self._resource_actions_summary,
            "evidenceops://worklog/summary": self._resource_worklog_summary,
        }

    def run(self) -> None:
        while True:
            try:
                message = read_message(os.sys.stdin)
            except json.JSONDecodeError as error:
                write_message(
                    os.sys.stdout,
                    build_error_response(
                        None,
                        code=JSONRPC_INVALID_REQUEST,
                        message="Invalid JSON payload.",
                        data={"error": str(error)},
                    ),
                )
                continue

            if message is None:
                break
            response = self.handle_message(message)
            if response is not None:
                write_message(os.sys.stdout, response)

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        message_id = message.get("id")
        if message.get("jsonrpc") != "2.0":
            return build_error_response(
                message_id,
                code=JSONRPC_INVALID_REQUEST,
                message="Only JSON-RPC 2.0 is supported.",
            )

        method = str(message.get("method") or "").strip()
        params = message.get("params") if isinstance(message.get("params"), dict) else {}

        if method == "initialize":
            return build_success_response(
                message_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False},
                    },
                },
            )

        if method == "notifications/initialized":
            return None

        if method == "ping":
            return build_success_response(message_id, {})

        if method == "tools/list":
            return build_success_response(message_id, {"tools": self._build_tool_descriptors()})

        if method == "tools/call":
            return self._handle_tool_call(message_id, params)

        if method == "resources/list":
            return build_success_response(message_id, {"resources": self._build_resource_descriptors()})

        if method == "resources/read":
            return self._handle_resource_read(message_id, params)

        return build_error_response(
            message_id,
            code=JSONRPC_METHOD_NOT_FOUND,
            message=f"Unknown method: {method}",
        )

    def _build_tool_descriptors(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "list_documents",
                "description": "Lista documentos do repository EvidenceOps local com filtros opcionais.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "category": {"type": "string"},
                        "suffix": {"type": "string"},
                        "document_id": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                },
            },
            {
                "name": "search_documents",
                "description": "Busca documentos do repository com scoring local por múltiplos termos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "category": {"type": "string"},
                        "suffix": {"type": "string"},
                        "document_id": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_document",
                "description": "Resolve um documento específico por document_id ou relative_path.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string"},
                        "relative_path": {"type": "string"},
                    },
                },
            },
            {
                "name": "summarize_repository",
                "description": "Retorna o resumo agregado do repository local.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "suffix": {"type": "string"},
                        "document_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "compare_repository_state",
                "description": "Compara o estado atual do repository contra o último snapshot persistido e detecta drift.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "register_evidenceops_entry",
                "description": "Registra uma entrada no worklog e materializa ações derivadas no action store via MCP.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entry": {"type": "object"},
                    },
                    "required": ["entry"],
                },
            },
            {
                "name": "list_actions",
                "description": "Lista ações do action store local com filtros opcionais.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "owner": {"type": "string"},
                        "review_type": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                },
            },
            {
                "name": "summarize_actions",
                "description": "Retorna o resumo agregado do action store local.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1},
                    },
                },
            },
            {
                "name": "update_action",
                "description": "Atualiza uma ação do action store local, com aprovação obrigatória para updates sensíveis.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action_id": {"type": "integer", "minimum": 1},
                        "status": {"type": "string"},
                        "owner": {"type": "string"},
                        "due_date": {"type": "string"},
                        "metadata_patch": {"type": "object"},
                        "approval_status": {"type": "string"},
                        "approval_reason": {"type": "string"},
                        "approved_by": {"type": "string"},
                    },
                    "required": ["action_id"],
                },
            },
            {
                "name": "summarize_worklog",
                "description": "Retorna o resumo agregado do worklog local do EvidenceOps.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def _build_resource_descriptors(self) -> list[dict[str, Any]]:
        return [
            {
                "uri": uri,
                "name": uri.rsplit("/", 1)[-1],
                "mimeType": "application/json",
                "description": description,
            }
            for uri, description in [
                ("evidenceops://repository/summary", "Resumo agregado do repository local."),
                ("evidenceops://repository/drift", "Último resumo de drift do repository local."),
                ("evidenceops://actions/summary", "Resumo agregado do action store local."),
                ("evidenceops://worklog/summary", "Resumo agregado do worklog local."),
            ]
        ]

    def _handle_tool_call(self, message_id: object, params: dict[str, Any]) -> dict[str, Any]:
        tool_name = str(params.get("name") or "").strip()
        if not tool_name:
            return build_error_response(
                message_id,
                code=JSONRPC_INVALID_PARAMS,
                message="Tool name is required.",
            )
        handler = self.tool_handlers.get(tool_name)
        if handler is None:
            return build_error_response(
                message_id,
                code=JSONRPC_METHOD_NOT_FOUND,
                message=f"Unknown tool: {tool_name}",
            )
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        try:
            result = handler(arguments)
            serialized_result = sanitize_json_like(result)
            return build_success_response(
                message_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(serialized_result, ensure_ascii=False, indent=2),
                        }
                    ],
                    "structuredContent": serialized_result,
                    "isError": False,
                },
            )
        except ValueError as error:
            return build_error_response(
                message_id,
                code=JSONRPC_INVALID_PARAMS,
                message=str(error),
            )
        except PermissionError as error:
            return build_success_response(
                message_id,
                {
                    "content": [{"type": "text", "text": str(error)}],
                    "isError": True,
                },
            )
        except Exception as error:  # pragma: no cover - defensive fallback
            return build_error_response(
                message_id,
                code=JSONRPC_INTERNAL_ERROR,
                message="Unexpected server error.",
                data={"error": str(error), "traceback": traceback.format_exc()},
            )

    def _handle_resource_read(self, message_id: object, params: dict[str, Any]) -> dict[str, Any]:
        resource_uri = str(params.get("uri") or "").strip()
        if not resource_uri:
            return build_error_response(
                message_id,
                code=JSONRPC_INVALID_PARAMS,
                message="Resource uri is required.",
            )
        handler = self.resource_handlers.get(resource_uri)
        if handler is None:
            return build_error_response(
                message_id,
                code=JSONRPC_METHOD_NOT_FOUND,
                message=f"Unknown resource: {resource_uri}",
            )
        payload = sanitize_json_like(handler())
        return build_success_response(
            message_id,
            {
                "contents": [
                    {
                        "uri": resource_uri,
                        "mimeType": "application/json",
                        "text": json.dumps(payload, ensure_ascii=False, indent=2),
                    }
                ]
            },
        )

    def _tool_list_documents(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        return list_evidenceops_repository_entries(
            self.paths.repository_root,
            query=_optional_str(arguments, "query"),
            category=_optional_str(arguments, "category"),
            suffix=_optional_str(arguments, "suffix"),
            document_id=_optional_str(arguments, "document_id"),
            limit=_optional_int(arguments, "limit"),
            repository_backend=self.paths.repository_backend,
        )

    def _tool_search_documents(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        query = _required_str(arguments, "query")
        return search_evidenceops_repository_entries(
            self.paths.repository_root,
            query=query,
            category=_optional_str(arguments, "category"),
            suffix=_optional_str(arguments, "suffix"),
            document_id=_optional_str(arguments, "document_id"),
            limit=_optional_int(arguments, "limit"),
            repository_backend=self.paths.repository_backend,
        )

    def _tool_get_document(self, arguments: dict[str, Any]) -> dict[str, Any] | None:
        relative_path = _optional_str(arguments, "relative_path")
        document_id = _optional_str(arguments, "document_id")
        if not relative_path and not document_id:
            raise ValueError("Either 'relative_path' or 'document_id' must be provided.")
        return get_evidenceops_repository_document(
            self.paths.repository_root,
            relative_path=relative_path,
            document_id=document_id,
            repository_backend=self.paths.repository_backend,
        )

    def _tool_summarize_repository(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return summarize_evidenceops_repository_entries(
            self.paths.repository_root,
            category=_optional_str(arguments, "category"),
            suffix=_optional_str(arguments, "suffix"),
            document_id=_optional_str(arguments, "document_id"),
            repository_backend=self.paths.repository_backend,
        )

    def _tool_compare_repository_state(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return compare_evidenceops_repository_state(
            self.paths.repository_root,
            snapshot_path=self.paths.repository_snapshot_path,
            repository_backend=self.paths.repository_backend,
        )

    def _tool_list_actions(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        return list_evidenceops_action_items(
            self.paths.action_store_path,
            status=_optional_str(arguments, "status"),
            owner=_optional_str(arguments, "owner"),
            review_type=_optional_str(arguments, "review_type"),
            limit=_optional_int(arguments, "limit"),
        )

    def _tool_register_evidenceops_entry(self, arguments: dict[str, Any]) -> dict[str, Any]:
        entry = arguments.get("entry")
        if not isinstance(entry, dict):
            raise ValueError("'entry' must be a dictionary.")
        return register_evidenceops_entry(
            self.paths.worklog_path,
            self.paths.action_store_path,
            entry=entry,
        )

    def _tool_summarize_actions(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return summarize_evidenceops_action_items(
            self.paths.action_store_path,
            limit=_optional_int(arguments, "limit"),
        )

    def _tool_update_action(self, arguments: dict[str, Any]) -> dict[str, Any] | None:
        action_id = _required_int(arguments, "action_id")
        metadata_patch = arguments.get("metadata_patch") if isinstance(arguments.get("metadata_patch"), dict) else None
        return update_evidenceops_action_item(
            self.paths.action_store_path,
            action_id=action_id,
            status=_optional_str(arguments, "status"),
            owner=_optional_str(arguments, "owner"),
            due_date=_optional_str(arguments, "due_date"),
            metadata_patch=metadata_patch,
            approval_status=_optional_str(arguments, "approval_status"),
            approval_reason=_optional_str(arguments, "approval_reason"),
            approved_by=_optional_str(arguments, "approved_by"),
        )

    def _tool_summarize_worklog(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return summarize_evidenceops_worklog_entries(self.paths.worklog_path)

    def _resource_repository_summary(self) -> dict[str, Any]:
        return self._tool_summarize_repository({})

    def _resource_repository_drift(self) -> dict[str, Any]:
        return self._tool_compare_repository_state({})

    def _resource_actions_summary(self) -> dict[str, Any]:
        return self._tool_summarize_actions({})

    def _resource_worklog_summary(self) -> dict[str, Any]:
        return self._tool_summarize_worklog({})


def _optional_str(arguments: dict[str, Any], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _required_str(arguments: dict[str, Any], key: str) -> str:
    value = _optional_str(arguments, key)
    if not value:
        raise ValueError(f"'{key}' is required.")
    return value


def _optional_int(arguments: dict[str, Any], key: str) -> int | None:
    value = arguments.get(key)
    if value is None or value == "":
        return None
    return int(value)


def _required_int(arguments: dict[str, Any], key: str) -> int:
    value = _optional_int(arguments, key)
    if value is None:
        raise ValueError(f"'{key}' is required.")
    return value


def main() -> None:
    EvidenceOpsMcpServer().run()


if __name__ == "__main__":
    main()