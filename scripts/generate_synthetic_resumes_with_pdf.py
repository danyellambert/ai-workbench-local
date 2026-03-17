#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import textwrap
from dataclasses import dataclass, asdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def resolve_project_path(path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


FIRST_NAMES = [
    "Lucas", "Marina", "Ana", "Rafael", "Juliana", "Bruno", "Camila",
    "Felipe", "Beatriz", "Diego", "Larissa", "Thiago", "Renata", "Matheus",
    "Carolina", "Gabriel", "Isabela", "Pedro", "Laura", "Vinicius"
]

LAST_NAMES = [
    "Silva", "Souza", "Oliveira", "Pereira", "Costa", "Almeida",
    "Ferreira", "Rodrigues", "Gomes", "Martins", "Araujo", "Lima",
    "Barbosa", "Ribeiro", "Carvalho", "Nascimento"
]

COMPANIES = [
    "TechNova", "DataBridge", "Enerflux", "BlueMetrics", "Axis Consulting",
    "GreenGrid", "NovaOps", "CloudForge", "Labora Analytics", "Prime Systems",
    "EDF R&D", "ONS", "PowerDot", "Vinci Concessions", "Holcim", "Veolia"
]


@dataclass
class Experience:
    title: str
    company: str
    location: str
    start: str
    end: str
    bullets: List[str]


@dataclass
class Resume:
    full_name: str
    email: str
    phone: str
    location: str
    linkedin: str
    summary: str
    education: List[str]
    skills: List[str]
    languages: List[str]
    experience: List[Experience]
    projects: List[str]
    difficulty: str
    domain: str


def slugify(text: str) -> str:
    return (
        text.lower()
        .replace(" ", ".")
        .replace(",", "")
        .replace("/", ".")
        .replace("..", ".")
    )


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}"


def make_email(full_name: str) -> str:
    return f"{slugify(full_name)}@example.com"


def make_phone() -> str:
    return f"+55 11 9{random.randint(1000,9999)}-{random.randint(1000,9999)}"


def pick_some(values: List[str], k_min: int, k_max: int) -> List[str]:
    values = [x for x in values if x]
    if not values:
        return []
    k = min(len(values), random.randint(k_min, k_max))
    return random.sample(values, k)


def choose_domain(bank: dict) -> str:
    domains = list((bank.get("domains") or {}).keys())
    return random.choice(domains) if domains else "general"


def choose_location(bank: dict) -> str:
    locations = bank.get("locations") or ["São Paulo, Brazil"]
    return random.choice(locations)


def choose_summary(bank: dict, domain: str, skills: List[str]) -> str:
    summaries = bank.get("summaries") or []
    if summaries:
        base = random.choice(summaries)
    else:
        base = "Professional with experience in technical, analytical, and cross-functional work."
    if skills:
        return f"{base} Strong exposure to {', '.join(skills[:3])}."
    return base


def fallback_experience_lines() -> List[str]:
    return [
        "Analyzed operational and commercial data to identify trends and optimization opportunities.",
        "Collaborated with cross-functional teams across engineering, product, and business stakeholders.",
        "Automated recurring analyses and reporting workflows using Python and SQL.",
        "Prepared structured reports and presentations for leadership stakeholders.",
        "Improved internal processes through data-driven problem solving and clear documentation.",
    ]


def fallback_project_lines() -> List[str]:
    return [
        "Built a retrieval-augmented document analysis workflow to improve answer grounding.",
        "Created an automated reporting pipeline to reduce manual work.",
        "Implemented structured outputs to turn free-form documents into validated artifacts.",
        "Developed internal tools to streamline analysis and workflow execution.",
    ]


def generate_resume(bank: dict, difficulty: str) -> Resume:
    domain = choose_domain(bank)
    domain_bank = (bank.get("domains") or {}).get(domain, {})

    full_name = random_name()
    email = make_email(full_name)
    phone = make_phone()
    location = choose_location(bank)
    linkedin = f"https://linkedin.com/in/{slugify(full_name)}"

    shared_skills = bank.get("skills", [])
    domain_skills = domain_bank.get("skills", [])
    skills_pool = list(dict.fromkeys(domain_skills + shared_skills))
    skills = pick_some(skills_pool, 6, 10)

    languages = pick_some(bank.get("languages", []), 2, 3) or ["Portuguese (Native)", "English (Professional)"]
    education = pick_some(bank.get("degrees", []), 1, 3)

    shared_roles = bank.get("roles", [])
    domain_roles = domain_bank.get("roles", [])
    role_pool = list(dict.fromkeys(domain_roles + shared_roles))
    role_lines = pick_some(role_pool, 2, 4) or ["Analyst", "Engineer"]

    shared_exp = bank.get("experience_lines", []) or fallback_experience_lines()
    shared_proj = bank.get("project_lines", []) or fallback_project_lines()
    domain_proj = domain_bank.get("projects", [])

    summary = choose_summary(bank, domain, skills)

    exp_count = {"simple": 2, "medium": 3, "hard": 4}.get(difficulty, 3)
    experiences: List[Experience] = []

    for i in range(exp_count):
        title = role_lines[i % len(role_lines)]
        company = random.choice(bank.get("companies") or COMPANIES)
        bullets = pick_some(shared_exp, 3, 4)
        if not bullets:
            bullets = fallback_experience_lines()[:3]

        start_year = random.randint(2016, 2022)
        end_year = random.randint(max(start_year + 1, 2021), 2025)
        end = "Present" if random.random() < 0.2 and i == 0 else f"{end_year}-12"

        experiences.append(
            Experience(
                title=title,
                company=company,
                location=location,
                start=f"{start_year}-01",
                end=end,
                bullets=bullets[:3],
            )
        )

    projects = pick_some(domain_proj + shared_proj, 2, 5)
    if not projects:
        projects = fallback_project_lines()[:3]

    return Resume(
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
        linkedin=linkedin,
        summary=summary,
        education=education,
        skills=skills,
        languages=languages,
        experience=experiences,
        projects=projects,
        difficulty=difficulty,
        domain=domain,
    )


