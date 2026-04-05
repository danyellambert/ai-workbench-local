from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import statistics
import time
from collections import defaultdict
from dataclasses import replace
from difflib import get_close_matches
from pathlib import Path
from typing import Any

from ..config import BASE_DIR, RagSettings, get_rag_settings
from ..providers.registry import resolve_provider_runtime_profile
from ..rag.loaders import _extract_pdf_text, _extract_pdf_text_with_evidence_pipeline, load_document
from ..rag.service import retrieve_relevant_chunks_detailed, upsert_documents_in_rag_index
from ..evidence_cv.config import build_evidence_config_from_rag_settings
from ..evidence_cv.pipeline.runner import run_cv_pipeline_from_bytes
from .model_comparison import (
    infer_model_comparison_quantization_family,
    infer_model_comparison_runtime_bucket,
    run_model_comparison_candidate,
)
from .phase8_5_benchmark_round2 import (
    aggregate_ocr_vlm_events,
    aggregate_reranker_events,
    build_ocr_vlm_cases,
    build_reranker_cases,
    build_round2_report_sections,
    execute_ocr_vlm_case,
    execute_reranker_case,
    normalize_round2_case_results,
    validate_round2_manifest_groups,
)
from .phase8_5_operational_metrics import build_operational_metrics_bundle
from .phase8_5_runtime_metadata import (
    build_runtime_family_metadata,
    summarize_runtime_family_artifacts,
)
from .phase8_5_timeout import TimeoutExecutionError, time_limit
from .runtime_snapshot import build_benchmark_environment_snapshot


DEFAULT_PHASE8_5_MANIFEST_PATH = BASE_DIR / "phase8_eval" / "configs" / "phase8_5_benchmark_matrix.json"
EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


class _LocalUploadedFile:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def slugify(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in str(value or ""))
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "item"


def stable_json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(payload: object, *, length: int = 12) -> str:
    return hashlib.sha256(stable_json_dumps(payload).encode("utf-8")).hexdigest()[:length]


def build_case_id(case_payload: dict[str, object]) -> str:
    identity = {
        "group": case_payload.get("group"),
        "provider": case_payload.get("provider"),
        "model": case_payload.get("model"),
        "requested_model": case_payload.get("requested_model"),
        "case_name": case_payload.get("case_name"),
        "use_case_id": case_payload.get("use_case_id"),
        "candidate_id": case_payload.get("candidate_id"),
        "repetition": case_payload.get("repetition"),
        "dataset_id": case_payload.get("dataset_id"),
        "question_set_id": case_payload.get("question_set_id"),
        "input_file": case_payload.get("input_file"),
        "prompt_profile": case_payload.get("prompt_profile"),
        "response_format": case_payload.get("response_format"),
        "temperature": case_payload.get("temperature"),
        "top_p": case_payload.get("top_p"),
        "max_output_tokens": case_payload.get("max_output_tokens"),
        "think": case_payload.get("think"),
        "context_window": case_payload.get("context_window"),
        "embedding_context_window": case_payload.get("embedding_context_window"),
        "chunk_size": case_payload.get("chunk_size"),
        "chunk_overlap": case_payload.get("chunk_overlap"),
        "top_k": case_payload.get("top_k"),
        "rerank_pool_size": case_payload.get("rerank_pool_size"),
        "rerank_lexical_weight": case_payload.get("rerank_lexical_weight"),
        "model_resolution_status": case_payload.get("model_resolution_status"),
    }
    return f"case_{stable_hash(identity, length=16)}"


def build_run_id(
    manifest: dict[str, object],
    *,
    selected_groups: list[str],
    provider_filter: str | None,
    model_filter: str | None,
    smoke: bool,
) -> str:
    manifest_fingerprint_source = {
        key: value
        for key, value in manifest.items()
        if key != "_manifest_path"
    }
    identity = {
        "benchmark_id": manifest.get("benchmark_id"),
        "manifest_version": manifest.get("manifest_version"),
        "manifest_fingerprint": stable_hash(manifest_fingerprint_source, length=16),
        "selected_groups": sorted(selected_groups),
        "provider_filter": str(provider_filter or "").strip().lower() or None,
        "model_filter": str(model_filter or "").strip() or None,
        "smoke": bool(smoke),
    }
    return f"{slugify(str(manifest.get('benchmark_id') or 'phase8-5'))}-{stable_hash(identity, length=10)}"


def resolve_repo_path(path_value: str | Path, *, project_root: Path = BASE_DIR) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return (project_root / candidate).resolve()


def collect_relevant_environment_values() -> dict[str, object]:
    relevant_keys = [
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "OLLAMA_CONTEXT_WINDOW",
        "OLLAMA_TOP_P",
        "OLLAMA_MAX_TOKENS",
        "OLLAMA_HTTP_TIMEOUT_SECONDS",
        "OLLAMA_EMBED_BATCH_SIZE",
        "RAG_EMBEDDING_PROVIDER",
        "RAG_EMBEDDING_MODEL",
        "RAG_EMBEDDING_CONTEXT_WINDOW",
        "RAG_EMBEDDING_TRUNCATE",
        "RAG_CHUNK_SIZE",
        "RAG_CHUNK_OVERLAP",
        "RAG_TOP_K",
        "RAG_RERANK_POOL_SIZE",
        "RAG_RERANK_LEXICAL_WEIGHT",
        "OPENAI_MODEL",
        "OPENAI_CONTEXT_WINDOW",
        "HUGGINGFACE_MODEL",
        "HUGGINGFACE_AVAILABLE_MODELS",
        "HUGGINGFACE_CONTEXT_WINDOW",
        "HUGGINGFACE_EMBEDDING_MODEL",
        "HUGGINGFACE_AVAILABLE_EMBEDDING_MODELS",
        "HUGGINGFACE_SERVER_BASE_URL",
        "HUGGINGFACE_SERVER_MODEL",
        "HUGGINGFACE_SERVER_AVAILABLE_MODELS",
        "HUGGINGFACE_SERVER_CONTEXT_WINDOW",
        "HUGGINGFACE_SERVER_EMBEDDING_MODEL",
        "HUGGINGFACE_SERVER_AVAILABLE_EMBEDDING_MODELS",
        "HUGGINGFACE_INFERENCE_MODEL",
        "HUGGINGFACE_INFERENCE_CONTEXT_WINDOW",
        "OLLAMA_AVAILABLE_MODELS",
        "OLLAMA_AVAILABLE_EMBEDDING_MODELS",
    ]
    return {
        key: (str(os.getenv(key, "")).strip() or None)
        for key in relevant_keys
    }


def load_benchmark_manifest(path: str | Path = DEFAULT_PHASE8_5_MANIFEST_PATH) -> dict[str, object]:
    resolved_path = resolve_repo_path(path)
    payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Phase 8.5 benchmark manifest must be a JSON object.")
    validate_benchmark_manifest(payload, project_root=BASE_DIR)
    payload["_manifest_path"] = str(resolved_path)
    return payload


def validate_benchmark_manifest(manifest: dict[str, object], *, project_root: Path = BASE_DIR) -> None:
    required_top_level = [
        "benchmark_id",
        "manifest_version",
        "groups",
        "model_resolution_policy",
        "fairness",
        "timeout_policy",
        "output_directory_policy",
        "resume_policy",
    ]
    missing_top_level = [key for key in required_top_level if key not in manifest]
    if missing_top_level:
        raise ValueError(f"Manifest missing required keys: {', '.join(missing_top_level)}")

    groups = manifest.get("groups")
    if not isinstance(groups, dict) or not groups:
        raise ValueError("Manifest 'groups' must be a non-empty object.")

    resolution_policy = manifest.get("model_resolution_policy")
    if not isinstance(resolution_policy, dict):
        raise ValueError("Manifest 'model_resolution_policy' must be an object.")

    generation_group = groups.get("generation")
    if generation_group is not None:
        if not isinstance(generation_group, dict):
            raise ValueError("Manifest group 'generation' must be an object.")
        provider_pairs = generation_group.get("provider_model_pairs")
        use_case_groups = generation_group.get("use_case_groups")
        if not isinstance(provider_pairs, list) or not provider_pairs:
            raise ValueError("Manifest generation.provider_model_pairs must be a non-empty list.")
        if not isinstance(use_case_groups, list) or not use_case_groups:
            raise ValueError("Manifest generation.use_case_groups must be a non-empty list.")
        for pair in provider_pairs:
            if not isinstance(pair, dict) or not str(pair.get("provider") or "").strip() or not str(pair.get("model") or "").strip():
                raise ValueError("Each generation provider/model pair must include non-empty 'provider' and 'model'.")
            candidate_models = pair.get("candidate_models")
            if candidate_models is not None and not isinstance(candidate_models, list):
                raise ValueError("Generation provider/model pair 'candidate_models' must be a list when provided.")
        for use_case_group in use_case_groups:
            if not isinstance(use_case_group, dict) or not isinstance(use_case_group.get("cases"), list):
                raise ValueError("Each generation use_case_group must contain a 'cases' list.")
            for case in use_case_group.get("cases") or []:
                if not isinstance(case, dict):
                    raise ValueError("Generation case definitions must be objects.")
                required_case_keys = ["use_case_id", "benchmark_use_case", "prompt_profile", "response_format", "input_file", "prompt_template"]
                missing_case_keys = [key for key in required_case_keys if not str(case.get(key) or "").strip()]
                if missing_case_keys:
                    raise ValueError(
                        f"Generation case '{case}' missing keys: {', '.join(missing_case_keys)}"
                    )
                input_path = resolve_repo_path(str(case.get("input_file")), project_root=project_root)
                if not input_path.exists():
                    raise ValueError(f"Generation case input file not found: {input_path}")

    embeddings_group = groups.get("embeddings")
    if embeddings_group is not None:
        if not isinstance(embeddings_group, dict):
            raise ValueError("Manifest group 'embeddings' must be an object.")
        candidates = embeddings_group.get("embedding_candidates")
        dataset = embeddings_group.get("dataset")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError("Manifest embeddings.embedding_candidates must be a non-empty list.")
        if not isinstance(dataset, dict):
            raise ValueError("Manifest embeddings.dataset must be an object.")
        pdf_paths = dataset.get("pdf_paths")
        question_set_path = dataset.get("question_set_path")
        if not isinstance(pdf_paths, list) or not pdf_paths:
            raise ValueError("Manifest embeddings.dataset.pdf_paths must be a non-empty list.")
        if not str(question_set_path or "").strip():
            raise ValueError("Manifest embeddings.dataset.question_set_path must be configured.")
        for candidate in candidates:
            if not isinstance(candidate, dict) or not str(candidate.get("provider") or "").strip() or not str(candidate.get("model") or "").strip():
                raise ValueError("Each embedding candidate must include non-empty 'provider' and 'model'.")
            candidate_models = candidate.get("candidate_models")
            if candidate_models is not None and not isinstance(candidate_models, list):
                raise ValueError("Embedding candidate 'candidate_models' must be a list when provided.")
        for pdf_path in pdf_paths:
            resolved_pdf_path = resolve_repo_path(str(pdf_path), project_root=project_root)
            if not resolved_pdf_path.exists():
                raise ValueError(f"Embedding dataset PDF not found: {resolved_pdf_path}")
        resolved_question_set_path = resolve_repo_path(str(question_set_path), project_root=project_root)
        if not resolved_question_set_path.exists():
            raise ValueError(f"Embedding question set not found: {resolved_question_set_path}")

    validate_round2_manifest_groups(manifest)


def _discover_provider_models(
    provider_key: str,
    provider_entry: dict[str, object],
    *,
    capability: str,
) -> list[str]:
    provider_instance = provider_entry.get("instance")
    if provider_instance is None:
        return []
    if provider_key == "ollama" and hasattr(provider_instance, "_discover_local_models"):
        try:
            discovered = list(provider_instance._discover_local_models())  # type: ignore[attr-defined]
        except Exception:
            discovered = []
        if capability == "embeddings" and hasattr(provider_instance, "_looks_like_embedding_model"):
            return [
                model
                for model in discovered
                if provider_instance._looks_like_embedding_model(model)  # type: ignore[attr-defined]
            ]
        return discovered
    if provider_key == "huggingface_server":
        if capability == "chat" and hasattr(provider_instance, "_catalog_chat_models"):
            try:
                return list(provider_instance._catalog_chat_models())  # type: ignore[attr-defined]
            except Exception:
                return []
        if capability == "embeddings" and hasattr(provider_instance, "_catalog_embedding_models"):
            try:
                return list(provider_instance._catalog_embedding_models())  # type: ignore[attr-defined]
            except Exception:
                return []
    if capability == "embeddings" and hasattr(provider_instance, "list_available_embedding_models"):
        try:
            return list(provider_instance.list_available_embedding_models())
        except Exception:
            return []
    if capability == "chat" and hasattr(provider_instance, "list_available_models"):
        try:
            return list(provider_instance.list_available_models())
        except Exception:
            return []
    return []


