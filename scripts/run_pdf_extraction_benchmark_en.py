from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import argparse
import csv
import json
import re
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from src.config import BASE_DIR, get_ollama_settings, get_rag_settings
from src.prompt_profiles import build_prompt_messages
from src.providers.registry import build_provider_registry
from src.rag.loaders import load_document
from src.rag.pdf_extraction import describe_pdf_extraction_mode, normalize_pdf_extraction_mode
from src.rag.prompting import inject_rag_context
from src.rag.service import build_source_metadata, retrieve_relevant_chunks_detailed, upsert_documents_in_rag_index


DEFAULT_PDFS = [
    "2025-HB-44-20250106-Final-508.pdf",
    "kaur-2016-ijca-911367.pdf",
    "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf",
    "c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf",
]

COMMON_QUESTIONS = [
    "What is the central topic of the document?",
    "What are the 3 most important sections or takeaways?",
    "Does the document contain tables? What do they show?",
    "Does the document contain figures or diagrams? What do they show?",
    "What is one important piece of information from the middle of the document?",
    "What is one limitation, note, or important observation mentioned near the end?",
]

DOCUMENT_QUESTIONS = {
    "kaur-2016-ijca-911367.pdf": [
        "What main problem does the paper try to solve?",
        "What are the main contributions of the work?",
        "What does Figure 1 show?",
        "What does Figure 3 show?",
        "What does Figure 4 show?",
        "Which method or combination achieved the best performance?",
        "Which evaluation metric was used?",
        "What does the main results table compare?",
        "What limitations or future work are mentioned?",
        "At a high level, how does the method work based on both the text and the figures?",
    ],
    "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf": [
        "What main problem does the paper try to solve?",
        "What core observations motivate the proposed method?",
        "What does Figure 1 show?",
        "What does Figure 2 illustrate?",
        "What does Figure 3 show?",
        "What does Figure 5 show?",
        "At a high level, how does the curvilinear projection work?",
        "Which algorithm is used to solve the optimization problem?",
        "What are the main experimental results described in the paper?",
        "According to the paper, what kinds of robustness does the method demonstrate?",
    ],
    "c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf": [
        "What is the exact title of the document?",
        "Which organization is responsible for the document?",
        "What is the main topic of the manual?",
        "What are the main sections or chapters of the manual?",
        "Which scanner models are mentioned near the beginning?",
        "How do you connect the base using USB?",
        "How do you connect the base using keyboard wedge?",
        "What battery and safety warnings are mentioned?",
        "Which certifications or regulatory compliance items appear in the document?",
        "What do the figures or diagrams in the opening chapter illustrate?",
    ],
    "2025-HB-44-20250106-Final-508.pdf": [
        "What is the overall purpose of the handbook?",
        "What are the major parts or blocks of the document?",
        "What does the abstract say about specifications, tolerances, and technical requirements?",
        "How is the document organized structurally?",
        "Which sections appear in the main table of contents?",
        "What does the Introduction say about the purpose of the handbook?",
        "What does the document say about retroactive and nonretroactive requirements?",
        "Looking at Section 2.20 Scales, what does it cover at a high level?",
        "Are there important tables in the opening pages? What do they organize?",
        "According to the opening pages, which types of devices or systems does the handbook cover?",
    ],
}


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "file"


class UploadedPath:
    def __init__(self, path: Path):
        self._path = path
        self.name = path.name
        self.size = path.stat().st_size
        self.type = "application/pdf"

    def getvalue(self) -> bytes:
        return self._path.read_bytes()



def _resolve_pdf_paths(paths: list[str] | None) -> list[Path]:
    candidates = [Path(p) for p in paths] if paths else []
    if not candidates:
        for name in DEFAULT_PDFS:
            local = BASE_DIR / name
            if local.exists():
                candidates.append(local)
                continue
            data_path = Path("/mnt/data") / name
            if data_path.exists():
                candidates.append(data_path)
    resolved: list[Path] = []
    for path in candidates:
        if path.exists():
            resolved.append(path.resolve())
    if not resolved:
        raise RuntimeError(
            "No PDFs were found. Pass paths with --pdfs or place the files in the project directory."
        )
    return resolved



