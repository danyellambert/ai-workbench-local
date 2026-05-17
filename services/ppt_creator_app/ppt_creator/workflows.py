from __future__ import annotations

from copy import deepcopy

from ppt_creator.assets import get_asset_collection
from ppt_creator.brand_packs import build_branding_bundle, get_brand_pack
from ppt_creator.profiles import get_audience_profile
from ppt_creator.templates import _build_slide_asset_suggestions, build_domain_template

WORKFLOW_PRESETS: dict[str, dict[str, object]] = {
    "sales_qbr": {
        "display_name": "Sales QBR",
        "domain": "sales",
        "audience_profile": "sales",
        "description": "Quarterly business review for commercial leadership with KPI, forecast, and execution framing.",
        "operating_mode": "commercial",
        "cadence": "quarterly",
        "stakeholders": ["CRO", "VP Sales", "Revenue Operations"],
        "recommended_asset_collections": ["sales_dashboards", "forecast_reviews"],
        "default_brand_pack": "sales_pipeline",
        "default_preview_backend": "office",
        "default_preview_require_real": True,
        "default_preview_fail_on_regression": False,
        "default_baseline_dir": "outputs/sales_qbr_baseline",
        "recommended_preview_source": "rendered_pptx",
        "preview_provenance_guidance": "Prefer preview-pptx/review-pptx artifacts for commercial deck sign-off and keep the preview manifest with the promoted baseline.",
        "default_output_pptx": "outputs/sales_qbr.pptx",
        "default_preview_dir": "outputs/sales_qbr_previews",
        "default_report_json": "outputs/sales_qbr_report.json",
        "suggested_steps": ["template", "review", "render", "preview-pptx", "review-pptx", "promote-baseline"],
        "recommended_regression_flow": ["render", "preview-pptx", "review-pptx", "promote-baseline"],
    },
    "board_strategy": {
        "display_name": "Board Strategy Review",
        "domain": "strategy",
        "audience_profile": "board",
        "description": "Board-facing strategy review focused on trade-offs, sequencing, and decision clarity.",
        "operating_mode": "board",
        "cadence": "quarterly",
        "stakeholders": ["Board", "CEO", "Strategy Office"],
        "recommended_asset_collections": ["boardroom_backdrops", "executive_decision_moments"],
        "default_brand_pack": "board_navy",
        "default_preview_backend": "office",
        "default_preview_require_real": True,
        "default_preview_fail_on_regression": False,
        "default_baseline_dir": "outputs/board_strategy_review_baseline",
        "recommended_preview_source": "rendered_pptx",
        "preview_provenance_guidance": "Board-facing reviews should use rendered PPTX previews as the canonical regression source before any baseline promotion.",
        "default_output_pptx": "outputs/board_strategy_review.pptx",
        "default_preview_dir": "outputs/board_strategy_review_previews",
        "default_report_json": "outputs/board_strategy_review_report.json",
        "suggested_steps": ["template", "review", "render", "preview-pptx", "compare-pptx", "promote-baseline"],
        "recommended_regression_flow": ["render", "preview-pptx", "compare-pptx", "promote-baseline"],
    },
    "product_operating_review": {
        "display_name": "Product Operating Review",
        "domain": "product",
        "audience_profile": "product",
        "description": "Operating review for roadmap, adoption, and portfolio decisions across product leadership.",
        "operating_mode": "product",
        "cadence": "monthly",
        "stakeholders": ["CPO", "Product Directors", "Design", "Engineering"],
        "recommended_asset_collections": ["product_mockups", "roadmap_workshops"],
        "default_brand_pack": "product_signal",
        "default_preview_backend": "auto",
        "default_preview_require_real": False,
        "default_preview_fail_on_regression": False,
        "default_baseline_dir": "outputs/product_operating_review_baseline",
        "recommended_preview_source": "rendered_pptx",
        "preview_provenance_guidance": "Use office-backed preview when available, but keep auto fallback for faster monthly operating reviews.",
        "default_output_pptx": "outputs/product_operating_review.pptx",
        "default_preview_dir": "outputs/product_operating_review_previews",
        "default_report_json": "outputs/product_operating_review_report.json",
        "suggested_steps": ["template", "review", "preview", "render", "preview-pptx"],
        "recommended_regression_flow": ["render", "preview-pptx", "compare-pptx"],
    },
    "consulting_steerco": {
        "display_name": "Consulting SteerCo",
        "domain": "consulting",
        "audience_profile": "consulting",
        "description": "Client steerco packet for consulting engagements with synthesis, options, and recommendation framing.",
        "operating_mode": "client_service",
        "cadence": "monthly",
        "stakeholders": ["Engagement Lead", "Client Sponsor", "PMO"],
        "recommended_asset_collections": ["strategy_workshops", "team_alignment_sessions"],
        "default_brand_pack": "consulting_signature",
        "default_preview_backend": "office",
        "default_preview_require_real": True,
        "default_preview_fail_on_regression": False,
        "default_baseline_dir": "outputs/consulting_steerco_baseline",
        "recommended_preview_source": "rendered_pptx",
        "preview_provenance_guidance": "Client steerco baselines should be promoted only from rendered PPTX previews so provenance stays explicit during review cycles.",
        "default_output_pptx": "outputs/consulting_steerco.pptx",
        "default_preview_dir": "outputs/consulting_steerco_previews",
        "default_report_json": "outputs/consulting_steerco_report.json",
        "suggested_steps": ["template", "review", "render", "preview-pptx", "compare-pptx", "promote-baseline"],
        "recommended_regression_flow": ["render", "preview-pptx", "compare-pptx", "promote-baseline"],
    },
    "commercial_proposal": {
        "display_name": "Commercial Proposal",
        "domain": "proposal",
        "audience_profile": "proposal",
        "description": "Proposal/commercial workflow for turning scoped offers into decision-ready executive decks.",
        "operating_mode": "commercial_proposal",
        "cadence": "deal_cycle",
        "stakeholders": ["Account Executive", "Engagement Lead", "Client Sponsor"],
        "recommended_asset_collections": ["executive_decision_moments", "strategy_workshops"],
        "default_brand_pack": "consulting_signature",
        "default_preview_backend": "office",
        "default_preview_require_real": True,
        "default_preview_fail_on_regression": False,
        "default_baseline_dir": "outputs/commercial_proposal_baseline",
        "recommended_preview_source": "rendered_pptx",
        "preview_provenance_guidance": "Commercial proposals should be reviewed from the final rendered PPTX so proposal baselines track exactly what buyers see.",
        "default_output_pptx": "outputs/commercial_proposal.pptx",
        "default_preview_dir": "outputs/commercial_proposal_previews",
        "default_report_json": "outputs/commercial_proposal_report.json",
        "suggested_steps": ["template", "review", "render", "preview-pptx", "compare-pptx", "promote-baseline"],
        "recommended_regression_flow": ["render", "preview-pptx", "compare-pptx", "promote-baseline"],
    },
}


