from __future__ import annotations

import argparse
import json
import shlex
import sqlite3
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from src.config import get_ollama_settings, get_rag_settings  # noqa: E402
from src.providers.registry import build_provider_registry, resolve_provider_runtime_profile  # noqa: E402
from src.rag.loaders import load_document  # noqa: E402
from src.rag.service import upsert_documents_in_rag_index  # noqa: E402
from src.storage.rag_store import load_rag_store, save_rag_store  # noqa: E402


DEFAULT_GOLD_MANIFEST = ROOT_DIR / "phase5_eval" / "fixtures" / "11_real_document_gold_sets_manifest.json"
DEFAULT_CHECKLIST_FIXTURE = ROOT_DIR / "phase5_eval" / "fixtures" / "06_checklist_who_surgical_gold.json"
DEFAULT_EVIDENCE_GOLD_SET = ROOT_DIR / "phase5_eval" / "fixtures" / "evidence_cv_mini_gold_set.json"
DEFAULT_OUT_PATH = ROOT_DIR / "phase5_eval" / "reports" / "phase8_live_evals.json"
DEFAULT_EVAL_DB_PATH = ROOT_DIR / ".phase8_eval_runs.sqlite3"


@dataclass
class LocalUploadedFile:
    path: Path

    @property
    def name(self) -> str:
        return self.path.name

    def getvalue(self) -> bytes:
        return self.path.read_bytes()


def _resolve_path(path_value: str | None) -> Path:
    path = Path(path_value or "")
    return path if path.is_absolute() else ROOT_DIR / path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid JSON payload at {path}")
    return payload


