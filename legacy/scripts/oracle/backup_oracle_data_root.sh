#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${1:-${AI_DECISION_STUDIO_ORACLE_DATA_ROOT:-/opt/ai-decision-studio/data}}"
OUT_DIR="${2:-${AI_DECISION_STUDIO_BACKUP_ROOT:-$DATA_ROOT/backups}}"
TIMESTAMP="${AI_DECISION_STUDIO_BACKUP_TIMESTAMP:-$(date +%Y%m%d-%H%M%S)}"

DATA_ROOT="$(cd "$DATA_ROOT" && pwd)"
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

ARCHIVE="$OUT_DIR/ai-decision-studio-data-$TIMESTAMP.tar.gz"
MANIFEST="$OUT_DIR/ai-decision-studio-data-$TIMESTAMP.manifest.json"

case "$DATA_ROOT" in
  "/"|"")
    echo "ERROR: unsafe DATA_ROOT: $DATA_ROOT" >&2
    exit 1
    ;;
esac

for required in baseline runtime artifacts users; do
  if [[ ! -d "$DATA_ROOT/$required" ]]; then
    echo "ERROR: missing required data directory: $DATA_ROOT/$required" >&2
    exit 1
  fi
done

ENV_HITS="$(find "$DATA_ROOT"/baseline "$DATA_ROOT"/runtime "$DATA_ROOT"/artifacts "$DATA_ROOT"/users \
  \( -name ".env" -o -name ".env.*" -o -name "*.env" \) \
  -type f 2>/dev/null | sed -n '1,50p' || true)"

if [[ -n "$ENV_HITS" ]]; then
  echo "ERROR: env-like files found inside data root. Refusing backup." >&2
  echo "$ENV_HITS" >&2
  exit 1
fi

TMP_ARCHIVE="$ARCHIVE.tmp"

COPYFILE_DISABLE=1 tar -czf "$TMP_ARCHIVE" \
  --exclude="._*" \
  --exclude=".DS_Store" \
  -C "$DATA_ROOT" \
  baseline runtime artifacts users

mv "$TMP_ARCHIVE" "$ARCHIVE"

ARCHIVE="$ARCHIVE" MANIFEST="$MANIFEST" DATA_ROOT="$DATA_ROOT" TIMESTAMP="$TIMESTAMP" python3 - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

archive = Path(os.environ["ARCHIVE"])
manifest = Path(os.environ["MANIFEST"])
data_root = Path(os.environ["DATA_ROOT"])
timestamp = os.environ["TIMESTAMP"]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())

payload = {
    "ok": True,
    "kind": "ai_decision_studio_oracle_data_backup",
    "timestamp": timestamp,
    "data_root": str(data_root),
    "archive": str(archive),
    "archive_size_bytes": archive.stat().st_size,
    "archive_sha256": sha256(archive),
    "included_roots": ["baseline", "runtime", "artifacts", "users"],
    "excluded": [".env", ".env.*", "*.env", "backups"],
    "counts": {
        "baseline_files": count_files(data_root / "baseline"),
        "runtime_files": count_files(data_root / "runtime"),
        "artifacts_files": count_files(data_root / "artifacts"),
        "users_files": count_files(data_root / "users"),
    },
}
manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))
PY

echo
echo "OK: backup created"
echo "archive=$ARCHIVE"
echo "manifest=$MANIFEST"
