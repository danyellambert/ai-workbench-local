#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_TTL_DAYS = 7
DEFAULT_MAX_SESSION_MB = 250


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _size_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                total += item.stat().st_size
        except OSError:
            continue
    return total


def _latest_mtime(path: Path) -> float:
    latest = 0.0
    if not path.exists():
        return latest
    try:
        latest = max(latest, path.stat().st_mtime)
    except OSError:
        pass
    for item in path.rglob("*"):
        try:
            latest = max(latest, item.stat().st_mtime)
        except OSError:
            continue
    return latest


def _default_users_root() -> Path:
    value = (
        os.environ.get("AI_DECISION_STUDIO_USERS_ROOT")
        or os.environ.get("APP_USERS_ROOT")
        or "/opt/ai-decision-studio/data/users"
    )
    return Path(value).expanduser()


def _session_dirs(public_sessions_root: Path) -> list[Path]:
    if not public_sessions_root.exists():
        return []
    sessions: list[Path] = []
    for item in public_sessions_root.iterdir():
        if item.is_dir() and item.name.startswith("sess_"):
            sessions.append(item)
    return sorted(sessions, key=lambda p: p.name)


def build_report(
    *,
    users_root: Path,
    ttl_days: int,
    max_session_mb: int,
    apply: bool,
    delete_oversized: bool,
) -> dict[str, Any]:
    users_root = users_root.expanduser().resolve(strict=False)
    public_sessions_root = users_root / "public_sessions"
    now = time.time()
    ttl_seconds = max(0, ttl_days) * 24 * 60 * 60
    max_session_bytes = max(0, max_session_mb) * 1024 * 1024

    report: dict[str, Any] = {
        "ok": True,
        "mode": "apply" if apply else "dry_run",
        "users_root": str(users_root),
        "public_sessions_root": str(public_sessions_root),
        "policy": {
            "ttl_days": ttl_days,
            "max_session_mb": max_session_mb,
            "delete_oversized": delete_oversized,
        },
        "summary": {
            "sessions_seen": 0,
            "stale_sessions": 0,
            "oversized_sessions": 0,
            "delete_candidates": 0,
            "deleted_sessions": 0,
            "kept_sessions": 0,
            "total_size_bytes": 0,
            "deleted_size_bytes": 0,
        },
        "sessions": [],
        "errors": [],
    }

    if not public_sessions_root.exists():
        return report

    if not _is_relative_to(public_sessions_root, users_root):
        report["ok"] = False
        report["errors"].append("public_sessions_root is outside users_root")
        return report

    for session_dir in _session_dirs(public_sessions_root):
        session_resolved = session_dir.resolve(strict=False)
        if not _is_relative_to(session_resolved, public_sessions_root):
            report["errors"].append(f"Skipping unsafe session path: {session_dir}")
            continue

        latest = _latest_mtime(session_dir)
        age_seconds = max(0.0, now - latest) if latest else 0.0
        age_days = age_seconds / 86400 if latest else None
        size = _size_bytes(session_dir)

        reasons: list[str] = []
        if latest and ttl_seconds > 0 and age_seconds > ttl_seconds:
            reasons.append("stale")
        if max_session_bytes > 0 and size > max_session_bytes:
            reasons.append("oversized")

        should_delete = False
        if "stale" in reasons:
            should_delete = True
        if "oversized" in reasons and delete_oversized:
            should_delete = True

        entry: dict[str, Any] = {
            "session_id": session_dir.name,
            "path": str(session_dir),
            "size_bytes": size,
            "size_mb": round(size / 1024 / 1024, 3),
            "latest_mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(latest)) if latest else None,
            "age_days": round(age_days, 3) if age_days is not None else None,
            "has_overlay": (session_dir / "overlay").exists(),
            "reasons": reasons,
            "action": "delete" if should_delete else "keep",
            "deleted": False,
        }

        report["summary"]["sessions_seen"] += 1
        report["summary"]["total_size_bytes"] += size
        if "stale" in reasons:
            report["summary"]["stale_sessions"] += 1
        if "oversized" in reasons:
            report["summary"]["oversized_sessions"] += 1
        if should_delete:
            report["summary"]["delete_candidates"] += 1
        else:
            report["summary"]["kept_sessions"] += 1

        if apply and should_delete:
            try:
                shutil.rmtree(session_dir)
                entry["deleted"] = True
                report["summary"]["deleted_sessions"] += 1
                report["summary"]["deleted_size_bytes"] += size
            except Exception as exc:  # defensive ops script
                report["ok"] = False
                report["errors"].append(f"Failed to delete {session_dir}: {exc}")

        report["sessions"].append(entry)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean old public session overlays safely.")
    parser.add_argument("--users-root", default=str(_default_users_root()), help="Path to AI_DECISION_STUDIO_USERS_ROOT.")
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS, help="Delete sessions older than this when --apply is used.")
    parser.add_argument("--max-session-mb", type=int, default=DEFAULT_MAX_SESSION_MB, help="Report sessions larger than this size.")
    parser.add_argument("--delete-oversized", action="store_true", help="Delete oversized sessions when --apply is used.")
    parser.add_argument("--apply", action="store_true", help="Actually delete candidates. Default is dry-run.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report only.")
    args = parser.parse_args()

    report = build_report(
        users_root=Path(args.users_root),
        ttl_days=args.ttl_days,
        max_session_mb=args.max_session_mb,
        apply=args.apply,
        delete_oversized=args.delete_oversized,
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
