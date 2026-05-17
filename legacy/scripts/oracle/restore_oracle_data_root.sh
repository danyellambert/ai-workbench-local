#!/usr/bin/env bash
set -euo pipefail

ARCHIVE="${1:-}"
DEST_ROOT="${2:-${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-}}"
FORCE="${3:-}"

if [[ -z "$ARCHIVE" || -z "$DEST_ROOT" ]]; then
  echo "Usage: legacy/scripts/oracle/restore_oracle_data_root.sh <backup.tar.gz> <destination-data-root> [--force]" >&2
  exit 1
fi

if [[ ! -f "$ARCHIVE" ]]; then
  echo "ERROR: backup archive not found: $ARCHIVE" >&2
  exit 1
fi

DEST_ROOT="$(mkdir -p "$DEST_ROOT" && cd "$DEST_ROOT" && pwd)"

case "$DEST_ROOT" in
  "/"|"")
    echo "ERROR: unsafe DEST_ROOT: $DEST_ROOT" >&2
    exit 1
    ;;
esac

if [[ "$FORCE" != "--force" ]]; then
  if find "$DEST_ROOT" -mindepth 1 -maxdepth 1 | grep -q .; then
    echo "ERROR: destination is not empty: $DEST_ROOT" >&2
    echo "Pass --force to replace baseline/runtime/artifacts/users." >&2
    exit 1
  fi
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

tar -xzf "$ARCHIVE" -C "$TMP_DIR"

for required in baseline runtime artifacts users; do
  if [[ ! -d "$TMP_DIR/$required" ]]; then
    echo "ERROR: backup missing required root: $required" >&2
    exit 1
  fi
done

if [[ "$FORCE" == "--force" ]]; then
  rm -rf "$DEST_ROOT/baseline" "$DEST_ROOT/runtime" "$DEST_ROOT/artifacts" "$DEST_ROOT/users"
fi

mkdir -p "$DEST_ROOT"

for required in baseline runtime artifacts users; do
  rsync -a "$TMP_DIR/$required" "$DEST_ROOT/"
done

mkdir -p "$DEST_ROOT/backups"

DEST_ROOT="$DEST_ROOT" ARCHIVE="$ARCHIVE" python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

dest = Path(os.environ["DEST_ROOT"])
archive = Path(os.environ["ARCHIVE"])

def count_files(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file()) if path.exists() else 0

payload = {
    "ok": True,
    "restored_from": str(archive),
    "destination": str(dest),
    "checks": {
        "baseline_exists": (dest / "baseline").exists(),
        "runtime_exists": (dest / "runtime").exists(),
        "artifacts_exists": (dest / "artifacts").exists(),
        "users_exists": (dest / "users").exists(),
        "backups_exists": (dest / "backups").exists(),
    },
    "counts": {
        "baseline_files": count_files(dest / "baseline"),
        "runtime_files": count_files(dest / "runtime"),
        "artifacts_files": count_files(dest / "artifacts"),
        "users_files": count_files(dest / "users"),
    },
}
print(json.dumps(payload, indent=2, ensure_ascii=False))
assert all(payload["checks"].values()), payload
PY

echo
echo "OK: restore completed"
