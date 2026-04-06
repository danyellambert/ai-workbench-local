import unittest

from src.rag.reranking import build_candidate_pool_size, hybrid_rerank_chunks, lexical_score, rank_chunks_lexically


class RerankingTests(unittest.TestCase):
    def test_candidate_pool_size_respects_filtered_count(self) -> None:
        self.assertEqual(
            build_candidate_pool_size(top_k=4, rerank_pool_size=8, filtered_chunks_count=5),
            5,
        )

    def test_lexical_score_rewards_exact_phrase(self) -> None:
        exact = lexical_score("alpha beta", "alpha beta appears together in the chunk")
        partial = lexical_score("alpha beta", "alpha appears here but the other keyword is missing")
        self.assertGreater(exact, partial)

    def test_hybrid_rerank_prioritizes_combined_signal(self) -> None:
        chunks = [
            {
                "document_id": "doc-1",
                "chunk_id": 1,
                "start_char": 0,
                "end_char": 20,
                "text": "alpha beta release notes",
                "vector_score": 0.82,
                "score": 0.82,
            },
            {
                "document_id": "doc-2",
                "chunk_id": 1,
                "start_char": 0,
                "end_char": 20,
                "text": "generic document without the query",
                "vector_score": 0.9,
                "score": 0.9,
            },
        ]
        lexical_candidates = rank_chunks_lexically("alpha beta", chunks, limit=2)
        reranked = hybrid_rerank_chunks(
            "alpha beta",
            chunks,
            lexical_candidates,
            top_k=2,
            lexical_weight=0.35,
        )
        self.assertEqual(reranked[0]["document_id"], "doc-1")


if __name__ == "__main__":
    unittest.main()