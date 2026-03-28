from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from src.config import RagSettings
from src.rag.chunking import chunk_text, describe_chunking_strategy
from src.rag.langchain_adapter import (
    describe_retrieval_strategy,
    resolve_retrieval_strategy,
    similarity_search_with_langchain_chroma,
)
from src.rag.loaders import LoadedDocument
from src.rag.reranking import build_candidate_pool_size, hybrid_rerank_chunks, rank_chunks_lexically
from src.rag.vector_store import ChromaVectorStore, LocalVectorStore



def _compress_embedding(embedding: list[float]) -> list[float]:
    return [round(float(value), 6) for value in embedding]



def _settings_payload(settings: RagSettings) -> dict[str, object]:
    return {
        "loader_strategy": settings.loader_strategy,
        "chunking_strategy": settings.chunking_strategy,
        "retrieval_strategy": settings.retrieval_strategy,
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_context_window": settings.embedding_context_window,
        "embedding_truncate": settings.embedding_truncate,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "top_k": settings.top_k,
        "rerank_pool_size": settings.rerank_pool_size,
        "rerank_lexical_weight": settings.rerank_lexical_weight,
        "context_budget_ratio": settings.context_budget_ratio,
        "pdf_extraction_mode": settings.pdf_extraction_mode,
        "pdf_docling_enabled": settings.pdf_docling_enabled,
        "pdf_docling_ocr_enabled": settings.pdf_docling_ocr_enabled,
        "pdf_docling_force_full_page_ocr": settings.pdf_docling_force_full_page_ocr,
        "pdf_docling_picture_description": settings.pdf_docling_picture_description,
        "pdf_ocr_fallback_enabled": settings.pdf_ocr_fallback_enabled,
        "pdf_ocr_fallback_languages": settings.pdf_ocr_fallback_languages,
    }