def _load_gold_manifest(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    items = payload.get("gold_sets") if isinstance(payload.get("gold_sets"), list) else []
    return [item for item in items if isinstance(item, dict)]


def _load_indexed_document_map() -> dict[str, dict[str, Any]]:
    settings = get_rag_settings()
    rag_store = load_rag_store(settings.store_path)
    documents = rag_store.get("documents", []) if isinstance(rag_store, dict) else []
    indexed: dict[str, dict[str, Any]] = {}
    for item in documents:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            indexed[name] = item
    return indexed


def _build_ollama_tags_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        path = path[: -len("/v1")]
    if not path:
        path = ""
    return urlunsplit((parsed.scheme or "http", parsed.netloc, f"{path}/api/tags", "", ""))


def _check_ollama_runtime() -> dict[str, Any]:
    settings = get_ollama_settings()
    tags_url = _build_ollama_tags_url(settings.base_url)
    try:
        with urllib.request.urlopen(tags_url, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("models") if isinstance(payload, dict) else []
        model_names = [str(item.get("name") or "") for item in models if isinstance(item, dict)]
        return {
            "ready": True,
            "tags_url": tags_url,
            "model_count": len(model_names),
            "models": model_names,
        }
    except Exception as error:
        return {
            "ready": False,
            "tags_url": tags_url,
            "error": str(error),
            "model_count": 0,
            "models": [],
        }


def _check_provider_profiles(provider: str) -> dict[str, Any]:
    registry = build_provider_registry()
    rag_settings = get_rag_settings()
    chat_profile = resolve_provider_runtime_profile(registry, provider, capability="chat", fallback_provider="ollama")
    embedding_profile = resolve_provider_runtime_profile(
        registry,
        rag_settings.embedding_provider,
        capability="embeddings",
        fallback_provider="ollama",
    )
    ollama_runtime = _check_ollama_runtime() if str(chat_profile.get("effective_provider") or "") == "ollama" else None
    chat_ready = bool(chat_profile.get("provider_entry")) and (bool(ollama_runtime.get("ready")) if ollama_runtime is not None else True)
    embedding_ready = bool(embedding_profile.get("provider_entry"))
    return {
        "chat_profile": chat_profile,
        "embedding_profile": embedding_profile,
        "ollama_runtime": ollama_runtime,
        "chat_ready": chat_ready,
        "embedding_ready": embedding_ready,
    }


def _sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_json_value(item)
            for key, item in value.items()
            if str(key) != "instance" and str(key) != "provider_instance"
        }
    if isinstance(value, list):
        return [_sanitize_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_json_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def build_live_eval_preflight(
    *,
    provider: str,
    gold_manifest_path: Path,
    checklist_fixture_path: Path,
    evidence_gold_set_path: Path,
) -> dict[str, Any]:
    provider_checks = _check_provider_profiles(provider)
    indexed_documents = _load_indexed_document_map()
    manifest_entries = _load_gold_manifest(gold_manifest_path)

    structured_entries: list[dict[str, Any]] = []
    for entry in manifest_entries:
        document_name = str(entry.get("document_name") or "")
        document_path = _resolve_path(str(entry.get("document_path") or ""))
        gold_path = _resolve_path(str(entry.get("gold_path") or ""))
        indexed = document_name in indexed_documents
        structured_entries.append(
            {
                "task_type": str(entry.get("task_type") or ""),
                "document_name": document_name,
                "document_path": str(document_path),
                "gold_path": str(gold_path),
                "document_exists": document_path.exists(),
                "gold_exists": gold_path.exists(),
                "indexed": indexed,
                "indexed_document_id": indexed_documents.get(document_name, {}).get("document_id"),
                "runnable": indexed and document_path.exists() and gold_path.exists(),
            }
        )

    checklist_fixture = _load_json(checklist_fixture_path)
    checklist_document_name = str(checklist_fixture.get("document_name") or "")
    checklist_ready = checklist_fixture_path.exists() and checklist_document_name in indexed_documents

    evidence_gold_set = _load_json(evidence_gold_set_path)
    evidence_documents = evidence_gold_set.get("documents") if isinstance(evidence_gold_set.get("documents"), list) else []
    evidence_items = []
    for item in evidence_documents:
        if not isinstance(item, dict):
            continue
        file_path = _resolve_path(str(item.get("file") or ""))
        evidence_items.append(
            {
                "file": str(file_path),
                "exists": file_path.exists(),
            }
        )
    evidence_ready = evidence_gold_set_path.exists() and all(item["exists"] for item in evidence_items)

    missing_indexed_documents = [
        item["document_name"]
        for item in structured_entries
        if item["document_exists"] and item["gold_exists"] and not item["indexed"]
    ]

    return {
        "provider_checks": _sanitize_json_value(provider_checks),
        "rag_store_path": str(get_rag_settings().store_path),
        "indexed_document_count": len(indexed_documents),
        "indexed_documents": sorted(indexed_documents.keys()),
        "structured_entries": structured_entries,
        "missing_indexed_documents": missing_indexed_documents,
        "checklist_fixture": {
            "path": str(checklist_fixture_path),
            "document_name": checklist_document_name,
            "ready": checklist_ready,
        },
        "evidence_gold_set": {
            "path": str(evidence_gold_set_path),
            "ready": evidence_ready,
            "documents": evidence_items,
        },
    }


def _resolve_embeddings_provider_instance():
    registry = build_provider_registry()
    rag_settings = get_rag_settings()
    profile = resolve_provider_runtime_profile(
        registry,
        rag_settings.embedding_provider,
        capability="embeddings",
        fallback_provider="ollama",
    )
    instance = profile.get("provider_instance")
    if instance is None:
        raise RuntimeError("No embedding provider available for indexing missing documents.")
    return instance


def index_missing_manifest_documents(structured_entries: list[dict[str, Any]]) -> dict[str, Any]:
    rag_settings = get_rag_settings()
    rag_index = load_rag_store(rag_settings.store_path)
    indexed_map = _load_indexed_document_map()
    documents_to_index = []
    planned = []
    for entry in structured_entries:
        document_name = str(entry.get("document_name") or "")
        document_path = Path(str(entry.get("document_path") or ""))
        if document_name in indexed_map or not document_path.exists():
            continue
        documents_to_index.append(load_document(LocalUploadedFile(document_path), rag_settings))
        planned.append(document_name)

    if not documents_to_index:
        return {"indexed_count": 0, "indexed_documents": [], "sync_status": None}

    embedding_provider = _resolve_embeddings_provider_instance()
    updated_index, sync_status = upsert_documents_in_rag_index(
        documents=documents_to_index,
        settings=rag_settings,
        embedding_provider=embedding_provider,
        rag_index=rag_index,
    )
    save_rag_store(rag_settings.store_path, updated_index)
    return {
        "indexed_count": len(planned),
        "indexed_documents": planned,
        "sync_status": sync_status,
    }


def build_live_eval_commands(
    *,
    provider: str,
    model: str | None,
    gold_manifest_path: Path,
    checklist_fixture_path: Path,
    evidence_gold_set_path: Path,
    preflight: dict[str, Any],
    context_strategy: str,
    skip_structured: bool,
    skip_checklist: bool,
    skip_evidence_cv: bool,
    limit_structured_docs: int | None,
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []

    if not skip_structured:
        runnable_structured = [item for item in preflight.get("structured_entries", []) if item.get("runnable")]
        if isinstance(limit_structured_docs, int) and limit_structured_docs > 0:
            runnable_structured = runnable_structured[:limit_structured_docs]
        for item in runnable_structured:
            argv = [
                sys.executable,
                str(ROOT_DIR / "scripts" / "run_phase5_structured_eval.py"),
                "--task",
                str(item.get("task_type") or ""),
                "--provider",
                provider,
                "--use-indexed-document",
                "--document-name",
                str(item.get("document_name") or ""),
                "--context-strategy",
                context_strategy,
                "--gold-manifest",
                str(gold_manifest_path),
            ]
            if model:
                argv.extend(["--model", model])
            commands.append(
                {
                    "suite_name": "structured_real_document_eval",
                    "label": f"{item.get('task_type')}:{item.get('document_name')}",
                    "argv": argv,
                }
            )

    if not skip_checklist and bool(preflight.get("checklist_fixture", {}).get("ready")):
        checklist_document_name = str(preflight.get("checklist_fixture", {}).get("document_name") or "")
        argv = [
            sys.executable,
            str(ROOT_DIR / "scripts" / "evaluate_checklist_regression.py"),
            "--fixture",
            str(checklist_fixture_path),
            "--provider",
            provider,
            "--document-name",
            checklist_document_name,
            "--context-strategy",
            context_strategy,
        ]
        if model:
            argv.extend(["--model", model])
        commands.append(
            {
                "suite_name": "checklist_regression",
                "label": f"checklist:{checklist_document_name}",
                "argv": argv,
            }
        )

    if not skip_evidence_cv and bool(preflight.get("evidence_gold_set", {}).get("ready")):
        commands.append(
            {
                "suite_name": "evidence_cv_gold_eval",
                "label": "evidence_cv_gold_eval",
                "argv": [
                    sys.executable,
                    str(ROOT_DIR / "scripts" / "evaluate_evidence_cv_gold_set.py"),
                    "--gold-set",
                    str(evidence_gold_set_path),
                    "--out",
                    str(ROOT_DIR / "phase5_eval" / "reports" / "evidence_cv_eval_metrics_live.json"),
                ],
            }
        )

    return commands


def _count_eval_runs(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT COUNT(*) FROM eval_runs").fetchone()
    return int(row[0] if row else 0)


def run_live_eval_commands(commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in commands:
        started_at = time.perf_counter()
        completed = subprocess.run(
            item["argv"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
        )
        duration_s = round(time.perf_counter() - started_at, 3)
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        results.append(
            {
                "suite_name": item.get("suite_name"),
                "label": item.get("label"),
                "command": shlex.join([str(arg) for arg in item["argv"]]),
                "returncode": completed.returncode,
                "duration_s": duration_s,
                "stdout_tail": stdout[-4000:] if stdout else "",
                "stderr_tail": stderr[-4000:] if stderr else "",
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live Phase 8 evals that depend on local provider/RAG/document readiness.")
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--model", default=None)
    parser.add_argument("--gold-manifest", default=str(DEFAULT_GOLD_MANIFEST))
    parser.add_argument("--checklist-fixture", default=str(DEFAULT_CHECKLIST_FIXTURE))
    parser.add_argument("--evidence-gold-set", default=str(DEFAULT_EVIDENCE_GOLD_SET))
    parser.add_argument("--out", default=str(DEFAULT_OUT_PATH))
    parser.add_argument("--context-strategy", default="document_scan", choices=["document_scan", "retrieval"])
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--index-missing", action="store_true")
    parser.add_argument("--skip-structured", action="store_true")
    parser.add_argument("--skip-checklist", action="store_true")
    parser.add_argument("--skip-evidence-cv", action="store_true")
    parser.add_argument("--limit-structured-docs", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gold_manifest_path = _resolve_path(args.gold_manifest)
    checklist_fixture_path = _resolve_path(args.checklist_fixture)
    evidence_gold_set_path = _resolve_path(args.evidence_gold_set)
    out_path = _resolve_path(args.out)

    preflight = build_live_eval_preflight(
        provider=args.provider,
        gold_manifest_path=gold_manifest_path,
        checklist_fixture_path=checklist_fixture_path,
        evidence_gold_set_path=evidence_gold_set_path,
    )

    strict_failures = []
    if not bool(preflight.get("provider_checks", {}).get("chat_ready")):
        strict_failures.append("chat_provider_not_ready")
    if not bool(preflight.get("provider_checks", {}).get("embedding_ready")):
        strict_failures.append("embedding_provider_not_ready")
    if args.strict and preflight.get("missing_indexed_documents"):
        strict_failures.append("missing_indexed_documents")
    if args.strict and not bool(preflight.get("evidence_gold_set", {}).get("ready")) and not args.skip_evidence_cv:
        strict_failures.append("evidence_gold_set_not_ready")

    indexing_report = None
    if args.index_missing:
        indexing_report = index_missing_manifest_documents(preflight.get("structured_entries", []))
        preflight = build_live_eval_preflight(
            provider=args.provider,
            gold_manifest_path=gold_manifest_path,
            checklist_fixture_path=checklist_fixture_path,
            evidence_gold_set_path=evidence_gold_set_path,
        )
        if args.strict and preflight.get("missing_indexed_documents"):
            strict_failures.append("missing_indexed_documents_after_indexing")

    if args.preflight_only or strict_failures:
        payload = {
            "preflight": preflight,
            "indexing_report": _sanitize_json_value(indexing_report),
            "strict_failures": strict_failures,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2 if strict_failures else 0

    commands = build_live_eval_commands(
        provider=args.provider,
        model=args.model,
        gold_manifest_path=gold_manifest_path,
        checklist_fixture_path=checklist_fixture_path,
        evidence_gold_set_path=evidence_gold_set_path,
        preflight=preflight,
        context_strategy=args.context_strategy,
        skip_structured=args.skip_structured,
        skip_checklist=args.skip_checklist,
        skip_evidence_cv=args.skip_evidence_cv,
        limit_structured_docs=(args.limit_structured_docs if args.limit_structured_docs > 0 else None),
    )

    if not commands:
        payload = {
            "preflight": preflight,
            "indexing_report": _sanitize_json_value(indexing_report),
            "commands": [],
            "results": [],
            "message": "No runnable live eval commands were produced.",
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if args.strict else 0

    before_count = _count_eval_runs(DEFAULT_EVAL_DB_PATH)
    results = run_live_eval_commands(commands)
    after_count = _count_eval_runs(DEFAULT_EVAL_DB_PATH)
    worst_returncode = max((int(item.get("returncode") or 0) for item in results), default=0)

    payload = {
        "provider": args.provider,
        "model": args.model,
        "eval_db_path": str(DEFAULT_EVAL_DB_PATH),
        "preflight": preflight,
        "indexing_report": _sanitize_json_value(indexing_report),
        "commands": [
            {
                "suite_name": item.get("suite_name"),
                "label": item.get("label"),
                "command": shlex.join([str(arg) for arg in item.get("argv", [])]),
            }
            for item in commands
        ],
        "results": results,
        "eval_runs_before": before_count,
        "eval_runs_after": after_count,
        "eval_runs_delta": after_count - before_count,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return worst_returncode


if __name__ == "__main__":
    raise SystemExit(main())