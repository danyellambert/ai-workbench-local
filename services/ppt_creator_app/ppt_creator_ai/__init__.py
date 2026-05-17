"""Optional briefing-to-deck generation layer kept separate from the core renderer."""

from ppt_creator_ai.briefing import (
    BriefingFAQ,
    BriefingInput,
    BriefingMetric,
    BriefingMilestone,
    BriefingOption,
    build_briefing_analysis,
    generate_presentation_input_from_briefing,
    generate_presentation_payload_from_briefing,
    review_presentation_density,
    suggest_image_queries_from_briefing,
    summarize_text_to_executive_bullets,
)
from ppt_creator_ai.providers import (
    HeuristicBriefingProvider,
    LocalServiceBriefingProvider,
    get_provider,
    list_provider_names,
)

__all__ = [
    "BriefingFAQ",
    "BriefingInput",
    "BriefingMetric",
    "BriefingMilestone",
    "BriefingOption",
    "build_briefing_analysis",
    "generate_presentation_input_from_briefing",
    "generate_presentation_payload_from_briefing",
    "review_presentation_density",
    "suggest_image_queries_from_briefing",
    "summarize_text_to_executive_bullets",
    "HeuristicBriefingProvider",
    "LocalServiceBriefingProvider",
    "get_provider",
    "list_provider_names",
]
