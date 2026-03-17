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


from typing import List, Literal

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


FIRST_NAMES = [
    "Lucas", "Marina", "Ana", "Rafael", "Juliana", "Bruno", "Camila",
    "Felipe", "Beatriz", "Diego", "Larissa", "Thiago", "Renata", "Matheus",
    "Carolina", "Gabriel", "Isabela", "Pedro", "Laura", "Vinicius",
]

LAST_NAMES = [
    "Silva", "Souza", "Oliveira", "Pereira", "Costa", "Almeida",
    "Ferreira", "Rodrigues", "Gomes", "Martins", "Araujo", "Lima",
    "Barbosa", "Ribeiro", "Carvalho", "Nascimento",
]

COMPANIES = [
    "TechNova", "DataBridge", "Enerflux", "BlueMetrics", "Axis Consulting",
    "GreenGrid", "NovaOps", "CloudForge", "Labora Analytics", "Prime Systems",
    "EDF R&D", "ONS", "PowerDot", "Vinci Concessions", "Holcim", "Veolia",
    "OpenField Energy", "Aster Analytics", "NorthBridge Systems", "Mercury Labs",
]

LayoutType = Literal[
    "classic_one_column",
    "modern_two_column",
    "compact_sidebar",
    "dense_executive",
    "scan_like_image_pdf",
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
    layout_type: str
    text_extractable: bool


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


def choose_summary(bank: dict, skills: List[str]) -> str:
    summaries = bank.get("summaries") or []
    base = random.choice(summaries) if summaries else (
        "Professional with experience in technical, analytical, and cross-functional work."
    )
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
        "Defined metrics and analytical frameworks to support decision-making.",
    ]


def fallback_project_lines() -> List[str]:
    return [
        "Built a retrieval-augmented document analysis workflow to improve answer grounding.",
        "Created an automated reporting pipeline to reduce manual work.",
        "Implemented structured outputs to turn free-form documents into validated artifacts.",
        "Developed internal tools to streamline analysis and workflow execution.",
    ]


def resolve_layout(layout_arg: str, index: int) -> str:
    if layout_arg != "auto":
        return layout_arg
    layouts = [
        "classic_one_column",
        "modern_two_column",
        "compact_sidebar",
        "dense_executive",
        "scan_like_image_pdf",
    ]
    return layouts[index % len(layouts)]


def generate_resume(bank: dict, difficulty: str, layout_type: str) -> Resume:
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
    skills = pick_some(skills_pool, 6, 12)

    languages = pick_some(bank.get("languages", []), 2, 3) or ["Portuguese (Native)", "English (Professional)"]
    education = pick_some(bank.get("degrees", []), 1, 3)

    shared_roles = bank.get("roles", [])
    domain_roles = domain_bank.get("roles", [])
    role_pool = list(dict.fromkeys(domain_roles + shared_roles))
    role_lines = pick_some(role_pool, 2, 4) or ["Analyst", "Engineer"]

    shared_exp = bank.get("experience_lines", []) or fallback_experience_lines()
    shared_proj = bank.get("project_lines", []) or fallback_project_lines()
    domain_proj = domain_bank.get("projects", [])

    summary = choose_summary(bank, skills)

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

    text_extractable = layout_type != "scan_like_image_pdf"

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
        layout_type=layout_type,
        text_extractable=text_extractable,
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
        f"- Layout: {resume.layout_type}",
        f"- Text extractable: {resume.text_extractable}",
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


def _wrap(text: str, width: int) -> List[str]:
    return textwrap.wrap(text, width=width) if text else [""]


def render_classic_one_column(resume: Resume, output_path: Path) -> None:
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
    write_line(f"{resume.location} | {resume.email} | {resume.phone}")
    write_line(f"{resume.linkedin}")
    write_line()

    write_line("SUMMARY", bold=True, size=11)
    for line in _wrap(resume.summary, 100):
        write_line(line)

    write_line()
    write_line("EDUCATION", bold=True, size=11)
    for edu in resume.education:
        for line in _wrap(f"- {edu}", 100):
            write_line(line)

    write_line()
    write_line("SKILLS", bold=True, size=11)
    for line in _wrap(", ".join(resume.skills), 100):
        write_line(line)

    write_line()
    write_line("LANGUAGES", bold=True, size=11)
    for lang in resume.languages:
        write_line(f"- {lang}")

    write_line()
    write_line("EXPERIENCE", bold=True, size=11)
    for exp in resume.experience:
        write_line(exp.title, bold=True)
        write_line(f"{exp.company} | {exp.location} | {exp.start} to {exp.end}")
        for bullet in exp.bullets:
            for line in _wrap(f"- {bullet}", 100):
                write_line(line)
        write_line()

    write_line("PROJECTS", bold=True, size=11)
    for project in resume.projects:
        for line in _wrap(f"- {project}", 100):
            write_line(line)

    c.save()


