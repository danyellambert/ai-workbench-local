from __future__ import annotations

import json
import hashlib
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_eval_store(path: Path) -> None:
    with _connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                suite_name TEXT NOT NULL,
                task_type TEXT,
                case_name TEXT,
                provider TEXT,
                model TEXT,
                status TEXT NOT NULL,
                score REAL,
                max_score REAL,
                quality_score REAL,
                overall_confidence REAL,
                latency_s REAL,
                needs_review INTEGER NOT NULL DEFAULT 0,
                context_strategy TEXT,
                run_key TEXT,
                metrics_json TEXT NOT NULL DEFAULT '{}',
                reasons_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(eval_runs)").fetchall()
        }
        if "run_key" not in columns:
            connection.execute("ALTER TABLE eval_runs ADD COLUMN run_key TEXT")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_eval_runs_suite_created_at ON eval_runs(suite_name, created_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_eval_runs_task_status ON eval_runs(task_type, status)"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_eval_runs_run_key ON eval_runs(run_key)"
        )


def _build_run_key(payload: dict[str, Any]) -> str:
    canonical = {
        "created_at": payload.get("created_at"),
        "suite_name": payload.get("suite_name"),
        "task_type": payload.get("task_type"),
        "case_name": payload.get("case_name"),
        "provider": payload.get("provider"),
        "model": payload.get("model"),
        "status": payload.get("status"),
        "score": payload.get("score"),
        "max_score": payload.get("max_score"),
        "quality_score": payload.get("quality_score"),
        "overall_confidence": payload.get("overall_confidence"),
        "latency_s": payload.get("latency_s"),
        "needs_review": payload.get("needs_review"),
        "context_strategy": payload.get("context_strategy"),
        "metrics_json": payload.get("metrics_json"),
        "reasons_json": payload.get("reasons_json"),
        "metadata_json": payload.get("metadata_json"),
    }
    serialized = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def append_eval_run(path: Path, entry: dict[str, Any]) -> int:
    ensure_eval_store(path)
    payload = {
        "created_at": str(entry.get("created_at") or datetime.now().isoformat()),
        "suite_name": str(entry.get("suite_name") or "eval").strip() or "eval",
        "task_type": str(entry.get("task_type") or "").strip() or None,
        "case_name": str(entry.get("case_name") or "").strip() or None,
        "provider": str(entry.get("provider") or "").strip() or None,
        "model": str(entry.get("model") or "").strip() or None,
        "status": str(entry.get("status") or "UNKNOWN").strip() or "UNKNOWN",
        "score": float(entry.get("score")) if isinstance(entry.get("score"), (int, float)) else None,
        "max_score": float(entry.get("max_score")) if isinstance(entry.get("max_score"), (int, float)) else None,
        "quality_score": float(entry.get("quality_score")) if isinstance(entry.get("quality_score"), (int, float)) else None,
        "overall_confidence": float(entry.get("overall_confidence")) if isinstance(entry.get("overall_confidence"), (int, float)) else None,
        "latency_s": float(entry.get("latency_s")) if isinstance(entry.get("latency_s"), (int, float)) else None,
        "needs_review": 1 if bool(entry.get("needs_review")) else 0,
        "context_strategy": str(entry.get("context_strategy") or "").strip() or None,
        "metrics_json": json.dumps(entry.get("metrics") or {}, ensure_ascii=False),
        "reasons_json": json.dumps(entry.get("reasons") or [], ensure_ascii=False),
        "metadata_json": json.dumps(entry.get("metadata") or {}, ensure_ascii=False),
    }
    payload["run_key"] = str(entry.get("run_key") or _build_run_key(payload))
    with _connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO eval_runs (
                created_at,
                suite_name,
                task_type,
                case_name,
                provider,
                model,
                status,
                score,
                max_score,
                quality_score,
                overall_confidence,
                latency_s,
                needs_review,
                context_strategy,
                run_key,
                metrics_json,
                reasons_json,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["created_at"],
                payload["suite_name"],
                payload["task_type"],
                payload["case_name"],
                payload["provider"],
                payload["model"],
                payload["status"],
                payload["score"],
                payload["max_score"],
                payload["quality_score"],
                payload["overall_confidence"],
                payload["latency_s"],
                payload["needs_review"],
                payload["context_strategy"],
                payload["run_key"],
                payload["metrics_json"],
                payload["reasons_json"],
                payload["metadata_json"],
            ),
        )
        return int(cursor.lastrowid)


