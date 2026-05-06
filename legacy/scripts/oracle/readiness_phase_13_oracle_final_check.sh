#!/usr/bin/env bash
set -euo pipefail

REPORT="${AI_DECISION_STUDIO_PHASE13_REPORT:-runtime/ai_decision_studio_functional_baseline/parity_reports/phase_13_oracle_final_report.json}"
REPORT_DIR="$(dirname "$REPORT")"

mkdir -p "$REPORT_DIR"

export AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE="${AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE:-docker-compose.oracle-like.yml}"
export AI_DECISION_STUDIO_ORACLE_DATA_ROOT="${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-runtime/ai_decision_studio_functional_baseline/oracle_like_data}"
export AI_DECISION_STUDIO_SANITIZED_BASELINE_ROOT="${AI_DECISION_STUDIO_SANITIZED_BASELINE_ROOT:-runtime/ai_decision_studio_functional_baseline/current_sanitized_baseline/baseline}"
export AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT="${AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT:-8069}"
export EVIDENCEOPS_REPOSITORY_BACKEND="${EVIDENCEOPS_REPOSITORY_BACKEND:-local}"

echo "== Phase 13 Oracle final readiness check =="
echo "report=$REPORT"
echo "compose=$AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE"
echo "data_root=$AI_DECISION_STUDIO_ORACLE_DATA_ROOT"
echo "baseline=$AI_DECISION_STUDIO_SANITIZED_BASELINE_ROOT"
echo "frontend_port=$AI_DECISION_STUDIO_FRONTEND_PUBLIC_PORT"
echo "evidenceops_backend=$EVIDENCEOPS_REPOSITORY_BACKEND"

PHASE13_TMP="$(mktemp -d)"
export PHASE13_TMP
export REPORT

cleanup() {
  rm -rf "$PHASE13_TMP"
}
trap cleanup EXIT

run_step() {
  NAME="$1"
  shift

  LOG="$PHASE13_TMP/${NAME}.log"
  STATUS_FILE="$PHASE13_TMP/${NAME}.status"

  echo
  echo "== Step: $NAME =="
  set +e
  "$@" >"$LOG" 2>&1
  CODE="$?"
  set -e

  echo "$CODE" > "$STATUS_FILE"
  cat "$LOG"

  if [ "$CODE" != "0" ]; then
    echo
    echo "ERROR: step failed: $NAME" >&2
    return "$CODE"
  fi
}

FINAL_CODE=0

run_step oracle_like_readiness \
  legacy/scripts/oracle/readiness_oracle_like_deploy_check.sh || FINAL_CODE=1

if [ "$FINAL_CODE" = "0" ]; then
  export AI_DECISION_STUDIO_ORACLE_DATA_RESET="${AI_DECISION_STUDIO_ORACLE_DATA_RESET:-1}"
  run_step prepare_oracle_data_root \
    legacy/scripts/oracle/prepare_oracle_data_root.sh || FINAL_CODE=1
fi

if [ "$FINAL_CODE" = "0" ]; then
  run_step smoke_oracle_like_compose \
    legacy/scripts/oracle/smoke_oracle_like_compose.sh || FINAL_CODE=1
fi

if [ "$FINAL_CODE" = "0" ]; then
  run_step build_oracle_deployment_bundle \
    scripts/build_oracle_deployment_bundle.sh || FINAL_CODE=1
fi

python3 - <<'PY'
import json
import os
from pathlib import Path

tmp = Path(os.environ["PHASE13_TMP"])
report = Path(os.environ["REPORT"])

steps = []
for name in [
    "oracle_like_readiness",
    "prepare_oracle_data_root",
    "smoke_oracle_like_compose",
    "build_oracle_deployment_bundle",
]:
    status_path = tmp / f"{name}.status"
    log_path = tmp / f"{name}.log"

    if status_path.exists():
        code = int(status_path.read_text(encoding="utf-8").strip())
    else:
        code = None

    if log_path.exists():
        log_tail = "\n".join(log_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-80:])
    else:
        log_tail = ""

    steps.append({
        "name": name,
        "ok": code == 0,
        "exit_code": code,
        "log_tail": log_tail,
    })

data = {
    "ok": all(step["ok"] for step in steps),
    "checks": {step["name"]: step["ok"] for step in steps},
    "steps": steps,
    "artifacts": {
        "oracle_like_deploy_report": "runtime/ai_decision_studio_functional_baseline/parity_reports/oracle_like_deploy_readiness_report.json",
        "oracle_data_root_prepare_report": "runtime/ai_decision_studio_functional_baseline/parity_reports/oracle_data_root_prepare_report.json",
        "oracle_like_compose_smoke_report": "runtime/ai_decision_studio_functional_baseline/parity_reports/oracle_like_compose_smoke_report.json",
        "oracle_deployment_bundle_report": "runtime/ai_decision_studio_functional_baseline/parity_reports/oracle_deployment_bundle_report.json",
        "oracle_deployment_bundle": "runtime/ai_decision_studio_functional_baseline/oracle_deployment_bundle/ai-decision-studio-oracle-app-bundle.tar.gz",
    },
}

report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(data, indent=2, ensure_ascii=False))

if not data["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Phase 13 Oracle final readiness check completed =="
