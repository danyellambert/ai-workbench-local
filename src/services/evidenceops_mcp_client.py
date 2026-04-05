from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path
from typing import Any

from ..mcp.jsonrpc_stdio import read_message, write_message


DEFAULT_EVIDENCEOPS_MCP_SERVER_KEY = "evidenceops_local"
DEFAULT_CLINE_MCP_SETTINGS_PATH = Path("/Users/danyellambert/.cline/data/settings/cline_mcp_settings.json")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_evidenceops_env(project_root: Path | None = None) -> dict[str, str]:
    resolved_root = project_root or _project_root()
    repository_root = resolved_root / "data" / "corpus_revisado" / "option_b_synthetic_premium"
    return {
        "EVIDENCEOPS_REPOSITORY_ROOT": str(repository_root),
        "EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH": str(repository_root / ".phase95_evidenceops_repository_snapshot.json"),
        "EVIDENCEOPS_ACTION_STORE_PATH": str(resolved_root / ".phase95_evidenceops_actions.sqlite3"),
        "EVIDENCEOPS_WORKLOG_PATH": str(resolved_root / ".phase95_evidenceops_worklog.json"),
    }


@dataclass(frozen=True)
class EvidenceOpsMcpClientConfig:
    command: str
    args: list[str]
    env: dict[str, str]
    server_name: str = "evidenceops-local-mcp"
    transport: str = "stdio"


@dataclass
class EvidenceOpsMcpTelemetry:
    server_name: str
    transport: str = "stdio"
    calls: list[dict[str, Any]] = field(default_factory=list)

    def record(self, *, kind: str, name: str, latency_s: float, success: bool, error_message: str | None = None) -> None:
        self.calls.append(
            {
                "kind": kind,
                "name": name,
                "latency_s": round(float(latency_s), 6),
                "success": bool(success),
                "error_message": str(error_message or "").strip() or None,
            }
        )

    def summary(self) -> dict[str, Any]:
        tool_calls = [call for call in self.calls if call.get("kind") == "tool"]
        resource_calls = [call for call in self.calls if call.get("kind") == "resource"]
        error_calls = [call for call in self.calls if not bool(call.get("success"))]
        tool_names = [str(call.get("name") or "") for call in tool_calls if str(call.get("name") or "").strip()]
        return {
            "server_name": self.server_name,
            "transport": self.transport,
            "status": "error" if error_calls else ("success" if self.calls else "idle"),
            "tool_call_count": len(tool_calls),
            "read_call_count": len(resource_calls),
            "write_call_count": len([name for name in tool_names if name in {"register_evidenceops_entry", "update_action"}]),
            "error_call_count": len(error_calls),
            "total_latency_s": round(sum(float(call.get("latency_s") or 0.0) for call in self.calls), 6),
            "tool_names": tool_names,
        }


class EvidenceOpsMcpClientError(RuntimeError):
    pass


class EvidenceOpsMcpToolError(EvidenceOpsMcpClientError):
    pass


def resolve_evidenceops_mcp_client_config(
    *,
    project_root: Path | None = None,
    python_executable: str | None = None,
) -> EvidenceOpsMcpClientConfig:
    resolved_root = project_root or _project_root()
    resolved_python = python_executable or shutil.which("python") or sys.executable
    return EvidenceOpsMcpClientConfig(
        command=str(resolved_python),
        args=[str(resolved_root / "scripts" / "run_evidenceops_mcp_server.py")],
        env=_default_evidenceops_env(resolved_root),
    )


def build_evidenceops_mcp_server_entry(config: EvidenceOpsMcpClientConfig | None = None) -> dict[str, Any]:
    resolved_config = config or resolve_evidenceops_mcp_client_config()
    return {
        "disabled": False,
        "autoApprove": [],
        "command": resolved_config.command,
        "args": list(resolved_config.args),
        "env": dict(resolved_config.env),
    }


