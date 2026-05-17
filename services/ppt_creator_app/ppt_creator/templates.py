from __future__ import annotations

import json

from ppt_creator.assets import get_asset_collection
from ppt_creator.brand_packs import apply_brand_pack, build_branding_bundle, get_brand_pack
from ppt_creator.profiles import get_audience_profile

DOMAIN_ASSET_COLLECTIONS: dict[str, list[str]] = {
    "sales": ["sales_dashboards", "forecast_reviews"],
    "consulting": ["strategy_workshops", "team_alignment_sessions"],
    "strategy": ["boardroom_backdrops", "strategy_workshops"],
    "product": ["product_mockups", "roadmap_workshops"],
    "proposal": ["executive_decision_moments", "strategy_workshops", "team_alignment_sessions"],
}

DOMAIN_TEMPLATES: dict[str, dict[str, object]] = {
    "sales": {
        "presentation": {
            "title": "Sales operating review",
            "subtitle": "Commercial performance and execution priorities",
            "client_name": "Revenue Leadership",
            "author": "PPT Creator",
            "date": "2026-03-26",
            "theme": "dark_boardroom",
            "footer_text": "Sales template",
        },
        "slides": [
            {
                "type": "title",
                "title": "Sales operating review",
                "subtitle": "Commercial performance and execution priorities",
                "layout_variant": "hero_cover",
                "eyebrow": "Sales template",
            },
            {
                "type": "agenda",
                "title": "Agenda",
                "bullets": ["Performance", "Pipeline", "Execution risks", "Next actions"],
            },
            {
                "type": "metrics",
                "title": "Headline performance",
                "metrics": [
                    {"value": "$8.4M", "label": "pipeline added"},
                    {"value": "31%", "label": "win rate"},
                    {"value": "104%", "label": "plan attainment"},
                ],
            },
            {
                "type": "chart",
                "title": "Quarterly revenue trend",
                "layout_variant": "column",
                "chart_categories": ["Q1", "Q2", "Q3", "Q4"],
                "chart_series": [
                    {"name": "Revenue", "values": [5.2, 6.1, 7.4, 8.4]},
                ],
            },
            {
                "type": "summary",
                "title": "Executive summary",
                "bullets": [
                    "Protect pipeline quality",
                    "Reduce deal slippage",
                    "Focus coaching on conversion moments",
                ],
            },
            {"type": "closing", "title": "Closing thought", "quote": "Execution quality compounds when the operating rhythm stays consistent."},
        ],
    },
    "consulting": {
        "presentation": {
            "title": "Consulting engagement review",
            "subtitle": "Client situation, options, and recommendation",
            "client_name": "Client Name",
            "author": "PPT Creator",
            "date": "2026-03-26",
            "theme": "consulting_clean",
            "footer_text": "Consulting template",
        },
        "slides": [
            {
                "type": "title",
                "title": "Consulting engagement review",
                "subtitle": "Client situation, options, and recommendation",
                "layout_variant": "hero_cover",
                "eyebrow": "Consulting template",
            },
            {
                "type": "agenda",
                "title": "Discussion flow",
                "bullets": ["Situation", "Diagnosis", "Options", "Recommendation"],
            },
            {
                "type": "comparison",
                "title": "Option framing",
                "comparison_columns": [
                    {"title": "Current approach", "body": "The organization keeps absorbing unnecessary complexity."},
                    {"title": "Recommended approach", "bullets": ["Simplify priorities", "Clarify ownership", "Sequence execution"]},
                ],
            },
            {
                "type": "summary",
                "title": "Recommendation",
                "body": "The recommended path reduces complexity first, then scales only after decision clarity improves.",
                "bullets": ["Narrow scope", "Clarify decisions", "Measure progress monthly"],
            },
            {"type": "closing", "title": "Closing thought", "quote": "A stronger operating model is usually the result of fewer, clearer choices."},
        ],
    },
    "strategy": {
        "presentation": {
            "title": "Strategy review",
            "subtitle": "Priorities, trade-offs, and sequencing",
            "client_name": "Strategy Office",
            "author": "PPT Creator",
            "date": "2026-03-26",
            "theme": "executive_premium_minimal",
            "footer_text": "Strategy template",
        },
        "slides": [
            {
                "type": "title",
                "title": "Strategy review",
                "subtitle": "Priorities, trade-offs, and sequencing",
                "layout_variant": "hero_cover",
                "eyebrow": "Strategy template",
            },
            {
                "type": "timeline",
                "title": "Strategic sequence",
                "timeline_items": [
                    {"title": "Diagnose", "body": "Clarify the few questions that matter most."},
                    {"title": "Decide", "body": "Choose the winning priorities and explicit trade-offs."},
                    {"title": "Sequence", "body": "Stage execution in a realistic order."},
                ],
            },
            {
                "type": "two_column",
                "title": "Strategic trade-off",
                "two_column_columns": [
                    {"title": "If focus drifts", "body": "Execution spreads too thin and decisions stay noisy."},
                    {"title": "If focus sharpens", "bullets": ["Clearer trade-offs", "Better capital allocation", "Faster learning"]},
                ],
            },
            {
                "type": "summary",
                "title": "Executive summary",
                "bullets": ["Focus on fewer bets", "Stage execution deliberately", "Review strategy through measurable milestones"],
            },
            {"type": "closing", "title": "Closing thought", "quote": "Strategy compounds when sequencing is as disciplined as ambition."},
        ],
    },
    "product": {
        "presentation": {
            "title": "Product portfolio review",
            "subtitle": "Roadmap, adoption, and product decisions",
            "client_name": "Product Leadership",
            "author": "PPT Creator",
            "date": "2026-03-26",
            "theme": "startup_minimal",
            "footer_text": "Product template",
        },
        "slides": [
            {
                "type": "title",
                "title": "Product portfolio review",
                "subtitle": "Roadmap, adoption, and product decisions",
                "layout_variant": "hero_cover",
                "eyebrow": "Product template",
            },
            {
                "type": "agenda",
                "title": "Agenda",
                "bullets": ["Product signals", "Roadmap choices", "Risks", "Next quarter"],
            },
            {
                "type": "table",
                "title": "Portfolio snapshot",
                "table_columns": ["Area", "Status", "Action"],
                "table_rows": [
                    ["Core workflow", "Healthy", "Sustain investment"],
                    ["New bets", "Mixed", "Reduce parallel scope"],
                ],
            },
            {
                "type": "chart",
                "title": "Adoption trend",
                "layout_variant": "line",
                "chart_categories": ["Jan", "Feb", "Mar", "Apr"],
                "chart_series": [
                    {"name": "Active teams", "values": [12, 16, 21, 29]},
                ],
            },
            {
                "type": "faq",
                "title": "Leadership FAQ",
                "faq_items": [
                    {"title": "What should move first?", "body": "Prioritize the workflow with the strongest usage pull and clearest value signal."},
                    {"title": "What should wait?", "body": "Pause low-conviction initiatives until the roadmap is more concentrated."},
                ],
            },
            {
                "type": "summary",
                "title": "Recommendation",
                "bullets": ["Concentrate roadmap scope", "Protect core adoption", "Use clear decision gates"],
            },
        ],
    },
    "proposal": {
        "presentation": {
            "title": "Commercial proposal",
            "subtitle": "Decision-ready proposal and scoped path to impact",
            "client_name": "Prospective Client",
            "author": "PPT Creator",
            "date": "2026-03-26",
            "theme": "consulting_clean",
            "footer_text": "Proposal template",
        },
        "slides": [
            {
                "type": "title",
                "title": "Commercial proposal",
                "subtitle": "Decision-ready proposal and scoped path to impact",
                "layout_variant": "hero_cover",
                "eyebrow": "Proposal template",
            },
            {
                "type": "agenda",
                "title": "Proposal flow",
                "bullets": ["Client context", "Value case", "Offer options", "Commercial structure", "Recommendation"],
            },
            {
                "type": "cards",
                "title": "Why this proposal is built to win",
                "cards": [
                    {
                        "title": "Faster path to value",
                        "body": "Start with the highest-confidence workstream so value is visible early and the engagement de-risks quickly.",
                        "footer": "Accelerate proof",
                    },
                    {
                        "title": "Scoped for execution",
                        "body": "Keep the initial scope narrow enough to deliver cleanly while preserving room to expand after sign-off.",
                        "footer": "Lower delivery risk",
                    },
                    {
                        "title": "Clear decision structure",
                        "body": "Translate the proposal into explicit workstreams, commercial choices, and approval points.",
                        "footer": "Better buying clarity",
                    },
                ],
            },
            {
                "type": "comparison",
                "title": "Offer options",
                "comparison_columns": [
                    {
                        "title": "Focused pilot",
                        "body": "A narrower first phase to prove value, stabilize delivery, and create confidence for expansion.",
                        "bullets": ["Fast launch", "Lower commitment", "Sharper proof points"],
                    },
                    {
                        "title": "Scaled engagement",
                        "body": "A broader scope for teams that already have strong alignment and want a faster transformation arc.",
                        "bullets": ["Wider reach", "More coordination", "Higher upfront commitment"],
                    },
                ],
            },
            {
                "type": "table",
                "title": "Commercial structure",
                "table_columns": ["Workstream", "Included scope", "Commercial model"],
                "table_rows": [
                    ["Discovery and framing", "Leadership interviews, operating hypothesis, executive readout", "Fixed fee"],
                    ["Pilot delivery", "Workflow build, rollout support, QA cadence", "Milestone-based"],
                    ["Scale-up option", "Expansion backlog, enablement, governance handoff", "Optional phase"],
                ],
            },
            {
                "type": "summary",
                "title": "Recommended path",
                "body": "The best path is to approve a focused first phase that proves business value quickly while preserving an explicit scale-up option after the first decision gate.",
                "bullets": ["Approve the focused pilot", "Measure visible value early", "Expand only after proof and alignment"],
            },
            {
                "type": "closing",
                "title": "Closing thought",
                "quote": "A strong proposal makes the buying decision feel clearer, safer, and easier to act on.",
            },
        ],
    },
}


