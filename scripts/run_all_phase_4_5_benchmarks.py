from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import BASE_DIR
from src.providers.registry import build_provider_registry

DEFAULT_PDFS = [
    "2025-HB-44-20250106-Final-508.pdf",
    "kaur-2016-ijca-911367.pdf",
    "Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf",
    "c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf",
]

DEFAULT_EMBEDDING_MODELS = [
    "bge-m3:latest",
    "embeddinggemma:300m",
    "qwen3-embedding:0.6b",
    "nomic-embed-text-v2-moe:latest",
    "qwen3-embedding:4b",
]

RETRIEVAL_QUESTIONS = [
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
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all Phase 4.5 benchmark groups sequentially with fail-safe execution.")
    parser.add_argument("--pdfs", nargs="*", help="PDF files to benchmark. Defaults to the 4 benchmark PDFs.")
    parser.add_argument("--output-dir", help="Optional output directory. Defaults to benchmark_runs/<timestamp>_phase_4_5_all.")
    parser.add_argument("--test", action="store_true", help="Run a fast smoke test version of all 4 benchmark groups.")
    parser.add_argument("--skip-extraction-generation", action="store_true", help="Skip answer generation in the PDF extraction benchmark.")
    return parser.parse_args()



def resolve_pdf_paths(paths: list[str] | None) -> list[Path]:
    raw_paths = [Path(item) for item in paths] if paths else [Path(name) for name in DEFAULT_PDFS]
    resolved: list[Path] = []
    for path in raw_paths:
        candidates = [path]
        if not path.is_absolute():
            candidates.extend([ROOT_DIR / path, BASE_DIR / path.name, Path("/mnt/data") / path.name])
        for candidate in candidates:
            if candidate.exists():
                resolved.append(candidate.resolve())
                break
        else:
            raise FileNotFoundError(f"PDF not found: {path}")
    return resolved



def choose_context_windows(max_ctx: int | None, test_mode: bool) -> list[int]:
    if not isinstance(max_ctx, int) or max_ctx <= 0:
        max_ctx = 8192

    minimum = 256 if max_ctx >= 256 else max_ctx
    ladder = [minimum]
    for value in [512, 1024, 2048, 4096, 8192, 16384, 32768]:
        if minimum < value < max_ctx:
            ladder.append(value)
    if max_ctx not in ladder:
        ladder.append(max_ctx)

    ladder = sorted(dict.fromkeys(int(value) for value in ladder if value > 0))
    if not test_mode:
        return ladder

    if len(ladder) <= 2:
        return ladder
    midpoint = ladder[len(ladder) // 2]
    return sorted(dict.fromkeys([ladder[0], midpoint, ladder[-1]]))



def inspect_embedding_context_limits(models: list[str]) -> dict[str, dict[str, Any]]:
    provider = build_provider_registry()["ollama"]["instance"]
    info: dict[str, dict[str, Any]] = {}
    for model in models:
        try:
            details = provider.inspect_embedding_context_window(model=model)
            info[model] = {
                "declared_context_length": details.get("declared_context_length"),
                "show_available": details.get("show_available"),
                "show_error": details.get("show_error"),
            }
        except Exception as error:
            info[model] = {
                "declared_context_length": None,
                "show_available": False,
                "show_error": str(error),
            }
    return info



def build_suite_config(output_dir: Path, pdf_paths: list[Path], test_mode: bool) -> Path:
    embedding_models_full = DEFAULT_EMBEDDING_MODELS[:]
    if test_mode:
        embedding_models_for_group_2 = ["bge-m3:latest", "embeddinggemma:300m"]
        retrieval_questions = RETRIEVAL_QUESTIONS[:2]
    else:
        embedding_models_for_group_2 = embedding_models_full
        retrieval_questions = RETRIEVAL_QUESTIONS[:]

    context_info = inspect_embedding_context_limits(embedding_models_full)

    context_runs: list[dict[str, Any]] = []
    models_for_context = embedding_models_for_group_2 if test_mode else embedding_models_full
    for model in models_for_context:
        max_ctx = context_info.get(model, {}).get("declared_context_length")
        for ctx in choose_context_windows(max_ctx, test_mode):
            context_runs.append(
                {
                    "label": f"{model.replace(':', '_')}_ctx_{ctx}",
                    "embedding_model": model,
                    "embedding_context_window": ctx,
                }
            )

    if test_mode:
        retrieval_runs = [
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
        ]
    else:
        retrieval_runs = [
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
                "label": "lower_overlap",
                "chunk_size": 1200,
                "chunk_overlap": 80,
                "top_k": 4,
                "rerank_pool_size": 8,
            },
            {
                "label": "lighter_rerank_pool",
                "chunk_size": 1200,
                "chunk_overlap": 200,
                "top_k": 4,
                "rerank_pool_size": 4,
            },
        ]

    suite_config = {
        "questions": retrieval_questions,
        "benchmarks": {
            "embedding_models": {
                "enabled": True,
                "runs": [{"label": model.replace(":", "_"), "embedding_model": model} for model in embedding_models_for_group_2],
            },
            "embedding_context_window": {
                "enabled": True,
                "runs": context_runs,
            },
            "retrieval_tuning": {
                "enabled": True,
                "base": {
                    "embedding_model": "bge-m3:latest",
                    "embedding_context_window": 2048,
                },
                "runs": retrieval_runs,
            },
        },
        "meta": {
            "test_mode": test_mode,
            "pdfs": [path.name for path in pdf_paths],
            "context_inspection": context_info,
        },
    }

    config_path = output_dir / ("suite_config_test.json" if test_mode else "suite_config_full.json")
    config_path.write_text(json.dumps(suite_config, indent=2, ensure_ascii=False), encoding="utf-8")
    return config_path



def run_command(step_name: str, cmd: list[str], output_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    print(f"\n=== STEP: {step_name} ===")
    print("command:", " ".join(cmd))
    try:
        result = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, check=False)
        duration = time.perf_counter() - started
        log_path = output_dir / f"{step_name}.log"
        log_path.write_text(
            "STDOUT\n======\n"
            + (result.stdout or "")
            + "\n\nSTDERR\n======\n"
            + (result.stderr or ""),
            encoding="utf-8",
        )
        status = "ok" if result.returncode == 0 else "failed"
        print((result.stdout or "").strip())
        if result.returncode != 0 and result.stderr:
            print(result.stderr.strip())
        return {
            "step": step_name,
            "status": status,
            "returncode": result.returncode,
            "duration_seconds": round(duration, 4),
            "command": cmd,
            "log_path": str(log_path),
        }
    except Exception as error:
        duration = time.perf_counter() - started
        log_path = output_dir / f"{step_name}.log"
        log_path.write_text(str(error), encoding="utf-8")
        print(f"[error] {step_name}: {error}")
        return {
            "step": step_name,
            "status": "failed",
            "returncode": None,
            "duration_seconds": round(duration, 4),
            "command": cmd,
            "log_path": str(log_path),
            "error": str(error),
        }



def build_readme(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase 4.5 all-in-one benchmark runner",
        "",
        f"Generated at: `{summary['generated_at']}`",
        f"Test mode: `{summary['test_mode']}`",
        "",
        "## PDFs",
        "",
    ]
    for pdf in summary["pdfs"]:
        lines.append(f"- `{pdf}`")
    lines.extend(["", "## Steps", "", "| Step | Status | Duration (s) | Log |", "|---|---|---:|---|"])
    for step in summary["steps"]:
        lines.append(f"| `{step['step']}` | `{step['status']}` | {step['duration_seconds']:.4f} | `{step['log_path']}` |")
    return "\n".join(lines) + "\n"



def main() -> None:
    args = parse_args()
    pdf_paths = resolve_pdf_paths(args.pdfs)
    if args.test:
        pdf_paths = pdf_paths[:2]

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else BASE_DIR / "benchmark_runs" / f"{timestamp}_phase_4_5_all"
    output_dir.mkdir(parents=True, exist_ok=True)

    suite_config_path = build_suite_config(output_dir, pdf_paths, args.test)

    extraction_cmd = [
        sys.executable,
        "scripts/run_pdf_extraction_benchmark_en.py",
        "--pdfs",
        *[str(path) for path in (pdf_paths[:1] if args.test else pdf_paths)],
        "--output-dir",
        str(output_dir / "01_pdf_extraction"),
    ]
    if args.test:
        extraction_cmd.extend(["--modes", "basic"])
        extraction_cmd.append("--no-generate")
    elif args.skip_extraction_generation:
        extraction_cmd.append("--no-generate")

    embeddings_cmd = [
        sys.executable,
        "scripts/run_phase_4_5_benchmark_suite.py",
        "--pdfs",
        *[str(path) for path in pdf_paths],
        "--suite-config",
        str(suite_config_path),
        "--groups",
        "embedding_models",
        "--output-dir",
        str(output_dir / "02_embedding_models"),
    ]

    context_cmd = [
        sys.executable,
        "scripts/run_phase_4_5_benchmark_suite.py",
        "--pdfs",
        *[str(path) for path in pdf_paths],
        "--suite-config",
        str(suite_config_path),
        "--groups",
        "embedding_context_window",
        "--output-dir",
        str(output_dir / "03_embedding_context_windows"),
    ]

    tuning_cmd = [
        sys.executable,
        "scripts/run_phase_4_5_benchmark_suite.py",
        "--pdfs",
        *[str(path) for path in pdf_paths],
        "--suite-config",
        str(suite_config_path),
        "--groups",
        "retrieval_tuning",
        "--output-dir",
        str(output_dir / "04_retrieval_tuning"),
    ]

    steps = [
        run_command("01_pdf_extraction", extraction_cmd, output_dir),
        run_command("02_embedding_models", embeddings_cmd, output_dir),
        run_command("03_embedding_context_windows", context_cmd, output_dir),
        run_command("04_retrieval_tuning", tuning_cmd, output_dir),
    ]

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_mode": args.test,
        "pdfs": [path.name for path in pdf_paths],
        "suite_config_path": str(suite_config_path),
        "steps": steps,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "README.md").write_text(build_readme(summary), encoding="utf-8")

    print(f"\nMaster summary written to: {output_dir / 'summary.json'}")
    print(f"Human-readable report: {output_dir / 'README.md'}")


if __name__ == "__main__":
    main()
