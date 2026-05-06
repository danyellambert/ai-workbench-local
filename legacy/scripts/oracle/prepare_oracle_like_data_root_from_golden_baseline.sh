#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-}"
if [ -z "$DATA_ROOT" ]; then
  echo "ERROR: AI_DECISION_STUDIO_ORACLE_DATA_ROOT is required."
  exit 1
fi

BASELINE_ROOT="${AI_DECISION_STUDIO_BASELINE_ROOT:-$DATA_ROOT/baseline}"
RUNTIME_ROOT="${AI_DECISION_STUDIO_RUNTIME_ROOT:-$DATA_ROOT/runtime}"
ARTIFACT_ROOT="${AI_DECISION_STUDIO_ARTIFACT_ROOT:-$DATA_ROOT/artifacts}"
GOLDEN_BASELINE_SOURCE="${AI_DECISION_STUDIO_GOLDEN_BASELINE_SOURCE:-}"

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_ROOT="${AI_DECISION_STUDIO_DATA_PREP_BACKUP_ROOT:-$DATA_ROOT/backups/pre-oracle-like-rich-data-prep-$STAMP}"

echo "== Oracle-like rich data root preparation =="
echo "data_root=$DATA_ROOT"
echo "baseline_root=$BASELINE_ROOT"
echo "runtime_root=$RUNTIME_ROOT"
echo "artifact_root=$ARTIFACT_ROOT"
echo "golden_baseline_source=${GOLDEN_BASELINE_SOURCE:-<existing baseline>}"
echo "backup_root=$BACKUP_ROOT"

mkdir -p "$BASELINE_ROOT" "$RUNTIME_ROOT" "$ARTIFACT_ROOT" "$BACKUP_ROOT/preserve"

echo
echo "== Backup current data root slices =="
if [ -d "$BASELINE_ROOT" ]; then rsync -a "$BASELINE_ROOT/" "$BACKUP_ROOT/baseline/"; fi
if [ -d "$RUNTIME_ROOT" ]; then rsync -a "$RUNTIME_ROOT/" "$BACKUP_ROOT/runtime/"; fi
if [ -d "$ARTIFACT_ROOT" ]; then rsync -a "$ARTIFACT_ROOT/" "$BACKUP_ROOT/artifacts/"; fi

echo
echo "== Preserve local product settings =="
cp -f "$RUNTIME_ROOT/state/product/preferences.json" "$BACKUP_ROOT/preserve/preferences.json" 2>/dev/null || true
cp -f "$RUNTIME_ROOT/state/product/runtime_controls.json" "$BACKUP_ROOT/preserve/runtime_controls.json" 2>/dev/null || true

if [ -n "$GOLDEN_BASELINE_SOURCE" ]; then
  if [ ! -d "$GOLDEN_BASELINE_SOURCE" ]; then
    echo "ERROR: golden baseline source does not exist: $GOLDEN_BASELINE_SOURCE"
    exit 1
  fi

  SRC_RESOLVED="$(cd "$GOLDEN_BASELINE_SOURCE" && pwd)"
  DST_RESOLVED="$(cd "$BASELINE_ROOT" && pwd)"

  if [ "$SRC_RESOLVED" != "$DST_RESOLVED" ]; then
    echo
    echo "== Import golden baseline =="
    rsync -a --delete "$SRC_RESOLVED/" "$BASELINE_ROOT/"
  else
    echo
    echo "== Golden baseline source is already the target baseline; skipping baseline import =="
  fi
fi

echo
echo "== Seed runtime from baseline/.runtime =="
if [ ! -d "$BASELINE_ROOT/.runtime" ]; then
  echo "ERROR: rich baseline runtime missing: $BASELINE_ROOT/.runtime"
  exit 1
fi
rsync -a --delete "$BASELINE_ROOT/.runtime/" "$RUNTIME_ROOT/"

echo
echo "== Seed artifacts from baseline/artifacts =="
if [ ! -d "$BASELINE_ROOT/artifacts" ]; then
  echo "ERROR: rich baseline artifacts missing: $BASELINE_ROOT/artifacts"
  exit 1
fi
rsync -a --delete "$BASELINE_ROOT/artifacts/" "$ARTIFACT_ROOT/"

echo
echo "== Restore local product settings =="
mkdir -p "$RUNTIME_ROOT/state/product"
cp -f "$BACKUP_ROOT/preserve/preferences.json" "$RUNTIME_ROOT/state/product/preferences.json" 2>/dev/null || true
cp -f "$BACKUP_ROOT/preserve/runtime_controls.json" "$RUNTIME_ROOT/state/product/runtime_controls.json" 2>/dev/null || true

echo
echo "== Seed EvidenceOps action store =="
SRC_ACTION_STORE="$BASELINE_ROOT/.phase95_evidenceops_actions.sqlite3"
DST_ACTION_STORE="$RUNTIME_ROOT/state/evidenceops/actions.sqlite3"
if [ ! -f "$SRC_ACTION_STORE" ]; then
  echo "ERROR: rich EvidenceOps action store missing: $SRC_ACTION_STORE"
  exit 1
fi
mkdir -p "$(dirname "$DST_ACTION_STORE")"
cp -f "$SRC_ACTION_STORE" "$DST_ACTION_STORE"

echo
echo "== Validate prepared data root =="
python3 - <<'PY'
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

data_root = Path(os.environ["AI_DECISION_STUDIO_ORACLE_DATA_ROOT"])
baseline = Path(os.environ.get("AI_DECISION_STUDIO_BASELINE_ROOT") or data_root / "baseline")
runtime = Path(os.environ.get("AI_DECISION_STUDIO_RUNTIME_ROOT") or data_root / "runtime")
artifacts = Path(os.environ.get("AI_DECISION_STUDIO_ARTIFACT_ROOT") or data_root / "artifacts")

def file_count(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file()) if path.exists() else 0

def sqlite_count(path: Path, table: str) -> int:
    if not path.exists():
        return 0
    conn = sqlite3.connect(path)
    try:
        return int(conn.execute(f"select count(*) from {table}").fetchone()[0])
    finally:
        conn.close()

benchmark_summaries = list((baseline / "evals/benchmark-runs").glob("**/aggregated/summary.json"))
eval_db = runtime / "evals/phase8/phase8_eval_runs.sqlite3"
action_store = runtime / "state/evidenceops/actions.sqlite3"

report = {
    "baseline_files": file_count(baseline),
    "runtime_files": file_count(runtime),
    "artifact_files": file_count(artifacts),
    "benchmark_summary_count": len(benchmark_summaries),
    "eval_runs": sqlite_count(eval_db, "eval_runs"),
    "evidenceops_actions": sqlite_count(action_store, "evidenceops_actions"),
    "paths": {
        "baseline": str(baseline),
        "runtime": str(runtime),
        "artifacts": str(artifacts),
        "eval_db": str(eval_db),
        "action_store": str(action_store),
    },
}

print(json.dumps(report, indent=2, ensure_ascii=False))

if report["benchmark_summary_count"] < 5:
    raise SystemExit("ERROR: benchmark summaries look too sparse.")
if report["eval_runs"] < 76:
    raise SystemExit("ERROR: eval runs look too sparse.")
if report["evidenceops_actions"] < 72:
    raise SystemExit("ERROR: EvidenceOps actions look too sparse.")
if report["artifact_files"] < 1000:
    raise SystemExit("ERROR: artifact root looks too sparse.")
PY

echo
echo "OK: Oracle-like rich data root prepared"
