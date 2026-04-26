from __future__ import annotations

import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.config import BASE_DIR
from src.services.preferences_benchmark import (
    WORKFLOW_TO_USE_CASE,
    build_benchmark_recommendations,
)
from src.providers.registry import build_provider_registry
from src.storage.secret_store import delete_secret, get_secret, set_secret
from src.services.runtime_controls import (
    DOC_PRESETS,
    EXECUTION_POLICIES,
    QUALITY_POSTURES,
    RUNTIME_CONTROLS_STATE_VERSION,
    TABLE_EXTRACTION_MODES,
    OCR_BACKENDS,
    PDF_EXTRACTION_MODES,
    RETRIEVAL_STRATEGIES,
    GROUNDING_STRICTNESS,
    CONTEXT_WINDOWS,
    WORKFLOW_CATALOG,
    _build_connections,
    _catalog_label,
    _clamp_float,
    _clamp_int,
    _default_embedding_provider_key,
    _default_provider_key,
    _derive_doc_preset,
    _derive_execution_policy,
    _derive_fallback_chain,
    _derive_quality_posture,
    _canonical_ollama_hosted_model,
    _default_ollama_embedding_model,
    _looks_like_non_ollama_embedding_model,
    _normalize_context_window_label,
    _normalize_prompt_profile,
    build_effective_rag_settings,
    get_prompt_profiles,
)
from src.storage.preferences_state import load_preferences_state, save_preferences_state
from src.storage.runtime_controls_state import save_runtime_controls_state
from src.storage.runtime_paths import get_preferences_state_path, get_runtime_controls_state_path

if TYPE_CHECKING:
    from src.app.product_bootstrap import ProductBootstrap


PREFERENCES_CONTRACT_VERSION = "preferences.v1"
PREFERENCES_STATE_VERSION = "preferences.state.v1"

DEFAULT_CONNECTION_POLICY_RULES = [
    {
        "id": "allow-hosted-overflow",
        "label": "Allow hosted burst overflow",
        "description": "Allow the active workflow profile to burst from local to hosted capacity when needed.",
        "enabled": True,
    },
    {
        "id": "require-evidence-strict",
        "label": "Require evidence-safe review defaults",
        "description": "Document Review and Comparison should stay within balanced or strict grounding defaults.",
        "enabled": True,
    },
]

DEFAULT_OPERATOR_PREFERENCES = {
    "reducedMotion": False,
    "defaultEvidencePanelOpen": True,
    "defaultExportFormat": "pptx",
    "defaultBenchmarkBaseline": "",
    "showSourceBadges": True,
    "autoOpenInspectorDetails": False,
}

ALLOWED_CONNECTION_OVERLAY_FIELDS = {
    "name",
    "description",
    "role",
    "usageNote",
    "baseUrl",
    "preferredModel",
}

UI_CREDENTIAL_CONNECTION_IDS = {
    "openai": "openai_api_key",
    "huggingface_inference": "huggingface_inference_api_key",
    "ollama_hosted": "ollama_hosted_api_key",
}

EXECUTION_POLICY_VALUES = {str(item.get("value") or "") for item in EXECUTION_POLICIES}
QUALITY_POSTURE_VALUES = {str(item.get("value") or "") for item in QUALITY_POSTURES}
DOC_PRESET_VALUES = {str(item.get("value") or "") for item in DOC_PRESETS}
RETRIEVAL_STRATEGY_VALUES = {str(item.get("value") or "") for item in RETRIEVAL_STRATEGIES} | {"semantic", "lexical"}
WORKFLOW_IDS = [str(item.get("workflowId") or "") for item in WORKFLOW_CATALOG if str(item.get("workflowId") or "")]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(workspace_root: Path | None = None) -> Path:
    return get_preferences_state_path(workspace_root or BASE_DIR)


def _runtime_controls_state_path(workspace_root: Path | None = None) -> Path:
    return get_runtime_controls_state_path(workspace_root or BASE_DIR)


def _clone(value: Any) -> Any:
    return deepcopy(value)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return normalized or "profile"


def _ensure_unique_profile_id(profile_id: str, seen: set[str]) -> str:
    candidate = profile_id
    index = 2
    while candidate in seen:
        candidate = f"{profile_id}-{index}"
        index += 1
    seen.add(candidate)
    return candidate


def _derive_connection_workflow_fit(connection: dict[str, Any]) -> list[str]:
    recommendations = build_benchmark_recommendations()
    workflow_winners = recommendations.get("workflow_winners") if isinstance(recommendations.get("workflow_winners"), dict) else {}
    connection_id = str(connection.get("id") or "").strip()
    workflow_ids: list[str] = []
    for workflow in WORKFLOW_CATALOG:
        workflow_id = str(workflow.get("workflowId") or "")
        use_case_id = WORKFLOW_TO_USE_CASE.get(workflow_id)
        winner = workflow_winners.get(use_case_id) if isinstance(workflow_winners.get(use_case_id), dict) else {}
        if connection_id and connection_id == str(winner.get("provider") or "").strip():
            workflow_ids.append(workflow_id)
    return workflow_ids


def _sanitize_connection_overlay(raw_overlay: dict[str, Any] | None) -> dict[str, Any]:
    overlay = dict(raw_overlay or {})
    normalized: dict[str, Any] = {}
    for key in ALLOWED_CONNECTION_OVERLAY_FIELDS:
        if key not in overlay:
            continue
        value = overlay.get(key)
        text = str(value or "").strip()
        if text:
            normalized[key] = text
    return normalized


def _credential_management_for_connection(connection: dict[str, Any]) -> str:
    if str(connection.get("authMethod") or "none") == "none":
        return "not_required"
    if str(connection.get("id") or "") in UI_CREDENTIAL_CONNECTION_IDS:
        return "macos_keychain"
    return "env_only"


def _supports_ui_credential_update(connection: dict[str, Any]) -> bool:
    return str(connection.get("id") or "") in UI_CREDENTIAL_CONNECTION_IDS


def _connection_usage_note(connection: dict[str, Any]) -> str:
    mode = str(connection.get("mode") or "local")
    if _supports_ui_credential_update(connection):
        return "Credential can be stored locally in the macOS Keychain. The frontend never receives the saved secret back."
    if mode == "local":
        return "Connection metadata is editable in workspace preferences. Credentials remain managed outside the UI."
    if mode == "hosted":
        return "Hosted/shared endpoint available to the workspace. Credentials remain managed outside the UI."
    return "Optional external/cloud endpoint. Secrets are not exposed in the UI and remain managed via environment or external config."