def render_modern_two_column(resume: Resume, output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    left_w = 6.2 * cm
    margin = 1.2 * cm
    y_left = height - 1.6 * cm
    y_right = height - 1.8 * cm
    line_h = 12

    # Sidebar background
    c.setFillColorRGB(0.92, 0.95, 0.99)
    c.rect(0, 0, left_w, height, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)

    def write_left(text: str = "", bold: bool = False, size: int = 9):
        nonlocal y_left
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(0.8 * cm, y_left, text[:40])
        y_left -= line_h

    def write_right(text: str = "", bold: bool = False, size: int = 9):
        nonlocal y_right
        if y_right < 2 * cm:
            c.showPage()
            y_right = height - 1.8 * cm
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(left_w + margin, y_right, text[:92])
        y_right -= line_h

    write_right(resume.full_name, bold=True, size=17)
    write_right(f"{resume.domain.title()} Profile", bold=False, size=11)
    write_right()

    write_left("CONTACT", bold=True, size=10)
    write_left(resume.location)
    write_left(resume.email)
    write_left(resume.phone)
    write_left("LinkedIn")
    write_left(resume.linkedin[:38])
    write_left()

    write_left("SKILLS", bold=True, size=10)
    for skill in resume.skills[:12]:
        write_left(f"• {skill}")
    write_left()

    write_left("LANGUAGES", bold=True, size=10)
    for lang in resume.languages:
        write_left(f"• {lang}")
    write_left()

    write_right("PROFILE", bold=True, size=11)
    for line in _wrap(resume.summary, 78):
        write_right(line)

    write_right()
    write_right("EXPERIENCE", bold=True, size=11)
    for exp in resume.experience:
        write_right(exp.title, bold=True)
        write_right(f"{exp.company} | {exp.start} to {exp.end}")
        write_right(f"{exp.location}")
        for bullet in exp.bullets:
            for line in _wrap(f"• {bullet}", 78):
                write_right(line)
        write_right()

    write_right("EDUCATION", bold=True, size=11)
    for edu in resume.education:
        for line in _wrap(f"• {edu}", 78):
            write_right(line)

    write_right()
    write_right("PROJECTS", bold=True, size=11)
    for project in resume.projects:
        for line in _wrap(f"• {project}", 78):
            write_right(line)

    c.save()


def render_compact_sidebar(resume: Resume, output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    sidebar_w = 5.0 * cm
    margin = 1.0 * cm
    y_left = height - 1.4 * cm
    y_right = height - 1.5 * cm
    line_h = 11

    c.setFillColorRGB(0.15, 0.18, 0.24)
    c.rect(0, 0, sidebar_w, height, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)

    def write_left(text: str = "", bold: bool = False, size: int = 8):
        nonlocal y_left
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(0.6 * cm, y_left, text[:34])
        y_left -= line_h

    def write_right(text: str = "", bold: bool = False, size: int = 9):
        nonlocal y_right
        c.setFillColorRGB(0, 0, 0)
        if y_right < 2 * cm:
            c.showPage()
            y_right = height - 1.5 * cm
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(sidebar_w + margin, y_right, text[:98])
        y_right -= line_h

    write_left(resume.full_name, bold=True, size=11)
    write_left(resume.location)
    write_left(resume.email[:34])
    write_left(resume.phone)
    write_left()
    write_left("CORE SKILLS", bold=True, size=9)
    for skill in resume.skills[:10]:
        write_left(f"- {skill}")
    write_left()
    write_left("LANGUAGES", bold=True, size=9)
    for lang in resume.languages:
        write_left(f"- {lang}")

    write_right("SUMMARY", bold=True, size=11)
    for line in _wrap(resume.summary, 84):
        write_right(line)
    write_right()
    write_right("EXPERIENCE", bold=True, size=11)
    for exp in resume.experience:
        write_right(exp.title, bold=True)
        write_right(f"{exp.company} | {exp.location}")
        write_right(f"{exp.start} to {exp.end}")
        for bullet in exp.bullets[:2]:
            for line in _wrap(f"- {bullet}", 84):
                write_right(line)
        write_right()
    write_right("EDUCATION", bold=True, size=11)
    for edu in resume.education:
        for line in _wrap(f"- {edu}", 84):
            write_right(line)

    c.save()


def render_dense_executive(resume: Resume, output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    x = 1.6 * cm
    y = height - 1.5 * cm
    line_h = 10

    def write_line(text: str = "", bold: bool = False, size: int = 8):
        nonlocal y
        if y < 1.7 * cm:
            c.showPage()
            y = height - 1.5 * cm
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x, y, text[:150])
        y -= line_h

    write_line(resume.full_name, bold=True, size=15)
    write_line(f"{resume.location} | {resume.email} | {resume.phone} | {resume.linkedin}")
    write_line()
    write_line("EXECUTIVE PROFILE", bold=True, size=9)
    for line in _wrap(resume.summary, 120):
        write_line(line)
    write_line()
    write_line("CORE SKILLS", bold=True, size=9)
    for line in _wrap(", ".join(resume.skills), 120):
        write_line(line)
    write_line()
    write_line("PROFESSIONAL EXPERIENCE", bold=True, size=9)
    for exp in resume.experience:
        write_line(f"{exp.title} | {exp.company} | {exp.location} | {exp.start} to {exp.end}", bold=True, size=8)
        for bullet in exp.bullets:
            for line in _wrap(f"- {bullet}", 120):
                write_line(line)
    write_line()
    write_line("EDUCATION", bold=True, size=9)
    for edu in resume.education:
        for line in _wrap(f"- {edu}", 120):
            write_line(line)
    write_line()
    write_line("LANGUAGES", bold=True, size=9)
    write_line(", ".join(resume.languages))
    write_line()
    write_line("PROJECT HIGHLIGHTS", bold=True, size=9)
    for project in resume.projects:
        for line in _wrap(f"- {project}", 120):
            write_line(line)
    c.save()


def render_scan_like_image_pdf(resume: Resume, output_path: Path) -> None:
    width, height = 1654, 2339  # roughly A4 at 150 DPI
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    x_left = 80
    y = 70
    line_h = 24

    def write(text: str = "", *, indent: int = 0):
        nonlocal y
        for line in _wrap(text, 95):
            draw.text((x_left + indent, y), line, fill="black", font=font)
            y += line_h

    write(resume.full_name)
    write(f"{resume.location} | {resume.email} | {resume.phone}")
    write(f"{resume.linkedin}")
    y += 12
    write("SUMMARY")
    write(resume.summary, indent=12)
    y += 8
    write("SKILLS")
    write(", ".join(resume.skills), indent=12)
    y += 8
    write("EXPERIENCE")
    for exp in resume.experience:
        write(f"{exp.title} | {exp.company} | {exp.location} | {exp.start} to {exp.end}", indent=12)
        for bullet in exp.bullets:
            write(f"- {bullet}", indent=24)
        y += 4
    write("EDUCATION")
    for edu in resume.education:
        write(f"- {edu}", indent=12)
    y += 8
    write("LANGUAGES")
    for lang in resume.languages:
        write(f"- {lang}", indent=12)
    y += 8
    write("PROJECTS")
    for project in resume.projects:
        write(f"- {project}", indent=12)

    img.save(str(output_path), "PDF", resolution=150.0)


def render_pdf(resume: Resume, output_path: Path) -> None:
    if resume.layout_type == "classic_one_column":
        render_classic_one_column(resume, output_path)
    elif resume.layout_type == "modern_two_column":
        render_modern_two_column(resume, output_path)
    elif resume.layout_type == "compact_sidebar":
        render_compact_sidebar(resume, output_path)
    elif resume.layout_type == "dense_executive":
        render_dense_executive(resume, output_path)
    elif resume.layout_type == "scan_like_image_pdf":
        render_scan_like_image_pdf(resume, output_path)
    else:
        render_classic_one_column(resume, output_path)


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
    parser.add_argument(
        "--layout",
        choices=[
            "auto",
            "classic_one_column",
            "modern_two_column",
            "compact_sidebar",
            "dense_executive",
            "scan_like_image_pdf",
        ],
        default="auto",
        help="Layout strategy to use",
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
        layout_type = resolve_layout(args.layout, i)
        resume = generate_resume(bank, difficulty, layout_type)
        stem = f"{i:04d}_{difficulty}_{layout_type}_{slugify(resume.full_name)}"

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