def list_template_domains() -> list[str]:
    return sorted(DOMAIN_TEMPLATES)


def build_domain_template(
    domain: str,
    *,
    theme_name: str | None = None,
    audience_profile: str | None = None,
    brand_pack: str | None = None,
) -> dict[str, object]:
    normalized = domain.strip().lower().replace("-", "_")
    if normalized not in DOMAIN_TEMPLATES:
        raise ValueError(f"Unknown template domain: {domain}")

    payload = json.loads(json.dumps(DOMAIN_TEMPLATES[normalized]))
    if audience_profile:
        profile = get_audience_profile(audience_profile)
        payload["presentation"]["footer_text"] = str(profile["footer_text"])
        if payload["slides"] and payload["slides"][0].get("type") == "title":
            payload["slides"][0]["eyebrow"] = str(profile["cover_eyebrow"])
        if not theme_name:
            payload["presentation"]["theme"] = str(profile["default_theme"])
    if brand_pack:
        payload = apply_brand_pack(payload, brand_pack)
    if theme_name:
        payload["presentation"]["theme"] = theme_name
    return payload


def _infer_slide_visual_type(slide_payload: dict[str, object]) -> str:
    text = " ".join(
        str(slide_payload.get(key) or "")
        for key in ["title", "subtitle", "body", "image_caption"]
    ).lower()
    slide_type = str(slide_payload.get("type") or "")
    if any(keyword in text for keyword in ["screenshot", "screen", "dashboard", "ui", "mockup"]):
        return "screenshot"
    if any(keyword in text for keyword in ["diagram", "workflow", "process", "architecture", "roadmap", "timeline"]):
        return "diagram"
    if slide_type in {"metrics", "chart", "table"} or any(
        keyword in text for keyword in ["metric", "kpi", "trend", "analysis", "analytics", "table"]
    ):
        return "analytical_visual"
    return "photo"