def list_workflow_presets() -> list[str]:
    return sorted(WORKFLOW_PRESETS)


def get_workflow_preset(name: str) -> dict[str, object]:
    normalized = name.strip().lower().replace("-", "_")
    if normalized not in WORKFLOW_PRESETS:
        raise ValueError(f"Unknown workflow preset: {name}")
    preset = deepcopy(WORKFLOW_PRESETS[normalized])
    preset["name"] = normalized
    return preset


def build_workflow_packet(
    name: str,
    *,
    theme_name: str | None = None,
    brand_pack: str | None = None,
) -> dict[str, object]:
    workflow = get_workflow_preset(name)
    audience_profile_name = str(workflow["audience_profile"])
    domain = str(workflow["domain"])
    effective_brand_pack = brand_pack or str(workflow.get("default_brand_pack") or "").strip() or None
    asset_collection_names = list(workflow.get("recommended_asset_collections", []))
    brand_pack_payload = get_brand_pack(effective_brand_pack) if effective_brand_pack else None
    for collection_name in (brand_pack_payload or {}).get("recommended_asset_collections", []):
        if collection_name not in asset_collection_names:
            asset_collection_names.append(collection_name)
    recommended_asset_collections = [
        get_asset_collection(collection_name)
        for collection_name in asset_collection_names
    ]
    template = build_domain_template(
        domain,
        theme_name=theme_name,
        audience_profile=audience_profile_name,
        brand_pack=effective_brand_pack,
    )
    return {
        "workflow": workflow,
        "brand_pack": brand_pack_payload,
        "branding_bundle": build_branding_bundle(brand_pack_payload),
        "audience_profile": get_audience_profile(audience_profile_name),
        "asset_collections": recommended_asset_collections,
        "asset_strategy": {
            "workflow_name": workflow["name"],
            "visual_language": (brand_pack_payload or {}).get("visual_language"),
            "cover_asset_collection": (brand_pack_payload or {}).get("cover_asset_collection"),
            "placeholder_style": (brand_pack_payload or {}).get("placeholder_style"),
            "logo_text": ((brand_pack_payload or {}).get("presentation_overrides") or {}).get("logo_text"),
            "logo_path": ((brand_pack_payload or {}).get("presentation_overrides") or {}).get("logo_path"),
            "recommended_asset_collections": asset_collection_names,
        },
        "preview_recommendation": {
            "backend": workflow.get("default_preview_backend"),
            "require_real_previews": bool(workflow.get("default_preview_require_real", False)),
            "fail_on_regression": bool(workflow.get("default_preview_fail_on_regression", False)),
            "baseline_dir": workflow.get("default_baseline_dir"),
            "recommended_source": workflow.get("recommended_preview_source") or "rendered_pptx",
            "critical_regression_flow": list(workflow.get("recommended_regression_flow", [])),
            "guidance": workflow.get("preview_provenance_guidance"),
        },
        "template": template,
        "slide_asset_suggestions": _build_slide_asset_suggestions(
            template,
            recommended_asset_collections,
            brand_pack_payload=brand_pack_payload,
            workflow_name=str(workflow["name"]),
        ),
    }