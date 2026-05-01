from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ppt_creator.schema import PresentationInput
from ppt_creator_ai.briefing import _infer_narrative_archetype, _infer_prompt_language

if TYPE_CHECKING:
    from ppt_creator_ai.briefing import BriefingInput


_GENERIC_TITLE_KEYS = {
    "agenda",
    "executive summary",
    "summary",
    "closing",
    "closing thought",
    "recommendation",
    "key points",
    "headline metrics",
    "metrics",
    "comparison",
    "two column",
    "two column narrative",
    "table",
    "executive table",
    "faq",
    "executive faq",
}


def _normalize_title_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower()).strip()


def _shorten_words(value: str | None, *, max_words: int) -> str | None:
    if not value:
        return value
    words = value.split()
    if len(words) <= max_words:
        return value.strip()
    return " ".join(words[:max_words]).rstrip(" ,;:.!?") + "..."


def _shorten_list(values: list[str], *, max_items: int, max_words: int) -> list[str]:
    return [_shorten_words(value, max_words=max_words) or "" for value in values[:max_items]]


def _briefing_language(briefing: "BriefingInput" | None) -> str:
    if briefing is None:
        return "en"
    return _infer_prompt_language(
        " ".join(
            part
            for part in [
                briefing.title,
                briefing.subtitle,
                briefing.audience,
                briefing.objective,
                briefing.context,
                briefing.briefing_text,
            ]
            if part
        )
    )


def _briefing_archetype(briefing: "BriefingInput" | None) -> str:
    if briefing is None:
        return "decision"
    return _infer_narrative_archetype(
        " ".join(
            part
            for part in [
                briefing.title,
                briefing.subtitle,
                briefing.audience,
                briefing.objective,
                briefing.context,
                briefing.briefing_text,
            ]
            if part
        )
    )


def _briefing_seed(briefing: "BriefingInput" | None, *, max_words: int = 6) -> str | None:
    if briefing is None:
        return None
    source = briefing.title or briefing.objective or briefing.context or briefing.briefing_text
    return _shorten_words(source, max_words=max_words)


def _first_briefing_recommendation(briefing: "BriefingInput" | None, *, max_words: int = 18) -> str | None:
    if briefing is None:
        return None
    source = (
        (briefing.recommendations[0] if briefing.recommendations else None)
        or briefing.objective
        or briefing.context
        or briefing.title
    )
    return _shorten_words(source, max_words=max_words)


def _suggest_executive_title(
    *,
    slide_type: str,
    briefing: "BriefingInput" | None,
    language: str,
    narrative_archetype: str,
) -> str | None:
    seed = _briefing_seed(briefing)
    if slide_type == "agenda":
        return "Decision agenda"
    if slide_type == "metrics":
        return "Metrics that matter"
    if slide_type == "comparison":
        return "Decision trade-offs"
    if slide_type == "two_column":
        return "Recommendation lenses"
    if slide_type == "table":
        return "Executive decision table"
    if slide_type == "faq":
        return "Risks and objections"
    if slide_type == "summary":
        return "Final recommendation"
    if slide_type == "closing":
        if seed:
            return f"Next move: {seed}"
        return "Next move"
    if slide_type in {"bullets", "image_text"}:
        if narrative_archetype == "proposal":
            return "Why this approach"
        if seed:
            return seed
        return "Context that matters"
    return seed


def _rewrite_generic_title(
    current_title: str | None,
    *,
    slide_type: str,
    briefing: "BriefingInput" | None,
    language: str,
    narrative_archetype: str,
) -> str | None:
    if briefing is None:
        return current_title
    normalized = _normalize_title_key(current_title)
    if normalized and normalized not in _GENERIC_TITLE_KEYS:
        return current_title
    return _suggest_executive_title(
        slide_type=slide_type,
        briefing=briefing,
        language=language,
        narrative_archetype=narrative_archetype,
    ) or current_title


