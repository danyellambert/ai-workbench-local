from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvidencePipelineConfig:
    ollama_base_url: str = "http://localhost:11434"
    vl_model: str = "sorc/qwen3.5-instruct:2b"
    ocr_backend: str = "ocrmypdf"
    enable_docling: bool = True
    enable_secondary_verification: bool = True
    enable_vl: bool = True
    vl_use_for_scan_like_only: bool = True
    vl_scan_like_min_pages: int = 1
    vl_max_regions_per_page: int = 3
    vl_render_dpi: int = 200
    debug_dir: Path | None = None
    max_pages: int | None = None
    image_dpi: int = 300
    min_confirmed_confidence: float = 0.75
    min_visual_candidate_confidence: float = 0.55
    product_consume_visual_candidates: bool = False
    product_consume_needs_review: bool = False
    vl_router_enabled: bool = True
    vl_router_low_text_threshold: int = 120
    vl_router_min_contact_count: int = 1
    vl_router_force_regions_for_scan_like: int = 4
    vl_router_default_regions_for_partial_docs: int = 2


def build_evidence_config_from_rag_settings(rag_settings) -> EvidencePipelineConfig:
    return EvidencePipelineConfig(
        ollama_base_url="http://localhost:11434",
        ocr_backend="ocrmypdf",
        image_dpi=getattr(rag_settings, "pdf_scan_image_ocr_oversample_dpi", 300),
    )