from __future__ import annotations

import getpass
import subprocess


SECRET_STORE_SERVICE_PREFIX = "ai-workbench-local"
SECRET_STORE_ACCOUNT = getpass.getuser() or "workspace"

# The backend can keep running while Preferences replaces a credential. Keep a
# process-local copy of UI-managed secrets so the next workflow request cannot
# accidentally read a stale duplicate Keychain entry.
_SECRET_CACHE: dict[str, str] = {}


def _service_name(secret_key: str) -> str:
    normalized = str(secret_key or "").strip()
    return f"{SECRET_STORE_SERVICE_PREFIX}:{normalized}"


def get_secret(secret_key: str) -> str | None:
    normalized_key = str(secret_key or "").strip()
    if not normalized_key:
        return None
    if normalized_key in _SECRET_CACHE:
        cached_value = str(_SECRET_CACHE.get(normalized_key) or "").strip()
        return cached_value or None

    service_name = _service_name(normalized_key)
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                SECRET_STORE_ACCOUNT,
                "-s",
                service_name,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None
    secret_value = str(result.stdout or "").strip()
    return secret_value or None


def delete_secret(secret_key: str) -> bool:
    normalized_key = str(secret_key or "").strip()
    if not normalized_key:
        return True

    _SECRET_CACHE.pop(normalized_key, None)
    service_name = _service_name(normalized_key)

    # macOS Keychain can contain duplicate generic-password items for the same
    # service/account, especially across repeated development saves. Delete all
    # matches so a later `find-generic-password` cannot keep returning an older
    # token.
    for _ in range(20):
        try:
            result = subprocess.run(
                [
                    "security",
                    "delete-generic-password",
                    "-a",
                    SECRET_STORE_ACCOUNT,
                    "-s",
                    service_name,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        if result.returncode != 0:
            return True
    return True


def set_secret(secret_key: str, secret_value: str) -> bool:
    normalized_key = str(secret_key or "").strip()
    normalized_value = str(secret_value or "").strip()
    if not normalized_key:
        return False
    if not normalized_value:
        return delete_secret(normalized_key)

    if not delete_secret(normalized_key):
        return False

    service_name = _service_name(normalized_key)
    try:
        result = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-a",
                SECRET_STORE_ACCOUNT,
                "-s",
                service_name,
                "-w",
                normalized_value,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False

    if result.returncode != 0:
        return False
    _SECRET_CACHE[normalized_key] = normalized_value
    return True