def _rewrite_body_copy(
    *,
    slide_type: str,
    current_body: str | None,
    briefing: "BriefingInput" | None,
    language: str,
) -> str | None:
    preferred = _first_briefing_recommendation(briefing)
    if preferred is None:
        return current_body
    normalized_body = (current_body or "").strip().lower()
    if slide_type == "agenda" and (not normalized_body or normalized_body in {"dense intro", "intro", "agenda"}):
        return "Executive path from context to the final recommendation."
    if slide_type == "summary" and (not normalized_body or len(normalized_body.split()) <= 5):
        return preferred
    if slide_type in {"bullets", "image_text"} and (not normalized_body or normalized_body in {"generic", "generic intro", "dense intro"}):
        return preferred
    return current_body


def _rewrite_closing_quote(
    current_quote: str | None,
    *,
    briefing: "BriefingInput" | None,
    language: str,
) -> str | None:
    preferred = _first_briefing_recommendation(briefing, max_words=20)
    normalized_quote = (current_quote or "").strip().lower()
    if preferred is None:
        return current_quote
    if not normalized_quote or normalized_quote in {"done.", "done", "generic close.", "generic close"}:
        return f"The best next move is this: {preferred}"
    return current_quote


def _refine_columns(columns: list[dict[str, object]]) -> list[dict[str, object]]:
    refined: list[dict[str, object]] = []
    for column in columns[:2]:
        updated = dict(column)
        updated["title"] = _shorten_words(str(column.get("title") or ""), max_words=7) or column.get("title")
        updated["body"] = _shorten_words(column.get("body") if isinstance(column.get("body"), str) else None, max_words=26)
        updated["bullets"] = _shorten_list(
            [str(item) for item in column.get("bullets", []) if isinstance(item, str)],
            max_items=3,
            max_words=10,
        )
        updated["footer"] = _shorten_words(column.get("footer") if isinstance(column.get("footer"), str) else None, max_words=8)
        updated["tag"] = _shorten_words(column.get("tag") if isinstance(column.get("tag"), str) else None, max_words=5)
        refined.append(updated)
    return refined


def _refine_table(slide: dict[str, object]) -> None:
    slide["table_columns"] = _shorten_list(
        [str(item) for item in slide.get("table_columns", []) if isinstance(item, str)],
        max_items=4,
        max_words=4,
    )
    rows = slide.get("table_rows", [])
    if not isinstance(rows, list):
        return
    max_cols = len(slide.get("table_columns", [])) or 4
    slide["table_rows"] = [
        [_shorten_words(str(cell), max_words=5) or "" for cell in row[:max_cols]]
        for row in rows[:6]
        if isinstance(row, list)
    ]


def _refine_cards(items: list[dict[str, object]], *, max_items: int) -> list[dict[str, object]]:
    refined: list[dict[str, object]] = []
    for item in items[:max_items]:
        updated = dict(item)
        updated["title"] = _shorten_words(str(item.get("title") or ""), max_words=8) or item.get("title")
        updated["body"] = _shorten_words(item.get("body") if isinstance(item.get("body"), str) else None, max_words=24)
        if "footer" in updated:
            updated["footer"] = _shorten_words(updated.get("footer") if isinstance(updated.get("footer"), str) else None, max_words=8)
        if "tag" in updated:
            updated["tag"] = _shorten_words(updated.get("tag") if isinstance(updated.get("tag"), str) else None, max_words=5)
        refined.append(updated)
    return refined