def _candidate_supports_embedding_subset(candidate_role: str, subset_kind: str) -> bool:
    normalized_role = str(candidate_role or "").strip().lower()
    normalized_subset = str(subset_kind or "general").strip().lower() or "general"
    if "code" in normalized_role:
        return normalized_subset == "code"
    if normalized_role.startswith("baseline"):
        return True
    if "general" in normalized_role:
        return normalized_subset == "general"
    return True


def _load_embedding_dataset_subsets(
    dataset: dict[str, object],
    *,
    smoke_limits: dict[str, object],
    smoke: bool,
) -> list[dict[str, object]]:
    configured_subsets = [item for item in (dataset.get("subsets") or []) if isinstance(item, dict)]
    subset_specs = configured_subsets or [
        {
            "subset_id": str(dataset.get("dataset_id") or "phase8_embedding_dataset"),
            "subset_label": str(dataset.get("dataset_id") or "phase8_embedding_dataset"),
            "subset_kind": "general",
            "document_paths": list(dataset.get("pdf_paths") or []),
            "question_set_path": dataset.get("question_set_path"),
        }
    ]

    prepared: list[dict[str, object]] = []
    for subset in subset_specs:
        document_paths = [resolve_repo_path(str(item)) for item in (subset.get("document_paths") or subset.get("pdf_paths") or [])]
        question_set_path = resolve_repo_path(str(subset.get("question_set_path") or dataset.get("question_set_path") or ""))
        question_payload = json.loads(question_set_path.read_text(encoding="utf-8"))
        questions = [item for item in (question_payload.get("questions") or []) if isinstance(item, dict)]
        if smoke:
            document_paths = document_paths[: max(1, int(smoke_limits.get("max_pdfs") or 1))]
            questions = questions[: max(1, int(smoke_limits.get("max_questions") or 1))]
        prepared.append(
            {
                "subset_id": str(subset.get("subset_id") or question_set_path.stem),
                "subset_label": str(subset.get("subset_label") or subset.get("subset_id") or question_set_path.stem),
                "subset_kind": str(subset.get("subset_kind") or "general"),
                "document_paths": [str(path) for path in document_paths],
                "question_set_path": str(question_set_path),
                "question_set_id": str(subset.get("question_set_id") or question_set_path.stem),
                "questions": questions,
            }
        )
    return prepared


def _clean_model_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    ordered: list[str] = []
    for item in values:
        normalized = str(item or "").strip()
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered


def _match_available_model_name(candidate: str | None, available_models: list[str]) -> str | None:
    normalized_candidate = str(candidate or "").strip().lower()
    if not normalized_candidate:
        return None
    for available_model in available_models:
        normalized_available = str(available_model or "").strip()
        if normalized_available.lower() == normalized_candidate:
            return normalized_available
    return None


def _heuristic_closest_available_model(candidate_options: list[str], available_models: list[str]) -> str | None:
    if not candidate_options or not available_models:
        return None
    lowered_available = {str(item).strip().lower(): str(item).strip() for item in available_models if str(item).strip()}
    for candidate in candidate_options:
        matches = get_close_matches(str(candidate).strip().lower(), list(lowered_available.keys()), n=1, cutoff=0.55)
        if matches:
            return lowered_available[matches[0]]
    return None


def _candidate_model_options(
    manifest: dict[str, object],
    candidate_entry: dict[str, object],
    *,
    requested_model: str,
) -> list[str]:
    ordered: list[str] = []

    def _append(value: str | None) -> None:
        normalized = str(value or "").strip()
        if normalized and normalized not in ordered:
            ordered.append(normalized)

    _append(requested_model)
    for item in _clean_model_list(candidate_entry.get("candidate_models")):
        _append(item)
    _append(str(candidate_entry.get("model") or ""))

    resolution_policy = manifest.get("model_resolution_policy") if isinstance(manifest.get("model_resolution_policy"), dict) else {}
    default_requested_map = (
        resolution_policy.get("default_requested_to_candidate_models")
        if isinstance(resolution_policy.get("default_requested_to_candidate_models"), dict)
        else {}
    )
    for item in _clean_model_list(default_requested_map.get(requested_model)):
        _append(item)
    return ordered


def resolve_requested_model(
    manifest: dict[str, object],
    candidate_entry: dict[str, object],
    *,
    requested_model: str,
    available_models: list[str],
) -> dict[str, object]:
    resolution_policy = manifest.get("model_resolution_policy") if isinstance(manifest.get("model_resolution_policy"), dict) else {}
    heuristic_enabled = bool(resolution_policy.get("heuristic_closest_match_enabled", True))
    candidate_model_options = _candidate_model_options(
        manifest,
        candidate_entry,
        requested_model=requested_model,
    )

    if available_models:
        for candidate_model in candidate_model_options:
            matched = _match_available_model_name(candidate_model, available_models)
            if matched:
                return {
                    "requested_model": requested_model,
                    "model_resolved": matched,
                    "mapping_status": "exact" if matched.lower() == requested_model.lower() else "closest_available",
                    "resolution_source": "provider_inventory",
                    "candidate_model_options": candidate_model_options,
                    "available_models": available_models,
                }

        if heuristic_enabled:
            heuristic_match = _heuristic_closest_available_model(candidate_model_options, available_models)
            if heuristic_match:
                return {
                    "requested_model": requested_model,
                    "model_resolved": heuristic_match,
                    "mapping_status": "closest_available",
                    "resolution_source": "heuristic_provider_inventory",
                    "candidate_model_options": candidate_model_options,
                    "available_models": available_models,
                }

        return {
            "requested_model": requested_model,
            "model_resolved": None,
            "mapping_status": "skipped",
            "resolution_source": "provider_inventory",
            "candidate_model_options": candidate_model_options,
            "available_models": available_models,
        }

    explicit_manifest_fallback = str(candidate_entry.get("model") or "").strip()
    explicit_candidate_models = _clean_model_list(candidate_entry.get("candidate_models"))
    fallback_model = (
        explicit_manifest_fallback
        or (explicit_candidate_models[0] if explicit_candidate_models else None)
        or (candidate_model_options[0] if candidate_model_options else None)
        or requested_model
    )
    return {
        "requested_model": requested_model,
        "model_resolved": fallback_model,
        "mapping_status": "exact" if fallback_model.lower() == requested_model.lower() else "closest_available",
        "resolution_source": "manifest_assumption_without_inventory",
        "candidate_model_options": candidate_model_options,
        "available_models": available_models,
    }


def _inspect_runtime_artifact(
    provider_entry: dict[str, object],
    *,
    capability: str,
    model: str,
    requested_context_window: int | None,
) -> dict[str, object]:
    provider_instance = provider_entry.get("instance")
    if provider_instance is None:
        return {}
    try:
        if capability == "embeddings" and hasattr(provider_instance, "inspect_embedding_context_window"):
            artifact = provider_instance.inspect_embedding_context_window(model, requested_context_window=requested_context_window)
            return artifact if isinstance(artifact, dict) else {}
        if capability == "chat" and hasattr(provider_instance, "inspect_context_window"):
            artifact = provider_instance.inspect_context_window(model, requested_context_window=requested_context_window)
            return artifact if isinstance(artifact, dict) else {}
    except Exception as error:
        return {"inspection_error": str(error)}
    return {}


def _build_generation_context_chunks(text: str, *, source: str, chunk_size: int = 700) -> list[dict[str, object]]:
    normalized = str(text or "").strip()
    if not normalized:
        return []
    chunks: list[dict[str, object]] = []
    start = 0
    index = 1
    while start < len(normalized):
        chunk_text = normalized[start : start + chunk_size]
        chunks.append(
            {
                "document_id": slugify(source),
                "chunk_id": index,
                "source": source,
                "text": chunk_text,
                "snippet": chunk_text[:280],
            }
        )
        start += chunk_size
        index += 1
    return chunks


def _apply_smoke_limit(items: list[dict[str, object]], *, max_items: int | None) -> list[dict[str, object]]:
    if not isinstance(max_items, int) or max_items <= 0:
        return list(items)
    return list(items[:max_items])