def _build_slide_asset_suggestions(
    template: dict[str, object],
    asset_collections: list[dict[str, object]],
    *,
    brand_pack_payload: dict[str, object] | None = None,
    workflow_name: str | None = None,
) -> list[dict[str, object]]:
    slide_asset_suggestions: list[dict[str, object]] = []
    cover_asset_collection = None
    if brand_pack_payload and brand_pack_payload.get("cover_asset_collection"):
        cover_asset_collection = get_asset_collection(str(brand_pack_payload["cover_asset_collection"]))

    for index, slide_payload in enumerate(template.get("slides", []), start=1):
        slide_type = str(slide_payload.get("type") or "slide")
        visual_type = _infer_slide_visual_type(slide_payload)
        matching_collections = [
            collection
            for collection in asset_collections
            if slide_type in list(collection.get("preferred_layouts", []))
        ] or list(asset_collections)
        if slide_type == "title" and cover_asset_collection is not None:
            matching_collections = [cover_asset_collection, *[c for c in matching_collections if c.get("name") != cover_asset_collection.get("name")]]

        recommended_queries: list[str] = []
        for collection in matching_collections:
            for query in list(collection.get("queries", [])):
                if query not in recommended_queries:
                    recommended_queries.append(str(query))

        primary_collection = matching_collections[0] if matching_collections else None
        suggestion: dict[str, object] = {
            "slide_number": index,
            "slide_type": slide_type,
            "title": slide_payload.get("title"),
            "visual_type": visual_type,
            "recommended_asset_collections": [collection["name"] for collection in matching_collections],
            "recommended_queries": recommended_queries[:4],
        }
        if primary_collection:
            if primary_collection.get("visual_style"):
                suggestion["asset_style"] = primary_collection["visual_style"]
            if primary_collection.get("composition_notes"):
                suggestion["composition_notes"] = primary_collection["composition_notes"]
            if primary_collection.get("preferred_focal_point"):
                suggestion["recommended_focal_point"] = dict(primary_collection["preferred_focal_point"])
        if brand_pack_payload:
            suggestion["brand_pack"] = brand_pack_payload["name"]
            if brand_pack_payload.get("visual_language"):
                suggestion["brand_visual_language"] = brand_pack_payload["visual_language"]
        if workflow_name:
            suggestion["workflow_name"] = workflow_name
        slide_asset_suggestions.append(suggestion)

    return slide_asset_suggestions


