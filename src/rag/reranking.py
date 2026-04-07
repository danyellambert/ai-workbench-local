from __future__ import annotations

import re


TOKEN_PATTERN = re.compile(r"[\w\-]{3,}", re.UNICODE)


def chunk_key(chunk: dict[str, object]) -> str:
    return "::".join(
        [
            str(chunk.get("document_id") or chunk.get("file_hash") or "document"),
            str(chunk.get("chunk_id") or 0),
            str(chunk.get("start_char") or 0),
            str(chunk.get("end_char") or 0),
        ]
    )


def tokenize(text: str) -> set[str]:
    normalized = (text or "").replace("’", "'").replace("`", "'")
    return {match.group(0).lower() for match in TOKEN_PATTERN.finditer(normalized)}


def lexical_score(query: str, chunk_text: str) -> float:
    normalized_query = (query or "").strip().replace("’", "'").replace("`", "'")
    normalized_chunk = (chunk_text or "").replace("’", "'").replace("`", "'")
    query_terms = tokenize(normalized_query)
    if not query_terms:
        return 0.0

    chunk_terms = tokenize(normalized_chunk)
    if not chunk_terms:
        return 0.0

    overlap_ratio = len(query_terms & chunk_terms) / max(len(query_terms), 1)
    exact_phrase_bonus = 0.45 if normalized_query and normalized_query.lower() in normalized_chunk.lower() else 0.0
    partial_phrase_bonus = 0.2 if len(normalized_query.split()) >= 4 and any(
        fragment in normalized_chunk.lower()
        for fragment in [normalized_query.lower()[: max(len(normalized_query) // 2, 12)]]
    ) else 0.0
    return round(min(overlap_ratio + exact_phrase_bonus + partial_phrase_bonus, 1.0), 4)


def rank_chunks_lexically(query: str, chunks: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    for chunk in chunks:
        lexical = lexical_score(query, str(chunk.get("text", "")))
        if lexical <= 0:
            continue
        ranked.append({**chunk, "lexical_score": lexical})

    ranked.sort(key=lambda item: item.get("lexical_score", 0.0), reverse=True)
    return ranked[:limit]


def build_candidate_pool_size(*, top_k: int, rerank_pool_size: int, filtered_chunks_count: int) -> int:
    pool = max(top_k, rerank_pool_size)
    return min(max(pool, top_k), max(filtered_chunks_count, top_k))


def hybrid_rerank_chunks(
    query: str,
    vector_candidates: list[dict[str, object]],
    lexical_candidates: list[dict[str, object]],
    *,
    top_k: int,
    lexical_weight: float,
) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}

    for candidate in [*vector_candidates, *lexical_candidates]:
        key = chunk_key(candidate)
        existing = merged.get(key, {})
        vector_score = float(candidate.get("vector_score") or candidate.get("score") or existing.get("vector_score") or 0.0)
        current_text = str(candidate.get("text", ""))
        lexical = float(candidate.get("lexical_score") or existing.get("lexical_score") or lexical_score(query, current_text))
        merged[key] = {
            **existing,
            **candidate,
            "vector_score": round(vector_score, 4),
            "lexical_score": round(lexical, 4),
        }

    reranked: list[dict[str, object]] = []
    bounded_lexical_weight = min(max(float(lexical_weight), 0.0), 0.9)
    vector_weight = 1.0 - bounded_lexical_weight
    for candidate in merged.values():
        vector_score = float(candidate.get("vector_score") or 0.0)
        lexical = float(candidate.get("lexical_score") or 0.0)
        rerank_score = round(vector_score * vector_weight + lexical * bounded_lexical_weight, 4)
        reranked.append({**candidate, "score": rerank_score, "rerank_score": rerank_score})

    reranked.sort(
        key=lambda item: (
            item.get("rerank_score", 0.0),
            item.get("lexical_score", 0.0),
            item.get("vector_score", 0.0),
        ),
        reverse=True,
    )
    return reranked[:top_k]