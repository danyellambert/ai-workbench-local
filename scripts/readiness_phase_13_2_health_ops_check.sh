#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 13.2 health ops readiness =="

SCRIPT="scripts/oracle_health_ops_report.py"

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

script = Path("scripts/oracle_health_ops_report.py").resolve()

with tempfile.TemporaryDirectory(prefix="ads_health_ops_") as tmp:
    data_root = Path(tmp) / "data"

    for name in ["baseline", "runtime", "artifacts", "users", "backups"]:
        (data_root / name).mkdir(parents=True, exist_ok=True)

    (data_root / "baseline" / "baseline.txt").write_text("baseline-ok", encoding="utf-8")
    (data_root / "runtime" / "runtime.txt").write_text("runtime-ok", encoding="utf-8")
    (data_root / "artifacts" / "artifact.txt").write_text("artifact-ok", encoding="utf-8")
    (data_root / "users" / "public_sessions" / "sess_test" / "overlay").mkdir(parents=True)
    (data_root / "users" / "public_sessions" / "sess_test" / "overlay" / "session_state.json").write_text("{}", encoding="utf-8")

    backup = data_root / "backups" / "ai-decision-studio-data-synthetic.tar.gz"
    backup.write_bytes(b"fake-backup")
    os.utime(backup, (time.time(), time.time()))

    proc = subprocess.run(
        [
            "python3",
            str(script),
            "--data-root",
            str(data_root),
            "--base-url",
            "http://127.0.0.1:1",
            "--skip-http",
            "--skip-docker",
            "--max-backup-age-hours",
            "48",
            "--public-session-max-mb",
            "10",
            "--public-session-ttl-days",
            "7",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(proc.stdout)

    assert payload["ok"] is True, payload
    assert payload["checks"]["data_root_exists"] is True
    assert payload["checks"]["required_dirs_exist"] is True
    assert payload["checks"]["disk_below_threshold"] is True
    assert payload["checks"]["latest_backup_recent"] is True
    assert payload["checks"]["public_sessions_within_quota"] is True
    assert payload["public_sessions"]["sessions_seen"] == 1

    print(json.dumps({
        "ok": True,
        "checks": payload["checks"],
        "public_sessions": payload["public_sessions"],
        "backup": payload["backup"],
    }, indent=2, ensure_ascii=False))

print("OK: Phase 13.2 health ops readiness passed")
PY
