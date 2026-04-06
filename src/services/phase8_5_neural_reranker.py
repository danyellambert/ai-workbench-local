from __future__ import annotations

from functools import lru_cache


def supports_local_neural_reranker_runtime() -> bool:
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
    except Exception:
        return False
    return True


@lru_cache(maxsize=8)
def _load_local_cross_encoder(model_name: str):
    if not supports_local_neural_reranker_runtime():
        raise RuntimeError("sentence-transformers CrossEncoder runtime is not available in this environment.")

    from sentence_transformers import CrossEncoder

    try:
        return CrossEncoder(model_name, local_files_only=True)
    except TypeError:
        return CrossEncoder(model_name)


def score_query_document_pairs(
    *,
    model_name: str,
    pairs: list[tuple[str, str]],
) -> list[float]:
    if not pairs:
        return []
    encoder = _load_local_cross_encoder(str(model_name or "").strip())
    try:
        scores = encoder.predict(pairs, show_progress_bar=False)
    except TypeError:
        scores = encoder.predict(pairs)
    return [float(score) for score in list(scores)]