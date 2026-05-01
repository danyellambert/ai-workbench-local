"""Layout renderers for supported slide types."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from ppt_creator.layouts import (
    agenda,
    bullets,
    cards,
    chart,
    closing,
    comparison,
    faq,
    image_text,
    metrics,
    section,
    summary,
    table,
    timeline,
    title,
    two_column,
)
from ppt_creator.schema import LAYOUT_VARIANTS_BY_SLIDE_TYPE, SlideType

LayoutRenderer = Callable[[Any, Any, Any, Any, int, int], None]

LAYOUT_RENDERERS: dict[SlideType, LayoutRenderer] = {
    SlideType.TITLE: title.render,
    SlideType.SECTION: section.render,
    SlideType.AGENDA: agenda.render,
    SlideType.BULLETS: bullets.render,
    SlideType.CARDS: cards.render,
    SlideType.CHART: chart.render,
    SlideType.METRICS: metrics.render,
    SlideType.IMAGE_TEXT: image_text.render,
    SlideType.TIMELINE: timeline.render,
    SlideType.COMPARISON: comparison.render,
    SlideType.TWO_COLUMN: two_column.render,
    SlideType.TABLE: table.render,
    SlideType.FAQ: faq.render,
    SlideType.SUMMARY: summary.render,
    SlideType.CLOSING: closing.render,
}

LAYOUT_CATALOG: dict[SlideType, dict[str, object]] = {
    SlideType.TITLE: {
        "category": "cover",
        "summary": "Cover slide for opening the story with premium typography and optional hero visual.",
        "recommended_profiles": ["board", "consulting", "sales", "product", "proposal"],
    },
    SlideType.SECTION: {
        "category": "navigation",
        "summary": "Section divider that resets the narrative and anchors the next chapter.",
        "recommended_profiles": ["board", "consulting", "strategy", "proposal"],
    },
    SlideType.AGENDA: {
        "category": "navigation",
        "summary": "Agenda slide for sequencing the discussion and framing the flow of the deck.",
        "recommended_profiles": ["board", "consulting", "sales", "product", "proposal"],
    },
    SlideType.BULLETS: {
        "category": "narrative",
        "summary": "Narrative bullet slide with optional insight panel or full-width exposition.",
        "recommended_profiles": ["consulting", "sales", "proposal"],
    },
    SlideType.CARDS: {
        "category": "synthesis",
        "summary": "Three-up value cards for executive signals, benefits, or pillars.",
        "recommended_profiles": ["board", "consulting", "product", "proposal"],
    },
    SlideType.METRICS: {
        "category": "analytical",
        "summary": "KPI card layout for headline metrics and compact performance readouts.",
        "recommended_profiles": ["board", "sales", "product"],
    },
    SlideType.CHART: {
        "category": "analytical",
        "summary": "Data-driven chart slide for trends, comparisons, and quantitative evidence.",
        "recommended_profiles": ["board", "sales", "product", "proposal"],
    },
    SlideType.IMAGE_TEXT: {
        "category": "visual_narrative",
        "summary": "Text plus visual slot composition for operating models, screenshots, and illustrated stories.",
        "recommended_profiles": ["consulting", "product", "proposal"],
    },
    SlideType.TIMELINE: {
        "category": "sequence",
        "summary": "Stepwise timeline for phases, milestones, and execution sequencing.",
        "recommended_profiles": ["board", "consulting", "product", "proposal"],
    },
    SlideType.COMPARISON: {
        "category": "decision",
        "summary": "Side-by-side option comparison for trade-offs and recommendation framing.",
        "recommended_profiles": ["board", "consulting", "proposal"],
    },
    SlideType.TWO_COLUMN: {
        "category": "decision",
        "summary": "Two-panel narrative for current vs target state or left/right reasoning.",
        "recommended_profiles": ["consulting", "strategy", "proposal"],
    },
    SlideType.TABLE: {
        "category": "analytical",
        "summary": "Executive table for scoped workstreams, options, and structured commercial detail.",
        "recommended_profiles": ["consulting", "product", "proposal"],
    },
    SlideType.FAQ: {
        "category": "objection_handling",
        "summary": "FAQ/appendix format for common objections, operating questions, and leadership concerns.",
        "recommended_profiles": ["board", "consulting", "product", "proposal"],
    },
    SlideType.SUMMARY: {
        "category": "synthesis",
        "summary": "Executive synthesis with optional side panel and supporting visual.",
        "recommended_profiles": ["board", "consulting", "sales", "product", "proposal"],
    },
    SlideType.CLOSING: {
        "category": "close",
        "summary": "Closing slide for final recommendation, quote, or next-step framing.",
        "recommended_profiles": ["board", "consulting", "sales", "product", "proposal"],
    },
}


def get_layout_catalog(slide_type: str | SlideType) -> dict[str, object]:
    resolved_type = slide_type if isinstance(slide_type, SlideType) else SlideType(str(slide_type).strip().lower().replace("-", "_"))
    metadata = deepcopy(LAYOUT_CATALOG.get(resolved_type, {}))
    return {
        "type": resolved_type.value,
        "display_name": resolved_type.value.replace("_", " ").title(),
        "category": metadata.get("category"),
        "summary": metadata.get("summary"),
        "recommended_profiles": list(metadata.get("recommended_profiles", [])),
        "layout_variants": sorted(LAYOUT_VARIANTS_BY_SLIDE_TYPE.get(resolved_type, set())),
        "renderer_module": LAYOUT_RENDERERS[resolved_type].__module__.split(".")[-1],
    }


def list_layout_catalog() -> list[dict[str, object]]:
    return [get_layout_catalog(slide_type) for slide_type in SlideType]

__all__ = ["LAYOUT_RENDERERS", "LAYOUT_CATALOG", "LayoutRenderer", "get_layout_catalog", "list_layout_catalog"]
