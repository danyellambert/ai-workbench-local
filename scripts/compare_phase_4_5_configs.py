from __future__ import annotations

import argparse
import json
from pathlib import Path


TEMPLATE = {
    "questions": [
        {
            "question": "Quais são os pontos centrais do documento X?",
            "expected_document_ids": ["substitua-pelo-hash-ou-id"],
            "notes": "Use perguntas que só um documento consiga responder.",
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
        "screenshots do app com as mesmas perguntas",
        "latência de retrieval",
        "fontes retornadas",
        "qualidade percebida da resposta",
    ],
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera um template local para comparação prática da Fase 4.5.")
    parser.add_argument("--output", default="docs/phase_4_5_eval_template.json", help="Caminho do template JSON.")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(TEMPLATE, indent=2, ensure_ascii=False))
    print(f"[ok] Template de comparação salvo em {output_path}")
    print("Use esse arquivo para conduzir a rodada local de comparação entre embeddings e tuning fino.")
