from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.storage.runtime_paths import get_phase55_langgraph_shadow_log_path  # noqa: E402
from src.storage.phase55_langgraph_shadow_log import (  # noqa: E402
    load_langgraph_shadow_log,
    summarize_langgraph_shadow_log,
)


def _build_divergence_examples(entries: list[dict[str, object]], limit: int = 10) -> list[dict[str, object]]:
    examples: list[dict[str, object]] = []
    for entry in reversed(entries):
        if bool(entry.get("same_success")) and not bool(entry.get("alternate_better_quality")) and not bool(entry.get("primary_better_quality")):
            continue
        examples.append(
            {
                "timestamp": entry.get("timestamp"),
                "task_type": entry.get("task_type"),
                "primary_strategy_used": entry.get("primary_strategy_used"),
                "alternate_strategy_used": entry.get("alternate_strategy_used"),
                "primary_success": entry.get("primary_success"),
                "alternate_success": entry.get("alternate_success"),
                "quality_delta": entry.get("quality_delta"),
                "latency_delta_s": entry.get("latency_delta_s"),
                "alternate_avoided_review": entry.get("alternate_avoided_review"),
                "query": entry.get("query"),
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _build_report(entries: list[dict[str, object]], recent_limit: int = 15) -> dict[str, object]:
    return {
        "aggregate": summarize_langgraph_shadow_log(entries),
        "recent_runs": list(reversed(entries[-recent_limit:])) if entries else [],
        "divergence_examples": _build_divergence_examples(entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Phase 5.5 shadow comparison report for direct vs LangGraph structured execution.")
    parser.add_argument(
        "--log",
        default=str(get_phase55_langgraph_shadow_log_path(ROOT_DIR)),
        help="Path to the local LangGraph shadow log JSON file.",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT_DIR / "phase5_eval/reports/phase55_langgraph_shadow_summary.json"),
        help="Path to save the generated LangGraph summary report.",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.out)
    entries = load_langgraph_shadow_log(log_path)
    payload = {
        "log_path": str(log_path),
        **_build_report(entries),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())