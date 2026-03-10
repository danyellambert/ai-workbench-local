import time

from src.config import RagSettings
from src.rag.chunking import chunk_text
from src.rag.loaders import LoadedDocument
from src.rag.vector_store import LocalVectorStore


def build_rag_index(document: LoadedDocument, settings: RagSettings, embedding_provider) -> dict[str, object]:
    chunks = chunk_text(
        text=document.text,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        source_name=document.name,
    )

    if not chunks:
        raise RuntimeError("Não foi possível gerar chunks a partir do documento enviado.")

    embeddings = embedding_provider.create_embeddings(
        [chunk["text"] for chunk in chunks],
        model=settings.embedding_model,
    )

    indexed_chunks: list[dict[str, object]] = []
    for chunk, embedding in zip(chunks, embeddings):
        indexed_chunks.append({**chunk, "embedding": embedding})

    return {
        "document": {
            "name": document.name,
            "file_type": document.file_type,
            "file_hash": document.file_hash,
            "char_count": len(document.text),
        },
        "settings": {
            "embedding_model": settings.embedding_model,
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "top_k": settings.top_k,
        },
        "chunks": indexed_chunks,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def retrieve_relevant_chunks(
    query: str,
    rag_index: dict[str, object] | None,
    settings: RagSettings,
    embedding_provider,
) -> list[dict[str, object]]:
    if not rag_index:
        return []

    chunks = rag_index.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        return []

    query_embedding = embedding_provider.create_embeddings(
        [query],
        model=settings.embedding_model,
    )[0]

    store = LocalVectorStore(chunks)
    return store.similarity_search(query_embedding, settings.top_k)


def build_source_metadata(chunks: list[dict[str, object]]) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    for chunk in chunks:
        sources.append(
            {
                "source": chunk.get("source"),
                "chunk_id": chunk.get("chunk_id"),
                "score": chunk.get("score"),
                "snippet": chunk.get("snippet") or str(chunk.get("text", ""))[:400],
            }
        )
    return sources