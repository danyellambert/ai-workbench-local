from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.storage.runtime_paths import get_phase8_eval_db_path  # noqa: E402
from src.storage.phase8_eval_import import import_eval_history_reports  # noqa: E402
from src.storage.phase8_eval_store import load_eval_runs, summarize_eval_runs  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill the Phase 8 SQLite eval store from historical JSON reports.")
    parser.add_argument(
        "--reports-dir",
        default=str(ROOT_DIR / "phase5_eval" / "reports"),
        help="Directory containing historical eval JSON reports.",
    )
    parser.add_argument(
        "--db",
        default=str(get_phase8_eval_db_path(ROOT_DIR)),
        help="Path to the Phase 8 eval SQLite database.",
    )
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    db_path = Path(args.db)
    imported_counts = import_eval_history_reports(reports_dir, db_path)
    entries = load_eval_runs(db_path)
    payload = {
        "reports_dir": str(reports_dir),
        "db_path": str(db_path),
        "imported_counts": imported_counts,
        "aggregate": summarize_eval_runs(entries),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())