def _coerce_rag_index(rag_index: dict[str, object] | None, settings: RagSettings) -> dict[str, object]:
    if not isinstance(rag_index, dict):
        return {
            "documents": [],
            "chunks": [],
            "settings": _settings_payload(settings),
            "updated_at": None,
        }

    if not isinstance(rag_index.get("documents"), list) and isinstance(rag_index.get("chunks"), list):
        legacy_chunks = [chunk for chunk in rag_index.get("chunks", []) if isinstance(chunk, dict)]
        grouped_documents: dict[str, dict[str, object]] = {}
        migrated_chunks: list[dict[str, object]] = []

        for chunk in legacy_chunks:
            normalized_chunk = dict(chunk)
            embedding = normalized_chunk.get("embedding")
            if isinstance(embedding, list):
                normalized_chunk["embedding"] = _compress_embedding(embedding)

            source_name = str(normalized_chunk.get("source") or "documento")
            document_id = str(normalized_chunk.get("document_id") or normalized_chunk.get("file_hash") or source_name)
            file_type = normalized_chunk.get("file_type")

            grouped = grouped_documents.setdefault(
                document_id,
                {
                    "document_id": document_id,
                    "name": source_name,
                    "file_type": file_type,
                    "file_hash": normalized_chunk.get("file_hash"),
                    "char_count": 0,
                    "chunk_count": 0,
                    "indexed_at": rag_index.get("updated_at") or rag_index.get("created_at"),
                    "loader_metadata": normalized_chunk.get("loader_metadata") or {},
                },
            )

            text_value = str(normalized_chunk.get("text", ""))
            grouped["char_count"] = int(grouped.get("char_count", 0)) + len(text_value)
            grouped["chunk_count"] = int(grouped.get("chunk_count", 0)) + 1

            migrated_chunks.append(
                {
                    **normalized_chunk,
                    "document_id": document_id,
                    "source": source_name,
                    "file_type": file_type,
                }
            )

        return {
            "documents": list(grouped_documents.values()),
            "chunks": migrated_chunks,
            "settings": rag_index.get("settings", _settings_payload(settings)),
            "updated_at": rag_index.get("updated_at") or rag_index.get("created_at"),
        }

    if isinstance(rag_index.get("documents"), list) and isinstance(rag_index.get("chunks"), list):
        normalized_chunks: list[dict[str, object]] = []
        for chunk in rag_index.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            normalized_chunk = dict(chunk)
            embedding = normalized_chunk.get("embedding")
            if isinstance(embedding, list):
                normalized_chunk["embedding"] = _compress_embedding(embedding)
            normalized_chunks.append(normalized_chunk)

        return {
            "documents": rag_index.get("documents", []),
            "chunks": normalized_chunks,
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
            "loader_metadata": document.get("loader_metadata") or {},
        }
        migrated_chunks: list[dict[str, object]] = []
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            normalized_chunk = dict(chunk)
            embedding = normalized_chunk.get("embedding")
            if isinstance(embedding, list):
                normalized_chunk["embedding"] = _compress_embedding(embedding)
            migrated_chunks.append(
                {
                    **normalized_chunk,
                    "document_id": document_id,
                    "file_hash": document.get("file_hash"),
                    "file_type": document.get("file_type"),
                    "source": normalized_chunk.get("source") or document.get("name"),
                    "loader_metadata": normalized_chunk.get("loader_metadata") or document.get("loader_metadata") or {},
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



def _normalize_chunk_filters(
    chunks: list[dict[str, object]],
    document_ids: list[str] | None = None,
    file_types: list[str] | None = None,
) -> list[dict[str, object]]:
    filtered_chunks = [chunk for chunk in chunks if isinstance(chunk, dict)]

    if document_ids is not None:
        document_ids_set = {str(item) for item in document_ids if item}
        filtered_chunks = [
            chunk
            for chunk in filtered_chunks
            if str(chunk.get("document_id") or chunk.get("file_hash") or "") in document_ids_set
        ]

    if file_types is not None:
        file_types_set = {str(item) for item in file_types if item}
        filtered_chunks = [
            chunk for chunk in filtered_chunks if str(chunk.get("file_type") or "") in file_types_set
        ]

    return filtered_chunks



def _remove_chroma_persist_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)



def sync_chroma_from_rag_index(
    settings: RagSettings,
    rag_index: dict[str, object] | None,
) -> dict[str, object]:
    normalized = _coerce_rag_index(rag_index, settings)
    chunks = [chunk for chunk in normalized.get("chunks", []) if isinstance(chunk, dict)]

    try:
        chroma_store = ChromaVectorStore(settings.chroma_path)
        if chunks:
            chroma_store.rebuild(chunks)
            collection_count = chroma_store.count_entries()
            return {
                "ok": True,
                "backend": "chroma",
                "chunks_in_json": len(chunks),
                "chunks_in_chroma": collection_count,
                "persist_dir_exists": settings.chroma_path.exists(),
                "message": f"Chroma sincronizado com {collection_count} chunk(s).",
            }

        chroma_store.clear(remove_persist_dir=False)
        return {
            "ok": True,
            "backend": "chroma",
            "chunks_in_json": 0,
            "chunks_in_chroma": 0,
            "persist_dir_exists": settings.chroma_path.exists(),
            "message": "Chroma limpo logicamente; o diretório persistido foi mantido para evitar erro de banco readonly durante a mesma sessão.",
        }
    except Exception as error:
        if not chunks:
            return {
                "ok": False,
                "backend": "local_fallback",
                "chunks_in_json": 0,
                "chunks_in_chroma": None,
                "persist_dir_exists": settings.chroma_path.exists(),
                "message": f"Falha ao limpar logicamente o Chroma nesta sessão: {error}",
            }
        print(f"[RAG] Falha ao sincronizar Chroma; mantendo fallback local: {error}")
        return {
            "ok": False,
            "backend": "local_fallback",
            "chunks_in_json": len(chunks),
            "chunks_in_chroma": None,
            "persist_dir_exists": settings.chroma_path.exists(),
            "message": f"Falha ao sincronizar Chroma: {error}",
        }



def clear_persisted_rag_index(settings: RagSettings) -> dict[str, object]:
    try:
        chroma_store = ChromaVectorStore(settings.chroma_path)
        chroma_store.clear(remove_persist_dir=False)
        return {
            "ok": True,
            "backend": "chroma",
            "persist_dir_exists": settings.chroma_path.exists(),
            "message": "Índice lógico do Chroma limpo com sucesso. O diretório persistido foi mantido para evitar o erro de banco readonly na mesma sessão do app.",
        }
    except Exception as error:
        return {
            "ok": False,
            "backend": "local_fallback",
            "persist_dir_exists": settings.chroma_path.exists(),
            "message": (
                "Falha ao limpar logicamente o Chroma nesta sessão. "
                f"Detalhes: {error}"
            ),
        }



def reset_chroma_persist_directory(settings: RagSettings) -> dict[str, object]:
    try:
        chroma_store = ChromaVectorStore(settings.chroma_path)
        chroma_store.clear(remove_persist_dir=True)
        _remove_chroma_persist_dir(settings.chroma_path)
        return {
            "ok": True,
            "backend": "chroma",
            "persist_dir_exists": settings.chroma_path.exists(),
            "message": "Persistência física do Chroma removida. Reinicie o app antes de reindexar para evitar cache/handles antigos do SQLite.",
        }
    except Exception as error:
        _remove_chroma_persist_dir(settings.chroma_path)
        return {
            "ok": not settings.chroma_path.exists(),
            "backend": "local_fallback",
            "persist_dir_exists": settings.chroma_path.exists(),
            "message": (
                "Persistência física do Chroma removida com fallback. Reinicie o app antes de reindexar. "
                f"Detalhes: {error}"
            ),
        }



def inspect_vector_backend_status(
    rag_index: dict[str, object] | None,
    settings: RagSettings,
) -> dict[str, object]:
    normalized = _coerce_rag_index(rag_index, settings)
    json_chunks = [chunk for chunk in normalized.get("chunks", []) if isinstance(chunk, dict)]
    persist_dir_exists = settings.chroma_path.exists()
    status = {
        "json_chunks": len(json_chunks),
        "chroma_chunks": None,
        "backend_ready": False,
        "persist_dir": str(settings.chroma_path),
        "persist_dir_exists": persist_dir_exists,
        "status": "sem_indice" if not json_chunks else "desconhecido",
        "message": "Nenhum índice documental carregado." if not json_chunks else "Status do backend ainda não confirmado.",
    }

    if not json_chunks:
        if persist_dir_exists:
            status["message"] = "Sem índice canônico carregado; persistência local do Chroma ainda existe em disco."
        return status

    try:
        if not persist_dir_exists:
            status["status"] = "fallback_local"
            status["message"] = "Persistência do Chroma ausente; retrieval deve usar fallback local a partir do JSON canônico."
            return status

        chroma_store = ChromaVectorStore(settings.chroma_path)
        chroma_chunks = chroma_store.count_entries()
        status["chroma_chunks"] = chroma_chunks
        status["backend_ready"] = chroma_chunks == len(json_chunks)
        status["status"] = "sincronizado" if chroma_chunks == len(json_chunks) else "dessincronizado"
        status["message"] = (
            "JSON canônico e Chroma persistido estão alinhados."
            if chroma_chunks == len(json_chunks)
            else "JSON canônico e Chroma persistido ainda não estão alinhados."
        )
        return status
    except Exception as error:
        status["status"] = "fallback_local"
        status["message"] = f"Chroma indisponível; retrieval deve usar fallback local. Detalhes: {error}"
        return status



def inspect_embedding_configuration_compatibility(
    rag_index: dict[str, object] | None,
    settings: RagSettings,
) -> dict[str, object]:
    normalized = _coerce_rag_index(rag_index, settings)
    stored_settings = normalized.get("settings", {}) if isinstance(normalized.get("settings"), dict) else {}
    index_embedding_provider = stored_settings.get("embedding_provider")
    index_embedding_model = stored_settings.get("embedding_model")
    index_embedding_context_window = stored_settings.get("embedding_context_window")
    current_embedding_provider = settings.embedding_provider
    current_embedding_model = settings.embedding_model
    current_embedding_context_window = settings.embedding_context_window

    if not normalized.get("chunks"):
        return {
            "compatible": True,
            "status": "sem_indice",
            "message": "Nenhum índice ativo para comparar embedding.",
            "current_embedding_provider": current_embedding_provider,
            "current_embedding_model": current_embedding_model,
            "current_embedding_context_window": current_embedding_context_window,
            "index_embedding_provider": index_embedding_provider,
            "index_embedding_model": index_embedding_model,
            "index_embedding_context_window": index_embedding_context_window,
        }

    compatible = (
        (index_embedding_provider or "ollama") == current_embedding_provider
        and 
        index_embedding_model == current_embedding_model
        and int(index_embedding_context_window or 0) == int(current_embedding_context_window or 0)
    )
    return {
        "compatible": compatible,
        "status": "compativel" if compatible else "incompativel",
        "message": (
            "Embedding atual compatível com o índice carregado."
            if compatible
            else "O índice foi criado com outro provider/modelo de embedding ou outra janela de contexto do embedding. Reindexe antes de usar o RAG."
        ),
        "current_embedding_provider": current_embedding_provider,
        "current_embedding_model": current_embedding_model,
        "current_embedding_context_window": current_embedding_context_window,
        "index_embedding_provider": index_embedding_provider,
        "index_embedding_model": index_embedding_model,
        "index_embedding_context_window": index_embedding_context_window,
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
) -> tuple[dict[str, object], dict[str, object]]:
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
            strategy=settings.chunking_strategy,
        )

        if not chunks:
            raise RuntimeError(f"Não foi possível gerar chunks a partir do documento `{document.name}`.")

        embeddings = embedding_provider.create_embeddings(
            [chunk["text"] for chunk in chunks],
            model=settings.embedding_model,
            context_window=settings.embedding_context_window,
            truncate=settings.embedding_truncate,
        )

        chunking_strategy_used = next(
            (str(chunk.get("chunking_strategy_used") or "") for chunk in chunks if chunk.get("chunking_strategy_used")),
            settings.chunking_strategy,
        )
        chunking_fallback_reason = next(
            (str(chunk.get("chunking_strategy_fallback_reason") or "") for chunk in chunks if chunk.get("chunking_strategy_fallback_reason")),
            "",
        ) or None
        document_metadata = {
            **(document.metadata or {}),
            "chunking_strategy_requested": settings.chunking_strategy,
            "chunking_strategy_used": chunking_strategy_used,
            "chunking_strategy_label": describe_chunking_strategy(chunking_strategy_used),
            **({"chunking_strategy_fallback_reason": chunking_fallback_reason} if chunking_fallback_reason else {}),
        }

        indexed_chunks: list[dict[str, object]] = []
        for chunk, embedding in zip(chunks, embeddings):
            indexed_chunks.append(
                {
                    **chunk,
                    "embedding": _compress_embedding(embedding),
                    "document_id": document_id,
                    "file_hash": document.file_hash,
                    "file_type": document.file_type,
                    "loader_metadata": document_metadata,
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
            "loader_metadata": document_metadata,
        }
        existing_chunks.extend(indexed_chunks)

    updated_index = {
        "documents": list(existing_documents.values()),
        "chunks": existing_chunks,
        "settings": _settings_payload(settings),
        "updated_at": now,
    }
    sync_status = sync_chroma_from_rag_index(settings, updated_index)
    return updated_index, sync_status



def remove_documents_from_rag_index(
    rag_index: dict[str, object] | None,
    settings: RagSettings,
    document_ids: list[str],
) -> tuple[dict[str, object] | None, dict[str, object]]:
    normalized = _coerce_rag_index(rag_index, settings)
    document_ids_set = {str(item) for item in document_ids if item}

    remaining_documents = [
        document
        for document in normalized.get("documents", [])
        if isinstance(document, dict)
        and str(document.get("document_id") or document.get("file_hash") or "") not in document_ids_set
    ]
    remaining_chunks = [
        chunk
        for chunk in normalized.get("chunks", [])
        if isinstance(chunk, dict)
        and str(chunk.get("document_id") or chunk.get("file_hash") or "") not in document_ids_set
    ]

    if not remaining_documents:
        sync_status = sync_chroma_from_rag_index(settings, None)
        return None, sync_status

    updated_index = {
        "documents": remaining_documents,
        "chunks": remaining_chunks,
        "settings": normalized.get("settings", _settings_payload(settings)),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    sync_status = sync_chroma_from_rag_index(settings, updated_index)
    return updated_index, sync_status



def retrieve_relevant_chunks_detailed(
    query: str,
    rag_index: dict[str, object] | None,
    settings: RagSettings,
    embedding_provider,
    document_ids: list[str] | None = None,
    file_types: list[str] | None = None,
) -> dict[str, object]:
    normalized = _coerce_rag_index(rag_index, settings)
    all_chunks = normalized.get("chunks")
    if not isinstance(all_chunks, list) or not all_chunks:
        return {
            "chunks": [],
            "backend_used": "none",
            "backend_message": "Índice documental vazio.",
            "filtered_chunks_available": 0,
            "candidate_pool_size": 0,
            "reranking_applied": False,
            "vector_backend_status": inspect_vector_backend_status(rag_index, settings),
        }

    filtered_chunks = _normalize_chunk_filters(all_chunks, document_ids=document_ids, file_types=file_types)
    if not filtered_chunks:
        return {
            "chunks": [],
            "backend_used": "none",
            "backend_message": "Nenhum chunk disponível após aplicar filtros.",
            "filtered_chunks_available": 0,
            "candidate_pool_size": 0,
            "reranking_applied": False,
            "vector_backend_status": inspect_vector_backend_status(rag_index, settings),
        }

    vector_backend_status = inspect_vector_backend_status(rag_index, settings)
    candidate_pool_size = build_candidate_pool_size(
        top_k=settings.top_k,
        rerank_pool_size=settings.rerank_pool_size,
        filtered_chunks_count=len(filtered_chunks),
    )
    vector_candidates: list[dict[str, object]] = []
    backend_used = "local_fallback"
    backend_message = "Retrieval servido por fallback local a partir do JSON canônico."
    requested_retrieval_strategy, effective_retrieval_strategy, retrieval_strategy_fallback_reason = resolve_retrieval_strategy(settings.retrieval_strategy)

    if effective_retrieval_strategy == "langchain_chroma":
        langchain_results, langchain_error = similarity_search_with_langchain_chroma(
            query=query,
            settings=settings,
            embedding_provider=embedding_provider,
            top_k=candidate_pool_size,
            document_ids=document_ids,
            file_types=file_types,
        )
        if langchain_results:
            backend_used = "langchain_chroma"
            backend_message = "Retrieval servido pelo adaptador experimental LangChain + Chroma."
            vector_candidates = [{**chunk, "vector_score": chunk.get("score", 0.0)} for chunk in langchain_results]
        else:
            retrieval_strategy_fallback_reason = langchain_error or "langchain_returned_no_results"

    query_embedding = None
    if not vector_candidates:
        query_embedding = embedding_provider.create_embeddings(
            [query],
            model=settings.embedding_model,
            context_window=settings.embedding_context_window,
            truncate=settings.embedding_truncate,
        )[0]

        try:
            chroma_store = ChromaVectorStore(settings.chroma_path)
            chroma_results = chroma_store.similarity_search(
                query_embedding,
                candidate_pool_size,
                document_ids=document_ids,
                file_types=file_types,
            )
            if chroma_results:
                backend_used = "chroma"
                backend_message = "Retrieval servido pelo Chroma persistido sincronizado."
                vector_candidates = [{**chunk, "vector_score": chunk.get("score", 0.0)} for chunk in chroma_results]
                effective_retrieval_strategy = "manual_hybrid"
            else:
                print("[RAG] Chroma não retornou resultados; usando fallback local.")
        except Exception as error:
            print(f"[RAG] Chroma falhou na busca; usando fallback local: {error}")
            vector_backend_status = {
                **vector_backend_status,
                "status": "fallback_local",
                "backend_ready": False,
                "message": f"Falha de retrieval no Chroma: {error}",
            }

    if not vector_candidates:
        store = LocalVectorStore(filtered_chunks)
        local_results = store.similarity_search(query_embedding, candidate_pool_size)
        vector_candidates = [{**chunk, "vector_score": chunk.get("score", 0.0)} for chunk in local_results]
        backend_used = "local_fallback"
        backend_message = "Retrieval servido por fallback local a partir do JSON canônico."
        effective_retrieval_strategy = "manual_hybrid"

    lexical_candidates = rank_chunks_lexically(query, filtered_chunks, candidate_pool_size)
    reranked_chunks = hybrid_rerank_chunks(
        query,
        vector_candidates,
        lexical_candidates,
        top_k=settings.top_k,
        lexical_weight=settings.rerank_lexical_weight,
    )

    return {
        "chunks": reranked_chunks,
        "backend_used": backend_used,
        "backend_message": backend_message,
        "filtered_chunks_available": len(filtered_chunks),
        "candidate_pool_size": candidate_pool_size,
        "reranking_applied": True,
        "vector_backend_status": vector_backend_status,
        "retrieval_strategy_requested": requested_retrieval_strategy,
        "retrieval_strategy_used": effective_retrieval_strategy,
        "retrieval_strategy_label": describe_retrieval_strategy(effective_retrieval_strategy),
        "retrieval_strategy_fallback_reason": retrieval_strategy_fallback_reason,
        "rerank_strategy": {
            "type": "hybrid_vector_lexical",
            "lexical_weight": settings.rerank_lexical_weight,
            "candidate_pool_size": candidate_pool_size,
        },
    }



def retrieve_relevant_chunks(
    query: str,
    rag_index: dict[str, object] | None,
    settings: RagSettings,
    embedding_provider,
    document_ids: list[str] | None = None,
    file_types: list[str] | None = None,
) -> list[dict[str, object]]:
    return retrieve_relevant_chunks_detailed(
        query=query,
        rag_index=rag_index,
        settings=settings,
        embedding_provider=embedding_provider,
        document_ids=document_ids,
        file_types=file_types,
    )["chunks"]



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
                "vector_score": chunk.get("vector_score"),
                "lexical_score": chunk.get("lexical_score"),
                "snippet": chunk.get("snippet") or str(chunk.get("text", ""))[:400],
            }
        )
    return sources
