import json
from pathlib import Path


def load_rag_store(store_path: Path) -> dict[str, object] | None:
    if not store_path.exists():
        return None

    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def save_rag_store(store_path: Path, data: dict[str, object]) -> None:
    store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_rag_store(store_path: Path) -> None:
    if store_path.exists():
        store_path.unlink()