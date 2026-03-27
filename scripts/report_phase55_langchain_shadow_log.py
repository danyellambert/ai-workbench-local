from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.storage.phase55_shadow_log import load_shadow_log, summarize_shadow_log


def _build_divergence_examples(entries: list[dict[str, object]], limit: int = 10) -> list[dict[str, object]]:
    examples: list[dict[str, object]] = []
    for entry in reversed(entries):
        if bool(entry.get("same_top_1")) and bool(entry.get("same_top_3_order")):
            continue
        examples.append(
            {
                "timestamp": entry.get("timestamp"),
                "query": entry.get("query"),
                "primary_strategy": entry.get("primary_strategy"),
                "alternate_strategy": entry.get("alternate_strategy"),
                "overlap_ratio": entry.get("overlap_ratio"),
                "same_top_1": entry.get("same_top_1"),
                "same_top_3_order": entry.get("same_top_3_order"),
                "primary_top_1": entry.get("primary_top_1"),
                "alternate_top_1": entry.get("alternate_top_1"),
                "alternate_fallback_reason": entry.get("alternate_fallback_reason"),
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _build_report(entries: list[dict[str, object]], recent_limit: int = 15) -> dict[str, object]:
    aggregate = summarize_shadow_log(entries)
    recent_runs = list(reversed(entries[-recent_limit:])) if entries else []
    return {
        "aggregate": aggregate,
        "recent_runs": recent_runs,
        "divergence_examples": _build_divergence_examples(entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Phase 5.5 shadow comparison report for manual vs LangChain retrieval.")
    parser.add_argument(
        "--log",
        default=str(ROOT_DIR / ".phase55_langchain_shadow_log.json"),
        help="Path to the local shadow log JSON file.",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT_DIR / "phase5_eval/reports/phase55_langchain_shadow_summary.json"),
        help="Path to save the generated summary report.",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.out)
    entries = load_shadow_log(log_path)
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