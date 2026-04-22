from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_CHAT_ROLES = {"user", "assistant"}
VALID_CHAT_SESSION_STATUSES = {"active", "error", "completed"}
VALID_WORKFLOW_RUN_STATUSES = {"queued", "running", "completed", "warning", "error", "failed"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_json_like(value: object):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_sanitize_json_like(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            if isinstance(key, str):
                sanitized[key] = _sanitize_json_like(item)
        return sanitized
    return str(value)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def load_lab_chat_sessions(path: Path) -> list[dict[str, object]]:
    payload = _read_json(path, [])
    if not isinstance(payload, list):
        return []
    sessions: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        session_id = str(item.get("session_id") or item.get("id") or "").strip()
        if not session_id:
            continue
        raw_messages = item.get("messages") if isinstance(item.get("messages"), list) else []
        messages: list[dict[str, object]] = []
        for raw_message in raw_messages:
            if not isinstance(raw_message, dict):
                continue
            role = str(raw_message.get("role") or "").strip().lower()
            content = str(raw_message.get("content") or "")
            if role not in VALID_CHAT_ROLES or not content.strip():
                continue
            normalized_message: dict[str, object] = {
                "id": str(raw_message.get("id") or _new_id("msg")),
                "role": role,
                "content": content,
                "timestamp": str(raw_message.get("timestamp") or _now_iso()),
            }
            sources = raw_message.get("sources") if isinstance(raw_message.get("sources"), list) else []
            if sources:
                normalized_message["sources"] = _sanitize_json_like(sources)
            diagnostics = raw_message.get("diagnostics") if isinstance(raw_message.get("diagnostics"), dict) else None
            if diagnostics:
                normalized_message["diagnostics"] = _sanitize_json_like(diagnostics)
            messages.append(normalized_message)
        normalized_session: dict[str, object] = {
            "session_id": session_id,
            "title": str(item.get("title") or "AI Lab chat session").strip() or "AI Lab chat session",
            "created_at": str(item.get("created_at") or _now_iso()),
            "updated_at": str(item.get("updated_at") or item.get("created_at") or _now_iso()),
            "status": str(item.get("status") or "active") if str(item.get("status") or "active") in VALID_CHAT_SESSION_STATUSES else "active",
            "document_ids": [str(document_id) for document_id in (item.get("document_ids") or []) if str(document_id or "").strip()],
            "messages": messages,
        }
        last_error = str(item.get("last_error") or "").strip()
        if last_error:
            normalized_session["last_error"] = last_error
        runtime = item.get("runtime") if isinstance(item.get("runtime"), dict) else None
        if runtime:
            normalized_session["runtime"] = _sanitize_json_like(runtime)
        sessions.append(normalized_session)
    sessions.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    return sessions


def save_lab_chat_sessions(path: Path, sessions: list[dict[str, object]]) -> None:
    _write_json(path, [_sanitize_json_like(item) for item in sessions])


def upsert_lab_chat_session(path: Path, session: dict[str, object]) -> dict[str, object]:
    session_id = str(session.get("session_id") or session.get("id") or "").strip() or _new_id("session")
    normalized_session = {
        "session_id": session_id,
        "title": str(session.get("title") or "AI Lab chat session").strip() or "AI Lab chat session",
        "created_at": str(session.get("created_at") or _now_iso()),
        "updated_at": str(session.get("updated_at") or _now_iso()),
        "status": str(session.get("status") or "active") if str(session.get("status") or "active") in VALID_CHAT_SESSION_STATUSES else "active",
        "document_ids": [str(document_id) for document_id in (session.get("document_ids") or []) if str(document_id or "").strip()],
        "messages": [item for item in (session.get("messages") if isinstance(session.get("messages"), list) else []) if isinstance(item, dict)],
    }
    if isinstance(session.get("runtime"), dict):
        normalized_session["runtime"] = _sanitize_json_like(session.get("runtime"))
    if str(session.get("last_error") or "").strip():
        normalized_session["last_error"] = str(session.get("last_error")).strip()

    sessions = load_lab_chat_sessions(path)
    updated = False
    for index, current in enumerate(sessions):
        if str(current.get("session_id") or "") == session_id:
            sessions[index] = normalized_session
            updated = True
            break
    if not updated:
        sessions.insert(0, normalized_session)
    save_lab_chat_sessions(path, sessions)
    return normalized_session


def create_lab_chat_session(path: Path, *, title: str | None = None, document_ids: list[str] | None = None) -> dict[str, object]:
    timestamp = _now_iso()
    session = {
        "session_id": _new_id("session"),
        "title": str(title or "AI Lab chat session").strip() or "AI Lab chat session",
        "created_at": timestamp,
        "updated_at": timestamp,
        "status": "active",
        "document_ids": [str(document_id) for document_id in (document_ids or []) if str(document_id or "").strip()],
        "messages": [],
    }
    return upsert_lab_chat_session(path, session)


def append_lab_chat_message(
    path: Path,
    *,
    session_id: str,
    role: str,
    content: str,
    sources: list[dict[str, object]] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized_role = str(role or "").strip().lower()
    if normalized_role not in VALID_CHAT_ROLES:
        raise ValueError("Chat role must be 'user' or 'assistant'.")
    normalized_content = str(content or "").strip()
    if not normalized_content:
        raise ValueError("Chat message content is required.")

    sessions = load_lab_chat_sessions(path)
    for session in sessions:
        if str(session.get("session_id") or "") != str(session_id or "").strip():
            continue
        message = {
            "id": _new_id("msg"),
            "role": normalized_role,
            "content": normalized_content,
            "timestamp": _now_iso(),
        }
        if sources:
            message["sources"] = _sanitize_json_like(sources)
        if diagnostics:
            message["diagnostics"] = _sanitize_json_like(diagnostics)
        messages = session.get("messages") if isinstance(session.get("messages"), list) else []
        messages.append(message)
        session["messages"] = messages
        session["updated_at"] = message["timestamp"]
        session["status"] = "active"
        session.pop("last_error", None)
        save_lab_chat_sessions(path, sessions)
        return message
    raise KeyError(f"Chat session not found: {session_id}")


def update_lab_chat_session_runtime(
    path: Path,
    *,
    session_id: str,
    runtime: dict[str, object] | None = None,
    status: str | None = None,
    last_error: str | None = None,
    document_ids: list[str] | None = None,
) -> dict[str, object]:
    sessions = load_lab_chat_sessions(path)
    for session in sessions:
        if str(session.get("session_id") or "") != str(session_id or "").strip():
            continue
        if isinstance(runtime, dict):
            session["runtime"] = _sanitize_json_like(runtime)
        if status and status in VALID_CHAT_SESSION_STATUSES:
            session["status"] = status
        if document_ids is not None:
            session["document_ids"] = [str(document_id) for document_id in document_ids if str(document_id or "").strip()]
        if last_error:
            session["last_error"] = str(last_error).strip()
        else:
            session.pop("last_error", None)
        session["updated_at"] = _now_iso()
        save_lab_chat_sessions(path, sessions)
        return session
    raise KeyError(f"Chat session not found: {session_id}")


def get_lab_chat_session(path: Path, session_id: str) -> dict[str, object] | None:
    normalized_session_id = str(session_id or "").strip()
    if not normalized_session_id:
        return None
    for session in load_lab_chat_sessions(path):
        if str(session.get("session_id") or "") == normalized_session_id:
            return session
    return None


def load_lab_workflow_runs(path: Path) -> list[dict[str, object]]:
    payload = _read_json(path, [])
    if not isinstance(payload, list):
        return []
    runs: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        run_id = str(item.get("run_id") or item.get("id") or "").strip()
        if not run_id:
            continue
        normalized: dict[str, object] = {
            "run_id": run_id,
            "task_id": str(item.get("task_id") or item.get("workflow_id") or "document_review").strip() or "document_review",
            "workflow_id": str(item.get("workflow_id") or "document_review").strip() or "document_review",
            "created_at": str(item.get("created_at") or _now_iso()),
            "updated_at": str(item.get("updated_at") or item.get("created_at") or _now_iso()),
            "status": str(item.get("status") or "completed") if str(item.get("status") or "completed") in VALID_WORKFLOW_RUN_STATUSES else "completed",
            "input_text": str(item.get("input_text") or ""),
            "document_ids": [str(document_id) for document_id in (item.get("document_ids") or []) if str(document_id or "").strip()],
            "document_names": [str(name) for name in (item.get("document_names") or []) if str(name or "").strip()],
            "confidence": float(item.get("confidence") or 0.0) if isinstance(item.get("confidence"), (int, float)) else 0.0,
            "needs_review": bool(item.get("needs_review")),
            "source_count": int(item.get("source_count") or 0),
        }
        for optional_key in [
            "provider",
            "model",
            "review_reason",
            "summary",
            "artifact_path",
            "artifact_label",
            "execution_mode",
            "result_title",
            "trace_id",
            "surface",
            "reran_from_run_id",
        ]:
            optional_value = item.get(optional_key)
            if optional_value is not None:
                normalized[optional_key] = _sanitize_json_like(optional_value)
        for optional_numeric_key in ["latency_s", "total_tokens", "context_chars"]:
            if isinstance(item.get(optional_numeric_key), (int, float)):
                normalized[optional_numeric_key] = float(item.get(optional_numeric_key))
        for optional_dict_key in ["result", "raw_json", "trace", "request_payload", "response_payload"]:
            optional_value = item.get(optional_dict_key)
            if isinstance(optional_value, dict):
                normalized[optional_dict_key] = _sanitize_json_like(optional_value)
        runs.append(normalized)
    runs.sort(key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""), reverse=True)
    return runs


def save_lab_workflow_runs(path: Path, runs: list[dict[str, object]]) -> None:
    _write_json(path, [_sanitize_json_like(item) for item in runs])


def append_lab_workflow_run(path: Path, run_record: dict[str, object]) -> dict[str, object]:
    normalized = {
        "run_id": str(run_record.get("run_id") or run_record.get("id") or _new_id("run")),
        "task_id": str(run_record.get("task_id") or run_record.get("workflow_id") or "document_review").strip() or "document_review",
        "workflow_id": str(run_record.get("workflow_id") or "document_review").strip() or "document_review",
        "created_at": str(run_record.get("created_at") or _now_iso()),
        "updated_at": str(run_record.get("updated_at") or _now_iso()),
        "status": str(run_record.get("status") or "completed") if str(run_record.get("status") or "completed") in VALID_WORKFLOW_RUN_STATUSES else "completed",
        "input_text": str(run_record.get("input_text") or ""),
        "document_ids": [str(document_id) for document_id in (run_record.get("document_ids") or []) if str(document_id or "").strip()],
        "document_names": [str(name) for name in (run_record.get("document_names") or []) if str(name or "").strip()],
        "confidence": float(run_record.get("confidence") or 0.0) if isinstance(run_record.get("confidence"), (int, float)) else 0.0,
        "needs_review": bool(run_record.get("needs_review")),
        "source_count": int(run_record.get("source_count") or 0),
    }
    for optional_key in [
        "provider",
        "model",
        "review_reason",
        "summary",
        "artifact_path",
        "artifact_label",
        "execution_mode",
        "result_title",
        "trace_id",
        "surface",
        "reran_from_run_id",
    ]:
        optional_value = run_record.get(optional_key)
        if optional_value is not None:
            normalized[optional_key] = _sanitize_json_like(optional_value)
    for optional_numeric_key in ["latency_s", "total_tokens", "context_chars"]:
        if isinstance(run_record.get(optional_numeric_key), (int, float)):
            normalized[optional_numeric_key] = float(run_record.get(optional_numeric_key))
    for optional_dict_key in ["result", "raw_json", "trace", "request_payload", "response_payload"]:
        optional_value = run_record.get(optional_dict_key)
        if isinstance(optional_value, dict):
            normalized[optional_dict_key] = _sanitize_json_like(optional_value)

    runs = load_lab_workflow_runs(path)
    runs.insert(0, normalized)
    save_lab_workflow_runs(path, runs)
    return normalized


def get_lab_workflow_run(path: Path, run_id: str) -> dict[str, object] | None:
    normalized_run_id = str(run_id or "").strip()
    if not normalized_run_id:
        return None
    for run in load_lab_workflow_runs(path):
        if str(run.get("run_id") or "") == normalized_run_id:
            return run
    return None