def build_template_packet(
    domain: str,
    *,
    theme_name: str | None = None,
    audience_profile: str | None = None,
    brand_pack: str | None = None,
) -> dict[str, object]:
    template = build_domain_template(
        domain,
        theme_name=theme_name,
        audience_profile=audience_profile,
        brand_pack=brand_pack,
    )
    normalized = domain.strip().lower().replace("-", "_")
    audience_profile_payload = get_audience_profile(audience_profile) if audience_profile else None
    brand_pack_payload = get_brand_pack(brand_pack) if brand_pack else None

    collection_names: list[str] = []
    for collection_name in DOMAIN_ASSET_COLLECTIONS.get(normalized, []):
        if collection_name not in collection_names:
            collection_names.append(collection_name)
    for collection_name in (brand_pack_payload or {}).get("recommended_asset_collections", []):
        if collection_name not in collection_names:
            collection_names.append(str(collection_name))

    asset_collections = [get_asset_collection(collection_name) for collection_name in collection_names]
    slide_asset_suggestions = _build_slide_asset_suggestions(
        template,
        asset_collections,
        brand_pack_payload=brand_pack_payload,
    )

    return {
        "domain": normalized,
        "template": template,
        "audience_profile": audience_profile_payload,
        "brand_pack": brand_pack_payload,
        "branding_bundle": build_branding_bundle(brand_pack_payload),
        "asset_collections": asset_collections,
        "asset_strategy": {
            "domain_asset_collections": DOMAIN_ASSET_COLLECTIONS.get(normalized, []),
            "brand_pack_asset_collections": list((brand_pack_payload or {}).get("recommended_asset_collections", [])),
            "visual_language": (brand_pack_payload or {}).get("visual_language"),
            "cover_asset_collection": (brand_pack_payload or {}).get("cover_asset_collection"),
            "placeholder_style": (brand_pack_payload or {}).get("placeholder_style"),
            "logo_text": ((brand_pack_payload or {}).get("presentation_overrides") or {}).get("logo_text"),
            "logo_path": ((brand_pack_payload or {}).get("presentation_overrides") or {}).get("logo_path"),
        },
        "slide_asset_suggestions": slide_asset_suggestions,
    }
