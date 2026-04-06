#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def resolve_project_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()



from pypdf import PdfReader

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(\+?\d[\d\-\s().]{7,}\d)")
URL_RE = re.compile(r"(https?://\S+|www\.\S+|linkedin\.com/\S+|github\.com/\S+)", re.I)

SECTION_HINTS = [
    "experience", "education", "skills", "projects", "summary", "profile",
    "languages", "certifications", "interests", "employment", "work history"
]

SKILL_CANDIDATES = [
    "Python", "SQL", "Java", "C++", "JavaScript", "TypeScript", "React", "Node.js",
    "FastAPI", "Flask", "Django", "Docker", "Kubernetes", "Git", "Linux",
    "Pandas", "NumPy", "Scikit-learn", "PyTorch", "TensorFlow", "Power BI",
    "Tableau", "Excel", "PowerPoint", "MATLAB", "Aspen Plus", "Powerfactory",
    "PSCAD", "SIMULINK", "PostgreSQL", "MongoDB", "AWS", "GCP", "Azure", "R",
]

DEGREE_HINTS = [
    "Bachelor", "Master", "B.Sc", "M.Sc", "PhD", "MBA", "Engineer", "Engineering",
    "Computer Science", "Data Science", "Economics", "Business", "Statistics",
    "Mathematics", "Mechanical", "Electrical", "Chemical", "Information Systems"
]

ROLE_HINTS = [
    "Engineer", "Analyst", "Scientist", "Developer", "Manager", "Consultant",
    "Researcher", "Intern", "Specialist", "Coordinator", "Administrator", "Designer"
]


def extract_text(pdf_path: Path) -> str:
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


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def collect_components(input_dir: Path) -> dict:
    pdfs = sorted(input_dir.rglob("*.pdf"))

    skills = Counter()
    degrees = Counter()
    roles = Counter()
    sections = Counter()
    project_lines = Counter()
    experience_lines = Counter()
    locations = Counter()
    languages = Counter()
    urls = Counter()

    for idx, pdf_path in enumerate(pdfs, start=1):
        if idx % 100 == 0 or idx == 1 or idx == len(pdfs):
            print(f"Processing {idx}/{len(pdfs)}: {pdf_path.name}")

        text = extract_text(pdf_path)
        if not text.strip():
            continue

        lines = [normalize_line(x) for x in text.splitlines()]
        lines = [x for x in lines if x]

        lowered_text = text.lower()

        for hint in SECTION_HINTS:
            if hint in lowered_text:
                sections[hint] += 1

        for skill in SKILL_CANDIDATES:
            if re.search(rf"\b{re.escape(skill)}\b", text, re.I):
                skills[skill] += 1

        for line in lines[:80]:
            for hint in DEGREE_HINTS:
                if hint.lower() in line.lower():
                    degrees[line] += 1
                    break

        for line in lines[:120]:
            for hint in ROLE_HINTS:
                if hint.lower() in line.lower():
                    roles[line] += 1
                    break

        for line in lines[:150]:
            if any(token in line.lower() for token in ["project", "built", "developed", "implemented", "created"]):
                project_lines[line] += 1

        for line in lines[:200]:
            if any(token in line.lower() for token in ["responsible", "developed", "analyzed", "designed", "managed", "improved", "led", "supported"]):
                experience_lines[line] += 1

        for match in URL_RE.findall(text):
            urls[match] += 1

        for line in lines[:80]:
            if "," in line and len(line.split()) <= 8 and not EMAIL_RE.search(line) and not PHONE_RE.search(line):
                locations[line] += 1

        for lang in ["Portuguese", "English", "French", "Spanish", "German", "Italian"]:
            if re.search(rf"\b{lang}\b", text, re.I):
                languages[lang] += 1

    return {
        "skills": [x for x, _ in skills.most_common(150)],
        "degrees": [x for x, _ in degrees.most_common(150)],
        "roles": [x for x, _ in roles.most_common(200)],
        "sections": [x for x, _ in sections.most_common(30)],
        "project_lines": [x for x, _ in project_lines.most_common(300)],
        "experience_lines": [x for x, _ in experience_lines.most_common(400)],
        "locations": [x for x, _ in locations.most_common(150)],
        "languages": [x for x, _ in languages.most_common(30)],
        "stats": {
            "pdf_count": len(pdfs),
            "nonempty_skill_count": len(skills),
            "nonempty_degree_count": len(degrees),
            "nonempty_role_count": len(roles),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a reusable resume component bank from public PDFs.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    input_dir = resolve_project_path(args.input_dir)
    output_path = resolve_project_path(args.output)

    bank = collect_components(input_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bank, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Component bank saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