def install_evidenceops_mcp_server_in_cline_settings(
    *,
    settings_path: Path | None = None,
    config: EvidenceOpsMcpClientConfig | None = None,
    server_key: str = DEFAULT_EVIDENCEOPS_MCP_SERVER_KEY,
) -> dict[str, Any]:
    resolved_settings_path = settings_path or DEFAULT_CLINE_MCP_SETTINGS_PATH
    resolved_settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"mcpServers": {}}
    if resolved_settings_path.exists():
        try:
            loaded = json.loads(resolved_settings_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except (OSError, json.JSONDecodeError):
            payload = {"mcpServers": {}}
    mcp_servers = payload.get("mcpServers") if isinstance(payload.get("mcpServers"), dict) else {}
    payload["mcpServers"] = mcp_servers
    mcp_servers[str(server_key)] = build_evidenceops_mcp_server_entry(config)
    resolved_settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


class EvidenceOpsMcpClient:
    def __init__(self, config: EvidenceOpsMcpClientConfig | None = None) -> None:
        self.config = config or resolve_evidenceops_mcp_client_config()
        self.process: subprocess.Popen[bytes] | None = None
        self._request_ids = count(1)
        self.telemetry = EvidenceOpsMcpTelemetry(
            server_name=self.config.server_name,
            transport=self.config.transport,
        )

    def __enter__(self) -> "EvidenceOpsMcpClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        env = os.environ.copy()
        env.update(self.config.env)
        self.process = subprocess.Popen(
            [self.config.command, *self.config.args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self.initialize()

    def close(self) -> None:
        process = self.process
        self.process = None
        if process is None:
            return
        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for stream_name in ("stdout", "stderr"):
            stream = getattr(process, stream_name, None)
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass

    def initialize(self) -> dict[str, Any]:
        response = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "evidenceops-app-client", "version": "0.1.0"},
                "capabilities": {},
            },
        )
        self.notify("notifications/initialized", {})
        return response

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        process = self._require_process()
        write_message(
            process.stdin,
            {"jsonrpc": "2.0", "method": method, "params": params or {}},
        )

    def list_tools(self) -> list[dict[str, Any]]:
        response = self._request("tools/list", {})
        result = response.get("result") if isinstance(response.get("result"), dict) else {}
        return list(result.get("tools") or []) if isinstance(result.get("tools"), list) else []

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        started_at = time.perf_counter()
        response = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        latency_s = time.perf_counter() - started_at
        if isinstance(response.get("error"), dict):
            message = str(response["error"].get("message") or f"Tool call failed: {name}")
            self.telemetry.record(kind="tool", name=name, latency_s=latency_s, success=False, error_message=message)
            raise EvidenceOpsMcpToolError(message)

        result = response.get("result") if isinstance(response.get("result"), dict) else {}
        if bool(result.get("isError")):
            content = result.get("content") if isinstance(result.get("content"), list) else []
            message = str(content[0].get("text") if content and isinstance(content[0], dict) else f"Tool call failed: {name}")
            self.telemetry.record(kind="tool", name=name, latency_s=latency_s, success=False, error_message=message)
            raise EvidenceOpsMcpToolError(message)

        self.telemetry.record(kind="tool", name=name, latency_s=latency_s, success=True)
        if "structuredContent" in result:
            return result.get("structuredContent")
        content = result.get("content") if isinstance(result.get("content"), list) else []
        if content and isinstance(content[0], dict):
            text = content[0].get("text")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        return result

    def read_resource(self, uri: str) -> Any:
        started_at = time.perf_counter()
        response = self._request("resources/read", {"uri": uri})
        latency_s = time.perf_counter() - started_at
        if isinstance(response.get("error"), dict):
            message = str(response["error"].get("message") or f"Resource read failed: {uri}")
            self.telemetry.record(kind="resource", name=uri, latency_s=latency_s, success=False, error_message=message)
            raise EvidenceOpsMcpClientError(message)
        self.telemetry.record(kind="resource", name=uri, latency_s=latency_s, success=True)
        result = response.get("result") if isinstance(response.get("result"), dict) else {}
        contents = result.get("contents") if isinstance(result.get("contents"), list) else []
        if contents and isinstance(contents[0], dict):
            text = contents[0].get("text")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        return result

    def telemetry_summary(self) -> dict[str, Any]:
        return self.telemetry.summary()

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        process = self._require_process()
        request_id = next(self._request_ids)
        write_message(
            process.stdin,
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
        )
        response = read_message(process.stdout)
        if response is None:
            raise EvidenceOpsMcpClientError(f"No response received for method '{method}'.")
        return response

    def _require_process(self) -> subprocess.Popen[bytes]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise EvidenceOpsMcpClientError("MCP process is not running.")
        return self.process


def register_evidenceops_entry_via_mcp(
    entry: dict[str, Any],
    *,
    config: EvidenceOpsMcpClientConfig | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    with EvidenceOpsMcpClient(config) as client:
        result = client.call_tool("register_evidenceops_entry", {"entry": entry})
        return result, client.telemetry_summary()


def update_evidenceops_action_via_mcp(
    *,
    action_id: int,
    status: str | None = None,
    owner: str | None = None,
    due_date: str | None = None,
    metadata_patch: dict[str, Any] | None = None,
    approval_status: str | None = None,
    approval_reason: str | None = None,
    approved_by: str | None = None,
    config: EvidenceOpsMcpClientConfig | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    arguments: dict[str, Any] = {"action_id": int(action_id)}
    if status is not None:
        arguments["status"] = status
    if owner is not None:
        arguments["owner"] = owner
    if due_date is not None:
        arguments["due_date"] = due_date
    if metadata_patch is not None:
        arguments["metadata_patch"] = metadata_patch
    if approval_status is not None:
        arguments["approval_status"] = approval_status
    if approval_reason is not None:
        arguments["approval_reason"] = approval_reason
    if approved_by is not None:
        arguments["approved_by"] = approved_by

    with EvidenceOpsMcpClient(config) as client:
        result = client.call_tool("update_action", arguments)
        return result, client.telemetry_summary()