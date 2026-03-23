from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_rag_settings
from scripts.report_evidence_shadow_rollout import analyze_pdf


ROLLOUT_ENV_KEY = "RAG_PDF_EVIDENCE_PIPELINE_ROLLOUT_PERCENTAGE"
DEFAULT_LADDER = [0, 10, 25, 50, 100]
DEFAULT_PDF_DIR = ROOT_DIR / "data" / "synthetic" / "resumes_multilayout" / "pdf"
DEFAULT_SEMANTIC_GATE_DIR = ROOT_DIR / "data" / "materials_demo" / "cv_analysis"
DEFAULT_SEMANTIC_GATE_PATTERN = "Sample-Resume-*.pdf"
EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


@dataclass(frozen=True)
class RolloutDecision:
    action: str
    current_percentage: int
    next_percentage: int
    reasons: list[str]


def _normalize_email(value: str) -> str:
    normalized = (value or "").strip().lower()
    return normalized if EMAIL_PATTERN.match(normalized) else ""


def _normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) < 8 or len(digits) > 15:
        return ""
    return digits


def _read_env_rollout(env_path: Path, fallback: int) -> int:
    if not env_path.exists():
        return fallback
    pattern = re.compile(rf"^{re.escape(ROLLOUT_ENV_KEY)}=(\d+)\s*$", re.MULTILINE)
    match = pattern.search(env_path.read_text(encoding="utf-8"))
    if not match:
        return fallback
    return max(0, min(100, int(match.group(1))))


def _set_runtime_rollout_percentage(percentage: int) -> None:
    os.environ[ROLLOUT_ENV_KEY] = str(max(0, min(100, percentage)))


def _collect_pdf_paths(pdfs: list[str], pdf_dir: str | None) -> list[Path]:
    collected: list[Path] = []
    for item in pdfs:
        path = Path(item)
        if path.suffix.lower() == ".pdf" and path.exists():
            collected.append(path)
    if pdf_dir:
        directory = Path(pdf_dir)
        if directory.exists():
            collected.extend(sorted(path for path in directory.glob("*.pdf") if path.is_file()))
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in collected:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_paths.append(path)
    return sorted(unique_paths)


def _build_batches(pdf_paths: list[Path], batch_size: int) -> list[list[Path]]:
    if batch_size <= 0:
        return [pdf_paths]
    return [pdf_paths[index:index + batch_size] for index in range(0, len(pdf_paths), batch_size)]


def _collect_semantic_gate_paths(semantic_gate_dir: str | None, pattern: str) -> list[Path]:
    if not semantic_gate_dir:
        return []
    directory = Path(semantic_gate_dir)
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob(pattern) if path.is_file())


def _aggregate_results(per_file: list[dict[str, object]]) -> dict[str, object]:
    valid_items = [item for item in per_file if "shadow_rollout" in item]
    return {
        "files": len(per_file),
        "files_failed": len([item for item in per_file if "error" in item]),
        "rollout_selected": sum(1 for item in per_file if (item.get("routing_diagnostics") or {}).get("rollout_selected") is True),
        "rollout_filtered": sum(1 for item in per_file if (item.get("routing_diagnostics") or {}).get("reason") == "rollout_percentage_filtered"),
        "routed_to_evidence": sum(1 for item in per_file if (item.get("routing_diagnostics") or {}).get("decision") == "evidence_path"),
        "agreements": sum(int(item["shadow_rollout"].get("agreements") or 0) for item in valid_items),
        "email_complements": sum(int(item["shadow_rollout"].get("email_complements") or 0) for item in valid_items),
        "phone_complements": sum(int(item["shadow_rollout"].get("phone_complements") or 0) for item in valid_items),
        "email_conflicts": sum(int(item["shadow_rollout"].get("email_conflicts") or 0) for item in valid_items),
        "phone_conflicts": sum(int(item["shadow_rollout"].get("phone_conflicts") or 0) for item in valid_items),
        "vl_timeouts": sum(int((item.get("evidence", {}).get("vl_runtime", {}) or {}).get("timeouts") or 0) for item in valid_items),
        "vl_regions_failed": sum(int((item.get("evidence", {}).get("vl_runtime", {}) or {}).get("regions_failed") or 0) for item in valid_items),
    }


