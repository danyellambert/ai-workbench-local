from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Report only files where VL was called from multilayout benchmark")
    parser.add_argument("--benchmark", default="phase5_eval/reports/evidence_cv_multilayout_router_benchmark.json")
    parser.add_argument("--out", default="phase5_eval/reports/evidence_cv_vl_called_cases_report.json")
    args = parser.parse_args()

    payload = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    called_cases = []
    category_counts: dict[str, int] = {}

    for item in payload.get("per_file", []):
        router = ((item.get("evidence_router") or {}).get("vl_router") or {})
        if not router.get("enabled"):
            continue
        category = item.get("vl_value_category") or "unknown"
        category_counts[category] = category_counts.get(category, 0) + 1
        called_cases.append(
            {
                "file": item.get("file"),
                "source_type": (item.get("evidence_router") or {}).get("source_type"),
                "reasons": router.get("reasons"),
                "regions_selected": router.get("regions_selected"),
                "evidence_summary": (item.get("evidence_router") or {}).get("evidence_summary"),
                "vl_value_category": category,
                "semantic_diagnosis": item.get("semantic_diagnosis"),
            }
        )

    report = {
        "aggregate": {
            "vl_called_cases": len(called_cases),
            "category_counts": category_counts,
        },
        "cases": called_cases,
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())