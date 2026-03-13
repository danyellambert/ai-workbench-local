from __future__ import annotations

from math import sqrt
from pathlib import Path
from typing import Any


def _normalize_embedding(value: object) -> list[float] | None:
    if not isinstance(value, list):
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b:
        return 0.0

    size = min(len(vector_a), len(vector_b))
    if size == 0:
        return 0.0

    dot_product = sum(vector_a[i] * vector_b[i] for i in range(size))
    magnitude_a = sqrt(sum(vector_a[i] * vector_a[i] for i in range(size)))
    magnitude_b = sqrt(sum(vector_b[i] * vector_b[i] for i in range(size)))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _make_chunk_chroma_id(entry: dict[str, object], fallback_index: int) -> str:
    document_id = str(entry.get("document_id") or entry.get("file_hash") or "document")
    chunk_id = _coerce_int(entry.get("chunk_id"), fallback_index)
    start_char = _coerce_int(entry.get("start_char"), 0)
    end_char = _coerce_int(entry.get("end_char"), 0)
    return f"{document_id}::chunk::{chunk_id}::{start_char}::{end_char}"


class LocalVectorStore:
    def __init__(self, entries: list[dict[str, object]]):
        self.entries = entries

    def similarity_search(self, query_embedding: list[float], top_k: int) -> list[dict[str, object]]:
        scored_entries: list[dict[str, object]] = []

        for entry in self.entries:
            embedding = entry.get("embedding")
            if not isinstance(embedding, list):
                continue
            score = cosine_similarity(query_embedding, embedding)
            scored_entries.append({**entry, "score": round(score, 4)})

        scored_entries.sort(key=lambda item: item.get("score", 0), reverse=True)
        return scored_entries[:top_k]


class ChromaVectorStore:
    COLLECTION_NAME = "rag_chunks"

    def __init__(self, persist_path: Path):
        self.persist_path = Path(persist_path)

    def _get_collection(self):
        import chromadb

        self.persist_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.persist_path))
        return client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def clear(self) -> None:
        collection = self._get_collection()
        existing = collection.get(include=[])
        existing_ids = existing.get("ids") or []
        if existing_ids:
            collection.delete(ids=existing_ids)

    def rebuild(self, entries: list[dict[str, object]]) -> None:
        collection = self._get_collection()
        existing = collection.get(include=[])
        existing_ids = existing.get("ids") or []
        if existing_ids:
            collection.delete(ids=existing_ids)

        ids: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, object]] = []
        documents: list[str] = []
        seen_ids: set[str] = set()

        for index, entry in enumerate(entries):
            embedding = _normalize_embedding(entry.get("embedding"))
            if not embedding:
                continue

            chunk_chroma_id = _make_chunk_chroma_id(entry, index)
            if chunk_chroma_id in seen_ids:
                continue
            seen_ids.add(chunk_chroma_id)

            ids.append(chunk_chroma_id)
            embeddings.append(embedding)
            documents.append(str(entry.get("text", "")))
            metadatas.append(
                {
                    "source": str(entry.get("source", "documento")),
                    "chunk_id": _coerce_int(entry.get("chunk_id"), index),
                    "document_id": str(entry.get("document_id") or entry.get("file_hash") or "documento"),
                    "file_type": str(entry.get("file_type") or ""),
                    "snippet": str(entry.get("snippet") or ""),
                    "start_char": _coerce_int(entry.get("start_char"), 0),
                    "end_char": _coerce_int(entry.get("end_char"), 0),
                }
            )

        if ids:
            collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def delete_document_ids(self, document_ids: list[str]) -> int:
        ids_to_remove = [str(document_id) for document_id in document_ids if document_id]
        if not ids_to_remove:
            return 0

        collection = self._get_collection()
        existing = collection.get(where={"document_id": {"$in": ids_to_remove}}, include=[])
        chroma_ids = existing.get("ids") or []
        if not chroma_ids:
            return 0

        collection.delete(ids=chroma_ids)
        return len(chroma_ids)

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None = None,
        file_types: list[str] | None = None,
    ) -> list[dict[str, object]]:
        collection = self._get_collection()

        where_clauses: list[dict[str, object]] = []
        if document_ids:
            where_clauses.append({"document_id": {"$in": [str(item) for item in document_ids if item]}})
        if file_types:
            where_clauses.append({"file_type": {"$in": [str(item) for item in file_types if item]}})

        where: dict[str, object] | None = None
        if len(where_clauses) == 1:
            where = where_clauses[0]
        elif len(where_clauses) > 1:
            where = {"$and": where_clauses}

        query_kwargs: dict[str, object] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where is not None:
            query_kwargs["where"] = where

        results = collection.query(**query_kwargs)

        metadatas = (results.get("metadatas") or [[]])[0]
        documents = (results.get("documents") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        output: list[dict[str, object]] = []
        for metadata, document, distance in zip(metadatas, documents, distances):
            score = round(1 - float(distance), 4)
            output.append(
                {
                    "source": metadata.get("source"),
                    "chunk_id": metadata.get("chunk_id"),
                    "document_id": metadata.get("document_id"),
                    "file_type": metadata.get("file_type"),
                    "snippet": metadata.get("snippet"),
                    "start_char": metadata.get("start_char"),
                    "end_char": metadata.get("end_char"),
                    "text": document,
                    "score": score,
                }
            )
        return output
