from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import (
    GradioProductSettings,
    OllamaSettings,
    PresentationExportSettings,
    RagSettings,
    get_gradio_product_settings,
    get_ollama_settings,
    get_presentation_export_settings,
    get_rag_settings,
)
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.product.service import build_product_workflow_catalog, build_product_workflow_frontend_contract
from src.prompt_profiles import get_prompt_profiles
from src.providers.registry import build_provider_registry
from src.structured.registry import build_structured_task_registry


@dataclass(frozen=True)
class ProductBootstrap:
    workspace_root: Path
    product_settings: GradioProductSettings
    settings: OllamaSettings
    rag_settings: RagSettings
    evidence_config: Any
    provider_registry: dict[str, dict[str, object]]
    prompt_profiles: dict[str, dict[str, str]]
    structured_task_registry: Any
    presentation_export_settings: PresentationExportSettings
    workflow_catalog: dict[str, object]
    workflow_frontend_contract: dict[str, Any]


def build_product_bootstrap() -> ProductBootstrap:
    settings = get_ollama_settings()
    rag_settings = get_rag_settings()
    return ProductBootstrap(
        workspace_root=Path(__file__).resolve().parents[2],
        product_settings=get_gradio_product_settings(),
        settings=settings,
        rag_settings=rag_settings,
        evidence_config=build_evidence_config_from_rag_settings(rag_settings),
        provider_registry=build_provider_registry(),
        prompt_profiles=get_prompt_profiles(),
        structured_task_registry=build_structured_task_registry(),
        presentation_export_settings=get_presentation_export_settings(),
        workflow_catalog=build_product_workflow_catalog(),
        workflow_frontend_contract=build_product_workflow_frontend_contract(),
    )