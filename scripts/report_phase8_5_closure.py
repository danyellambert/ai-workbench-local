from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.storage.runtime_paths import get_phase8_eval_db_path  # noqa: E402
from src.services.phase8_5_closure import build_phase8_5_closure_bundle, render_phase8_5_closure_markdown  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the final Phase 8.5 closure bundle.")
    parser.add_argument("--benchmark-run-dir", default=None, help="Optional benchmark run directory to inspect.")
    parser.add_argument("--eval-db", default=str(get_phase8_eval_db_path(ROOT_DIR)), help="Path to the Phase 8 eval SQLite database.")
    parser.add_argument(
        "--out-json",
        default=str(ROOT_DIR / "phase5_eval" / "reports" / "phase8_5_closure_summary.json"),
        help="Path to write the closure JSON summary.",
    )
    parser.add_argument(
        "--out-md",
        default=str(ROOT_DIR / "phase5_eval" / "reports" / "phase8_5_closure_report.md"),
        help="Path to write the closure markdown report.",
    )
    parser.add_argument("--print-markdown", action="store_true", help="Also print markdown after JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_phase8_5_closure_bundle(
        project_root=ROOT_DIR,
        benchmark_run_dir=args.benchmark_run_dir,
        eval_db_path=args.eval_db,
    )
    markdown = render_phase8_5_closure_markdown(summary)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.print_markdown:
        print("\n---\n")
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())