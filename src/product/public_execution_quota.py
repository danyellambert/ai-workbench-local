from __future__ import annotations

import json
import os
import tempfile
import threading
import time
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


def _state_path(users_root: Path | None) -> Path:
    root = users_root or users_root_from_env()
    return Path(root).expanduser().resolve() / "public_execution_quota" / "executions.json"


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "events": []}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "events": []}

    if not isinstance(payload, dict):
        return {"version": 1, "events": []}

    events = payload.get("events")
    if not isinstance(events, list):
        events = []

    return {"version": 1, "events": [event for event in events if isinstance(event, dict)]}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=".public_execution_quota.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        tmp_name = handle.name

    Path(tmp_name).replace(path)


def check_public_execution_quota(
    *,
    identity: RequestIdentity,
    execution_kind: str,
    users_root: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Limit public execution attempts per anonymous public session.

    This is not a storage quota and it does not delete anything. It only writes a
    small counter file under the users root. Admin/global requests bypass it.
    """

    if identity.can_write_global:
        return {
            "ok": True,
            "enforced": False,
            "scope": "global",
            "message": "Admin/global execution is not subject to public execution quota.",
        }

    enabled = _env_bool("AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_ENABLED", True)
    if not enabled:
        return {
            "ok": True,
            "enforced": False,
            "scope": "session_overlay",
            "message": "Public execution quota is disabled.",
        }

    max_per_session = _env_int("AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_MAX_PER_SESSION", 20)
    if max_per_session <= 0:
        return {
            "ok": True,
            "enforced": False,
            "scope": "session_overlay",
            "message": "Public execution quota is disabled by max_per_session <= 0.",
        }

    session_id = str(identity.session_id or identity.user_id or "unknown").strip() or "unknown"
    kind = str(execution_kind or "execution").strip() or "execution"
    current_time = float(now if now is not None else time.time())
    path = _state_path(users_root)

    with _STATE_LOCK:
        state = _read_state(path)
        events = state.get("events", [])

        session_events = [
            event
            for event in events
            if event.get("session_id") == session_id
        ]

        if len(session_events) >= max_per_session:
            state["events"] = events
            _write_state(path, state)
            return {
                "ok": False,
                "enforced": True,
                "scope": "session_overlay",
                "blocked_by": ["session"],
                "session_id": session_id,
                "execution_kind": kind,
                "max_per_session": max_per_session,
                "session_count": len(session_events),
                "message": (
                    "Public demo execution quota reached for this session. "
                    "Start a new admin session or increase the public execution quota."
                ),
            }

        events.append(
            {
                "ts": current_time,
                "session_id": session_id,
                "kind": kind,
            }
        )
        state["events"] = events
        _write_state(path, state)

    return {
        "ok": True,
        "enforced": True,
        "scope": "session_overlay",
        "session_id": session_id,
        "execution_kind": kind,
        "max_per_session": max_per_session,
        "session_count": len(session_events) + 1,
        "message": "Public demo execution is within session quota.",
    }
