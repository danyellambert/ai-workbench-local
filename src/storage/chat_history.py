import json
from pathlib import Path


VALID_ROLES = {"user", "assistant"}


def load_chat_history(history_path: Path) -> list[dict[str, str]]:
    if not history_path.exists():
        return []

    try:
        raw_data = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(raw_data, list):
        return []

    history: list[dict[str, str]] = []
    for item in raw_data:
        if (
            isinstance(item, dict)
            and item.get("role") in VALID_ROLES
            and isinstance(item.get("content"), str)
        ):
            history.append({"role": item["role"], "content": item["content"]})

    return history


def save_chat_history(history_path: Path, messages: list[dict[str, str]]) -> None:
    history_path.write_text(
        json.dumps(messages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_chat_history(history_path: Path) -> None:
    if history_path.exists():
        history_path.unlink()