from __future__ import annotations

import getpass
import json
import os
import subprocess
import sys
from pathlib import Path
from shutil import which
from tempfile import NamedTemporaryFile
from typing import Any


SECRET_STORE_SERVICE_PREFIX = "ai-workbench-local"
SECRET_STORE_ACCOUNT = getpass.getuser() or "workspace"
_SECRET_CACHE: dict[str, str] = {}


def _service_name(secret_key: str) -> str:
    return f"{SECRET_STORE_SERVICE_PREFIX}:{str(secret_key or '').strip()}"


def _running_inside_container() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(errors="ignore")
        return "docker" in cgroup.lower() or "containerd" in cgroup.lower()
    except Exception:
        return False


def _secret_store_backend() -> str:
    configured = str(os.getenv("AI_DECISION_STUDIO_SECRET_STORE_BACKEND", "")).strip().lower()

    if configured in {"file", "json", "deployment_file", "deployment", "volume"}:
        return "file"

    if configured in {"keychain", "macos_keychain", "macos"}:
        return "macos_keychain"

    if sys.platform == "darwin" and which("security") and not _running_inside_container():
        return "macos_keychain"

    return "file"


def _file_store_path() -> Path:
    explicit = (
        os.getenv("AI_DECISION_STUDIO_SECRET_STORE_PATH")
        or os.getenv("AI_DECISION_STUDIO_CREDENTIAL_STORE_PATH")
        or os.getenv("PRODUCT_CREDENTIAL_STORE_PATH")
        or os.getenv("CREDENTIAL_STORE_PATH")
    )

    if explicit:
        return Path(explicit).expanduser()

    if _running_inside_container() or Path("/app").exists():
        return Path("/app/secrets/credential_store.json")

    return Path.home() / ".config" / "ai-decision-studio" / "secrets" / "credential_store.json"


def _load_file_store() -> dict[str, str]:
    path = _file_store_path()

    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(payload, dict):
        return {}

    secrets = payload.get("secrets") if isinstance(payload.get("secrets"), dict) else payload

    if not isinstance(secrets, dict):
        return {}

    return {
        str(key): str(value)
        for key, value in secrets.items()
        if str(key).strip() and str(value).strip()
    }


def _save_file_store(secrets: dict[str, str]) -> bool:
    path = _file_store_path()

    payload: dict[str, Any] = {
        "version": "credential_store.v1",
        "backend": "file",
        "secrets": {
            str(key): str(value)
            for key, value in secrets.items()
            if str(key).strip() and str(value).strip()
        },
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass

        with NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            tmp_name = handle.name

        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)

        return True
    except Exception:
        try:
            if "tmp_name" in locals():
                Path(tmp_name).unlink(missing_ok=True)
        except Exception:
            pass

        return False


def _get_file_secret(secret_key: str) -> str | None:
    value = str(_load_file_store().get(secret_key) or "").strip()
    return value or None


def _set_file_secret(secret_key: str, secret_value: str) -> bool:
    secrets = _load_file_store()
    secrets[secret_key] = secret_value
    return _save_file_store(secrets)


def _delete_file_secret(secret_key: str) -> bool:
    secrets = _load_file_store()
    secrets.pop(secret_key, None)
    return _save_file_store(secrets)


def _get_keychain_secret(secret_key: str) -> str | None:
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-a",
                SECRET_STORE_ACCOUNT,
                "-s",
                _service_name(secret_key),
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

    value = str(result.stdout or "").strip()
    return value or None


def _delete_keychain_secret(secret_key: str) -> bool:
    service_name = _service_name(secret_key)

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


def _set_keychain_secret(secret_key: str, secret_value: str) -> bool:
    if not _delete_keychain_secret(secret_key):
        return False

    try:
        result = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-a",
                SECRET_STORE_ACCOUNT,
                "-s",
                _service_name(secret_key),
                "-w",
                secret_value,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False

    return result.returncode == 0


def get_secret(secret_key: str) -> str | None:
    key = str(secret_key or "").strip()

    if not key:
        return None

    if key in _SECRET_CACHE:
        value = str(_SECRET_CACHE.get(key) or "").strip()
        return value or None

    if _secret_store_backend() == "macos_keychain":
        value = _get_keychain_secret(key)
    else:
        value = _get_file_secret(key)

    if value:
        _SECRET_CACHE[key] = value

    return value or None


def set_secret(secret_key: str, secret_value: str) -> bool:
    key = str(secret_key or "").strip()
    value = str(secret_value or "").strip()

    if not key:
        return False

    if not value:
        return delete_secret(key)

    if _secret_store_backend() == "macos_keychain":
        saved = _set_keychain_secret(key, value)
    else:
        saved = _set_file_secret(key, value)

    if not saved:
        return False

    _SECRET_CACHE[key] = value
    return True


def delete_secret(secret_key: str) -> bool:
    key = str(secret_key or "").strip()

    if not key:
        return True

    _SECRET_CACHE.pop(key, None)

    if _secret_store_backend() == "macos_keychain":
        return _delete_keychain_secret(key)

    return _delete_file_secret(key)