def render_markdown(resume: Resume) -> str:
    lines = [
        f"# {resume.full_name}",
        "",
        f"- Email: {resume.email}",
        f"- Phone: {resume.phone}",
        f"- Location: {resume.location}",
        f"- LinkedIn: {resume.linkedin}",
        f"- Domain: {resume.domain}",
        f"- Difficulty: {resume.difficulty}",
        "",
        "## Summary",
        resume.summary,
        "",
        "## Education",
    ]

    for edu in resume.education:
        lines.append(f"- {edu}")

    lines.extend(["", "## Skills", ", ".join(resume.skills), "", "## Languages"])
    for lang in resume.languages:
        lines.append(f"- {lang}")

    lines.extend(["", "## Experience"])
    for exp in resume.experience:
        lines.append(f"### {exp.title}")
        lines.append(f"{exp.company} | {exp.location} | {exp.start} to {exp.end}")
        for bullet in exp.bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    lines.append("## Projects")
    for project in resume.projects:
        lines.append(f"- {project}")

    return "\n".join(lines).strip() + "\n"


def render_pdf(resume: Resume, output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    left = 2 * cm
    top = height - 2 * cm
    y = top
    line_height = 14

    def ensure_space():
        nonlocal y
        if y < 2 * cm:
            c.showPage()
            y = top

    def write_line(text: str = "", *, bold: bool = False, size: int = 10):
        nonlocal y
        ensure_space()
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(left, y, text[:135])
        y -= line_height

    write_line(resume.full_name, bold=True, size=16)
    write_line(f"Email: {resume.email}")
    write_line(f"Phone: {resume.phone}")
    write_line(f"Location: {resume.location}")
    write_line(f"LinkedIn: {resume.linkedin}")
    write_line(f"Domain: {resume.domain} | Difficulty: {resume.difficulty}")
    write_line()

    write_line("Summary", bold=True, size=12)
    for line in textwrap.wrap(resume.summary, width=100):
        write_line(line)

    write_line()
    write_line("Education", bold=True, size=12)
    for edu in resume.education:
        for line in textwrap.wrap(f"- {edu}", width=100):
            write_line(line)

    write_line()
    write_line("Skills", bold=True, size=12)
    for line in textwrap.wrap(", ".join(resume.skills), width=100):
        write_line(line)

    write_line()
    write_line("Languages", bold=True, size=12)
    for lang in resume.languages:
        write_line(f"- {lang}")

    write_line()
    write_line("Experience", bold=True, size=12)
    for exp in resume.experience:
        write_line(exp.title, bold=True)
        write_line(f"{exp.company} | {exp.location} | {exp.start} to {exp.end}")
        for bullet in exp.bullets:
            for line in textwrap.wrap(f"- {bullet}", width=100):
                write_line(line)
        write_line()

    write_line("Projects", bold=True, size=12)
    for project in resume.projects:
        for line in textwrap.wrap(f"- {project}", width=100):
            write_line(line)

    c.save()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=["json", "md", "pdf"],
        default=["json", "md"],
        help="Output formats to generate",
    )
    args = parser.parse_args()

    bank_path = resolve_project_path(args.bank)
    outdir = resolve_project_path(args.outdir)

    bank = json.loads(bank_path.read_text(encoding="utf-8"))

    json_dir = outdir / "json"
    md_dir = outdir / "md"
    pdf_dir = outdir / "pdf"

    if "json" in args.formats:
        json_dir.mkdir(parents=True, exist_ok=True)
    if "md" in args.formats:
        md_dir.mkdir(parents=True, exist_ok=True)
    if "pdf" in args.formats:
        pdf_dir.mkdir(parents=True, exist_ok=True)

    difficulties = ["simple", "medium", "hard"]

    for i in range(args.count):
        difficulty = difficulties[i % len(difficulties)]
        resume = generate_resume(bank, difficulty)
        stem = f"{i:04d}_{difficulty}_{slugify(resume.full_name)}"

        if "json" in args.formats:
            (json_dir / f"{stem}.json").write_text(
                json.dumps(asdict(resume), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        if "md" in args.formats:
            (md_dir / f"{stem}.md").write_text(
                render_markdown(resume),
                encoding="utf-8",
            )

        if "pdf" in args.formats:
            render_pdf(resume, pdf_dir / f"{stem}.pdf")

    print(f"Synthetic resumes saved to: {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
