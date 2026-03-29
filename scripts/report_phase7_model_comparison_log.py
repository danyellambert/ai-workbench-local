from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.storage.phase7_model_comparison_log import (  # noqa: E402
    load_model_comparison_log,
    summarize_model_comparison_log,
)
from src.storage.phase55_shadow_log import load_shadow_log, summarize_shadow_log  # noqa: E402
from src.storage.phase55_langgraph_shadow_log import load_langgraph_shadow_log, summarize_langgraph_shadow_log  # noqa: E402


def _build_report(
    entries: list[dict[str, object]],
    retrieval_shadow_entries: list[dict[str, object]],
    langgraph_shadow_entries: list[dict[str, object]],
    recent_limit: int = 10,
) -> dict[str, object]:
    aggregate = summarize_model_comparison_log(entries)
    return {
        "aggregate": aggregate,
        "highlights": {
            "top_provider": aggregate.get("top_provider"),
            "top_model": aggregate.get("top_model"),
            "top_format": aggregate.get("top_format"),
            "top_runtime_bucket": aggregate.get("top_runtime_bucket"),
            "top_quantization_family": aggregate.get("top_quantization_family"),
            "top_retrieval_strategy": (aggregate.get("retrieval_strategy_leaderboard") or [None])[0],
            "top_embedding_provider": (aggregate.get("embedding_provider_leaderboard") or [None])[0],
            "top_embedding_model": (aggregate.get("embedding_model_leaderboard") or [None])[0],
            "top_prompt_profile": (aggregate.get("prompt_profile_leaderboard") or [None])[0],
            "top_benchmark_use_case": aggregate.get("top_benchmark_use_case"),
            "avg_groundedness_score": aggregate.get("avg_groundedness_score"),
            "avg_schema_adherence": aggregate.get("avg_schema_adherence"),
            "avg_use_case_fit_score": aggregate.get("avg_use_case_fit_score"),
        },
        "leaderboards": {
            "providers": aggregate.get("provider_leaderboard") or [],
            "models": aggregate.get("model_leaderboard") or [],
            "formats": aggregate.get("format_leaderboard") or [],
            "runtime_buckets": aggregate.get("runtime_bucket_leaderboard") or [],
            "quantization_families": aggregate.get("quantization_family_leaderboard") or [],
            "retrieval_strategies": aggregate.get("retrieval_strategy_leaderboard") or [],
            "embedding_providers": aggregate.get("embedding_provider_leaderboard") or [],
            "embedding_models": aggregate.get("embedding_model_leaderboard") or [],
            "prompt_profiles": aggregate.get("prompt_profile_leaderboard") or [],
            "document_usage": aggregate.get("document_usage_leaderboard") or [],
            "benchmark_use_cases": aggregate.get("benchmark_use_case_leaderboard") or [],
        },
        "strategy_benchmarks": {
            "retrieval_shadow": summarize_shadow_log(retrieval_shadow_entries),
            "langgraph_shadow": summarize_langgraph_shadow_log(langgraph_shadow_entries),
        },
        "recent_runs": list(reversed(entries[-recent_limit:])) if entries else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Phase 7 model comparison report.")
    parser.add_argument(
        "--log",
        default=str(ROOT_DIR / ".phase7_model_comparison_log.json"),
        help="Path to the local model comparison log JSON file.",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT_DIR / "phase5_eval/reports/phase7_model_comparison_summary.json"),
        help="Path to save the generated model comparison summary.",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.out)
    entries = load_model_comparison_log(log_path)
    retrieval_shadow_entries = load_shadow_log(ROOT_DIR / ".phase55_langchain_shadow_log.json")
    langgraph_shadow_entries = load_langgraph_shadow_log(ROOT_DIR / ".phase55_langgraph_shadow_log.json")
    payload = {
        "log_path": str(log_path),
        **_build_report(entries, retrieval_shadow_entries, langgraph_shadow_entries),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())