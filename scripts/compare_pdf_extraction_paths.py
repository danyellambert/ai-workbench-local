from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_rag_settings
from src.rag.loaders import _extract_pdf_text, _extract_pdf_text_with_evidence_pipeline
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.evidence_cv.pipeline.runner import run_cv_pipeline_from_bytes


def compare_pdf(pdf_path: Path) -> dict[str, object]:
    rag_settings = get_rag_settings()
    file_bytes = pdf_path.read_bytes()

    legacy_text, legacy_metadata = _extract_pdf_text(file_bytes, rag_settings)

    evidence_error = None
    evidence_text = ""
    evidence_metadata: dict[str, object] = {}
    evidence_no_vl_summary: dict[str, object] | None = None
    try:
        no_vl_config = build_evidence_config_from_rag_settings(rag_settings)
        no_vl_config = no_vl_config.__class__(**{**no_vl_config.__dict__, "enable_vl": False})
        no_vl_result = run_cv_pipeline_from_bytes(file_bytes, ".pdf", no_vl_config)
        evidence_no_vl_summary = {
            "source_type": no_vl_result.source_type,
            "emails_found": len(no_vl_result.resume.emails),
            "phones_found": len(no_vl_result.resume.phones),
            "name_status": no_vl_result.resume.name.status,
            "location_status": no_vl_result.resume.location.status,
            "warnings": no_vl_result.warnings,
        }
        evidence_text, evidence_metadata = _extract_pdf_text_with_evidence_pipeline(
            file_bytes,
            pdf_path.name,
            rag_settings,
        )
    except Exception as error:  # pragma: no cover - operational comparison helper
        evidence_error = str(error)

    return {
        "file": str(pdf_path),
        "legacy": {
            "chars": len(legacy_text),
            "extractor": legacy_metadata.get("extractor"),
            "strategy": legacy_metadata.get("strategy"),
            "strategy_label": legacy_metadata.get("strategy_label"),
            "final_text_chars": legacy_metadata.get("final_text_chars"),
            "suspicious_pages": legacy_metadata.get("suspicious_pages"),
            "ocr_backend": legacy_metadata.get("ocr_backend"),
            "image_first_ocr_applied": legacy_metadata.get("image_first_ocr_applied"),
        },
        "evidence": {
            "chars": len(evidence_text),
            "extractor": evidence_metadata.get("extractor"),
            "strategy": evidence_metadata.get("strategy"),
            "source_type": evidence_metadata.get("source_type"),
            "warnings": evidence_metadata.get("warnings"),
            "without_vl": evidence_no_vl_summary,
            "summary": evidence_metadata.get("evidence_summary"),
            "vl_name_status": (evidence_metadata.get("evidence_summary") or {}).get("name_status"),
            "duplicates_or_noise": {
                "emails_minus_baseline": max(0, ((evidence_metadata.get("evidence_summary") or {}).get("emails_found") or 0) - ((evidence_no_vl_summary or {}).get("emails_found") or 0)),
                "phones_minus_baseline": max(0, ((evidence_metadata.get("evidence_summary") or {}).get("phones_found") or 0) - ((evidence_no_vl_summary or {}).get("phones_found") or 0)),
            },
            "error": evidence_error,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare legacy PDF extraction path with evidence_cv pipeline")
    parser.add_argument("pdfs", nargs="+", help="One or more PDF files to compare")
    parser.add_argument("--out", help="Optional JSON output path")
    args = parser.parse_args()

    results = [compare_pdf(Path(item)) for item in args.pdfs]
    aggregate = {
        "files": len(results),
        "legacy_total_chars": sum(item["legacy"]["chars"] for item in results),
        "evidence_total_chars": sum(item["evidence"]["chars"] for item in results),
        "with_vl_email_total": sum(((item["evidence"].get("summary") or {}).get("emails_found") or 0) for item in results),
        "with_vl_phone_total": sum(((item["evidence"].get("summary") or {}).get("phones_found") or 0) for item in results),
        "without_vl_email_total": sum(((item["evidence"].get("without_vl") or {}).get("emails_found") or 0) for item in results),
        "without_vl_phone_total": sum(((item["evidence"].get("without_vl") or {}).get("phones_found") or 0) for item in results),
    }
    payload = {"aggregate": aggregate, "comparisons": results}

    if args.out:
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())