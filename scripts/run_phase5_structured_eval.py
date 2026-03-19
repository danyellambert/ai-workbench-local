from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


from src.structured.envelope import TaskExecutionRequest, StructuredResult
from src.structured.service import structured_service

FIXTURES_DIR = PROJECT_ROOT / "phase5_eval" / "fixtures"
REPORTS_DIR = PROJECT_ROOT / "phase5_eval" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PLACEHOLDER_PATTERNS = [
    r"\bfull name\b",
    r"\bname@example\.com\b",
    r"\bskill 1\b",
    r"\bstrength 1\b",
    r"\bimprovement 1\b",
    r"\bitem 1\b",
    r"\btopic title\b",
    r"\btask title\b",
    r"\bcompany x\b",
]


@dataclass
class EvalOutcome:
    task: str
    status: str
    score: int
    max_score: int
    reasons: list[str]
    output_path: str | None = None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path), strict=False)
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(pages).strip()
def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _contains_placeholder(value: Any) -> bool:
    text = _stringify(value).lower()
    return any(re.search(pattern, text) for pattern in PLACEHOLDER_PATTERNS)


def _count_non_empty_strings(items: list[Any]) -> int:
    count = 0
    for item in items:
        if isinstance(item, str) and item.strip():
            count += 1
    return count


def _evaluate_result(task: str, result: StructuredResult) -> EvalOutcome:
    reasons: list[str] = []
    score = 0
    max_score = 5

    if result.success and result.validated_output is not None:
        score += 1
    else:
        reasons.append("task execution did not succeed")
        return EvalOutcome(task, "FAIL", score, max_score, reasons)

    payload = result.validated_output
    if payload.task_type == task:
        score += 1
    else:
        reasons.append(f"unexpected task_type: {payload.task_type}")

    dumped = payload.model_dump(mode="json")
    if not _contains_placeholder(dumped):
        score += 1
    else:
        reasons.append("output contains obvious prompt placeholders")

    if task == "extraction":
        entities = dumped.get("entities", [])
        fields = dumped.get("extracted_fields", [])
        if len(entities) + len(fields) >= 2:
            score += 1
        else:
            reasons.append("extraction returned too little structured content")

        if dumped.get("main_subject") and (dumped.get("important_dates") or dumped.get("important_numbers") or dumped.get("action_items") or dumped.get("risks")):
            score += 1
        else:
            reasons.append("extraction missing main subject or useful secondary structure")

    elif task == "summary":
        topics = dumped.get("topics", [])
        executive_summary = dumped.get("executive_summary", "")
        if topics and executive_summary.strip():
            score += 1
        else:
            reasons.append("summary missing topics or executive summary")

        insights = dumped.get("key_insights", [])
        if len(insights) >= 1:
            score += 1
        else:
            reasons.append("summary missing key insights")

    elif task == "checklist":
        items = dumped.get("items", [])
        title = dumped.get("title", "")
        if title.strip() and len(items) >= 3:
            score += 1
        else:
            reasons.append("checklist missing title or enough items")

        item_titles = [item.get("title", "") for item in items if isinstance(item, dict)]
        if _count_non_empty_strings(item_titles) >= 3:
            score += 1
        else:
            reasons.append("checklist items are too weak or empty")

    elif task == "cv_analysis":
        personal = dumped.get("personal_info") or {}
        sections = dumped.get("sections", [])
        skills = dumped.get("skills", [])
        if (personal.get("full_name") or personal.get("email")) and sections:
            score += 1
        else:
            reasons.append("cv analysis missing basic personal info or sections")

        if len(skills) >= 2 or len(sections) >= 2:
            score += 1
        else:
            reasons.append("cv analysis returned too little resume structure")

    elif task == "code_analysis":
        issues = dumped.get("detected_issues", [])
        summary = dumped.get("snippet_summary", "")
        if summary.strip() and len(issues) >= 1:
            score += 1
        else:
            reasons.append("code analysis missing summary or issues")

        if dumped.get("refactor_plan") and dumped.get("test_suggestions"):
            score += 1
        else:
            reasons.append("code analysis missing refactor plan or test suggestions")

    status = "PASS" if score >= 5 else "WARN" if score >= 3 else "FAIL"
    return EvalOutcome(task, status, score, max_score, reasons)


def _build_request(task: str, input_text: str, provider: str, model: str | None) -> TaskExecutionRequest:
    return TaskExecutionRequest(
        task_type=task,
        input_text=input_text,
        use_rag_context=False,
        source_document_ids=[],
        provider=provider,
        model=model,
    )


def _default_input_for_task(task: str) -> str:
    mapping = {
        "extraction": FIXTURES_DIR / "01_extraction_input.txt",
        "summary": FIXTURES_DIR / "02_summary_input.txt",
        "checklist": FIXTURES_DIR / "03_checklist_input.txt",
        "cv_analysis": FIXTURES_DIR / "04_cv_sample.txt",
        "code_analysis": FIXTURES_DIR / "05_code_sample.py",
    }
    return _read_text(mapping[task])


def _save_report(report: dict[str, Any]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORTS_DIR / f"phase5_structured_eval_{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def run_tasks(tasks: list[str], provider: str, model: str | None, cv_pdf: str | None) -> int:
    outputs: list[dict[str, Any]] = []
    worst_exit = 0

    for task in tasks:
        if task == "cv_analysis" and cv_pdf:
            input_text = _read_pdf_text(Path(cv_pdf))
        else:
            input_text = _default_input_for_task(task)

        request = _build_request(task, input_text=input_text, provider=provider, model=model)
        result = structured_service.execute_task(request)
        outcome = _evaluate_result(task, result)

        outputs.append({
            "task": task,
            "status": outcome.status,
            "score": outcome.score,
            "max_score": outcome.max_score,
            "reasons": outcome.reasons,
            "success": result.success,
            "error": result.error.model_dump(mode="json") if result.error else None,
            "validation_error": result.validation_error,
            "parsing_error": result.parsing_error,
            "payload": result.validated_output.model_dump(mode="json") if result.validated_output else None,
        })

        print(f"[{outcome.status}] {task}: {outcome.score}/{outcome.max_score}")
        if outcome.reasons:
            for reason in outcome.reasons:
                print(f"  - {reason}")

        if outcome.status == "FAIL":
            worst_exit = max(worst_exit, 2)
        elif outcome.status == "WARN":
            worst_exit = max(worst_exit, 1)

    report = {
        "generated_at": datetime.now().isoformat(),
        "provider": provider,
        "model": model,
        "tasks": outputs,
    }
    out = _save_report(report)
    print(f"\nReport saved to: {out}")
    return worst_exit


def main() -> int:
    parser = argparse.ArgumentParser(description="Run automated smoke evals for Phase 5 structured outputs.")
    parser.add_argument("--task", default="all", choices=["all", "extraction", "summary", "checklist", "cv_analysis", "code_analysis"])
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--model", default=None)
    parser.add_argument("--cv-pdf", default=None, help="Optional PDF path for cv_analysis instead of the default text fixture")
    args = parser.parse_args()

    tasks = [args.task] if args.task != "all" else ["extraction", "summary", "checklist", "cv_analysis", "code_analysis"]
    return run_tasks(tasks, provider=args.provider, model=args.model, cv_pdf=args.cv_pdf)


if __name__ == "__main__":
    raise SystemExit(main())
