from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.evals.phase8_thresholds import build_phase8_threshold_catalog  # noqa: E402
from src.evals.phase8_agent_workflow import (  # noqa: E402
    evaluate_routing_case,
    evaluate_workflow_case,
    load_phase8_agent_workflow_cases,
    summarize_phase8_case_results,
)
from src.storage.phase8_eval_store import append_eval_run  # noqa: E402


DEFAULT_CASES_PATH = ROOT_DIR / "phase8_eval" / "fixtures" / "phase8_agent_workflow_eval_cases.json"
DEFAULT_OUT_PATH = ROOT_DIR / "phase5_eval" / "reports" / "phase8_agent_workflow_eval.json"
EVAL_DB_PATH = ROOT_DIR / ".phase8_eval_runs.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Phase 8 evals for agent routing and LangGraph workflow guardrails.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--out", default=str(DEFAULT_OUT_PATH))
    args = parser.parse_args()

    cases = load_phase8_agent_workflow_cases(Path(args.cases))
    routing_results = [evaluate_routing_case(case) for case in cases.get("routing_cases", [])]
    workflow_results = [evaluate_workflow_case(case) for case in cases.get("workflow_cases", [])]

    for item in [*routing_results, *workflow_results]:
        append_eval_run(EVAL_DB_PATH, item)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "cases_path": str(Path(args.cases)),
        "eval_store_path": str(EVAL_DB_PATH),
        "threshold_catalog": build_phase8_threshold_catalog(),
        "routing_summary": summarize_phase8_case_results(routing_results, suite_name="document_agent_routing_eval"),
        "workflow_summary": summarize_phase8_case_results(workflow_results, suite_name="langgraph_workflow_eval"),
        "routing_results": routing_results,
        "workflow_results": workflow_results,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())