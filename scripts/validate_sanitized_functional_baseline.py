from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path


ABS_PATH_RE = re.compile(r"""(?:/Users/[^"'\n\r,}\]]*|/private/[^"'\n\r,}\]]*|/var/folders/[^"'\n\r,}\]]*)""")
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|passwd|authorization|bearer)\s*[:=]")
TEXT_SUFFIXES = {".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".env"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def count_json(path: Path, *keys: str) -> int:
    payload = load_json(path)
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


def sqlite_count(path: Path, table: str) -> int:
    if not path.exists():
        return 0
    with sqlite3.connect(path) as conn:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int(row[0]) if row else 0


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def scan_text(root: Path) -> dict:
    abs_findings = []
    secret_findings = []

    for path in iter_text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        abs_hits = sorted(set(ABS_PATH_RE.findall(text)))
        if abs_hits:
            abs_findings.append({"path": str(path.relative_to(root)), "hits": abs_hits[:10]})
        if SECRET_RE.search(text):
            secret_findings.append({"path": str(path.relative_to(root))})

    return {
        "absolute_path_findings": abs_findings,
        "secret_pattern_findings": secret_findings,
    }


def validate(baseline_dir: Path) -> dict:
    manifest_path = baseline_dir / "manifest.json"
    baseline_root = baseline_dir / "baseline"

    if not manifest_path.exists():
        raise SystemExit(f"Missing manifest: {manifest_path}")
    if not baseline_root.exists():
        raise SystemExit(f"Missing baseline root: {baseline_root}")

    manifest = load_json(manifest_path)

    paths = {
        "rag_store": baseline_root / ".runtime/state/rag/rag_store.json",
        "preindexed_corpus": baseline_root / ".runtime/state/rag/preindexed_public_corpus.json",
        "workflow_history": baseline_root / ".runtime/logs/product/workflow_history.json",
        "telemetry_runs": baseline_root / ".runtime/logs/product/telemetry_runs.json",
        "lab_workflow_runs": baseline_root / ".runtime/state/lab/workflow_runs.json",
        "evidenceops_worklog": baseline_root / ".runtime/logs/evidenceops/worklog.json",
        "evidenceops_actions": baseline_root / ".phase95_evidenceops_actions.sqlite3",
        "presentation_exports": baseline_root / "artifacts/presentation_exports",
        "external_files": baseline_root / "external_files",
    }

    missing = [name for name, path in paths.items() if not path.exists()]

    counts = {
        "rag_documents": count_json(paths["rag_store"], "documents") if paths["rag_store"].exists() else 0,
        "rag_chunks": count_json(paths["rag_store"], "chunks") if paths["rag_store"].exists() else 0,
        "preindexed_documents": count_json(paths["preindexed_corpus"], "documents") if paths["preindexed_corpus"].exists() else 0,
        "preindexed_chunks": count_json(paths["preindexed_corpus"], "chunks") if paths["preindexed_corpus"].exists() else 0,
        "workflow_history_runs": count_json(paths["workflow_history"], "runs", "history", "items") if paths["workflow_history"].exists() else 0,
        "telemetry_runs": count_json(paths["telemetry_runs"], "runs", "telemetry", "items") if paths["telemetry_runs"].exists() else 0,
        "lab_workflow_runs": count_json(paths["lab_workflow_runs"], "runs", "workflow_runs", "items") if paths["lab_workflow_runs"].exists() else 0,
        "evidenceops_worklog_entries": count_json(paths["evidenceops_worklog"], "entries", "items") if paths["evidenceops_worklog"].exists() else 0,
        "evidenceops_action_rows": sqlite_count(paths["evidenceops_actions"], "evidenceops_actions") if paths["evidenceops_actions"].exists() else 0,
    }

    artifact_metadata_files = []
    if paths["presentation_exports"].exists():
        artifact_metadata_files = list(paths["presentation_exports"].rglob("metadata.json"))

    counts["artifact_metadata_files"] = len(artifact_metadata_files)

    file_inventory = {
        "pptx": len(list(baseline_root.rglob("*.pptx"))),
        "pdf": len(list(baseline_root.rglob("*.pdf"))),
        "png": len(list(baseline_root.rglob("*.png"))),
        "json": len(list(baseline_root.rglob("*.json"))),
        "external_files": len([p for p in paths["external_files"].rglob("*") if p.is_file()]) if paths["external_files"].exists() else 0,
    }

    scan = scan_text(baseline_root)

    failures = []

    if missing:
        failures.append({"type": "missing_required_paths", "items": missing})

    minimums = {
        "rag_documents": 17,
        "rag_chunks": 283,
        "preindexed_documents": 55,
        "preindexed_chunks": 967,
        "workflow_history_runs": 100,
        "telemetry_runs": 100,
        "lab_workflow_runs": 100,
        "evidenceops_worklog_entries": 68,
        "evidenceops_action_rows": 72,
        "artifact_metadata_files": 80,
    }

    for key, expected_min in minimums.items():
        if counts.get(key, 0) < expected_min:
            failures.append({
                "type": "count_below_minimum",
                "key": key,
                "expected_min": expected_min,
                "actual": counts.get(key, 0),
            })

    if scan["absolute_path_findings"]:
        failures.append({
            "type": "absolute_paths_remaining",
            "count": len(scan["absolute_path_findings"]),
        })

    if scan["secret_pattern_findings"]:
        failures.append({
            "type": "secret_patterns_remaining",
            "count": len(scan["secret_pattern_findings"]),
        })

    if not manifest.get("docker_ready"):
        failures.append({"type": "manifest_not_sanitization_ready"})

    result = {
        "ok": not failures,
        "baseline_dir": str(baseline_dir),
        "counts": counts,
        "file_inventory": file_inventory,
        "manifest_docker_ready": manifest.get("docker_ready"),
        "scan": {
            "absolute_path_file_count": len(scan["absolute_path_findings"]),
            "secret_pattern_file_count": len(scan["secret_pattern_findings"]),
        },
        "failures": failures,
    }

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()

    result = validate(Path(args.baseline_dir).resolve())

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
