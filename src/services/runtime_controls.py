from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.config import (
    BASE_DIR,
    RagSettings,
    get_huggingface_inference_settings,
    get_huggingface_server_settings,
    get_huggingface_settings,
    get_ollama_hosted_settings,
    get_ollama_settings,
    get_openai_settings,
    get_rag_settings,
)
from src.providers.registry import build_provider_registry
from src.storage.preferences_state import load_preferences_state, save_preferences_state
from src.prompt_profiles import get_prompt_profiles
from src.storage.runtime_controls_state import (
    load_runtime_controls_state,
    merge_runtime_controls_state,
    save_runtime_controls_state,
)
from src.storage.runtime_paths import get_preferences_state_path, get_runtime_controls_state_path

if TYPE_CHECKING:
    from src.app.product_bootstrap import ProductBootstrap
    from src.product.models import ProductWorkflowRequest


RUNTIME_CONTROLS_CONTRACT_VERSION = "runtime_controls.v1"
RUNTIME_CONTROLS_STATE_VERSION = "runtime_controls.state.v1"

EXECUTION_POLICIES = [
    {"value": "local_only", "label": "Local Only", "description": "Strictly local execution. Fail hard if unavailable."},
    {"value": "prefer_local_burst_hosted", "label": "Prefer Local · Burst to Hosted", "description": "Prefer local inference and keep hosted capacity as overflow/reference."},
    {"value": "hosted_only", "label": "Hosted Only", "description": "Prefer hosted inference as the primary route."},
    {"value": "hosted_deep_review", "label": "Hosted · Deep Review", "description": "Hosted-first posture for heavier review and longer reasoning."},
    {"value": "cloud_selected_workflows", "label": "Cloud · Selected Workflows", "description": "Cloud endpoints are reserved for selected workflows or demo scenarios."},
    {"value": "benchmark_reference_only", "label": "Benchmark Reference Only", "description": "External endpoints remain reference targets for comparison and demos."},
]

QUALITY_POSTURES = [
    {"value": "max_quality", "label": "Max Quality", "description": "Favor richer grounding and deeper outputs over latency."},
    {"value": "balanced", "label": "Balanced", "description": "Balance quality, responsiveness and operational simplicity."},
    {"value": "low_latency", "label": "Low Latency", "description": "Favor shorter responses and lower-latency runtime choices."},
    {"value": "cost_optimized", "label": "Cost Optimized", "description": "Favor cheaper execution paths where quality remains acceptable."},
]

DOC_PRESETS = [
    {"value": "standard", "label": "Standard", "description": "Balanced parsing defaults for typical documents."},
    {"value": "ocr_heavy", "label": "OCR Heavy", "description": "More aggressive OCR and scan recovery posture."},
    {"value": "vlm_enhanced", "label": "VLM Enhanced", "description": "Use richer vision-assisted parsing when enabled."},
    {"value": "fast_text", "label": "Fast Text", "description": "Favor lighter parsing for clean text-first files."},
]

RETRIEVAL_STRATEGIES = [
    {"value": "hybrid", "label": "Hybrid (semantic + lexical)", "description": "Current production-safe retrieval strategy."},
]

GROUNDING_STRICTNESS = [
    {"value": "strict", "label": "Strict — evidence only", "description": "Avoid speculation and stay tightly evidence-bound."},
    {"value": "balanced", "label": "Balanced", "description": "Allow practical synthesis while staying grounded."},
    {"value": "permissive", "label": "Permissive — allow inference", "description": "Allow more inference when evidence is thinner."},
]

CONTEXT_WINDOWS = [
    {"value": "auto", "label": "Auto", "context_window": None},
    {"value": "4k", "label": "4,096", "context_window": 4096},
    {"value": "8k", "label": "8,192", "context_window": 8192},
    {"value": "16k", "label": "16,384", "context_window": 16384},
    {"value": "32k", "label": "32,768", "context_window": 32768},
    {"value": "64k", "label": "65,536", "context_window": 65536},
    {"value": "128k", "label": "131,072", "context_window": 131072},
]

PDF_EXTRACTION_MODES = [
    {"value": "basic", "label": "Basic · pypdf only", "description": "Fastest extraction path for cleaner PDFs."},
    {"value": "hybrid", "label": "Smart hybrid", "description": "Balanced parsing with selective richer extraction."},
    {"value": "complete", "label": "Complete per page", "description": "Higher coverage for difficult documents."},
    {"value": "docling", "label": "Full-document Docling", "description": "Favor full-document richer parsing."},
]

OCR_BACKENDS = [
    {"value": "ocrmypdf", "label": "OCRmyPDF", "description": "Current OCR backend surfaced by the runtime configuration."},
]

