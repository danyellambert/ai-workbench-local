from __future__ import annotations

import math
import os
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from src.config import RagSettings
from src.rag.service import normalize_rag_index, sync_chroma_from_rag_index
from src.storage.rag_store import load_rag_store, save_rag_store
from src.storage.runtime_paths import get_runtime_root

PREINDEX_KIND = "evidenceops_preindexed_corpus.v1"
DEFAULT_PREINDEX_RELATIVE_PATH = Path("state") / "rag" / "preindexed_public_corpus.json"


def _truthy_env(name: str, default: bool = True) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def preindexed_fast_import_enabled() -> bool:
    return _truthy_env("EVIDENCEOPS_PREINDEX_FAST_IMPORT_ENABLED", True)


def get_preindexed_store_path(workspace_root: str | Path) -> Path:
    explicit = str(os.getenv("EVIDENCEOPS_PREINDEX_STORE_PATH", "")).strip()
    if explicit:
        return Path(explicit).expanduser()
    return get_runtime_root(Path(workspace_root)) / DEFAULT_PREINDEX_RELATIVE_PATH


def load_preindexed_store(workspace_root: str | Path) -> dict[str, Any] | None:
    payload = load_rag_store(get_preindexed_store_path(workspace_root))
    if not isinstance(payload, dict):
        return None
    documents = payload.get("documents")
    chunks = payload.get("chunks")
    if not isinstance(documents, list) or not isinstance(chunks, list):
        return None
    return payload


def _normalize_key(value: object) -> str:
    return "".join(character.lower() for character in str(value or "") if character.isalnum())


def _path_tail(value: object) -> str:
    return Path(str(value or "").strip()).name


def _document_locator_values(document: dict[str, Any]) -> list[str]:
    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    preindex = metadata.get("preindex") if isinstance(metadata.get("preindex"), dict) else {}
    values = [
        document.get("document_id"),
        document.get("file_hash"),
        document.get("name"),
        metadata.get("nextcloud_relative_path"),
        metadata.get("relative_path"),
        metadata.get("source_relative_path"),
        metadata.get("title"),
        metadata.get("filename"),
        preindex.get("relative_path"),
        preindex.get("title"),
        preindex.get("filename"),
        preindex.get("document_id"),
    ]
    expanded: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        expanded.append(normalized)
        tail = _path_tail(normalized)
        if tail and tail != normalized:
            expanded.append(tail)
    return expanded


def _import_locator_values(import_item: dict[str, Any]) -> list[str]:
    values = [
        import_item.get("relative_path"),
        import_item.get("document_id"),
        import_item.get("filename"),
        import_item.get("title"),
        import_item.get("webdav_url"),
    ]
    expanded: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        expanded.append(normalized)
        tail = _path_tail(normalized)
        if tail and tail != normalized:
            expanded.append(tail)
    return expanded


def _preindex_documents(payload: dict[str, Any]) -> list[dict[str, Any]]:
    documents = payload.get("documents")
    return [item for item in documents if isinstance(item, dict)] if isinstance(documents, list) else []


def _preindex_chunks_for_document(payload: dict[str, Any], document_id: str) -> list[dict[str, Any]]:
    chunks = payload.get("chunks")
    if not isinstance(chunks, list):
        return []
    return [
        chunk
        for chunk in chunks
        if isinstance(chunk, dict)
        and str(chunk.get("document_id") or chunk.get("file_hash") or "") == document_id
    ]


def find_preindexed_document(workspace_root: str | Path, import_item: dict[str, Any]) -> dict[str, Any] | None:
    if not preindexed_fast_import_enabled():
        return None
    store = load_preindexed_store(workspace_root)
    if not isinstance(store, dict):
        return None

    requested_keys = {_normalize_key(value) for value in _import_locator_values(import_item) if _normalize_key(value)}
    if not requested_keys:
        return None

    store_path = get_preindexed_store_path(workspace_root)
    corpus_stats = _preindex_corpus_simulation_stats(store)

    # Prefer exact normalized-key matches against the locator metadata produced by
    # the preindexing script.
    for document in _preindex_documents(store):
        document_keys = {_normalize_key(value) for value in _document_locator_values(document) if _normalize_key(value)}
        if requested_keys & document_keys:
            document_id = str(document.get("document_id") or document.get("file_hash") or "").strip()
            chunks = _preindex_chunks_for_document(store, document_id)
            if document_id and chunks:
                return {
                    "document": deepcopy(document),
                    "chunks": deepcopy(chunks),
                    "preindex_store": str(store_path),
                    "corpus_stats": dict(corpus_stats),
                }

    return None


