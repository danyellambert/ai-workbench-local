#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def resolve_project_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


from statistics import mean

from pypdf import PdfReader

SECTION_PATTERNS = [
    r"\bexperience\b", r"\beducation\b", r"\bskills?\b", r"\bprojects?\b",
    r"\bsummary\b", r"\bprofile\b", r"\bcertifications?\b", r"\blanguages?\b",
    r"\bwork history\b", r"\bemployment\b", r"\bobjective\b",
    r"\bachievements?\b", r"\binterests?\b", r"\bpublications?\b",
]

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\-\s().]{7,}\d)")
URL_RE = re.compile(r"(https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+)", re.I)
BULLET_RE = re.compile(r"(^|\n)\s*([•\-–*]|[0-9]+\.)\s+", re.M)


@dataclass
class ResumeFeatures:
    relative_path: str
    top_folder: str
    file_size_bytes: int
    page_count: int
    extracted_chars: int
    chars_per_page: float
    line_count: int
    nonempty_line_count: int
    bullet_count: int
    email_count: int
    phone_count: int
    url_count: int
    section_hits: int
    extraction_ratio: float
    likely_scanned: bool
    complexity_score: float
    bucket: str


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def kaggle_download(dataset: str, workdir: Path) -> Path:
    safe_mkdir(workdir)
    out_zip = workdir / "dataset.zip"
    if out_zip.exists():
        return out_zip
    run_command(["kaggle", "datasets", "download", "-d", dataset, "-p", str(workdir)])
    zips = sorted(workdir.glob("*.zip"))
    if not zips:
        raise FileNotFoundError("No zip found after Kaggle download.")
    latest = max(zips, key=lambda p: p.stat().st_mtime)
    if latest != out_zip:
        latest.rename(out_zip)
    return out_zip


def unzip_dataset(zip_path: Path, target_dir: Path) -> Path:
    safe_mkdir(target_dir)
    marker = target_dir / ".unzipped_ok"
    if marker.exists():
        return target_dir
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)
    marker.write_text("ok", encoding="utf-8")
    return target_dir


