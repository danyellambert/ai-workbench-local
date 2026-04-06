from __future__ import annotations

import os
from pathlib import Path


def _resolve_root_from_env(env_name: str, default_path: Path) -> Path:
    raw_value = str(os.getenv(env_name, "")).strip()
    return Path(raw_value) if raw_value else default_path


def get_runtime_root(base_dir: Path) -> Path:
    return _resolve_root_from_env("APP_RUNTIME_ROOT", base_dir / ".runtime")


def get_artifact_root(base_dir: Path) -> Path:
    return _resolve_root_from_env("APP_ARTIFACT_ROOT", base_dir / "artifacts")


def _prefer_existing_legacy_path(new_path: Path, legacy_path: Path) -> Path:
    if new_path.exists():
        return new_path
    if legacy_path.exists():
        return legacy_path
    return new_path


def get_chat_history_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "state" / "chat" / "chat_history.json", base_dir / ".chat_history.json")


def get_rag_store_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "state" / "rag" / "rag_store.json", base_dir / ".rag_store.json")


def get_rag_chroma_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "state" / "rag" / "chroma", base_dir / ".chroma_rag")


def get_phase55_shadow_log_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "logs" / "phase55" / "langchain_shadow_log.json", base_dir / ".phase55_langchain_shadow_log.json")


def get_phase55_langgraph_shadow_log_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "logs" / "phase55" / "langgraph_shadow_log.json", base_dir / ".phase55_langgraph_shadow_log.json")


def get_phase6_document_agent_log_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "logs" / "phase6" / "document_agent_log.json", base_dir / ".phase6_document_agent_log.json")


def get_phase7_model_comparison_log_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "logs" / "phase7" / "model_comparison_log.json", base_dir / ".phase7_model_comparison_log.json")


def get_phase8_eval_db_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "evals" / "phase8" / "phase8_eval_runs.sqlite3", base_dir / ".phase8_eval_runs.sqlite3")


def get_runtime_execution_log_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "logs" / "runtime" / "runtime_execution_log.json", base_dir / ".runtime_execution_log.json")


def get_phase95_evidenceops_worklog_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "logs" / "evidenceops" / "worklog.json", base_dir / ".phase95_evidenceops_worklog.json")


def get_phase95_evidenceops_action_store_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "state" / "evidenceops" / "actions.sqlite3", base_dir / ".phase95_evidenceops_actions.sqlite3")


def get_phase95_evidenceops_repository_snapshot_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "state" / "evidenceops" / "repository_snapshot.json", base_dir / ".phase95_evidenceops_repository_snapshot.json")


def get_product_workflow_history_path(base_dir: Path) -> Path:
    runtime_root = get_runtime_root(base_dir)
    return _prefer_existing_legacy_path(runtime_root / "logs" / "product" / "workflow_history.json", base_dir / ".product_workflow_history.json")
