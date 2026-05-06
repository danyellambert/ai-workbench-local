#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.oracle}"
PROJECT="${PROJECT:-ai-decision-studio}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.local.yml}"
OVERRIDE_FILE="${OVERRIDE_FILE:-docker-compose.aws-slim.yml}"
REPORT="runtime/ai_decision_studio_functional_baseline/parity_reports/public_ai_lab_overlay_readiness_report.json"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      ENV_FILE="${2:?}"
      shift 2
      ;;
    --project)
      PROJECT="${2:?}"
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

COMPOSE_ARGS=(-p "$PROJECT" -f "$COMPOSE_FILE")
if [ -f "$OVERRIDE_FILE" ]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
fi

docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T product-api python - <<'PY' | tee "$REPORT"
from pathlib import Path
from datetime import datetime, timezone
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8011"
ROOT = Path("/app/users/public_sessions")

errors = []
checks = {}
evidence = {}

def require(name, condition, detail=""):
    checks[name] = bool(condition)
    if not condition:
        errors.append(f"{name} failed" + (f": {detail}" if detail else ""))

def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def latest_timestamp(items):
    values = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("timestamp") or item.get("created_at") or "").strip()
        if raw:
            values.append(raw)
    return max(values) if values else None

def fetch(path, *, session_id=None):
    headers = {}
    if session_id:
        headers["Cookie"] = f"ads_session_id={session_id}"
    req = urllib.request.Request(BASE_URL + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code

    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "_status": status, "_error": repr(exc), "_bytes": len(raw)}

    if isinstance(data, dict):
        data["_status"] = status
        data["_bytes"] = len(raw)
    return data

def find_latest_session_with_overlay_runs():
    candidates = []
    if not ROOT.exists():
        return None

    for session in ROOT.iterdir():
        if not session.is_dir():
            continue
        runs = session / "overlay" / "runs"
        workflow_path = runs / "workflow_history.json"
        runtime_path = runs / "runtime_execution_log.json"
        telemetry_path = runs / "telemetry_runs.json"
        lab_runs_path = runs / "lab_workflow_runs.json"

        if not workflow_path.exists():
            continue

        score_files = [p for p in [workflow_path, runtime_path, telemetry_path, lab_runs_path] if p.exists()]
        if not score_files:
            continue

        newest = max(p.stat().st_mtime for p in score_files)
        candidates.append((newest, session.name))

    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else None

session_id = find_latest_session_with_overlay_runs()

require("public_session_with_overlay_exists", bool(session_id), "no public session with overlay/runs was found")

