#!/usr/bin/env bash
set -euo pipefail

SOURCE_BASELINE="${AI_DECISION_STUDIO_SANITIZED_BASELINE_ROOT:-../ai_decision_studio_functional_baseline/current_sanitized_baseline/baseline}"
DATA_ROOT="${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-../ai_decision_studio_functional_baseline/oracle_like_data}"
REPORT="${AI_DECISION_STUDIO_ORACLE_DATA_PREP_REPORT:-../ai_decision_studio_functional_baseline/parity_reports/oracle_data_root_prepare_report.json}"
RESET="${AI_DECISION_STUDIO_ORACLE_DATA_RESET:-0}"

BASELINE_DST="$DATA_ROOT/baseline"
RUNTIME_DST="$DATA_ROOT/runtime"
ARTIFACT_DST="$DATA_ROOT/artifacts"
USERS_DST="$DATA_ROOT/users"
BACKUPS_DST="$DATA_ROOT/backups"

echo "== Prepare Oracle-like data root =="
echo "source_baseline=$SOURCE_BASELINE"
echo "data_root=$DATA_ROOT"
echo "report=$REPORT"
echo "reset=$RESET"

if [ ! -d "$SOURCE_BASELINE" ]; then
  echo "ERROR: source baseline not found: $SOURCE_BASELINE" >&2
  exit 1
fi

case "$DATA_ROOT" in
  ""|"/"|"/opt"|"/opt/"|"/Users"|"/Users/")
    echo "ERROR: refusing unsafe DATA_ROOT: $DATA_ROOT" >&2
    exit 1
    ;;
esac

if [ "$RESET" = "1" ]; then
  echo "== Reset Oracle-like data root =="
  rm -rf "$BASELINE_DST" "$RUNTIME_DST" "$ARTIFACT_DST" "$USERS_DST" "$BACKUPS_DST"
fi

mkdir -p "$BASELINE_DST" "$RUNTIME_DST" "$ARTIFACT_DST" "$USERS_DST" "$BACKUPS_DST"
mkdir -p "$(dirname "$REPORT")"

copy_if_empty() {
  SRC="$1"
  DST="$2"
  LABEL="$3"

  if [ ! -d "$SRC" ]; then
    echo "SKIP $LABEL: source does not exist: $SRC"
    return 0
  fi

  if find "$DST" -mindepth 1 -print -quit | grep -q .; then
    echo "SKIP $LABEL: destination already has files: $DST"
    return 0
  fi

  echo "COPY $LABEL: $SRC -> $DST"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$SRC"/ "$DST"/
  else
    cp -R "$SRC"/. "$DST"/
  fi
}

copy_if_empty "$SOURCE_BASELINE" "$BASELINE_DST" "baseline"
copy_if_empty "$SOURCE_BASELINE/.runtime" "$RUNTIME_DST" "runtime seed"
copy_if_empty "$SOURCE_BASELINE/artifacts" "$ARTIFACT_DST" "artifacts seed"

python3 - <<'PY'
import json
import os
import re
from pathlib import Path

source_baseline = Path(os.environ.get("AI_DECISION_STUDIO_SANITIZED_BASELINE_ROOT", "../ai_decision_studio_functional_baseline/current_sanitized_baseline/baseline")).resolve()
data_root = Path(os.environ.get("AI_DECISION_STUDIO_ORACLE_DATA_ROOT", "../ai_decision_studio_functional_baseline/oracle_like_data")).resolve()
report_path = Path(os.environ.get("AI_DECISION_STUDIO_ORACLE_DATA_PREP_REPORT", "../ai_decision_studio_functional_baseline/parity_reports/oracle_data_root_prepare_report.json")).resolve()

baseline = data_root / "baseline"
runtime = data_root / "runtime"
artifacts = data_root / "artifacts"
users = data_root / "users"
backups = data_root / "backups"

secret_re = re.compile(r"(?i)(api[_-]?key|token|password|passwd|authorization|bearer|secret)\s*[:=]\s*([\"']?)([^\"'\s,}]+)")

def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())

def count_dirs(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_dir())

def env_files(path: Path) -> list[str]:
    if not path.exists():
        return []
    result = []
    for item in path.rglob("*"):
        if item.is_file() and (item.name.lower().startswith(".env") or item.suffix.lower() == ".env"):
            result.append(str(item.relative_to(path)))
    return result

def secret_findings(path: Path, limit: int = 50) -> list[dict]:
    findings = []
    if not path.exists():
        return findings

    for item in path.rglob("*"):
        if len(findings) >= limit:
            break
        if not item.is_file():
            continue
        if item.stat().st_size > 1_000_000:
            continue
        if item.suffix.lower() in {".png", ".jpg", ".jpeg", ".pptx", ".pdf", ".zip", ".sqlite3", ".bin", ".pickle"}:
            continue

        try:
            text = item.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            match = secret_re.search(line)
            if not match:
                continue
            value = match.group(3).strip()
            if not value or value in {"***REDACTED***", "REDACTED", "SET"}:
                continue
            if value.startswith("${") or value.startswith("$"):
                continue
            findings.append({
                "path": str(item.relative_to(path)),
                "line": lineno,
                "key": match.group(1),
            })
            break

    return findings

checks = {
    "source_baseline_exists": source_baseline.exists(),
    "data_root_exists": data_root.exists(),
    "baseline_exists": baseline.exists(),
    "runtime_exists": runtime.exists(),
    "artifacts_exists": artifacts.exists(),
    "users_exists": users.exists(),
    "backups_exists": backups.exists(),
    "baseline_file_count_gt_100": count_files(baseline) > 100,
    "runtime_seed_has_files": count_files(runtime) > 0,
    "artifacts_seed_has_files": count_files(artifacts) > 0,
    "no_env_files_in_data_root": not env_files(data_root),
    "no_secret_patterns_in_data_root": not secret_findings(data_root),
}

report = {
    "ok": all(checks.values()),
    "checks": checks,
    "paths": {
        "source_baseline": str(source_baseline),
        "data_root": str(data_root),
        "baseline": str(baseline),
        "runtime": str(runtime),
        "artifacts": str(artifacts),
        "users": str(users),
        "backups": str(backups),
    },
    "counts": {
        "baseline_files": count_files(baseline),
        "baseline_dirs": count_dirs(baseline),
        "runtime_files": count_files(runtime),
        "artifacts_files": count_files(artifacts),
        "users_files": count_files(users),
    },
    "safety": {
        "env_files": env_files(data_root),
        "secret_findings": secret_findings(data_root),
    },
}

report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(report, indent=2, ensure_ascii=False))

if not report["ok"]:
    raise SystemExit(1)
PY

echo
echo "== Oracle-like data root prepared =="