def build_generation_cases(
    manifest: dict[str, object],
    *,
    registry: dict[str, dict[str, object]],
    smoke: bool,
    provider_filter: str | None = None,
    model_filter: str | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    generation_group = groups.get("generation") if isinstance(groups.get("generation"), dict) else {}
    fairness = manifest.get("fairness") if isinstance(manifest.get("fairness"), dict) else {}
    smoke_limits = generation_group.get("smoke_limits") if isinstance(generation_group.get("smoke_limits"), dict) else {}
    selected_provider_pairs = [
        item
        for item in (generation_group.get("provider_model_pairs") or [])
        if isinstance(item, dict)
    ]
    if provider_filter:
        normalized_provider_filter = str(provider_filter).strip().lower()
        selected_provider_pairs = [
            item
            for item in selected_provider_pairs
            if str(item.get("provider") or "").strip().lower() == normalized_provider_filter
        ]
    if model_filter:
        normalized_model_filter = str(model_filter).strip()
        selected_provider_pairs = [
            item
            for item in selected_provider_pairs
            if normalized_model_filter in {
                str(item.get("model") or "").strip(),
                str(item.get("requested_model") or "").strip(),
            }
        ]
    selected_use_case_groups = [
        item
        for item in (generation_group.get("use_case_groups") or [])
        if isinstance(item, dict)
    ]
    if smoke:
        selected_provider_pairs = _apply_smoke_limit(
            selected_provider_pairs,
            max_items=int(smoke_limits.get("max_provider_model_pairs") or 0),
        )
    flattened_use_cases: list[dict[str, object]] = []
    for use_case_group in selected_use_case_groups:
        group_id = str(use_case_group.get("group_id") or "generation")
        group_label = str(use_case_group.get("label") or group_id)
        for case in use_case_group.get("cases") or []:
            if not isinstance(case, dict):
                continue
            flattened_use_cases.append(
                {
                    **case,
                    "group_id": group_id,
                    "group_label": group_label,
                }
            )
    if smoke:
        flattened_use_cases = _apply_smoke_limit(
            flattened_use_cases,
            max_items=int(smoke_limits.get("max_use_cases") or 0),
        )

    repetitions = int(generation_group.get("repetitions") or 1)
    if smoke:
        repetitions = int(smoke_limits.get("repetitions") or 1)

    cases: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for provider_pair in selected_provider_pairs:
        provider = str(provider_pair.get("provider") or "").strip().lower()
        requested_model = str(provider_pair.get("requested_model") or provider_pair.get("model") or "").strip()
        provider_entry = registry.get(provider)
        if not isinstance(provider_entry, dict) or not bool(provider_entry.get("supports_chat")):
            skipped.append(
                {
                    "group": "generation",
                    "provider": provider,
                    "model": requested_model,
                    "requested_model": requested_model,
                    "reason": "provider_unavailable_or_no_chat_support",
                }
            )
            continue
        available_models = _discover_provider_models(provider, provider_entry, capability="chat")
        resolution = resolve_requested_model(
            manifest,
            provider_pair,
            requested_model=requested_model,
            available_models=available_models,
        )
        model = str(resolution.get("model_resolved") or "").strip()
        if resolution.get("mapping_status") == "skipped" or not model:
            skipped.append(
                {
                    "group": "generation",
                    "provider": provider,
                    "model": requested_model,
                    "requested_model": requested_model,
                    "reason": "model_not_available_for_provider",
                    "available_models": available_models,
                    "candidate_model_options": resolution.get("candidate_model_options"),
                    "mapping_status": resolution.get("mapping_status"),
                    "resolution_source": resolution.get("resolution_source"),
                }
            )
            continue

        for use_case in flattened_use_cases:
            input_path = resolve_repo_path(str(use_case.get("input_file")))
            input_text = input_path.read_text(encoding="utf-8")
            rendered_prompt = str(use_case.get("prompt_template") or "").format(input_text=input_text.strip())
            for repetition in range(1, repetitions + 1):
                case_payload = {
                    "group": "generation",
                    "provider": provider,
                    "model": model,
                    "requested_model": requested_model,
                    "case_name": str(use_case.get("use_case_id") or "generation_case"),
                    "use_case_id": str(use_case.get("use_case_id") or "generation_case"),
                    "input_file": str(input_path),
                    "prompt_profile": use_case.get("prompt_profile"),
                    "response_format": use_case.get("response_format"),
                    "temperature": fairness.get("temperature"),
                    "top_p": fairness.get("top_p"),
                    "max_output_tokens": fairness.get("max_output_tokens"),
                    "context_window": fairness.get("context_window"),
                    "repetition": repetition,
                }
                cases.append(
                    {
                        "case_id": build_case_id(case_payload),
                        "group": "generation",
                        "provider": provider,
                        "model": model,
                        "requested_model": requested_model,
                        "requested_runtime_family": provider_pair.get("requested_runtime_family"),
                        "model_resolution_status": resolution.get("mapping_status"),
                        "model_resolution_source": resolution.get("resolution_source"),
                        "requested_model_candidates": resolution.get("candidate_model_options") or [],
                        "provider_label": provider_entry.get("label"),
                        "group_id": use_case.get("group_id"),
                        "group_label": use_case.get("group_label"),
                        "use_case_id": use_case.get("use_case_id"),
                        "use_case_label": use_case.get("label") or use_case.get("use_case_id"),
                        "benchmark_use_case": use_case.get("benchmark_use_case"),
                        "prompt_profile": use_case.get("prompt_profile"),
                        "response_format": use_case.get("response_format"),
                        "structured_output_mode": use_case.get("structured_output_mode") or fairness.get("structured_output_mode"),
                        "input_file": str(input_path),
                        "input_chars": len(input_text),
                        "prompt_text": rendered_prompt,
                        "context_chunks": _build_generation_context_chunks(input_text, source=input_path.name),
                        "temperature": fairness.get("temperature"),
                        "top_p": fairness.get("top_p"),
                        "max_output_tokens": fairness.get("max_output_tokens"),
                        "think": fairness.get("think"),
                        "context_window": fairness.get("context_window"),
                        "seed": fairness.get("seed"),
                        "seed_supported": fairness.get("seed_supported"),
                        "repetition": repetition,
                    }
                )
    return cases, skipped


def build_embedding_cases(
    manifest: dict[str, object],
    *,
    registry: dict[str, dict[str, object]],
    smoke: bool,
    provider_filter: str | None = None,
    model_filter: str | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    embeddings_group = groups.get("embeddings") if isinstance(groups.get("embeddings"), dict) else {}
    dataset = embeddings_group.get("dataset") if isinstance(embeddings_group.get("dataset"), dict) else {}
    fairness = manifest.get("fairness") if isinstance(manifest.get("fairness"), dict) else {}
    smoke_limits = embeddings_group.get("smoke_limits") if isinstance(embeddings_group.get("smoke_limits"), dict) else {}
    candidate_entries = [
        item
        for item in (embeddings_group.get("embedding_candidates") or [])
        if isinstance(item, dict)
    ]
    if provider_filter:
        normalized_provider_filter = str(provider_filter).strip().lower()
        candidate_entries = [
            item
            for item in candidate_entries
            if str(item.get("provider") or "").strip().lower() == normalized_provider_filter
        ]
    if model_filter:
        normalized_model_filter = str(model_filter).strip()
        candidate_entries = [
            item
            for item in candidate_entries
            if normalized_model_filter in {
                str(item.get("model") or "").strip(),
                str(item.get("requested_model") or "").strip(),
            }
        ]
    if smoke:
        candidate_entries = _apply_smoke_limit(
            candidate_entries,
            max_items=int(smoke_limits.get("max_candidates") or 0),
        )

    subset_specs = _load_embedding_dataset_subsets(
        dataset,
        smoke_limits=smoke_limits,
        smoke=smoke,
    )

    repetitions = int(embeddings_group.get("repetitions") or 1)
    if smoke:
        repetitions = int(smoke_limits.get("repetitions") or 1)

    cases: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for candidate in candidate_entries:
        provider = str(candidate.get("provider") or "").strip().lower()
        requested_model = str(candidate.get("requested_model") or candidate.get("model") or "").strip()
        provider_entry = registry.get(provider)
        if not isinstance(provider_entry, dict) or not bool(provider_entry.get("supports_embeddings")):
            skipped.append(
                {
                    "group": "embeddings",
                    "provider": provider,
                    "model": requested_model,
                    "requested_model": requested_model,
                    "reason": "provider_unavailable_or_no_embedding_support",
                }
            )
            continue
        available_models = _discover_provider_models(provider, provider_entry, capability="embeddings")
        resolution = resolve_requested_model(
            manifest,
            candidate,
            requested_model=requested_model,
            available_models=available_models,
        )
        model = str(resolution.get("model_resolved") or "").strip()
        if resolution.get("mapping_status") == "skipped" or not model:
            skipped.append(
                {
                    "group": "embeddings",
                    "provider": provider,
                    "model": requested_model,
                    "requested_model": requested_model,
                    "reason": "model_not_available_for_provider",
                    "available_models": available_models,
                    "candidate_model_options": resolution.get("candidate_model_options"),
                    "mapping_status": resolution.get("mapping_status"),
                    "resolution_source": resolution.get("resolution_source"),
                }
            )
            continue

        candidate_role = str(candidate.get("role") or "challenger")
        for subset in subset_specs:
            subset_id = str(subset.get("subset_id") or "default")
            subset_kind = str(subset.get("subset_kind") or "general")
            if not _candidate_supports_embedding_subset(candidate_role, subset_kind):
                continue
            for repetition in range(1, repetitions + 1):
                case_payload = {
                    "group": "embeddings",
                    "provider": provider,
                    "model": model,
                    "requested_model": requested_model,
                    "case_name": str(candidate.get("candidate_id") or model),
                    "candidate_id": str(candidate.get("candidate_id") or model),
                    "dataset_id": str(dataset.get("dataset_id") or "phase8_embedding_dataset"),
                    "question_set_id": str(subset.get("question_set_id") or subset_id),
                    "embedding_context_window": fairness.get("embedding_context_window"),
                    "chunk_size": fairness.get("chunk_size"),
                    "chunk_overlap": fairness.get("chunk_overlap"),
                    "top_k": fairness.get("top_k"),
                    "rerank_pool_size": fairness.get("rerank_pool_size"),
                    "rerank_lexical_weight": fairness.get("rerank_lexical_weight"),
                    "repetition": repetition,
                }
                cases.append(
                    {
                        "case_id": build_case_id(case_payload),
                        "group": "embeddings",
                        "provider": provider,
                        "model": model,
                        "requested_model": requested_model,
                        "requested_runtime_family": candidate.get("requested_runtime_family"),
                        "model_resolution_status": resolution.get("mapping_status"),
                        "model_resolution_source": resolution.get("resolution_source"),
                        "requested_model_candidates": resolution.get("candidate_model_options") or [],
                        "provider_label": provider_entry.get("label"),
                        "candidate_id": candidate.get("candidate_id") or model,
                        "candidate_role": candidate_role,
                        "dataset_id": dataset.get("dataset_id") or "phase8_embedding_dataset",
                        "subset_id": subset_id,
                        "subset_label": subset.get("subset_label") or subset_id,
                        "subset_kind": subset_kind,
                        "question_set_id": subset.get("question_set_id") or subset_id,
                        "document_paths": list(subset.get("document_paths") or []),
                        "pdf_paths": list(subset.get("document_paths") or []),
                        "questions": list(subset.get("questions") or []),
                        "question_set_path": str(subset.get("question_set_path") or ""),
                        "embedding_context_window": fairness.get("embedding_context_window"),
                        "embedding_truncate": fairness.get("embedding_truncate"),
                        "chunk_size": fairness.get("chunk_size"),
                        "chunk_overlap": fairness.get("chunk_overlap"),
                        "top_k": fairness.get("top_k"),
                        "rerank_pool_size": fairness.get("rerank_pool_size"),
                        "rerank_lexical_weight": fairness.get("rerank_lexical_weight"),
                        "pdf_extraction_mode": dataset.get("pdf_extraction_mode") or "basic",
                        "pdf_docling_enabled": bool(dataset.get("pdf_docling_enabled", False)),
                        "pdf_ocr_fallback_enabled": bool(dataset.get("pdf_ocr_fallback_enabled", False)),
                        "pdf_scan_image_ocr_enabled": bool(dataset.get("pdf_scan_image_ocr_enabled", False)),
                        "pdf_evidence_pipeline_enabled": bool(dataset.get("pdf_evidence_pipeline_enabled", False)),
                        "repetition": repetition,
                    }
                )

    return cases, skipped


def load_successful_case_ids(events_path: str | Path) -> set[str]:
    resolved_path = Path(events_path)
    if not resolved_path.exists():
        return set()
    successful_case_ids: set[str] = set()
    for line in resolved_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("event_type") != "case_result":
            continue
        if payload.get("status") == "success" and str(payload.get("case_id") or "").strip():
            successful_case_ids.add(str(payload.get("case_id")))
    return successful_case_ids


def append_jsonl_record(path: str | Path, payload: dict[str, object]) -> None:
    resolved_path = Path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    with resolved_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_case_result_events(events_path: str | Path) -> list[dict[str, object]]:
    resolved_path = Path(events_path)
    if not resolved_path.exists():
        return []
    results: list[dict[str, object]] = []
    for line in resolved_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("event_type") == "case_result":
            results.append(payload)
    return results


def select_latest_case_result_events(events: list[dict[str, object]]) -> list[dict[str, object]]:
    latest_by_case_id: dict[str, dict[str, object]] = {}
    for event in events:
        case_id = str(event.get("case_id") or "").strip()
        if not case_id:
            continue
        candidate_timestamp = float(event.get("finished_at") or event.get("started_at") or 0.0)
        current = latest_by_case_id.get(case_id)
        current_timestamp = float(current.get("finished_at") or current.get("started_at") or 0.0) if isinstance(current, dict) else -1.0
        if current is None or candidate_timestamp >= current_timestamp:
            latest_by_case_id[case_id] = event
    return sorted(
        latest_by_case_id.values(),
        key=lambda item: (
            str(item.get("group") or ""),
            float(item.get("finished_at") or item.get("started_at") or 0.0),
            str(item.get("case_id") or ""),
        ),
    )


def build_preflight_payload(
    manifest: dict[str, object],
    *,
    registry: dict[str, dict[str, object]],
    run_id: str,
    output_dir: Path,
    selected_groups: list[str],
    smoke: bool,
    provider_filter: str | None,
    model_filter: str | None,
    resume: bool,
) -> dict[str, object]:
    generation_cases, generation_skipped = build_generation_cases(
        manifest,
        registry=registry,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    embedding_cases, embedding_skipped = build_embedding_cases(
        manifest,
        registry=registry,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    reranker_cases = build_reranker_cases(
        manifest,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    ocr_vlm_cases = build_ocr_vlm_cases(
        manifest,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    selected_case_count = 0
    if "generation" in selected_groups:
        selected_case_count += len(generation_cases)
    if "embeddings" in selected_groups:
        selected_case_count += len(embedding_cases)
    if "rerankers" in selected_groups:
        selected_case_count += len(reranker_cases)
    if "ocr_vlm" in selected_groups:
        selected_case_count += len(ocr_vlm_cases)

    raw_events_path = output_dir / "raw" / "events.jsonl"
    successful_case_ids = load_successful_case_ids(raw_events_path)
    return {
        "run_id": run_id,
        "output_dir": str(output_dir),
        "selected_groups": selected_groups,
        "smoke": bool(smoke),
        "provider_filter": provider_filter,
        "model_filter": model_filter,
        "resume_requested": bool(resume),
        "planned_case_count": selected_case_count,
        "resume_success_case_count": len(successful_case_ids),
        "groups": {
            "generation": {
                "planned_cases": len(generation_cases),
                "skipped_candidates": generation_skipped,
                "sample_case_ids": [case.get("case_id") for case in generation_cases[:5]],
            },
            "embeddings": {
                "planned_cases": len(embedding_cases),
                "skipped_candidates": embedding_skipped,
                "sample_case_ids": [case.get("case_id") for case in embedding_cases[:5]],
            },
            "rerankers": {
                "planned_cases": len(reranker_cases),
                "skipped_candidates": [],
                "sample_case_ids": [case.get("case_id") for case in reranker_cases[:5]],
            },
            "ocr_vlm": {
                "planned_cases": len(ocr_vlm_cases),
                "skipped_candidates": [],
                "sample_case_ids": [case.get("case_id") for case in ocr_vlm_cases[:5]],
            },
        },
    }


def _build_isolated_rag_settings(case: dict[str, object], case_dir: Path) -> RagSettings:
    base_settings = get_rag_settings()
    embedding_truncate = case.get("embedding_truncate")
    return replace(
        base_settings,
        embedding_provider=str(case.get("provider") or base_settings.embedding_provider),
        embedding_model=str(case.get("model") or base_settings.embedding_model),
        embedding_context_window=int(case.get("embedding_context_window") or base_settings.embedding_context_window),
        embedding_truncate=(
            bool(embedding_truncate)
            if isinstance(embedding_truncate, bool)
            else base_settings.embedding_truncate
        ),
        chunk_size=int(case.get("chunk_size") or base_settings.chunk_size),
        chunk_overlap=int(case.get("chunk_overlap") or base_settings.chunk_overlap),
        top_k=int(case.get("top_k") or base_settings.top_k),
        rerank_pool_size=int(case.get("rerank_pool_size") or base_settings.rerank_pool_size),
        rerank_lexical_weight=float(case.get("rerank_lexical_weight") or base_settings.rerank_lexical_weight),
        pdf_extraction_mode=str(case.get("pdf_extraction_mode") or base_settings.pdf_extraction_mode),
        pdf_docling_enabled=bool(case.get("pdf_docling_enabled", base_settings.pdf_docling_enabled)),
        pdf_ocr_fallback_enabled=bool(case.get("pdf_ocr_fallback_enabled", base_settings.pdf_ocr_fallback_enabled)),
        pdf_scan_image_ocr_enabled=bool(case.get("pdf_scan_image_ocr_enabled", base_settings.pdf_scan_image_ocr_enabled)),
        pdf_evidence_pipeline_enabled=bool(case.get("pdf_evidence_pipeline_enabled", base_settings.pdf_evidence_pipeline_enabled)),
        store_path=case_dir / ".rag_store.json",
        chroma_path=case_dir / ".chroma_rag",
    )


def _run_embedding_questions(
    *,
    questions: list[dict[str, object]],
    rag_index: dict[str, object],
    settings: RagSettings,
    embedding_provider: object,
    query_timeout_s: int | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    per_question_results: list[dict[str, object]] = []
    retrieval_latencies: list[float] = []
    hit_at_1_values: list[int] = []
    hit_at_k_values: list[int] = []
    reciprocal_ranks: list[float] = []

    for item in questions:
        question = str(item.get("question") or "")
        expected_document_names = {str(name) for name in item.get("expected_document_names", [])}
        started_at = time.perf_counter()
        with time_limit(
            query_timeout_s,
            f"embedding query timeout after {query_timeout_s}s",
        ):
            retrieval_details = retrieve_relevant_chunks_detailed(
                query=question,
                rag_index=rag_index,
                settings=settings,
                embedding_provider=embedding_provider,
            )
        retrieval_seconds = time.perf_counter() - started_at
        retrieval_latencies.append(retrieval_seconds)

        chunks = retrieval_details.get("chunks", []) if isinstance(retrieval_details.get("chunks"), list) else []
        retrieved_names = [str(chunk.get("source") or "") for chunk in chunks if isinstance(chunk, dict)]
        hit_at_1 = bool(retrieved_names[:1] and retrieved_names[0] in expected_document_names)
        hit_at_k = any(name in expected_document_names for name in retrieved_names[: settings.top_k])

        reciprocal_rank = 0.0
        first_relevant_rank = None
        for rank, name in enumerate(retrieved_names, start=1):
            if name in expected_document_names:
                reciprocal_rank = 1.0 / rank
                first_relevant_rank = rank
                break

        hit_at_1_values.append(1 if hit_at_1 else 0)
        hit_at_k_values.append(1 if hit_at_k else 0)
        reciprocal_ranks.append(float(reciprocal_rank))
        per_question_results.append(
            {
                "question": question,
                "expected_document_names": sorted(expected_document_names),
                "retrieved_names": retrieved_names,
                "hit_at_1": hit_at_1,
                "hit_at_k": hit_at_k,
                "reciprocal_rank": round(reciprocal_rank, 4),
                "first_relevant_rank": first_relevant_rank,
                "retrieval_seconds": round(retrieval_seconds, 4),
                "backend_used": retrieval_details.get("backend_used"),
                "candidate_pool_size": retrieval_details.get("candidate_pool_size"),
                "reranking_applied": retrieval_details.get("reranking_applied"),
                "top_sources": [
                    {
                        "source": chunk.get("source"),
                        "document_id": chunk.get("document_id"),
                        "chunk_id": chunk.get("chunk_id"),
                        "score": chunk.get("score"),
                        "vector_score": chunk.get("vector_score"),
                        "lexical_score": chunk.get("lexical_score"),
                        "snippet": str(chunk.get("snippet") or chunk.get("text") or "")[:280],
                    }
                    for chunk in chunks
                    if isinstance(chunk, dict)
                ],
            }
        )

    aggregate = {
        "question_count": len(questions),
        "hit_at_1": round(sum(hit_at_1_values) / max(len(hit_at_1_values), 1), 4) if hit_at_1_values else 0.0,
        "hit_at_k": round(sum(hit_at_k_values) / max(len(hit_at_k_values), 1), 4) if hit_at_k_values else 0.0,
        "mrr": round(sum(reciprocal_ranks) / max(len(reciprocal_ranks), 1), 4) if reciprocal_ranks else 0.0,
        "average_retrieval_seconds": round(statistics.mean(retrieval_latencies), 4) if retrieval_latencies else 0.0,
        "median_retrieval_seconds": round(statistics.median(retrieval_latencies), 4) if retrieval_latencies else 0.0,
        "max_retrieval_seconds": round(max(retrieval_latencies), 4) if retrieval_latencies else 0.0,
    }
    return per_question_results, aggregate


def classify_runtime_path(
    *,
    provider_requested: str,
    provider_effective: str,
    model_effective: str,
    runtime_artifact: dict[str, object] | None,
) -> dict[str, object]:
    requested = str(provider_requested or "").strip().lower()
    effective = str(provider_effective or provider_requested or "").strip().lower()
    model = str(model_effective or "").strip()
    artifact = runtime_artifact if isinstance(runtime_artifact, dict) else {}
    backend_provider = str(artifact.get("backend_provider") or "").strip().lower() or None
    backend_model_ref = str(artifact.get("backend_model_ref") or "").strip() or None

    if effective == "ollama":
        runtime_path = "direct_runtime"
        runtime_path_label = "Direct runtime"
        backend_equivalence_type = "native_runtime"
        backend_provider_resolved = "ollama"
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = False
        path_comparison_note = "Direct provider path with no hub-wrapper layer."
    elif effective == "huggingface_server":
        runtime_path = "hub_wrapped_runtime"
        runtime_path_label = "Hub-wrapped runtime"
        backend_equivalence_type = "wrapped_backend"
        backend_provider_resolved = backend_provider
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = True
        if backend_provider == "ollama":
            path_comparison_note = (
                "Backend appears equivalent to direct Ollama, but requests flow through the local hub and may incur extra HTTP/serving overhead."
            )
        else:
            path_comparison_note = "Requests flow through the local hub layer before reaching the effective backend."
    elif effective in {"openai", "huggingface_inference"}:
        runtime_path = "cloud_managed_runtime"
        runtime_path_label = "Cloud managed runtime"
        backend_equivalence_type = "managed_service"
        backend_provider_resolved = backend_provider or effective
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = False
        path_comparison_note = "Managed remote serving path; not directly comparable to local direct-runtime overhead."
    elif effective == "huggingface_local":
        runtime_path = "local_native_runtime"
        runtime_path_label = "Local native runtime"
        backend_equivalence_type = "native_runtime"
        backend_provider_resolved = backend_provider or effective
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = False
        path_comparison_note = "Local native runtime path outside Ollama; backend semantics may differ from Ollama-native execution."
    else:
        runtime_path = "unknown_runtime_path"
        runtime_path_label = "Unknown runtime path"
        backend_equivalence_type = "unknown"
        backend_provider_resolved = backend_provider or effective or requested or None
        backend_model_ref_resolved = backend_model_ref or model or None
        path_overhead_expected = False
        path_comparison_note = "Runtime path could not be classified precisely from the available metadata."

    backend_equivalence_key = None
    if backend_provider_resolved and backend_model_ref_resolved:
        backend_equivalence_key = f"{backend_provider_resolved}::{backend_model_ref_resolved}"
    elif effective and model:
        backend_equivalence_key = f"{effective}::{model}"

    equivalent_direct_runtime_key = None
    if runtime_path == "hub_wrapped_runtime" and backend_provider_resolved == "ollama":
        equivalent_direct_runtime_key = f"ollama::{backend_model_ref_resolved or model}"
    elif runtime_path == "direct_runtime" and backend_provider_resolved == "ollama":
        equivalent_direct_runtime_key = f"ollama::{backend_model_ref_resolved or model}"

    return {
        "runtime_path": runtime_path,
        "runtime_path_label": runtime_path_label,
        "backend_equivalence_type": backend_equivalence_type,
        "backend_provider_resolved": backend_provider_resolved,
        "backend_model_ref_resolved": backend_model_ref_resolved,
        "backend_equivalence_key": backend_equivalence_key,
        "equivalent_direct_runtime_key": equivalent_direct_runtime_key,
        "path_overhead_expected": path_overhead_expected,
        "path_comparison_note": path_comparison_note,
    }


def execute_generation_case(
    case: dict[str, object],
    *,
    run_id: str,
    registry: dict[str, dict[str, object]],
    timeout_s: int | None = None,
) -> dict[str, object]:
    requested_provider = str(case.get("provider") or "")
    requested_model = str(case.get("requested_model") or case.get("model") or "")
    resolved_model = str(case.get("model") or requested_model)
    runtime_profile = resolve_provider_runtime_profile(
        registry,
        requested_provider,
        capability="chat",
        fallback_provider=None,
    )
    effective_provider = str(runtime_profile.get("effective_provider") or requested_provider)
    if requested_provider and effective_provider != requested_provider:
        runtime_profile = {
            **runtime_profile,
            "effective_provider": requested_provider,
            "provider_entry": {},
            "provider_instance": None,
            "fallback_reason": f"requested_provider_unavailable:{requested_provider}",
        }
    provider_entry = runtime_profile.get("provider_entry") if isinstance(runtime_profile.get("provider_entry"), dict) else {}
    runtime_artifact = _inspect_runtime_artifact(
        provider_entry,
        capability="chat",
        model=resolved_model,
        requested_context_window=int(case.get("context_window") or 0) or None,
    )
    started_at = time.time()
    try:
        with time_limit(timeout_s, f"generation case timeout after {timeout_s}s"):
            result = run_model_comparison_candidate(
                registry=registry,
                provider_name=requested_provider,
                model_name=resolved_model,
                prompt_profile=str(case.get("prompt_profile") or "neutro"),
                prompt_text=str(case.get("prompt_text") or ""),
                benchmark_use_case=str(case.get("benchmark_use_case") or "ad_hoc"),
                response_format=str(case.get("response_format") or "plain_text"),
                temperature=float(case.get("temperature") or 0.0),
                context_window=int(case.get("context_window") or 8192),
                retrieved_chunks=list(case.get("context_chunks") or []),
                rag_settings=get_rag_settings(),
                top_p=float(case.get("top_p")) if isinstance(case.get("top_p"), (int, float)) else None,
                max_tokens=int(case.get("max_output_tokens")) if isinstance(case.get("max_output_tokens"), (int, float)) else None,
                think=case.get("think") if isinstance(case.get("think"), bool) else None,
                fallback_provider=None,
            )
    except TimeoutExecutionError as error:
        result = {
            "success": False,
            "provider_effective": requested_provider,
            "model_effective": resolved_model,
            "runtime_bucket": infer_model_comparison_runtime_bucket(requested_provider, resolved_model),
            "quantization_family": infer_model_comparison_quantization_family(requested_provider, resolved_model),
            "latency_s": None,
            "output_chars": 0,
            "output_words": 0,
            "format_adherence": 0.0,
            "groundedness_score": 0.0,
            "schema_adherence": None,
            "use_case_fit_score": 0.0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "usage_source": None,
            "context_injected": False,
            "used_chunks": 0,
            "dropped_chunks": 0,
            "context_preview_chars": 0,
            "error": str(error),
            "response_text": "",
        }
    runtime_path_metadata = classify_runtime_path(
        provider_requested=requested_provider,
        provider_effective=str(result.get("provider_effective") or requested_provider),
        model_effective=str(result.get("model_effective") or resolved_model),
        runtime_artifact=runtime_artifact,
    )
    runtime_family_metadata = build_runtime_family_metadata(
        requested_runtime_family=str(case.get("requested_runtime_family") or "") or None,
        provider_effective=str(result.get("provider_effective") or requested_provider),
        model_effective=str(result.get("model_effective") or resolved_model),
        runtime_artifact=runtime_artifact,
    )
    generation_metrics = build_operational_metrics_bundle(
        total_wall_time_s=result.get("total_wall_time_s") if isinstance(result.get("total_wall_time_s"), (int, float)) else None,
        repetition=int(case.get("repetition") or 1),
        ttft_s=result.get("ttft_s") if isinstance(result.get("ttft_s"), (int, float)) else None,
        throughput_tokens_per_s=result.get("throughput_tokens_per_s") if isinstance(result.get("throughput_tokens_per_s"), (int, float)) else None,
    )
    event = {
        "event_type": "case_result",
        "run_id": run_id,
        "case_id": case.get("case_id"),
        "status": "success" if bool(result.get("success")) else "failed",
        "group": "generation",
        "started_at": started_at,
        "finished_at": time.time(),
        "provider_requested": requested_provider,
        "provider_effective": result.get("provider_effective"),
        "model_requested": requested_model,
        "model_effective": result.get("model_effective"),
        "requested_runtime_family": case.get("requested_runtime_family"),
        "model_resolution_status": case.get("model_resolution_status"),
        "model_resolution_source": case.get("model_resolution_source"),
        "requested_model_candidates": case.get("requested_model_candidates") or [],
        "provider_label": case.get("provider_label"),
        "group_id": case.get("group_id"),
        "group_label": case.get("group_label"),
        "use_case_id": case.get("use_case_id"),
        "use_case_label": case.get("use_case_label"),
        "benchmark_use_case": case.get("benchmark_use_case"),
        "prompt_profile": case.get("prompt_profile"),
        "response_format": case.get("response_format"),
        "structured_output_mode": case.get("structured_output_mode"),
        "input_file": case.get("input_file"),
        "input_chars": case.get("input_chars"),
        "temperature": case.get("temperature"),
        "top_p": case.get("top_p"),
        "max_output_tokens": case.get("max_output_tokens"),
        "think_requested": case.get("think"),
        "context_window": case.get("context_window"),
        "seed_requested": case.get("seed"),
        "seed_supported": bool(case.get("seed_supported")),
        "seed_applied": False,
        "repetition": case.get("repetition"),
        "runtime_bucket": result.get("runtime_bucket"),
        "quantization_family": result.get("quantization_family"),
        "latency_s": result.get("latency_s"),
        "output_chars": result.get("output_chars"),
        "output_words": result.get("output_words"),
        "format_adherence": result.get("format_adherence"),
        "groundedness_score": result.get("groundedness_score"),
        "schema_adherence": result.get("schema_adherence"),
        "use_case_fit_score": result.get("use_case_fit_score"),
        "prompt_tokens": result.get("prompt_tokens"),
        "completion_tokens": result.get("completion_tokens"),
        "total_tokens": result.get("total_tokens"),
        "usage_source": result.get("usage_source"),
        "total_wall_time_s": result.get("total_wall_time_s"),
        "total_wall_time_status": result.get("total_wall_time_status"),
        "ttft_s": result.get("ttft_s"),
        "ttft_status": result.get("ttft_status"),
        "ttft_measurement_method": result.get("ttft_measurement_method"),
        "throughput_tokens_per_s": result.get("throughput_tokens_per_s"),
        "throughput_status": result.get("throughput_status"),
        "cold_start_wall_time_s": result.get("cold_start_wall_time_s"),
        "cold_start_status": result.get("cold_start_status"),
        "warm_start_wall_time_s": result.get("warm_start_wall_time_s"),
        "warm_start_status": result.get("warm_start_status"),
        "memory_peak_estimate_mb": result.get("memory_peak_estimate_mb"),
        "memory_status": result.get("memory_status"),
        "memory_measurement_method": result.get("memory_measurement_method"),
        "context_injected": result.get("context_injected"),
        "used_chunks": result.get("used_chunks"),
        "dropped_chunks": result.get("dropped_chunks"),
        "context_preview_chars": result.get("context_preview_chars"),
        "prompt_serialization_mode": result.get("prompt_serialization_mode"),
        "chat_template_used": result.get("chat_template_used"),
        "chat_template_source": result.get("chat_template_source"),
        "runtime_artifact": runtime_artifact,
        "error": result.get("error"),
        "response_text": result.get("response_text"),
        **runtime_path_metadata,
        **runtime_family_metadata,
        **generation_metrics,
    }
    return event


def execute_embedding_case(
    case: dict[str, object],
    *,
    run_id: str,
    registry: dict[str, dict[str, object]],
    run_output_dir: Path,
    indexing_timeout_s: int | None = None,
    query_timeout_s: int | None = None,
) -> dict[str, object]:
    requested_provider = str(case.get("provider") or "")
    requested_model = str(case.get("requested_model") or case.get("model") or "")
    resolved_model = str(case.get("model") or requested_model)
    runtime_profile = resolve_provider_runtime_profile(
        registry,
        requested_provider,
        capability="embeddings",
        fallback_provider=None,
    )
    effective_provider = str(runtime_profile.get("effective_provider") or requested_provider)
    if requested_provider and effective_provider != requested_provider:
        runtime_profile = {
            **runtime_profile,
            "effective_provider": requested_provider,
            "provider_entry": {},
            "provider_instance": None,
            "fallback_reason": f"requested_provider_unavailable:{requested_provider}",
        }
    provider_entry = runtime_profile.get("provider_entry") if isinstance(runtime_profile.get("provider_entry"), dict) else {}
    provider_instance = provider_entry.get("instance")
    runtime_artifact = _inspect_runtime_artifact(
        provider_entry,
        capability="embeddings",
        model=resolved_model,
        requested_context_window=int(case.get("embedding_context_window") or 0) or None,
    )
    started_at = time.time()
    event_started_perf = time.perf_counter()
    event: dict[str, object] = {
        "event_type": "case_result",
        "run_id": run_id,
        "case_id": case.get("case_id"),
        "status": "failed",
        "group": "embeddings",
        "started_at": started_at,
        "provider_requested": requested_provider,
        "provider_effective": runtime_profile.get("effective_provider") or requested_provider,
        "model_requested": requested_model,
        "model_effective": resolved_model,
        "requested_runtime_family": case.get("requested_runtime_family"),
        "model_resolution_status": case.get("model_resolution_status"),
        "model_resolution_source": case.get("model_resolution_source"),
        "requested_model_candidates": case.get("requested_model_candidates") or [],
        "provider_label": case.get("provider_label"),
        "candidate_id": case.get("candidate_id"),
        "candidate_role": case.get("candidate_role"),
        "dataset_id": case.get("dataset_id"),
        "subset_id": case.get("subset_id"),
        "subset_label": case.get("subset_label"),
        "subset_kind": case.get("subset_kind"),
        "question_set_id": case.get("question_set_id"),
        "question_set_path": case.get("question_set_path"),
        "document_count": len(case.get("document_paths") or case.get("pdf_paths") or []),
        "question_count": len(case.get("questions") or []),
        "embedding_context_window": case.get("embedding_context_window"),
        "embedding_truncate": case.get("embedding_truncate"),
        "chunk_size": case.get("chunk_size"),
        "chunk_overlap": case.get("chunk_overlap"),
        "top_k": case.get("top_k"),
        "rerank_pool_size": case.get("rerank_pool_size"),
        "rerank_lexical_weight": case.get("rerank_lexical_weight"),
        "pdf_extraction_mode": case.get("pdf_extraction_mode"),
        "pdf_docling_enabled": case.get("pdf_docling_enabled"),
        "pdf_ocr_fallback_enabled": case.get("pdf_ocr_fallback_enabled"),
        "pdf_scan_image_ocr_enabled": case.get("pdf_scan_image_ocr_enabled"),
        "pdf_evidence_pipeline_enabled": case.get("pdf_evidence_pipeline_enabled"),
        "repetition": case.get("repetition"),
        "runtime_bucket": infer_model_comparison_runtime_bucket(requested_provider, resolved_model),
        "quantization_family": infer_model_comparison_quantization_family(requested_provider, resolved_model),
        "runtime_artifact": runtime_artifact,
        "error": None,
    }
    runtime_path_metadata = classify_runtime_path(
        provider_requested=requested_provider,
        provider_effective=str(runtime_profile.get("effective_provider") or requested_provider),
        model_effective=resolved_model,
        runtime_artifact=runtime_artifact,
    )
    runtime_family_metadata = build_runtime_family_metadata(
        requested_runtime_family=str(case.get("requested_runtime_family") or "") or None,
        provider_effective=str(runtime_profile.get("effective_provider") or requested_provider),
        model_effective=resolved_model,
        runtime_artifact=runtime_artifact,
    )
    event.update(runtime_path_metadata)
    event.update(runtime_family_metadata)
    if provider_instance is None:
        event["finished_at"] = time.time()
        event["error"] = runtime_profile.get("fallback_reason") or "provider_unavailable"
        event.update(
            build_operational_metrics_bundle(
                total_wall_time_s=time.perf_counter() - event_started_perf,
                repetition=int(case.get("repetition") or 1),
            )
        )
        return event

    case_dir = run_output_dir / "cases" / str(case.get("case_id"))
    case_dir.mkdir(parents=True, exist_ok=True)
    settings = _build_isolated_rag_settings(case, case_dir)
    try:
        indexing_started = time.perf_counter()
        with time_limit(
            indexing_timeout_s,
            f"embedding indexing timeout after {indexing_timeout_s}s",
        ):
            loaded_documents = [
                load_document(_LocalUploadedFile(Path(path)), settings)
                for path in case.get("document_paths") or case.get("pdf_paths") or []
            ]
            rag_index, sync_status = upsert_documents_in_rag_index(
                documents=loaded_documents,
                settings=settings,
                embedding_provider=provider_instance,
                rag_index=None,
            )
        indexing_seconds = time.perf_counter() - indexing_started
        per_question_results, aggregate_metrics = _run_embedding_questions(
            questions=list(case.get("questions") or []),
            rag_index=rag_index,
            settings=settings,
            embedding_provider=provider_instance,
            query_timeout_s=query_timeout_s,
        )
        event.update(
            {
                "status": "success",
                "indexing_seconds": round(indexing_seconds, 4),
                "sync_status": sync_status,
                "aggregate_metrics": aggregate_metrics,
                "per_question_results": per_question_results,
                "hit_at_1": aggregate_metrics.get("hit_at_1"),
                "hit_at_k": aggregate_metrics.get("hit_at_k"),
                "mrr": aggregate_metrics.get("mrr"),
                "average_retrieval_seconds": aggregate_metrics.get("average_retrieval_seconds"),
                "median_retrieval_seconds": aggregate_metrics.get("median_retrieval_seconds"),
                "max_retrieval_seconds": aggregate_metrics.get("max_retrieval_seconds"),
            }
        )
    except Exception as error:
        event["error"] = str(error)
    event.update(
        build_operational_metrics_bundle(
            total_wall_time_s=time.perf_counter() - event_started_perf,
            repetition=int(case.get("repetition") or 1),
        )
    )
    event["finished_at"] = time.time()
    return event


def normalize_case_results(events: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    generation_rows: list[dict[str, object]] = []
    embedding_rows: list[dict[str, object]] = []
    embedding_question_rows: list[dict[str, object]] = []
    for event in events:
        if str(event.get("group") or "") == "generation":
            generation_rows.append(
                {
                    "run_id": event.get("run_id"),
                    "case_id": event.get("case_id"),
                    "status": event.get("status"),
                    "provider_requested": event.get("provider_requested"),
                    "provider_effective": event.get("provider_effective"),
                    "model_requested": event.get("model_requested"),
                    "model_effective": event.get("model_effective"),
                    "requested_runtime_family": event.get("requested_runtime_family"),
                    "resolved_runtime_family": event.get("resolved_runtime_family"),
                    "runtime_family_resolution_status": event.get("runtime_family_resolution_status"),
                    "runtime_family_resolution_note": event.get("runtime_family_resolution_note"),
                    "model_resolution_status": event.get("model_resolution_status"),
                    "model_resolution_source": event.get("model_resolution_source"),
                    "group_id": event.get("group_id"),
                    "use_case_id": event.get("use_case_id"),
                    "benchmark_use_case": event.get("benchmark_use_case"),
                    "prompt_profile": event.get("prompt_profile"),
                    "response_format": event.get("response_format"),
                    "structured_output_mode": event.get("structured_output_mode"),
                    "temperature": event.get("temperature"),
                    "top_p": event.get("top_p"),
                    "max_output_tokens": event.get("max_output_tokens"),
                    "think_requested": event.get("think_requested"),
                    "context_window": event.get("context_window"),
                    "repetition": event.get("repetition"),
                    "runtime_bucket": event.get("runtime_bucket"),
                    "quantization_family": event.get("quantization_family"),
                    "latency_s": event.get("latency_s"),
                    "output_chars": event.get("output_chars"),
                    "output_words": event.get("output_words"),
                    "format_adherence": event.get("format_adherence"),
                    "groundedness_score": event.get("groundedness_score"),
                    "schema_adherence": event.get("schema_adherence"),
                    "use_case_fit_score": event.get("use_case_fit_score"),
                    "prompt_tokens": event.get("prompt_tokens"),
                    "completion_tokens": event.get("completion_tokens"),
                    "total_tokens": event.get("total_tokens"),
                    "usage_source": event.get("usage_source"),
                    "total_wall_time_s": event.get("total_wall_time_s"),
                    "total_wall_time_status": event.get("total_wall_time_status"),
                    "ttft_s": event.get("ttft_s"),
                    "ttft_status": event.get("ttft_status"),
                    "ttft_measurement_method": event.get("ttft_measurement_method"),
                    "throughput_tokens_per_s": event.get("throughput_tokens_per_s"),
                    "throughput_status": event.get("throughput_status"),
                    "cold_start_wall_time_s": event.get("cold_start_wall_time_s"),
                    "cold_start_status": event.get("cold_start_status"),
                    "warm_start_wall_time_s": event.get("warm_start_wall_time_s"),
                    "warm_start_status": event.get("warm_start_status"),
                    "memory_peak_estimate_mb": event.get("memory_peak_estimate_mb"),
                    "memory_status": event.get("memory_status"),
                    "memory_measurement_method": event.get("memory_measurement_method"),
                    "runtime_path": event.get("runtime_path"),
                    "runtime_path_label": event.get("runtime_path_label"),
                    "backend_equivalence_type": event.get("backend_equivalence_type"),
                    "backend_provider_resolved": event.get("backend_provider_resolved"),
                    "backend_model_ref_resolved": event.get("backend_model_ref_resolved"),
                    "backend_equivalence_key": event.get("backend_equivalence_key"),
                    "equivalent_direct_runtime_key": event.get("equivalent_direct_runtime_key"),
                    "path_overhead_expected": event.get("path_overhead_expected"),
                    "path_comparison_note": event.get("path_comparison_note"),
                    "seed_requested": event.get("seed_requested"),
                    "seed_supported": event.get("seed_supported"),
                    "seed_applied": event.get("seed_applied"),
                    "prompt_serialization_mode": event.get("prompt_serialization_mode"),
                    "chat_template_used": event.get("chat_template_used"),
                    "chat_template_source": event.get("chat_template_source"),
                    "error": event.get("error"),
                }
            )
        if str(event.get("group") or "") == "embeddings":
            aggregate_metrics = event.get("aggregate_metrics") if isinstance(event.get("aggregate_metrics"), dict) else {}
            embedding_rows.append(
                {
                    "run_id": event.get("run_id"),
                    "case_id": event.get("case_id"),
                    "status": event.get("status"),
                    "provider_requested": event.get("provider_requested"),
                    "provider_effective": event.get("provider_effective"),
                    "model_requested": event.get("model_requested"),
                    "model_effective": event.get("model_effective"),
                    "requested_runtime_family": event.get("requested_runtime_family"),
                    "resolved_runtime_family": event.get("resolved_runtime_family"),
                    "runtime_family_resolution_status": event.get("runtime_family_resolution_status"),
                    "runtime_family_resolution_note": event.get("runtime_family_resolution_note"),
                    "model_resolution_status": event.get("model_resolution_status"),
                    "model_resolution_source": event.get("model_resolution_source"),
                    "candidate_id": event.get("candidate_id"),
                    "candidate_role": event.get("candidate_role"),
                    "dataset_id": event.get("dataset_id"),
                    "subset_id": event.get("subset_id"),
                    "subset_label": event.get("subset_label"),
                    "subset_kind": event.get("subset_kind"),
                    "question_set_id": event.get("question_set_id"),
                    "document_count": event.get("document_count"),
                    "question_count": event.get("question_count"),
                    "embedding_context_window": event.get("embedding_context_window"),
                    "embedding_truncate": event.get("embedding_truncate"),
                    "chunk_size": event.get("chunk_size"),
                    "chunk_overlap": event.get("chunk_overlap"),
                    "top_k": event.get("top_k"),
                    "pdf_extraction_mode": event.get("pdf_extraction_mode"),
                    "pdf_docling_enabled": event.get("pdf_docling_enabled"),
                    "pdf_ocr_fallback_enabled": event.get("pdf_ocr_fallback_enabled"),
                    "pdf_scan_image_ocr_enabled": event.get("pdf_scan_image_ocr_enabled"),
                    "pdf_evidence_pipeline_enabled": event.get("pdf_evidence_pipeline_enabled"),
                    "rerank_pool_size": event.get("rerank_pool_size"),
                    "rerank_lexical_weight": event.get("rerank_lexical_weight"),
                    "repetition": event.get("repetition"),
                    "runtime_bucket": event.get("runtime_bucket"),
                    "quantization_family": event.get("quantization_family"),
                    "runtime_path": event.get("runtime_path"),
                    "runtime_path_label": event.get("runtime_path_label"),
                    "backend_equivalence_type": event.get("backend_equivalence_type"),
                    "backend_provider_resolved": event.get("backend_provider_resolved"),
                    "backend_model_ref_resolved": event.get("backend_model_ref_resolved"),
                    "backend_equivalence_key": event.get("backend_equivalence_key"),
                    "equivalent_direct_runtime_key": event.get("equivalent_direct_runtime_key"),
                    "path_overhead_expected": event.get("path_overhead_expected"),
                    "path_comparison_note": event.get("path_comparison_note"),
                    "total_wall_time_s": event.get("total_wall_time_s"),
                    "total_wall_time_status": event.get("total_wall_time_status"),
                    "cold_start_wall_time_s": event.get("cold_start_wall_time_s"),
                    "cold_start_status": event.get("cold_start_status"),
                    "warm_start_wall_time_s": event.get("warm_start_wall_time_s"),
                    "warm_start_status": event.get("warm_start_status"),
                    "memory_peak_estimate_mb": event.get("memory_peak_estimate_mb"),
                    "memory_status": event.get("memory_status"),
                    "memory_measurement_method": event.get("memory_measurement_method"),
                    "indexing_seconds": event.get("indexing_seconds"),
                    "hit_at_1": aggregate_metrics.get("hit_at_1", event.get("hit_at_1")),
                    "hit_at_k": aggregate_metrics.get("hit_at_k", event.get("hit_at_k")),
                    "mrr": aggregate_metrics.get("mrr", event.get("mrr")),
                    "average_retrieval_seconds": aggregate_metrics.get("average_retrieval_seconds", event.get("average_retrieval_seconds")),
                    "median_retrieval_seconds": aggregate_metrics.get("median_retrieval_seconds", event.get("median_retrieval_seconds")),
                    "max_retrieval_seconds": aggregate_metrics.get("max_retrieval_seconds", event.get("max_retrieval_seconds")),
                    "error": event.get("error"),
                }
            )
            for question_result in event.get("per_question_results") or []:
                if not isinstance(question_result, dict):
                    continue
                embedding_question_rows.append(
                    {
                        "run_id": event.get("run_id"),
                        "case_id": event.get("case_id"),
                        "provider_requested": event.get("provider_requested"),
                        "model_requested": event.get("model_requested"),
                        "candidate_id": event.get("candidate_id"),
                        "subset_id": event.get("subset_id"),
                        "subset_kind": event.get("subset_kind"),
                        "runtime_path": event.get("runtime_path"),
                        "backend_equivalence_key": event.get("backend_equivalence_key"),
                        "question": question_result.get("question"),
                        "hit_at_1": question_result.get("hit_at_1"),
                        "hit_at_k": question_result.get("hit_at_k"),
                        "reciprocal_rank": question_result.get("reciprocal_rank"),
                        "first_relevant_rank": question_result.get("first_relevant_rank"),
                        "retrieval_seconds": question_result.get("retrieval_seconds"),
                        "backend_used": question_result.get("backend_used"),
                    }
                )
    return {
        "generation": generation_rows,
        "embeddings": embedding_rows,
        "embedding_questions": embedding_question_rows,
    }


def _average(values: list[float]) -> float:
    return round(sum(values) / max(len(values), 1), 4) if values else 0.0


def _format_backend_label(item: dict[str, object]) -> str | None:
    backend_provider = str(item.get("backend_provider_resolved") or "").strip()
    backend_model = str(item.get("backend_model_ref_resolved") or "").strip()
    if backend_provider and backend_model:
        return f"{backend_provider}::{backend_model}"
    if backend_provider:
        return backend_provider
    if backend_model:
        return backend_model
    return None


def _summarize_model_resolution(events: list[dict[str, object]]) -> dict[str, object]:
    counts: dict[str, int] = defaultdict(int)
    substitutions: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    for event in events:
        status = str(event.get("model_resolution_status") or "exact").strip() or "exact"
        counts[status] += 1
        requested_model = str(event.get("model_requested") or "").strip()
        effective_model = str(event.get("model_effective") or "").strip()
        if status == "exact" and requested_model == effective_model:
            continue
        key = (
            str(event.get("group") or ""),
            str(event.get("provider_requested") or ""),
            requested_model,
            effective_model,
            status,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        substitutions.append(
            {
                "group": event.get("group"),
                "provider_requested": event.get("provider_requested"),
                "model_requested": requested_model,
                "model_effective": effective_model,
                "mapping_status": status,
                "resolution_source": event.get("model_resolution_source"),
                "requested_model_candidates": event.get("requested_model_candidates") or [],
            }
        )
    return {
        "counts": dict(counts),
        "substitutions": substitutions,
    }


def _summarize_metric_status_counts(events: list[dict[str, object]], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for event in events:
        status = str(event.get(field_name) or "not_supported").strip() or "not_supported"
        counts[status] += 1
    return dict(counts)


def _summarize_runtime_paths(events: list[dict[str, object]]) -> list[dict[str, object]]:
    by_path: dict[str, list[dict[str, object]]] = defaultdict(list)
    for event in events:
        runtime_path = str(event.get("runtime_path") or "unknown_runtime_path")
        by_path[runtime_path].append(event)
    summary: list[dict[str, object]] = []
    for runtime_path, runtime_events in by_path.items():
        backend_labels = sorted({label for label in (_format_backend_label(item) for item in runtime_events) if label})
        summary.append(
            {
                "runtime_path": runtime_path,
                "runtime_path_label": runtime_events[0].get("runtime_path_label") or runtime_path,
                "case_count": len(runtime_events),
                "successful_cases": sum(1 for item in runtime_events if item.get("status") == "success"),
                "failed_cases": sum(1 for item in runtime_events if item.get("status") != "success"),
                "candidate_count": len({f"{item.get('provider_requested')}::{item.get('model_requested')}" for item in runtime_events}),
                "path_overhead_expected": any(bool(item.get("path_overhead_expected")) for item in runtime_events),
                "backend_examples": backend_labels[:5],
            }
        )
    summary.sort(key=lambda item: str(item.get("runtime_path") or ""))
    return summary


def aggregate_case_results(events: list[dict[str, object]]) -> dict[str, object]:
    generation_events = [event for event in events if event.get("group") == "generation"]
    embedding_events = [event for event in events if event.get("group") == "embeddings"]

    def _aggregate_generation() -> dict[str, object]:
        by_candidate: dict[str, list[dict[str, object]]] = defaultdict(list)
        for event in generation_events:
            key = f"{event.get('provider_requested')}::{event.get('model_requested')}"
            by_candidate[key].append(event)
        ranking: list[dict[str, object]] = []
        for key, candidate_events in by_candidate.items():
            successful = [item for item in candidate_events if item.get("status") == "success"]
            ranking.append(
                {
                    "candidate": key,
                    "provider": candidate_events[0].get("provider_requested"),
                    "model": candidate_events[0].get("model_requested"),
                    "runtime_path": candidate_events[0].get("runtime_path"),
                    "runtime_path_label": candidate_events[0].get("runtime_path_label"),
                    "backend_equivalence_type": candidate_events[0].get("backend_equivalence_type"),
                    "backend_provider_resolved": candidate_events[0].get("backend_provider_resolved"),
                    "backend_model_ref_resolved": candidate_events[0].get("backend_model_ref_resolved"),
                    "backend_equivalence_key": candidate_events[0].get("backend_equivalence_key"),
                    "equivalent_direct_runtime_key": candidate_events[0].get("equivalent_direct_runtime_key"),
                    "path_overhead_expected": candidate_events[0].get("path_overhead_expected"),
                    "case_count": len(candidate_events),
                    "success_rate": round(len(successful) / max(len(candidate_events), 1), 4),
                    "avg_latency_s": _average([
                        float(item.get("latency_s"))
                        for item in successful
                        if isinstance(item.get("latency_s"), (int, float))
                    ]),
                    "avg_format_adherence": _average([
                        float(item.get("format_adherence"))
                        for item in candidate_events
                        if isinstance(item.get("format_adherence"), (int, float))
                    ]),
                    "avg_groundedness_score": _average([
                        float(item.get("groundedness_score"))
                        for item in candidate_events
                        if isinstance(item.get("groundedness_score"), (int, float))
                    ]),
                    "avg_schema_adherence": _average([
                        float(item.get("schema_adherence"))
                        for item in candidate_events
                        if isinstance(item.get("schema_adherence"), (int, float))
                    ]),
                    "avg_use_case_fit_score": _average([
                        float(item.get("use_case_fit_score"))
                        for item in candidate_events
                        if isinstance(item.get("use_case_fit_score"), (int, float))
                    ]),
                    "avg_total_wall_time_s": _average([
                        float(item.get("total_wall_time_s"))
                        for item in candidate_events
                        if isinstance(item.get("total_wall_time_s"), (int, float))
                    ]),
                    "avg_ttft_s": _average([
                        float(item.get("ttft_s"))
                        for item in candidate_events
                        if isinstance(item.get("ttft_s"), (int, float))
                    ]),
                    "avg_throughput_tokens_per_s": _average([
                        float(item.get("throughput_tokens_per_s"))
                        for item in candidate_events
                        if isinstance(item.get("throughput_tokens_per_s"), (int, float))
                    ]),
                    "operational_metric_support": {
                        "total_wall_time_status": _summarize_metric_status_counts(candidate_events, "total_wall_time_status"),
                        "ttft_status": _summarize_metric_status_counts(candidate_events, "ttft_status"),
                        "throughput_status": _summarize_metric_status_counts(candidate_events, "throughput_status"),
                        "cold_start_status": _summarize_metric_status_counts(candidate_events, "cold_start_status"),
                        "warm_start_status": _summarize_metric_status_counts(candidate_events, "warm_start_status"),
                        "memory_status": _summarize_metric_status_counts(candidate_events, "memory_status"),
                    },
                    "avg_total_tokens": _average([
                        float(item.get("total_tokens"))
                        for item in candidate_events
                        if isinstance(item.get("total_tokens"), (int, float))
                    ]),
                }
            )
        ranking.sort(
            key=lambda item: (
                -float(item.get("success_rate") or 0.0),
                -float(item.get("avg_use_case_fit_score") or 0.0),
                -float(item.get("avg_format_adherence") or 0.0),
                float(item.get("avg_latency_s") or 10**9),
            )
        )
        return {
            "total_cases": len(generation_events),
            "successful_cases": sum(1 for event in generation_events if event.get("status") == "success"),
            "failed_cases": sum(1 for event in generation_events if event.get("status") != "success"),
            "runtime_path_breakdown": _summarize_runtime_paths(generation_events),
            "candidate_ranking": ranking,
            "top_candidate": ranking[0] if ranking else None,
        }

    def _aggregate_embeddings() -> dict[str, object]:
        by_candidate: dict[str, list[dict[str, object]]] = defaultdict(list)
        by_subset: dict[str, list[dict[str, object]]] = defaultdict(list)
        for event in embedding_events:
            subset_id = str(event.get("subset_id") or "default")
            key = f"{event.get('provider_requested')}::{event.get('model_requested')}::{subset_id}"
            by_candidate[key].append(event)
            by_subset[subset_id].append(event)
        ranking: list[dict[str, object]] = []
        for key, candidate_events in by_candidate.items():
            successful = [item for item in candidate_events if item.get("status") == "success"]
            ranking.append(
                {
                    "candidate": key,
                    "provider": candidate_events[0].get("provider_requested"),
                    "model": candidate_events[0].get("model_requested"),
                    "candidate_role": candidate_events[0].get("candidate_role"),
                    "model_effective": candidate_events[0].get("model_effective"),
                    "model_resolution_status": candidate_events[0].get("model_resolution_status"),
                    "subset_id": candidate_events[0].get("subset_id"),
                    "subset_label": candidate_events[0].get("subset_label"),
                    "subset_kind": candidate_events[0].get("subset_kind"),
                    "requested_runtime_family": candidate_events[0].get("requested_runtime_family"),
                    "resolved_runtime_family": candidate_events[0].get("resolved_runtime_family"),
                    "runtime_path": candidate_events[0].get("runtime_path"),
                    "runtime_path_label": candidate_events[0].get("runtime_path_label"),
                    "backend_equivalence_type": candidate_events[0].get("backend_equivalence_type"),
                    "backend_provider_resolved": candidate_events[0].get("backend_provider_resolved"),
                    "backend_model_ref_resolved": candidate_events[0].get("backend_model_ref_resolved"),
                    "backend_equivalence_key": candidate_events[0].get("backend_equivalence_key"),
                    "equivalent_direct_runtime_key": candidate_events[0].get("equivalent_direct_runtime_key"),
                    "path_overhead_expected": candidate_events[0].get("path_overhead_expected"),
                    "case_count": len(candidate_events),
                    "success_rate": round(len(successful) / max(len(candidate_events), 1), 4),
                    "avg_hit_at_1": _average([
                        float(item.get("hit_at_1"))
                        for item in successful
                        if isinstance(item.get("hit_at_1"), (int, float))
                    ]),
                    "avg_hit_at_k": _average([
                        float(item.get("hit_at_k"))
                        for item in successful
                        if isinstance(item.get("hit_at_k"), (int, float))
                    ]),
                    "avg_mrr": _average([
                        float(item.get("mrr"))
                        for item in successful
                        if isinstance(item.get("mrr"), (int, float))
                    ]),
                    "avg_indexing_seconds": _average([
                        float(item.get("indexing_seconds"))
                        for item in successful
                        if isinstance(item.get("indexing_seconds"), (int, float))
                    ]),
                    "avg_retrieval_seconds": _average([
                        float(item.get("average_retrieval_seconds"))
                        for item in successful
                        if isinstance(item.get("average_retrieval_seconds"), (int, float))
                    ]),
                    "avg_total_wall_time_s": _average([
                        float(item.get("total_wall_time_s"))
                        for item in successful
                        if isinstance(item.get("total_wall_time_s"), (int, float))
                    ]),
                }
            )
        ranking.sort(
            key=lambda item: (
                -float(item.get("success_rate") or 0.0),
                -float(item.get("avg_mrr") or 0.0),
                -float(item.get("avg_hit_at_1") or 0.0),
                float(item.get("avg_retrieval_seconds") or 10**9),
            )
        )
        subset_rankings: list[dict[str, object]] = []
        for subset_id, subset_events in by_subset.items():
            subset_candidates = [item for item in ranking if str(item.get("subset_id") or "default") == subset_id]
            subset_rankings.append(
                {
                    "subset_id": subset_id,
                    "subset_label": next((item.get("subset_label") for item in subset_candidates if item.get("subset_label")), subset_id),
                    "subset_kind": next((item.get("subset_kind") for item in subset_candidates if item.get("subset_kind")), None),
                    "case_count": len(subset_events),
                    "candidate_ranking": subset_candidates,
                    "top_candidate": subset_candidates[0] if subset_candidates else None,
                }
            )
        subset_rankings.sort(key=lambda item: str(item.get("subset_id") or ""))
        preferred_top = next(
            (
                item.get("top_candidate")
                for item in subset_rankings
                if str(item.get("subset_kind") or "").strip().lower() == "general" and isinstance(item.get("top_candidate"), dict)
            ),
            ranking[0] if ranking else None,
        )
        subset_notes: list[dict[str, object]] = []
        general_top_candidate = next(
            (
                item.get("top_candidate")
                for item in subset_rankings
                if str(item.get("subset_kind") or "").strip().lower() == "general"
                and isinstance(item.get("top_candidate"), dict)
            ),
            None,
        )
        for item in subset_rankings:
            if str(item.get("subset_kind") or "").strip().lower() != "code":
                continue
            top_candidate = item.get("top_candidate") if isinstance(item.get("top_candidate"), dict) else None
            if not isinstance(top_candidate, dict):
                continue

            same_as_general_winner = (
                isinstance(general_top_candidate, dict)
                and str(top_candidate.get("provider") or "").strip() == str(general_top_candidate.get("provider") or "").strip()
                and str(top_candidate.get("model") or "").strip() == str(general_top_candidate.get("model") or "").strip()
            )
            candidate_role = str(top_candidate.get("candidate_role") or "").strip().lower()
            if not same_as_general_winner and "code" in candidate_role:
                continue

            reason = "same_as_general_winner" if same_as_general_winner else "no_dedicated_code_winner"
            model_label = str(top_candidate.get("model_effective") or top_candidate.get("model") or "").strip() or "unknown-model"
            provider_label = str(top_candidate.get("provider") or "unknown-provider").strip()
            message = (
                f"The code subset currently reuses `{provider_label}::{model_label}` as the best available local code fallback "
                f"because no stronger dedicated code embedding won cleanly in this environment."
            )
            subset_notes.append(
                {
                    "subset_id": item.get("subset_id"),
                    "subset_label": item.get("subset_label"),
                    "subset_kind": item.get("subset_kind"),
                    "reason": reason,
                    "provider": top_candidate.get("provider"),
                    "model": top_candidate.get("model"),
                    "model_effective": top_candidate.get("model_effective"),
                    "candidate_role": top_candidate.get("candidate_role"),
                    "message": message,
                }
            )
        return {
            "total_cases": len(embedding_events),
            "successful_cases": sum(1 for event in embedding_events if event.get("status") == "success"),
            "failed_cases": sum(1 for event in embedding_events if event.get("status") != "success"),
            "runtime_path_breakdown": _summarize_runtime_paths(embedding_events),
            "candidate_ranking": ranking,
            "subset_rankings": subset_rankings,
            "subset_notes": subset_notes,
            "top_candidate": preferred_top,
        }

    aggregated = {
        "total_cases": len(events),
        "successful_cases": sum(1 for event in events if event.get("status") == "success"),
        "failed_cases": sum(1 for event in events if event.get("status") != "success"),
        "runtime_path_breakdown": _summarize_runtime_paths(events),
        "model_resolution_summary": _summarize_model_resolution(events),
        "runtime_family_resolution_summary": summarize_runtime_family_artifacts(events),
        "generation": _aggregate_generation(),
        "embeddings": _aggregate_embeddings(),
    }
    return aggregated


def _write_csv_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_benchmark_outputs(
    *,
    run_dir: Path,
    manifest: dict[str, object],
    environment_snapshot: dict[str, object],
    preflight: dict[str, object],
    events: list[dict[str, object]],
) -> dict[str, object]:
    latest_events = select_latest_case_result_events(events)
    normalized = normalize_case_results(latest_events)
    normalized_round2 = normalize_round2_case_results(latest_events)
    aggregated = aggregate_case_results(latest_events)
    reranker_events = [event for event in latest_events if event.get("group") == "rerankers"]
    ocr_vlm_events = [event for event in latest_events if event.get("group") == "ocr_vlm"]
    aggregated["rerankers"] = aggregate_reranker_events(reranker_events)
    aggregated["ocr_vlm"] = aggregate_ocr_vlm_events(ocr_vlm_events)
    (run_dir / "aggregated").mkdir(parents=True, exist_ok=True)
    (run_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)

    (run_dir / "manifest.resolved.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "environment_snapshot.json").write_text(json.dumps(environment_snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "preflight.json").write_text(json.dumps(preflight, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "aggregated" / "latest_case_results.json").write_text(
        json.dumps(latest_events, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "aggregated" / "summary.json").write_text(json.dumps(aggregated, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "aggregated" / "generation_summary.json").write_text(
        json.dumps(aggregated.get("generation"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "aggregated" / "embedding_summary.json").write_text(
        json.dumps(aggregated.get("embeddings"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "aggregated" / "reranker_summary.json").write_text(
        json.dumps(aggregated.get("rerankers"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "aggregated" / "ocr_vlm_summary.json").write_text(
        json.dumps(aggregated.get("ocr_vlm"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _write_csv_rows(run_dir / "normalized" / "generation_cases.csv", normalized.get("generation") or [])
    _write_csv_rows(run_dir / "normalized" / "embedding_cases.csv", normalized.get("embeddings") or [])
    _write_csv_rows(run_dir / "normalized" / "embedding_questions.csv", normalized.get("embedding_questions") or [])
    _write_csv_rows(run_dir / "normalized" / "reranker_cases.csv", normalized_round2.get("rerankers") or [])
    _write_csv_rows(run_dir / "normalized" / "reranker_questions.csv", normalized_round2.get("reranker_questions") or [])
    _write_csv_rows(run_dir / "normalized" / "ocr_vlm_cases.csv", normalized_round2.get("ocr_vlm") or [])

    report_lines = [
        "# Phase 8.5 Benchmark Report",
        "",
        f"- Run ID: `{preflight.get('run_id')}`",
        f"- Total case attempts recorded: **{len(events)}**",
        f"- Latest unique cases considered: **{aggregated.get('total_cases', 0)}**",
        f"- Total cases: **{aggregated.get('total_cases', 0)}**",
        f"- Successful cases: **{aggregated.get('successful_cases', 0)}**",
        f"- Failed cases: **{aggregated.get('failed_cases', 0)}**",
        "",
        "## Generation ranking",
        "",
        "| Rank | Provider | Model | Runtime path | Backend | Success rate | Avg use-case fit | Avg latency (s) |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for index, item in enumerate((aggregated.get("generation") or {}).get("candidate_ranking", []), start=1):
        backend_label = _format_backend_label(item) or "-"
        report_lines.append(
            f"| {index} | `{item.get('provider')}` | `{item.get('model')}` | `{item.get('runtime_path') or '-'}` | `{backend_label}` | {float(item.get('success_rate') or 0.0):.4f} | {float(item.get('avg_use_case_fit_score') or 0.0):.4f} | {float(item.get('avg_latency_s') or 0.0):.4f} |"
        )
    report_lines.extend(
        [
            "",
            "## Generation operational metrics",
            "",
            "| Provider | Model | Avg total wall time (s) | Avg TTFT (s) | Avg throughput (tok/s) | TTFT status counts | Throughput status counts |",
            "| --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for item in (aggregated.get("generation") or {}).get("candidate_ranking", []):
        support = item.get("operational_metric_support") if isinstance(item.get("operational_metric_support"), dict) else {}
        ttft_counts = json.dumps(support.get("ttft_status") or {}, ensure_ascii=False, sort_keys=True)
        throughput_counts = json.dumps(support.get("throughput_status") or {}, ensure_ascii=False, sort_keys=True)
        report_lines.append(
            f"| `{item.get('provider')}` | `{item.get('model')}` | {float(item.get('avg_total_wall_time_s') or 0.0):.4f} | {float(item.get('avg_ttft_s') or 0.0):.4f} | {float(item.get('avg_throughput_tokens_per_s') or 0.0):.4f} | `{ttft_counts}` | `{throughput_counts}` |"
        )
    report_lines.extend(
        [
            "",
            "## Embedding ranking",
            "",
            "| Rank | Provider | Model | Role | Runtime path | Backend | Avg MRR | Avg Hit@1 | Avg retrieval (s) |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for index, item in enumerate((aggregated.get("embeddings") or {}).get("candidate_ranking", []), start=1):
        backend_label = _format_backend_label(item) or "-"
        report_lines.append(
            f"| {index} | `{item.get('provider')}` | `{item.get('model')}` | `{item.get('candidate_role')}` | `{item.get('runtime_path') or '-'}` | `{backend_label}` | {float(item.get('avg_mrr') or 0.0):.4f} | {float(item.get('avg_hit_at_1') or 0.0):.4f} | {float(item.get('avg_retrieval_seconds') or 0.0):.4f} |"
        )
    embedding_subset_notes = [
        item
        for item in ((aggregated.get("embeddings") or {}).get("subset_notes") or [])
        if isinstance(item, dict)
    ]
    if embedding_subset_notes:
        report_lines.extend(
            [
                "",
                "### Embedding subset notes",
                "",
            ]
        )
        for item in embedding_subset_notes:
            report_lines.append(f"- `{item.get('subset_label') or item.get('subset_id')}`: {item.get('message')}")
    report_lines.extend(
        [
            "",
            "## Runtime path breakdown",
            "",
            "| Runtime path | Cases | Successful | Failed | Expected overhead | Backend examples |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for item in aggregated.get("runtime_path_breakdown") or []:
        backend_examples = ", ".join(item.get("backend_examples") or []) or "-"
        report_lines.append(
            f"| `{item.get('runtime_path')}` | {int(item.get('case_count') or 0)} | {int(item.get('successful_cases') or 0)} | {int(item.get('failed_cases') or 0)} | {'yes' if item.get('path_overhead_expected') else 'no'} | {backend_examples} |"
        )
    model_resolution_summary = aggregated.get("model_resolution_summary") if isinstance(aggregated.get("model_resolution_summary"), dict) else {}
    substitutions = [item for item in (model_resolution_summary.get("substitutions") or []) if isinstance(item, dict)]
    report_lines.extend(
        [
            "",
            "## Requested vs resolved model mapping",
            "",
            f"- Resolution counts: `{json.dumps(model_resolution_summary.get('counts') or {}, ensure_ascii=False, sort_keys=True)}`",
        ]
    )
    if substitutions:
        report_lines.extend(
            [
                "",
                "| Group | Provider | Requested model | Resolved model | Mapping status | Resolution source |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in substitutions:
            report_lines.append(
                f"| `{item.get('group') or '-'}` | `{item.get('provider_requested') or '-'}` | `{item.get('model_requested') or '-'}` | `{item.get('model_effective') or '-'}` | `{item.get('mapping_status') or '-'}` | `{item.get('resolution_source') or '-'}` |"
            )
    else:
        report_lines.append("- No requested-vs-resolved substitutions were needed for the latest case results.")
    if reranker_events or ocr_vlm_events:
        report_lines.extend([""])
        report_lines.extend(build_round2_report_sections(aggregated))
    report_lines.extend(
        [
            "",
            "## Fairness notes",
            "",
            "- Temperature, top_p, max output tokens, context windows, prompt profile, response format, runtime bucket, and quantization family are captured per case.",
            "- Seed is recorded as requested metadata, but not all providers in this repo currently expose a universal deterministic seed control.",
            "- Direct runtimes and hub-wrapped runtimes are now distinguished explicitly in the raw events, normalized tables, aggregated summaries, and this report.",
            "- A `huggingface_server` alias backed by Ollama is treated as a wrapped runtime path, not as identical to direct Ollama, because it may add hub/router HTTP overhead.",
            "- Comparisons are only apples-to-apples where provider/runtime semantics align; exact resolved runtime artifact details are stored in `environment_snapshot.json` and raw events.",
            "",
        ]
    )
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return aggregated


def run_phase8_5_benchmark(
    *,
    manifest: dict[str, object],
    registry: dict[str, dict[str, object]],
    run_id: str,
    run_dir: Path,
    selected_groups: list[str],
    smoke: bool,
    provider_filter: str | None,
    model_filter: str | None,
    resume: bool,
) -> dict[str, object]:
    timeout_policy = manifest.get("timeout_policy") if isinstance(manifest.get("timeout_policy"), dict) else {}
    preflight = build_preflight_payload(
        manifest,
        registry=registry,
        run_id=run_id,
        output_dir=run_dir,
        selected_groups=selected_groups,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
        resume=resume,
    )
    raw_events_path = run_dir / "raw" / "events.jsonl"
    successful_case_ids = load_successful_case_ids(raw_events_path) if resume else set()
    generation_cases, _ = build_generation_cases(
        manifest,
        registry=registry,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    embedding_cases, _ = build_embedding_cases(
        manifest,
        registry=registry,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    reranker_cases = build_reranker_cases(
        manifest,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    ocr_vlm_cases = build_ocr_vlm_cases(
        manifest,
        smoke=smoke,
        provider_filter=provider_filter,
        model_filter=model_filter,
    )
    execution_cases: list[dict[str, object]] = []
    if "generation" in selected_groups:
        execution_cases.extend(generation_cases)
    if "embeddings" in selected_groups:
        execution_cases.extend(embedding_cases)
    if "rerankers" in selected_groups:
        execution_cases.extend(reranker_cases)
    if "ocr_vlm" in selected_groups:
        execution_cases.extend(ocr_vlm_cases)

    append_jsonl_record(
        raw_events_path,
        {
            "event_type": "run_started",
            "run_id": run_id,
            "started_at": time.time(),
            "selected_groups": selected_groups,
            "smoke": bool(smoke),
            "resume": bool(resume),
        },
    )

    executed_events: list[dict[str, object]] = []
    for case in execution_cases:
        case_id = str(case.get("case_id") or "")
        if resume and case_id in successful_case_ids:
            append_jsonl_record(
                raw_events_path,
                {
                    "event_type": "case_skipped_resume",
                    "run_id": run_id,
                    "case_id": case_id,
                    "group": case.get("group"),
                    "reason": "already_completed_successfully",
                    "timestamp": time.time(),
                },
            )
            continue
        if case.get("group") == "generation":
            event = execute_generation_case(
                case,
                run_id=run_id,
                registry=registry,
                timeout_s=int(timeout_policy.get("generation_case_timeout_s") or 0) or None,
            )
        elif case.get("group") == "embeddings":
            event = execute_embedding_case(
                case,
                run_id=run_id,
                registry=registry,
                run_output_dir=run_dir,
                indexing_timeout_s=int(timeout_policy.get("embedding_indexing_timeout_s") or 0) or None,
                query_timeout_s=int(timeout_policy.get("embedding_query_timeout_s") or 0) or None,
            )
        elif case.get("group") == "rerankers":
            event = execute_reranker_case(
                case,
                run_id=run_id,
                registry=registry,
                run_output_dir=run_dir,
                indexing_timeout_s=int(timeout_policy.get("embedding_indexing_timeout_s") or 0) or None,
                query_timeout_s=int(timeout_policy.get("embedding_query_timeout_s") or 0) or None,
            )
        else:
            event = execute_ocr_vlm_case(case, run_id=run_id)
        append_jsonl_record(raw_events_path, event)
        executed_events.append(event)

    all_case_events = load_case_result_events(raw_events_path)
    resolved_case_artifacts = [
        {
            "case_id": event.get("case_id"),
            "group": event.get("group"),
            "provider_requested": event.get("provider_requested"),
            "provider_effective": event.get("provider_effective"),
            "model_requested": event.get("model_requested"),
            "model_effective": event.get("model_effective"),
            "requested_runtime_family": event.get("requested_runtime_family"),
            "resolved_runtime_family": event.get("resolved_runtime_family"),
            "runtime_family_resolution_status": event.get("runtime_family_resolution_status"),
            "runtime_family_resolution_note": event.get("runtime_family_resolution_note"),
            "model_resolution_status": event.get("model_resolution_status"),
            "model_resolution_source": event.get("model_resolution_source"),
            "requested_model_candidates": event.get("requested_model_candidates") or [],
            "runtime_artifact": event.get("runtime_artifact"),
            "runtime_bucket": event.get("runtime_bucket"),
            "quantization_family": event.get("quantization_family"),
            "runtime_path": event.get("runtime_path"),
            "backend_equivalence_key": event.get("backend_equivalence_key"),
            "equivalent_direct_runtime_key": event.get("equivalent_direct_runtime_key"),
            "path_overhead_expected": event.get("path_overhead_expected"),
            "status": event.get("status"),
        }
        for event in all_case_events
    ]
    environment_snapshot = build_benchmark_environment_snapshot(
        project_root=BASE_DIR,
        registry=registry,
        manifest=manifest,
        selected_groups=selected_groups,
        fairness_config=manifest.get("fairness") if isinstance(manifest.get("fairness"), dict) else {},
        environment_overrides={
            **collect_relevant_environment_values(),
            "timeout_policy": manifest.get("timeout_policy"),
            "resume_policy": manifest.get("resume_policy"),
        },
        resolved_case_artifacts=resolved_case_artifacts,
    )
    aggregated = write_benchmark_outputs(
        run_dir=run_dir,
        manifest=manifest,
        environment_snapshot=environment_snapshot,
        preflight=preflight,
        events=all_case_events,
    )
    append_jsonl_record(
        raw_events_path,
        {
            "event_type": "run_completed",
            "run_id": run_id,
            "finished_at": time.time(),
            "aggregated": {
                "total_cases": aggregated.get("total_cases"),
                "successful_cases": aggregated.get("successful_cases"),
                "failed_cases": aggregated.get("failed_cases"),
            },
        },
    )
    return {
        "preflight": preflight,
        "environment_snapshot": environment_snapshot,
        "aggregated": aggregated,
        "events": all_case_events,
    }
