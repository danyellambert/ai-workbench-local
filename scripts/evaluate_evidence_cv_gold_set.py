from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_rag_settings
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.evidence_cv.pipeline.runner import run_cv_pipeline_from_bytes
from src.rag.loaders import _extract_pdf_text, _extract_pdf_text_with_evidence_pipeline


EMAIL_PATTERN = __import__("re").compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", __import__("re").I)


def _normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 8 or len(digits) > 15:
        return ""
    if digits.startswith("55") and len(digits) > 11:
        return digits
    return digits


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    return normalized if EMAIL_PATTERN.match(normalized) else ""


def _normalize_email_list(values: list[str]) -> list[str]:
    return sorted({item for item in (_normalize_email(value) for value in values) if item})


def _normalize_phone_list(values: list[str]) -> list[str]:
    return sorted({item for item in (_normalize_phone(value) for value in values) if item})


def _extract_legacy_contacts(file_bytes: bytes) -> dict[str, object]:
    rag = get_rag_settings()
    text, _ = _extract_pdf_text(file_bytes, rag)
    import re

    emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    phones = re.findall(r"\+?\d[\d\s().-]{7,}\d", text)
    return {
        "name": None,
        "location": None,
        "emails": _normalize_email_list(emails),
        "phones": _normalize_phone_list(phones),
        "name_status": "not_found",
        "location_status": "not_found",
    }


def _extract_evidence_no_vl(file_bytes: bytes) -> dict[str, object]:
    rag = get_rag_settings()
    config = build_evidence_config_from_rag_settings(rag)
    config = config.__class__(**{**config.__dict__, "ocr_backend": "ocrmypdf"})
    config = config.__class__(**{**config.__dict__, "enable_vl": False})
    result = run_cv_pipeline_from_bytes(file_bytes, ".pdf", config)
    return {
        "name": result.resume.name.value,
        "location": result.resume.location.value,
        "emails": _normalize_email_list([item.value for item in result.resume.emails if item.value]),
        "phones": _normalize_phone_list([item.value for item in result.resume.phones if item.value]),
        "name_status": result.resume.name.status,
        "location_status": result.resume.location.status,
    }


def _extract_evidence_with_vl(file_bytes: bytes, filename: str) -> dict[str, object]:
    rag = get_rag_settings()
    _, metadata = _extract_pdf_text_with_evidence_pipeline(file_bytes, filename, rag)
    summary = metadata.get("evidence_summary") or {}
    return {
        "name": summary.get("name_value"),
        "location": summary.get("location_value"),
        "emails": _normalize_email_list(summary.get("emails", [])),
        "phones": _normalize_phone_list(summary.get("phones", [])),
        "name_status": summary.get("name_status", "not_found"),
        "location_status": summary.get("location_status", "not_found"),
    }


