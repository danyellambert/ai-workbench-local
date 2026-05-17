"""Public API for the reusable JSON-to-PPTX creator."""

from ppt_creator.api import (
    build_api_server,
    compare_pptx_payload,
    generate_briefing_payload,
    preview_spec_payload,
    render_spec_payload,
    review_spec_payload,
    serve_api,
    validate_spec_payload,
)
from ppt_creator.assets import get_asset_collection, list_asset_collections
from ppt_creator.brand_packs import (
    apply_brand_pack,
    build_branding_bundle,
    get_brand_pack,
    list_brand_packs,
)
from ppt_creator.catalog import build_marketplace_catalog
from ppt_creator.layouts import get_layout_catalog, list_layout_catalog
from ppt_creator.preview import (
    PreviewRenderer,
    compare_pptx_artifacts,
    render_previews,
    review_pptx_artifact,
)
from ppt_creator.profiles import get_audience_profile, list_audience_profiles
from ppt_creator.qa import review_presentation, review_preview_artifacts
from ppt_creator.renderer import PresentationRenderer, render_presentation
from ppt_creator.schema import (
    CardItem,
    ComparisonColumn,
    MetricItem,
    PresentationInput,
    PresentationMeta,
    Slide,
    SlideType,
    TimelineItem,
)
from ppt_creator.templates import (
    build_domain_template,
    build_template_packet,
    list_template_domains,
)
from ppt_creator.theme import (
    CONSULTING_CLEAN,
    DARK_BOARDROOM,
    EXECUTIVE_PREMIUM_MINIMAL,
    STARTUP_MINIMAL,
    CanvasTokens,
    ColorTokens,
    ComponentTokens,
    GridTokens,
    SemanticLayoutPreset,
    SemanticLayoutTokens,
    SpacingTokens,
    Theme,
    TypographyTokens,
    get_theme,
    get_theme_catalog,
    list_theme_catalog,
    list_themes,
    theme_display_name,
)
from ppt_creator.workflows import build_workflow_packet, get_workflow_preset, list_workflow_presets

__version__ = "0.1.0"

__all__ = [
    "CanvasTokens",
    "ColorTokens",
    "ComponentTokens",
    "GridTokens",
    "SemanticLayoutPreset",
    "SemanticLayoutTokens",
    "__version__",
    "CardItem",
    "ComparisonColumn",
    "CONSULTING_CLEAN",
    "DARK_BOARDROOM",
    "EXECUTIVE_PREMIUM_MINIMAL",
    "MetricItem",
    "PresentationInput",
    "PresentationMeta",
    "PresentationRenderer",
    "SpacingTokens",
    "Slide",
    "SlideType",
    "Theme",
    "TimelineItem",
    "TypographyTokens",
    "STARTUP_MINIMAL",
    "build_api_server",
    "build_marketplace_catalog",
    "compare_pptx_artifacts",
    "compare_pptx_payload",
    "generate_briefing_payload",
    "build_domain_template",
    "build_template_packet",
    "build_workflow_packet",
    "apply_brand_pack",
    "build_branding_bundle",
    "get_asset_collection",
    "get_brand_pack",
    "get_audience_profile",
    "get_layout_catalog",
    "get_theme",
    "get_theme_catalog",
    "get_workflow_preset",
    "list_asset_collections",
    "list_audience_profiles",
    "list_brand_packs",
    "list_layout_catalog",
    "list_template_domains",
    "list_theme_catalog",
    "list_themes",
    "list_workflow_presets",
    "PreviewRenderer",
    "preview_spec_payload",
    "render_previews",
    "review_pptx_artifact",
    "review_preview_artifacts",
    "review_presentation",
    "review_spec_payload",
    "render_spec_payload",
    "render_presentation",
    "serve_api",
    "theme_display_name",
    "validate_spec_payload",
]
