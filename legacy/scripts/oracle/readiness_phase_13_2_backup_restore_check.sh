#!/usr/bin/env bash
set -euo pipefail

echo "== Phase 13.2 backup/restore readiness =="

BACKUP_SCRIPT="legacy/scripts/oracle/backup_oracle_data_root.sh"
RESTORE_SCRIPT="legacy/scripts/oracle/restore_oracle_data_root.sh"

bash -n "$BACKUP_SCRIPT"
bash -n "$RESTORE_SCRIPT"

python3 - <<'PY'
from __future__ import annotations

import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

repo = Path.cwd()
backup_script = repo / "scripts" / "backup_oracle_data_root.sh"
restore_script = repo / "scripts" / "restore_oracle_data_root.sh"

with tempfile.TemporaryDirectory(prefix="ads_backup_restore_") as tmp:
    tmp_root = Path(tmp)
    data_root = tmp_root / "data"
    backup_root = tmp_root / "backups"
    restore_root = tmp_root / "restored"

    for name in ["baseline", "runtime", "artifacts", "users", "backups"]:
        (data_root / name).mkdir(parents=True, exist_ok=True)

    (data_root / "baseline" / "baseline.txt").write_text("baseline-ok", encoding="utf-8")
    (data_root / "runtime" / "runtime.txt").write_text("runtime-ok", encoding="utf-8")
    (data_root / "artifacts" / "artifact.txt").write_text("artifact-ok", encoding="utf-8")
    (data_root / "users" / "user.txt").write_text("user-ok", encoding="utf-8")
    (data_root / "backups" / "should_not_be_in_archive.txt").write_text("exclude-me", encoding="utf-8")

    env = os.environ.copy()
    env["AI_DECISION_STUDIO_BACKUP_TIMESTAMP"] = "synthetic-restore-check"

    backup = subprocess.run(
        [str(backup_script), str(data_root), str(backup_root)],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )

    archive = backup_root / "ai-decision-studio-data-synthetic-restore-check.tar.gz"
    manifest = backup_root / "ai-decision-studio-data-synthetic-restore-check.manifest.json"

    assert archive.exists(), archive
    assert manifest.exists(), manifest

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()

    assert "baseline/baseline.txt" in names
    assert "runtime/runtime.txt" in names
    assert "artifacts/artifact.txt" in names
    assert "users/user.txt" in names
    assert not any(name.startswith("backups/") for name in names), names
    assert not any(name.startswith("._") or "/._" in name for name in names), names
    assert not any(name.endswith(".DS_Store") for name in names), names

    restore = subprocess.run(
        [str(restore_script), str(archive), str(restore_root)],
        check=True,
        text=True,
        capture_output=True,
    )

    assert (restore_root / "baseline" / "baseline.txt").read_text(encoding="utf-8") == "baseline-ok"
    assert (restore_root / "runtime" / "runtime.txt").read_text(encoding="utf-8") == "runtime-ok"
    assert (restore_root / "artifacts" / "artifact.txt").read_text(encoding="utf-8") == "artifact-ok"
    assert (restore_root / "users" / "user.txt").read_text(encoding="utf-8") == "user-ok"
    assert (restore_root / "backups").exists()

    print(json.dumps({
        "ok": True,
        "archive": str(archive),
        "manifest": str(manifest),
        "tar_entries": names,
        "backup_stdout_tail": backup.stdout.splitlines()[-5:],
        "restore_stdout_tail": restore.stdout.splitlines()[-5:],
    }, indent=2, ensure_ascii=False))

print("OK: Phase 13.2 backup/restore readiness passed")
PY
