from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.storage.runtime_paths import get_phase8_eval_db_path  # noqa: E402
from src.services.phase8_5_audit import build_phase8_5_audit, render_phase8_5_audit_markdown  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the Phase 8.5 Round 0 audit/preflight artifact.")
    parser.add_argument("--benchmark-run-dir", default=None, help="Optional benchmark run directory to inspect.")
    parser.add_argument("--eval-db", default=str(get_phase8_eval_db_path(ROOT_DIR)), help="Path to the Phase 8 eval SQLite database.")
    parser.add_argument("--out-json", default=None, help="Optional JSON output path.")
    parser.add_argument("--out-md", default=None, help="Optional markdown output path.")
    parser.add_argument("--print-markdown", action="store_true", help="Also print markdown after JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_phase8_5_audit(
        project_root=ROOT_DIR,
        benchmark_run_dir=args.benchmark_run_dir,
        eval_db_path=args.eval_db,
    )
    markdown = render_phase8_5_audit_markdown(audit)
    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.out_md:
        out_md = Path(args.out_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(markdown + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if args.print_markdown:
        print("\n---\n")
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())