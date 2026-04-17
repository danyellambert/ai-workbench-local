from __future__ import annotations

import getpass
import subprocess


SECRET_STORE_SERVICE_PREFIX = "ai-workbench-local"
SECRET_STORE_ACCOUNT = getpass.getuser() or "workspace"


def _service_name(secret_key: str) -> str:
    normalized = str(secret_key or "").strip()
    return f"{SECRET_STORE_SERVICE_PREFIX}:{normalized}"


def get_secret(secret_key: str) -> str | None:
    service_name = _service_name(secret_key)
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


def set_secret(secret_key: str, secret_value: str) -> bool:
    service_name = _service_name(secret_key)
    try:
        result = subprocess.run(
            [
                "security",
                "add-generic-password",
                "-U",
                "-a",
                SECRET_STORE_ACCOUNT,
                "-s",
                service_name,
                "-w",
                str(secret_value),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def delete_secret(secret_key: str) -> bool:
    service_name = _service_name(secret_key)
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
    return result.returncode == 0