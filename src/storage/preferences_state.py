from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_preferences_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_preferences_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_preferences_state(current: dict[str, Any] | None, patch: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(current or {})
    incoming = dict(patch or {})
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = merge_preferences_state(base.get(key), value)
        else:
            base[key] = value
    return base