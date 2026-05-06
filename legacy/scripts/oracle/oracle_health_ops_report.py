#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_REQUIRED_ROOTS = ("baseline", "runtime", "artifacts", "users", "backups")


def _path_size_bytes(path: Path) -> int:
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


def _http_health(base_url: str, timeout: int) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/health"
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw or "{}")
            except Exception:
                body = {"raw": raw[:1000]}
            return {
                "ok": resp.status == 200 and bool(body.get("ok")),
                "status": resp.status,
                "url": url,
                "latency_s": round(time.time() - started, 4),
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "status": exc.code,
            "url": url,
            "latency_s": round(time.time() - started, 4),
            "error": raw[:1000],
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "latency_s": round(time.time() - started, 4),
            "error": str(exc),
        }


def _parse_compose_ps(text: str) -> list[dict[str, Any]]:
    raw = text.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            return [parsed]
    except Exception:
        pass

    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except Exception:
            continue
    return rows


def _docker_compose_status(*, compose_file: str, compose_project: str) -> dict[str, Any]:
    cmd = [
        "docker",
        "compose",
        "-p",
        compose_project,
        "-f",
        compose_file,
        "ps",
        "--format",
        "json",
    ]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    except Exception as exc:
        return {
            "ok": False,
            "command": cmd,
            "error": str(exc),
            "services": [],
        }

    services = _parse_compose_ps(proc.stdout)
    expected = {"product-api", "frontend"}
    by_service = {
        str(item.get("Service") or item.get("service") or ""): item
        for item in services
        if isinstance(item, dict)
    }

    missing = sorted(expected - set(by_service))
    unhealthy = []

    for service in sorted(expected & set(by_service)):
        item = by_service[service]
        state = str(item.get("State") or item.get("state") or item.get("Status") or "").lower()
        health = str(item.get("Health") or item.get("health") or "").lower()
        status = str(item.get("Status") or item.get("status") or "").lower()

        running = "running" in state or "up" in status
        healthy = not health or health == "healthy"

        if not running or not healthy:
            unhealthy.append({
                "service": service,
                "state": state,
                "health": health,
                "status": status,
            })

    return {
        "ok": proc.returncode == 0 and not missing and not unhealthy,
        "command": cmd,
        "returncode": proc.returncode,
        "missing": missing,
        "unhealthy": unhealthy,
        "services": services,
        "stderr": proc.stderr.strip()[:1000],
    }