def find_pdfs(root: Path) -> list[Path]:
    return sorted([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf"])


def extract_text_from_pdf(pdf_path: Path) -> tuple[str, int]:
    try:
        reader = PdfReader(str(pdf_path), strict=False)
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
        return "\n".join(parts), len(reader.pages)
    except Exception:
        return "", 0


def count_section_hits(text: str) -> int:
    lowered = text.lower()
    return sum(1 for pattern in SECTION_PATTERNS if re.search(pattern, lowered))


def compute_complexity_score(
    page_count: int,
    extracted_chars: int,
    chars_per_page: float,
    bullet_count: int,
    section_hits: int,
    email_count: int,
    phone_count: int,
    url_count: int,
    extraction_ratio: float,
) -> float:
    score = 0.0

    if page_count >= 2:
        score += 0.5
    if page_count >= 3:
        score += 0.75

    if extracted_chars > 2500:
        score += 0.5
    if extracted_chars > 5000:
        score += 0.75
    if extracted_chars > 9000:
        score += 0.75

    if bullet_count > 8:
        score += 0.5
    if bullet_count > 20:
        score += 0.5

    if section_hits >= 3:
        score += 0.5
    if section_hits >= 5:
        score += 0.75
    if section_hits >= 7:
        score += 0.5

    if (email_count + phone_count + url_count) >= 2:
        score += 0.25
    if (email_count + phone_count + url_count) >= 4:
        score += 0.25

    if chars_per_page < 500:
        score += 0.75
    elif chars_per_page < 900:
        score += 0.25

    if extraction_ratio < 0.002:
        score += 0.5
    elif extraction_ratio < 0.004:
        score += 0.25

    return round(score, 2)


def bucket_from_features(extracted_chars: int, chars_per_page: float, extraction_ratio: float, score: float) -> tuple[str, bool]:
    likely_scanned = extracted_chars == 0 or chars_per_page < 120 or extraction_ratio < 0.0008
    if likely_scanned:
        return "ocr_needed", True
    if score < 1.75:
        return "simple", False
    if score < 3.75:
        return "medium", False
    return "hard", False


def analyze_pdf(pdf_path: Path, root: Path) -> ResumeFeatures:
    text, page_count = extract_text_from_pdf(pdf_path)
    extracted_chars = len(text)
    chars_per_page = round(extracted_chars / page_count, 2) if page_count else 0.0
    lines = text.splitlines()
    nonempty = [line for line in lines if line.strip()]
    bullet_count = len(BULLET_RE.findall(text))
    email_count = len(EMAIL_RE.findall(text))
    phone_count = len(PHONE_RE.findall(text))
    url_count = len(URL_RE.findall(text))
    section_hits = count_section_hits(text)

    file_size_bytes = pdf_path.stat().st_size
    extraction_ratio = round(extracted_chars / max(file_size_bytes, 1), 6)
    score = compute_complexity_score(
        page_count=page_count,
        extracted_chars=extracted_chars,
        chars_per_page=chars_per_page,
        bullet_count=bullet_count,
        section_hits=section_hits,
        email_count=email_count,
        phone_count=phone_count,
        url_count=url_count,
        extraction_ratio=extraction_ratio,
    )
    bucket, likely_scanned = bucket_from_features(extracted_chars, chars_per_page, extraction_ratio, score)

    rel = pdf_path.relative_to(root)
    parts = rel.parts
    top_folder = parts[0] if len(parts) > 1 else "root"

    return ResumeFeatures(
        relative_path=str(rel),
        top_folder=top_folder,
        file_size_bytes=file_size_bytes,
        page_count=page_count,
        extracted_chars=extracted_chars,
        chars_per_page=chars_per_page,
        line_count=len(lines),
        nonempty_line_count=len(nonempty),
        bullet_count=bullet_count,
        email_count=email_count,
        phone_count=phone_count,
        url_count=url_count,
        section_hits=section_hits,
        extraction_ratio=extraction_ratio,
        likely_scanned=likely_scanned,
        complexity_score=score,
        bucket=bucket,
    )


def write_csv(path: Path, rows: list[ResumeFeatures]) -> None:
    safe_mkdir(path.parent)
    if rows:
        fieldnames = list(asdict(rows[0]).keys())
    else:
        fieldnames = list(asdict(ResumeFeatures("", "", 0, 0, 0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0.0, False, 0.0, "")).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def copy_bucket_files(rows: list[ResumeFeatures], src_root: Path, out_root: Path) -> None:
    for row in rows:
        src = src_root / row.relative_path
        dst = out_root / row.bucket / row.relative_path
        safe_mkdir(dst.parent)
        if not dst.exists():
            shutil.copy2(src, dst)


def select_balanced_sample(rows: list[ResumeFeatures], sample_per_bucket: int) -> list[ResumeFeatures]:
    buckets = {"simple": [], "medium": [], "hard": [], "ocr_needed": []}
    for row in rows:
        buckets[row.bucket].append(row)

    selected = []
    targets = {"simple": 1.0, "medium": 2.7, "hard": 4.8, "ocr_needed": 0.0}
    for name, bucket_rows in buckets.items():
        if name == "ocr_needed":
            bucket_rows = sorted(bucket_rows, key=lambda r: (r.extracted_chars, r.relative_path))
        else:
            bucket_rows = sorted(
                bucket_rows,
                key=lambda r: (
                    abs(r.complexity_score - targets[name]),
                    -r.section_hits,
                    -r.extracted_chars,
                    r.relative_path,
                ),
            )
        selected.extend(bucket_rows[:sample_per_bucket])
    return selected


def save_summary(path: Path, rows: list[ResumeFeatures], sample_rows: list[ResumeFeatures]) -> None:
    by_folder_and_bucket: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        by_folder_and_bucket[row.top_folder][row.bucket] += 1

    data = {
        "total_pdfs": len(rows),
        "bucket_counts": dict(Counter(r.bucket for r in rows)),
        "avg_pages": round(mean([r.page_count for r in rows]), 2) if rows else 0.0,
        "avg_extracted_chars": round(mean([r.extracted_chars for r in rows]), 2) if rows else 0.0,
        "sample_size": len(sample_rows),
        "sample_bucket_counts": dict(Counter(r.bucket for r in sample_rows)),
        "top_folder_bucket_counts": {folder: dict(counter) for folder, counter in by_folder_and_bucket.items()},
    }
    safe_mkdir(path.parent)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split a resume PDF dataset into simple/medium/hard/ocr_needed buckets.")
    parser.add_argument("--dataset", default="hadikp/resume-data-pdf")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--workdir", type=Path, default=PROJECT_ROOT / "data/external/resume_data_pdf")
    parser.add_argument("--input-dir", type=Path, default=None)
    parser.add_argument("--outdir", type=Path, default=PROJECT_ROOT / "data/eval/resume_split_v2")
    parser.add_argument("--sample-per-bucket", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    workdir = resolve_project_path(args.workdir)
    input_dir = resolve_project_path(args.input_dir)
    outdir = resolve_project_path(args.outdir)

    if args.download:
        zip_path = kaggle_download(args.dataset, workdir)
        input_root = unzip_dataset(zip_path, workdir / "unzipped")
    elif input_dir:
        input_root = input_dir
    else:
        print("ERROR: use either --download or --input-dir", file=sys.stderr)
        return 2

    if not input_root.exists():
        print(f"ERROR: input directory does not exist: {input_root}", file=sys.stderr)
        return 2

    pdfs = find_pdfs(input_root)
    if not pdfs:
        print(f"ERROR: no PDF files found under {input_root}", file=sys.stderr)
        return 2

    print(f"Found {len(pdfs)} PDF files")

    rows = []
    for idx, pdf_path in enumerate(pdfs, start=1):
        if idx % 50 == 0 or idx == 1 or idx == len(pdfs):
            print(f"Analyzing {idx}/{len(pdfs)}: {pdf_path.name}")
        rows.append(analyze_pdf(pdf_path, input_root))

    bucket_order = {"simple": 0, "medium": 1, "hard": 2, "ocr_needed": 3}
    rows = sorted(rows, key=lambda r: (bucket_order.get(r.bucket, 99), r.top_folder, r.complexity_score, r.relative_path))

    safe_mkdir(outdir)

    all_csv = outdir / "resume_features_all.csv"
    write_csv(all_csv, rows)

    sample_rows = select_balanced_sample(rows, args.sample_per_bucket)
    sample_csv = outdir / "resume_features_sample.csv"
    write_csv(sample_csv, sample_rows)

    copy_bucket_files(rows, input_root, outdir / "all_buckets")
    copy_bucket_files(sample_rows, input_root, outdir / "sample_buckets")

    save_summary(outdir / "summary.json", rows, sample_rows)

    print("Done.")
    print(f"All features CSV:    {all_csv}")
    print(f"Sample features CSV: {sample_csv}")
    print(f"Summary JSON:        {outdir / 'summary.json'}")
    print(f"All buckets dir:     {outdir / 'all_buckets'}")
    print(f"Sample buckets dir:  {outdir / 'sample_buckets'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
