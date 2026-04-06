from __future__ import annotations

import argparse
import json
import re
import sys
import time
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from statistics import mean
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import BASE_DIR, get_rag_settings
from src.providers.registry import build_provider_registry
from src.rag.loaders import load_document
from src.rag.service import retrieve_relevant_chunks_detailed, upsert_documents_in_rag_index

DEFAULT_PDFS = [
    "2025-HB-44-20250106-Final-508.pdf",
    "kaur-2016-ijca-911367.pdf",
    "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf",
    "c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf",
]

DEFAULT_SUITE = {
    "questions": [
        {
            "id": "kaur_best_model",
            "question": "Which method combination achieved the best performance according to the Kaur paper?",
            "expected_sources": ["kaur-2016-ijca-911367.pdf"],
        },
        {
            "id": "kaur_metric",
            "question": "Which evaluation metric was used in the Kaur paper?",
            "expected_sources": ["kaur-2016-ijca-911367.pdf"],
        },
        {
            "id": "meng_optimization",
            "question": "Which algorithm is used to solve the optimization problem in the Meng paper?",
            "expected_sources": ["Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf"],
        },
        {
            "id": "meng_robustness",
            "question": "What kinds of robustness does the Meng paper claim for the proposed method?",
            "expected_sources": ["Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf"],
        },
        {
            "id": "hb44_intro",
            "question": "What is the purpose of Handbook 44 according to its introduction?",
            "expected_sources": ["2025-HB-44-20250106-Final-508.pdf"],
        },
        {
            "id": "hb44_retroactive",
            "question": "What does Handbook 44 say about retroactive and nonretroactive requirements?",
            "expected_sources": ["2025-HB-44-20250106-Final-508.pdf"],
        },
        {
            "id": "scanner_usb",
            "question": "How does the scanner manual describe connecting the cradle with USB?",
            "expected_sources": ["c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf"],
        },
        {
            "id": "scanner_battery",
            "question": "Which battery or safety warnings are mentioned in the scanner manual?",
            "expected_sources": ["c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf"],
        },
    ],
    "benchmarks": {
        "embedding_models": {
            "enabled": True,
            "runs": [
                {"label": "bge_m3", "embedding_model": "bge-m3:latest"},
                {"label": "embeddinggemma_300m", "embedding_model": "embeddinggemma:300m"},
                {"label": "qwen3_embedding_0_6b", "embedding_model": "qwen3-embedding:0.6b"},
            ],
        },
        "embedding_context_window": {
            "enabled": True,
            "base": {
                "embedding_model": "bge-m3:latest",
            },
            "runs": [
                {"label": "ctx_512", "embedding_context_window": 512},
                {"label": "ctx_1024", "embedding_context_window": 1024},
                {"label": "ctx_2048", "embedding_context_window": 2048},
                {"label": "ctx_4096", "embedding_context_window": 4096},
            ],
        },
        "retrieval_tuning": {
            "enabled": True,
            "base": {
                "embedding_model": "bge-m3:latest",
                "embedding_context_window": 2048,
            },
            "runs": [
                {
                    "label": "baseline",
                    "chunk_size": 1200,
                    "chunk_overlap": 200,
                    "top_k": 4,
                    "rerank_pool_size": 8,
                },
                {
                    "label": "smaller_chunks",
                    "chunk_size": 800,
                    "chunk_overlap": 120,
                    "top_k": 4,
                    "rerank_pool_size": 8,
                },
                {
                    "label": "larger_chunks",
                    "chunk_size": 1600,
                    "chunk_overlap": 240,
                    "top_k": 4,
                    "rerank_pool_size": 8,
                },
                {
                    "label": "higher_top_k",
                    "chunk_size": 1200,
                    "chunk_overlap": 200,
                    "top_k": 6,
                    "rerank_pool_size": 12,
                },
                {
                    "label": "lighter_rerank_pool",
                    "chunk_size": 1200,
                    "chunk_overlap": 200,
                    "top_k": 4,
                    "rerank_pool_size": 4,
                },
            ],
        },
    },
}


class UploadedPath:
    def __init__(self, path: Path):
        self._path = path
        self.name = path.name
        self.size = path.stat().st_size
        self.type = "application/pdf"

    def getvalue(self) -> bytes:
        return self._path.read_bytes()


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "run"


