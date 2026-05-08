from __future__ import annotations

import json
import os
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
    return Path(root).expanduser().resolve() / "public_execution_quota" / "executions.json"


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 2, "events": []}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 2, "events": []}

    if not isinstance(payload, dict):
        return {"version": 2, "events": []}

    events = payload.get("events")
    if not isinstance(events, list):
        events = []

    return {"version": 2, "events": [event for event in events if isinstance(event, dict)]}


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


def _event_ts(event: dict[str, Any]) -> float | None:
    try:
        return float(event.get("ts"))
    except (TypeError, ValueError):
        return None


def check_public_execution_quota(
    *,
    identity: RequestIdentity,
    execution_kind: str,
    users_root: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Limit public execution attempts per anonymous public session.

    This is not a storage quota and it does not delete anything. It only writes a
    small rolling-window counter file under the users root. Admin/global requests
    bypass it.
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

    max_per_session = _env_int("AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_MAX_PER_SESSION", 4)
    if max_per_session <= 0:
        return {
            "ok": True,
            "enforced": False,
            "scope": "session_overlay",
            "message": "Public execution quota is disabled by max_per_session <= 0.",
        }

    window_seconds = _env_int("AI_DECISION_STUDIO_PUBLIC_EXECUTION_QUOTA_WINDOW_SECONDS", 1200)
    if window_seconds <= 0:
        window_seconds = 1200

    session_id = str(identity.session_id or identity.user_id or "unknown").strip() or "unknown"
    kind = str(execution_kind or "execution").strip() or "execution"
    current_time = float(now if now is not None else time.time())
    cutoff = current_time - float(window_seconds)
    path = _state_path(users_root)

    with _STATE_LOCK:
        state = _read_state(path)
        raw_events = state.get("events", [])

        # Keep only events still relevant to the rolling window, plus malformed events
        # from other sessions are discarded safely.
        events: list[dict[str, Any]] = []
        for event in raw_events:
            event_time = _event_ts(event)
            if event_time is None:
                continue
            if event_time >= cutoff:
                events.append(event)

        session_events = [
            event
            for event in events
            if event.get("session_id") == session_id
        ]

        if len(session_events) >= max_per_session:
            oldest_ts = min((_event_ts(event) for event in session_events if _event_ts(event) is not None), default=current_time)
            reset_at_ts = float(oldest_ts) + float(window_seconds)
            retry_after_seconds = max(1, int(round(reset_at_ts - current_time)))

            state["events"] = events
            _write_state(path, state)

            return {
                "ok": False,
                "enforced": True,
                "scope": "session_overlay",
                "blocked_by": ["session_window"],
                "session_id": session_id,
                "execution_kind": kind,
                "max_per_session": max_per_session,
                "window_seconds": window_seconds,
                "retry_after_seconds": retry_after_seconds,
                "reset_at": _iso_utc(reset_at_ts),
                "session_count": len(session_events),
                "message": (
                    "Public demo execution limit reached. "
                    "Please wait about 20 minutes before running another workflow."
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
        "window_seconds": window_seconds,
        "remaining": max(0, max_per_session - (len(session_events) + 1)),
        "session_count": len(session_events) + 1,
        "message": "Public demo execution is within session quota.",
    }
