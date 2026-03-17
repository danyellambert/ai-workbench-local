from __future__ import annotations

from typing import Any, Optional

from ..config import get_rag_settings
from ..rag.service import retrieve_relevant_chunks_detailed


DEFAULT_DOCUMENT_SCAN_CHUNKS = 10
DEFAULT_DOCUMENT_SCAN_CHARS = 18000
DEFAULT_RETRIEVAL_CHUNKS = 8
DEFAULT_RETRIEVAL_CHARS = 14000


def _get_rag_index() -> dict[str, Any] | None:
    try:
        from .rag_state import get_rag_index
    except Exception:
        return None
    return get_rag_index()


def _get_embedding_provider():
    try:
        from ..providers.registry import build_provider_registry
    except Exception:
        return None
    registry = build_provider_registry()
    return registry.get("ollama", {}).get("instance")


def _filtered_chunks(rag_index: dict[str, Any], document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    chunks = rag_index.get("chunks", []) if isinstance(rag_index, dict) else []
    normalized = [chunk for chunk in chunks if isinstance(chunk, dict)]
    if document_ids:
        allowed = {str(item) for item in document_ids if item}
        normalized = [
            chunk
            for chunk in normalized
            if str(chunk.get("document_id") or chunk.get("file_hash") or "") in allowed
        ]
    return normalized


def _ordered_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(chunk: dict[str, Any]) -> tuple[str, int, int]:
        return (
            str(chunk.get("document_id") or chunk.get("file_hash") or "document"),
            int(chunk.get("chunk_id") or 0),
            int(chunk.get("start_char") or 0),
        )

    return sorted(chunks, key=_key)


def _join_chunk_context(chunks: list[dict[str, Any]], max_chars: int) -> str:
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        snippet = str(chunk.get("snippet") or chunk.get("text") or "").strip()
        if not snippet:
            continue
        source = str(chunk.get("source") or chunk.get("document_id") or "document")
        block = f"[Source: {source}]\n{snippet}"
        if used and used + len(block) + 2 > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


def build_document_scan_context(
    document_ids: list[str] | None = None,
    max_chunks: int = DEFAULT_DOCUMENT_SCAN_CHUNKS,
    max_chars: int = DEFAULT_DOCUMENT_SCAN_CHARS,
) -> str:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    chunks = _ordered_chunks(_filtered_chunks(rag_index, document_ids))
    if not chunks:
        return ""
    return _join_chunk_context(chunks[:max_chunks], max_chars=max_chars)


def build_retrieval_context(
    query: str,
    document_ids: list[str] | None = None,
    max_chunks: int = DEFAULT_RETRIEVAL_CHUNKS,
    max_chars: int = DEFAULT_RETRIEVAL_CHARS,
) -> str:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)

    embedding_provider = _get_embedding_provider()
    if embedding_provider is None:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)

    retrieval = retrieve_relevant_chunks_detailed(
        query=cleaned_query,
        rag_index=rag_index,
        settings=get_rag_settings(),
        embedding_provider=embedding_provider,
        document_ids=document_ids,
    )
    chunks = retrieval.get("chunks", []) if isinstance(retrieval, dict) else []
    if not chunks:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)
    return _join_chunk_context(chunks[:max_chunks], max_chars=max_chars)


def build_structured_document_context(
    *,
    query: str,
    document_ids: list[str] | None = None,
    strategy: str = "document_scan",
    max_chunks: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> str:
    strategy = (strategy or "document_scan").strip().lower()
    if strategy == "retrieval":
        return build_retrieval_context(
            query=query,
            document_ids=document_ids,
            max_chunks=max_chunks or DEFAULT_RETRIEVAL_CHUNKS,
            max_chars=max_chars or DEFAULT_RETRIEVAL_CHARS,
        )
    return build_document_scan_context(
        document_ids=document_ids,
        max_chunks=max_chunks or DEFAULT_DOCUMENT_SCAN_CHUNKS,
        max_chars=max_chars or DEFAULT_DOCUMENT_SCAN_CHARS,
    )
