from __future__ import annotations

import argparse
import json
from pathlib import Path


TEMPLATE = {
    "questions": [
        {
            "question": "What are the central points of document X?",
            "expected_document_ids": ["replace-with-hash-or-id"],
            "notes": "Use questions that only one document can answer.",
        }
    ],
    "runs": [
        {
            "label": "baseline-bge-m3",
            "embedding_model": "bge-m3",
            "chunk_size": 1200,
            "chunk_overlap": 200,
            "top_k": 4,
            "rerank_pool_size": 8,
        },
        {
            "label": "alt-nomic",
            "embedding_model": "nomic-embed-text",
            "chunk_size": 1200,
            "chunk_overlap": 200,
            "top_k": 4,
            "rerank_pool_size": 8,
        },
    ],
    "evidence_to_collect": [
        "app screenshots with the same questions",
        "retrieval latency",
        "returned sources",
        "perceived response quality",
    ],
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a local template for practical Phase 4.5 comparison.")
    parser.add_argument("--output", default="docs/phase_4_5_eval_template.json", help="Path to the JSON template.")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(TEMPLATE, indent=2, ensure_ascii=False))
    print(f"[ok] Comparison template saved to {output_path}")
    print("Use this file to run the local comparison round between embeddings and fine-tuning.")
