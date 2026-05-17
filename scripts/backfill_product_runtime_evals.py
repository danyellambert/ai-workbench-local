from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.product.runtime_eval import HISTORICAL_BACKFILL_SOURCE, evaluate_product_runtime_run
from src.storage.phase8_eval_store import append_eval_run, load_eval_runs
from src.storage.product_telemetry import load_product_telemetry_runs
from src.storage.runtime_paths import get_phase8_eval_db_path, get_product_telemetry_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Backfill product runtime evals from persisted telemetry runs.')
    parser.add_argument('--workspace-root', default=str(ROOT_DIR))
    parser.add_argument('--limit', type=int, default=0, help='Process only the most recent N telemetry runs.')
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).resolve()
    telemetry_runs = load_product_telemetry_runs(get_product_telemetry_path(workspace_root))
    if args.limit and args.limit > 0:
        telemetry_runs = telemetry_runs[: args.limit]

    eval_db_path = get_phase8_eval_db_path(workspace_root)
    inserted = 0
    generated = 0
    for run in telemetry_runs:
        rows = evaluate_product_runtime_run(run, result=None, source=HISTORICAL_BACKFILL_SOURCE)
        for row in rows:
            generated += 1
            row_id = append_eval_run(eval_db_path, row)
            inserted += 1 if int(row_id or 0) > 0 else 0

    total_after = len(load_eval_runs(eval_db_path))
    print({
        'workspace_root': str(workspace_root),
        'telemetry_runs': len(telemetry_runs),
        'generated_eval_rows': generated,
        'inserted_eval_rows': inserted,
        'eval_db_path': str(eval_db_path),
        'total_eval_rows_after': total_after,
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
