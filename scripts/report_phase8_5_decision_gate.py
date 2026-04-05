from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.services.phase8_5_decision_gate import (  # noqa: E402
    find_latest_phase8_5_run_dir,
    load_phase8_5_benchmark_artifacts,
    build_phase8_5_decision_summary,
    render_phase8_5_decision_markdown,
)
from src.storage.phase8_eval_diagnosis import build_eval_diagnosis  # noqa: E402
from src.storage.phase8_eval_store import load_eval_runs, summarize_eval_runs  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the Phase 8.5 Round 3 decision-gate summary.")
    parser.add_argument(
        "--benchmark-run-dir",
        default=None,
        help="Optional Phase 8.5 benchmark run directory. Defaults to the latest detected run under benchmark_runs/phase8_5_matrix or benchmark_runs/phase8_5_round1.",
    )
    parser.add_argument(
        "--eval-db",
        default=str(ROOT_DIR / ".phase8_eval_runs.sqlite3"),
        help="Path to the local Phase 8 eval SQLite database.",
    )
    parser.add_argument(
        "--out-json",
        default=None,
        help="Optional path to write the machine-readable decision summary JSON.",
    )
    parser.add_argument(
        "--out-md",
        default=None,
        help="Optional path to write the markdown decision report.",
    )
    parser.add_argument(
        "--print-markdown",
        action="store_true",
        help="Also print the markdown report to stdout after the JSON summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.benchmark_run_dir) if args.benchmark_run_dir else find_latest_phase8_5_run_dir(ROOT_DIR)
    if run_dir is None:
        raise SystemExit("No Phase 8.5 benchmark run directory could be detected.")

    artifacts = load_phase8_5_benchmark_artifacts(run_dir)
    eval_entries = load_eval_runs(Path(args.eval_db))
    eval_summary = summarize_eval_runs(eval_entries)
    eval_diagnosis = build_eval_diagnosis(eval_entries)

    decision_summary = build_phase8_5_decision_summary(
        benchmark_summary=artifacts.get("summary") if isinstance(artifacts.get("summary"), dict) else {},
        benchmark_events=[item for item in (artifacts.get("events") or []) if isinstance(item, dict)],
        manifest=artifacts.get("manifest") if isinstance(artifacts.get("manifest"), dict) else {},
        preflight=artifacts.get("preflight") if isinstance(artifacts.get("preflight"), dict) else {},
        eval_summary=eval_summary,
        eval_diagnosis=eval_diagnosis,
        benchmark_run_dir=str(run_dir),
    )
    markdown = render_phase8_5_decision_markdown(decision_summary)

    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(decision_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(markdown + "\n", encoding="utf-8")

    print(json.dumps(decision_summary, ensure_ascii=False, indent=2))
    if args.print_markdown:
        print("\n---\n")
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())