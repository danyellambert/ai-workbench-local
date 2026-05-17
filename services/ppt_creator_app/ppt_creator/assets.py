from __future__ import annotations

from copy import deepcopy

ASSET_COLLECTIONS: dict[str, dict[str, object]] = {
    "boardroom_backdrops": {
        "display_name": "Boardroom Backdrops",
        "description": "Premium boardroom and leadership-meeting visuals suited to title/summary slides.",
        "visual_style": "Premium boardroom hero photography with strong negative space.",
        "composition_notes": "Prefer wide executive scenes with clean edges for cover typography and summary overlays.",
        "preferred_focal_point": {"x": 0.56, "y": 0.34},
        "queries": [
            "executive boardroom meeting wide shot",
            "premium leadership discussion background",
            "decision meeting with negative space",
        ],
        "preferred_layouts": ["title", "summary"],
        "recommended_profiles": ["board", "consulting"],
    },
    "executive_decision_moments": {
        "display_name": "Executive Decision Moments",
        "description": "Crisp decision-oriented visuals for recommendation, summary, and closing frames.",
        "visual_style": "Editorial leadership imagery centered on decision tension and alignment.",
        "composition_notes": "Keep subjects centered slightly above the fold and preserve whitespace for closing copy.",
        "preferred_focal_point": {"x": 0.52, "y": 0.38},
        "queries": [
            "executive decision moment meeting",
            "leadership alignment summary visual",
            "final recommendation boardroom scene",
        ],
        "preferred_layouts": ["summary", "closing", "comparison"],
        "recommended_profiles": ["board", "consulting", "sales"],
    },
    "sales_dashboards": {
        "display_name": "Sales Dashboards",
        "description": "Revenue, forecast, and pipeline visuals for metrics/chart-heavy commercial decks.",
        "visual_style": "Analytical commercial dashboard visuals with premium enterprise polish.",
        "composition_notes": "Favor dense but legible KPI surfaces with clear central signal clusters.",
        "preferred_focal_point": {"x": 0.50, "y": 0.42},
        "queries": [
            "sales dashboard pipeline review",
            "forecast review leadership meeting",
            "executive revenue KPI dashboard",
        ],
        "preferred_layouts": ["metrics", "chart", "summary"],
        "recommended_profiles": ["sales"],
    },
    "forecast_reviews": {
        "display_name": "Forecast Reviews",
        "description": "Commercial review imagery centered on weekly/quarterly forecast execution.",
        "visual_style": "Commercial operating-review scenes with forecast and pipeline framing.",
        "composition_notes": "Prefer meeting-table visuals or large forecast boards that support comparison/agenda slides.",
        "preferred_focal_point": {"x": 0.54, "y": 0.40},
        "queries": [
            "sales forecast review meeting",
            "pipeline governance workshop",
            "revenue operations meeting",
        ],
        "preferred_layouts": ["agenda", "comparison", "summary"],
        "recommended_profiles": ["sales"],
    },
    "product_mockups": {
        "display_name": "Product Mockups",
        "description": "Product UI, app mockup, and digital-workflow imagery for product roadmap decks.",
        "visual_style": "Clean product UI and digital workflow visuals with high legibility.",
        "composition_notes": "Prefer cropped product surfaces with clear hero modules and minimal clutter.",
        "preferred_focal_point": {"x": 0.48, "y": 0.44},
        "queries": [
            "product dashboard interface mockup",
            "software workflow screenshot style",
            "product planning board with digital prototype",
        ],
        "preferred_layouts": ["image_text", "table", "summary"],
        "recommended_profiles": ["product"],
    },
    "roadmap_workshops": {
        "display_name": "Roadmap Workshops",
        "description": "Planning-wall and roadmap-working-session imagery for timeline/strategy sequences.",
        "visual_style": "Workshop/documentary imagery focused on planning surfaces, sticky notes, and roadmap walls.",
        "composition_notes": "Use wide planning scenes where the roadmap artifact stays visually dominant.",
        "preferred_focal_point": {"x": 0.50, "y": 0.39},
        "queries": [
            "product roadmap workshop wall",
            "milestone planning session",
            "strategy roadmap sticky notes leadership team",
        ],
        "preferred_layouts": ["timeline", "agenda", "two_column"],
        "recommended_profiles": ["product", "consulting"],
    },
    "strategy_workshops": {
        "display_name": "Strategy Workshops",
        "description": "Structured offsite and strategy working-session imagery for consulting narratives.",
        "visual_style": "Structured strategy-session imagery with whiteboards, facilitation, and executive posture.",
        "composition_notes": "Prefer scenes that suggest contrast, sequencing, and prioritization without visual noise.",
        "preferred_focal_point": {"x": 0.52, "y": 0.40},
        "queries": [
            "executive strategy workshop offsite",
            "consulting team strategy whiteboard",
            "leadership prioritization session",
        ],
        "preferred_layouts": ["comparison", "two_column", "summary"],
        "recommended_profiles": ["consulting", "board"],
    },
    "team_alignment_sessions": {
        "display_name": "Team Alignment Sessions",
        "description": "Alignment and planning visuals suited to change, governance, and recommendation slides.",
        "visual_style": "Leadership alignment and governance visuals with calm, structured composition.",
        "composition_notes": "Favor scenes with balanced visual weight so FAQ and summary overlays remain readable.",
        "preferred_focal_point": {"x": 0.51, "y": 0.37},
        "queries": [
            "leadership alignment meeting",
            "team planning session executive style",
            "stakeholder workshop executive presentation",
        ],
        "preferred_layouts": ["agenda", "faq", "summary"],
        "recommended_profiles": ["consulting", "product", "sales"],
    },
}


def list_asset_collections() -> list[str]:
    return sorted(ASSET_COLLECTIONS)


def get_asset_collection(name: str) -> dict[str, object]:
    normalized = name.strip().lower().replace("-", "_")
    if normalized not in ASSET_COLLECTIONS:
        raise ValueError(f"Unknown asset collection: {name}")
    payload = deepcopy(ASSET_COLLECTIONS[normalized])
    payload["name"] = normalized
    return payload