def _previous_step(current: int, ladder: list[int]) -> int:
    eligible = [step for step in ladder if step < current]
    return eligible[-1] if eligible else ladder[0]


def _next_step(current: int, ladder: list[int]) -> int:
    for step in ladder:
        if step > current:
            return step
    return ladder[-1]


def _decide_rollout(
    aggregate: dict[str, object],
    current_percentage: int,
    ladder: list[int],
    max_files_failed: int,
    max_email_conflicts: int,
    max_phone_conflicts: int,
    max_vl_timeouts: int,
    max_vl_regions_failed: int,
) -> RolloutDecision:
    reasons: list[str] = []

    if int(aggregate.get("files", 0)) == 0:
        return RolloutDecision("hold", current_percentage, current_percentage, ["no_files_analyzed"])

    blocking_reasons: list[str] = []
    if int(aggregate.get("files_failed", 0)) > max_files_failed:
        blocking_reasons.append("files_failed_above_threshold")
    if int(aggregate.get("email_conflicts", 0)) > max_email_conflicts:
        blocking_reasons.append("email_conflicts_above_threshold")
    if int(aggregate.get("phone_conflicts", 0)) > max_phone_conflicts:
        blocking_reasons.append("phone_conflicts_above_threshold")
    if int(aggregate.get("vl_timeouts", 0)) > max_vl_timeouts:
        blocking_reasons.append("vl_timeouts_above_threshold")
    if int(aggregate.get("vl_regions_failed", 0)) > max_vl_regions_failed:
        blocking_reasons.append("vl_regions_failed_above_threshold")

    if blocking_reasons:
        next_percentage = _previous_step(current_percentage, ladder)
        action = "rollback" if next_percentage < current_percentage else "hold"
        reasons.extend(blocking_reasons)
        return RolloutDecision(action, current_percentage, next_percentage, reasons)

    if int(aggregate.get("routed_to_evidence", 0)) <= 0:
        return RolloutDecision("hold", current_percentage, current_percentage, ["no_evidence_routing_observed"])

    next_percentage = _next_step(current_percentage, ladder)
    if next_percentage > current_percentage:
        return RolloutDecision("promote", current_percentage, next_percentage, ["guardrails_passed"])

    return RolloutDecision("hold", current_percentage, current_percentage, ["already_at_max_rollout"])


def _update_env_rollout(env_path: Path, percentage: int) -> None:
    content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    pattern = re.compile(rf"^{re.escape(ROLLOUT_ENV_KEY)}=.*$", re.MULTILINE)
    replacement = f"{ROLLOUT_ENV_KEY}={percentage}"
    if pattern.search(content):
        updated = pattern.sub(replacement, content)
    else:
        separator = "" if not content or content.endswith("\n") else "\n"
        updated = f"{content}{separator}{replacement}\n"
    env_path.write_text(updated, encoding="utf-8")