def _questions_for_pdf(path: Path) -> list[str]:
    specific = DOCUMENT_QUESTIONS.get(path.name, [])
    questions = [*specific, *COMMON_QUESTIONS]
    deduped: list[str] = []
    seen: set[str] = set()
    for question in questions:
        if question not in seen:
            deduped.append(question)
            seen.add(question)
    return deduped



def _generate_answer(
    provider,
    model: str,
    context_window: int,
    prompt_profile: str,
    question: str,
    retrieved_chunks: list[dict[str, Any]],
    rag_settings,
) -> tuple[str, dict[str, Any], float, str | None]:
    user_message = {"role": "user", "content": question}
    messages = build_prompt_messages(prompt_profile, [user_message])
    injected_messages, budget_details = inject_rag_context(
        messages,
        retrieved_chunks,
        context_window=context_window,
        settings=rag_settings,
    )
    started = time.perf_counter()
    try:
        stream = provider.stream_chat_completion(
            messages=injected_messages,
            model=model,
            temperature=0.0,
            context_window=context_window,
        )
        answer = "".join(provider.iter_stream_text(stream)).strip()
        return answer, budget_details, time.perf_counter() - started, None
    except Exception as error:
        return "", budget_details, time.perf_counter() - started, str(error)



def run_benchmark(
    pdf_paths: list[Path],
    modes: list[str],
    generate_answers: bool,
    provider_name: str,
    model: str | None,
    context_window: int | None,
    prompt_profile: str,
    output_dir: Path,
) -> dict[str, Any]:
    settings = get_rag_settings()
    ollama_settings = get_ollama_settings()
    registry = build_provider_registry()
    if provider_name not in registry:
        raise RuntimeError(f"Provider `{provider_name}` is not available.")

    provider = registry[provider_name]["instance"]
    selected_model = model or (
        ollama_settings.default_model if provider_name == "ollama" else getattr(provider.settings, "model", None)
    )
    if not selected_model:
        raise RuntimeError("No generation model was selected.")
    selected_context_window = int(context_window or ollama_settings.default_context_window)

    embedding_provider = registry["ollama"]["instance"]
    output_dir.mkdir(parents=True, exist_ok=True)

    benchmark: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "provider": provider_name,
        "model": selected_model,
        "prompt_profile": prompt_profile,
        "context_window": selected_context_window,
        "generate_answers": generate_answers,
        "pdfs": [],
        "summary": [],
    }

    for pdf_path in pdf_paths:
        pdf_entry: dict[str, Any] = {
            "pdf_name": pdf_path.name,
            "pdf_path": str(pdf_path),
            "questions": _questions_for_pdf(pdf_path),
            "modes": {},
        }
        print(f"\n=== Benchmark: {pdf_path.name} ===")
        for raw_mode in modes:
            mode = normalize_pdf_extraction_mode(raw_mode)
            mode_settings = replace(
                settings,
                pdf_extraction_mode=mode,
                store_path=output_dir / f".rag_store_{_slugify(pdf_path.stem)}_{mode}.json",
                chroma_path=output_dir / f".chroma_{_slugify(pdf_path.stem)}_{mode}",
            )
            uploaded = UploadedPath(pdf_path)
            print(f"\n--- Mode: {mode} ({describe_pdf_extraction_mode(mode)}) ---")
            extraction_started = time.perf_counter()
            loaded_document = load_document(uploaded, mode_settings)
            extraction_seconds = time.perf_counter() - extraction_started

            indexing_started = time.perf_counter()
            rag_index, sync_status = upsert_documents_in_rag_index(
                documents=[loaded_document],
                settings=mode_settings,
                embedding_provider=embedding_provider,
                rag_index=None,
            )
            indexing_seconds = time.perf_counter() - indexing_started

            chunks = rag_index.get("chunks", []) if isinstance(rag_index, dict) else []
            loader_metadata = loaded_document.metadata if isinstance(loaded_document.metadata, dict) else {}
            mode_entry: dict[str, Any] = {
                "mode": mode,
                "mode_label": describe_pdf_extraction_mode(mode),
                "extraction_seconds": round(extraction_seconds, 3),
                "indexing_seconds": round(indexing_seconds, 3),
                "document_char_count": len(loaded_document.text),
                "chunk_count": len(chunks),
                "sync_status": sync_status,
                "loader_metadata": loader_metadata,
                "questions": [],
            }

            for question in pdf_entry["questions"]:
                retrieval_started = time.perf_counter()
                retrieval_details = retrieve_relevant_chunks_detailed(
                    query=question,
                    rag_index=rag_index,
                    settings=mode_settings,
                    embedding_provider=embedding_provider,
                )
                retrieval_seconds = time.perf_counter() - retrieval_started
                retrieved_chunks = retrieval_details.get("chunks", []) or []
                answer = ""
                generation_seconds = 0.0
                generation_error = None
                prompt_budget = None
                if generate_answers:
                    answer, prompt_budget, generation_seconds, generation_error = _generate_answer(
                        provider=provider,
                        model=selected_model,
                        context_window=selected_context_window,
                        prompt_profile=prompt_profile,
                        question=question,
                        retrieved_chunks=retrieved_chunks,
                        rag_settings=mode_settings,
                    )

                question_result = {
                    "question": question,
                    "retrieval_seconds": round(retrieval_seconds, 3),
                    "generation_seconds": round(generation_seconds, 3),
                    "generation_error": generation_error,
                    "retrieved_chunks_count": len(retrieved_chunks),
                    "retrieval_backend": retrieval_details.get("backend_used"),
                    "retrieval_backend_message": retrieval_details.get("backend_message"),
                    "retrieval_strategy": retrieval_details.get("rerank_strategy"),
                    "top_sources": build_source_metadata(retrieved_chunks[: min(4, len(retrieved_chunks))]),
                    "answer": answer,
                    "prompt_budget": prompt_budget,
                    "manual_score": None,
                    "manual_notes": "",
                }
                mode_entry["questions"].append(question_result)

            pdf_entry["modes"][mode] = mode_entry
            benchmark["summary"].append(
                {
                    "pdf_name": pdf_path.name,
                    "mode": mode,
                    "mode_label": describe_pdf_extraction_mode(mode),
                    "extraction_seconds": mode_entry["extraction_seconds"],
                    "indexing_seconds": mode_entry["indexing_seconds"],
                    "document_char_count": mode_entry["document_char_count"],
                    "chunk_count": mode_entry["chunk_count"],
                    "docling_mode": loader_metadata.get("docling_mode"),
                    "docling_pages_used": loader_metadata.get("docling_pages_used"),
                    "suspicious_pages": loader_metadata.get("suspicious_pages"),
                }
            )
        benchmark["pdfs"].append(pdf_entry)

    return benchmark