TABLE_EXTRACTION_MODES = [
    {"value": "auto", "label": "Auto-detect", "description": "Current product runtime does not expose multiple table extractors yet."},
]

WORKFLOW_CATALOG = [
    {"workflowId": "document-review", "label": "Document Review"},
    {"workflowId": "comparison", "label": "Comparison"},
    {"workflowId": "action-plan", "label": "Action Plan"},
    {"workflowId": "candidate-review", "label": "Candidate Review"},
    {"workflowId": "chat-experiments", "label": "Chat Experiments"},
    {"workflowId": "workflow-inspector", "label": "Workflow Inspector"},
]

PRODUCT_CONNECTION_BLACKLIST = {"huggingface_local"}
BLOCKED_PRODUCT_MODELS = {"pptagent-q8"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(workspace_root: Path | None = None) -> Path:
    return get_runtime_controls_state_path(workspace_root or BASE_DIR)


def _preferences_state_path(workspace_root: Path | None = None) -> Path:
    return get_preferences_state_path(workspace_root or BASE_DIR)


def _catalog_label(catalog: list[dict[str, Any]], value: str, default: str | None = None) -> str:
    normalized = str(value or "").strip().lower()
    for item in catalog:
        if str(item.get("value") or "").strip().lower() == normalized:
            return str(item.get("label") or value)
    return default or value


def _clamp_float(value: Any, fallback: float, *, minimum: float, maximum: float, precision: int = 2) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        resolved = float(fallback)
    return round(max(minimum, min(maximum, resolved)), precision)


def _clamp_int(value: Any, fallback: int, *, minimum: int, maximum: int) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        resolved = int(fallback)
    return max(minimum, min(maximum, resolved))


def _normalize_context_window_label(value: Any, default_value: int | None = None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "auto":
        return "auto"
    for item in CONTEXT_WINDOWS:
        if str(item.get("value") or "") == normalized:
            return normalized
        if item.get("context_window") is not None and str(item.get("context_window")) == normalized:
            return str(item.get("value"))
    if isinstance(default_value, int):
        for item in CONTEXT_WINDOWS:
            if item.get("context_window") == default_value:
                return str(item.get("value"))
    return "auto"


def _context_window_from_label(value: str | None) -> int | None:
    normalized = str(value or "").strip().lower()
    if not normalized or normalized == "auto":
        return None
    for item in CONTEXT_WINDOWS:
        if str(item.get("value") or "") == normalized:
            context_window = item.get("context_window")
            return int(context_window) if isinstance(context_window, int) else None
    return int(normalized) if normalized.isdigit() else None


def _normalize_prompt_profile(value: str | None) -> str:
    prompt_profiles = get_prompt_profiles()
    normalized = str(value or "").strip()
    if normalized in prompt_profiles:
        return normalized
    default_prompt = get_ollama_settings().default_prompt_profile
    if default_prompt in prompt_profiles:
        return default_prompt
    return next(iter(prompt_profiles.keys()), "neutro")


def _is_blocked_product_model(model_name: str | None) -> bool:
    normalized = str(model_name or "").strip().lower()
    if not normalized:
        return False
    return any(normalized == blocked or normalized.startswith(f"{blocked}:") for blocked in BLOCKED_PRODUCT_MODELS)


def _filter_product_models(models: list[str]) -> list[str]:
    ordered: list[str] = []
    for model in models:
        normalized = str(model or "").strip()
        if not normalized or _is_blocked_product_model(normalized) or normalized in ordered:
            continue
        ordered.append(normalized)
    return ordered


def _provider_static_settings() -> dict[str, dict[str, Any]]:
    ollama = get_ollama_settings()
    ollama_hosted = get_ollama_hosted_settings()
    openai = get_openai_settings()
    hf_server = get_huggingface_server_settings()
    hf_inference = get_huggingface_inference_settings()
    settings = {
        "ollama": {
            "providerFamily": "ollama",
            "mode": "local",
            "baseUrl": ollama.base_url,
            "authMethod": "none",
            "apiKeyConfigured": False,
            "defaultModel": ollama.default_model,
            "defaultContextWindow": ollama.default_context_window,
            "defaultPromptProfile": ollama.default_prompt_profile,
            "defaultTopP": ollama.default_top_p,
            "defaultMaxTokens": ollama.default_max_tokens,
            "defaultTemperature": ollama.default_temperature,
            "availableModelsEnv": list(ollama.available_models_env),
            "availableEmbeddingModelsEnv": list(ollama.available_embedding_models_env),
        },
        "openai": {
            "providerFamily": "openai_compatible",
            "mode": "cloud",
            "baseUrl": "https://api.openai.com/v1",
            "authMethod": "api_key",
            "apiKeyConfigured": bool(openai.api_key),
            "defaultModel": openai.model,
            "defaultContextWindow": openai.default_context_window,
            "defaultPromptProfile": get_ollama_settings().default_prompt_profile,
            "defaultTopP": openai.default_top_p,
            "defaultMaxTokens": openai.default_max_tokens,
            "defaultTemperature": 0.2,
            "availableModelsEnv": list(openai.available_models_env),
            "availableEmbeddingModelsEnv": list(openai.available_embedding_models_env),
        },
        "huggingface_server": {
            "providerFamily": "huggingface",
            "mode": "hosted",
            "baseUrl": hf_server.base_url,
            "authMethod": "bearer_token" if hf_server.api_key else "none",
            "apiKeyConfigured": bool(hf_server.api_key),
            "defaultModel": hf_server.model,
            "defaultContextWindow": hf_server.default_context_window,
            "defaultPromptProfile": get_ollama_settings().default_prompt_profile,
            "defaultTopP": hf_server.default_top_p,
            "defaultMaxTokens": hf_server.default_max_tokens,
            "defaultTemperature": 0.2,
            "availableModelsEnv": list(hf_server.available_models_env),
            "availableEmbeddingModelsEnv": list(hf_server.available_embedding_models_env),
        },
        "huggingface_inference": {
            "providerFamily": "huggingface",
            "mode": "cloud",
            "baseUrl": hf_inference.base_url,
            "authMethod": "bearer_token" if hf_inference.api_key else "none",
            "apiKeyConfigured": bool(hf_inference.api_key),
            "defaultModel": hf_inference.model,
            "defaultContextWindow": hf_inference.default_context_window,
            "defaultPromptProfile": get_ollama_settings().default_prompt_profile,
            "defaultTopP": hf_inference.default_top_p,
            "defaultMaxTokens": hf_inference.default_max_tokens,
            "defaultTemperature": 0.2,
            "availableModelsEnv": list(hf_inference.available_models_env),
            "availableEmbeddingModelsEnv": list(hf_inference.available_embedding_models_env),
        },
    }
    settings["ollama_hosted"] = {
        "providerFamily": "ollama",
        "mode": "hosted",
        "baseUrl": ollama_hosted.base_url if ollama_hosted is not None else "",
        "authMethod": "api_key",
        "apiKeyConfigured": bool(ollama_hosted.api_key) if ollama_hosted is not None else False,
        "defaultModel": (ollama_hosted.default_model if ollama_hosted is not None else ollama.default_model),
        "defaultContextWindow": (ollama_hosted.default_context_window if ollama_hosted is not None else ollama.default_context_window),
        "defaultPromptProfile": (ollama_hosted.default_prompt_profile if ollama_hosted is not None else ollama.default_prompt_profile),
        "defaultTopP": (ollama_hosted.default_top_p if ollama_hosted is not None else ollama.default_top_p),
        "defaultMaxTokens": (ollama_hosted.default_max_tokens if ollama_hosted is not None else ollama.default_max_tokens),
        "defaultTemperature": (ollama_hosted.default_temperature if ollama_hosted is not None else ollama.default_temperature),
        "availableModelsEnv": list(ollama_hosted.available_models_env) if ollama_hosted is not None else [],
        "availableEmbeddingModelsEnv": list(ollama_hosted.available_embedding_models_env) if ollama_hosted is not None else [],
    }
    return settings


def _connection_capabilities(provider_key: str, provider_entry: dict[str, Any]) -> dict[str, bool]:
    if not provider_entry:
        return {
            "generation": False,
            "embeddings": False,
            "reranking": False,
            "structuredOutputs": False,
            "vision": False,
            "toolCalling": False,
            "streaming": False,
        }

    supports_chat = bool(provider_entry.get("supports_chat"))
    supports_embeddings = bool(provider_entry.get("supports_embeddings"))
    return {
        "generation": supports_chat,
        "embeddings": supports_embeddings,
        "reranking": False,
        "structuredOutputs": supports_chat and provider_key in {"ollama", "ollama_hosted", "openai", "huggingface_server"},
        "vision": supports_chat and provider_key == "openai",
        "toolCalling": supports_chat and provider_key == "openai",
        "streaming": supports_chat,
    }


def _infer_connection_status(provider_entry: dict[str, Any], static_settings: dict[str, Any]) -> str:
    if not provider_entry:
        return "not_configured"
    if not bool(provider_entry.get("supports_chat")) and not bool(provider_entry.get("supports_embeddings")):
        return "not_configured"
    if static_settings.get("authMethod") != "none" and not static_settings.get("apiKeyConfigured"):
        return "not_configured"
    return "connected"


def _list_models(provider_entry: dict[str, Any], *, embedding: bool = False) -> list[str]:
    instance = provider_entry.get("instance")
    if instance is None:
        return []
    try:
        if embedding and hasattr(instance, "list_available_embedding_models"):
            models = list(instance.list_available_embedding_models())
        elif hasattr(instance, "list_available_models"):
            models = list(instance.list_available_models())
        else:
            models = []
    except Exception:
        models = []
    ordered: list[str] = []
    for model in models:
        normalized = str(model or "").strip()
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return _filter_product_models(ordered)


def _build_connections(registry: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]], dict[str, list[str]], dict[str, dict[str, Any]]]:
    static_settings = _provider_static_settings()
    connections: list[dict[str, Any]] = []
    models_by_connection: dict[str, list[str]] = {}
    embedding_models_by_connection: dict[str, list[str]] = {}
    provider_settings: dict[str, dict[str, Any]] = {}
    label_lookup = {
        "ollama": "Ollama (local)",
        "ollama_hosted": "Ollama Hosted",
        "openai": "OpenAI",
        "huggingface_server": "Hugging Face server local",
        "huggingface_inference": "Hugging Face Inference",
    }
    for provider_key in dict.fromkeys([*static_settings.keys(), *registry.keys()]):
        if provider_key in PRODUCT_CONNECTION_BLACKLIST:
            continue
        provider_entry = registry.get(provider_key) if isinstance(registry.get(provider_key), dict) else {}
        static_config = static_settings.get(provider_key, {})
        provider_settings[provider_key] = static_config
        models_by_connection[provider_key] = _list_models(provider_entry, embedding=False) or _filter_product_models(list(static_config.get("availableModelsEnv") or []))
        embedding_models_by_connection[provider_key] = _list_models(provider_entry, embedding=True) or _filter_product_models(list(static_config.get("availableEmbeddingModelsEnv") or []))
        preferred_model = str(provider_entry.get("default_model") or static_config.get("defaultModel") or "")
        if _is_blocked_product_model(preferred_model):
            preferred_model = models_by_connection.get(provider_key, [""])[0] if models_by_connection.get(provider_key) else ""
        connections.append(
            {
                "id": provider_key,
                "name": str(provider_entry.get("label") or label_lookup.get(provider_key) or provider_key),
                "providerFamily": static_config.get("providerFamily") or "ollama",
                "mode": static_config.get("mode") or "local",
                "baseUrl": static_config.get("baseUrl") or str(provider_entry.get("detail") or ""),
                "authMethod": static_config.get("authMethod") or "none",
                "apiKeyConfigured": bool(static_config.get("apiKeyConfigured")),
                "status": _infer_connection_status(provider_entry, static_config),
                "preferredModel": preferred_model,
                "lastChecked": _utc_now_iso(),
                "description": str(provider_entry.get("detail") or static_config.get("description") or "Runtime connection surfaced by workspace preferences."),
                "capabilities": _connection_capabilities(provider_key, provider_entry),
                "role": "production" if provider_key == "ollama" else "burst_overflow" if provider_key == "ollama_hosted" else "benchmark_reference",
            }
        )
    return connections, models_by_connection, embedding_models_by_connection, provider_settings