def _evaluate_semantic_gate(
    sample_paths: list[Path],
    min_valid_email_rate: float,
    min_name_presence_rate: float,
    min_confirmed_name_rate: float,
    max_sample_errors: int,
    max_review_warning_rate: float,
) -> dict[str, object]:
    per_sample: list[dict[str, object]] = []
    samples_failed = 0
    samples_with_valid_email = 0
    samples_with_name = 0
    samples_with_confirmed_name = 0
    samples_with_review_warning = 0

    for path in sample_paths:
        analysis = analyze_pdf(path)
        if "error" in analysis:
            samples_failed += 1
            per_sample.append(
                {
                    "file": str(path),
                    "error": analysis["error"],
                    "passed_minimum": False,
                }
            )
            continue

        summary = (analysis.get("evidence") or {}).get("summary") or {}
        warnings = [str(item) for item in summary.get("warnings", [])]
        emails = [_normalize_email(item) for item in summary.get("emails", [])]
        emails = [item for item in emails if item]
        phones = [_normalize_phone(item) for item in summary.get("phones", [])]
        phones = [item for item in phones if item]
        name_value = str(summary.get("name_value") or "").strip()
        name_status = str(summary.get("name_status") or "not_found")
        review_warning = any("need review" in warning.lower() or "visual candidate" in warning.lower() for warning in warnings)
        has_valid_email = bool(emails)
        has_name = bool(name_value) and name_status != "not_found"
        has_confirmed_name = bool(name_value) and name_status == "confirmed"
        passed_minimum = has_valid_email and has_name

        samples_with_valid_email += int(has_valid_email)
        samples_with_name += int(has_name)
        samples_with_confirmed_name += int(has_confirmed_name)
        samples_with_review_warning += int(review_warning)
        per_sample.append(
            {
                "file": str(path),
                "name_status": name_status,
                "name_value": name_value or None,
                "valid_emails": emails,
                "valid_phones": phones,
                "warnings": warnings,
                "review_warning": review_warning,
                "passed_minimum": passed_minimum,
            }
        )

    total_samples = len(sample_paths)
    valid_email_rate = samples_with_valid_email / total_samples if total_samples else 0.0
    name_presence_rate = samples_with_name / total_samples if total_samples else 0.0
    confirmed_name_rate = samples_with_confirmed_name / total_samples if total_samples else 0.0
    review_warning_rate = samples_with_review_warning / total_samples if total_samples else 0.0

    reasons: list[str] = []
    action = "pass"
    if total_samples == 0:
        action = "hold"
        reasons.append("no_semantic_gate_samples_found")
    elif samples_failed > max_sample_errors:
        action = "hold"
        reasons.append("semantic_sample_errors_above_threshold")
    else:
        if valid_email_rate < min_valid_email_rate:
            action = "hold"
            reasons.append("semantic_valid_email_rate_below_threshold")
        if name_presence_rate < min_name_presence_rate:
            action = "hold"
            reasons.append("semantic_name_presence_rate_below_threshold")
        if confirmed_name_rate < min_confirmed_name_rate:
            action = "hold"
            reasons.append("semantic_confirmed_name_rate_below_threshold")
        if review_warning_rate > max_review_warning_rate:
            action = "hold"
            reasons.append("semantic_review_warning_rate_above_threshold")

    return {
        "action": action,
        "reasons": reasons or ["semantic_gate_passed"],
        "aggregate": {
            "samples": total_samples,
            "samples_failed": samples_failed,
            "samples_with_valid_email": samples_with_valid_email,
            "samples_with_name": samples_with_name,
            "samples_with_confirmed_name": samples_with_confirmed_name,
            "samples_with_review_warning": samples_with_review_warning,
            "valid_email_rate": round(valid_email_rate, 4),
            "name_presence_rate": round(name_presence_rate, 4),
            "confirmed_name_rate": round(confirmed_name_rate, 4),
            "review_warning_rate": round(review_warning_rate, 4),
        },
        "per_sample": per_sample,
    }


def _merge_rollout_decisions(
    operational_decision: RolloutDecision,
    semantic_gate: dict[str, object],
) -> RolloutDecision:
    semantic_action = str(semantic_gate.get("action") or "hold")
    semantic_reasons = [str(item) for item in semantic_gate.get("reasons", [])]
    if operational_decision.action == "rollback":
        return RolloutDecision(
            action="rollback",
            current_percentage=operational_decision.current_percentage,
            next_percentage=operational_decision.next_percentage,
            reasons=operational_decision.reasons + semantic_reasons,
        )
    if semantic_action != "pass":
        return RolloutDecision(
            action="hold",
            current_percentage=operational_decision.current_percentage,
            next_percentage=operational_decision.current_percentage,
            reasons=operational_decision.reasons + semantic_reasons,
        )
    return operational_decision


