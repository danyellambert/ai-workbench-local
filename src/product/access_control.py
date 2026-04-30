from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Mapping

SESSION_COOKIE_NAME = "ads_session_id"
ADMIN_SESSION_COOKIE_NAME = "ads_admin_session"
SESSION_ID_RE = re.compile(r"^sess_[a-zA-Z0-9_-]{24,80}$")
ADMIN_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12
PBKDF2_SCHEME = "pbkdf2_sha256"
DEFAULT_PBKDF2_ITERATIONS = 260_000


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

def _admin_overlay_root(users_root: Path) -> Path:
    return users_root / "admin" / "overlay"


def _admin_identity(*, users_root: Path | None = None) -> RequestIdentity:
    root = users_root or users_root_from_env()
    overlay_root = _admin_overlay_root(root)
    ensure_overlay_dirs(overlay_root)
    return RequestIdentity(
        role="admin",
        user_id="admin",
        session_id=None,
        overlay_root=overlay_root,
        can_write_global=True,
        can_publish_external=True,
    )


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def hash_admin_password(password: str, *, iterations: int = DEFAULT_PBKDF2_ITERATIONS, salt: str | None = None) -> str:
    if not password:
        raise ValueError("Admin password is required.")
    salt_text = salt or _b64encode(secrets.token_bytes(18))
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_text.encode("utf-8"), iterations)
    return f"{PBKDF2_SCHEME}${iterations}${salt_text}${_b64encode(digest)}"


def verify_admin_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, iterations_text, salt_text, expected_digest = str(encoded_hash or "").split("$", 3)
        if scheme != PBKDF2_SCHEME:
            return False
        iterations = int(iterations_text)
        candidate = hash_admin_password(password, iterations=iterations, salt=salt_text).split("$", 3)[3]
        return secrets.compare_digest(candidate, expected_digest)
    except Exception:
        return False


def admin_auth_configured() -> bool:
    return bool(
        os.environ.get("AI_DECISION_STUDIO_ADMIN_USERNAME")
        and os.environ.get("AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH")
        and os.environ.get("AI_DECISION_STUDIO_SESSION_SECRET")
    )


def _admin_username_from_env() -> str:
    return str(os.environ.get("AI_DECISION_STUDIO_ADMIN_USERNAME") or "").strip()


def authenticate_admin_credentials(username: str, password: str) -> bool:
    expected_username = _admin_username_from_env()
    expected_hash = os.environ.get("AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH") or ""
    if not expected_username or not expected_hash:
        return False
    if not secrets.compare_digest(str(username or "").strip(), expected_username):
        return False
    return verify_admin_password(str(password or ""), expected_hash)


def _session_secret() -> str:
    return str(os.environ.get("AI_DECISION_STUDIO_SESSION_SECRET") or "")


def _sign_admin_token_payload(payload: str) -> str:
    secret = _session_secret()
    if not secret:
        raise ValueError("AI_DECISION_STUDIO_SESSION_SECRET is required.")
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_admin_session_token(*, now: int | None = None) -> str:
    issued_at = int(now or time.time())
    expires_at = issued_at + ADMIN_TOKEN_MAX_AGE_SECONDS
    nonce = _b64encode(secrets.token_bytes(18))
    payload = f"v1.admin.{issued_at}.{expires_at}.{nonce}"
    signature = _sign_admin_token_payload(payload)
    return f"{payload}.{signature}"


def verify_admin_session_token(token: str | None, *, now: int | None = None) -> bool:
    if not token:
        return False
    parts = str(token).split(".")
    if len(parts) != 6:
        return False
    version, subject, issued_at_text, expires_at_text, nonce, signature = parts
    if version != "v1" or subject != "admin" or not nonce:
        return False
    try:
        issued_at = int(issued_at_text)
        expires_at = int(expires_at_text)
    except ValueError:
        return False
    current_time = int(now or time.time())
    if issued_at > current_time + 60:
        return False
    if expires_at < current_time:
        return False
    payload = ".".join(parts[:5])
    expected = _sign_admin_token_payload(payload)
    return hmac.compare_digest(signature, expected)


def create_admin_session_cookie() -> str:
    token = create_admin_session_token()
    return (
        f"{ADMIN_SESSION_COOKIE_NAME}={token}; "
        f"Path=/; HttpOnly; SameSite=Lax; Max-Age={ADMIN_TOKEN_MAX_AGE_SECONDS}"
    )


def clear_admin_session_cookie() -> str:
    return f"{ADMIN_SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def admin_session_identity(
    headers: Mapping[str, str] | object,
    *,
    users_root: Path | None = None,
) -> RequestIdentity | None:
    cookie = _parse_cookie_header(headers)
    token = cookie[ADMIN_SESSION_COOKIE_NAME].value if ADMIN_SESSION_COOKIE_NAME in cookie else None
    if not verify_admin_session_token(token):
        return None
    return _admin_identity(users_root=users_root)


def request_identity(
    headers: Mapping[str, str] | object,
    *,
    users_root: Path | None = None,
) -> tuple[RequestIdentity, str | None]:
    admin_identity = admin_session_identity(headers, users_root=users_root)
    if admin_identity is not None:
        return admin_identity, None
    return public_session_identity(headers, users_root=users_root)

