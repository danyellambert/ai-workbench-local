import json
from pathlib import Path


VALID_ROLES = {"user", "assistant"}


def _sanitize_metadata(metadata: object) -> dict[str, object]:
    if not isinstance(metadata, dict):
        return {}

    sanitized: dict[str, object] = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value

    return sanitized


def load_chat_history(history_path: Path) -> list[dict[str, object]]:
    if not history_path.exists():
        return []

    try:
        raw_data = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(raw_data, list):
        return []

    history: list[dict[str, object]] = []
    for item in raw_data:
        if (
            isinstance(item, dict)
            and item.get("role") in VALID_ROLES
            and isinstance(item.get("content"), str)
        ):
            sanitized_item: dict[str, object] = {"role": item["role"], "content": item["content"]}
            metadata = _sanitize_metadata(item.get("metadata"))
            if metadata:
                sanitized_item["metadata"] = metadata
            history.append(sanitized_item)

    return history


def save_chat_history(history_path: Path, messages: list[dict[str, object]]) -> None:
    history_path.write_text(
        json.dumps(messages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear_chat_history(history_path: Path) -> None:
    if history_path.exists():
        history_path.unlink()