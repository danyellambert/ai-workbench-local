from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_rag_settings
from src.rag.loaders import _extract_pdf_text, _extract_pdf_text_with_evidence_pipeline, _apply_hybrid_contact_policy, _build_shadow_rollout_report


def analyze_pdf(pdf_path: Path) -> dict[str, object]:
    rag = get_rag_settings()
    file_bytes = pdf_path.read_bytes()
    try:
        _, legacy_meta = _extract_pdf_text(file_bytes, rag)
        _, evidence_meta = _extract_pdf_text_with_evidence_pipeline(file_bytes, pdf_path.name, rag)
    except Exception as error:
        return {
            "file": str(pdf_path),
            "error": {
                "type": error.__class__.__name__,
                "message": str(error),
            },
        }

    hybrid = evidence_meta.get("hybrid_contact_policy") or _apply_hybrid_contact_policy(legacy_meta, evidence_meta)
    shadow = evidence_meta.get("shadow_rollout") or _build_shadow_rollout_report(legacy_meta, evidence_meta)
    evidence_summary = evidence_meta.get("evidence_summary") or {}

    return {
        "file": str(pdf_path),
        "source_type": evidence_meta.get("source_type"),
        "legacy": {
            "extractor": legacy_meta.get("extractor"),
            "strategy": legacy_meta.get("strategy"),
        },
        "evidence": {
            "extractor": evidence_meta.get("extractor"),
            "strategy": evidence_meta.get("strategy"),
            "summary": evidence_summary,
            "vl_runtime": evidence_meta.get("vl_runtime", {}),
        },
        "hybrid_contact_policy": hybrid,
        "shadow_rollout": shadow,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report shadow rollout metrics for evidence_cv hybrid policy")
    parser.add_argument("pdfs", nargs="+", help="PDF files to analyze")
    parser.add_argument("--out", default="phase5_eval/reports/evidence_cv_shadow_rollout_report.json")
    args = parser.parse_args()

    per_file = [analyze_pdf(Path(item)) for item in args.pdfs]
    valid_items = [item for item in per_file if "shadow_rollout" in item]
    aggregate = {
        "files": len(per_file),
        "files_failed": len([item for item in per_file if "error" in item]),
        "agreements": sum(int(item["shadow_rollout"].get("agreements") or 0) for item in valid_items),
        "email_complements": sum(int(item["shadow_rollout"].get("email_complements") or 0) for item in valid_items),
        "phone_complements": sum(int(item["shadow_rollout"].get("phone_complements") or 0) for item in valid_items),
        "email_conflicts": sum(int(item["shadow_rollout"].get("email_conflicts") or 0) for item in valid_items),
        "phone_conflicts": sum(int(item["shadow_rollout"].get("phone_conflicts") or 0) for item in valid_items),
        "vl_timeouts": sum(int((item.get("evidence", {}).get("vl_runtime", {}) or {}).get("timeouts") or 0) for item in valid_items),
        "vl_regions_failed": sum(int((item.get("evidence", {}).get("vl_runtime", {}) or {}).get("regions_failed") or 0) for item in valid_items),
    }
    payload = {"aggregate": aggregate, "per_file": per_file}
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())