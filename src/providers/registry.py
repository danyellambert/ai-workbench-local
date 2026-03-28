from src.config import get_huggingface_settings, get_ollama_settings, get_openai_settings
from src.providers.ollama_provider import OllamaProvider

try:
    from src.providers.openai_provider import OpenAIProvider
except Exception:  # optional dependency
    OpenAIProvider = None

try:
    from src.providers.huggingface_local_provider import HuggingFaceLocalProvider
except Exception:  # optional dependency
    HuggingFaceLocalProvider = None


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
