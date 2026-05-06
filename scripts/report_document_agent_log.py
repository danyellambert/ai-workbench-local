from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.storage.runtime_paths import get_phase6_document_agent_log_path  # noqa: E402
from src.storage.phase6_document_agent_log import (  # noqa: E402
    load_document_agent_log,
    summarize_document_agent_log,
)


def _build_needs_review_examples(entries: list[dict[str, object]], limit: int = 10) -> list[dict[str, object]]:
    examples: list[dict[str, object]] = []
    for entry in reversed(entries):
        if not bool(entry.get("needs_review")):
            continue
        examples.append(
            {
                "timestamp": entry.get("timestamp"),
                "user_intent": entry.get("user_intent"),
                "tool_used": entry.get("tool_used"),
                "confidence": entry.get("confidence"),
                "source_count": entry.get("source_count"),
                "needs_review_reason": entry.get("needs_review_reason"),
                "query": entry.get("query"),
            }
        )
        if len(examples) >= limit:
            break
    return examples


def _build_report(entries: list[dict[str, object]], recent_limit: int = 15) -> dict[str, object]:
    return {
        "aggregate": summarize_document_agent_log(entries),
        "recent_runs": list(reversed(entries[-recent_limit:])) if entries else [],
        "needs_review_examples": _build_needs_review_examples(entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Phase 6 report for Document Operations Copilot executions.")
    parser.add_argument(
        "--log",
        default=str(get_phase6_document_agent_log_path(ROOT_DIR)),
        help="Path to the local Document Operations Copilot log JSON file.",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT_DIR / "phase5_eval/reports/phase6_document_agent_summary.json"),
        help="Path to save the generated Phase 6 summary report.",
    )
    args = parser.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.out)
    entries = load_document_agent_log(log_path)
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