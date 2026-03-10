from math import sqrt


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