import time

from src.config import RagSettings
from src.rag.chunking import chunk_text
from src.rag.loaders import LoadedDocument
from src.rag.vector_store import LocalVectorStore


def _settings_payload(settings: RagSettings) -> dict[str, object]:
    return {
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "top_k": settings.top_k,
    }


def _coerce_rag_index(rag_index: dict[str, object] | None, settings: RagSettings) -> dict[str, object]:
    if not isinstance(rag_index, dict):
        return {
            "documents": [],
            "chunks": [],
            "settings": _settings_payload(settings),
            "updated_at": None,
        }

    if isinstance(rag_index.get("documents"), list) and isinstance(rag_index.get("chunks"), list):
        return {
            "documents": rag_index.get("documents", []),
            "chunks": rag_index.get("chunks", []),
            "settings": rag_index.get("settings", _settings_payload(settings)),
            "updated_at": rag_index.get("updated_at") or rag_index.get("created_at"),
        }

    document = rag_index.get("document")
    chunks = rag_index.get("chunks")
    if isinstance(document, dict) and isinstance(chunks, list):
        document_id = document.get("file_hash") or document.get("name") or "document"
        migrated_document = {
            "document_id": document_id,
            "name": document.get("name"),
            "file_type": document.get("file_type"),
            "file_hash": document.get("file_hash"),
            "char_count": document.get("char_count"),
            "chunk_count": len(chunks),
            "indexed_at": rag_index.get("created_at"),
        }
        migrated_chunks: list[dict[str, object]] = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            migrated_chunks.append(
                {
                    **chunk,
                    "document_id": document_id,
                    "file_hash": document.get("file_hash"),
                    "file_type": document.get("file_type"),
                    "source": chunk.get("source") or document.get("name"),
                }
            )

        return {
            "documents": [migrated_document],
            "chunks": migrated_chunks,
            "settings": rag_index.get("settings", _settings_payload(settings)),
            "updated_at": rag_index.get("created_at"),
        }

    return {
        "documents": [],
        "chunks": [],
        "settings": _settings_payload(settings),
        "updated_at": None,
    }


def normalize_rag_index(rag_index: dict[str, object] | None, settings: RagSettings) -> dict[str, object] | None:
    normalized = _coerce_rag_index(rag_index, settings)
    if not normalized["documents"] and not normalized["chunks"]:
        return None
    return normalized


def get_indexed_documents(rag_index: dict[str, object] | None, settings: RagSettings) -> list[dict[str, object]]:
    normalized = _coerce_rag_index(rag_index, settings)
    documents = normalized.get("documents", [])
    return [document for document in documents if isinstance(document, dict)]


def upsert_documents_in_rag_index(
    documents: list[LoadedDocument],
    settings: RagSettings,
    embedding_provider,
    rag_index: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized = _coerce_rag_index(rag_index, settings)
    document_ids_to_replace = {document.file_hash for document in documents}

    existing_documents = {
        document.get("document_id") or document.get("file_hash"): document
        for document in normalized.get("documents", [])
        if isinstance(document, dict)
    }
    existing_chunks = [
        chunk
        for chunk in normalized.get("chunks", [])
        if isinstance(chunk, dict) and (chunk.get("document_id") or chunk.get("file_hash")) not in document_ids_to_replace
    ]

    now = time.strftime("%Y-%m-%d %H:%M:%S")

    for document in documents:
        document_id = document.file_hash
        chunks = chunk_text(
            text=document.text,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            source_name=document.name,
        )

        if not chunks:
            raise RuntimeError(f"Não foi possível gerar chunks a partir do documento `{document.name}`.")

        embeddings = embedding_provider.create_embeddings(
            [chunk["text"] for chunk in chunks],
            model=settings.embedding_model,
        )

        indexed_chunks: list[dict[str, object]] = []
        for chunk, embedding in zip(chunks, embeddings):
            indexed_chunks.append(
                {
                    **chunk,
                    "embedding": embedding,
                    "document_id": document_id,
                    "file_hash": document.file_hash,
                    "file_type": document.file_type,
                }
            )

        existing_documents[document_id] = {
            "document_id": document_id,
            "name": document.name,
            "file_type": document.file_type,
            "file_hash": document.file_hash,
            "char_count": len(document.text),
            "chunk_count": len(indexed_chunks),
            "indexed_at": now,
        }
        existing_chunks.extend(indexed_chunks)

    return {
        "documents": list(existing_documents.values()),
        "chunks": existing_chunks,
        "settings": _settings_payload(settings),
        "updated_at": now,
    }


def remove_documents_from_rag_index(
    rag_index: dict[str, object] | None,
    settings: RagSettings,
    document_ids: list[str],
) -> dict[str, object] | None:
    normalized = _coerce_rag_index(rag_index, settings)
    document_ids_set = set(document_ids)

    remaining_documents = [
        document
        for document in normalized.get("documents", [])
        if isinstance(document, dict)
        and (document.get("document_id") or document.get("file_hash")) not in document_ids_set
    ]
    remaining_chunks = [
        chunk
        for chunk in normalized.get("chunks", [])
        if isinstance(chunk, dict)
        and (chunk.get("document_id") or chunk.get("file_hash")) not in document_ids_set
    ]

    if not remaining_documents:
        return None

    return {
        "documents": remaining_documents,
        "chunks": remaining_chunks,
        "settings": normalized.get("settings", _settings_payload(settings)),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def retrieve_relevant_chunks(
    query: str,
    rag_index: dict[str, object] | None,
    settings: RagSettings,
    embedding_provider,
    document_ids: list[str] | None = None,
    file_types: list[str] | None = None,
) -> list[dict[str, object]]:
    normalized = _coerce_rag_index(rag_index, settings)
    chunks = normalized.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        return []

    filtered_chunks = [chunk for chunk in chunks if isinstance(chunk, dict)]

    if document_ids is not None:
        document_ids_set = set(document_ids)
        filtered_chunks = [
            chunk
            for chunk in filtered_chunks
            if (chunk.get("document_id") or chunk.get("file_hash")) in document_ids_set
        ]

    if file_types is not None:
        file_types_set = set(file_types)
        filtered_chunks = [chunk for chunk in filtered_chunks if chunk.get("file_type") in file_types_set]

    if not filtered_chunks:
        return []

    query_embedding = embedding_provider.create_embeddings(
        [query],
        model=settings.embedding_model,
    )[0]

    store = LocalVectorStore(filtered_chunks)
    return store.similarity_search(query_embedding, settings.top_k)


def build_source_metadata(chunks: list[dict[str, object]]) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    for chunk in chunks:
        sources.append(
            {
                "source": chunk.get("source"),
                "document_id": chunk.get("document_id"),
                "file_type": chunk.get("file_type"),
                "chunk_id": chunk.get("chunk_id"),
                "score": chunk.get("score"),
                "snippet": chunk.get("snippet") or str(chunk.get("text", ""))[:400],
            }
        )
    return sources