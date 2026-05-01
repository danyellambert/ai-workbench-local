from __future__ import annotations

from ppt_creator.assets import get_asset_collection, list_asset_collections
from ppt_creator.brand_packs import get_brand_pack, list_brand_packs
from ppt_creator.layouts import list_layout_catalog
from ppt_creator.profiles import get_audience_profile, list_audience_profiles
from ppt_creator.templates import list_template_domains
from ppt_creator.theme import list_theme_catalog
from ppt_creator.workflows import get_workflow_preset, list_workflow_presets


def build_marketplace_catalog() -> dict[str, object]:
    themes = list_theme_catalog()
    layouts = list_layout_catalog()
    audience_profiles = [
        {"name": name, **get_audience_profile(name)}
        for name in list_audience_profiles()
    ]
    brand_packs = [get_brand_pack(name) for name in list_brand_packs()]
    asset_collections = [get_asset_collection(name) for name in list_asset_collections()]
    workflows = [get_workflow_preset(name) for name in list_workflow_presets()]
    template_domains = list_template_domains()

    return {
        "mode": "marketplace",
        "summary": {
            "theme_count": len(themes),
            "layout_count": len(layouts),
            "audience_profile_count": len(audience_profiles),
            "brand_pack_count": len(brand_packs),
            "asset_collection_count": len(asset_collections),
            "workflow_count": len(workflows),
            "template_domain_count": len(template_domains),
        },
        "themes": themes,
        "layouts": layouts,
        "audience_profiles": audience_profiles,
        "brand_packs": brand_packs,
        "asset_collections": asset_collections,
        "workflows": workflows,
        "template_domains": template_domains,
    }