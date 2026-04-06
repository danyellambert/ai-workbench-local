from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_rag_settings  # noqa: E402
from src.providers.ollama_provider import OllamaProvider  # noqa: E402
from src.providers.registry import build_provider_registry  # noqa: E402
from src.rag.loaders import load_document  # noqa: E402
from src.rag.service import get_indexed_documents, retrieve_relevant_chunks_detailed, upsert_documents_in_rag_index  # noqa: E402


@dataclass
class BenchmarkRunConfig:
    label: str
    embedding_model: str
    embedding_context_window: int
    chunk_size: int
    chunk_overlap: int
    top_k: int
    rerank_pool_size: int
    rerank_lexical_weight: float
    embedding_truncate: bool


class LocalUploadedFile:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an automated embedding benchmark for Phase 4.5 using the local RAG pipeline."
    )
    parser.add_argument("--pdfs", nargs="+", required=True, help="PDF files to index and benchmark.")
    parser.add_argument(
        "--questions",
        default="docs/embedding_benchmark_questions.example.json",
        help="JSON file containing benchmark questions and expected target documents.",
    )
    parser.add_argument(
        "--embedding-models",
        nargs="+",
        default=None,
        help="Embedding models to compare. If omitted, models are taken from the questions file or Ollama discovery.",
    )
    parser.add_argument("--embedding-context-window", type=int, default=8192)
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--rerank-pool-size", type=int, default=8)
    parser.add_argument("--rerank-lexical-weight", type=float, default=0.35)
    parser.add_argument("--embedding-truncate", action="store_true", default=True)
    parser.add_argument("--no-embedding-truncate", dest="embedding_truncate", action="store_false")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory where benchmark outputs will be written. Defaults to benchmark_runs/<timestamp>_embedding_benchmark.",
    )
    parser.add_argument(
        "--keep-run-indexes",
        action="store_true",
        help="Keep per-run temporary JSON/Chroma stores instead of deleting them after execution.",
    )
    return parser.parse_args()


