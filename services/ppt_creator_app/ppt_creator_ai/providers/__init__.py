from __future__ import annotations

from ppt_creator_ai.providers.base import (
    BriefingGenerationResult,
    BriefingProvider,
    DeckCritiqueResult,
)
from ppt_creator_ai.providers.heuristic import HeuristicBriefingProvider
from ppt_creator_ai.providers.local_service import LocalServiceBriefingProvider
from ppt_creator_ai.providers.ollama_local import OllamaLocalBriefingProvider

PROVIDERS: dict[str, BriefingProvider] = {
    HeuristicBriefingProvider.name: HeuristicBriefingProvider(),
    LocalServiceBriefingProvider.name: LocalServiceBriefingProvider(),
    OllamaLocalBriefingProvider.name: OllamaLocalBriefingProvider(),
}


def list_provider_names() -> list[str]:
    return sorted(PROVIDERS)


def get_provider(name: str) -> BriefingProvider:
    normalized = name.strip().lower().replace("-", "_")
    if normalized in {"service", "local", "hf_local_llm_service"}:
        normalized = LocalServiceBriefingProvider.name
    if normalized in {"ollama", "ollama_direct", "ollama_local"}:
        normalized = OllamaLocalBriefingProvider.name
    if normalized not in PROVIDERS:
        raise ValueError(f"Unknown briefing provider: {name}")
    return PROVIDERS[normalized]


def build_provider(name: str, **runtime_overrides: str | None) -> BriefingProvider:
    provider = get_provider(name)
    has_meaningful_override = any(value not in {None, ""} for value in runtime_overrides.values())
    if not has_meaningful_override:
        return provider
    clone_method = getattr(provider, "with_runtime_overrides", None)
    if callable(clone_method):
        return clone_method(**runtime_overrides)
    return provider


__all__ = [
    "BriefingGenerationResult",
    "BriefingProvider",
    "DeckCritiqueResult",
    "HeuristicBriefingProvider",
    "LocalServiceBriefingProvider",
    "OllamaLocalBriefingProvider",
    "PROVIDERS",
    "build_provider",
    "get_provider",
    "list_provider_names",
]