def resolve_pdf_paths(paths: list[str] | None) -> list[Path]:
    raw_paths = [Path(item) for item in paths] if paths else []
    if not raw_paths:
        raw_paths = [BASE_DIR / name for name in DEFAULT_PDFS]

    resolved: list[Path] = []
    for path in raw_paths:
        if path.exists():
            resolved.append(path.resolve())
            continue
        fallback = BASE_DIR / path.name
        if fallback.exists():
            resolved.append(fallback.resolve())
            continue
        data_fallback = Path("/mnt/data") / path.name
        if data_fallback.exists():
            resolved.append(data_fallback.resolve())
            continue
        raise FileNotFoundError(f"PDF not found: {path}")
    return resolved


def load_suite(path: Path | None) -> dict[str, Any]:
    if path is None:
        return deepcopy(DEFAULT_SUITE)
    return json.loads(path.read_text(encoding="utf-8"))


def isolate_settings(base_settings, run_dir: Path, **overrides):
    return replace(
        base_settings,
        store_path=run_dir / ".rag_store.json",
        chroma_path=run_dir / ".chroma_rag",
        **overrides,
    )


def index_documents(pdf_paths: list[Path], settings, embedding_provider) -> tuple[dict[str, Any], float, dict[str, Any]]:
    loaded_documents = []
    load_stats: list[dict[str, Any]] = []
    for pdf_path in pdf_paths:
        uploaded = UploadedPath(pdf_path)
        started = time.perf_counter()
        loaded = load_document(uploaded, settings)
        load_stats.append(
            {
                "pdf_name": pdf_path.name,
                "chars": len(loaded.text),
                "load_seconds": round(time.perf_counter() - started, 4),
                "metadata": loaded.metadata,
            }
        )
        loaded_documents.append(loaded)

    started = time.perf_counter()
    rag_index, sync_status = upsert_documents_in_rag_index(
        documents=loaded_documents,
        settings=settings,
        embedding_provider=embedding_provider,
        rag_index=None,
    )
    indexing_seconds = time.perf_counter() - started
    return rag_index, indexing_seconds, {"documents": load_stats, "sync_status": sync_status}


def evaluate_questions(questions: list[dict[str, Any]], rag_index, settings, embedding_provider) -> dict[str, Any]:
    per_question: list[dict[str, Any]] = []
    hit_at_1_values: list[float] = []
    hit_at_k_values: list[float] = []
    reciprocal_ranks: list[float] = []
    retrieval_latencies: list[float] = []

    for item in questions:
        question = str(item["question"])
        expected_sources = [str(source) for source in item.get("expected_sources", [])]

        started = time.perf_counter()
        retrieval = retrieve_relevant_chunks_detailed(
            query=question,
            rag_index=rag_index,
            settings=settings,
            embedding_provider=embedding_provider,
        )
        retrieval_seconds = time.perf_counter() - started
        retrieval_latencies.append(retrieval_seconds)

        chunks = retrieval.get("chunks") or []
        returned_sources = [str(chunk.get("source") or "") for chunk in chunks]
        returned_unique_sources = []
        seen = set()
        for source in returned_sources:
            if source not in seen:
                returned_unique_sources.append(source)
                seen.add(source)

        top_1_source = returned_sources[0] if returned_sources else None
        hit_at_1 = 1.0 if top_1_source in expected_sources else 0.0
        hit_at_k = 1.0 if any(source in expected_sources for source in returned_sources) else 0.0

        reciprocal_rank = 0.0
        for rank, source in enumerate(returned_sources, start=1):
            if source in expected_sources:
                reciprocal_rank = 1.0 / rank
                break

        hit_at_1_values.append(hit_at_1)
        hit_at_k_values.append(hit_at_k)
        reciprocal_ranks.append(reciprocal_rank)

        per_question.append(
            {
                "id": item.get("id"),
                "question": question,
                "expected_sources": expected_sources,
                "returned_sources": returned_sources,
                "returned_unique_sources": returned_unique_sources,
                "top_1_source": top_1_source,
                "hit_at_1": hit_at_1,
                "hit_at_k": hit_at_k,
                "reciprocal_rank": round(reciprocal_rank, 4),
                "retrieval_seconds": round(retrieval_seconds, 4),
                "backend_used": retrieval.get("backend_used"),
                "candidate_pool_size": retrieval.get("candidate_pool_size"),
                "chunks": [
                    {
                        "source": chunk.get("source"),
                        "chunk_id": chunk.get("chunk_id"),
                        "score": chunk.get("score"),
                        "vector_score": chunk.get("vector_score"),
                        "lexical_score": chunk.get("lexical_score"),
                        "snippet": str(chunk.get("snippet") or chunk.get("text") or "")[:300],
                    }
                    for chunk in chunks
                ],
            }
        )

    return {
        "per_question": per_question,
        "metrics": {
            "question_count": len(questions),
            "hit_at_1": round(sum(hit_at_1_values) / max(len(hit_at_1_values), 1), 4),
            "hit_at_k": round(sum(hit_at_k_values) / max(len(hit_at_k_values), 1), 4),
            "mrr": round(sum(reciprocal_ranks) / max(len(reciprocal_ranks), 1), 4),
            "avg_retrieval_seconds": round(sum(retrieval_latencies) / max(len(retrieval_latencies), 1), 4),
            "p95_retrieval_seconds": round(sorted(retrieval_latencies)[max(0, int(len(retrieval_latencies) * 0.95) - 1)], 4)
            if retrieval_latencies
            else 0.0,
        },
    }


