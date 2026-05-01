from __future__ import annotations

from copy import deepcopy

AUDIENCE_PROFILES: dict[str, dict[str, object]] = {
    "board": {
        "display_name": "Board",
        "default_theme": "dark_boardroom",
        "footer_text": "Board profile",
        "cover_eyebrow": "Board review",
        "preferred_layouts": ["title", "summary", "metrics", "comparison", "faq"],
        "tone": "concise, decision-oriented, risk-aware",
        "recommended_asset_collections": ["boardroom_backdrops", "executive_decision_moments"],
    },
    "consulting": {
        "display_name": "Consulting",
        "default_theme": "consulting_clean",
        "footer_text": "Consulting profile",
        "cover_eyebrow": "Client review",
        "preferred_layouts": ["title", "agenda", "comparison", "two_column", "summary"],
        "tone": "structured, analytical, synthesis-heavy",
        "recommended_asset_collections": ["strategy_workshops", "team_alignment_sessions"],
    },
    "sales": {
        "display_name": "Sales",
        "default_theme": "dark_boardroom",
        "footer_text": "Sales profile",
        "cover_eyebrow": "Revenue review",
        "preferred_layouts": ["title", "agenda", "metrics", "chart", "summary"],
        "tone": "pipeline-focused, operational, performance-driven",
        "recommended_asset_collections": ["sales_dashboards", "forecast_reviews"],
    },
    "product": {
        "display_name": "Product",
        "default_theme": "startup_minimal",
        "footer_text": "Product profile",
        "cover_eyebrow": "Product review",
        "preferred_layouts": ["title", "timeline", "table", "faq", "summary"],
        "tone": "roadmap-driven, adoption-aware, prioritization-focused",
        "recommended_asset_collections": ["product_mockups", "roadmap_workshops"],
    },
    "proposal": {
        "display_name": "Proposal",
        "default_theme": "consulting_clean",
        "footer_text": "Proposal profile",
        "cover_eyebrow": "Commercial proposal",
        "preferred_layouts": ["title", "cards", "comparison", "table", "summary", "closing"],
        "tone": "persuasive, commercially precise, outcome-oriented",
        "recommended_asset_collections": ["executive_decision_moments", "strategy_workshops"],
    },
}


def list_audience_profiles() -> list[str]:
    return sorted(AUDIENCE_PROFILES)


def get_audience_profile(name: str) -> dict[str, object]:
    normalized = name.strip().lower().replace("-", "_")
    if normalized not in AUDIENCE_PROFILES:
        raise ValueError(f"Unknown audience profile: {name}")
    return deepcopy(AUDIENCE_PROFILES[normalized])