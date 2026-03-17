#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.structured.envelope import TaskExecutionRequest  # noqa: E402
from src.structured.service import structured_service  # noqa: E402


def norm_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def similarity(a: str | None, b: str | None) -> float:
    a_n = norm_text(a)
    b_n = norm_text(b)
    if not a_n and not b_n:
        return 1.0
    if not a_n or not b_n:
        return 0.0
    return SequenceMatcher(None, a_n, b_n).ratio()


def list_similarity(pred: Iterable[str], gt: Iterable[str]) -> float:
    pred_list = [norm_text(x) for x in pred if norm_text(x)]
    gt_list = [norm_text(x) for x in gt if norm_text(x)]
    if not pred_list and not gt_list:
        return 1.0
    if not pred_list or not gt_list:
        return 0.0
    hits = 0
    remaining = gt_list.copy()
    for item in pred_list:
        for j, gt_item in enumerate(remaining):
            if item == gt_item or item in gt_item or gt_item in item:
                hits += 1
                remaining.pop(j)
                break
    precision = hits / max(len(pred_list), 1)
    recall = hits / max(len(gt_list), 1)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path), strict=False)
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
        return "\n".join(parts)
    except Exception:
        return ""


def flatten_education(gt: dict[str, Any]) -> list[str]:
    education = gt.get("education", [])
    return [str(x) for x in education if str(x).strip()]


def flatten_experience_titles(gt: dict[str, Any]) -> list[str]:
    titles = []
    for item in gt.get("experience", []):
        if isinstance(item, dict):
            title = item.get("title")
            if title:
                titles.append(str(title))
    return titles


@dataclass
class ResumeEvalResult:
    pdf_file: str
    json_file: str
    layout_type: str
    difficulty: str
    text_extractable_gt: bool
    extracted_chars: int
    task_success: bool
    overall_score: float
    status: str
    full_name_score: float
    email_score: float
    location_score: float
    skills_score: float
    languages_score: float
    education_score: float
    experience_titles_score: float
    notes: str