def _latest_backup(backups_root: Path, max_backup_age_hours: float) -> dict[str, Any]:
    backups = sorted(backups_root.glob("ai-decision-studio-data-*.tar.gz"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    if not backups:
        return {
            "ok": False,
            "found": False,
            "path": None,
            "age_hours": None,
            "max_age_hours": max_backup_age_hours,
        }

    latest = backups[0]
    age_hours = (time.time() - latest.stat().st_mtime) / 3600
    return {
        "ok": age_hours <= max_backup_age_hours,
        "found": True,
        "path": str(latest),
        "size_bytes": latest.stat().st_size,
        "age_hours": round(age_hours, 3),
        "max_age_hours": max_backup_age_hours,
        "count": len(backups),
    }


def _public_sessions_report(users_root: Path, ttl_days: int, max_session_mb: int) -> dict[str, Any]:
    public_root = users_root / "public_sessions"
    limit_bytes = max(0, max_session_mb) * 1024 * 1024
    ttl_seconds = max(0, ttl_days) * 24 * 60 * 60

    sessions = []
    stale = 0
    oversized = 0
    total_size = 0

    if public_root.exists():
        for session_dir in sorted(public_root.iterdir()):
            if not session_dir.is_dir() or not session_dir.name.startswith("sess_"):
                continue
            size = _path_size_bytes(session_dir)
            latest = _latest_mtime(session_dir)
            age_days = ((time.time() - latest) / 86400) if latest else None
            is_stale = bool(latest and ttl_seconds > 0 and (time.time() - latest) > ttl_seconds)
            is_oversized = bool(limit_bytes > 0 and size > limit_bytes)

            stale += 1 if is_stale else 0
            oversized += 1 if is_oversized else 0
            total_size += size

            sessions.append({
                "session_id": session_dir.name,
                "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 3),
                "age_days": round(age_days, 3) if age_days is not None else None,
                "stale": is_stale,
                "oversized": is_oversized,
            })

    return {
        "ok": oversized == 0,
        "public_sessions_root": str(public_root),
        "sessions_seen": len(sessions),
        "stale_sessions": stale,
        "oversized_sessions": oversized,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 3),
        "policy": {
            "ttl_days": ttl_days,
            "max_session_mb": max_session_mb,
        },
        "sessions": sorted(sessions, key=lambda item: int(item["size_bytes"]), reverse=True)[:20],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    data_root = Path(args.data_root).expanduser().resolve(strict=False)
    base_url = args.base_url.rstrip("/")

    checks: dict[str, bool] = {}
    warnings: list[str] = []
    errors: list[str] = []

    checks["data_root_exists"] = data_root.exists()
    if not data_root.exists():
        errors.append(f"data_root does not exist: {data_root}")

    required_dirs = {name: (data_root / name).exists() for name in DEFAULT_REQUIRED_ROOTS}
    checks["required_dirs_exist"] = all(required_dirs.values())
    if not checks["required_dirs_exist"]:
        errors.append(f"missing required dirs: {[name for name, ok in required_dirs.items() if not ok]}")

    root_sizes = {
        name: _path_size_bytes(data_root / name)
        for name in DEFAULT_REQUIRED_ROOTS
        if (data_root / name).exists()
    }

    disk_payload: dict[str, Any] = {}
    if data_root.exists():
        usage = shutil.disk_usage(data_root)
        used_percent = (usage.used / usage.total) * 100 if usage.total else 0.0
        disk_payload = {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "used_percent": round(used_percent, 2),
            "max_used_percent": args.max_disk_used_percent,
        }
        checks["disk_below_threshold"] = used_percent <= args.max_disk_used_percent
        if not checks["disk_below_threshold"]:
            errors.append(f"disk usage too high: {used_percent:.2f}%")
    else:
        checks["disk_below_threshold"] = False

    backup_payload = _latest_backup(data_root / "backups", args.max_backup_age_hours) if data_root.exists() else {"ok": False}
    checks["latest_backup_recent"] = bool(backup_payload.get("ok"))
    if not checks["latest_backup_recent"]:
        warnings.append("latest backup is missing or older than threshold")

    sessions_payload = _public_sessions_report(
        data_root / "users",
        ttl_days=args.public_session_ttl_days,
        max_session_mb=args.public_session_max_mb,
    ) if data_root.exists() else {"ok": False}
    checks["public_sessions_within_quota"] = bool(sessions_payload.get("ok"))
    if not checks["public_sessions_within_quota"]:
        errors.append("one or more public sessions exceed quota")
    if int(sessions_payload.get("stale_sessions") or 0) > 0:
        warnings.append("one or more public sessions are stale and should be cleaned")

    http_payload = None
    if not args.skip_http:
        http_payload = _http_health(base_url, timeout=args.http_timeout)
        checks["http_health_ok"] = bool(http_payload.get("ok"))
        if not checks["http_health_ok"]:
            errors.append("http health check failed")

    docker_payload = None
    if not args.skip_docker:
        docker_payload = _docker_compose_status(
            compose_file=args.compose_file,
            compose_project=args.compose_project,
        )
        checks["docker_compose_services_ok"] = bool(docker_payload.get("ok"))
        if not checks["docker_compose_services_ok"]:
            warnings.append("docker compose service status is not fully healthy")

    ok = not errors and checks.get("data_root_exists") and checks.get("required_dirs_exist") and checks.get("disk_below_threshold")

    return {
        "ok": bool(ok),
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "config": {
            "data_root": str(data_root),
            "base_url": base_url,
            "compose_file": args.compose_file,
            "compose_project": args.compose_project,
            "max_disk_used_percent": args.max_disk_used_percent,
            "max_backup_age_hours": args.max_backup_age_hours,
            "public_session_ttl_days": args.public_session_ttl_days,
            "public_session_max_mb": args.public_session_max_mb,
        },
        "root_sizes_bytes": root_sizes,
        "disk": disk_payload,
        "backup": backup_payload,
        "public_sessions": sessions_payload,
        "http_health": http_payload,
        "docker_compose": docker_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Decision Studio Oracle ops health report.")
    parser.add_argument("--data-root", default=os.environ.get("AI_DECISION_STUDIO_ORACLE_DATA_ROOT", "/opt/ai-decision-studio/data"))
    parser.add_argument("--base-url", default=os.environ.get("AI_DECISION_STUDIO_READINESS_BASE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--compose-file", default=os.environ.get("AI_DECISION_STUDIO_ORACLE_COMPOSE_FILE", "docker-compose.oracle-like.yml"))
    parser.add_argument("--compose-project", default=os.environ.get("COMPOSE_PROJECT_NAME", "ai-decision-studio"))
    parser.add_argument("--max-disk-used-percent", type=float, default=float(os.environ.get("AI_DECISION_STUDIO_MAX_DISK_USED_PERCENT", "85")))
    parser.add_argument("--max-backup-age-hours", type=float, default=float(os.environ.get("AI_DECISION_STUDIO_MAX_BACKUP_AGE_HOURS", "48")))
    parser.add_argument("--public-session-ttl-days", type=int, default=int(os.environ.get("AI_DECISION_STUDIO_PUBLIC_SESSION_TTL_DAYS", "7")))
    parser.add_argument("--public-session-max-mb", type=int, default=int(os.environ.get("AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB", "100")))
    parser.add_argument("--http-timeout", type=int, default=10)
    parser.add_argument("--skip-http", action="store_true")
    parser.add_argument("--skip-docker", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