def load_question_set(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Question file must contain a JSON object.")
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise RuntimeError("Question file must contain a non-empty 'questions' list.")
    return payload



def resolve_pdf_paths(raw_paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"PDF not found: {raw_path}")
        resolved.append(candidate)
    return resolved



def build_run_output_dir(base_output_dir: str | None) -> Path:
    if base_output_dir:
        output_dir = Path(base_output_dir)
        if not output_dir.is_absolute():
            output_dir = (PROJECT_ROOT / output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / "benchmark_runs" / f"{timestamp}_embedding_benchmark"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir



def build_provider() -> OllamaProvider:
    registry = build_provider_registry()
    provider = registry["ollama"]["instance"]
    if not isinstance(provider, OllamaProvider):
        raise RuntimeError("Ollama provider is not available.")
    return provider



def choose_embedding_models(args: argparse.Namespace, question_payload: dict[str, Any], provider: OllamaProvider) -> list[str]:
    if args.embedding_models:
        return list(dict.fromkeys(args.embedding_models))

    models_from_file = question_payload.get("embedding_models")
    if isinstance(models_from_file, list) and models_from_file:
        return [str(item) for item in dict.fromkeys(models_from_file)]

    discovered = provider.list_available_embedding_models()
    if not discovered:
        raise RuntimeError("No embedding models were discovered in Ollama.")
    return discovered



def materialize_run_settings(
    config: BenchmarkRunConfig,
    run_dir: Path,
):
    os.environ["OLLAMA_EMBEDDING_MODEL"] = config.embedding_model
    os.environ["OLLAMA_EMBEDDING_CONTEXT_WINDOW"] = str(config.embedding_context_window)
    os.environ["OLLAMA_EMBEDDING_TRUNCATE"] = "true" if config.embedding_truncate else "false"
    os.environ["RAG_CHUNK_SIZE"] = str(config.chunk_size)
    os.environ["RAG_CHUNK_OVERLAP"] = str(config.chunk_overlap)
    os.environ["RAG_TOP_K"] = str(config.top_k)
    os.environ["RAG_RERANK_POOL_SIZE"] = str(config.rerank_pool_size)
    os.environ["RAG_RERANK_LEXICAL_WEIGHT"] = str(config.rerank_lexical_weight)
    os.environ["RAG_STORE_PATH"] = str(run_dir / ".rag_store.json")
    os.environ["RAG_CHROMA_PATH"] = str(run_dir / ".chroma_rag")

    settings = get_rag_settings()
    # The project config currently ignores env overrides for store/chroma paths.
    # We patch the dataclass instance here to guarantee isolated benchmark runs.
    settings = type(settings)(
        **{
            **asdict(settings),
            "store_path": run_dir / ".rag_store.json",
            "chroma_path": run_dir / ".chroma_rag",
        }
    )
    return settings



def index_documents(provider: OllamaProvider, settings, pdf_paths: list[Path]) -> tuple[dict[str, Any], list[dict[str, Any]], float]:
    loaded_documents = [load_document(LocalUploadedFile(path), settings) for path in pdf_paths]
    started_at = time.perf_counter()
    rag_index, sync_status = upsert_documents_in_rag_index(
        documents=loaded_documents,
        settings=settings,
        embedding_provider=provider,
        rag_index=None,
    )
    indexing_seconds = time.perf_counter() - started_at
    indexed_documents = get_indexed_documents(rag_index, settings)
    return rag_index, indexed_documents, indexing_seconds



def score_question(result_chunks: list[dict[str, Any]], expected_document_names: set[str], top_k: int) -> dict[str, Any]:
    retrieved_names = [str(chunk.get("source") or "") for chunk in result_chunks]
    hit_at_1 = bool(retrieved_names[:1] and retrieved_names[0] in expected_document_names)
    hit_at_k = any(name in expected_document_names for name in retrieved_names[:top_k])

    reciprocal_rank = 0.0
    first_relevant_rank = None
    for rank, name in enumerate(retrieved_names, start=1):
        if name in expected_document_names:
            reciprocal_rank = 1.0 / rank
            first_relevant_rank = rank
            break

    return {
        "retrieved_names": retrieved_names,
        "hit_at_1": hit_at_1,
        "hit_at_k": hit_at_k,
        "reciprocal_rank": reciprocal_rank,
        "first_relevant_rank": first_relevant_rank,
    }



def run_question_benchmark(
    provider: OllamaProvider,
    settings,
    rag_index: dict[str, Any],
    questions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    per_question_results: list[dict[str, Any]] = []
    retrieval_latencies: list[float] = []
    hit_at_1_values: list[int] = []
    hit_at_k_values: list[int] = []
    reciprocal_ranks: list[float] = []

    for item in questions:
        question = str(item["question"])
        expected_document_names = {str(name) for name in item.get("expected_document_names", [])}
        started_at = time.perf_counter()
        retrieval_details = retrieve_relevant_chunks_detailed(
            query=question,
            rag_index=rag_index,
            settings=settings,
            embedding_provider=provider,
        )
        retrieval_seconds = time.perf_counter() - started_at
        retrieval_latencies.append(retrieval_seconds)

        chunks = retrieval_details.get("chunks", [])
        question_metrics = score_question(chunks, expected_document_names, settings.top_k)
        hit_at_1_values.append(1 if question_metrics["hit_at_1"] else 0)
        hit_at_k_values.append(1 if question_metrics["hit_at_k"] else 0)
        reciprocal_ranks.append(float(question_metrics["reciprocal_rank"]))

        top_sources = []
        for chunk in chunks:
            top_sources.append(
                {
                    "source": chunk.get("source"),
                    "document_id": chunk.get("document_id"),
                    "chunk_id": chunk.get("chunk_id"),
                    "score": chunk.get("score"),
                    "vector_score": chunk.get("vector_score"),
                    "lexical_score": chunk.get("lexical_score"),
                    "snippet": (chunk.get("snippet") or chunk.get("text") or "")[:280],
                }
            )

        per_question_results.append(
            {
                "question": question,
                "expected_document_names": sorted(expected_document_names),
                "retrieval_seconds": round(retrieval_seconds, 4),
                "backend_used": retrieval_details.get("backend_used"),
                "candidate_pool_size": retrieval_details.get("candidate_pool_size"),
                "reranking_applied": retrieval_details.get("reranking_applied"),
                **question_metrics,
                "top_sources": top_sources,
            }
        )

    aggregate = {
        "question_count": len(questions),
        "hit_at_1": round(sum(hit_at_1_values) / len(hit_at_1_values), 4),
        "hit_at_k": round(sum(hit_at_k_values) / len(hit_at_k_values), 4),
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
        "average_retrieval_seconds": round(statistics.mean(retrieval_latencies), 4),
        "median_retrieval_seconds": round(statistics.median(retrieval_latencies), 4),
        "max_retrieval_seconds": round(max(retrieval_latencies), 4),
    }
    return per_question_results, aggregate



def write_run_result(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "result.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")



def write_summary(output_dir: Path, summary_payload: dict[str, Any]) -> None:
    (output_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Embedding Benchmark Summary")
    lines.append("")
    lines.append(f"Generated at: `{summary_payload['generated_at']}`")
    lines.append("")
    lines.append("## Ranked results")
    lines.append("")
    lines.append("| Rank | Model | Hit@1 | Hit@K | MRR | Avg retrieval (s) | Indexing (s) |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for rank, item in enumerate(summary_payload["ranking"], start=1):
        metrics = item["aggregate_metrics"]
        lines.append(
            f"| {rank} | `{item['embedding_model']}` | {metrics['hit_at_1']:.4f} | {metrics['hit_at_k']:.4f} | {metrics['mrr']:.4f} | {metrics['average_retrieval_seconds']:.4f} | {item['indexing_seconds']:.4f} |"
        )

    lines.append("")
    lines.append("## Run directories")
    lines.append("")
    for item in summary_payload["ranking"]:
        lines.append(f"- `{item['embedding_model']}` → `{item['run_dir']}`")

    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")



def main() -> None:
    args = parse_args()
    output_dir = build_run_output_dir(args.output_dir)
    provider = build_provider()
    question_file = Path(args.questions)
    if not question_file.is_absolute():
        question_file = (PROJECT_ROOT / question_file).resolve()
    question_payload = load_question_set(question_file)
    pdf_paths = resolve_pdf_paths(args.pdfs)
    questions = question_payload["questions"]
    embedding_models = choose_embedding_models(args, question_payload, provider)

    summary_runs: list[dict[str, Any]] = []

    for model_name in embedding_models:
        safe_label = model_name.replace(":", "_").replace("/", "_")
        run_dir = output_dir / safe_label
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        config = BenchmarkRunConfig(
            label=safe_label,
            embedding_model=model_name,
            embedding_context_window=args.embedding_context_window,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            top_k=args.top_k,
            rerank_pool_size=args.rerank_pool_size,
            rerank_lexical_weight=args.rerank_lexical_weight,
            embedding_truncate=args.embedding_truncate,
        )
        settings = materialize_run_settings(config, run_dir)

        print(f"\n=== Running benchmark for embedding model: {model_name} ===")
        rag_index, indexed_documents, indexing_seconds = index_documents(provider, settings, pdf_paths)
        per_question_results, aggregate_metrics = run_question_benchmark(provider, settings, rag_index, questions)

        run_payload = {
            "generated_at": datetime.now().isoformat(),
            "config": asdict(config),
            "indexed_documents": indexed_documents,
            "indexing_seconds": round(indexing_seconds, 4),
            "aggregate_metrics": aggregate_metrics,
            "questions": per_question_results,
        }
        write_run_result(run_dir, run_payload)

        print(
            f"[done] {model_name} | Hit@1={aggregate_metrics['hit_at_1']:.4f} "
            f"Hit@K={aggregate_metrics['hit_at_k']:.4f} MRR={aggregate_metrics['mrr']:.4f} "
            f"Avg retrieval={aggregate_metrics['average_retrieval_seconds']:.4f}s Indexing={indexing_seconds:.4f}s"
        )

        summary_runs.append(
            {
                "embedding_model": model_name,
                "run_dir": str(run_dir.relative_to(PROJECT_ROOT)),
                "indexing_seconds": round(indexing_seconds, 4),
                "aggregate_metrics": aggregate_metrics,
            }
        )

        if not args.keep_run_indexes:
            shutil.rmtree(run_dir / ".chroma_rag", ignore_errors=True)
            try:
                (run_dir / ".rag_store.json").unlink()
            except FileNotFoundError:
                pass

    ranking = sorted(
        summary_runs,
        key=lambda item: (
            item["aggregate_metrics"]["hit_at_1"],
            item["aggregate_metrics"]["hit_at_k"],
            item["aggregate_metrics"]["mrr"],
            -item["aggregate_metrics"]["average_retrieval_seconds"],
        ),
        reverse=True,
    )

    summary_payload = {
        "generated_at": datetime.now().isoformat(),
        "question_file": str(question_file.relative_to(PROJECT_ROOT)),
        "pdfs": [str(path.relative_to(PROJECT_ROOT)) if path.is_relative_to(PROJECT_ROOT) else str(path) for path in pdf_paths],
        "ranking": ranking,
    }
    write_summary(output_dir, summary_payload)

    print(f"\nSummary written to: {output_dir / 'summary.json'}")
    print(f"Human-readable report: {output_dir / 'README.md'}")


if __name__ == "__main__":
    main()
