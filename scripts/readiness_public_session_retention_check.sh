#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 13.2 public session retention readiness =="

SCRIPT="scripts/cleanup_public_session_overlays.py"

if [[ ! -f "$SCRIPT" ]]; then
  echo "ERROR: missing $SCRIPT" >&2
  exit 1
fi

python3 -m py_compile "$SCRIPT"

python3 - <<'PY'
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

script = Path("scripts/cleanup_public_session_overlays.py").resolve()

def touch_tree(path: Path, timestamp: float) -> None:
    for item in sorted(path.rglob("*"), reverse=True):
        os.utime(item, (timestamp, timestamp))
    os.utime(path, (timestamp, timestamp))

with tempfile.TemporaryDirectory(prefix="ads_phase13_2_sessions_") as tmp:
    users_root = Path(tmp) / "users"
    public_root = users_root / "public_sessions"
    public_root.mkdir(parents=True, exist_ok=True)

    now = time.time()

    fresh = public_root / "sess_fresh"
    (fresh / "overlay" / "runs").mkdir(parents=True)
    (fresh / "overlay" / "runs" / "workflow_history.json").write_text("[]", encoding="utf-8")

    stale = public_root / "sess_stale"
    (stale / "overlay" / "runs").mkdir(parents=True)
    (stale / "overlay" / "runs" / "workflow_history.json").write_text("[]", encoding="utf-8")
    touch_tree(stale, now - 10 * 86400)

    oversized = public_root / "sess_oversized"
    (oversized / "overlay" / "artifacts").mkdir(parents=True)
    (oversized / "overlay" / "artifacts" / "big.bin").write_bytes(b"x" * (2 * 1024 * 1024 + 1))

    ignored = public_root / "not_a_session"
    ignored.mkdir()
    (ignored / "file.txt").write_text("ignore", encoding="utf-8")

    dry = subprocess.run(
        [
            "python3",
            str(script),
            "--users-root",
            str(users_root),
            "--ttl-days",
            "7",
            "--max-session-mb",
            "1",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    dry_payload = json.loads(dry.stdout)
    assert dry_payload["mode"] == "dry_run"
    assert dry_payload["summary"]["sessions_seen"] == 3
    assert dry_payload["summary"]["stale_sessions"] == 1
    assert stale.exists(), "dry-run must not delete stale session"

    applied = subprocess.run(
        [
            "python3",
            str(script),
            "--users-root",
            str(users_root),
            "--ttl-days",
            "7",
            "--max-session-mb",
            "1",
            "--apply",
            "--delete-oversized",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    applied_payload = json.loads(applied.stdout)

    assert applied_payload["mode"] == "apply"
    assert applied_payload["summary"]["deleted_sessions"] >= 2, applied_payload
    assert fresh.exists(), "fresh session must remain"
    assert not stale.exists(), "stale session should be deleted"
    assert not oversized.exists(), "oversized session should be deleted when --delete-oversized is used"
    assert ignored.exists(), "non sess_* directories must not be touched"

    print(json.dumps({
        "ok": True,
        "dry_run": dry_payload["summary"],
        "apply": applied_payload["summary"],
    }, indent=2, ensure_ascii=False))

print("OK: Phase 13.2 public session retention readiness passed")
PY