def _metadata_for_entry(entry: dict[str, Any]) -> dict[str, Any]:
    document = entry.get("document") if isinstance(entry.get("document"), dict) else {}
    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    return metadata


def source_payload_for_preindexed_entry(entry: dict[str, Any]) -> dict[str, Any]:
    document = entry.get("document") if isinstance(entry.get("document"), dict) else {}
    metadata = _metadata_for_entry(entry)
    preindex = metadata.get("preindex") if isinstance(metadata.get("preindex"), dict) else {}
    relative_path = str(
        preindex.get("relative_path")
        or metadata.get("nextcloud_relative_path")
        or metadata.get("relative_path")
        or document.get("name")
        or ""
    ).strip()
    filename = str(preindex.get("filename") or metadata.get("filename") or Path(relative_path).name or document.get("name") or "document").strip()
    return {
        "relative_path": relative_path or None,
        "title": str(preindex.get("title") or metadata.get("title") or document.get("name") or filename).strip() or filename,
        "document_id": str(document.get("document_id") or document.get("file_hash") or preindex.get("document_id") or "").strip() or None,
        "filename": filename,
    }


def _safe_float_env(name: str, default: float) -> float:
    raw = str(os.getenv(name, "")).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return max(0, int(value or default))
    except (TypeError, ValueError):
        return default


def _document_chunk_text(chunk: dict[str, Any]) -> str:
    for key in ("text", "content", "page_content", "chunk_text"):
        value = chunk.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _document_char_count(document: dict[str, Any], chunks: list[dict[str, Any]] | None = None) -> int:
    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    preindex = metadata.get("preindex") if isinstance(metadata.get("preindex"), dict) else {}
    for value in (
        document.get("char_count"),
        metadata.get("char_count"),
        metadata.get("text_char_count"),
        preindex.get("char_count"),
        preindex.get("text_char_count"),
    ):
        count = _safe_int(value)
        if count > 0:
            return count
    if chunks:
        return sum(len(_document_chunk_text(chunk)) for chunk in chunks if isinstance(chunk, dict))
    return 0


def _document_chunk_count(document: dict[str, Any], chunks: list[dict[str, Any]] | None = None) -> int:
    count = _safe_int(document.get("chunk_count"))
    if count > 0:
        return count
    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    preindex = metadata.get("preindex") if isinstance(metadata.get("preindex"), dict) else {}
    count = _safe_int(metadata.get("chunk_count") or preindex.get("chunk_count"))
    if count > 0:
        return count
    return len(chunks or [])


def _preindex_corpus_simulation_stats(payload: dict[str, Any]) -> dict[str, int]:
    """Return stable corpus-wide size references for realistic simulated ingest timing."""
    max_char_count = 0
    max_chunk_count = 0
    for document in _preindex_documents(payload):
        document_id = str(document.get("document_id") or document.get("file_hash") or "").strip()
        chunks = _preindex_chunks_for_document(payload, document_id) if document_id else []
        max_char_count = max(max_char_count, _document_char_count(document, chunks))
        max_chunk_count = max(max_chunk_count, _document_chunk_count(document, chunks))
    return {"max_char_count": max_char_count, "max_chunk_count": max_chunk_count}


def _simulation_profile(entries: list[dict[str, Any]]) -> dict[str, int]:
    max_char_count = 0
    max_chunk_count = 0
    for entry in entries:
        corpus_stats = entry.get("corpus_stats") if isinstance(entry.get("corpus_stats"), dict) else {}
        max_char_count = max(max_char_count, _safe_int(corpus_stats.get("max_char_count")))
        max_chunk_count = max(max_chunk_count, _safe_int(corpus_stats.get("max_chunk_count")))
        document = entry.get("document") if isinstance(entry.get("document"), dict) else {}
        chunks = entry.get("chunks") if isinstance(entry.get("chunks"), list) else []
        max_char_count = max(max_char_count, _document_char_count(document, chunks))
        max_chunk_count = max(max_chunk_count, _document_chunk_count(document, chunks))
    return {"max_char_count": max_char_count, "max_chunk_count": max_chunk_count}


