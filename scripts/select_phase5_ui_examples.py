#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

PREFERRED = {
    "textual_pass": ["modern_two_column", "classic_one_column"],
    "visual_pass": ["compact_sidebar", "dense_executive"],
    "scan_warn": ["scan_like_image_pdf"],
    "scan_fail": ["scan_like_image_pdf"],
}

def load_rows(csv_path: Path):
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def pick_first(rows, *, layout=None, status=None):
    for row in rows:
        if layout and row.get("layout_type") != layout:
            continue
        if status and row.get("status") != status:
            continue
        return row
    return None

def main():
    parser = argparse.ArgumentParser(description="Select representative Phase 5 UI examples from resume benchmark results.")
    parser.add_argument("--csv", type=Path, required=True, help="Path to resume_benchmark_results.csv")
    parser.add_argument("--out", type=Path, default=Path("phase5_eval/ui_examples_manifest.json"))
    args = parser.parse_args()

    rows = load_rows(args.csv)

    manifest = {
        "textual_pass": pick_first(rows, layout="modern_two_column", status="PASS")
                        or pick_first(rows, layout="classic_one_column", status="PASS"),
        "visual_pass": pick_first(rows, layout="compact_sidebar", status="PASS")
                       or pick_first(rows, layout="dense_executive", status="PASS"),
        "scan_warn": pick_first(rows, layout="scan_like_image_pdf", status="WARN"),
        "scan_fail_or_low": pick_first(rows, layout="scan_like_image_pdf", status="FAIL")
                            or pick_first(rows, layout="scan_like_image_pdf", status="OCR_REQUIRED"),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved manifest to: {args.out}")
    for key, value in manifest.items():
        if value:
            print(f"{key}: {value['pdf_file']} [{value['status']}]")
        else:
            print(f"{key}: not found")

if __name__ == "__main__":
    main()
