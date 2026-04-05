from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.config import OllamaSettings, RagSettings, get_ollama_settings, get_rag_settings
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.prompt_profiles import build_prompt_messages, get_prompt_profiles
from src.providers.registry import build_embedding_provider_sidebar_state, build_provider_registry
from src.structured.registry import build_structured_task_registry


@dataclass(frozen=True)
class AppBootstrap:
    settings: OllamaSettings
    rag_settings: RagSettings
    evidence_config: Any
    provider_registry: dict[str, dict[str, object]]
    prompt_profiles: dict[str, dict[str, str]]
    structured_task_registry: Any
    embedding_sidebar_state: dict[str, object]


def build_app_bootstrap() -> AppBootstrap:
    """Wire the main app runtime in one place to simplify smoke validation."""
    settings = get_ollama_settings()
    rag_settings = get_rag_settings()
    evidence_config = build_evidence_config_from_rag_settings(rag_settings)
    provider_registry = build_provider_registry()
    prompt_profiles = get_prompt_profiles()
    structured_task_registry = build_structured_task_registry()
    embedding_sidebar_state = build_embedding_provider_sidebar_state(provider_registry)
    return AppBootstrap(
        settings=settings,
        rag_settings=rag_settings,
        evidence_config=evidence_config,
        provider_registry=provider_registry,
        prompt_profiles=prompt_profiles,
        structured_task_registry=structured_task_registry,
        embedding_sidebar_state=embedding_sidebar_state,
    )