def _simulation_total_seconds(
    *,
    document: dict[str, Any],
    chunks: list[dict[str, Any]],
    profile: dict[str, int],
) -> float:
    minimum = _safe_float_env("EVIDENCEOPS_PREINDEX_SIM_MIN_SECONDS", 1.75)
    maximum = _safe_float_env("EVIDENCEOPS_PREINDEX_SIM_MAX_SECONDS", 15.0)
    if maximum < minimum:
        maximum = minimum
    curve = max(0.2, min(1.5, _safe_float_env("EVIDENCEOPS_PREINDEX_SIM_CURVE", 0.62)))

    char_count = _document_char_count(document, chunks)
    chunk_count = _document_chunk_count(document, chunks)
    reference_chars = max(1, _safe_int(profile.get("max_char_count")) or char_count or 1)
    reference_chunks = max(1, _safe_int(profile.get("max_chunk_count")) or chunk_count or 1)

    # The perceived wait should scale against the biggest preindexed document in
    # the corpus, not against a fixed 45k-char heuristic. This makes a 350k-char
    # contract feel heavier than a 9k-char note while keeping the demo capped.
    char_ratio = min(1.0, char_count / reference_chars) if char_count else 0.0
    chunk_ratio = min(1.0, chunk_count / reference_chunks) if chunk_count else 0.0
    blended_ratio = (0.82 * char_ratio) + (0.18 * chunk_ratio)

    # Keep tiny documents visible but short. A power curve gives useful
    # separation between 9k, 45k, 150k and 350k-char documents.
    shaped_ratio = max(0.0, min(1.0, blended_ratio)) ** curve
    return max(minimum, min(maximum, minimum + ((maximum - minimum) * shaped_ratio)))


