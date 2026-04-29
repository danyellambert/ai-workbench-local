from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
from pathlib import Path


SOURCE_PATHS = [
    ".runtime/state/rag",
    ".runtime/state/product",
    ".runtime/logs/product",
    ".runtime/state/lab",
    ".runtime/state/evidenceops",
    ".runtime/logs/evidenceops",
    ".phase95_evidenceops_actions.sqlite3",
    "artifacts/presentation_exports",
    "data/corpus_revisado/frontend_demo_grounded_v1",
    "data/corpus_revisado/option_b_synthetic_premium",
    "data/materials_demo",
]


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|passwd|authorization|bearer)\s*[:=]"),
]

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"/Users/[^\"'\s]+"),
    re.compile(r"/private/[^\"'\s]+"),
    re.compile(r"/var/folders/[^\"'\s]+"),
]


def copy_path(root: Path, out: Path, rel: str) -> dict:
    src = root / rel
    dst = out / "raw_sources" / rel

    if not src.exists():
        return {"source": rel, "exists": False, "copied": False}

    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return {
        "source": rel,
        "exists": True,
        "copied": True,
        "type": "dir" if src.is_dir() else "file",
    }


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".json", ".md", ".txt", ".yml", ".yaml", ".toml", ".env"}:
            yield path


def scan_file(path: Path, out_root: Path) -> dict:
    rel = str(path.relative_to(out_root))
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return {"path": rel, "read_error": str(exc)}

    absolute_paths = []
    secret_hits = []

    for pattern in ABSOLUTE_PATH_PATTERNS:
        absolute_paths.extend(sorted(set(pattern.findall(text)))[:20])

    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            secret_hits.append(pattern.pattern)

    result = {"path": rel}
    if absolute_paths:
        result["absolute_paths"] = absolute_paths[:20]
    if secret_hits:
        result["secret_pattern_hits"] = secret_hits
    return result


def safe_json_count(path: Path, *keys: str) -> int | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if isinstance(payload, list):
        return len(payload)

    if not isinstance(payload, dict):
        return None

    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)

    return None


def safe_sqlite_table_count(path: Path, table: str) -> int | None:
    if not path.exists():
        return None
    try:
        with sqlite3.connect(path) as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            return int(row[0]) if row else None
    except Exception:
        return None


def count_artifact_metadata_dirs(path: Path) -> int:
    if not path.exists():
        return 0
    return len([item for item in path.glob("*") if item.is_dir() and (item / "metadata.json").exists()])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    out = Path(args.out).resolve()

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    copy_report = [copy_path(root, out, rel) for rel in SOURCE_PATHS]

    raw = out / "raw_sources"
    scan_results = [item for item in (scan_file(path, raw) for path in iter_text_files(raw)) if len(item) > 1]

    counts = {
        "rag_documents": safe_json_count(raw / ".runtime/state/rag/rag_store.json", "documents"),
        "rag_chunks": safe_json_count(raw / ".runtime/state/rag/rag_store.json", "chunks"),
        "preindexed_documents": safe_json_count(raw / ".runtime/state/rag/preindexed_public_corpus.json", "documents"),
        "preindexed_chunks": safe_json_count(raw / ".runtime/state/rag/preindexed_public_corpus.json", "chunks"),
        "workflow_history_runs": safe_json_count(raw / ".runtime/logs/product/workflow_history.json", "runs", "history", "items"),
        "telemetry_runs": safe_json_count(raw / ".runtime/logs/product/telemetry_runs.json", "runs", "telemetry", "items"),
        "lab_workflow_runs": safe_json_count(raw / ".runtime/state/lab/workflow_runs.json", "runs", "workflow_runs", "items"),
        "lab_artifacts_index": safe_json_count(raw / ".runtime/state/lab/artifacts_index.json", "artifacts", "items"),
        "lab_artifacts_derived_from_presentation_exports": count_artifact_metadata_dirs(raw / "artifacts/presentation_exports"),
        "evidenceops_worklog_entries": safe_json_count(raw / ".runtime/logs/evidenceops/worklog.json", "entries", "items"),
        "evidenceops_action_rows": safe_sqlite_table_count(raw / ".phase95_evidenceops_actions.sqlite3", "evidenceops_actions"),
    }

    artifact_dirs = list((raw / "artifacts/presentation_exports").glob("*")) if (raw / "artifacts/presentation_exports").exists() else []
    counts["presentation_export_dirs"] = len([p for p in artifact_dirs if p.is_dir()])

    manifest = {
        "baseline_stage_kind": "functional_baseline_raw_stage",
        "purpose": "Copy real local state outside Git before path rewrite and Docker mounting.",
        "workspace_root": str(root),
        "copy_report": copy_report,
        "counts": counts,
        "audit": {
            "text_files_with_findings": len(scan_results),
            "raw_stage_contains_absolute_paths": any("absolute_paths" in item for item in scan_results),
            "raw_stage_contains_secret_pattern_hits": any("secret_pattern_hits" in item for item in scan_results),
        },
    }

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "audit_findings.json").write_text(json.dumps(scan_results, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "out": str(out),
        "counts": counts,
        "audit": manifest["audit"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
