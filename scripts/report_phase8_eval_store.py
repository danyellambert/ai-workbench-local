from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.evals.phase8_thresholds import build_phase8_threshold_catalog  # noqa: E402
from src.storage.runtime_paths import get_phase8_eval_db_path  # noqa: E402
from src.storage.phase8_eval_store import load_eval_runs, summarize_eval_runs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Phase 8 eval summary from the local SQLite store.")
    parser.add_argument(
        "--db",
        default=str(get_phase8_eval_db_path(ROOT_DIR)),
        help="Path to the local Phase 8 eval SQLite database.",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT_DIR / "phase5_eval/reports/phase8_eval_summary.json"),
        help="Path to save the generated Phase 8 eval summary.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of recent eval runs to include in the report.",
    )
    parser.add_argument(
        "--suite",
        default=None,
        help="Optional suite_name filter for the summary/report.",
    )
    parser.add_argument(
        "--task",
        default=None,
        help="Optional task_type filter for the summary/report.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    entries = load_eval_runs(db_path, suite_name=args.suite, task_type=args.task)
    payload = {
        "db_path": str(db_path),
        "suite_filter": args.suite,
        "task_filter": args.task,
        "threshold_catalog": build_phase8_threshold_catalog(),
        "aggregate": summarize_eval_runs(entries),
        "recent_runs": load_eval_runs(db_path, suite_name=args.suite, task_type=args.task, limit=args.limit),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())