from __future__ import annotations

from copy import deepcopy

BRAND_PACKS: dict[str, dict[str, object]] = {
    "board_navy": {
        "display_name": "Board Navy",
        "description": "Board-facing brand pack with dark boardroom styling and premium leadership framing.",
        "visual_language": "Dark, high-contrast board narrative with premium executive tone.",
        "cover_asset_collection": "boardroom_backdrops",
        "placeholder_style": "photo",
        "presentation_overrides": {
            "theme": "dark_boardroom",
            "footer_text": "Board brand pack",
            "client_name": "Executive Leadership",
            "primary_color": "14263F",
            "secondary_color": "B08B5B",
            "logo_text": "BOARD NAVY",
            "logo_fill_color": "14263F",
            "logo_text_color": "F7F5F2",
        },
        "cover_eyebrow": "Board review",
        "cover_layout_variant": "hero_cover",
        "recommended_asset_collections": ["boardroom_backdrops", "executive_decision_moments"],
        "recommended_workflows": ["board_strategy", "consulting_steerco"],
    },
    "consulting_signature": {
        "display_name": "Consulting Signature",
        "description": "Client-service pack with clean consulting styling and structured steering-committee framing.",
        "visual_language": "Structured advisory narrative with restrained consulting polish.",
        "cover_asset_collection": "strategy_workshops",
        "placeholder_style": "diagram",
        "presentation_overrides": {
            "theme": "consulting_clean",
            "footer_text": "Consulting brand pack",
            "client_name": "Advisory Team",
            "primary_color": "0E5A8A",
            "secondary_color": "7A8C99",
            "logo_text": "CONSULTING",
            "logo_fill_color": "0E5A8A",
            "logo_text_color": "FFFFFF",
        },
        "cover_eyebrow": "Advisory review",
        "cover_layout_variant": "hero_cover",
        "recommended_asset_collections": ["strategy_workshops", "team_alignment_sessions"],
        "recommended_workflows": ["consulting_steerco", "board_strategy"],
    },
    "sales_pipeline": {
        "display_name": "Sales Pipeline",
        "description": "Commercial pack tuned for pipeline, forecast and sales operating reviews.",
        "visual_language": "Commercial operating-review language centered on forecasts, dashboards, and momentum.",
        "cover_asset_collection": "sales_dashboards",
        "placeholder_style": "analytical_visual",
        "presentation_overrides": {
            "theme": "dark_boardroom",
            "footer_text": "Sales pipeline brand pack",
            "client_name": "Revenue Leadership",
            "primary_color": "6B1F2B",
            "secondary_color": "F59E0B",
            "logo_text": "SALES PIPELINE",
            "logo_fill_color": "6B1F2B",
            "logo_text_color": "FFF7ED",
        },
        "cover_eyebrow": "Revenue review",
        "cover_layout_variant": "hero_cover",
        "recommended_asset_collections": ["sales_dashboards", "forecast_reviews"],
        "recommended_workflows": ["sales_qbr"],
    },
    "product_signal": {
        "display_name": "Product Signal",
        "description": "Product-oriented pack with brighter accenting for roadmap and adoption narratives.",
        "visual_language": "Sharper product storytelling with roadmap, adoption, and interface-heavy visuals.",
        "cover_asset_collection": "product_mockups",
        "placeholder_style": "screenshot",
        "presentation_overrides": {
            "theme": "startup_minimal",
            "footer_text": "Product signal brand pack",
            "client_name": "Product Leadership",
            "primary_color": "0F766E",
            "secondary_color": "7C3AED",
            "logo_text": "PRODUCT SIGNAL",
            "logo_fill_color": "0F766E",
            "logo_text_color": "F8FAFB",
        },
        "cover_eyebrow": "Product review",
        "cover_layout_variant": "hero_cover",
        "recommended_asset_collections": ["product_mockups", "roadmap_workshops"],
        "recommended_workflows": ["product_operating_review"],
    },
}


def list_brand_packs() -> list[str]:
    return sorted(BRAND_PACKS)


def get_brand_pack(name: str) -> dict[str, object]:
    normalized = name.strip().lower().replace("-", "_")
    if normalized not in BRAND_PACKS:
        raise ValueError(f"Unknown brand pack: {name}")
    payload = deepcopy(BRAND_PACKS[normalized])
    payload["name"] = normalized
    return payload


def build_branding_bundle(brand_pack_payload: dict[str, object] | None) -> dict[str, object] | None:
    if not brand_pack_payload:
        return None

    presentation = dict(brand_pack_payload.get("presentation_overrides") or {})
    return {
        "name": brand_pack_payload.get("name"),
        "display_name": brand_pack_payload.get("display_name"),
        "theme": presentation.get("theme"),
        "footer_text": presentation.get("footer_text"),
        "client_name": presentation.get("client_name"),
        "primary_color": presentation.get("primary_color"),
        "secondary_color": presentation.get("secondary_color"),
        "logo_path": presentation.get("logo_path"),
        "logo_text": presentation.get("logo_text"),
        "logo_fill_color": presentation.get("logo_fill_color"),
        "logo_text_color": presentation.get("logo_text_color"),
        "cover_eyebrow": brand_pack_payload.get("cover_eyebrow"),
        "cover_layout_variant": brand_pack_payload.get("cover_layout_variant"),
        "visual_language": brand_pack_payload.get("visual_language"),
        "placeholder_style": brand_pack_payload.get("placeholder_style"),
        "recommended_asset_collections": list(brand_pack_payload.get("recommended_asset_collections", [])),
        "recommended_workflows": list(brand_pack_payload.get("recommended_workflows", [])),
    }


def apply_brand_pack(payload: dict[str, object], brand_pack_name: str) -> dict[str, object]:
    brand_pack = get_brand_pack(brand_pack_name)
    branded_payload = deepcopy(payload)
    presentation = dict(branded_payload.get("presentation") or {})
    for key, value in dict(brand_pack.get("presentation_overrides") or {}).items():
        if value is not None:
            presentation[key] = value
    branded_payload["presentation"] = presentation

    slides = branded_payload.get("slides") or []
    if slides and isinstance(slides[0], dict) and slides[0].get("type") == "title":
        if brand_pack.get("cover_eyebrow"):
            slides[0]["eyebrow"] = str(brand_pack["cover_eyebrow"])
        if brand_pack.get("cover_layout_variant"):
            slides[0]["layout_variant"] = str(brand_pack["cover_layout_variant"])

    return branded_payload