from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from ..structured.envelope import StructuredResult
from .phase8_5_runtime_metadata import infer_resolved_runtime_family, summarize_runtime_family_artifacts


def _safe_distribution_version(distribution_name: str) -> str | None:
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def _read_git_commit(project_root: str | Path | None) -> str | None:
    if not project_root:
        return None
    resolved_root = Path(project_root)
    try:
        result = subprocess.run(
            ["git", "-C", str(resolved_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    commit_hash = str(result.stdout or "").strip()
    return commit_hash or None


def _read_ollama_version() -> str | None:
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    output = str(result.stdout or result.stderr or "").strip()
    return output or None


def _summarize_model_resolution_artifacts(resolved_case_artifacts: list[dict[str, object]] | None) -> dict[str, object]:
    counts: dict[str, int] = {}
    substitutions: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    for artifact in resolved_case_artifacts or []:
        if not isinstance(artifact, dict):
            continue
        status = str(artifact.get("model_resolution_status") or "exact").strip() or "exact"
        counts[status] = counts.get(status, 0) + 1
        requested_model = str(artifact.get("model_requested") or "").strip()
        effective_model = str(artifact.get("model_effective") or "").strip()
        if status == "exact" and requested_model == effective_model:
            continue
        key = (
            str(artifact.get("group") or ""),
            str(artifact.get("provider_requested") or ""),
            requested_model,
            effective_model,
            status,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        substitutions.append(
            {
                "group": artifact.get("group"),
                "provider_requested": artifact.get("provider_requested"),
                "model_requested": requested_model,
                "model_effective": effective_model,
                "mapping_status": status,
                "resolution_source": artifact.get("model_resolution_source"),
            }
        )
    return {
        "counts": counts,
        "substitutions": substitutions,
    }


def build_benchmark_environment_snapshot(
    *,
    project_root: str | Path,
    registry: dict[str, dict[str, object]],
    manifest: dict[str, object],
    selected_groups: list[str],
    fairness_config: dict[str, object] | None = None,
    environment_overrides: dict[str, object] | None = None,
    package_names: list[str] | None = None,
    resolved_case_artifacts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    resolved_root = Path(project_root)
    package_snapshot: dict[str, str | None] = {}
    requested_packages = package_names or [
        "openai",
        "streamlit",
        "chromadb",
        "langchain-community",
        "langchain-chroma",
        "langgraph",
        "pypdf",
        "python-dotenv",
    ]
    for package_name in requested_packages:
        package_snapshot[package_name] = _safe_distribution_version(package_name)

    provider_inventory: dict[str, dict[str, object]] = {}
    for provider_key, provider_entry in registry.items():
        if not isinstance(provider_entry, dict):
            continue
        provider_instance = provider_entry.get("instance")
        chat_models = []
        embedding_models = []
        if provider_key == "ollama" and hasattr(provider_instance, "_discover_local_models"):
            try:
                discovered_models = list(provider_instance._discover_local_models())  # type: ignore[attr-defined]
            except Exception:
                discovered_models = []
            chat_models = list(discovered_models)
            if hasattr(provider_instance, "_looks_like_embedding_model"):
                embedding_models = [
                    model
                    for model in discovered_models
                    if provider_instance._looks_like_embedding_model(model)  # type: ignore[attr-defined]
                ]
        elif provider_key == "huggingface_server":
            if hasattr(provider_instance, "_catalog_chat_models"):
                try:
                    chat_models = list(provider_instance._catalog_chat_models())  # type: ignore[attr-defined]
                except Exception:
                    chat_models = []
            if hasattr(provider_instance, "_catalog_embedding_models"):
                try:
                    embedding_models = list(provider_instance._catalog_embedding_models())  # type: ignore[attr-defined]
                except Exception:
                    embedding_models = []
        else:
            if hasattr(provider_instance, "list_available_models"):
                try:
                    chat_models = list(provider_instance.list_available_models())
                except Exception:
                    chat_models = []
            if hasattr(provider_instance, "list_available_embedding_models"):
                try:
                    embedding_models = list(provider_instance.list_available_embedding_models())
                except Exception:
                    embedding_models = []
        provider_inventory[provider_key] = {
            "label": provider_entry.get("label"),
            "detail": provider_entry.get("detail"),
            "supports_chat": bool(provider_entry.get("supports_chat")),
            "supports_embeddings": bool(provider_entry.get("supports_embeddings")),
            "default_model": provider_entry.get("default_model"),
            "default_context_window": provider_entry.get("default_context_window"),
            "default_runtime_family": infer_resolved_runtime_family(
                provider_effective=provider_key,
                model_effective=str(provider_entry.get("default_model") or ""),
                runtime_artifact=None,
            ),
            "available_chat_models": chat_models,
            "available_embedding_models": embedding_models,
        }

    ollama_inventory = provider_inventory.get("ollama") if isinstance(provider_inventory.get("ollama"), dict) else {}
    model_resolution_summary = _summarize_model_resolution_artifacts(resolved_case_artifacts)
    runtime_family_resolution_summary = summarize_runtime_family_artifacts(resolved_case_artifacts)

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(resolved_root),
        "git_commit_hash": _read_git_commit(resolved_root),
        "ollama_version": _read_ollama_version(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
        },
        "packages": package_snapshot,
        "selected_groups": list(selected_groups),
        "benchmark_config": manifest,
        "fairness_config": dict(fairness_config or {}),
        "active_environment": dict(environment_overrides or {}),
        "provider_inventory": provider_inventory,
        "ollama_inventory": {
            "available_chat_models": list(ollama_inventory.get("available_chat_models") or []),
            "available_embedding_models": list(ollama_inventory.get("available_embedding_models") or []),
            "http_timeout_seconds": str(os.getenv("OLLAMA_HTTP_TIMEOUT_SECONDS", "")).strip() or None,
            "embed_batch_size": str(os.getenv("OLLAMA_EMBED_BATCH_SIZE", "")).strip() or None,
        },
        "model_resolution_summary": model_resolution_summary,
        "runtime_family_resolution_summary": runtime_family_resolution_summary,
        "resolved_case_artifacts": list(resolved_case_artifacts or []),
    }


def extract_last_assistant_metadata(messages: list[dict[str, object]]) -> dict[str, object]:
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        metadata = message.get("metadata")
        if isinstance(metadata, dict):
            return metadata
    return {}


def summarize_provider_path(provider: str, provider_label: str, ollama_base_url: str | None) -> tuple[str, str]:
    if provider == "ollama":
        base_url = str(ollama_base_url or "").strip()
        route = f"{provider_label} -> {base_url or 'endpoint not configured'}"
        if any(token in base_url.lower() for token in ["localhost", "127.0.0.1"]):
            dependency = "Local dependency: the app and Ollama server run on your machine."
        else:
            dependency = "Partial local dependency: local app, inference through a remote Ollama-compatible endpoint."
        return route, dependency
    if provider == "huggingface_server":
        route = f"{provider_label} -> OpenAI-compatible service / local AI hub"
        dependency = "Local dependency: app + local hub service; the effective backend may vary by alias/model published in the service."
        return route, dependency
    if provider == "openai":
        return f"{provider_label} -> direct cloud API", "Local dependency: local app; remote inference."
    if provider == "huggingface_local":
        return f"{provider_label} -> local Transformers runtime", "Local dependency: app + local inference through the Hugging Face ecosystem on your machine."
    return provider_label, "Unclassified local dependency."


def build_document_runtime_rows(
    document_ids: list[str],
    document_preview_map: dict[str, dict[str, object]],
    *,
    default_vl_model: str,
    default_ocr_backend: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for document_id in document_ids:
        preview = document_preview_map.get(str(document_id)) or {}
        document = preview.get("document") if isinstance(preview, dict) else {}
        if not isinstance(document, dict):
            continue
        loader_metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
        vl_runtime = loader_metadata.get("vl_runtime") if isinstance(loader_metadata.get("vl_runtime"), dict) else {}
        rows.append(
            {
                "documento": document.get("name"),
                "tipo": document.get("file_type"),
                "chunks": preview.get("chunks_count"),
                "loader": loader_metadata.get("loader_strategy_label") or loader_metadata.get("loader_strategy_used"),
                "extração_pdf": loader_metadata.get("strategy_label") or loader_metadata.get("strategy"),
                "source_type": loader_metadata.get("source_type"),
                "ocr_backend": loader_metadata.get("ocr_backend") or default_ocr_backend,
                "evidence_pipeline": bool(loader_metadata.get("evidence_pipeline_used")),
                "vl_model": vl_runtime.get("model") or default_vl_model,
            }
        )
    return rows


def build_eval_runtime_summary(
    eval_db_path: str | Path | None,
    *,
    recent_limit: int = 250,
) -> dict[str, object]:
    if not eval_db_path:
        return {}

    db_path = Path(eval_db_path)
    if not db_path.exists():
        return {
            "db_path": str(db_path),
            "db_exists": False,
            "entries_considered": 0,
            "total_runs": 0,
        }

    try:
        from ..storage.phase8_eval_diagnosis import build_eval_diagnosis
        from ..storage.phase8_eval_store import load_eval_runs, summarize_eval_runs

        entries = load_eval_runs(db_path, limit=recent_limit)
    except Exception:
        return {
            "db_path": str(db_path),
            "db_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
        }

    if not entries:
        return {
            "db_path": str(db_path),
            "db_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
        }

    aggregate = summarize_eval_runs(entries)
    diagnosis = build_eval_diagnosis(entries)
    decision_summary = diagnosis.get("decision_summary") if isinstance(diagnosis.get("decision_summary"), dict) else {}
    top_failure_reasons = diagnosis.get("top_failure_reasons") if isinstance(diagnosis.get("top_failure_reasons"), list) else []
    adaptation_candidates = diagnosis.get("adaptation_candidates") if isinstance(diagnosis.get("adaptation_candidates"), list) else []
    next_eval_priorities = decision_summary.get("next_eval_priorities") if isinstance(decision_summary.get("next_eval_priorities"), list) else []
    healthy_tasks = decision_summary.get("prompt_rag_sufficient_tasks") if isinstance(decision_summary.get("prompt_rag_sufficient_tasks"), list) else []

    return {
        "db_path": str(db_path),
        "db_exists": True,
        "entries_considered": len(entries),
        "recent_limit": int(recent_limit),
        "total_runs": int(aggregate.get("total_runs") or 0),
        "pass_rate": float(aggregate.get("pass_rate") or 0.0),
        "warn_rate": float(aggregate.get("warn_rate") or 0.0),
        "fail_rate": float(aggregate.get("fail_rate") or 0.0),
        "avg_score_ratio": float(aggregate.get("avg_score_ratio") or 0.0),
        "avg_latency_s": float(aggregate.get("avg_latency_s") or 0.0),
        "needs_review_rate": float(aggregate.get("needs_review_rate") or 0.0),
        "suite_counts": dict(aggregate.get("suite_counts") or {}),
        "task_counts": dict(aggregate.get("task_counts") or {}),
        "global_recommendation": decision_summary.get("global_recommendation"),
        "healthy_tasks": [
            {
                "task_type": item.get("task_type"),
                "pass_rate": item.get("pass_rate"),
                "avg_score_ratio": item.get("avg_score_ratio"),
            }
            for item in healthy_tasks[:5]
            if isinstance(item, dict)
        ],
        "adaptation_candidates": [
            {
                "task_type": item.get("task_type"),
                "adaptation_priority": item.get("adaptation_priority"),
                "fail_rate": item.get("fail_rate"),
                "avg_score_ratio": item.get("avg_score_ratio"),
                "recommended_action": item.get("recommended_action"),
            }
            for item in adaptation_candidates[:5]
            if isinstance(item, dict)
        ],
        "next_eval_priorities": [
            {
                "task_type": item.get("task_type"),
                "fail_rate": item.get("fail_rate"),
                "recent_fail_rate": item.get("recent_fail_rate"),
                "recommended_action": item.get("recommended_action"),
            }
            for item in next_eval_priorities[:5]
            if isinstance(item, dict)
        ],
        "top_failure_reasons": [
            {
                "reason": item.get("reason"),
                "count": item.get("count"),
            }
            for item in top_failure_reasons[:5]
            if isinstance(item, dict)
        ],
        "latest_created_at": entries[0].get("created_at"),
    }


def build_document_agent_runtime_summary(
    log_path: str | Path | None,
    *,
    recent_limit: int = 25,
) -> dict[str, object]:
    if not log_path:
        return {}

    resolved_path = Path(log_path)
    if not resolved_path.exists():
        return {
            "log_path": str(resolved_path),
            "log_exists": False,
            "entries_considered": 0,
            "total_runs": 0,
        }

    try:
        from ..storage.phase6_document_agent_log import load_document_agent_log, summarize_document_agent_log

        entries = load_document_agent_log(resolved_path)
    except Exception:
        return {
            "log_path": str(resolved_path),
            "log_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
        }

    if not entries:
        return {
            "log_path": str(resolved_path),
            "log_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
            "recent_entries": [],
        }

    aggregate = summarize_document_agent_log(entries)
    recent_entries = list(reversed(entries[-recent_limit:]))
    needs_review_examples = [
        {
            "timestamp": entry.get("timestamp"),
            "user_intent": entry.get("user_intent"),
            "tool_used": entry.get("tool_used"),
            "confidence": entry.get("confidence"),
            "needs_review_reason": entry.get("needs_review_reason"),
            "query": entry.get("query"),
        }
        for entry in recent_entries
        if bool(entry.get("needs_review"))
    ][:5]

    return {
        "log_path": str(resolved_path),
        "log_exists": True,
        "entries_considered": len(entries),
        "recent_limit": int(recent_limit),
        "total_runs": int(aggregate.get("total_runs") or 0),
        "success_rate": float(aggregate.get("success_rate") or 0.0),
        "needs_review_rate": float(aggregate.get("needs_review_rate") or 0.0),
        "avg_confidence": float(aggregate.get("avg_confidence") or 0.0),
        "avg_source_count": float(aggregate.get("avg_source_count") or 0.0),
        "avg_available_tools": float(aggregate.get("avg_available_tools") or 0.0),
        "runs_with_tool_errors": int(aggregate.get("runs_with_tool_errors") or 0),
        "intent_counts": dict(aggregate.get("intent_counts") or {}),
        "tool_counts": dict(aggregate.get("tool_counts") or {}),
        "answer_mode_counts": dict(aggregate.get("answer_mode_counts") or {}),
        "execution_strategy_counts": dict(aggregate.get("execution_strategy_counts") or {}),
        "workflow_route_decision_counts": dict(aggregate.get("workflow_route_decision_counts") or {}),
        "workflow_guardrail_decision_counts": dict(aggregate.get("workflow_guardrail_decision_counts") or {}),
        "review_reasons": dict(aggregate.get("review_reasons") or {}),
        "recent_entries": recent_entries,
        "needs_review_examples": needs_review_examples,
        "latest_timestamp": entries[-1].get("timestamp"),
    }


def build_runtime_execution_summary(
    log_path: str | Path | None,
    *,
    recent_limit: int = 25,
) -> dict[str, object]:
    if not log_path:
        return {}

    resolved_path = Path(log_path)
    if not resolved_path.exists():
        return {
            "log_path": str(resolved_path),
            "log_exists": False,
            "entries_considered": 0,
            "total_runs": 0,
        }

    try:
        from ..storage.runtime_execution_log import load_runtime_execution_log, summarize_runtime_execution_log

        entries = load_runtime_execution_log(resolved_path)
    except Exception:
        return {
            "log_path": str(resolved_path),
            "log_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
        }

    if not entries:
        return {
            "log_path": str(resolved_path),
            "log_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
            "recent_entries": [],
        }

    aggregate = summarize_runtime_execution_log(entries)
    return {
        "log_path": str(resolved_path),
        "log_exists": True,
        "entries_considered": len(entries),
        "recent_limit": int(recent_limit),
        **aggregate,
        "recent_entries": list(reversed(entries[-recent_limit:])),
    }


def build_evidenceops_worklog_summary(
    log_path: str | Path | None,
    *,
    recent_limit: int = 25,
) -> dict[str, object]:
    if not log_path:
        return {}

    resolved_path = Path(log_path)
    if not resolved_path.exists():
        return {
            "log_path": str(resolved_path),
            "log_exists": False,
            "entries_considered": 0,
            "total_runs": 0,
        }

    try:
        from ..storage.phase95_evidenceops_worklog import load_evidenceops_worklog, summarize_evidenceops_worklog

        entries = load_evidenceops_worklog(resolved_path)
    except Exception:
        return {
            "log_path": str(resolved_path),
            "log_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
        }

    if not entries:
        return {
            "log_path": str(resolved_path),
            "log_exists": True,
            "entries_considered": 0,
            "total_runs": 0,
            "recent_entries": [],
        }

    aggregate = summarize_evidenceops_worklog(entries)
    return {
        "log_path": str(resolved_path),
        "log_exists": True,
        "entries_considered": len(entries),
        "recent_limit": int(recent_limit),
        **aggregate,
        "recent_entries": list(reversed(entries[-recent_limit:])),
    }


def build_evidenceops_action_store_summary(
    store_path: str | Path | None,
    *,
    recent_limit: int = 25,
) -> dict[str, object]:
    if not store_path:
        return {}

    resolved_path = Path(store_path)
    if not resolved_path.exists():
        return {
            "store_path": str(resolved_path),
            "store_exists": False,
            "entries_considered": 0,
            "total_actions": 0,
        }

    try:
        from ..storage.phase95_evidenceops_action_store import load_evidenceops_actions, summarize_evidenceops_actions

        entries = load_evidenceops_actions(resolved_path)
    except Exception:
        return {
            "store_path": str(resolved_path),
            "store_exists": True,
            "entries_considered": 0,
            "total_actions": 0,
        }

    if not entries:
        return {
            "store_path": str(resolved_path),
            "store_exists": True,
            "entries_considered": 0,
            "total_actions": 0,
            "recent_entries": [],
        }

    aggregate = summarize_evidenceops_actions(entries)
    return {
        "store_path": str(resolved_path),
        "store_exists": True,
        "entries_considered": len(entries),
        "recent_limit": int(recent_limit),
        **aggregate,
        "recent_entries": entries[:recent_limit],
    }


def build_evidenceops_repository_summary(
    repository_root: str | Path | None,
    *,
    recent_limit: int = 25,
    snapshot_path: str | Path | None = None,
) -> dict[str, object]:
    if not repository_root:
        return {}

    resolved_root = Path(repository_root)
    resolved_snapshot_path = Path(snapshot_path) if snapshot_path else (resolved_root / ".phase95_evidenceops_repository_snapshot.json")
    if not resolved_root.exists() or not resolved_root.is_dir():
        return {
            "repository_root": str(resolved_root),
            "repository_exists": False,
            "snapshot_path": str(resolved_snapshot_path),
            "entries_considered": 0,
            "total_documents": 0,
        }

    try:
        from ..storage.phase95_evidenceops_repository_snapshot import (
            load_evidenceops_repository_snapshot,
            save_evidenceops_repository_snapshot,
        )
        from .evidenceops_repository import (
            build_evidenceops_repository_snapshot,
            diff_evidenceops_repository_snapshots,
            list_evidenceops_repository_documents,
            summarize_evidenceops_repository_documents,
        )

        documents = list_evidenceops_repository_documents(resolved_root)
    except Exception:
        return {
            "repository_root": str(resolved_root),
            "repository_exists": True,
            "snapshot_path": str(resolved_snapshot_path),
            "entries_considered": 0,
            "total_documents": 0,
        }

    aggregate = summarize_evidenceops_repository_documents(documents)
    previous_snapshot = load_evidenceops_repository_snapshot(resolved_snapshot_path)
    current_snapshot = build_evidenceops_repository_snapshot(resolved_root)
    drift_summary = diff_evidenceops_repository_snapshots(previous_snapshot, current_snapshot)
    save_evidenceops_repository_snapshot(resolved_snapshot_path, current_snapshot)
    recent_documents = sorted(
        documents,
        key=lambda item: (
            int(item.get("modified_at") or 0),
            str(item.get("relative_path") or ""),
        ),
        reverse=True,
    )[:recent_limit]
    return {
        "repository_root": str(resolved_root),
        "repository_exists": True,
        "snapshot_path": str(resolved_snapshot_path),
        "entries_considered": len(documents),
        "recent_limit": int(recent_limit),
        **aggregate,
        "drift_summary": drift_summary,
        "new_documents": drift_summary.get("new_documents") or [],
        "changed_documents": drift_summary.get("changed_documents") or [],
        "removed_documents": drift_summary.get("removed_documents") or [],
        "recent_documents": [
            {
                "document_id": item.get("document_id"),
                "title": item.get("title"),
                "category": item.get("category"),
                "relative_path": item.get("relative_path"),
                "suffix": item.get("suffix"),
                "size_kb": round(int(item.get("size_bytes") or 0) / 1024, 2),
            }
            for item in recent_documents
        ],
    }


def build_runtime_snapshot(
    *,
    selected_provider: str,
    selected_provider_label: str,
    provider_detail: str | None = None,
    selected_model: str,
    selected_embedding_provider: str,
    selected_embedding_model: str,
    selected_loader_strategy: str,
    selected_chunking_strategy: str,
    selected_retrieval_strategy: str,
    selected_pdf_extraction_mode: str,
    chat_selected_document_ids: list[str],
    structured_selected_document_ids: list[str],
    selected_structured_task: str,
    selected_structured_execution_strategy: str,
    messages: list[dict[str, object]],
    structured_result: StructuredResult | None,
    structured_task_registry: Any,
    document_preview_map: dict[str, dict[str, object]],
    indexed_documents_count: int,
    ollama_base_url: str,
    default_vl_model: str,
    default_ocr_backend: str,
    phase6_document_agent_log_path: str | Path | None = None,
    phase95_evidenceops_action_store_path: str | Path | None = None,
    phase95_evidenceops_repository_root: str | Path | None = None,
    phase95_evidenceops_repository_snapshot_path: str | Path | None = None,
    phase8_eval_db_path: str | Path | None = None,
    runtime_execution_log_path: str | Path | None = None,
    phase95_evidenceops_worklog_path: str | Path | None = None,
) -> dict[str, object]:
    provider_path, local_dependency = summarize_provider_path(
        selected_provider,
        selected_provider_label if not provider_detail else f"{selected_provider_label} ({provider_detail})",
        ollama_base_url,
    )
    last_chat_metadata = extract_last_assistant_metadata(messages)
    last_chat_usage = last_chat_metadata.get("usage") if isinstance(last_chat_metadata.get("usage"), dict) else {}
    last_chat_prompt_context = (
        last_chat_metadata.get("prompt_context") if isinstance(last_chat_metadata.get("prompt_context"), dict) else {}
    )
    structured_metadata = structured_result.execution_metadata if structured_result and isinstance(structured_result.execution_metadata, dict) else {}
    structured_telemetry = structured_metadata.get("telemetry") if isinstance(structured_metadata.get("telemetry"), dict) else {}
    structured_timings = structured_telemetry.get("timings_s") if isinstance(structured_telemetry.get("timings_s"), dict) else {}
    last_pre_model_prep_s = None
    if isinstance(structured_timings, dict):
        component_values = [
            structured_timings.get("document_load_s"),
            structured_timings.get("sanitize_s"),
            structured_timings.get("context_build_s"),
        ]
        numeric_values = [float(value) for value in component_values if isinstance(value, (int, float))]
        if numeric_values:
            last_pre_model_prep_s = round(sum(numeric_values), 4)

    task_model_map = {
        task_name: (task_definition.default_model or selected_model)
        for task_name, task_definition in structured_task_registry.list_tasks().items()
    }

    return {
        "provider_path": provider_path,
        "local_dependency": local_dependency,
        "chat": {
            "provider": last_chat_metadata.get("provider") or selected_provider,
            "model": last_chat_metadata.get("model") or selected_model,
            "embedding_provider": selected_embedding_provider,
            "embedding_model": selected_embedding_model,
            "selected_documents": len(chat_selected_document_ids),
            "retrieval_backend": last_chat_metadata.get("vector_backend_used"),
            "retrieval_strategy": last_chat_metadata.get("retrieval_strategy_used") or last_chat_metadata.get("retrieval_strategy_requested"),
            "retrieval_shadow_summary": last_chat_metadata.get("retrieval_shadow_summary"),
            "last_total_s": last_chat_metadata.get("latency_s"),
            "last_generation_s": last_chat_metadata.get("generation_latency_s"),
            "last_retrieval_s": last_chat_metadata.get("retrieval_latency_s"),
            "last_prompt_build_s": last_chat_metadata.get("prompt_build_latency_s"),
            "last_context_chars": last_chat_prompt_context.get("used_chars") or last_chat_usage.get("context_chars"),
            "last_prompt_context_used_chunks": last_chat_prompt_context.get("used_chunks"),
            "last_prompt_context_dropped_chunks": last_chat_prompt_context.get("dropped_chunks"),
            "last_prompt_context_truncated": last_chat_prompt_context.get("truncated"),
            "last_total_tokens": last_chat_usage.get("total_tokens"),
            "last_cost_usd": last_chat_usage.get("cost_usd"),
            "budget_routing_mode": last_chat_metadata.get("budget_routing_mode"),
            "budget_routing_reason": last_chat_metadata.get("budget_routing_reason"),
            "budget_auto_degrade_applied": last_chat_metadata.get("budget_auto_degrade_applied"),
            "budget_alert_status": last_chat_metadata.get("budget_alert_status"),
            "budget_alerts": last_chat_metadata.get("budget_alerts"),
            "provider_requested": last_chat_metadata.get("provider_requested"),
            "provider_effective": last_chat_metadata.get("provider_effective"),
        },
        "structured": {
            "current_task": selected_structured_task,
            "execution_strategy": structured_metadata.get("execution_strategy_used") or selected_structured_execution_strategy,
            "provider": structured_metadata.get("provider") or selected_provider,
            "model": structured_metadata.get("model") or selected_model,
            "selected_documents": len(structured_selected_document_ids),
            "agent_intent": structured_metadata.get("agent_intent_label") or structured_metadata.get("agent_intent"),
            "agent_tool": structured_metadata.get("agent_tool_label") or structured_metadata.get("agent_tool"),
            "agent_answer_mode": structured_metadata.get("agent_answer_mode"),
            "agent_available_tools": structured_metadata.get("agent_available_tools"),
            "needs_review": structured_metadata.get("needs_review"),
            "needs_review_reason": structured_metadata.get("needs_review_reason"),
            "agent_limitations": structured_metadata.get("agent_limitations"),
            "agent_recommended_actions": structured_metadata.get("agent_recommended_actions"),
            "agent_guardrails_applied": structured_metadata.get("agent_guardrails_applied"),
            "workflow_attempts": structured_metadata.get("workflow_attempts"),
            "workflow_context_strategies": structured_metadata.get("workflow_context_strategies"),
            "last_total_s": (structured_timings.get("total_s") if isinstance(structured_timings, dict) else None),
            "last_provider_s": (structured_timings.get("provider_total_s") if isinstance(structured_timings, dict) else None),
            "last_pre_model_prep_s": last_pre_model_prep_s,
            "last_document_load_s": (structured_timings.get("document_load_s") if isinstance(structured_timings, dict) else None),
            "last_sanitize_s": (structured_timings.get("sanitize_s") if isinstance(structured_timings, dict) else None),
            "last_context_s": (structured_timings.get("context_build_s") if isinstance(structured_timings, dict) else None),
            "last_parsing_s": (structured_timings.get("parsing_s") if isinstance(structured_timings, dict) else None),
            "last_context_chars": structured_metadata.get("context_chars_sent"),
            "last_full_document_chars": structured_metadata.get("full_document_chars"),
            "last_context_strategy": structured_metadata.get("context_strategy"),
            "last_total_tokens": structured_telemetry.get("budget_total_tokens") if isinstance(structured_telemetry, dict) else None,
            "last_cost_usd": structured_telemetry.get("budget_cost_usd") if isinstance(structured_telemetry, dict) else None,
            "budget_routing_mode": structured_telemetry.get("budget_routing_mode") if isinstance(structured_telemetry, dict) else None,
            "budget_routing_reason": structured_telemetry.get("budget_routing_reason") if isinstance(structured_telemetry, dict) else None,
            "budget_auto_degrade_applied": structured_telemetry.get("budget_auto_degrade_applied") if isinstance(structured_telemetry, dict) else None,
            "budget_alert_status": structured_telemetry.get("budget_alert_status") if isinstance(structured_telemetry, dict) else None,
            "budget_alerts": structured_telemetry.get("budget_alerts") if isinstance(structured_telemetry, dict) else None,
            "task_model_map": task_model_map,
        },
        "documents": {
            "loader_strategy": selected_loader_strategy,
            "chunking_strategy": selected_chunking_strategy,
            "retrieval_strategy": selected_retrieval_strategy,
            "pdf_extraction_mode": selected_pdf_extraction_mode,
            "ocr_backend_default": default_ocr_backend,
            "vl_model_default": default_vl_model,
            "indexed_documents": indexed_documents_count,
            "chat_selected_docs": build_document_runtime_rows(
                chat_selected_document_ids,
                document_preview_map,
                default_vl_model=default_vl_model,
                default_ocr_backend=default_ocr_backend,
            ),
            "structured_selected_docs": build_document_runtime_rows(
                structured_selected_document_ids,
                document_preview_map,
                default_vl_model=default_vl_model,
                default_ocr_backend=default_ocr_backend,
            ),
        },
        "document_agent": build_document_agent_runtime_summary(phase6_document_agent_log_path),
        "evidenceops": build_evidenceops_worklog_summary(phase95_evidenceops_worklog_path),
        "evidenceops_actions": build_evidenceops_action_store_summary(phase95_evidenceops_action_store_path),
        "evidenceops_repository": build_evidenceops_repository_summary(
            phase95_evidenceops_repository_root,
            snapshot_path=phase95_evidenceops_repository_snapshot_path,
        ),
        "evals": build_eval_runtime_summary(phase8_eval_db_path),
        "runtime_execution": build_runtime_execution_summary(runtime_execution_log_path),
    }