def load_eval_runs(
    path: Path,
    *,
    suite_name: str | None = None,
    task_type: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    clauses: list[str] = []
    params: list[Any] = []
    if suite_name:
        clauses.append("suite_name = ?")
        params.append(suite_name)
    if task_type:
        clauses.append("task_type = ?")
        params.append(task_type)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_clause = "LIMIT ?" if isinstance(limit, int) and limit > 0 else ""
    if limit_clause:
        params.append(limit)

    query = f"""
        SELECT *
        FROM eval_runs
        {where_clause}
        ORDER BY datetime(created_at) DESC, id DESC
        {limit_clause}
    """
    with _connect(path) as connection:
        rows = connection.execute(query, params).fetchall()

    entries: list[dict[str, Any]] = []
    for row in rows:
        entries.append(
            {
                "id": int(row["id"]),
                "created_at": row["created_at"],
                "suite_name": row["suite_name"],
                "task_type": row["task_type"],
                "case_name": row["case_name"],
                "provider": row["provider"],
                "model": row["model"],
                "status": row["status"],
                "score": row["score"],
                "max_score": row["max_score"],
                "quality_score": row["quality_score"],
                "overall_confidence": row["overall_confidence"],
                "latency_s": row["latency_s"],
                "needs_review": bool(row["needs_review"]),
                "context_strategy": row["context_strategy"],
                "run_key": row["run_key"],
                "metrics": json.loads(row["metrics_json"] or "{}"),
                "reasons": json.loads(row["reasons_json"] or "[]"),
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
        )
    return entries


def summarize_eval_runs(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {
            "total_runs": 0,
            "status_counts": {},
            "suite_counts": {},
            "task_counts": {},
            "pass_rate": 0.0,
            "warn_rate": 0.0,
            "fail_rate": 0.0,
            "avg_score_ratio": 0.0,
            "avg_latency_s": 0.0,
            "needs_review_rate": 0.0,
            "suite_leaderboard": [],
            "task_leaderboard": [],
        }

    status_counter: Counter[str] = Counter()
    suite_counter: Counter[str] = Counter()
    task_counter: Counter[str] = Counter()
    score_ratios: list[float] = []
    latencies: list[float] = []
    needs_review_count = 0
    suite_metrics: dict[str, dict[str, float | int]] = {}
    task_metrics: dict[str, dict[str, float | int]] = {}

    def _accumulate(target: dict[str, dict[str, float | int]], key: str, entry: dict[str, Any]) -> None:
        if not key:
            return
        bucket = target.setdefault(
            key,
            {
                "total_runs": 0,
                "pass_count": 0,
                "warn_count": 0,
                "fail_count": 0,
                "score_ratio_sum": 0.0,
                "score_ratio_count": 0,
                "latency_sum": 0.0,
                "latency_count": 0,
            },
        )
        bucket["total_runs"] = int(bucket.get("total_runs") or 0) + 1
        status = str(entry.get("status") or "UNKNOWN").upper()
        if status == "PASS":
            bucket["pass_count"] = int(bucket.get("pass_count") or 0) + 1
        elif status == "WARN":
            bucket["warn_count"] = int(bucket.get("warn_count") or 0) + 1
        elif status == "FAIL":
            bucket["fail_count"] = int(bucket.get("fail_count") or 0) + 1
        score = entry.get("score")
        max_score = entry.get("max_score")
        if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and float(max_score) > 0:
            bucket["score_ratio_sum"] = float(bucket.get("score_ratio_sum") or 0.0) + (float(score) / float(max_score))
            bucket["score_ratio_count"] = int(bucket.get("score_ratio_count") or 0) + 1
        latency_s = entry.get("latency_s")
        if isinstance(latency_s, (int, float)):
            bucket["latency_sum"] = float(bucket.get("latency_sum") or 0.0) + float(latency_s)
            bucket["latency_count"] = int(bucket.get("latency_count") or 0) + 1

    for entry in entries:
        status = str(entry.get("status") or "UNKNOWN").upper()
        suite_name = str(entry.get("suite_name") or "eval")
        task_type = str(entry.get("task_type") or "unknown")
        status_counter[status] += 1
        suite_counter[suite_name] += 1
        task_counter[task_type] += 1
        if bool(entry.get("needs_review")):
            needs_review_count += 1

        score = entry.get("score")
        max_score = entry.get("max_score")
        if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and float(max_score) > 0:
            score_ratios.append(round(float(score) / float(max_score), 4))
        latency_s = entry.get("latency_s")
        if isinstance(latency_s, (int, float)):
            latencies.append(float(latency_s))

        _accumulate(suite_metrics, suite_name, entry)
        _accumulate(task_metrics, task_type, entry)

    def _leaderboard_from_metrics(metrics: dict[str, dict[str, float | int]], key_name: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key, values in metrics.items():
            total_runs = int(values.get("total_runs") or 0)
            score_ratio_count = int(values.get("score_ratio_count") or 0)
            latency_count = int(values.get("latency_count") or 0)
            rows.append(
                {
                    key_name: key,
                    "total_runs": total_runs,
                    "pass_rate": round(int(values.get("pass_count") or 0) / max(total_runs, 1), 3),
                    "warn_rate": round(int(values.get("warn_count") or 0) / max(total_runs, 1), 3),
                    "fail_rate": round(int(values.get("fail_count") or 0) / max(total_runs, 1), 3),
                    "avg_score_ratio": round(float(values.get("score_ratio_sum") or 0.0) / max(score_ratio_count, 1), 3) if score_ratio_count else 0.0,
                    "avg_latency_s": round(float(values.get("latency_sum") or 0.0) / max(latency_count, 1), 3) if latency_count else 0.0,
                }
            )
        rows.sort(
            key=lambda item: (
                -float(item.get("pass_rate") or 0.0),
                -float(item.get("avg_score_ratio") or 0.0),
                float(item.get("avg_latency_s") or 10**9),
            )
        )
        return rows

    total_runs = len(entries)
    return {
        "total_runs": total_runs,
        "status_counts": dict(status_counter),
        "suite_counts": dict(suite_counter),
        "task_counts": dict(task_counter),
        "pass_rate": round(status_counter.get("PASS", 0) / max(total_runs, 1), 3),
        "warn_rate": round(status_counter.get("WARN", 0) / max(total_runs, 1), 3),
        "fail_rate": round(status_counter.get("FAIL", 0) / max(total_runs, 1), 3),
        "avg_score_ratio": round(sum(score_ratios) / max(len(score_ratios), 1), 3) if score_ratios else 0.0,
        "avg_latency_s": round(sum(latencies) / max(len(latencies), 1), 3) if latencies else 0.0,
        "needs_review_rate": round(needs_review_count / max(total_runs, 1), 3),
        "suite_leaderboard": _leaderboard_from_metrics(suite_metrics, "suite_name"),
        "task_leaderboard": _leaderboard_from_metrics(task_metrics, "task_type"),
    }


def clear_eval_store(path: Path) -> None:
    if path.exists():
        path.unlink()