def summarise_group(group_name: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    ranking = sorted(
        results,
        key=lambda item: (
            item["metrics"]["hit_at_1"],
            item["metrics"]["hit_at_k"],
            item["metrics"]["mrr"],
            -item["metrics"]["avg_retrieval_seconds"],
            -item["indexing_seconds"],
        ),
        reverse=True,
    )
    return {
        "benchmark": group_name,
        "best_label": ranking[0]["label"] if ranking else None,
        "ranking": [
            {
                "label": item["label"],
                "metrics": item["metrics"],
                "indexing_seconds": item["indexing_seconds"],
                "settings": item["settings"],
            }
            for item in ranking
        ],
        "avg_hit_at_1": round(mean(item["metrics"]["hit_at_1"] for item in results), 4) if results else 0.0,
        "avg_mrr": round(mean(item["metrics"]["mrr"] for item in results), 4) if results else 0.0,
    }


def run_group(
    group_name: str,
    group_config: dict[str, Any],
    questions: list[dict[str, Any]],
    pdf_paths: list[Path],
    embedding_provider,
    root_output_dir: Path,
) -> dict[str, Any]:
    base_settings = get_rag_settings()
    group_output_dir = root_output_dir / slugify(group_name)
    group_output_dir.mkdir(parents=True, exist_ok=True)

    base_overrides = group_config.get("base", {})
    results: list[dict[str, Any]] = []

    for run_index, run in enumerate(group_config.get("runs", []), start=1):
        label = str(run.get("label") or f"run_{run_index}")
        run_overrides = {**base_overrides, **{k: v for k, v in run.items() if k != "label"}}
        run_output_dir = group_output_dir / f"{run_index:02d}_{slugify(label)}"
        run_output_dir.mkdir(parents=True, exist_ok=True)

        settings = isolate_settings(base_settings, run_output_dir, **run_overrides)
        print(f"\n=== [{group_name}] {label} ===")
        print(f"settings: embedding={settings.embedding_model} embed_ctx={settings.embedding_context_window} chunk={settings.chunk_size}/{settings.chunk_overlap} top_k={settings.top_k} rerank_pool={settings.rerank_pool_size}")

        rag_index, indexing_seconds, indexing_details = index_documents(pdf_paths, settings, embedding_provider)
        evaluation = evaluate_questions(questions, rag_index, settings, embedding_provider)

        result = {
            "benchmark": group_name,
            "label": label,
            "settings": {
                "embedding_model": settings.embedding_model,
                "embedding_context_window": settings.embedding_context_window,
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap,
                "top_k": settings.top_k,
                "rerank_pool_size": settings.rerank_pool_size,
                "embedding_truncate": settings.embedding_truncate,
                "pdf_extraction_mode": settings.pdf_extraction_mode,
            },
            "pdfs": [path.name for path in pdf_paths],
            "indexing_seconds": round(indexing_seconds, 4),
            "indexing_details": indexing_details,
            "metrics": evaluation["metrics"],
            "questions": evaluation["per_question"],
        }

        (run_output_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(
            f"[done] {label} | Hit@1={result['metrics']['hit_at_1']:.4f} "
            f"Hit@K={result['metrics']['hit_at_k']:.4f} "
            f"MRR={result['metrics']['mrr']:.4f} "
            f"Avg retrieval={result['metrics']['avg_retrieval_seconds']:.4f}s "
            f"Indexing={result['indexing_seconds']:.4f}s"
        )
        results.append(result)

    group_summary = summarise_group(group_name, results)
    (group_output_dir / "summary.json").write_text(json.dumps(group_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"summary": group_summary, "results": results}


def build_readme(suite_result: dict[str, Any]) -> str:
    lines = [
        "# Phase 4.5 benchmark suite",
        "",
        f"Generated at: `{suite_result['generated_at']}`",
        "",
        "## PDFs used",
        "",
    ]
    for pdf_name in suite_result["pdfs"]:
        lines.append(f"- `{pdf_name}`")

    lines.extend(["", "## Benchmark groups", ""])
    for group in suite_result["groups"]:
        summary = group["summary"]
        lines.append(f"### {summary['benchmark']}")
        lines.append("")
        lines.append(f"Best run: `{summary['best_label']}`")
        lines.append("")
        lines.append("| Rank | Label | Hit@1 | Hit@K | MRR | Avg retrieval (s) | Indexing (s) |")
        lines.append("|---|---|---:|---:|---:|---:|---:|")
        for rank, item in enumerate(summary["ranking"], start=1):
            metrics = item["metrics"]
            lines.append(
                f"| {rank} | `{item['label']}` | {metrics['hit_at_1']:.4f} | {metrics['hit_at_k']:.4f} | {metrics['mrr']:.4f} | {metrics['avg_retrieval_seconds']:.4f} | {item['indexing_seconds']:.4f} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete Phase 4.5 benchmark suite.")
    parser.add_argument("--pdfs", nargs="*", help="PDFs to index for the suite. Defaults to the project benchmark PDFs.")
    parser.add_argument("--suite-config", help="Optional JSON suite config path.")
    parser.add_argument(
        "--groups",
        nargs="*",
        choices=["embedding_models", "embedding_context_window", "retrieval_tuning"],
        help="Optional subset of benchmark groups to run.",
    )
    parser.add_argument("--output-dir", help="Optional output directory. Defaults to benchmark_runs/<timestamp>_phase_4_5_suite")
    args = parser.parse_args()

    pdf_paths = resolve_pdf_paths(args.pdfs)
    suite = load_suite(Path(args.suite_config) if args.suite_config else None)
    selected_groups = set(args.groups or ["embedding_models", "embedding_context_window", "retrieval_tuning"])

    registry = build_provider_registry()
    embedding_provider = registry["ollama"]["instance"]

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else BASE_DIR / "benchmark_runs" / f"{timestamp}_phase_4_5_suite"
    output_dir.mkdir(parents=True, exist_ok=True)

    suite_result = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pdfs": [path.name for path in pdf_paths],
        "questions": suite["questions"],
        "groups": [],
    }

    for group_name, group_config in suite["benchmarks"].items():
        if group_name not in selected_groups:
            continue
        if not group_config.get("enabled", True):
            continue
        group_result = run_group(
            group_name=group_name,
            group_config=group_config,
            questions=suite["questions"],
            pdf_paths=pdf_paths,
            embedding_provider=embedding_provider,
            root_output_dir=output_dir,
        )
        suite_result["groups"].append(group_result)

    (output_dir / "summary.json").write_text(json.dumps(suite_result, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "README.md").write_text(build_readme(suite_result), encoding="utf-8")

    print(f"\nSuite summary written to: {output_dir / 'summary.json'}")
    print(f"Human-readable report: {output_dir / 'README.md'}")


if __name__ == "__main__":
    main()
