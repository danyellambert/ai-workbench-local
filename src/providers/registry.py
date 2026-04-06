import os
from dataclasses import replace

from src.config import (
    get_huggingface_inference_settings,
    get_huggingface_server_settings,
    get_huggingface_settings,
    get_ollama_settings,
    get_openai_settings,
)
from src.providers.ollama_provider import OllamaProvider

try:
    from src.providers.openai_provider import OpenAIProvider
except Exception:  # optional dependency
    OpenAIProvider = None

try:
    from src.providers.huggingface_local_provider import HuggingFaceLocalProvider
except Exception:  # optional dependency
    HuggingFaceLocalProvider = None

try:
    from src.providers.huggingface_server_provider import HuggingFaceServerProvider
except Exception:  # optional dependency
    HuggingFaceServerProvider = None

try:
    from src.providers.huggingface_inference_provider import HuggingFaceInferenceProvider
except Exception:  # optional dependency
    HuggingFaceInferenceProvider = None


def capability_to_registry_flag(capability: str) -> str:
    return {
        "chat": "supports_chat",
        "embeddings": "supports_embeddings",
    }.get(capability, capability)


def filter_registry_by_capability(
    registry: dict[str, dict[str, object]],
    capability: str,
) -> dict[str, dict[str, object]]:
    capability_key = capability_to_registry_flag(capability)
    return {
        provider_key: provider_data
        for provider_key, provider_data in registry.items()
        if isinstance(provider_data, dict) and bool(provider_data.get(capability_key))
    }


def describe_embedding_provider_unavailable_reason(
    provider_key: str,
    provider_data: dict[str, object] | None = None,
) -> str:
    if provider_key == "huggingface_server":
        return "o serviço atual não publicou aliases com suporte a embeddings (`supports_embeddings=true`) no catálogo `/v1/models`."
    if provider_key == "huggingface_inference":
        return "configure `HUGGINGFACE_INFERENCE_EMBEDDING_MODEL` para habilitar embeddings nesse runtime remoto."
    if provider_key == "huggingface_local":
        return "o runtime local de embeddings do ecossistema Hugging Face não está disponível ou não foi configurado neste ambiente."
    if provider_key == "openai":
        return "o provider OpenAI não está disponível no ambiente atual ou não foi configurado com chave/modelo adequados."
    return "este provider não expõe embeddings na configuração atual."


def build_embedding_provider_sidebar_state(
    registry: dict[str, dict[str, object]],
) -> dict[str, object]:
    available_registry = filter_registry_by_capability(registry, "embeddings")
    available_options = {
        provider_key: str(provider_data.get("label") or provider_key)
        for provider_key, provider_data in available_registry.items()
    }
    available_models_by_provider = {
        provider_key: (
            provider_data["instance"].list_available_embedding_models()
            if hasattr(provider_data["instance"], "list_available_embedding_models")
            else provider_data["instance"].list_available_models()
        )
        for provider_key, provider_data in available_registry.items()
    }
    unavailable_items: list[dict[str, str]] = []
    for provider_key, provider_data in registry.items():
        if provider_key in available_registry or not isinstance(provider_data, dict):
            continue
        unavailable_items.append(
            {
                "provider_key": provider_key,
                "label": str(provider_data.get("label") or provider_key),
                "reason": describe_embedding_provider_unavailable_reason(provider_key, provider_data),
            }
        )
    unavailable_items.sort(key=lambda item: item["label"].lower())
    return {
        "available_registry": available_registry,
        "available_options": available_options,
        "available_models_by_provider": available_models_by_provider,
        "unavailable_items": unavailable_items,
    }


