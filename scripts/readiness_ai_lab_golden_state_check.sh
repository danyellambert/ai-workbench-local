#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.oracle}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8071}"
MIN_BENCHMARK_RUNS="1"
MIN_BENCHMARK_MODELS="1"
MIN_EVIDENCEOPS_ACTIONS="1"
MIN_HISTORICAL_CASES="1"
REPORT="../ai_decision_studio_functional_baseline/parity_reports/ai_lab_golden_state_readiness_report.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --base-url)
      BASE_URL="${2:?}"
      shift 2
      ;;
    --report)
      REPORT="${2:?}"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$REPORT")"

python3 - "$BASE_URL" "$MIN_BENCHMARK_RUNS" "$MIN_BENCHMARK_MODELS" "$MIN_EVIDENCEOPS_ACTIONS" "$MIN_HISTORICAL_CASES" "$REPORT" <<'PY'
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

base_url = sys.argv[1].rstrip("/")
min_benchmark_runs = int(sys.argv[2])
min_benchmark_models = int(sys.argv[3])
min_evidenceops_actions = int(sys.argv[4])
min_historical_cases = int(sys.argv[5])
report_path = Path(sys.argv[6])

errors = []
checks = {}
evidence = {}

def fetch(name, path):
    url = base_url + path
    try:
        with urllib.request.urlopen(url, timeout=90) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    except Exception as exc:
        errors.append(f"{name}: request failed: {exc!r}")
        return {}

    evidence[f"{name}_http_status"] = status
    evidence[f"{name}_bytes"] = len(raw)

    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        errors.append(f"{name}: non-json response status={status}: {exc}")
        return {}

def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))

evidenceops = fetch("evidenceops", "/api/lab/evidenceops")
benchmarks = fetch("benchmarks", "/api/lab/benchmarks")
evals = fetch("evals", "/api/lab/evals")
overview = fetch("overview", "/api/lab/overview")
runtime = fetch("runtime", "/api/lab/runtime")

evidenceops_summary = evidenceops.get("summary") or {}
benchmark_summary = benchmarks.get("summary") or {}
eval_totals = evals.get("totals") or {}
overview_kpis = overview.get("kpis") or []

actions_len = len(evidenceops.get("actions") or [])
open_actions = int(evidenceops_summary.get("openActions") or 0)
benchmark_total_runs = int(benchmark_summary.get("totalRuns") or 0)
benchmark_model_count = int(benchmark_summary.get("modelCount") or 0)
historical_cases = len(evals.get("historicalCases") or [])
eval_total = int(eval_totals.get("total") or 0)

eval_pass_rate_value = None
for kpi in overview_kpis:
    if kpi.get("label") == "Eval Pass Rate":
        eval_pass_rate_value = kpi.get("value")

evidence.update({
    "evidenceops_actions_len": actions_len,
    "evidenceops_openActions": open_actions,
    "benchmarks_totalRuns": benchmark_total_runs,
    "benchmarks_modelCount": benchmark_model_count,
    "evals_historicalCases": historical_cases,
    "evals_totals_total": eval_total,
    "overview_evalPassRate": eval_pass_rate_value,
})

require("evidenceops_ok", evidenceops.get("ok") is True)
require("evidenceops_live", evidenceops.get("status") == "live")
require("evidenceops_actions_present", actions_len >= min_evidenceops_actions, f"{actions_len} < {min_evidenceops_actions}")
require("evidenceops_open_actions_present", open_actions >= min_evidenceops_actions, f"{open_actions} < {min_evidenceops_actions}")

require("benchmarks_ok", benchmarks.get("ok") is True)
require("benchmarks_not_empty", benchmark_total_runs >= min_benchmark_runs, f"{benchmark_total_runs} < {min_benchmark_runs}")
require("benchmarks_models_present", benchmark_model_count >= min_benchmark_models, f"{benchmark_model_count} < {min_benchmark_models}")

require("evals_ok", evals.get("ok") is True)
require("evals_historical_cases_present", historical_cases >= min_historical_cases, f"{historical_cases} < {min_historical_cases}")
require("evals_totals_present", eval_total >= min_historical_cases, f"{eval_total} < {min_historical_cases}")

require("overview_ok", overview.get("ok") is True)
require("overview_live", overview.get("status") == "live")
require("overview_eval_pass_rate_present", eval_pass_rate_value not in (None, "", "0%"), str(eval_pass_rate_value))

require("runtime_ok", runtime.get("ok") is True)
require("runtime_live", runtime.get("status") == "live")

payload = {
    "ok": not errors,
    "base_url": base_url,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}

report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)

print("OK: AI Lab golden state readiness passed")
PY