def _default_provider_key(registry: dict[str, dict[str, Any]]) -> str:
    if "ollama" in registry:
        return "ollama"
    for key, entry in registry.items():
        if key in PRODUCT_CONNECTION_BLACKLIST:
            continue
        if isinstance(entry, dict) and bool(entry.get("supports_chat")):
            return key
    allowed_keys = [key for key in registry.keys() if key not in PRODUCT_CONNECTION_BLACKLIST]
    return next(iter(allowed_keys), "ollama")


def _default_embedding_provider_key(registry: dict[str, dict[str, Any]], rag_settings: RagSettings) -> str:
    requested = str(rag_settings.embedding_provider or "").strip().lower()
    if requested in registry and requested not in PRODUCT_CONNECTION_BLACKLIST:
        return requested
    if "ollama" in registry:
        return "ollama"
    for key, entry in registry.items():
        if key in PRODUCT_CONNECTION_BLACKLIST:
            continue
        if isinstance(entry, dict) and bool(entry.get("supports_embeddings")):
            return key
    return _default_provider_key(registry)


def _load_runtime_seed_from_preferences(workspace_root: Path | None = None) -> dict[str, Any] | None:
    raw_state = load_preferences_state(_preferences_state_path(workspace_root)) or {}
    active_profile_id = str(raw_state.get("active_profile_id") or "").strip()
    profiles = raw_state.get("runtime_profiles") if isinstance(raw_state.get("runtime_profiles"), list) else []
    if active_profile_id:
        for item in profiles:
            if isinstance(item, dict) and str(item.get("id") or "") == active_profile_id:
                return item
    for item in profiles:
        if isinstance(item, dict):
            return item
    return None