def build_provider_registry() -> dict[str, dict[str, object]]:
    ollama_settings = get_ollama_settings()
    registry: dict[str, dict[str, object]] = {
        "ollama": {
            "label": "Ollama (local)",
            "detail": f"Base URL: `{ollama_settings.base_url}`",
            "instance": OllamaProvider(ollama_settings),
            "supports_chat": True,
            "supports_embeddings": True,
            "default_model": ollama_settings.default_model,
            "default_context_window": ollama_settings.default_context_window,
        }
    }

    openai_settings = get_openai_settings()
    if openai_settings.api_key and OpenAIProvider is not None:
        registry["openai"] = {
            "label": "OpenAI",
            "detail": "Provider cloud opcional configurado por variável de ambiente",
            "instance": OpenAIProvider(openai_settings),
            "supports_chat": True,
            "supports_embeddings": True,
            "default_model": openai_settings.model,
            "default_context_window": openai_settings.default_context_window,
        }

    huggingface_settings = get_huggingface_settings()
    if huggingface_settings.model and HuggingFaceLocalProvider is not None:
        registry["huggingface_local"] = {
            "label": "Hugging Face local (experimental)",
            "detail": (
                "Runtime local experimental via Transformers"
                if HuggingFaceLocalProvider.supports_generation_runtime()
                else "Runtime local experimental configurado, mas `transformers` não está instalado"
            ),
            "instance": HuggingFaceLocalProvider(huggingface_settings),
            "supports_chat": HuggingFaceLocalProvider.supports_generation_runtime(),
            "supports_embeddings": HuggingFaceLocalProvider.supports_embedding_runtime(),
            "default_model": huggingface_settings.model,
            "default_context_window": huggingface_settings.default_context_window,
        }

    huggingface_server_settings = get_huggingface_server_settings()
    if HuggingFaceServerProvider is not None:
        candidate_settings = []
        if huggingface_server_settings.base_url:
            candidate_settings.append((huggingface_server_settings, False))
        else:
            for candidate_base_url in [
                str(os.getenv("HF_LOCAL_LLM_SERVICE_BASE_URL") or "").strip(),
                "http://127.0.0.1:8788/v1",
            ]:
                if not candidate_base_url:
                    continue
                candidate_settings.append((replace(huggingface_server_settings, base_url=candidate_base_url), True))

        for candidate_setting, autodiscovered in candidate_settings:
            huggingface_server_provider = HuggingFaceServerProvider(candidate_setting)
            available_server_models = huggingface_server_provider.list_available_models()
            if not available_server_models:
                continue
            available_server_embedding_models = huggingface_server_provider.list_available_embedding_models()
            default_server_model = candidate_setting.model or available_server_models[0]
            detail_prefix = "Servidor local auto-descoberto em" if autodiscovered else "Servidor local configurado em"
            registry["huggingface_server"] = {
                "label": "Hugging Face server local",
                "detail": f"{detail_prefix} `{candidate_setting.base_url}`",
                "instance": huggingface_server_provider,
                "supports_chat": True,
                "supports_embeddings": bool(available_server_embedding_models),
                "default_model": default_server_model,
                "default_context_window": candidate_setting.default_context_window,
            }
            break

    huggingface_inference_settings = get_huggingface_inference_settings()
    if (
        huggingface_inference_settings.api_key
        and huggingface_inference_settings.base_url
        and huggingface_inference_settings.model
        and HuggingFaceInferenceProvider is not None
    ):
        registry["huggingface_inference"] = {
            "label": "Hugging Face Inference",
            "detail": f"Endpoint remoto configurado em `{huggingface_inference_settings.base_url}`",
            "instance": HuggingFaceInferenceProvider(huggingface_inference_settings),
            "supports_chat": True,
            "supports_embeddings": bool(huggingface_inference_settings.embedding_model),
            "default_model": huggingface_inference_settings.model,
            "default_context_window": huggingface_inference_settings.default_context_window,
        }

    return registry


def resolve_provider_entry(
    registry: dict[str, dict[str, object]],
    provider_name: str | None,
    *,
    capability: str,
    fallback_provider: str | None = None,
) -> tuple[str | None, dict[str, object] | None, str | None]:
    requested = (provider_name or "").strip().lower()
    capability_key = capability_to_registry_flag(capability)

    if requested:
        candidate = registry.get(requested)
        if isinstance(candidate, dict) and bool(candidate.get(capability_key)):
            return requested, candidate, None

    fallback_key = fallback_provider if fallback_provider in registry else None
    if fallback_key and bool(registry[fallback_key].get(capability_key)):
        return fallback_key, registry[fallback_key], (f"{capability}_provider_unavailable:{requested}" if requested and requested != fallback_key else None)

    for key, candidate in registry.items():
        if isinstance(candidate, dict) and bool(candidate.get(capability_key)):
            return key, candidate, (f"{capability}_provider_unavailable:{requested}" if requested and requested != key else None)

    return None, None, f"no_provider_with_capability:{capability}"


def resolve_provider_runtime_profile(
    registry: dict[str, dict[str, object]],
    provider_name: str | None,
    *,
    capability: str,
    fallback_provider: str | None = None,
) -> dict[str, object]:
    requested_provider = (provider_name or fallback_provider or "").strip().lower()
    effective_provider, provider_entry, fallback_reason = resolve_provider_entry(
        registry,
        requested_provider,
        capability=capability,
        fallback_provider=fallback_provider,
    )
    normalized_entry = provider_entry if isinstance(provider_entry, dict) else {}
    return {
        "requested_provider": requested_provider,
        "effective_provider": effective_provider,
        "provider_entry": normalized_entry,
        "provider_instance": normalized_entry.get("instance"),
        "provider_label": normalized_entry.get("label"),
        "default_model": normalized_entry.get("default_model"),
        "default_context_window": normalized_entry.get("default_context_window"),
        "fallback_reason": fallback_reason,
        "supports_capability": bool(normalized_entry.get(capability_to_registry_flag(capability))),
    }
