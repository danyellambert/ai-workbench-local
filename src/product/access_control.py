from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Mapping

SESSION_COOKIE_NAME = "ads_session_id"
SESSION_ID_RE = re.compile(r"^sess_[a-zA-Z0-9_-]{24,80}$")


@dataclass(frozen=True)
class RequestIdentity:
    role: str
    user_id: str
    session_id: str | None
    overlay_root: Path
    can_write_global: bool
    can_publish_external: bool

    def to_public_dict(self) -> dict:
        return {
            "role": self.role,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "overlay_root": str(self.overlay_root),
            "can_write_global": self.can_write_global,
            "can_publish_external": self.can_publish_external,
        }


def users_root_from_env() -> Path:
    raw = (
        os.environ.get("APP_USERS_ROOT")
        or os.environ.get("AI_DECISION_STUDIO_USERS_ROOT")
        or "/app/users"
    )
    return Path(raw).expanduser().resolve()


def _parse_cookie_header(headers: Mapping[str, str] | object) -> SimpleCookie:
    cookie = SimpleCookie()

    raw = ""
    if hasattr(headers, "get"):
        raw = headers.get("Cookie", "") or headers.get("cookie", "") or ""

    if raw:
        cookie.load(raw)

    return cookie


def _new_public_session_id() -> str:
    return "sess_" + secrets.token_urlsafe(32).replace("-", "_")


def _valid_session_id(value: str | None) -> bool:
    return bool(value and SESSION_ID_RE.match(value))


def _public_overlay_root(users_root: Path, session_id: str) -> Path:
    return users_root / "public_sessions" / session_id / "overlay"


def ensure_overlay_dirs(overlay_root: Path) -> None:
    for name in [
        "documents",
        "indexes",
        "runs",
        "artifacts",
        "handoffs",
        "actions",
    ]:
        (overlay_root / name).mkdir(parents=True, exist_ok=True)

    session_state = overlay_root / "session_state.json"
    if not session_state.exists():
        session_state.write_text(
            '{\n  "version": 1,\n  "kind": "public_session_overlay"\n}\n',
            encoding="utf-8",
        )


def public_session_identity(
    headers: Mapping[str, str] | object,
    *,
    users_root: Path | None = None,
) -> tuple[RequestIdentity, str | None]:
    root = users_root or users_root_from_env()
    cookie = _parse_cookie_header(headers)

    incoming = None
    if SESSION_COOKIE_NAME in cookie:
        incoming = cookie[SESSION_COOKIE_NAME].value

    created = False
    if not _valid_session_id(incoming):
        incoming = _new_public_session_id()
        created = True

    session_id = incoming
    overlay_root = _public_overlay_root(root, session_id)
    ensure_overlay_dirs(overlay_root)

    identity = RequestIdentity(
        role="public",
        user_id=session_id,
        session_id=session_id,
        overlay_root=overlay_root,
        can_write_global=False,
        can_publish_external=False,
    )

    set_cookie = None
    if created:
        set_cookie = (
            f"{SESSION_COOKIE_NAME}={session_id}; "
            "Path=/; HttpOnly; SameSite=Lax; Max-Age=2592000"
        )

    return identity, set_cookie


def identity_payload(identity: RequestIdentity) -> dict:
    return {
        "ok": True,
        "identity": identity.to_public_dict(),
        "policy": {
            "public_can_write_overlay": True,
            "public_can_write_global": identity.can_write_global,
            "public_can_publish_external": identity.can_publish_external,
        },
    }