def _sync_runtime_controls_to_preferences_state(workspace_root: Path | None, normalized_profile: dict[str, Any]) -> None:
    path = _preferences_state_path(workspace_root)
    raw_state = load_preferences_state(path) or {}
    profiles = raw_state.get("runtime_profiles") if isinstance(raw_state.get("runtime_profiles"), list) else []
    active_profile_id = str(raw_state.get("active_profile_id") or "").strip()
    if not active_profile_id or not profiles:
        return

    mirrored_fields = {
        "primaryConnectionId",
        "primaryModel",
        "fallbackChain",
        "executionPolicy",
        "retrievalStrategy",
        "embeddingConnectionId",
        "embeddingModel",
        "rerankingEnabled",
        "docProcessingPreset",
        "qualityPosture",
        "summary",
        "generation",
        "retrieval",
        "docProcessing",
    }
    updated_profiles: list[dict[str, Any]] = []
    replaced = False
    for item in profiles:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "") != active_profile_id:
            updated_profiles.append(item)
            continue
        next_item = dict(item)
        for field in mirrored_fields:
            if field in normalized_profile:
                next_item[field] = normalized_profile[field]
        updated_profiles.append(next_item)
        replaced = True

    if not replaced:
        next_item = {**normalized_profile, "id": active_profile_id, "isActive": True}
        updated_profiles.append(next_item)

    raw_state["runtime_profiles"] = updated_profiles
    raw_state["updated_at"] = _utc_now_iso()
    save_preferences_state(path, raw_state)