def _score_list(predicted: list[str], expected: list[str]) -> dict[str, float | int]:
    pred = set(predicted)
    gold = set(expected)
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "predicted_total": len(pred),
        "gold_total": len(gold),
        "true_positives": sorted(pred & gold),
        "false_positives": sorted(pred - gold),
        "false_negatives": sorted(gold - pred),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def _score_single(predicted: str | None, expected: str | None, status: str) -> dict[str, object]:
    predicted_norm = (predicted or "").strip().lower() or None
    expected_norm = (expected or "").strip().lower() or None
    tp = int(predicted_norm is not None and predicted_norm == expected_norm)
    fp = int(predicted_norm is not None and predicted_norm != expected_norm)
    fn = int(expected_norm is not None and predicted_norm != expected_norm)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "predicted": predicted,
        "expected": expected,
        "status": status,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate evidence CV extraction against mini gold set")
    parser.add_argument("--gold-set", default="phase5_eval/reports/evidence_cv_mini_gold_set.json")
    parser.add_argument("--out", default="phase5_eval/reports/evidence_cv_eval_metrics.json")
    args = parser.parse_args()

    gold_payload = json.loads(Path(args.gold_set).read_text(encoding="utf-8"))
    per_file: list[dict[str, object]] = []
    aggregate = {
        "legacy": {"emails": {"tp": 0, "fp": 0, "fn": 0, "predicted_total": 0, "gold_total": 0}, "phones": {"tp": 0, "fp": 0, "fn": 0, "predicted_total": 0, "gold_total": 0}, "name": {"tp": 0, "fp": 0, "fn": 0}, "location": {"tp": 0, "fp": 0, "fn": 0}},
        "evidence_no_vl": {"emails": {"tp": 0, "fp": 0, "fn": 0, "predicted_total": 0, "gold_total": 0}, "phones": {"tp": 0, "fp": 0, "fn": 0, "predicted_total": 0, "gold_total": 0}, "name": {"tp": 0, "fp": 0, "fn": 0}, "location": {"tp": 0, "fp": 0, "fn": 0}},
        "evidence_with_vl": {"emails": {"tp": 0, "fp": 0, "fn": 0, "predicted_total": 0, "gold_total": 0}, "phones": {"tp": 0, "fp": 0, "fn": 0, "predicted_total": 0, "gold_total": 0}, "name": {"tp": 0, "fp": 0, "fn": 0}, "location": {"tp": 0, "fp": 0, "fn": 0}},
    }

    for document in gold_payload.get("documents", []):
        file_path = Path(document["file"])
        file_bytes = file_path.read_bytes()
        legacy = _extract_legacy_contacts(file_bytes)
        no_vl = _extract_evidence_no_vl(file_bytes)
        with_vl = _extract_evidence_with_vl(file_bytes, file_path.name)

        scores = {
            "legacy": {
                "emails": _score_list(legacy["emails"], _normalize_email_list(document.get("emails", []))),
                "phones": _score_list(legacy["phones"], _normalize_phone_list(document.get("phones", []))),
                "name": _score_single(legacy["name"], document.get("name"), legacy["name_status"]),
                "location": _score_single(legacy["location"], document.get("location"), legacy["location_status"]),
            },
            "evidence_no_vl": {
                "emails": _score_list(no_vl["emails"], _normalize_email_list(document.get("emails", []))),
                "phones": _score_list(no_vl["phones"], _normalize_phone_list(document.get("phones", []))),
                "name": _score_single(no_vl["name"], document.get("name"), no_vl["name_status"]),
                "location": _score_single(no_vl["location"], document.get("location"), no_vl["location_status"]),
            },
            "evidence_with_vl": {
                "emails": _score_list(with_vl["emails"], _normalize_email_list(document.get("emails", []))),
                "phones": _score_list(with_vl["phones"], _normalize_phone_list(document.get("phones", []))),
                "name": _score_single(with_vl["name"], document.get("name"), with_vl["name_status"]),
                "location": _score_single(with_vl["location"], document.get("location"), with_vl["location_status"]),
            },
        }

        for variant, fields in scores.items():
            for field_name, field_score in fields.items():
                for metric in ("tp", "fp", "fn", "predicted_total", "gold_total"):
                    if metric not in field_score:
                        continue
                    aggregate[variant][field_name][metric] += int(field_score[metric])

        per_file.append({
            "file": document["file"],
            "gold": {
                **document,
                "emails_normalized": _normalize_email_list(document.get("emails", [])),
                "phones_normalized": _normalize_phone_list(document.get("phones", [])),
            },
            "predictions": {
                "legacy": legacy,
                "evidence_no_vl": no_vl,
                "evidence_with_vl": with_vl,
            },
            "scores": scores,
        })

    for variant, fields in aggregate.items():
        for field_name, counts in fields.items():
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            counts["precision"] = round(tp / (tp + fp), 4) if tp + fp else 1.0
            counts["recall"] = round(tp / (tp + fn), 4) if tp + fn else 1.0

    payload = {"gold_set": args.gold_set, "aggregate": aggregate, "per_file": per_file}
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())