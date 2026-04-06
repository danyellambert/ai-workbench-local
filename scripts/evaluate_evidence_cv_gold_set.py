from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_rag_settings
from src.evals.phase8_thresholds import EVIDENCE_CV_GOLD_THRESHOLDS
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.evidence_cv.pipeline.runner import run_cv_pipeline_from_bytes
from src.storage.runtime_paths import get_phase8_eval_db_path
from src.storage.phase8_eval_store import append_eval_run
from src.rag.loaders import _extract_pdf_text, _extract_pdf_text_with_evidence_pipeline


EMAIL_PATTERN = __import__("re").compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", __import__("re").I)
EVAL_DB_PATH = get_phase8_eval_db_path(ROOT_DIR)


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
    matched = False
    if predicted_norm is not None and expected_norm is not None:
        matched = predicted_norm == expected_norm or expected_norm in predicted_norm or predicted_norm in expected_norm
    tp = int(matched)
    fp = int(predicted_norm is not None and not matched)
    fn = int(expected_norm is not None and not matched)
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


def _f1_score(field_score: dict[str, object]) -> float:
    precision = float(field_score.get("precision") or 0.0)
    recall = float(field_score.get("recall") or 0.0)
    if precision + recall <= 0:
        return 0.0
    return round((2 * precision * recall) / (precision + recall), 4)


def _build_eval_run_for_variant(
    *,
    file_name: str,
    gold_set_path: str,
    variant: str,
    variant_scores: dict[str, dict[str, object]],
) -> dict[str, object]:
    email_f1 = _f1_score(variant_scores.get("emails") or {})
    phone_f1 = _f1_score(variant_scores.get("phones") or {})
    name_f1 = _f1_score(variant_scores.get("name") or {})
    location_f1 = _f1_score(variant_scores.get("location") or {})
    avg_f1 = round((email_f1 + phone_f1 + name_f1 + location_f1) / 4, 4)
    score = round(avg_f1 * 4, 3)

    status = "PASS"
    if avg_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("warn_min_avg_f1") or 0.65):
        status = "FAIL"
    elif avg_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("pass_min_avg_f1") or 0.9):
        status = "WARN"

    reasons: list[str] = []
    if email_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("email_f1_target") or 0.9):
        reasons.append(f"email_f1_below_target:{email_f1:.3f}")
    if phone_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("phone_f1_target") or 0.9):
        reasons.append(f"phone_f1_below_target:{phone_f1:.3f}")
    if name_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("name_f1_target") or 1.0):
        reasons.append(f"name_match_incomplete:{name_f1:.3f}")
    if location_f1 < float(EVIDENCE_CV_GOLD_THRESHOLDS.get("location_f1_target") or 1.0):
        reasons.append(f"location_match_incomplete:{location_f1:.3f}")

    return {
        "created_at": datetime.now().isoformat(),
        "suite_name": "evidence_cv_gold_eval",
        "task_type": "cv_contacts",
        "case_name": file_name,
        "provider": "evidence_cv",
        "model": variant,
        "status": status,
        "score": score,
        "max_score": 4,
        "metrics": {
            "avg_f1": avg_f1,
            "email_f1": email_f1,
            "phone_f1": phone_f1,
            "name_f1": name_f1,
            "location_f1": location_f1,
            "emails_precision": variant_scores.get("emails", {}).get("precision"),
            "emails_recall": variant_scores.get("emails", {}).get("recall"),
            "phones_precision": variant_scores.get("phones", {}).get("precision"),
            "phones_recall": variant_scores.get("phones", {}).get("recall"),
        },
        "reasons": reasons,
        "metadata": {
            "gold_set": gold_set_path,
            "variant": variant,
            "thresholds": EVIDENCE_CV_GOLD_THRESHOLDS,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate evidence CV extraction against mini gold set")
    parser.add_argument("--gold-set", default="phase5_eval/fixtures/evidence_cv_mini_gold_set.json")
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

        for variant, variant_scores in scores.items():
            append_eval_run(
                EVAL_DB_PATH,
                _build_eval_run_for_variant(
                    file_name=file_path.name,
                    gold_set_path=args.gold_set,
                    variant=variant,
                    variant_scores=variant_scores,
                ),
            )

    for variant, fields in aggregate.items():
        for field_name, counts in fields.items():
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            counts["precision"] = round(tp / (tp + fp), 4) if tp + fp else 1.0
            counts["recall"] = round(tp / (tp + fn), 4) if tp + fn else 1.0

    payload = {
        "gold_set": args.gold_set,
        "eval_store_path": str(EVAL_DB_PATH),
        "aggregate": aggregate,
        "per_file": per_file,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())