def _build_provider_connections(
    *,
    bootstrap: ProductBootstrap,
    state: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]]]:
    registry = build_provider_registry()
    connections, models_by_connection, embedding_models_by_connection, _ = _build_connections(registry)
    recommendations = build_benchmark_recommendations()
    preferred_model_by_connection = recommendations.get("preferred_model_by_connection") if isinstance(recommendations.get("preferred_model_by_connection"), dict) else {}
    overlays = state.get("connection_overlays") if isinstance(state.get("connection_overlays"), dict) else {}
    test_results = state.get("connection_test_results") if isinstance(state.get("connection_test_results"), dict) else {}
    normalized_connections: list[dict[str, Any]] = []
    for connection in connections:
        connection_id = str(connection.get("id") or "")
        overlay = _sanitize_connection_overlay(overlays.get(connection_id) if isinstance(overlays.get(connection_id), dict) else {})
        test_result = test_results.get(connection_id) if isinstance(test_results.get(connection_id), dict) else {}
        current = dict(connection)
        benchmark_model = str(preferred_model_by_connection.get(connection_id) or "").strip()
        available_models = models_by_connection.get(connection_id) or []
        if benchmark_model and benchmark_model in available_models and not str(overlay.get("preferredModel") or "").strip():
            current["preferredModel"] = benchmark_model
        current = {**current, **overlay}
        current["workflowFit"] = _derive_connection_workflow_fit(current)
        current.setdefault("usageNote", _connection_usage_note(current))
        current["credentialManagement"] = _credential_management_for_connection(current)
        current["supportsCredentialUpdate"] = _supports_ui_credential_update(current)
        if str(test_result.get("checked_at") or "").strip():
            current["lastChecked"] = str(test_result.get("checked_at") or current.get("lastChecked") or "")
        if str(test_result.get("status") or "") in {"connected", "degraded", "disconnected", "not_configured"}:
            current["status"] = str(test_result.get("status"))
        error_message = str(test_result.get("error_message") or "").strip()
        if error_message:
            current["lastErrorMessage"] = error_message
        normalized_connections.append(current)
    return normalized_connections, models_by_connection, embedding_models_by_connection


def _profile_summary(profile: dict[str, Any], connections_by_id: dict[str, dict[str, Any]]) -> str:
    primary_connection_id = str(profile.get("primaryConnectionId") or "")
    embedding_connection_id = str(profile.get("embeddingConnectionId") or "")
    primary_connection = connections_by_id.get(primary_connection_id, {})
    embedding_connection = connections_by_id.get(embedding_connection_id, {})
    primary_name = str(primary_connection.get("name") or primary_connection_id or "Unknown")
    embedding_name = str(embedding_connection.get("name") or embedding_connection_id or "Unknown")
    doc_preset = _catalog_label(DOC_PRESETS, str(profile.get("docProcessingPreset") or "standard"), "Standard")
    retrieval_strategy = str(profile.get("retrievalStrategy") or "hybrid")
    return (
        f"Primary runtime uses {primary_name} with model {profile.get('primaryModel')}, {retrieval_strategy} retrieval, "
        f"embedding via {embedding_name} ({profile.get('embeddingModel')}) and document preset {doc_preset}."
    )