def evaluate_one(pdf_path: Path, json_path: Path, model: str | None, temperature: float) -> ResumeEvalResult:
    gt = json.loads(json_path.read_text(encoding="utf-8"))
    text = extract_pdf_text(pdf_path)
    try:
        request = TaskExecutionRequest(
            task_type="cv_analysis",
            input_text=f"analyze this resume\n\n{text}" if text.strip() else "",
            model=model,
            temperature=temperature,
            use_document_context=False,
            context_strategy="document_scan",
        )
    except Exception:
        request = TaskExecutionRequest(
            task_name="cv_analysis",
            input_text=f"analyze this resume\n\n{text}" if text.strip() else "",
            model=model,
            temperature=temperature,
            use_document_context=False,
            context_strategy="document_scan",
        )
    result = structured_service.execute_task(request)

    layout_type = gt.get("layout_type", "unknown")
    difficulty = gt.get("difficulty", "unknown")
    text_extractable_gt = bool(gt.get("text_extractable", True))
    extracted_chars = len(text)

    if not result.success or result.validated_output is None:
        notes = result.validation_error or result.parsing_error or "task execution failed"
        return ResumeEvalResult(
            pdf_file=pdf_path.name,
            json_file=json_path.name,
            layout_type=layout_type,
            difficulty=difficulty,
            text_extractable_gt=text_extractable_gt,
            extracted_chars=extracted_chars,
            task_success=False,
            overall_score=0.0,
            status="FAIL",
            full_name_score=0.0,
            email_score=0.0,
            location_score=0.0,
            skills_score=0.0,
            languages_score=0.0,
            education_score=0.0,
            experience_titles_score=0.0,
            notes=notes,
        )

    payload = result.validated_output.model_dump(mode="json")

    gt_name = (((gt.get("full_name")) or "").strip())
    pred_info = payload.get("personal_info") or {}
    pred_name = pred_info.get("full_name")
    pred_email = pred_info.get("email")
    pred_location = pred_info.get("location")

    full_name_score = similarity(pred_name, gt_name)
    email_score = similarity(pred_email, gt.get("email"))
    location_score = similarity(pred_location, gt.get("location"))

    skills_score = list_similarity(payload.get("skills", []), gt.get("skills", []))
    languages_score = list_similarity(payload.get("languages", []), gt.get("languages", []))
    education_score = list_similarity(
        [item.get("text") if isinstance(item, dict) else str(item) for sec in payload.get("sections", []) if (sec.get("section_type") == "education" or (sec.get("title") or "").lower().startswith("education")) for item in sec.get("content", [])],
        flatten_education(gt),
    )
    experience_titles_score = list_similarity(
        [sec.get("title", "") for sec in payload.get("sections", []) if sec.get("section_type") == "experience"] +
        [item.get("details", {}).get("title", "") for sec in payload.get("sections", []) for item in sec.get("content", []) if isinstance(item, dict)],
        flatten_experience_titles(gt),
    )

    # OCR-like layouts should not be penalized as harshly on semantic extraction if no text is extractable.
    if extracted_chars == 0 and not text_extractable_gt:
        base_weights = [0.10, 0.05, 0.05, 0.20, 0.20, 0.20, 0.20]
    else:
        base_weights = [0.18, 0.12, 0.10, 0.18, 0.12, 0.15, 0.15]

    scores = [
        full_name_score,
        email_score,
        location_score,
        skills_score,
        languages_score,
        education_score,
        experience_titles_score,
    ]
    overall = sum(w * s for w, s in zip(base_weights, scores))

    if overall >= 0.75:
        status = "PASS"
    elif overall >= 0.45:
        status = "WARN"
    else:
        status = "FAIL"

    notes_parts = []
    if extracted_chars == 0:
        notes_parts.append("no extractable PDF text")
    if layout_type == "scan_like_image_pdf":
        notes_parts.append("scan-like layout")
    if full_name_score < 0.5:
        notes_parts.append("weak full_name match")
    if skills_score < 0.4:
        notes_parts.append("weak skills match")

    return ResumeEvalResult(
        pdf_file=pdf_path.name,
        json_file=json_path.name,
        layout_type=layout_type,
        difficulty=difficulty,
        text_extractable_gt=text_extractable_gt,
        extracted_chars=extracted_chars,
        task_success=True,
        overall_score=round(overall, 4),
        status=status,
        full_name_score=round(full_name_score, 4),
        email_score=round(email_score, 4),
        location_score=round(location_score, 4),
        skills_score=round(skills_score, 4),
        languages_score=round(languages_score, 4),
        education_score=round(education_score, 4),
        experience_titles_score=round(experience_titles_score, 4),
        notes="; ".join(notes_parts),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark cv_analysis using synthetic resume PDF/JSON pairs.")
    parser.add_argument("--pdf-dir", type=Path, required=True, help="Directory containing generated resume PDFs.")
    parser.add_argument("--json-dir", type=Path, required=True, help="Directory containing matching JSON ground truth.")
    parser.add_argument("--outdir", type=Path, default=Path("phase5_eval/resume_benchmark"), help="Output directory for reports.")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of files for quick runs.")
    parser.add_argument("--model", type=str, default=None, help="Optional model override.")
    parser.add_argument("--temperature", type=float, default=0.1)
    args = parser.parse_args()

    pdfs = sorted(args.pdf_dir.glob("*.pdf"))
    if args.limit > 0:
        pdfs = pdfs[: args.limit]

    if not pdfs:
        print(f"ERROR: no PDFs found under {args.pdf_dir}", file=sys.stderr)
        return 2

    results: list[ResumeEvalResult] = []
    missing_pairs: list[str] = []

    for idx, pdf_path in enumerate(pdfs, start=1):
        json_path = args.json_dir / f"{pdf_path.stem}.json"
        if not json_path.exists():
            missing_pairs.append(pdf_path.name)
            continue
        print(f"Evaluating {idx}/{len(pdfs)}: {pdf_path.name}")
        results.append(evaluate_one(pdf_path, json_path, args.model, args.temperature))

    args.outdir.mkdir(parents=True, exist_ok=True)

    csv_path = args.outdir / "resume_benchmark_results.csv"
    json_path = args.outdir / "resume_benchmark_results.json"
    summary_path = args.outdir / "resume_benchmark_summary.json"

    fieldnames = list(asdict(results[0]).keys()) if results else list(ResumeEvalResult(
        pdf_file="", json_file="", layout_type="", difficulty="", text_extractable_gt=True, extracted_chars=0,
        task_success=False, overall_score=0.0, status="", full_name_score=0.0, email_score=0.0,
        location_score=0.0, skills_score=0.0, languages_score=0.0, education_score=0.0,
        experience_titles_score=0.0, notes=""
    ).__dict__.keys())

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(asdict(row))

    json_path.write_text(json.dumps([asdict(r) for r in results], indent=2, ensure_ascii=False), encoding="utf-8")

    by_status: dict[str, int] = {}
    by_layout: dict[str, dict[str, int]] = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_layout.setdefault(r.layout_type, {"PASS": 0, "WARN": 0, "FAIL": 0})
        by_layout[r.layout_type][r.status] += 1

    summary = {
        "evaluated_pairs": len(results),
        "missing_pairs": missing_pairs,
        "status_counts": by_status,
        "layout_status_counts": by_layout,
        "avg_overall_score": round(sum(r.overall_score for r in results) / len(results), 4) if results else 0.0,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("Benchmark complete.")
    print(f"CSV results:     {csv_path}")
    print(f"JSON results:    {json_path}")
    print(f"Summary:         {summary_path}")
    print(f"Status counts:   {by_status}")
    if missing_pairs:
        print(f"Missing pairs:   {len(missing_pairs)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