def simulate_preindexed_document_stages(
    *,
    job_id: str,
    entries: list[dict[str, Any]],
    update_stage: Callable[..., Any],
    reset_steps: Callable[..., Any] | None = None,
    start_document: int = 1,
    total_documents: int | None = None,
    profile: dict[str, int] | None = None,
) -> None:
    display_total = int(total_documents or len(entries) or 0)
    timing_profile = profile or _simulation_profile(entries)
    stage_weights = {
        "extraction": 0.30,
        "chunking": 0.18,
        "embeddings": 0.32,
    }
    for offset, entry in enumerate(entries):
        position = int(start_document) + offset
        document = entry.get("document") if isinstance(entry.get("document"), dict) else {}
        chunks = entry.get("chunks") if isinstance(entry.get("chunks"), list) else []
        metadata = _metadata_for_entry(entry)
        name = str(document.get("name") or metadata.get("filename") or f"Document {position}")
        if reset_steps is not None:
            reset_steps(
                job_id,
                message=f"Indexing {name} ({position}/{display_total}).",
                document_name=name,
                current_document=position,
                total_documents=display_total,
            )
        char_count = _document_char_count(document, chunks)
        chunk_count = _document_chunk_count(document, chunks)
        page_count = metadata.get("page_count")
        total_seconds = _simulation_total_seconds(document=document, chunks=chunks, profile=timing_profile)
        base_metadata = {
            "document_name": name,
            "current_document": position,
            "total_documents": display_total,
            "char_count": char_count,
            "chunk_count": chunk_count,
            "page_count": page_count,
            "simulated_total_seconds": round(total_seconds, 2),
            "simulation_reference_char_count": timing_profile.get("max_char_count"),
            "simulation_reference_chunk_count": timing_profile.get("max_chunk_count"),
        }

        update_stage(
            job_id,
            "extraction",
            status="running",
            detail=f"Extracting {name} ({position}/{display_total}).",
            metadata={**base_metadata, "progress_pct": 25.0},
        )
        time.sleep(max(0.05, total_seconds * stage_weights["extraction"]))
        update_stage(
            job_id,
            "extraction",
            status="completed",
            detail=f"Extraction completed for {name}.",
            metadata={**base_metadata, "progress_pct": 100.0},
        )

        update_stage(
            job_id,
            "chunking",
            status="running",
            detail=f"Chunking {name} ({position}/{display_total}).",
            metadata={**base_metadata, "processed_chunks": 0, "total_chunks": chunk_count, "progress_pct": 35.0},
        )
        time.sleep(max(0.05, total_seconds * stage_weights["chunking"]))
        update_stage(
            job_id,
            "chunking",
            status="completed",
            detail=f"{chunk_count} chunk(s) created for {name}.",
            metadata={**base_metadata, "processed_chunks": chunk_count, "total_chunks": chunk_count, "progress_pct": 100.0},
        )

        update_stage(
            job_id,
            "embeddings",
            status="running",
            detail=f"Generating embeddings for {name} ({chunk_count} chunk(s)).",
            metadata={**base_metadata, "processed_chunks": max(0, chunk_count // 3), "total_chunks": chunk_count, "progress_pct": 35.0},
        )
        time.sleep(max(0.05, total_seconds * stage_weights["embeddings"]))
        update_stage(
            job_id,
            "embeddings",
            status="completed",
            detail=f"Embeddings ready for {name}.",
            metadata={**base_metadata, "processed_chunks": chunk_count, "total_chunks": chunk_count, "progress_pct": 100.0},
        )


def activate_preindexed_documents(
    *,
    entries: list[dict[str, Any]],
    rag_settings: RagSettings,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
) -> tuple[dict[str, Any], dict[str, object]]:
    current_index = normalize_rag_index(load_rag_store(rag_settings.store_path), rag_settings) or {
        "documents": [],
        "chunks": [],
        "settings": {},
        "updated_at": None,
    }
    existing_documents = [item for item in current_index.get("documents", []) if isinstance(item, dict)]
    existing_chunks = [item for item in current_index.get("chunks", []) if isinstance(item, dict)]

    replacement_ids = {
        str((entry.get("document") or {}).get("document_id") or (entry.get("document") or {}).get("file_hash") or "").strip()
        for entry in entries
        if isinstance(entry.get("document"), dict)
    }
    replacement_ids = {item for item in replacement_ids if item}
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    activated_documents: list[dict[str, Any]] = []
    activated_chunks: list[dict[str, Any]] = []
    for entry in entries:
        document = deepcopy(entry.get("document") if isinstance(entry.get("document"), dict) else {})
        document_id = str(document.get("document_id") or document.get("file_hash") or "").strip()
        if not document_id:
            continue
        metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
        metadata = {
            **metadata,
            "source_type": "nextcloud",
        }
        document.update({"document_id": document_id, "file_hash": document.get("file_hash") or document_id, "indexed_at": now, "loader_metadata": metadata})
        activated_documents.append(document)
        entry_chunks = entry.get("chunks")
        for chunk in (entry_chunks if isinstance(entry_chunks, list) else []):
            if not isinstance(chunk, dict):
                continue
            normalized_chunk = deepcopy(chunk)
            normalized_chunk.update({"document_id": document_id, "file_hash": document.get("file_hash") or document_id, "loader_metadata": metadata})
            activated_chunks.append(normalized_chunk)

    remaining_documents = [
        document
        for document in existing_documents
        if str(document.get("document_id") or document.get("file_hash") or "") not in replacement_ids
    ]
    remaining_chunks = [
        chunk
        for chunk in existing_chunks
        if str(chunk.get("document_id") or chunk.get("file_hash") or "") not in replacement_ids
    ]

    updated_index = {
        "documents": [*remaining_documents, *activated_documents],
        "chunks": [*remaining_chunks, *activated_chunks],
        "settings": current_index.get("settings") or {},
        "updated_at": now,
    }
    save_rag_store(rag_settings.store_path, updated_index)

    if _truthy_env("EVIDENCEOPS_PREINDEX_SYNC_CHROMA_ON_IMPORT", True):
        sync_status = sync_chroma_from_rag_index(rag_settings, updated_index, progress_callback=progress_callback)
    else:
        sync_status = {
            "ok": True,
            "backend": "json_only",
            "chunks_in_json": len(updated_index["chunks"]),
            "message": "Preindexed corpus activated in the canonical JSON store; Chroma sync was disabled by environment.",
        }
    return updated_index, sync_status