def _verified_profile_workflow_fit(profile: dict[str, Any], recommendations: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    resolved = recommendations or build_benchmark_recommendations()
    workflow_winners = resolved.get("workflow_winners") if isinstance(resolved.get("workflow_winners"), dict) else {}
    provider_id = str(profile.get("primaryConnectionId") or "").strip()
    model_id = str(profile.get("primaryModel") or "").strip()
    fits: list[dict[str, Any]] = []
    for workflow in WORKFLOW_CATALOG:
        workflow_id = str(workflow.get("workflowId") or "")
        use_case_id = WORKFLOW_TO_USE_CASE.get(workflow_id)
        winner = workflow_winners.get(use_case_id) if isinstance(workflow_winners.get(use_case_id), dict) else {}
        winner_provider = str(winner.get("provider") or "").strip()
        winner_model = str(winner.get("model") or "").strip()
        if not winner_provider or not winner_model:
            continue
        if winner_provider != provider_id or winner_model != model_id:
            continue
        reason = str(winner.get("reason") or "").strip()
        fits.append(
            {
                "workflowId": workflow_id,
                "label": str(workflow.get("label") or workflow_id),
                "compatibility": "recommended",
                **({"reason": reason} if reason else {}),
            }
        )
    return fits


def _normalize_runtime_profile(
    *,
    raw_profile: dict[str, Any],
    fallback_profile: dict[str, Any],
    connections: list[dict[str, Any]],
    models_by_connection: dict[str, list[str]],
    embedding_models_by_connection: dict[str, list[str]],
    active_profile_id: str,
    seen_ids: set[str],
) -> dict[str, Any]:
    base = _clone(fallback_profile)
    patch = dict(raw_profile or {})
    connections_by_id = {str(item.get("id") or ""): item for item in connections}

    requested_id = str(patch.get("id") or base.get("id") or patch.get("name") or "profile").strip()
    profile_id = _ensure_unique_profile_id(_slugify(requested_id), seen_ids)
    canonical_profile_id = profile_id.lower()
    is_current_profile = canonical_profile_id == "current-product-runtime"
    is_deep_review_profile = canonical_profile_id == "deep-review"
    is_local_profile = canonical_profile_id == "local-only"

    primary_connection_id = str(patch.get("primaryConnectionId") or base.get("primaryConnectionId") or "").strip()
    if is_current_profile or is_deep_review_profile:
        primary_connection_id = "ollama_hosted" if "ollama_hosted" in connections_by_id else primary_connection_id
    elif is_local_profile:
        primary_connection_id = "ollama" if "ollama" in connections_by_id else primary_connection_id
    if primary_connection_id not in connections_by_id:
        primary_connection_id = str(base.get("primaryConnectionId") or next(iter(connections_by_id.keys()), ""))

    embedding_connection_id = str(patch.get("embeddingConnectionId") or base.get("embeddingConnectionId") or primary_connection_id).strip()
    if is_current_profile or is_local_profile:
        embedding_connection_id = "ollama" if "ollama" in connections_by_id else primary_connection_id
    elif is_deep_review_profile:
        embedding_connection_id = "huggingface_inference" if "huggingface_inference" in connections_by_id else primary_connection_id
    if embedding_connection_id not in connections_by_id:
        embedding_connection_id = str(base.get("embeddingConnectionId") or primary_connection_id)

    base_generation = base.get("generation") if isinstance(base.get("generation"), dict) else {}
    patch_generation = patch.get("generation") if isinstance(patch.get("generation"), dict) else {}
    generation = {
        "temperature": _clamp_float(patch_generation.get("temperature"), float(base_generation.get("temperature") or 0.2), minimum=0.0, maximum=1.5),
        "contextWindow": _normalize_context_window_label(patch_generation.get("contextWindow") or base_generation.get("contextWindow") or "auto"),
        "promptProfile": _normalize_prompt_profile(str(patch_generation.get("promptProfile") or base_generation.get("promptProfile") or "")),
        "streaming": bool(patch_generation.get("streaming", base_generation.get("streaming", True))),
        "maxOutputTokens": _clamp_int(patch_generation.get("maxOutputTokens"), int(base_generation.get("maxOutputTokens") or 4096), minimum=256, maximum=262144),
        "topP": _clamp_float(patch_generation.get("topP"), float(base_generation.get("topP") or 0.95), minimum=0.0, maximum=1.0),
        "structuredOutput": bool(patch_generation.get("structuredOutput", base_generation.get("structuredOutput", False))),
    }

    base_retrieval = base.get("retrieval") if isinstance(base.get("retrieval"), dict) else {}
    patch_retrieval = patch.get("retrieval") if isinstance(patch.get("retrieval"), dict) else {}
    retrieval = {
        "topK": _clamp_int(patch_retrieval.get("topK"), int(base_retrieval.get("topK") or 12), minimum=1, maximum=200),
        "chunkSize": _clamp_int(patch_retrieval.get("chunkSize"), int(base_retrieval.get("chunkSize") or 1200), minimum=128, maximum=8192),
        "chunkOverlap": _clamp_int(patch_retrieval.get("chunkOverlap"), int(base_retrieval.get("chunkOverlap") or 200), minimum=0, maximum=2048),
        "rerankPoolSize": _clamp_int(patch_retrieval.get("rerankPoolSize"), int(base_retrieval.get("rerankPoolSize") or 0), minimum=0, maximum=400),
        "rerankLexicalWeight": _clamp_float(patch_retrieval.get("rerankLexicalWeight"), float(base_retrieval.get("rerankLexicalWeight") or 0.3), minimum=0.0, maximum=1.0),
        "groundingStrictness": str(patch_retrieval.get("groundingStrictness") or base_retrieval.get("groundingStrictness") or "balanced").strip().lower() or "balanced",
    }

    base_doc_processing = base.get("docProcessing") if isinstance(base.get("docProcessing"), dict) else {}
    patch_doc_processing = patch.get("docProcessing") if isinstance(patch.get("docProcessing"), dict) else {}
    doc_processing = {
        "pdfExtractionMode": str(patch_doc_processing.get("pdfExtractionMode") or base_doc_processing.get("pdfExtractionMode") or "hybrid").strip().lower() or "hybrid",
        "ocrBackend": str(patch_doc_processing.get("ocrBackend") or base_doc_processing.get("ocrBackend") or "ocrmypdf").strip().lower() or "ocrmypdf",
        "vlmEnhancement": bool(patch_doc_processing.get("vlmEnhancement", base_doc_processing.get("vlmEnhancement", False))),
        "tableExtractionMode": str(patch_doc_processing.get("tableExtractionMode") or base_doc_processing.get("tableExtractionMode") or "auto").strip().lower() or "auto",
        "ocrFailoverEnabled": bool(patch_doc_processing.get("ocrFailoverEnabled", base_doc_processing.get("ocrFailoverEnabled", True))),
        "scannedDocumentThreshold": _clamp_float(
            patch_doc_processing.get("scannedDocumentThreshold"),
            float(base_doc_processing.get("scannedDocumentThreshold") or 0.6),
            minimum=0.1,
            maximum=1.0,
        ),
    }

    reranking_enabled = bool(patch.get("rerankingEnabled", base.get("rerankingEnabled", retrieval["rerankPoolSize"] > 0)))
    if not reranking_enabled:
        retrieval["rerankPoolSize"] = 0

    primary_model_options = models_by_connection.get(primary_connection_id) or []
    embedding_model_options = embedding_models_by_connection.get(embedding_connection_id) or []
    requested_primary_model = str(patch.get("primaryModel") or base.get("primaryModel") or "").strip()
    requested_embedding_model = str(patch.get("embeddingModel") or base.get("embeddingModel") or "").strip()
    primary_model = requested_primary_model if requested_primary_model else (primary_model_options[0] if primary_model_options else "")
    # Preserve explicitly saved model ids even when the live model catalog is stale or
    # the hosted endpoint is temporarily unreachable. This keeps saved runtime profiles
    # stable and lets Ollama-compatible cloud tags resolve at execution time.
    if not primary_model and primary_model_options:
        primary_model = primary_model_options[0]
    if is_current_profile:
        primary_model = _canonical_ollama_hosted_model(primary_model or "nemotron-3-super:cloud")
    elif is_deep_review_profile:
        primary_model = _canonical_ollama_hosted_model(primary_model or "nemotron-3-nano:30b-cloud")
    embedding_model = requested_embedding_model if requested_embedding_model else (embedding_model_options[0] if embedding_model_options else "")
    if not embedding_model and embedding_model_options:
        embedding_model = embedding_model_options[0]
    if is_current_profile or is_local_profile:
        if not embedding_model or _looks_like_non_ollama_embedding_model(embedding_model):
            embedding_model = (embedding_model_options[0] if embedding_model_options else _default_ollama_embedding_model())
    elif is_deep_review_profile:
        embedding_model = "BAAI/bge-small-en-v1.5"

    derived_fallback_chain = _derive_fallback_chain(connections, primary_connection_id, models_by_connection, embedding_models_by_connection)
    requested_fallback_chain = patch.get("fallbackChain") if isinstance(patch.get("fallbackChain"), list) else (base.get("fallbackChain") if isinstance(base.get("fallbackChain"), list) else [])
    fallback_chain: list[dict[str, Any]] = []
    seen_fallback_steps: set[str] = set()
    for raw_step in requested_fallback_chain:
        if not isinstance(raw_step, dict):
            continue
        connection_id = str(raw_step.get("connectionId") or "").strip()
        if not connection_id:
            continue
        connection = connections_by_id.get(connection_id, {})
        capabilities = connection.get("capabilities") if isinstance(connection.get("capabilities"), dict) else {}
        if not bool(capabilities.get("generation")) and not bool(capabilities.get("embeddings")):
            continue
        model_choices = models_by_connection.get(connection_id) or []
        embedding_choices = embedding_models_by_connection.get(connection_id) or []
        model_name = str(raw_step.get("model") or "").strip()
        if not model_name:
            if model_choices:
                model_name = model_choices[0]
            elif embedding_choices:
                model_name = embedding_choices[0]
            else:
                model_name = str(connection.get("preferredModel") or "").strip()
        if not model_name:
            continue
        step_key = f"{connection_id}::{model_name}"
        if step_key in seen_fallback_steps:
            continue
        fallback_chain.append(
            {
                "connectionId": connection_id,
                "model": model_name,
                "label": str(raw_step.get("label") or f"Fallback to {connection.get('name')}").strip() or f"Fallback to {connection.get('name')}",
            }
        )
        seen_fallback_steps.add(step_key)
        if len(fallback_chain) >= 3:
            break

    quality_posture = str(patch.get("qualityPosture") or base.get("qualityPosture") or "").strip()
    if quality_posture not in QUALITY_POSTURE_VALUES:
        quality_posture = _derive_quality_posture(int(retrieval["topK"]), int(generation["maxOutputTokens"]))

    execution_policy = str(patch.get("executionPolicy") or base.get("executionPolicy") or "").strip()
    if execution_policy not in EXECUTION_POLICY_VALUES:
        execution_policy = _derive_execution_policy(connections_by_id.get(primary_connection_id, {}), fallback_chain or derived_fallback_chain)

    fallback_enabled = bool(patch.get("fallbackEnabled", base.get("fallbackEnabled", bool(fallback_chain or derived_fallback_chain))))
    if execution_policy == "local_only":
        fallback_enabled = False
    if is_current_profile or is_deep_review_profile or is_local_profile:
        fallback_enabled = False
        fallback_chain = []
    elif not fallback_enabled:
        fallback_chain = []
    elif not fallback_chain:
        fallback_chain = derived_fallback_chain

    doc_processing_preset = str(patch.get("docProcessingPreset") or base.get("docProcessingPreset") or "").strip()
    if doc_processing_preset not in DOC_PRESET_VALUES:
        doc_processing_preset = _derive_doc_preset(doc_processing)

    retrieval_strategy = str(patch.get("retrievalStrategy") or base.get("retrievalStrategy") or "hybrid").strip().lower()
    if retrieval_strategy not in RETRIEVAL_STRATEGY_VALUES:
        retrieval_strategy = "hybrid"

    # The three built-in profiles deliberately share the same request wiring as
    # Current Product Runtime. Old saved copies of Deep Review/Local Only may
    # contain stale provider, fallback, or embedding fields from previous builds;
    # reset those canonical fields here so selecting a profile always means the
    # backend calls exactly the provider/model displayed in Preferences.
    if is_current_profile:
        primary_connection_id = "ollama_hosted" if "ollama_hosted" in connections_by_id else primary_connection_id
        primary_model = _canonical_ollama_hosted_model("nemotron-3-super:cloud")
        embedding_connection_id = "ollama" if "ollama" in connections_by_id else primary_connection_id
        embedding_model = _default_ollama_embedding_model() if embedding_connection_id == "ollama" else embedding_model
        execution_policy = "hosted_generation_local_embeddings"
        quality_posture = "low_latency"
        doc_processing_preset = "standard"
        fallback_enabled = False
        fallback_chain = []
    elif is_deep_review_profile:
        primary_connection_id = "ollama_hosted" if "ollama_hosted" in connections_by_id else primary_connection_id
        primary_model = _canonical_ollama_hosted_model("nemotron-3-nano:30b-cloud")
        embedding_connection_id = "huggingface_inference" if "huggingface_inference" in connections_by_id else primary_connection_id
        embedding_model = "BAAI/bge-small-en-v1.5"
        execution_policy = "hosted_only"
        quality_posture = "low_latency"
        doc_processing_preset = "standard"
        fallback_enabled = False
        fallback_chain = []
    elif is_local_profile:
        primary_connection_id = "ollama" if "ollama" in connections_by_id else primary_connection_id
        primary_model = "qwen2.5:7b"
        embedding_connection_id = "ollama" if "ollama" in connections_by_id else primary_connection_id
        embedding_model = _default_ollama_embedding_model() if embedding_connection_id == "ollama" else embedding_model
        execution_policy = "local_only"
        quality_posture = "privacy_first"
        doc_processing_preset = "standard"
        fallback_enabled = False
        fallback_chain = []

    intended_workflows = patch.get("intendedWorkflows") if isinstance(patch.get("intendedWorkflows"), list) else base.get("intendedWorkflows")
    normalized_workflows = [str(item).strip() for item in (intended_workflows or WORKFLOW_IDS) if str(item).strip() in WORKFLOW_IDS]
    if not normalized_workflows:
        normalized_workflows = WORKFLOW_IDS[:]

    normalized = {
        "id": profile_id,
        "name": str(patch.get("name") or base.get("name") or f"Profile {profile_id}").strip() or f"Profile {profile_id}",
        "primaryConnectionId": primary_connection_id,
        "primaryModel": primary_model,
        "fallbackEnabled": fallback_enabled,
        "fallbackChain": fallback_chain,
        "executionPolicy": execution_policy,
        "retrievalStrategy": retrieval_strategy,
        "embeddingConnectionId": embedding_connection_id,
        "embeddingModel": embedding_model,
        "rerankingEnabled": reranking_enabled,
        "docProcessingPreset": doc_processing_preset,
        "qualityPosture": quality_posture,
        "intendedWorkflows": normalized_workflows,
        "isActive": profile_id == active_profile_id,
        "isDefault": bool(patch.get("isDefault", profile_id == active_profile_id)),
        "summary": "",
        "generation": generation,
        "retrieval": retrieval,
        "docProcessing": doc_processing,
        "workflowFit": [],
    }
    normalized["workflowFit"] = _verified_profile_workflow_fit(normalized)
    normalized["summary"] = str(patch.get("summary") or "").strip() or _profile_summary(normalized, connections_by_id)
    return normalized


def _seed_runtime_profiles(
    *,
    base_profile: dict[str, Any],
    connections: list[dict[str, Any]],
    models_by_connection: dict[str, list[str]],
    embedding_models_by_connection: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], str]:
    connections_by_id = {str(connection.get("id") or ""): connection for connection in connections}

    hosted_connection_id = "ollama_hosted" if "ollama_hosted" in connections_by_id else str(base_profile.get("primaryConnectionId") or "ollama")
    local_connection_id = "ollama" if "ollama" in connections_by_id else str(base_profile.get("primaryConnectionId") or hosted_connection_id)
    # Canonical hosted profiles should not inherit a Hugging Face embedding provider
    # from prior runtime state. Keep embeddings on Ollama unless Ollama is absent.
    embedding_connection_id = local_connection_id if local_connection_id in connections_by_id else hosted_connection_id
    embedding_model_choices = embedding_models_by_connection.get(embedding_connection_id) or []
    embedding_model = str(base_profile.get("embeddingModel") or "").strip() or (embedding_model_choices[0] if embedding_model_choices else "")
    if not embedding_model or _looks_like_non_ollama_embedding_model(embedding_model):
        embedding_model = embedding_model_choices[0] if embedding_model_choices else _default_ollama_embedding_model()

    base_generation = _clone(base_profile.get("generation") if isinstance(base_profile.get("generation"), dict) else {})
    base_retrieval = _clone(base_profile.get("retrieval") if isinstance(base_profile.get("retrieval"), dict) else {})
    base_doc_processing = _clone(base_profile.get("docProcessing") if isinstance(base_profile.get("docProcessing"), dict) else {})
    base_doc_preset = str(base_profile.get("docProcessingPreset") or _derive_doc_preset(base_doc_processing) or "standard")

    common_generation = {
        **base_generation,
        "temperature": 0.2,
        "topP": 0.95,
        "maxOutputTokens": 4352,
        "contextWindow": "auto",
        "promptProfile": _normalize_prompt_profile(None),
        "streaming": True,
        "structuredOutput": False,
    }
    common_retrieval = {
        **base_retrieval,
        "groundingStrictness": str(base_retrieval.get("groundingStrictness") or "balanced"),
    }

    def _fallback_chain_for(profile_connection_id: str, *, enabled: bool) -> list[dict[str, str]]:
        if not enabled:
            return []
        return _derive_fallback_chain(connections, profile_connection_id, models_by_connection, embedding_models_by_connection)

    current_product_seed = {
        **_clone(base_profile),
        "id": "current-product-runtime",
        "name": "Current Product Runtime",
        "primaryConnectionId": hosted_connection_id,
        "primaryModel": "nemotron-3-super:cloud",
        "embeddingConnectionId": embedding_connection_id,
        "embeddingModel": embedding_model,
        "fallbackEnabled": False,
        "fallbackChain": [],
        "executionPolicy": "hosted_generation_local_embeddings",
        "retrievalStrategy": "hybrid",
        "rerankingEnabled": bool((base_retrieval.get("rerankPoolSize") or 0) > 0),
        "docProcessingPreset": "standard",
        "qualityPosture": "low_latency",
        "generation": common_generation,
        "retrieval": common_retrieval,
        "docProcessing": base_doc_processing,
        "intendedWorkflows": WORKFLOW_IDS[:],
        "summary": "Hosted Ollama generation profile using Nemotron 3 Super Cloud with local Ollama embeddings and the standard document processing stack.",
        "isDefault": True,
    }
    # Build Demo Profile and Local Only as direct copies of Current Product Runtime
    # with only the visible runtime choices changed. This keeps every saved
    # profile on the same request/credential resolution path.
    demo_embedding_connection_id = "huggingface_inference" if "huggingface_inference" in connections_by_id else hosted_connection_id
    deep_review_seed = {
        **_clone(current_product_seed),
        "id": "deep-review",
        "name": "Demo Profile",
        "primaryConnectionId": hosted_connection_id,
        "primaryModel": "nemotron-3-nano:30b-cloud",
        "embeddingConnectionId": demo_embedding_connection_id,
        "embeddingModel": "BAAI/bge-small-en-v1.5",
        "executionPolicy": "hosted_only",
        "qualityPosture": "low_latency",
        "retrieval": {**common_retrieval, "groundingStrictness": "balanced"},
        "summary": "Live demo profile using hosted Ollama Nemotron 3 Nano 30B Cloud with Hugging Face BGE-small embeddings for predictable low-latency runs.",
    }
    local_seed = {
        **_clone(current_product_seed),
        "id": "local-only",
        "name": "Local Only",
        "primaryConnectionId": local_connection_id,
        "primaryModel": "qwen2.5:7b",
        "embeddingConnectionId": local_connection_id,
        "embeddingModel": (embedding_models_by_connection.get(local_connection_id) or [embedding_model])[0] if (embedding_models_by_connection.get(local_connection_id) or [embedding_model]) else embedding_model,
        "executionPolicy": "local_only",
        "qualityPosture": "privacy_first",
        "docProcessingPreset": "standard",
        "retrieval": {**common_retrieval, "groundingStrictness": "balanced"},
        "summary": "Fully local profile for privacy-first runs. Keeps prompts, retrieval, and document context on the local Ollama runtime.",
    }
    seeds = [current_product_seed, deep_review_seed, local_seed]

    seen_ids: set[str] = set()
    active_profile_id = "current-product-runtime"
    profiles = [
        _normalize_runtime_profile(
            raw_profile=seed,
            fallback_profile=base_profile,
            connections=connections,
            models_by_connection=models_by_connection,
            embedding_models_by_connection=embedding_models_by_connection,
            active_profile_id=active_profile_id,
            seen_ids=seen_ids,
        )
        for seed in seeds
    ]
    return profiles, active_profile_id