def _run_single_round(
    pdf_paths: list[Path],
    semantic_sample_paths: list[Path],
    current_percentage: int,
    out_path: Path,
    env_path: Path,
    max_files_failed: int,
    max_email_conflicts: int,
    max_phone_conflicts: int,
    max_vl_timeouts: int,
    max_vl_regions_failed: int,
    semantic_min_valid_email_rate: float,
    semantic_min_name_presence_rate: float,
    semantic_min_confirmed_name_rate: float,
    semantic_max_sample_errors: int,
    semantic_max_review_warning_rate: float,
    apply_decision: bool,
) -> dict[str, object]:
    _set_runtime_rollout_percentage(current_percentage)
    per_file = [analyze_pdf(path) for path in pdf_paths]
    aggregate = _aggregate_results(per_file)
    operational_decision = _decide_rollout(
        aggregate=aggregate,
        current_percentage=current_percentage,
        ladder=DEFAULT_LADDER,
        max_files_failed=max_files_failed,
        max_email_conflicts=max_email_conflicts,
        max_phone_conflicts=max_phone_conflicts,
        max_vl_timeouts=max_vl_timeouts,
        max_vl_regions_failed=max_vl_regions_failed,
    )
    semantic_gate = _evaluate_semantic_gate(
        sample_paths=semantic_sample_paths,
        min_valid_email_rate=semantic_min_valid_email_rate,
        min_name_presence_rate=semantic_min_name_presence_rate,
        min_confirmed_name_rate=semantic_min_confirmed_name_rate,
        max_sample_errors=semantic_max_sample_errors,
        max_review_warning_rate=semantic_max_review_warning_rate,
    )
    decision = _merge_rollout_decisions(operational_decision, semantic_gate)

    applied = False
    if apply_decision and decision.next_percentage != current_percentage:
        _update_env_rollout(env_path, decision.next_percentage)
        _set_runtime_rollout_percentage(decision.next_percentage)
        applied = True

    payload = {
        "env_path": str(env_path),
        "files_analyzed": [str(path) for path in pdf_paths],
        "semantic_gate_files": [str(path) for path in semantic_sample_paths],
        "aggregate": aggregate,
        "operational_decision": {
            "action": operational_decision.action,
            "current_percentage": operational_decision.current_percentage,
            "next_percentage": operational_decision.next_percentage,
            "reasons": operational_decision.reasons,
        },
        "semantic_gate": semantic_gate,
        "decision": {
            "action": decision.action,
            "current_percentage": decision.current_percentage,
            "next_percentage": decision.next_percentage,
            "reasons": decision.reasons,
            "applied": applied,
        },
        "per_file": per_file,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _run_auto_mode(
    pdf_paths: list[Path],
    semantic_sample_paths: list[Path],
    env_path: Path,
    out_path: Path,
    batch_size: int,
    max_files_failed: int,
    max_email_conflicts: int,
    max_phone_conflicts: int,
    max_vl_timeouts: int,
    max_vl_regions_failed: int,
    semantic_min_valid_email_rate: float,
    semantic_min_name_presence_rate: float,
    semantic_min_confirmed_name_rate: float,
    semantic_max_sample_errors: int,
    semantic_max_review_warning_rate: float,
    apply_decision: bool,
) -> dict[str, object]:
    rag = get_rag_settings()
    current_percentage = _read_env_rollout(env_path, int(getattr(rag, "pdf_evidence_pipeline_rollout_percentage", 100)))
    batches = _build_batches(pdf_paths, batch_size)
    rounds: list[dict[str, object]] = []

    for round_index, batch in enumerate(batches, start=1):
        round_out_path = out_path.with_name(f"{out_path.stem}_round_{round_index:02d}{out_path.suffix}")
        round_payload = _run_single_round(
            pdf_paths=batch,
            semantic_sample_paths=semantic_sample_paths,
            current_percentage=current_percentage,
            out_path=round_out_path,
            env_path=env_path,
            max_files_failed=max_files_failed,
            max_email_conflicts=max_email_conflicts,
            max_phone_conflicts=max_phone_conflicts,
            max_vl_timeouts=max_vl_timeouts,
            max_vl_regions_failed=max_vl_regions_failed,
            semantic_min_valid_email_rate=semantic_min_valid_email_rate,
            semantic_min_name_presence_rate=semantic_min_name_presence_rate,
            semantic_min_confirmed_name_rate=semantic_min_confirmed_name_rate,
            semantic_max_sample_errors=semantic_max_sample_errors,
            semantic_max_review_warning_rate=semantic_max_review_warning_rate,
            apply_decision=apply_decision,
        )
        rounds.append(round_payload)
        decision = round_payload["decision"]
        current_percentage = int(decision["next_percentage"])
        if decision["action"] != "promote":
            break

    final_payload = {
        "mode": "auto",
        "env_path": str(env_path),
        "pdf_dir": str(DEFAULT_PDF_DIR),
        "semantic_gate_dir": str(DEFAULT_SEMANTIC_GATE_DIR),
        "semantic_gate_files": [str(path) for path in semantic_sample_paths],
        "total_files_available": len(pdf_paths),
        "batch_size": batch_size,
        "rounds": rounds,
        "final_rollout_percentage": current_percentage,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return final_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Automatically promote, hold, or rollback evidence_cv rollout based on shadow telemetry")
    parser.add_argument("pdfs", nargs="*", default=[], help="PDF files to analyze")
    parser.add_argument("--pdf-dir", default=str(DEFAULT_PDF_DIR), help="Directory with PDFs to analyze automatically")
    parser.add_argument("--semantic-gate-dir", default=str(DEFAULT_SEMANTIC_GATE_DIR), help="Directory with more realistic CV samples used as semantic gate")
    parser.add_argument("--semantic-gate-pattern", default=DEFAULT_SEMANTIC_GATE_PATTERN, help="Glob pattern for semantic gate samples")
    parser.add_argument("--env", default=str(ROOT_DIR / ".env"), help="Path to .env file to update when --apply is used")
    parser.add_argument("--out", default="phase5_eval/reports/evidence_cv_auto_rollout_decision.json", help="JSON file to write the decision report")
    parser.add_argument("--apply", action="store_true", help="Apply the decided rollout percentage to the .env file")
    parser.add_argument("--auto", action="store_true", help="Run sequential automatic rollout rounds over batches from --pdf-dir")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for --auto mode")
    parser.add_argument("--max-files-failed", type=int, default=0)
    parser.add_argument("--max-email-conflicts", type=int, default=0)
    parser.add_argument("--max-phone-conflicts", type=int, default=0)
    parser.add_argument("--max-vl-timeouts", type=int, default=0)
    parser.add_argument("--max-vl-regions-failed", type=int, default=0)
    parser.add_argument("--semantic-min-valid-email-rate", type=float, default=1.0)
    parser.add_argument("--semantic-min-name-presence-rate", type=float, default=1.0)
    parser.add_argument("--semantic-min-confirmed-name-rate", type=float, default=0.67)
    parser.add_argument("--semantic-max-sample-errors", type=int, default=0)
    parser.add_argument("--semantic-max-review-warning-rate", type=float, default=1.0)
    args = parser.parse_args()

    env_path = Path(args.env)
    pdf_paths = _collect_pdf_paths(args.pdfs, args.pdf_dir)
    semantic_sample_paths = _collect_semantic_gate_paths(args.semantic_gate_dir, args.semantic_gate_pattern)
    out_path = Path(args.out)
    if args.auto:
        payload = _run_auto_mode(
            pdf_paths=pdf_paths,
            semantic_sample_paths=semantic_sample_paths,
            env_path=env_path,
            out_path=out_path,
            batch_size=args.batch_size,
            max_files_failed=args.max_files_failed,
            max_email_conflicts=args.max_email_conflicts,
            max_phone_conflicts=args.max_phone_conflicts,
            max_vl_timeouts=args.max_vl_timeouts,
            max_vl_regions_failed=args.max_vl_regions_failed,
            semantic_min_valid_email_rate=args.semantic_min_valid_email_rate,
            semantic_min_name_presence_rate=args.semantic_min_name_presence_rate,
            semantic_min_confirmed_name_rate=args.semantic_min_confirmed_name_rate,
            semantic_max_sample_errors=args.semantic_max_sample_errors,
            semantic_max_review_warning_rate=args.semantic_max_review_warning_rate,
            apply_decision=args.apply,
        )
    else:
        rag = get_rag_settings()
        current_percentage = _read_env_rollout(env_path, int(getattr(rag, "pdf_evidence_pipeline_rollout_percentage", 100)))
        payload = _run_single_round(
            pdf_paths=pdf_paths,
            semantic_sample_paths=semantic_sample_paths,
            current_percentage=current_percentage,
            out_path=out_path,
            env_path=env_path,
            max_files_failed=args.max_files_failed,
            max_email_conflicts=args.max_email_conflicts,
            max_phone_conflicts=args.max_phone_conflicts,
            max_vl_timeouts=args.max_vl_timeouts,
            max_vl_regions_failed=args.max_vl_regions_failed,
            semantic_min_valid_email_rate=args.semantic_min_valid_email_rate,
            semantic_min_name_presence_rate=args.semantic_min_name_presence_rate,
            semantic_min_confirmed_name_rate=args.semantic_min_confirmed_name_rate,
            semantic_max_sample_errors=args.semantic_max_sample_errors,
            semantic_max_review_warning_rate=args.semantic_max_review_warning_rate,
            apply_decision=args.apply,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())