def write_outputs(benchmark: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"benchmark_pdf_extraction_{stamp}.json"
    csv_path = output_dir / f"benchmark_pdf_extraction_summary_{stamp}.csv"
    md_path = output_dir / f"benchmark_pdf_extraction_review_{stamp}.md"

    json_path.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "pdf_name",
                "mode",
                "mode_label",
                "extraction_seconds",
                "indexing_seconds",
                "document_char_count",
                "chunk_count",
                "docling_mode",
                "docling_pages_used",
                "suspicious_pages",
            ],
        )
        writer.writeheader()
        for row in benchmark.get("summary", []):
            serialized = dict(row)
            for key in ("docling_pages_used",):
                if key in serialized and isinstance(serialized[key], list):
                    serialized[key] = ",".join(str(item) for item in serialized[key])
            writer.writerow(serialized)

    md_lines = [
        "# PDF Extraction Benchmark Review",
        "",
        f"Generated at: {benchmark.get('generated_at')}",
        f"Provider: {benchmark.get('provider')} · Model: {benchmark.get('model')} · Prompt profile: {benchmark.get('prompt_profile')}",
        "",
        "## How to use this review file",
        "",
        "For each question, fill in:",
        "- `manual_score`: 0, 1, or 2",
        "- `manual_notes`: comments about answer quality, retrieval quality, and noise",
        "",
    ]

    for pdf_entry in benchmark.get("pdfs", []):
        md_lines.append(f"## {pdf_entry.get('pdf_name')}")
        md_lines.append("")
        for mode_name, mode_entry in pdf_entry.get("modes", {}).items():
            md_lines.append(f"### Mode: {mode_name} — {mode_entry.get('mode_label')}")
            md_lines.append("")
            md_lines.append(f"- Extraction time: {mode_entry.get('extraction_seconds')} s")
            md_lines.append(f"- Indexing time: {mode_entry.get('indexing_seconds')} s")
            md_lines.append(f"- Final characters: {mode_entry.get('document_char_count')}")
            md_lines.append(f"- Chunks: {mode_entry.get('chunk_count')}")
            metadata = mode_entry.get("loader_metadata", {}) or {}
            md_lines.append(f"- Docling mode: {metadata.get('docling_mode')}")
            md_lines.append(f"- Suspicious pages: {metadata.get('suspicious_page_numbers')}")
            md_lines.append(f"- Pages processed with Docling: {metadata.get('docling_pages_used')}")
            md_lines.append("")
            for index, question in enumerate(mode_entry.get("questions", []), start=1):
                md_lines.append(f"#### Question {index}")
                md_lines.append("")
                md_lines.append(f"**Question:** {question.get('question')}")
                md_lines.append("")
                md_lines.append(f"**Retrieval backend:** {question.get('retrieval_backend')}")
                md_lines.append(f"**Retrieval time:** {question.get('retrieval_seconds')} s")
                md_lines.append(f"**Generation time:** {question.get('generation_seconds')} s")
                md_lines.append(f"**Top sources:** `{json.dumps(question.get('top_sources', []), ensure_ascii=False)}`")
                answer = (question.get("answer") or "").strip()
                if answer:
                    md_lines.append("")
                    md_lines.append("**Generated answer:**")
                    md_lines.append("")
                    md_lines.append(answer)
                md_lines.append("")
                md_lines.append("- manual_score: ")
                md_lines.append("- manual_notes: ")
                md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "markdown": md_path}



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the project's PDF extraction benchmark automation.")
    parser.add_argument("--pdfs", nargs="*", help="List of PDF paths to evaluate.")
    parser.add_argument("--modes", nargs="*", default=["basic", "hybrid", "complete"], help="Extraction modes to test.")
    parser.add_argument("--no-generate", action="store_true", help="Skip LLM answer generation and collect only extraction and retrieval data.")
    parser.add_argument("--provider", default="ollama", help="Provider used for answer generation.")
    parser.add_argument("--model", default=None, help="Generation model.")
    parser.add_argument("--context-window", type=int, default=None, help="Context window for generation.")
    parser.add_argument("--prompt-profile", default="neutral", help="Prompt profile.")
    parser.add_argument("--output-dir", default=str(BASE_DIR / "benchmark_runs"), help="Output directory.")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    pdf_paths = _resolve_pdf_paths(args.pdfs)
    modes = [normalize_pdf_extraction_mode(mode) for mode in args.modes]
    output_dir = Path(args.output_dir)

    benchmark = run_benchmark(
        pdf_paths=pdf_paths,
        modes=modes,
        generate_answers=not args.no_generate,
        provider_name=args.provider,
        model=args.model,
        context_window=args.context_window,
        prompt_profile=args.prompt_profile,
        output_dir=output_dir,
    )
    outputs = write_outputs(benchmark, output_dir)
    print("\nBenchmark completed.")
    for name, path in outputs.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
