#!/usr/bin/env bash
set -euo pipefail

ARCHIVE=""
MANIFEST=""
EXPECTED_SHA=""
ENV_FILE=".env.oracle"
PROJECT="ai-decision-studio"
COMPOSE_FILE="docker-compose.oracle-like.yml"
OVERRIDE_FILE="docker-compose.aws-slim.override.yml"
DATA_ROOT="/opt/ai-decision-studio/data"
DELETE_ARCHIVE=0
SKIP_BACKUP=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --archive)
      ARCHIVE="${2:?}"
      shift 2
      ;;
    --manifest)
      MANIFEST="${2:?}"
      shift 2
      ;;
    --sha)
      EXPECTED_SHA="${2:?}"
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
    --data-root)
      DATA_ROOT="${2:?}"
      shift 2
      ;;
    --delete-archive-after-restore)
      DELETE_ARCHIVE=1
      shift
      ;;
    --skip-backup)
      SKIP_BACKUP=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$ARCHIVE" ]; then
  echo "ERROR: --archive is required" >&2
  exit 1
fi

if [ ! -f "$ARCHIVE" ]; then
  echo "ERROR: archive not found: $ARCHIVE" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

if [ -z "$MANIFEST" ]; then
  CANDIDATE="${ARCHIVE%.tar.gz}.manifest.json"
  if [ -f "$CANDIDATE" ]; then
    MANIFEST="$CANDIDATE"
  fi
fi

COMPOSE_ARGS=(-p "$PROJECT" -f "$COMPOSE_FILE")
if [ -f "$OVERRIDE_FILE" ]; then
  COMPOSE_ARGS+=(-f "$OVERRIDE_FILE")
fi

echo
echo "== Validate AI Lab golden archive SHA =="
python3 - "$ARCHIVE" "$MANIFEST" "$EXPECTED_SHA" <<'PY'
from pathlib import Path
import hashlib
import json
import sys

archive = Path(sys.argv[1])
manifest_arg = sys.argv[2]
expected = sys.argv[3].strip()

if manifest_arg and not expected:
    manifest = Path(manifest_arg)
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        expected = str(data.get("archive_sha256") or "").strip()

h = hashlib.sha256()
with archive.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)

actual = h.hexdigest()

print(f"archive={archive}")
print(f"actual_sha256={actual}")

if expected:
    print(f"expected_sha256={expected}")
    if actual != expected:
        raise SystemExit("ERROR: SHA mismatch")

print("OK: archive validated")
PY

TMP="$(mktemp -d /tmp/ads_ai_lab_golden_state.XXXXXX)"
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT

echo
echo "== Extract archive to temp =="
tar -xzf "$ARCHIVE" -C "$TMP"

if [ "$SKIP_BACKUP" -eq 0 ]; then
  echo
  echo "== Backup current AI Lab state before overlay =="
  SAFETY_DIR="${AI_DECISION_STUDIO_AI_LAB_SAFETY_BACKUP_DIR:-$HOME/ads_uploads/ai_lab_golden_state/safety_backups}"
  mkdir -p "$SAFETY_DIR"
  BACKUP="$SAFETY_DIR/ai-lab-before-golden-restore-$(date +%Y%m%d-%H%M%S).tar.gz"

  python3 - "$DATA_ROOT" >/tmp/ads_ai_lab_backup_paths.txt <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
candidates = [
    "baseline/.phase95_evidenceops_actions.sqlite3",
    "baseline/benchmark_runs",
    "baseline/phase5_eval",
    "baseline/phase8_eval",
    "runtime/state/evidenceops",
    "runtime/logs/evidenceops",
    "runtime/evals/phase8",
    "runtime/logs/runtime",
    "runtime/logs/phase6",
    "runtime/logs/phase7",
    "runtime/logs/phase55",
]

for rel in candidates:
    if (root / rel).exists():
        print(rel)
PY

  if [ -s /tmp/ads_ai_lab_backup_paths.txt ]; then
    COPYFILE_DISABLE=1 tar -czf "$BACKUP" \
      --exclude="._*" \
      --exclude=".DS_Store" \
      -C "$DATA_ROOT" \
      -T /tmp/ads_ai_lab_backup_paths.txt

    echo "backup=$BACKUP"
    ls -lh "$BACKUP"
  else
    echo "WARN: no existing AI Lab paths found to backup"
  fi
fi

echo
echo "== Stop product-api/frontend before overlay =="
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" stop product-api frontend

echo
echo "== Robust overlay with sudo rsync =="
sudo rsync -a --chown=ubuntu:ubuntu "$TMP"/ "$DATA_ROOT"/

echo
echo "== Start product-api/frontend =="
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" up -d product-api frontend

sleep 15

echo
echo "== Validate restored AI Lab files =="
docker compose --env-file "$ENV_FILE" "${COMPOSE_ARGS[@]}" exec -T product-api python - <<'PY'
from pathlib import Path
import json
import sqlite3

def sqlite_count(path, table):
    path = Path(path)
    if not path.exists():
        return -1
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return int(cur.fetchone()[0])
    finally:
        con.close()

def count_files(path):
    path = Path(path)
    return sum(1 for p in path.rglob("*") if p.is_file()) if path.exists() else 0

payload = {
    "benchmark_run_files": count_files("/app/baseline/benchmark_runs"),
    "runtime_actions_rows": sqlite_count("/app/runtime/state/evidenceops/actions.sqlite3", "evidenceops_actions"),
    "runtime_eval_rows": sqlite_count("/app/runtime/evals/phase8/phase8_eval_runs.sqlite3", "eval_runs"),
    "runtime_execution_log_exists": Path("/app/runtime/logs/runtime/runtime_execution_log.json").exists(),
    "phase6_log_exists": Path("/app/runtime/logs/phase6/document_agent_log.json").exists(),
    "phase7_log_exists": Path("/app/runtime/logs/phase7/model_comparison_log.json").exists(),
}

payload["ok"] = (
    payload["benchmark_run_files"] > 0
    and payload["runtime_actions_rows"] > 0
    and payload["runtime_eval_rows"] > 0
    and payload["runtime_execution_log_exists"]
)

print(json.dumps(payload, indent=2, ensure_ascii=False))

if not payload["ok"]:
    raise SystemExit("ERROR: AI Lab golden state restore incomplete")
PY

if [ -x scripts/readiness_ai_lab_golden_state_check.sh ]; then
  echo
  echo "== Run AI Lab golden readiness check =="
  scripts/readiness_ai_lab_golden_state_check.sh --env-file "$ENV_FILE"
fi

if [ "$DELETE_ARCHIVE" -eq 1 ]; then
  rm -f "$ARCHIVE"
  if [ -n "$MANIFEST" ] && [ -f "$MANIFEST" ]; then
    rm -f "$MANIFEST"
  fi
fi

echo
echo "OK: AI Lab golden state restored"
