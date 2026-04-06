from __future__ import annotations

from typing import Any

from src.config import RagSettings


def describe_retrieval_strategy(strategy: str) -> str:
    labels = {
        "manual_hybrid": "Manual hybrid",
        "langchain_chroma": "LangChain + Chroma (experimental)",
    }
    return labels.get((strategy or "").strip().lower(), strategy or "manual_hybrid")


def resolve_retrieval_strategy(strategy: str | None) -> tuple[str, str, str | None]:
    requested = (strategy or "manual_hybrid").strip().lower() or "manual_hybrid"
    if requested == "manual_hybrid":
        return requested, "manual_hybrid", None
    if requested == "langchain_chroma":
        try:
            from langchain_chroma import Chroma  # noqa: F401
        except Exception:
            return requested, "manual_hybrid", "langchain_chroma_not_installed"
        return requested, "langchain_chroma", None
    return requested, "manual_hybrid", "unknown_strategy"


class ProviderBackedEmbeddings:
    def __init__(self, provider: Any, settings: RagSettings):
        self.provider = provider
        self.settings = settings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.provider.create_embeddings(
            texts,
            model=self.settings.embedding_model,
            context_window=self.settings.embedding_context_window,
            truncate=self.settings.embedding_truncate,
        )

    def embed_query(self, text: str) -> list[float]:
        embeddings = self.provider.create_embeddings(
            [text],
            model=self.settings.embedding_model,
            context_window=self.settings.embedding_context_window,
            truncate=self.settings.embedding_truncate,
        )
        return embeddings[0] if embeddings else []


def _build_where_filter(
    document_ids: list[str] | None = None,
    file_types: list[str] | None = None,
) -> dict[str, object] | None:
    clauses: list[dict[str, object]] = []
    if document_ids:
        clauses.append({"document_id": {"$in": [str(item) for item in document_ids if item]}})
    if file_types:
        clauses.append({"file_type": {"$in": [str(item) for item in file_types if item]}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def similarity_search_with_langchain_chroma(
    *,
    query: str,
    settings: RagSettings,
    embedding_provider: Any,
    top_k: int,
    document_ids: list[str] | None = None,
    file_types: list[str] | None = None,
) -> tuple[list[dict[str, object]], str | None]:
    requested, effective, fallback_reason = resolve_retrieval_strategy("langchain_chroma")
    if effective != "langchain_chroma":
        return [], fallback_reason or "langchain_strategy_unavailable"

    try:
        from langchain_chroma import Chroma
    except Exception:
        return [], "langchain_chroma_not_installed"

    try:
        vectorstore = Chroma(
            collection_name="rag_chunks",
            persist_directory=str(settings.chroma_path),
            embedding_function=ProviderBackedEmbeddings(embedding_provider, settings),
        )
        where_filter = _build_where_filter(document_ids=document_ids, file_types=file_types)
        results = vectorstore.similarity_search_with_relevance_scores(
            query,
            k=top_k,
            filter=where_filter,
        )
    except Exception as error:
        return [], f"langchain_query_failed:{error}"

    output: list[dict[str, object]] = []
    for document, score in results:
        metadata = dict(getattr(document, "metadata", {}) or {})
        output.append(
            {
                "source": metadata.get("source"),
                "chunk_id": metadata.get("chunk_id"),
                "document_id": metadata.get("document_id"),
                "file_type": metadata.get("file_type"),
                "snippet": metadata.get("snippet"),
                "start_char": metadata.get("start_char"),
                "end_char": metadata.get("end_char"),
                "text": getattr(document, "page_content", "") or "",
                "score": round(float(score), 4),
                "retrieval_strategy_requested": requested,
                "retrieval_strategy_used": "langchain_chroma",
            }
        )
    return output, None