def _canonical_profile_id(profile_id: str) -> str:
    normalized = _slugify(profile_id)
    aliases = {
        "workspace-default": "current-product-runtime",
        "grounded-review": "current-product-runtime",
        "current-product-runtime": "current-product-runtime",
        "fast-triage": "local-only",
        "local": "local-only",
        "local-only": "local-only",
        "action-plan-benchmark": "deep-review",
        "action-plan-summary": "deep-review",
        "deep-review": "deep-review",
    }
    return aliases.get(normalized, normalized)


def _normalize_connection_policy_rules(raw_rules: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    raw_lookup = {
        str(item.get("id") or ""): item
        for item in (raw_rules or [])
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    normalized: list[dict[str, Any]] = []
    for default_rule in DEFAULT_CONNECTION_POLICY_RULES:
        raw = raw_lookup.get(str(default_rule.get("id") or ""), {})
        normalized.append(
            {
                "id": default_rule["id"],
                "label": str(raw.get("label") or default_rule["label"]),
                "description": str(raw.get("description") or default_rule["description"]),
                "enabled": bool(raw.get("enabled", default_rule["enabled"])),
            }
        )
    return normalized


def _normalize_operator_preferences(raw_preferences: dict[str, Any] | None, profiles: list[dict[str, Any]], active_profile_id: str) -> dict[str, Any]:
    raw = dict(raw_preferences or {})
    profile_ids = {str(profile.get("id") or "") for profile in profiles}
    benchmark_baseline = str(raw.get("defaultBenchmarkBaseline") or DEFAULT_OPERATOR_PREFERENCES["defaultBenchmarkBaseline"] or active_profile_id).strip()
    if benchmark_baseline not in profile_ids:
        benchmark_baseline = active_profile_id
    export_format = str(raw.get("defaultExportFormat") or DEFAULT_OPERATOR_PREFERENCES["defaultExportFormat"]).strip().lower()
    if export_format not in {"pdf", "markdown", "json", "pptx"}:
        export_format = "pptx"
    return {
        "reducedMotion": bool(raw.get("reducedMotion", DEFAULT_OPERATOR_PREFERENCES["reducedMotion"])),
        "defaultEvidencePanelOpen": bool(raw.get("defaultEvidencePanelOpen", DEFAULT_OPERATOR_PREFERENCES["defaultEvidencePanelOpen"])),
        "defaultExportFormat": export_format,
        "defaultBenchmarkBaseline": benchmark_baseline,
        "showSourceBadges": bool(raw.get("showSourceBadges", DEFAULT_OPERATOR_PREFERENCES["showSourceBadges"])),
        "autoOpenInspectorDetails": bool(raw.get("autoOpenInspectorDetails", DEFAULT_OPERATOR_PREFERENCES["autoOpenInspectorDetails"])),
    }


def _normalize_preferences_state(
    *,
    bootstrap: ProductBootstrap,
    raw_state: dict[str, Any] | None,
) -> dict[str, Any]:
    state = dict(raw_state or {})
    runtime_rag_settings = build_effective_rag_settings(default_settings=bootstrap.rag_settings, workspace_root=bootstrap.workspace_root)
    registry = build_provider_registry()
    connections, models_by_connection, embedding_models_by_connection, _ = _build_connections(registry)
    runtime_connections, models_by_connection, embedding_models_by_connection = _build_provider_connections(bootstrap=bootstrap, state=state)

    base_profile = {
        "id": "workspace-default",
        "name": "Current Product Runtime",
        "primaryConnectionId": _default_provider_key(registry),
        "primaryModel": (models_by_connection.get(_default_provider_key(registry)) or [""])[0],
        "fallbackChain": _derive_fallback_chain(runtime_connections, _default_provider_key(registry), models_by_connection, embedding_models_by_connection),
        "executionPolicy": "prefer_local_burst_hosted",
        "retrievalStrategy": "hybrid",
        "embeddingConnectionId": _default_embedding_provider_key(registry, runtime_rag_settings),
        "embeddingModel": (embedding_models_by_connection.get(_default_embedding_provider_key(registry, runtime_rag_settings)) or [runtime_rag_settings.embedding_model])[0],
        "rerankingEnabled": runtime_rag_settings.rerank_pool_size > 0,
        "docProcessingPreset": _derive_doc_preset(
            {
                "pdfExtractionMode": runtime_rag_settings.pdf_extraction_mode,
                "ocrBackend": runtime_rag_settings.evidence_ocr_backend,
                "vlmEnhancement": runtime_rag_settings.pdf_evidence_pipeline_enabled,
                "tableExtractionMode": "auto",
                "ocrFailoverEnabled": runtime_rag_settings.pdf_ocr_fallback_enabled,
                "scannedDocumentThreshold": runtime_rag_settings.pdf_scan_image_ocr_min_suspicious_ratio,
            }
        ),
        "qualityPosture": _derive_quality_posture(runtime_rag_settings.top_k, 4096),
        "intendedWorkflows": WORKFLOW_IDS[:],
        "isActive": True,
        "isDefault": True,
        "summary": "",
        "generation": {
            "temperature": 0.2,
            "contextWindow": "auto",
            "promptProfile": _normalize_prompt_profile(None),
            "streaming": True,
            "maxOutputTokens": 4096,
            "topP": 0.95,
            "structuredOutput": False,
        },
        "retrieval": {
            "topK": runtime_rag_settings.top_k,
            "chunkSize": runtime_rag_settings.chunk_size,
            "chunkOverlap": runtime_rag_settings.chunk_overlap,
            "rerankPoolSize": runtime_rag_settings.rerank_pool_size,
            "rerankLexicalWeight": runtime_rag_settings.rerank_lexical_weight,
            "groundingStrictness": "balanced",
        },
        "docProcessing": {
            "pdfExtractionMode": runtime_rag_settings.pdf_extraction_mode,
            "ocrBackend": runtime_rag_settings.evidence_ocr_backend,
            "vlmEnhancement": runtime_rag_settings.pdf_evidence_pipeline_enabled,
            "tableExtractionMode": "auto",
            "ocrFailoverEnabled": runtime_rag_settings.pdf_ocr_fallback_enabled,
            "scannedDocumentThreshold": runtime_rag_settings.pdf_scan_image_ocr_min_suspicious_ratio,
        },
        "workflowFit": [],
    }

    seed_profiles, seed_active_profile_id = _seed_runtime_profiles(
        base_profile=base_profile,
        connections=runtime_connections,
        models_by_connection=models_by_connection,
        embedding_models_by_connection=embedding_models_by_connection,
    )
    raw_profiles = list(seed_profiles)
    active_profile_id = _canonical_profile_id(str(state.get("active_profile_id") or seed_active_profile_id).strip() or seed_active_profile_id)
    seen_ids: set[str] = set()
    normalized_profiles = [
        _normalize_runtime_profile(
            raw_profile=item if isinstance(item, dict) else {},
            fallback_profile=seed_profiles[0],
            connections=runtime_connections,
            models_by_connection=models_by_connection,
            embedding_models_by_connection=embedding_models_by_connection,
            active_profile_id=active_profile_id,
            seen_ids=seen_ids,
        )
        for item in raw_profiles
    ]
    if not normalized_profiles:
        normalized_profiles = seed_profiles
    profile_ids = [str(profile.get("id") or "") for profile in normalized_profiles]
    if active_profile_id not in profile_ids:
        active_profile_id = profile_ids[0]
    for profile in normalized_profiles:
        profile["isActive"] = str(profile.get("id") or "") == active_profile_id
        profile["isDefault"] = str(profile.get("id") or "") == active_profile_id or bool(profile.get("isDefault", False))

    normalized_policy_rules = _normalize_connection_policy_rules(
        state.get("connection_policy_rules") if isinstance(state.get("connection_policy_rules"), list) else None,
    )
    normalized_operator_preferences = _normalize_operator_preferences(
        state.get("operator_preferences") if isinstance(state.get("operator_preferences"), dict) else None,
        normalized_profiles,
        active_profile_id,
    )
    connection_overlays = {
        str(key): _sanitize_connection_overlay(value if isinstance(value, dict) else {})
        for key, value in (state.get("connection_overlays") if isinstance(state.get("connection_overlays"), dict) else {}).items()
        if str(key).strip()
    }
    connection_test_results = {
        str(key): {
            "status": str(value.get("status") or ""),
            "checked_at": str(value.get("checked_at") or ""),
            "latency_ms": float(value.get("latency_ms") or 0.0) if str(value.get("latency_ms") or "").strip() else None,
            "error_message": str(value.get("error_message") or "").strip() or None,
        }
        for key, value in (state.get("connection_test_results") if isinstance(state.get("connection_test_results"), dict) else {}).items()
        if str(key).strip() and isinstance(value, dict)
    }

    return {
        "contract_version": PREFERENCES_STATE_VERSION,
        "updated_at": str(state.get("updated_at") or "").strip() or None,
        "active_profile_id": active_profile_id,
        "runtime_profiles": normalized_profiles,
        "connection_policy_rules": normalized_policy_rules,
        "operator_preferences": normalized_operator_preferences,
        "connection_overlays": connection_overlays,
        "connection_test_results": connection_test_results,
        "provider_connections": runtime_connections,
        "options": {
            "modelsByConnection": models_by_connection,
            "embeddingModelsByConnection": embedding_models_by_connection,
        },
    }


def _sync_active_profile_to_runtime_controls(bootstrap: ProductBootstrap, state: dict[str, Any]) -> None:
    profiles = state.get("runtime_profiles") if isinstance(state.get("runtime_profiles"), list) else []
    active_profile_id = str(state.get("active_profile_id") or "").strip()
    active_profile = next((profile for profile in profiles if isinstance(profile, dict) and str(profile.get("id") or "") == active_profile_id), None)
    if active_profile is None and profiles:
        active_profile = profiles[0]
    if active_profile is None:
        return
    save_runtime_controls_state(
        _runtime_controls_state_path(bootstrap.workspace_root),
        {
            "contract_version": RUNTIME_CONTROLS_STATE_VERSION,
            "updated_at": _utc_now_iso(),
            "profile": active_profile,
        },
    )


def build_preferences_payload(bootstrap: ProductBootstrap) -> dict[str, Any]:
    raw_state = load_preferences_state(_state_path(bootstrap.workspace_root)) or {}
    normalized = _normalize_preferences_state(bootstrap=bootstrap, raw_state=raw_state)
    provider_connections, models_by_connection, embedding_models_by_connection = _build_provider_connections(bootstrap=bootstrap, state=normalized)
    prompt_profiles = get_prompt_profiles()
    return {
        "ok": True,
        "contract_version": PREFERENCES_CONTRACT_VERSION,
        "updated_at": normalized.get("updated_at"),
        "active_profile_id": normalized.get("active_profile_id"),
        "provider_connections": provider_connections,
        "runtime_profiles": normalized.get("runtime_profiles") or [],
        "connection_policy_rules": normalized.get("connection_policy_rules") or [],
        "operator_preferences": normalized.get("operator_preferences") or _clone(DEFAULT_OPERATOR_PREFERENCES),
        "catalogs": {
            "executionPolicies": EXECUTION_POLICIES,
            "qualityPostures": QUALITY_POSTURES,
            "docPresets": DOC_PRESETS,
            "retrievalStrategies": RETRIEVAL_STRATEGIES,
            "groundingStrictness": GROUNDING_STRICTNESS,
            "contextWindows": CONTEXT_WINDOWS,
            "pdfExtractionModes": PDF_EXTRACTION_MODES,
            "ocrBackends": OCR_BACKENDS,
            "tableExtractionModes": TABLE_EXTRACTION_MODES,
            "promptProfiles": [
                {"value": key, "label": value.get("label") or key, "description": value.get("description")}
                for key, value in prompt_profiles.items()
            ],
        },
        "options": {
            "modelsByConnection": models_by_connection,
            "embeddingModelsByConnection": embedding_models_by_connection,
        },
        "credential_policy": {
            "mode": "macos_keychain_for_supported_connections",
            "can_update_from_ui": True,
            "notes": [
                "OpenAI, Hugging Face Inference and Ollama Hosted credentials can be stored locally in the macOS Keychain.",
                "The frontend never receives credential values in clear text.",
                "Other connections continue using configured/not-configured state and editable non-secret metadata only.",
            ],
        },
    }


def _refresh_bootstrap_provider_registry(bootstrap: ProductBootstrap) -> None:
    """Refresh long-lived provider instances after a UI-managed secret changes."""
    try:
        refreshed_registry = build_provider_registry()
        bootstrap.provider_registry.clear()
        bootstrap.provider_registry.update(refreshed_registry)
    except Exception:
        # Preferences payloads are built from a fresh registry below; do not fail the
        # credential save just because an optional provider cannot be refreshed here.
        pass


def update_preferences_connection_credential(bootstrap: ProductBootstrap, connection_id: str, api_key: str | None) -> dict[str, Any]:
    normalized_connection_id = str(connection_id or "").strip()
    secret_key = UI_CREDENTIAL_CONNECTION_IDS.get(normalized_connection_id)
    if not secret_key:
        raise ValueError("This connection does not support credential updates from the UI.")

    secret_value = str(api_key or "").strip()
    ok = delete_secret(secret_key) if not secret_value else set_secret(secret_key, secret_value)
    if not ok:
        raise ValueError("Could not update the credential in the local macOS Keychain.")
    if secret_value and str(get_secret(secret_key) or "").strip() != secret_value:
        raise ValueError("Credential was saved, but the runtime could not read back the new Keychain value.")

    _refresh_bootstrap_provider_registry(bootstrap)

    raw_state = load_preferences_state(_state_path(bootstrap.workspace_root)) or {}
    raw_state["updated_at"] = _utc_now_iso()
    save_preferences_state(_state_path(bootstrap.workspace_root), raw_state)
    return build_preferences_payload(bootstrap)


def update_preferences_payload(bootstrap: ProductBootstrap, patch_payload: dict[str, Any]) -> dict[str, Any]:
    current_state = load_preferences_state(_state_path(bootstrap.workspace_root)) or {}
    working_state = _normalize_preferences_state(bootstrap=bootstrap, raw_state=current_state)

    if isinstance(patch_payload.get("runtime_profiles"), list):
        working_state["runtime_profiles"] = [item for item in patch_payload.get("runtime_profiles") or [] if isinstance(item, dict)]
    if str(patch_payload.get("active_profile_id") or "").strip():
        working_state["active_profile_id"] = str(patch_payload.get("active_profile_id") or "").strip()
    if isinstance(patch_payload.get("connection_policy_rules"), list):
        working_state["connection_policy_rules"] = [item for item in patch_payload.get("connection_policy_rules") or [] if isinstance(item, dict)]
    if isinstance(patch_payload.get("operator_preferences"), dict):
        operator_preferences = dict(working_state.get("operator_preferences") or {})
        operator_preferences.update(dict(patch_payload.get("operator_preferences") or {}))
        working_state["operator_preferences"] = operator_preferences
    if isinstance(patch_payload.get("provider_connections"), list):
        overlays = dict(working_state.get("connection_overlays") or {})
        for item in patch_payload.get("provider_connections") or []:
            if not isinstance(item, dict):
                continue
            connection_id = str(item.get("id") or "").strip()
            if not connection_id:
                continue
            current_overlay = overlays.get(connection_id) if isinstance(overlays.get(connection_id), dict) else {}
            next_overlay = {**current_overlay, **_sanitize_connection_overlay(item)}
            overlays[connection_id] = next_overlay
        working_state["connection_overlays"] = overlays

    normalized = _normalize_preferences_state(bootstrap=bootstrap, raw_state=working_state)
    normalized["updated_at"] = _utc_now_iso()

    save_preferences_state(
        _state_path(bootstrap.workspace_root),
        {
            "contract_version": PREFERENCES_STATE_VERSION,
            "updated_at": normalized.get("updated_at"),
            "active_profile_id": normalized.get("active_profile_id"),
            "runtime_profiles": normalized.get("runtime_profiles") or [],
            "connection_policy_rules": normalized.get("connection_policy_rules") or [],
            "operator_preferences": normalized.get("operator_preferences") or _clone(DEFAULT_OPERATOR_PREFERENCES),
            "connection_overlays": normalized.get("connection_overlays") or {},
            "connection_test_results": normalized.get("connection_test_results") or {},
        },
    )
    _sync_active_profile_to_runtime_controls(bootstrap, normalized)
    return build_preferences_payload(bootstrap)


def test_preferences_connection(bootstrap: ProductBootstrap, connection_id: str) -> dict[str, Any]:
    normalized_state = _normalize_preferences_state(
        bootstrap=bootstrap,
        raw_state=load_preferences_state(_state_path(bootstrap.workspace_root)) or {},
    )
    connection_id = str(connection_id or "").strip()
    provider_connections = normalized_state.get("provider_connections") if isinstance(normalized_state.get("provider_connections"), list) else []
    connection = next((item for item in provider_connections if isinstance(item, dict) and str(item.get("id") or "") == connection_id), None)
    if connection is None:
        raise ValueError(f"Unknown connection `{connection_id}`.")

    checked_at = _utc_now_iso()
    started_at = time.perf_counter()
    status = "not_configured"
    error_message: str | None = None

    try:
        if str(connection.get("authMethod") or "none") != "none" and not bool(connection.get("apiKeyConfigured")):
            status = "not_configured"
            error_message = "Credentials are not configured in the current environment."
        else:
            registry = build_provider_registry()
            provider_entry = registry.get(connection_id)
            if not isinstance(provider_entry, dict):
                status = "disconnected"
                error_message = "Provider entry is unavailable in the current registry."
            else:
                instance = provider_entry.get("instance")
                if instance is not None and hasattr(instance, "probe_connection"):
                    probe = instance.probe_connection() or {}
                    status = str(probe.get("status") or "degraded")
                    error_message = str(probe.get("last_error_message") or "").strip() or None
                else:
                    chat_models: list[str] = []
                    embedding_models: list[str] = []
                    if instance is not None and hasattr(instance, "list_available_models"):
                        chat_models = [str(model or "").strip() for model in instance.list_available_models() if str(model or "").strip()]
                    if instance is not None and hasattr(instance, "list_available_embedding_models"):
                        embedding_models = [str(model or "").strip() for model in instance.list_available_embedding_models() if str(model or "").strip()]
                    status = "connected" if chat_models or embedding_models or str(connection.get("status") or "") == "connected" else "degraded"
    except Exception as error:  # pragma: no cover - defensive endpoint behavior
        status = "degraded" if str(connection.get("status") or "") == "connected" else "disconnected"
        error_message = str(error)

    latency_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
    raw_state = load_preferences_state(_state_path(bootstrap.workspace_root)) or {}
    connection_test_results = raw_state.get("connection_test_results") if isinstance(raw_state.get("connection_test_results"), dict) else {}
    connection_test_results = dict(connection_test_results)
    connection_test_results[connection_id] = {
        "status": status,
        "checked_at": checked_at,
        "latency_ms": latency_ms,
        "error_message": error_message,
    }
    normalized_state["connection_test_results"] = connection_test_results
    normalized_state["updated_at"] = _utc_now_iso()
    save_preferences_state(
        _state_path(bootstrap.workspace_root),
        {
            "contract_version": PREFERENCES_STATE_VERSION,
            "updated_at": normalized_state.get("updated_at"),
            "active_profile_id": normalized_state.get("active_profile_id"),
            "runtime_profiles": normalized_state.get("runtime_profiles") or [],
            "connection_policy_rules": normalized_state.get("connection_policy_rules") or [],
            "operator_preferences": normalized_state.get("operator_preferences") or _clone(DEFAULT_OPERATOR_PREFERENCES),
            "connection_overlays": normalized_state.get("connection_overlays") or {},
            "connection_test_results": connection_test_results,
        },
    )
    return {
        "ok": True,
        "connection_id": connection_id,
        "result": {
            "status": status,
            "checked_at": checked_at,
            "latency_ms": latency_ms,
            "error_message": error_message,
        },
    }