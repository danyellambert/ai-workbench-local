import json
from pathlib import Path


def _document_catalog_path(store_path: Path) -> Path:
    return store_path.with_name(f"{store_path.stem}_documents.json")


def _extract_documents_from_store(store_path: Path) -> list[dict[str, object]] | None:
    start_marker = b'"documents":'
    end_marker = b',"chunks":'
    buffer = bytearray()
    found_start = False

    try:
        with store_path.open("rb") as handle:
            while True:
                chunk = handle.read(64 * 1024)
                if not chunk:
                    break
                buffer.extend(chunk)

                if not found_start:
                    start_index = buffer.find(start_marker)
                    if start_index == -1:
                        if len(buffer) > len(start_marker) * 4:
                            buffer = buffer[-len(start_marker) * 4 :]
                        continue
                    buffer = buffer[start_index + len(start_marker) :]
                    found_start = True

                end_index = buffer.find(end_marker)
                if end_index != -1:
                    payload = json.loads(buffer[:end_index].decode("utf-8"))
                    if isinstance(payload, list):
                        return [item for item in payload if isinstance(item, dict)]
                    return None

                if len(buffer) > 8 * 1024 * 1024:
                    return None
    except (OSError, json.JSONDecodeError):
        return None

    return None


def load_rag_document_catalog(store_path: Path) -> list[dict[str, object]] | None:
    catalog_path = _document_catalog_path(store_path)
    if catalog_path.exists():
        try:
            payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            documents = payload.get("documents") if isinstance(payload, dict) else payload
            if isinstance(documents, list):
                return [item for item in documents if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError, AttributeError):
            pass

    documents = _extract_documents_from_store(store_path)
    if documents is not None:
        try:
            catalog_path.parent.mkdir(parents=True, exist_ok=True)
            catalog_path.write_text(
                json.dumps({"documents": documents}, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        except OSError:
            pass
        return documents

    return None


def load_rag_store(store_path: Path) -> dict[str, object] | None:
    if not store_path.exists():
        return None

    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    return data if isinstance(data, dict) else None


def save_rag_store(store_path: Path, data: dict[str, object]) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    documents = data.get("documents") if isinstance(data, dict) else None
    if isinstance(documents, list):
        catalog_path = _document_catalog_path(store_path)
        catalog_path.write_text(
            json.dumps({"documents": documents}, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )


def clear_rag_store(store_path: Path) -> None:
    if store_path.exists():
        store_path.unlink()

    catalog_path = _document_catalog_path(store_path)
    if catalog_path.exists():
        catalog_path.unlink()