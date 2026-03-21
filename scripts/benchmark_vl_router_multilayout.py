from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_rag_settings
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.evidence_cv.pipeline.runner import run_cv_pipeline_from_bytes
from src.rag.loaders import _extract_pdf_text, _extract_pdf_text_with_evidence_pipeline


EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def _normalized_contacts(items: list[str]) -> set[str]:
    normalized = set()
    for item in items:
        text = str(item or "").strip().lower()
        if not text:
            continue
        if "@" in text:
            if not EMAIL_RE.match(text) or text.endswith(".co"):
                continue
            normalized.add(text)
            continue
        digits = re.sub(r"\D", "", text)
        if len(digits) < 8 or len(digits) > 15:
            continue
        normalized.add(digits)
    return normalized


def _run_evidence_no_vl(file_bytes: bytes):
    rag = get_rag_settings()
    config = build_evidence_config_from_rag_settings(rag)
    config = config.__class__(**{**config.__dict__, "ocr_backend": "ocrmypdf", "enable_vl": False})
    start = time.perf_counter()
    result = run_cv_pipeline_from_bytes(file_bytes, ".pdf", config)
    elapsed = time.perf_counter() - start
    return result, elapsed


def benchmark_file(pdf_path: Path) -> dict[str, object]:
    rag = get_rag_settings()
    file_bytes = pdf_path.read_bytes()

    start = time.perf_counter()
    _, legacy_meta = _extract_pdf_text(file_bytes, rag)
    legacy_elapsed = time.perf_counter() - start

    evidence_no_vl, no_vl_elapsed = _run_evidence_no_vl(file_bytes)

    start = time.perf_counter()
    _, evidence_meta = _extract_pdf_text_with_evidence_pipeline(file_bytes, pdf_path.name, rag)
    evidence_elapsed = time.perf_counter() - start

    vl_runtime = (evidence_meta.get("vl_runtime") or {})
    router_meta = evidence_meta.get("vl_router") or {}
    evidence_summary = evidence_meta.get("evidence_summary") or {}

    before_contacts = _normalized_contacts([item.value for item in evidence_no_vl.resume.emails if item.value] + [item.value for item in evidence_no_vl.resume.phones if item.value])
    after_contacts = _normalized_contacts((evidence_summary.get("emails") or []) + (evidence_summary.get("phones") or []))
    name_gain = evidence_no_vl.resume.name.status != "confirmed" and evidence_summary.get("name_status") == "confirmed"
    location_gain = evidence_no_vl.resume.location.status != "confirmed" and evidence_summary.get("location_status") == "confirmed"
    review_only = evidence_summary.get("name_status") == "visual_candidate" or evidence_summary.get("location_status") == "visual_candidate"
    added_noise = len(after_contacts - before_contacts) > 0 and not (name_gain or location_gain)
    semantic_false_positive = (evidence_summary.get("name_value") or "").strip().lower() in {"present", "remote"} or (evidence_summary.get("location_value") or "").strip().lower() in {"remote", "present"}

    if semantic_false_positive:
        vl_value = "vl_called_and_false_positive"
    elif name_gain or location_gain:
        vl_value = "vl_called_and_added_value"
    elif after_contacts - before_contacts:
        vl_value = "vl_called_and_added_partial_value"
    elif review_only:
        vl_value = "vl_called_but_review_only"
    elif added_noise:
        vl_value = "vl_called_and_added_noise"
    elif (vl_runtime.get("regions_attempted") or 0) > 0:
        vl_value = "vl_called_but_no_gain"
    else:
        vl_value = "vl_skipped_and_ocr_was_sufficient"

    return {
        "file": str(pdf_path),
        "legacy": {"elapsed_seconds": round(legacy_elapsed, 4), "strategy": legacy_meta.get("strategy"), "source_type": legacy_meta.get("source_type")},
        "evidence_no_vl": {
            "elapsed_seconds": round(no_vl_elapsed, 4),
            "source_type": evidence_no_vl.source_type,
            "emails_found": len(evidence_no_vl.resume.emails),
            "phones_found": len(evidence_no_vl.resume.phones),
            "name_status": evidence_no_vl.resume.name.status,
            "location_status": evidence_no_vl.resume.location.status,
        },
        "evidence_router": {
            "elapsed_seconds": round(evidence_elapsed, 4),
            "source_type": evidence_meta.get("source_type"),
            "evidence_summary": evidence_summary,
            "vl_runtime": vl_runtime,
            "vl_router": router_meta,
        },
        "vl_value_category": vl_value,
        "semantic_diagnosis": {
            "name_value": evidence_summary.get("name_value"),
            "location_value": evidence_summary.get("location_value"),
            "semantic_false_positive": semantic_false_positive,
            "name_gain": name_gain,
            "location_gain": location_gain,
            "review_only": review_only,
            "added_noise": added_noise,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark OCR-first / VL-on-demand router on multilayout resume corpus")
    parser.add_argument("--pdf-dir", default="data/synthetic/resumes_multilayout/pdf")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", default="phase5_eval/reports/evidence_cv_multilayout_router_benchmark.json")
    args = parser.parse_args()

    pdf_paths = sorted(Path(args.pdf_dir).glob("*.pdf"))
    if args.limit and args.limit > 0:
        pdf_paths = pdf_paths[: args.limit]

    per_file = [benchmark_file(path) for path in pdf_paths]
    reason_counter = Counter()
    source_type_counter = Counter()
    value_counter = Counter()
    vl_called = 0
    vl_skipped = 0

    for item in per_file:
        router = ((item.get("evidence_router") or {}).get("vl_router") or {})
        runtime = ((item.get("evidence_router") or {}).get("vl_runtime") or {})
        source_type_counter[(item.get("evidence_router") or {}).get("source_type") or "unknown"] += 1
        value_counter[item.get("vl_value_category") or "unknown"] += 1
        for reason in router.get("reasons", []):
            reason_counter[reason] += 1
        if router.get("enabled"):
            vl_called += 1
        else:
            vl_skipped += 1

    payload = {
        "aggregate": {
            "files_processed": len(per_file),
            "vl_called": vl_called,
            "vl_skipped": vl_skipped,
            "reasons_most_frequent": reason_counter.most_common(),
            "document_type_distribution": dict(source_type_counter),
            "vl_value_categories": dict(value_counter),
        },
        "per_file": per_file,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())