if session_id:
    runs_root = ROOT / session_id / "overlay" / "runs"

    workflow_path = runs_root / "workflow_history.json"
    runtime_path = runs_root / "runtime_execution_log.json"
    telemetry_path = runs_root / "telemetry_runs.json"
    lab_runs_path = runs_root / "lab_workflow_runs.json"

    workflow_items = read_json(workflow_path, [])
    runtime_items = read_json(runtime_path, [])
    telemetry_items = read_json(telemetry_path, [])
    lab_run_items = read_json(lab_runs_path, [])

    if not isinstance(workflow_items, list):
        workflow_items = []
    if not isinstance(runtime_items, list):
        runtime_items = []
    if not isinstance(telemetry_items, list):
        telemetry_items = []
    if not isinstance(lab_run_items, list):
        lab_run_items = []

    overlay_workflow_latest = latest_timestamp(workflow_items)
    overlay_runtime_latest = latest_timestamp(runtime_items)

    evidence.update({
        "session_id": session_id,
        "overlay_workflow_path": str(workflow_path),
        "overlay_runtime_path": str(runtime_path),
        "overlay_telemetry_path": str(telemetry_path),
        "overlay_lab_runs_path": str(lab_runs_path),
        "overlay_workflow_count": len(workflow_items),
        "overlay_runtime_count": len(runtime_items),
        "overlay_telemetry_count": len(telemetry_items),
        "overlay_lab_runs_count": len(lab_run_items),
        "overlay_workflow_latest": overlay_workflow_latest,
        "overlay_runtime_latest": overlay_runtime_latest,
    })

    require("overlay_workflow_history_present", len(workflow_items) > 0)
    require("overlay_runtime_log_present", len(runtime_items) > 0)
    require("overlay_telemetry_present", len(telemetry_items) > 0)

    # Baseline/global-ish view with an empty newly-created public session.
    base_runtime = fetch("/api/lab/runtime")
    base_evals = fetch("/api/lab/evals")
    base_overview = fetch("/api/lab/overview")

    # Target public session view.
    run_history = fetch("/api/product/run-history", session_id=session_id)
    runtime = fetch("/api/lab/runtime", session_id=session_id)
    evals = fetch("/api/lab/evals", session_id=session_id)
    overview = fetch("/api/lab/overview", session_id=session_id)

    evidence.update({
        "run_history_read_scope": run_history.get("read_scope"),
        "run_history_source": run_history.get("source"),
        "run_history_total_runs": (run_history.get("summary") or {}).get("total_runs"),
        "run_history_latest_timestamp": (run_history.get("summary") or {}).get("latest_timestamp"),
        "run_history_additional_history_paths": run_history.get("additional_history_paths"),

        "runtime_read_scope": runtime.get("read_scope"),
        "runtime_lastTraceAt": (runtime.get("ops_summary") or {}).get("lastTraceAt"),
        "runtime_throughput24h": (runtime.get("ops_summary") or {}).get("throughput24h"),
        "runtime_additional_runtime_log_paths": runtime.get("additional_runtime_log_paths"),
        "base_runtime_lastTraceAt": (base_runtime.get("ops_summary") or {}).get("lastTraceAt"),

        "evals_read_scope": evals.get("read_scope"),
        "evals_live_total": (evals.get("liveTotals") or {}).get("total"),
        "base_evals_live_total": (base_evals.get("liveTotals") or {}).get("total"),

        "overview_read_scope": overview.get("read_scope"),
        "overview_kpis": overview.get("kpis"),
        "base_overview_kpis": base_overview.get("kpis"),
    })

    workflow_total = int((run_history.get("summary") or {}).get("total_runs") or 0)
    overview_workflow_runs = None
    for kpi in overview.get("kpis") or []:
        if isinstance(kpi, dict) and kpi.get("label") == "Workflow Runs":
            overview_workflow_runs = int(kpi.get("value") or 0)

    evals_live_total = int((evals.get("liveTotals") or {}).get("total") or 0)
    base_evals_live_total = int((base_evals.get("liveTotals") or {}).get("total") or 0)

    require("run_history_overlay_scope", run_history.get("read_scope") == "global_plus_session_overlay", str(run_history.get("read_scope")))
    require("run_history_uses_overlay_source", "session_overlay" in str(run_history.get("source") or ""), str(run_history.get("source")))
    require("run_history_lists_overlay_path", session_id in json.dumps(run_history.get("additional_history_paths") or []), json.dumps(run_history.get("additional_history_paths") or []))

    require("runtime_overlay_scope", runtime.get("read_scope") == "global_plus_session_overlay", str(runtime.get("read_scope")))
    require("runtime_lists_overlay_path", session_id in json.dumps(runtime.get("additional_runtime_log_paths") or []), json.dumps(runtime.get("additional_runtime_log_paths") or []))
    if overlay_runtime_latest:
        require("runtime_sees_overlay_latest_trace", str((runtime.get("ops_summary") or {}).get("lastTraceAt") or "") >= overlay_runtime_latest[:19], f"lastTraceAt={(runtime.get('ops_summary') or {}).get('lastTraceAt')} overlay={overlay_runtime_latest}")

    require("evals_overlay_scope", evals.get("read_scope") == "global_plus_session_overlay", str(evals.get("read_scope")))
    require("evals_live_total_includes_overlay", evals_live_total > base_evals_live_total, f"{evals_live_total} <= {base_evals_live_total}")

    require("overview_overlay_scope", overview.get("read_scope") == "global_plus_session_overlay", str(overview.get("read_scope")))
    require("overview_workflow_runs_matches_overlay_history", overview_workflow_runs == workflow_total, f"overview={overview_workflow_runs} run_history={workflow_total}")

payload = {
    "ok": not errors,
    "checks": checks,
    "errors": errors,
    "evidence": evidence,
}

print(json.dumps(payload, indent=2, ensure_ascii=False))

if errors:
    raise SystemExit(1)
PY