def refine_presentation_payload(
    payload: dict[str, object],
    *,
    review: dict[str, object] | None = None,
    briefing: "BriefingInput" | None = None,
    slide_critiques: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    updated_payload = {
        "presentation": dict(payload.get("presentation") or {}),
        "slides": [dict(slide) for slide in (payload.get("slides") or []) if isinstance(slide, dict)],
    }
    review_lookup = {
        int(slide_review["slide_number"]): slide_review
        for slide_review in (review or {}).get("slides", [])
    }
    critique_lookup = {
        int(slide_critique["slide_number"]): slide_critique
        for slide_critique in (slide_critiques or [])
        if isinstance(slide_critique, dict) and isinstance(slide_critique.get("slide_number"), int)
    }
    language = _briefing_language(briefing)
    narrative_archetype = _briefing_archetype(briefing)

    for index, slide in enumerate(updated_payload["slides"], start=1):
        slide_review = review_lookup.get(index, {})
        slide_critique = critique_lookup.get(index, {})
        risk_level = str(slide_review.get("risk_level") or "low")

        if risk_level in {"medium", "high"}:
            slide_type = str(slide.get("type") or "")
            slide["title"] = _rewrite_generic_title(
                _shorten_words(slide.get("title") if isinstance(slide.get("title"), str) else None, max_words=12),
                slide_type=slide_type,
                briefing=briefing,
                language=language,
                narrative_archetype=narrative_archetype,
            )
            slide["subtitle"] = _shorten_words(
                slide.get("subtitle") if isinstance(slide.get("subtitle"), str) else None,
                max_words=18,
            )
            if slide_critique.get("executive_tone_guidance") and not slide.get("subtitle"):
                guidance = slide_critique.get("executive_tone_guidance") or []
                if guidance:
                    slide["subtitle"] = _shorten_words(str(guidance[0]), max_words=14)

        slide_type = str(slide.get("type") or "")
        if slide_type in {"agenda", "bullets", "image_text", "summary"}:
            shortened_body = _shorten_words(slide.get("body") if isinstance(slide.get("body"), str) else None, max_words=30)
            slide["body"] = _rewrite_body_copy(
                slide_type=slide_type,
                current_body=shortened_body,
                briefing=briefing,
                language=language,
            )
            slide["bullets"] = _shorten_list(
                [str(item) for item in slide.get("bullets", []) if isinstance(item, str)],
                max_items=4,
                max_words=10,
            )

        if slide_type == "cards":
            slide["cards"] = _refine_cards(
                [item for item in slide.get("cards", []) if isinstance(item, dict)],
                max_items=3,
            )

        if slide_type == "metrics":
            metrics = []
            for metric in [item for item in slide.get("metrics", []) if isinstance(item, dict)][:4]:
                updated = dict(metric)
                updated["label"] = _shorten_words(str(metric.get("label") or ""), max_words=5) or metric.get("label")
                updated["detail"] = _shorten_words(metric.get("detail") if isinstance(metric.get("detail"), str) else None, max_words=16)
                updated["trend"] = _shorten_words(metric.get("trend") if isinstance(metric.get("trend"), str) else None, max_words=6)
                metrics.append(updated)
            slide["metrics"] = metrics

        if slide_type == "timeline":
            slide["timeline_items"] = _refine_cards(
                [item for item in slide.get("timeline_items", []) if isinstance(item, dict)],
                max_items=4,
            )

        if slide_type in {"comparison", "two_column"}:
            key = "comparison_columns" if slide_type == "comparison" else "two_column_columns"
            slide[key] = _refine_columns([item for item in slide.get(key, []) if isinstance(item, dict)])

        if slide_type == "table":
            _refine_table(slide)

        if slide_type == "faq":
            slide["faq_items"] = _refine_cards(
                [item for item in slide.get("faq_items", []) if isinstance(item, dict)],
                max_items=3,
            )

        if slide_type == "chart":
            slide["body"] = _shorten_words(slide.get("body") if isinstance(slide.get("body"), str) else None, max_words=24)
            slide["chart_categories"] = [str(item) for item in slide.get("chart_categories", [])[:6] if isinstance(item, str)]
            slide["chart_series"] = [item for item in slide.get("chart_series", [])[:3] if isinstance(item, dict)]

        if slide_type == "closing":
            shortened_quote = _shorten_words(slide.get("quote") if isinstance(slide.get("quote"), str) else None, max_words=24)
            slide["quote"] = _rewrite_closing_quote(
                shortened_quote,
                briefing=briefing,
                language=language,
            )

    return updated_payload


def refine_presentation_input(
    spec: PresentationInput,
    *,
    review: dict[str, object] | None = None,
    briefing: "BriefingInput" | None = None,
    slide_critiques: list[dict[str, object]] | None = None,
) -> PresentationInput:
    refined_payload = refine_presentation_payload(
        spec.model_dump(mode="json"),
        review=review,
        briefing=briefing,
        slide_critiques=slide_critiques,
    )
    return PresentationInput.model_validate(refined_payload)
