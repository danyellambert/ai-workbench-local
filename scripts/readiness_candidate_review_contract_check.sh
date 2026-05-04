#!/usr/bin/env bash
set -euo pipefail

REPORT="runtime/ai_decision_studio_functional_baseline/parity_reports/candidate_review_contract_readiness_report.json"
ENV_FILE=""
PROJECT="${PROJECT:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.oracle-like.yml}"
OVERRIDE_FILE="${OVERRIDE_FILE:-docker-compose.aws-slim.override.yml}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --report)
      REPORT="${2:?}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --project)
      PROJECT="${2:?}"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$REPORT")"

COMPOSE_ARGS=(-p "$PROJECT" -f "$COMPOSE_FILE")
if [ -f "$OVERRIDE_FILE" ]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
fi

PYTHON_RUNNER=(python3)
if [ -n "$ENV_FILE" ] && command -v docker >/dev/null 2>&1; then
  if docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" ps -q product-api >/dev/null 2>&1; then
    PYTHON_RUNNER=(docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T product-api python)
  fi
fi

"${PYTHON_RUNNER[@]}" - <<'PY' | tee "$REPORT"
import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from src.structured.base import CVAnalysisPayload, ExperienceEntry


ROOT = Path.cwd()
errors = []
checks = {}
evidence = {}


def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


product_pkg = types.ModuleType("src.product")
product_pkg.__path__ = [str(ROOT / "src/product")]
sys.modules["src.product"] = product_pkg

candidate_context_module = _load_module(
    "src.product.candidate_review_context",
    "src/product/candidate_review_context.py",
)
_load_module(
    "src.product.models",
    "src/product/models.py",
)
candidate_presenter_module = _load_module(
    "src.product.candidate_review_presenter",
    "src/product/candidate_review_presenter.py",
)

normalize_role_brief_text = candidate_context_module.normalize_role_brief_text
build_candidate_review_view = candidate_presenter_module.build_candidate_review_view

frontend = Path("frontend/src/pages/CandidateReviewPage.tsx").read_text(encoding="utf-8")
require("frontend_role_brief_recognizes_jd", r"\bjd\b" in frontend)
require(
    "frontend_candidate_classifier_not_hiring_only",
    "candidate|curriculum|francis\\s+taylor" in frontend and "candidate|curriculum|hiring" not in frontend,
)

role_context = normalize_role_brief_text(
    """Job title: Scientific and Preclinical R&D Medical Lead
Target seniority: Senior
Must-have requirements:
- preclinical research leadership
- medical affairs collaboration
- scientific strategy
Interview focus:
- translational research ownership
Role-specific watchouts:
- limited regulated medical environment evidence
"""
)

evidence["role_context"] = role_context.to_dict()
require("backend_role_context_title_present", bool(role_context.title), json.dumps(role_context.to_dict(), ensure_ascii=False))
require("backend_role_context_seniority_present", bool(role_context.seniority), json.dumps(role_context.to_dict(), ensure_ascii=False))
require("backend_role_context_must_haves_present", len(role_context.must_haves) >= 2, json.dumps(role_context.to_dict(), ensure_ascii=False))
require("backend_role_context_watchouts_present", len(role_context.red_flags) >= 1, json.dumps(role_context.to_dict(), ensure_ascii=False))

from src.structured.service import StructuredOutputService

service = StructuredOutputService.__new__(StructuredOutputService)

entries = [
    ExperienceEntry(title="Role 1", organization="Org A", date_range="2018 to 2020"),
    ExperienceEntry(title="Role 2", organization="Org B", date_range="2020 to 2022"),
    ExperienceEntry(title="Role 3", organization="Org C", date_range="2022 to Present"),
]
experience_years = service._compute_experience_years_from_entries(entries)
evidence["structured_service_class_name"] = "StructuredOutputService"
evidence["experience_years_2018_2020_2022_present"] = experience_years
evidence["experience_intervals"] = [
    service._parse_date_range_to_month_interval(entry.date_range)
    for entry in entries
]

require("experience_years_gt_5", experience_years > 5.0, str(experience_years))
require("present_interval_parsed", evidence["experience_intervals"][-1] is not None, json.dumps(evidence["experience_intervals"]))

payload = CVAnalysisPayload(
    personal_info={"full_name": "Francis Taylor", "location": "Remote"},
    skills=["clinical research", "scientific strategy", "stakeholder collaboration"],
    experience_entries=entries,
    experience_years=experience_years,
    strengths=["Scientific strategy and clinical research background are explicit."],
    improvement_areas=[],
    languages=[],
    education_entries=[],
    projects=[],
)

structured_result = SimpleNamespace(
    validated_output=payload,
    execution_metadata={},
)

result = SimpleNamespace(
    workflow_id="candidate_review",
    workflow_label="Candidate Review",
    status="completed",
    summary="Candidate review completed.",
    highlights=[],
    warnings=[],
    recommendation="Proceed with focused validation.",
    structured_result=structured_result,
    grounding_preview=None,
    artifacts=[],
    debug_metadata={
        "input_text": """Evaluate the CV against the normalized hiring thesis below.
Role title: Scientific and Preclinical R&D Medical Lead
Target seniority: Senior
Must-have requirements:
- preclinical research leadership
- regulated medical environment evidence
- scientific strategy
Role-specific watchouts:
- limited regulated medical environment evidence
"""
    },
)

view = build_candidate_review_view(result)
evidence["candidate_review_view"] = {
    "candidate_profile": view.get("candidate_profile"),
    "gaps": view.get("gaps"),
    "seniority_signals": view.get("seniority_signals"),
    "watchouts": view.get("watchouts"),
    "role_context": view.get("role_context"),
}

require("candidate_view_gaps_non_empty", bool(view.get("gaps")), json.dumps(evidence["candidate_review_view"], ensure_ascii=False))
require("candidate_view_seniority_signals_non_empty", bool(view.get("seniority_signals")), json.dumps(evidence["candidate_review_view"], ensure_ascii=False))
require("candidate_view_watchouts_non_empty", bool(view.get("watchouts")), json.dumps(evidence["candidate_review_view"], ensure_ascii=False))
require("candidate_view_experience_gt_5", (view.get("candidate_profile") or {}).get("experience_years", 0) > 5.0, json.dumps(evidence["candidate_review_view"], ensure_ascii=False))

payload_out = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}

print(json.dumps(payload_out, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)
PY
