from __future__ import annotations

import json
import os
import secrets
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.product.access_control import RequestIdentity, users_root_from_env


_STATE_LOCK = threading.Lock()


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = str(os.environ.get(name) or "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _iso_utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _state_path(users_root: Path | None) -> Path:
    root = users_root or users_root_from_env()
    return Path(root).expanduser().resolve() / "public_execution_gate" / "in_flight.json"


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "in_flight": []}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "in_flight": []}

    if not isinstance(payload, dict):
        return {"version": 1, "in_flight": []}

    entries = payload.get("in_flight")
    if not isinstance(entries, list):
        entries = []

    return {"version": 1, "in_flight": [entry for entry in entries if isinstance(entry, dict)]}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=".public_execution_gate.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        tmp_name = handle.name

    Path(tmp_name).replace(path)


def _entry_ts(entry: dict[str, Any]) -> float | None:
    try:
        return float(entry.get("started_at_ts"))
    except (TypeError, ValueError):
        return None


def acquire_public_execution_slot(
    *,
    identity: RequestIdentity,
    execution_kind: str,
    users_root: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Acquire a short-lived public execution slot.

    This protects the shared AI runtime/provider key from simultaneous public
    abuse. It is separate from the rolling execution quota. Admin/global
    requests bypass this gate.
    """

    if identity.can_write_global:
        return {
            "ok": True,
            "acquired": False,
            "enforced": False,
            "scope": "global",
            "message": "Admin/global execution is not subject to public execution concurrency limits.",
        }

    enabled = _env_bool("AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_ENABLED", True)
    if not enabled:
        return {
            "ok": True,
            "acquired": False,
            "enforced": False,
            "scope": "session_overlay",
            "message": "Public execution concurrency gate is disabled.",
        }

    max_per_session = _env_int("AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_PER_SESSION", 1)
    max_global = _env_int("AI_DECISION_STUDIO_PUBLIC_EXECUTION_MAX_IN_FLIGHT_GLOBAL", 2)
    ttl_seconds = _env_int("AI_DECISION_STUDIO_PUBLIC_EXECUTION_IN_FLIGHT_TTL_SECONDS", 300)

    if max_per_session <= 0 and max_global <= 0:
        return {
            "ok": True,
            "acquired": False,
            "enforced": False,
            "scope": "session_overlay",
            "message": "Public execution concurrency gate is disabled by limits <= 0.",
        }

    if ttl_seconds <= 0:
        ttl_seconds = 300

    session_id = str(identity.session_id or identity.user_id or "unknown").strip() or "unknown"
    kind = str(execution_kind or "execution").strip() or "execution"
    current_time = float(now if now is not None else time.time())
    cutoff = current_time - float(ttl_seconds)
    path = _state_path(users_root)

    with _STATE_LOCK:
        state = _read_state(path)
        entries: list[dict[str, Any]] = []
        expired_count = 0

        for entry in state.get("in_flight", []):
            started_at = _entry_ts(entry)
            if started_at is None:
                continue
            if started_at < cutoff:
                expired_count += 1
                continue
            entries.append(entry)

        session_entries = [entry for entry in entries if entry.get("session_id") == session_id]
        global_count = len(entries)

        if max_per_session > 0 and len(session_entries) >= max_per_session:
            state["in_flight"] = entries
            _write_state(path, state)
            return {
                "ok": False,
                "acquired": False,
                "enforced": True,
                "scope": "session_overlay",
                "blocked_by": ["session_in_flight"],
                "session_id": session_id,
                "execution_kind": kind,
                "max_in_flight_per_session": max_per_session,
                "max_in_flight_global": max_global,
                "in_flight_per_session": len(session_entries),
                "in_flight_global": global_count,
                "ttl_seconds": ttl_seconds,
                "retry_after_seconds": 15,
                "expired_count": expired_count,
                "message": "You already have a workflow running. Wait for it to finish before starting another one.",
            }

        if max_global > 0 and global_count >= max_global:
            state["in_flight"] = entries
            _write_state(path, state)
            return {
                "ok": False,
                "acquired": False,
                "enforced": True,
                "scope": "session_overlay",
                "blocked_by": ["global_in_flight"],
                "session_id": session_id,
                "execution_kind": kind,
                "max_in_flight_per_session": max_per_session,
                "max_in_flight_global": max_global,
                "in_flight_per_session": len(session_entries),
                "in_flight_global": global_count,
                "ttl_seconds": ttl_seconds,
                "retry_after_seconds": 30,
                "expired_count": expired_count,
                "message": "The public demo runtime is busy. Please try again in a few seconds.",
            }

        token = secrets.token_urlsafe(24)
        entry = {
            "token": token,
            "started_at_ts": current_time,
            "started_at": _iso_utc(current_time),
            "session_id": session_id,
            "kind": kind,
        }
        entries.append(entry)
        state["in_flight"] = entries
        _write_state(path, state)

    return {
        "ok": True,
        "acquired": True,
        "enforced": True,
        "scope": "session_overlay",
        "token": token,
        "session_id": session_id,
        "execution_kind": kind,
        "max_in_flight_per_session": max_per_session,
        "max_in_flight_global": max_global,
        "in_flight_per_session": len(session_entries) + 1,
        "in_flight_global": global_count + 1,
        "ttl_seconds": ttl_seconds,
        "expired_count": expired_count,
        "message": "Public execution concurrency slot acquired.",
    }


def release_public_execution_slot(
    gate: dict[str, Any] | None,
    *,
    users_root: Path | None = None,
) -> dict[str, Any]:
    if not gate or not gate.get("acquired"):
        return {"ok": True, "released": False}

    token = str(gate.get("token") or "").strip()
    if not token:
        return {"ok": True, "released": False}

    path = _state_path(users_root)

    with _STATE_LOCK:
        state = _read_state(path)
        entries = state.get("in_flight", [])
        remaining = [entry for entry in entries if entry.get("token") != token]
        released = len(remaining) != len(entries)
        state["in_flight"] = remaining
        _write_state(path, state)

    return {"ok": True, "released": released}
