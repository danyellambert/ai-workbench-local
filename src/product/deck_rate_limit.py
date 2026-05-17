from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from src.product.access_control import RequestIdentity, users_root_from_env


_STATE_LOCK = threading.Lock()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    raw = str(os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value


def _header_value(headers: Mapping[str, str] | object, name: str) -> str:
    if hasattr(headers, "get"):
        return str(headers.get(name, "") or headers.get(name.lower(), "") or "").strip()
    return ""


def _client_ip_from_request(headers: Mapping[str, str] | object, client_address: object) -> str:
    forwarded = _header_value(headers, "X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()

    real_ip = _header_value(headers, "X-Real-IP")
    if real_ip:
        return real_ip.strip()

    if isinstance(client_address, tuple) and client_address:
        return str(client_address[0] or "").strip()

    return "unknown"


def _hash_ip(ip: str) -> str:
    normalized = str(ip or "unknown").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _state_path(users_root: Path | None) -> Path:
    root = users_root or users_root_from_env()
    root = Path(root).expanduser().resolve()
    return root / "public_rate_limits" / "deck_generation.json"


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "events": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "events": []}

    if not isinstance(data, dict):
        return {"version": 1, "events": []}

    events = data.get("events")
    if not isinstance(events, list):
        events = []

    return {"version": 1, "events": [event for event in events if isinstance(event, dict)]}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=".deck_generation.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temp_name = handle.name

    Path(temp_name).replace(path)


def check_public_deck_generation_rate_limit(
    *,
    identity: RequestIdentity,
    headers: Mapping[str, str] | object,
    client_address: object,
    users_root: Path | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Rate-limit public deck generation by session and IP.

    Admin/global requests are never limited here. The limiter writes only under
    the users root, not baseline/runtime/artifacts global state.
    """

    if identity.can_write_global:
        return {
            "ok": True,
            "enforced": False,
            "scope": "global",
            "message": "Admin deck generation is not subject to public deck rate limits.",
        }

    enabled = _env_bool("AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_ENABLED", True)
    if not enabled:
        return {
            "ok": True,
            "enforced": False,
            "scope": "session_overlay",
            "message": "Public deck generation rate limit is disabled.",
        }

    window_seconds = max(1, _env_int("AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_WINDOW_SECONDS", 3600))
    max_per_session = _env_int("AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_MAX_PER_SESSION", 3)
    max_per_ip = _env_int("AI_DECISION_STUDIO_PUBLIC_DECK_RATE_LIMIT_MAX_PER_IP", 12)

    current_time = float(now if now is not None else time.time())
    cutoff = current_time - window_seconds

    session_id = str(identity.session_id or identity.user_id or "unknown").strip() or "unknown"
    client_ip = _client_ip_from_request(headers, client_address)
    ip_hash = _hash_ip(client_ip)

    path = _state_path(users_root)

    with _STATE_LOCK:
        state = _read_state(path)

        events = []
        for event in state.get("events", []):
            try:
                ts = float(event.get("ts", 0))
            except Exception:
                continue
            if ts >= cutoff:
                events.append(event)

        session_count = sum(1 for event in events if event.get("session_id") == session_id)
        ip_count = sum(1 for event in events if event.get("ip_hash") == ip_hash)

        blocked_by = []
        retry_after_seconds = 0

        if max_per_session > 0 and session_count >= max_per_session:
            blocked_by.append("session")
            session_times = [
                float(event.get("ts", 0))
                for event in events
                if event.get("session_id") == session_id
            ]
            if session_times:
                retry_after_seconds = max(retry_after_seconds, int(max(1, window_seconds - (current_time - min(session_times)))))

        if max_per_ip > 0 and ip_count >= max_per_ip:
            blocked_by.append("ip")
            ip_times = [
                float(event.get("ts", 0))
                for event in events
                if event.get("ip_hash") == ip_hash
            ]
            if ip_times:
                retry_after_seconds = max(retry_after_seconds, int(max(1, window_seconds - (current_time - min(ip_times)))))

        if blocked_by:
            state["events"] = events
            _write_state(path, state)
            return {
                "ok": False,
                "enforced": True,
                "scope": "session_overlay",
                "blocked_by": blocked_by,
                "window_seconds": window_seconds,
                "max_per_session": max_per_session,
                "max_per_ip": max_per_ip,
                "session_count": session_count,
                "ip_count": ip_count,
                "retry_after_seconds": retry_after_seconds,
                "message": (
                    "Public demo deck generation rate limit reached. "
                    "Please wait before generating another deck."
                ),
            }

        events.append(
            {
                "ts": current_time,
                "session_id": session_id,
                "ip_hash": ip_hash,
                "kind": "deck_generation",
            }
        )
        state["events"] = events
        _write_state(path, state)

    return {
        "ok": True,
        "enforced": True,
        "scope": "session_overlay",
        "window_seconds": window_seconds,
        "max_per_session": max_per_session,
        "max_per_ip": max_per_ip,
        "session_count": session_count + 1,
        "ip_count": ip_count + 1,
        "message": "Public demo deck generation is within rate limits.",
    }