def _derive_execution_policy(primary_connection: dict[str, Any], fallback_chain: list[dict[str, str]]) -> str:
    mode = str(primary_connection.get("mode") or "local")
    if mode == "local":
        return "prefer_local_burst_hosted" if fallback_chain else "local_only"
    if mode == "hosted":
        return "hosted_deep_review" if fallback_chain else "hosted_only"
    return "cloud_selected_workflows"


def _derive_quality_posture(top_k: int, max_tokens: int) -> str:
    if max_tokens >= 4096 and top_k >= 12:
        return "max_quality"
    if max_tokens <= 1536 and top_k <= 8:
        return "low_latency"
    return "balanced"


def _derive_doc_preset(doc_processing: dict[str, Any]) -> str:
    if bool(doc_processing.get("vlmEnhancement")):
        return "vlm_enhanced"
    if bool(doc_processing.get("ocrFailoverEnabled")) and str(doc_processing.get("pdfExtractionMode") or "") in {"complete", "docling"}:
        return "ocr_heavy"
    if str(doc_processing.get("pdfExtractionMode") or "") == "basic" and not bool(doc_processing.get("ocrFailoverEnabled")):
        return "fast_text"
    return "standard"


def _workflow_fit(profile: dict[str, Any], primary_connection: dict[str, Any]) -> list[dict[str, Any]]:
    capabilities = primary_connection.get("capabilities") if isinstance(primary_connection.get("capabilities"), dict) else {}
    fits: list[dict[str, Any]] = []
    retrieval_strategy = str(profile.get("retrievalStrategy") or "hybrid")
    quality_posture = str(profile.get("qualityPosture") or "balanced")
    for workflow in WORKFLOW_CATALOG:
        workflow_id = str(workflow["workflowId"])
        compatibility = "compatible"
        reason = None
        if workflow_id == "workflow-inspector":
            compatibility = "recommended" if bool(capabilities.get("structuredOutputs")) else "restricted"
            if compatibility == "restricted":
                reason = "Structured outputs are limited on the active provider." 
        elif workflow_id in {"document-review", "comparison"} and quality_posture == "max_quality":
            compatibility = "recommended"
            reason = "Current runtime is tuned for grounded review workloads."
        elif workflow_id == "candidate-review" and quality_posture == "low_latency":
            compatibility = "recommended"
            reason = "Lower-latency settings fit screening-style review well."
        elif workflow_id == "action-plan" and retrieval_strategy != "hybrid":
            compatibility = "restricted"
            reason = "Hybrid retrieval is usually safer for richer planning context."
        fits.append(
            {
                "workflowId": workflow_id,
                "label": workflow["label"],
                "compatibility": compatibility,
                **({"reason": reason} if reason else {}),
            }
        )
    return fits


