#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SESSION_RE = re.compile(r"^sess_[A-Za-z0-9_-]+$")


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def resolve_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def data_root_from_env() -> Path:
    value = os.environ.get("AI_DECISION_STUDIO_DATA_ROOT")
    if value:
        return resolve_path(value)
    return resolve_path("/opt/ai-decision-studio/data")


def users_root_from_env() -> Path:
    for key in ("AI_DECISION_STUDIO_USERS_ROOT", "AI_DECISION_STUDIO_USER_OVERLAY_ROOT"):
        value = os.environ.get(key)
        if value:
            return resolve_path(value)
    return data_root_from_env() / "users"


def is_safe_public_session_dir(session_dir: Path, public_sessions_root: Path) -> bool:
    try:
        session_resolved = session_dir.resolve()
        root_resolved = public_sessions_root.resolve()
        rel = session_resolved.relative_to(root_resolved)
    except Exception:
        return False

    if len(rel.parts) != 1:
        return False

    if not SESSION_RE.match(rel.parts[0]):
        return False

    if session_dir.is_symlink():
        return False

    return True


def assert_safe_roots(data_root: Path, users_root: Path, public_sessions_root: Path) -> None:
    data_root = data_root.resolve()
    users_root = users_root.resolve()
    public_sessions_root = public_sessions_root.resolve()

    protected = [
        data_root / "baseline",
        data_root / "runtime",
        data_root / "artifacts",
        data_root / "backups",
        resolve_path(os.environ.get("AI_DECISION_STUDIO_BASELINE_ROOT", str(data_root / "baseline"))),
        resolve_path(os.environ.get("AI_DECISION_STUDIO_RUNTIME_ROOT", str(data_root / "runtime"))),
        resolve_path(os.environ.get("AI_DECISION_STUDIO_ARTIFACT_ROOT", str(data_root / "artifacts"))),
    ]

    try:
        public_sessions_root.relative_to(users_root)
    except ValueError as exc:
        raise RuntimeError(
            f"public_sessions_root must live under users_root: public_sessions_root={public_sessions_root} users_root={users_root}"
        ) from exc

    for protected_root in protected:
        protected_root = protected_root.resolve()
        if public_sessions_root == protected_root:
            raise RuntimeError(f"Refusing to use protected root as public session root: {protected_root}")
        try:
            public_sessions_root.relative_to(protected_root)
            raise RuntimeError(f"Refusing public session root inside protected global path: {protected_root}")
        except ValueError:
            pass


def latest_mtime(path: Path) -> float:
    latest = path.lstat().st_mtime
    for child in path.rglob("*"):
        try:
            latest = max(latest, child.lstat().st_mtime)
        except FileNotFoundError:
            continue
    return latest


def summarize_tree(path: Path) -> dict[str, Any]:
    files = 0
    dirs = 0
    symlinks = 0
    bytes_total = 0

    for child in path.rglob("*"):
        try:
            stat = child.lstat()
        except FileNotFoundError:
            continue

        if child.is_symlink():
            symlinks += 1
        elif child.is_dir():
            dirs += 1
        elif child.is_file():
            files += 1
            bytes_total += stat.st_size

    return {
        "path": str(path),
        "files": files,
        "dirs": dirs,
        "symlinks": symlinks,
        "bytes": bytes_total,
    }


def remove_tree(session_dir: Path, public_sessions_root: Path, use_sudo: bool) -> None:
    if not is_safe_public_session_dir(session_dir, public_sessions_root):
        raise RuntimeError(f"Refusing to remove unsafe path: {session_dir}")

    try:
        shutil.rmtree(session_dir)
        return
    except PermissionError:
        if not use_sudo:
            raise

    if not is_safe_public_session_dir(session_dir, public_sessions_root):
        raise RuntimeError(f"Refusing sudo remove for unsafe path: {session_dir}")

    subprocess.run(
        ["sudo", "rm", "-rf", "--one-file-system", str(session_dir)],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean expired AI Decision Studio public demo sessions without touching baseline/global/admin state."
    )
    parser.add_argument(
        "--ttl-hours",
        type=float,
        default=float(os.environ.get("AI_DECISION_STUDIO_PUBLIC_SESSION_TTL_HOURS", "48")),
    )
    parser.add_argument(
        "--users-root",
        default=os.environ.get("AI_DECISION_STUDIO_USERS_ROOT"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=env_bool("AI_DECISION_STUDIO_PUBLIC_CLEANUP_DRY_RUN", True),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete expired public session directories.",
    )
    parser.add_argument(
        "--use-sudo",
        action="store_true",
        default=env_bool("AI_DECISION_STUDIO_PUBLIC_CLEANUP_USE_SUDO", True),
        help="Use sudo fallback when expired session dirs are owned by container/root.",
    )
    args = parser.parse_args()

    data_root = data_root_from_env()
    users_root = resolve_path(args.users_root) if args.users_root else users_root_from_env()
    public_sessions_root = users_root / "public_sessions"

    assert_safe_roots(data_root, users_root, public_sessions_root)

    now = time.time()
    cutoff = now - (args.ttl_hours * 3600)
    dry_run = False if args.apply else bool(args.dry_run)

    print("== Public demo session cleanup ==")
    print(f"data_root={data_root}")
    print(f"users_root={users_root}")
    print(f"public_sessions_root={public_sessions_root}")
    print(f"ttl_hours={args.ttl_hours}")
    print(f"dry_run={dry_run}")
    print(f"use_sudo={args.use_sudo}")

    if not public_sessions_root.exists():
        report = {
            "ok": True,
            "dry_run": dry_run,
            "ttl_hours": args.ttl_hours,
            "public_sessions_root": str(public_sessions_root),
            "expired_count": 0,
            "kept_count": 0,
            "removed": [],
            "expired": [],
            "kept": [],
        }
        print("OK: public_sessions_root does not exist; nothing to clean.")
        print(json.dumps(report, indent=2))
        return 0

    expired: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    skipped: list[str] = []

    for session_dir in sorted(public_sessions_root.iterdir()):
        if not session_dir.exists():
            continue

        if not session_dir.is_dir() or not is_safe_public_session_dir(session_dir, public_sessions_root):
            skipped.append(str(session_dir))
            print(f"SKIP non-session/unsafe path: {session_dir}")
            continue

        mtime = latest_mtime(session_dir)
        age_hours = (now - mtime) / 3600
        item = summarize_tree(session_dir)
        item["age_hours"] = round(age_hours, 2)
        item["expired"] = mtime < cutoff

        if item["expired"]:
            expired.append(item)
        else:
            kept.append(item)

    removed: list[str] = []

    for item in expired:
        session_dir = Path(item["path"])
        print(
            "EXPIRED "
            f"age_hours={item['age_hours']} "
            f"files={item['files']} "
            f"bytes={item['bytes']} "
            f"path={session_dir}"
        )

        if dry_run:
            continue

        remove_tree(session_dir, public_sessions_root, use_sudo=args.use_sudo)
        removed.append(str(session_dir))

    report = {
        "ok": True,
        "dry_run": dry_run,
        "ttl_hours": args.ttl_hours,
        "public_sessions_root": str(public_sessions_root),
        "expired_count": len(expired),
        "kept_count": len(kept),
        "skipped_count": len(skipped),
        "removed": removed,
        "expired": expired,
        "kept": kept,
        "skipped": skipped,
    }

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