def _derive_fallback_chain(connections: list[dict[str, Any]], primary_connection_id: str, models_by_connection: dict[str, list[str]]) -> list[dict[str, str]]:
    fallbacks: list[dict[str, str]] = []
    for connection in connections:
        connection_id = str(connection.get("id") or "")
        if connection_id == primary_connection_id:
            continue
        capabilities = connection.get("capabilities") if isinstance(connection.get("capabilities"), dict) else {}
        if not bool(capabilities.get("generation")):
            continue
        if str(connection.get("status") or "") != "connected":
            continue
        model_choices = models_by_connection.get(connection_id) or []
        model_name = model_choices[0] if model_choices else str(connection.get("preferredModel") or "")
        if not model_name:
            continue
        fallbacks.append(
            {
                "connectionId": connection_id,
                "model": model_name,
                "label": f"Fallback to {connection.get('name')}",
            }
        )
        if len(fallbacks) >= 2:
            break
    return fallbacks


def _normalize_profile(
    *,
    registry: dict[str, dict[str, Any]],
    rag_settings: RagSettings,
    overrides: dict[str, Any] | None,
    connections: list[dict[str, Any]],
    models_by_connection: dict[str, list[str]],
    embedding_models_by_connection: dict[str, list[str]],
    provider_settings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    patch = dict(overrides or {})
    connections_by_id = {str(item.get("id")): item for item in connections}

    primary_connection_id = str(patch.get("primaryConnectionId") or _default_provider_key(registry))
    if primary_connection_id not in connections_by_id:
        primary_connection_id = _default_provider_key(registry)
    embedding_connection_id = str(patch.get("embeddingConnectionId") or _default_embedding_provider_key(registry, rag_settings))
    if embedding_connection_id not in connections_by_id:
        embedding_connection_id = _default_embedding_provider_key(registry, rag_settings)

    primary_connection = connections_by_id.get(primary_connection_id, {})
    primary_static = provider_settings.get(primary_connection_id, {})
    primary_models = models_by_connection.get(primary_connection_id) or []
    embedding_models = embedding_models_by_connection.get(embedding_connection_id) or []

    generation_patch = patch.get("generation") if isinstance(patch.get("generation"), dict) else {}
    retrieval_patch = patch.get("retrieval") if isinstance(patch.get("retrieval"), dict) else {}
    doc_patch = patch.get("docProcessing") if isinstance(patch.get("docProcessing"), dict) else {}

    generation = {
        "temperature": _clamp_float(generation_patch.get("temperature"), float(primary_static.get("defaultTemperature") or 0.2), minimum=0.0, maximum=1.5),
        "contextWindow": _normalize_context_window_label(generation_patch.get("contextWindow"), primary_static.get("defaultContextWindow")),
        "promptProfile": _normalize_prompt_profile(generation_patch.get("promptProfile") or primary_static.get("defaultPromptProfile")),
        "streaming": bool(generation_patch.get("streaming", True)),
        "maxOutputTokens": _clamp_int(generation_patch.get("maxOutputTokens"), int(primary_static.get("defaultMaxTokens") or 4096), minimum=256, maximum=262144),
        "topP": _clamp_float(generation_patch.get("topP"), float(primary_static.get("defaultTopP") or 0.95), minimum=0.0, maximum=1.0),
        "structuredOutput": bool(generation_patch.get("structuredOutput", False)),
    }

    retrieval = {
        "topK": _clamp_int(retrieval_patch.get("topK"), rag_settings.top_k, minimum=1, maximum=200),
        "chunkSize": _clamp_int(retrieval_patch.get("chunkSize"), rag_settings.chunk_size, minimum=128, maximum=8192),
        "chunkOverlap": _clamp_int(retrieval_patch.get("chunkOverlap"), rag_settings.chunk_overlap, minimum=0, maximum=2048),
        "rerankPoolSize": _clamp_int(retrieval_patch.get("rerankPoolSize"), rag_settings.rerank_pool_size, minimum=0, maximum=400),
        "rerankLexicalWeight": _clamp_float(retrieval_patch.get("rerankLexicalWeight"), rag_settings.rerank_lexical_weight, minimum=0.0, maximum=1.0),
        "groundingStrictness": str(retrieval_patch.get("groundingStrictness") or "balanced").strip().lower() or "balanced",
    }

    doc_processing = {
        "pdfExtractionMode": str(doc_patch.get("pdfExtractionMode") or rag_settings.pdf_extraction_mode or "hybrid").strip().lower(),
        "ocrBackend": str(doc_patch.get("ocrBackend") or rag_settings.evidence_ocr_backend or "ocrmypdf").strip().lower(),
        "vlmEnhancement": bool(doc_patch.get("vlmEnhancement", rag_settings.pdf_evidence_pipeline_enabled)),
        "tableExtractionMode": str(doc_patch.get("tableExtractionMode") or "auto").strip().lower() or "auto",
        "ocrFailoverEnabled": bool(doc_patch.get("ocrFailoverEnabled", rag_settings.pdf_ocr_fallback_enabled)),
        "scannedDocumentThreshold": _clamp_float(doc_patch.get("scannedDocumentThreshold"), rag_settings.pdf_scan_image_ocr_min_suspicious_ratio, minimum=0.1, maximum=1.0),
    }

    reranking_enabled = bool(patch.get("rerankingEnabled", retrieval["rerankPoolSize"] > 0))
    if not reranking_enabled:
        retrieval["rerankPoolSize"] = 0

    primary_model = str(patch.get("primaryModel") or (primary_models[0] if primary_models else primary_static.get("defaultModel") or "")).strip()
    embedding_model = str(patch.get("embeddingModel") or (embedding_models[0] if embedding_models else rag_settings.embedding_model)).strip()
    fallback_chain = _derive_fallback_chain(connections, primary_connection_id, models_by_connection)
    quality_posture = str(patch.get("qualityPosture") or _derive_quality_posture(int(retrieval["topK"]), int(generation["maxOutputTokens"])))

    profile = {
        "id": "runtime-controls-live",
        "name": str(patch.get("name") or "Current Product Runtime"),
        "primaryConnectionId": primary_connection_id,
        "primaryModel": primary_model,
        "fallbackChain": fallback_chain,
        "executionPolicy": str(patch.get("executionPolicy") or _derive_execution_policy(primary_connection, fallback_chain)),
        "retrievalStrategy": "hybrid",
        "embeddingConnectionId": embedding_connection_id,
        "embeddingModel": embedding_model,
        "rerankingEnabled": reranking_enabled,
        "docProcessingPreset": str(patch.get("docProcessingPreset") or _derive_doc_preset(doc_processing)),
        "qualityPosture": quality_posture,
        "intendedWorkflows": [item["workflowId"] for item in WORKFLOW_CATALOG],
        "isActive": True,
        "isDefault": True,
        "summary": "",
        "generation": generation,
        "retrieval": retrieval,
        "docProcessing": doc_processing,
        "workflowFit": [],
    }
    profile["workflowFit"] = _workflow_fit(profile, primary_connection)
    primary_name = str(primary_connection.get("name") or primary_connection_id)
    embedding_name = str(connections_by_id.get(embedding_connection_id, {}).get("name") or embedding_connection_id)
    profile["summary"] = (
        f"Primary runtime uses {primary_name} with model {primary_model}, hybrid retrieval, "
        f"embedding via {embedding_name} ({embedding_model}) and document preset {_catalog_label(DOC_PRESETS, profile['docProcessingPreset'])}."
    )
    return profile


def build_runtime_controls_payload(bootstrap: ProductBootstrap) -> dict[str, Any]:
    state = load_runtime_controls_state(_state_path(bootstrap.workspace_root)) or {}
    registry = build_provider_registry()
    connections, models_by_connection, embedding_models_by_connection, provider_settings = _build_connections(registry)
    active_profile = _normalize_profile(
        registry=registry,
        rag_settings=build_effective_rag_settings(default_settings=bootstrap.rag_settings, workspace_root=bootstrap.workspace_root),
        overrides=(state.get("profile") if isinstance(state.get("profile"), dict) else _load_runtime_seed_from_preferences(bootstrap.workspace_root) or {}),
        connections=connections,
        models_by_connection=models_by_connection,
        embedding_models_by_connection=embedding_models_by_connection,
        provider_settings=provider_settings,
    )
    prompt_profiles = get_prompt_profiles()
    return {
        "ok": True,
        "contract_version": RUNTIME_CONTROLS_CONTRACT_VERSION,
        "data_source": "live",
        "updated_at": state.get("updated_at"),
        "active_profile": active_profile,
        "available_connections": connections,
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
    }


def update_runtime_controls_payload(bootstrap: ProductBootstrap, patch_payload: dict[str, Any]) -> dict[str, Any]:
    state_path = _state_path(bootstrap.workspace_root)
    current_state = load_runtime_controls_state(state_path) or {}
    merged_state = merge_runtime_controls_state(current_state, patch_payload)
    registry = build_provider_registry()
    connections, models_by_connection, embedding_models_by_connection, provider_settings = _build_connections(registry)
    normalized_profile = _normalize_profile(
        registry=registry,
        rag_settings=build_effective_rag_settings(default_settings=bootstrap.rag_settings, workspace_root=bootstrap.workspace_root),
        overrides=merged_state.get("profile") if isinstance(merged_state.get("profile"), dict) else {},
        connections=connections,
        models_by_connection=models_by_connection,
        embedding_models_by_connection=embedding_models_by_connection,
        provider_settings=provider_settings,
    )
    save_runtime_controls_state(
        state_path,
        {
            "contract_version": RUNTIME_CONTROLS_STATE_VERSION,
            "updated_at": _utc_now_iso(),
            "profile": normalized_profile,
        },
    )
    _sync_runtime_controls_to_preferences_state(bootstrap.workspace_root, normalized_profile)
    return build_runtime_controls_payload(bootstrap)


def build_effective_rag_settings(*, default_settings: RagSettings | None = None, workspace_root: Path | None = None) -> RagSettings:
    base = default_settings if isinstance(default_settings, RagSettings) else get_rag_settings()
    state = load_runtime_controls_state(_state_path(workspace_root)) or {}
    profile = state.get("profile") if isinstance(state.get("profile"), dict) else {}
    retrieval = profile.get("retrieval") if isinstance(profile.get("retrieval"), dict) else {}
    doc_processing = profile.get("docProcessing") if isinstance(profile.get("docProcessing"), dict) else {}
    return replace(
        base,
        embedding_provider=str(profile.get("embeddingConnectionId") or base.embedding_provider),
        embedding_model=str(profile.get("embeddingModel") or base.embedding_model),
        top_k=_clamp_int(retrieval.get("topK"), base.top_k, minimum=1, maximum=200),
        chunk_size=_clamp_int(retrieval.get("chunkSize"), base.chunk_size, minimum=128, maximum=8192),
        chunk_overlap=_clamp_int(retrieval.get("chunkOverlap"), base.chunk_overlap, minimum=0, maximum=2048),
        rerank_pool_size=_clamp_int(retrieval.get("rerankPoolSize"), base.rerank_pool_size, minimum=0, maximum=400),
        rerank_lexical_weight=_clamp_float(retrieval.get("rerankLexicalWeight"), base.rerank_lexical_weight, minimum=0.0, maximum=1.0),
        pdf_extraction_mode=str(doc_processing.get("pdfExtractionMode") or base.pdf_extraction_mode),
        evidence_ocr_backend=str(doc_processing.get("ocrBackend") or base.evidence_ocr_backend),
        pdf_ocr_fallback_enabled=bool(doc_processing.get("ocrFailoverEnabled", base.pdf_ocr_fallback_enabled)),
        pdf_scan_image_ocr_min_suspicious_ratio=_clamp_float(doc_processing.get("scannedDocumentThreshold"), base.pdf_scan_image_ocr_min_suspicious_ratio, minimum=0.1, maximum=1.0),
        pdf_evidence_pipeline_enabled=bool(doc_processing.get("vlmEnhancement", base.pdf_evidence_pipeline_enabled)),
        pdf_docling_picture_description=bool(doc_processing.get("vlmEnhancement", base.pdf_docling_picture_description)),
    )


def apply_runtime_controls_to_product_request(
    request: ProductWorkflowRequest,
    bootstrap: ProductBootstrap,
    explicit_fields: set[str] | None = None,
) -> ProductWorkflowRequest:
    payload = build_runtime_controls_payload(bootstrap)
    profile = payload.get("active_profile") if isinstance(payload.get("active_profile"), dict) else {}
    generation = profile.get("generation") if isinstance(profile.get("generation"), dict) else {}
    explicit = {str(item) for item in (explicit_fields or set())}

    resolved_context_mode = request.context_window_mode
    resolved_context_window = request.context_window
    if "context_window_mode" not in explicit and "context_window" not in explicit:
        configured_label = str(generation.get("contextWindow") or "auto")
        configured_context_window = _context_window_from_label(configured_label)
        if configured_context_window is not None:
            resolved_context_mode = "manual"
            resolved_context_window = configured_context_window
        else:
            resolved_context_mode = "auto"
            resolved_context_window = None

    resolved_temperature = request.temperature if "temperature" in explicit else float(generation.get("temperature", request.temperature))
    resolved_top_p = request.top_p if "top_p" in explicit else float(generation.get("topP", request.top_p if request.top_p is not None else 0.95))
    resolved_max_tokens = request.max_tokens if "max_tokens" in explicit else int(generation.get("maxOutputTokens", request.max_tokens if request.max_tokens is not None else 4096))
    resolved_prompt_profile = request.prompt_profile if "prompt_profile" in explicit else str(generation.get("promptProfile") or request.prompt_profile or "neutro")

    return request.model_copy(
        update={
            "provider": request.provider if "provider" in explicit else str(profile.get("primaryConnectionId") or request.provider),
            "model": request.model if "model" in explicit and request.model else (request.model or str(profile.get("primaryModel") or "")),
            "temperature": resolved_temperature,
            "prompt_profile": resolved_prompt_profile,
            "top_p": resolved_top_p,
            "max_tokens": resolved_max_tokens,
            "context_window_mode": resolved_context_mode,
            "context_window": resolved_context_window,
        }
    )