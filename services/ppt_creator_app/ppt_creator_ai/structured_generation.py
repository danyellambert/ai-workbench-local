from __future__ import annotations

import json
import re

from ppt_creator.schema import PresentationInput
from ppt_creator_ai.briefing import (
    BriefingInput,
    _infer_narrative_archetype,
    assess_generated_payload_quality,
    build_llm_generation_contract,
    summarize_text_to_executive_bullets,
)


class DeckTextGenerationAdapter:
    _RUNTIME_NOISE_PREFIXES = (
        "load_backend:",
        "ggml_",
        "llama_",
        "common_",
        "main:",
        "build:",
        "system_info:",
        "sampler ",
        "generate:",
        "sched_reserve:",
        "print_info:",
        "load:",
    )

    def _prompt_specific_guidance(self, briefing: BriefingInput) -> list[str]:
        text = " ".join(
            filter(
                None,
                [
                    briefing.title,
                    briefing.subtitle,
                    briefing.audience,
                    briefing.objective,
                    briefing.context,
                    briefing.briefing_text,
                ],
            )
        ).lower()
        generic_titles = build_llm_generation_contract().get("quality_guardrails", {}).get(
            "avoid_generic_placeholder_titles",
            [],
        )
        archetype = _infer_narrative_archetype(text)
        guidance = [
            "Treat the briefing_text as the source of truth and reuse its nouns, storyline and requested sections in the slide titles.",
            "Do not return generic placeholder slide titles unless the briefing explicitly asks for them.",
            f"Placeholder titles to avoid: {', '.join(str(item) for item in generic_titles)}.",
            "Every non-agenda slide title should sound specific to the business problem or candidate story in the briefing.",
            "Keep the output in the same language as the briefing unless the briefing explicitly mixes languages.",
            "Do not emit renderer scaffolding, fake metadata, or placeholder copy such as Candidate Name, Executive lens, What matters, Key takeaways, Next actions, Theme, DECK, or PHOTO PLACEHOLDER.",
            "When the deck makes a strong claim about impact, capability or value, ground it in evidence-bearing content such as a case, metric, chart, comparison, timeline, table, or explicit operating detail.",
            "Avoid weak pseudo-metrics like High, Strong, Optimized, Accelerated, Alta or Otimizada when a stronger evidence format would be more credible.",
            f"Keep the narrative consistent with the dominant deck archetype implied by the briefing: {archetype}.",
        ]

        if any(keyword in text for keyword in ["interview", "candidate", "hiring", "ai engineer"]):
            guidance.extend(
                [
                    "This is a candidate/interview deck. Cover story, projects, technical depth, production/scalability, product/business partnership and explicit value to the company.",
                    "Good slide title patterns include: My story and value proposition; Most relevant AI projects; Technical depth + business view; The value I can generate.",
                ]
            )

        if any(keyword in text for keyword in ["board", "board of directors", "leadership team", "steerco"]):
            guidance.extend(
                [
                    "This is a board/executive deck. The cover title must name the initiative or decision, not the audience.",
                    "Never use audience-only titles like 'The board' or 'Board review' when the briefing clearly names a business initiative.",
                ]
            )

        if any(keyword in text for keyword in ["comparison", "options", "versus", "trade-off", "tradeoff"]):
            guidance.append("If the prompt asks for options or comparison, include a comparison slide with prompt-specific column titles.")
        if any(keyword in text for keyword in ["timeline", "rollout", "roadmap", "milestone", "quarter"]):
            guidance.append("If the prompt asks for sequencing or rollout, include a timeline slide with milestone-oriented language from the briefing.")
        if any(keyword in text for keyword in ["metrics", "metric", "kpi", "results", "measurable", "success"]):
            guidance.append("If the prompt asks for measurable results or success metrics, include metrics or chart slides instead of only bullet slides.")
        if any(keyword in text for keyword in ["risks", "faq", "objections", "concerns"]):
            guidance.append("If the prompt mentions risks, objections or FAQ, include a matching slide type rather than hiding the topic inside generic bullets.")

        return guidance

    def build_prompt(self, briefing: BriefingInput, *, theme_name: str | None = None) -> str:
        effective_theme = theme_name or briefing.theme
        briefing_payload = briefing.model_dump(mode="json")
        generation_contract = build_llm_generation_contract()
        prompt_specific_guidance = self._prompt_specific_guidance(briefing)
        return (
            "You are generating structured JSON for a PowerPoint deck renderer. "
            "Return only valid JSON with top-level keys 'presentation' and 'slides'. "
            "Do not wrap the result in markdown. Do not explain your reasoning. "
            "Use only these slide types: title, section, agenda, bullets, cards, metrics, chart, image_text, timeline, comparison, two_column, table, faq, summary, closing. "
            "Prefer concise executive slides and avoid overly dense content. "
            "The deck must be specific to the briefing and must not read like a generic placeholder template. "
            f"Use theme '{effective_theme}'.\n\n"
            "Generation contract JSON:\n"
            f"{json.dumps(generation_contract, ensure_ascii=False, indent=2)}\n\n"
            "Prompt-specific guidance:\n- "
            + "\n- ".join(prompt_specific_guidance)
            + "\n\n"
            "Structured briefing JSON:\n"
            f"{json.dumps(briefing_payload, ensure_ascii=False, indent=2)}\n\n"
            "Return a single JSON object now."
        )

    def _strip_runtime_noise(self, text: str) -> str:
        cleaned_lines = [
            line
            for line in text.splitlines()
            if not line.strip().startswith(self._RUNTIME_NOISE_PREFIXES)
        ]
        return "\n".join(cleaned_lines).strip()

    def _strip_prompt_echo(self, text: str, *, prompt: str | None = None) -> str:
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip()
        normalized_prompt = (prompt or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if normalized_prompt and normalized_text.startswith(normalized_prompt):
            return normalized_text[len(normalized_prompt) :].lstrip()
        return normalized_text

    def clean_model_output(self, text: str, *, prompt: str | None = None) -> str:
        cleaned = self._strip_prompt_echo(text, prompt=prompt)
        cleaned = self._strip_runtime_noise(cleaned)
        return cleaned.strip()

    def _json_extraction_failure_message(self, text: str, *, payload_label: str) -> str:
        has_payload_markers = any(
            marker in text
            for marker in (
                '"presentation"',
                '"slides"',
                '"slide_critiques"',
            )
        )
        unbalanced_curly = text.count("{") > text.count("}")
        unbalanced_square = text.count("[") > text.count("]")
        if has_payload_markers and (unbalanced_curly or unbalanced_square):
            return (
                f"Could not extract {payload_label} JSON from model output. "
                "The model appears to have started a JSON response but did not finish it before generation stopped. "
                "Consider increasing max_tokens, keeping temperature low, or using a stronger model."
            )
        return f"Could not extract {payload_label} JSON from model output"

    def build_revision_prompt(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> str:
        effective_theme = theme_name or briefing.theme
        review_summary = {
            "status": review.get("status"),
            "issue_count": review.get("issue_count"),
            "average_score": review.get("average_score"),
            "overflow_risk_count": review.get("overflow_risk_count"),
            "clipping_risk_count": review.get("clipping_risk_count"),
            "collision_risk_count": review.get("collision_risk_count"),
            "balance_warning_count": review.get("balance_warning_count"),
            "top_risk_slides": review.get("top_risk_slides"),
        }
        prompt = (
            "You are revising an existing presentation JSON after QA review. "
            "Return only valid JSON with top-level keys 'presentation' and 'slides'. "
            "Do not wrap the result in markdown. Do not explain your reasoning. "
            "Keep the output compatible with these slide types: title, section, agenda, bullets, cards, metrics, chart, image_text, timeline, comparison, two_column, table, faq, summary, closing. "
            "Preserve the overall storyline, but tighten dense slides, reduce clipping/collision risk, and improve executive readability. "
            "Rewrite weak titles, subtitles, and summary bullets into sharper executive language when needed. "
            "Replace generic placeholder titles with prompt-specific language taken from the briefing. "
            f"Use theme '{effective_theme}'.\n\n"
            "Structured briefing JSON:\n"
            f"{json.dumps(briefing.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            "Current presentation JSON:\n"
            f"{json.dumps(current_payload, ensure_ascii=False, indent=2)}\n\n"
            "QA review summary JSON:\n"
            f"{json.dumps(review_summary, ensure_ascii=False, indent=2)}\n\n"
            "Slide critique guidance JSON:\n"
            f"{json.dumps(slide_critiques[:8], ensure_ascii=False, indent=2)}\n\n"
        )
        if feedback_messages:
            prompt += "Additional revision guidance:\n- " + "\n- ".join(feedback_messages) + "\n\n"
        prompt += "Return a single revised JSON object now."
        return prompt

    def build_critique_prompt(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> str:
        effective_theme = theme_name or briefing.theme
        review_summary = {
            "status": review.get("status"),
            "issue_count": review.get("issue_count"),
            "average_score": review.get("average_score"),
            "overflow_risk_count": review.get("overflow_risk_count"),
            "clipping_risk_count": review.get("clipping_risk_count"),
            "collision_risk_count": review.get("collision_risk_count"),
            "balance_warning_count": review.get("balance_warning_count"),
            "top_risk_slides": review.get("top_risk_slides"),
        }
        prompt = (
            "You are critiquing an existing presentation JSON after QA review. "
            "Return only valid JSON with a top-level key 'slide_critiques'. "
            "Do not wrap the result in markdown. Do not explain your reasoning outside the JSON. "
            "For each risky slide, provide concise slide-by-slide critique that combines briefing intent, QA review, and visual/layout feedback. "
            "Each critique object should contain: slide_number, slide_type, title, risk_level, issues, rewrite_guidance, visual_guidance, executive_tone_guidance. "
            f"Use theme '{effective_theme}' as context.\n\n"
            "Structured briefing JSON:\n"
            f"{json.dumps(briefing.model_dump(mode='json'), ensure_ascii=False, indent=2)}\n\n"
            "Current presentation JSON:\n"
            f"{json.dumps(current_payload, ensure_ascii=False, indent=2)}\n\n"
            "QA review summary JSON:\n"
            f"{json.dumps(review_summary, ensure_ascii=False, indent=2)}\n\n"
            "Existing heuristic slide critiques JSON:\n"
            f"{json.dumps(slide_critiques[:8], ensure_ascii=False, indent=2)}\n\n"
        )
        if feedback_messages:
            prompt += "Additional visual/QA guidance:\n- " + "\n- ".join(feedback_messages) + "\n\n"
        prompt += "Return a single JSON object with the slide critiques now."
        return prompt

    def validate_generated_payload(
        self,
        normalized_payload: dict[str, object],
        briefing: BriefingInput,
        *,
        theme_name: str | None = None,
        fallback_payload: dict[str, object] | None = None,
    ) -> tuple[PresentationInput, bool, str | None]:
        try:
            spec = PresentationInput.model_validate(normalized_payload)
            quality = assess_generated_payload_quality(spec.model_dump(mode="json"), briefing)
            if quality["should_fallback"]:
                reason = "; ".join(str(problem) for problem in quality["problems"]) or "quality gate fallback"
                raise ValueError(reason)
            return spec, False, None
        except Exception as exc:
            raise ValueError(str(exc)) from exc

    def build_presentation_meta(
        self,
        presentation_payload: dict[str, object],
        briefing: BriefingInput,
        *,
        theme_name: str | None = None,
        title_slide_data: dict[str, object] | None = None,
    ) -> dict[str, object]:
        title_data = title_slide_data or {}
        client_name = (
            presentation_payload.get("client_name")
            or title_data.get("client_name")
            or briefing.client_name
        )
        return {
            "title": presentation_payload.get("title") or title_data.get("title") or briefing.title,
            "subtitle": presentation_payload.get("subtitle") or title_data.get("subtitle") or briefing.subtitle,
            "author": presentation_payload.get("author") or title_data.get("author") or briefing.author,
            "date": presentation_payload.get("date") or title_data.get("date") or briefing.date,
            "theme": theme_name or briefing.theme,
            "client_name": client_name,
            "footer_text": presentation_payload.get("footer_text")
            or (f"{client_name} • Briefing deck" if client_name else None),
        }

    def _coerce_text(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        cleaned = str(value).strip()
        return cleaned or None

    def _coerce_bullets(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[\n;•]+", value) if item.strip()]
        bullets: list[str] = []
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    cleaned = item.strip()
                    if cleaned:
                        bullets.append(cleaned)
                    continue
                if isinstance(item, dict):
                    cleaned = self._coerce_text(
                        item.get("title")
                        or item.get("label")
                        or item.get("body")
                        or item.get("content")
                        or item.get("value")
                    )
                    if cleaned:
                        bullets.append(cleaned)
        return bullets

    def _normalize_card_items(self, raw_items: object) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        if not isinstance(raw_items, list):
            return items
        for index, item in enumerate(raw_items, start=1):
            if isinstance(item, str):
                cleaned = self._coerce_text(item)
                if cleaned:
                    items.append({"title": f"Point {index}", "body": cleaned})
                continue
            if not isinstance(item, dict):
                continue
            title = self._coerce_text(item.get("title") or item.get("label") or item.get("heading")) or f"Card {index}"
            body = self._coerce_text(
                item.get("body")
                or item.get("subtitle")
                or item.get("content")
                or item.get("value")
                or item.get("detail")
            )
            footer = self._coerce_text(item.get("footer") or item.get("tag") or item.get("trend"))
            if not body:
                bullet_fallback = "; ".join(self._coerce_bullets(item.get("items") or item.get("bullets")))
                body = self._coerce_text(bullet_fallback)
            if body:
                payload = {"title": title, "body": body}
                if footer:
                    payload["footer"] = footer
                items.append(payload)
        return items

    def _normalize_metric_items(self, raw_items: object) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        if not isinstance(raw_items, list):
            return items
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            value = self._coerce_text(item.get("value") or item.get("metric") or item.get("number") or item.get("figure"))
            label = self._coerce_text(item.get("label") or item.get("title") or item.get("name"))
            detail = self._coerce_text(item.get("detail") or item.get("subtitle") or item.get("body") or item.get("content"))
            trend = self._coerce_text(item.get("trend") or item.get("footer") or item.get("delta"))
            if value and label:
                payload = {"value": value, "label": label}
                if detail:
                    payload["detail"] = detail
                if trend:
                    payload["trend"] = trend
                items.append(payload)
        return items

    def _normalize_timeline_items(self, raw_items: object) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        if not isinstance(raw_items, list):
            return items
        for index, item in enumerate(raw_items, start=1):
            if isinstance(item, str):
                cleaned = self._coerce_text(item)
                if cleaned:
                    items.append({"title": cleaned, "body": cleaned})
                continue
            if not isinstance(item, dict):
                continue
            title = self._coerce_text(
                item.get("title")
                or item.get("milestone")
                or item.get("step")
                or item.get("phase")
                or item.get("name")
            ) or f"Step {index}"
            body = self._coerce_text(item.get("body") or item.get("detail") or item.get("description") or item.get("content"))
            tag = self._coerce_text(item.get("tag") or item.get("phase"))
            footer = self._coerce_text(item.get("footer") or item.get("date") or item.get("duration"))
            payload: dict[str, object] = {"title": title}
            if body:
                payload["body"] = body
            if tag and tag != title:
                payload["tag"] = tag
            if footer and footer != title:
                payload["footer"] = footer
            items.append(payload)
        return items

    def _normalize_comparison_columns(self, raw_columns: object) -> list[dict[str, object]]:
        columns: list[dict[str, object]] = []
        if not isinstance(raw_columns, list):
            return columns
        for index, item in enumerate(raw_columns, start=1):
            if isinstance(item, str):
                cleaned = self._coerce_text(item)
                if cleaned:
                    columns.append({"title": f"Option {index}", "body": cleaned})
                continue
            if not isinstance(item, dict):
                continue
            title = self._coerce_text(
                item.get("title")
                or item.get("label")
                or item.get("column")
                or item.get("header")
                or item.get("name")
            ) or f"Option {index}"
            body = self._coerce_text(
                item.get("body")
                or item.get("content")
                or item.get("value")
                or item.get("description")
            )
            bullets = self._coerce_bullets(item.get("bullets") or item.get("items"))
            footer = self._coerce_text(item.get("footer") or item.get("summary") or item.get("evidence"))
            tag = self._coerce_text(item.get("tag") or item.get("phase"))
            if body or bullets:
                payload: dict[str, object] = {"title": title}
                if body:
                    payload["body"] = body
                if bullets:
                    payload["bullets"] = bullets
                if footer:
                    payload["footer"] = footer
                if tag:
                    payload["tag"] = tag
                columns.append(payload)
        return columns

    def _columns_to_cards(self, columns: list[dict[str, object]]) -> list[dict[str, object]]:
        cards: list[dict[str, object]] = []
        for index, column in enumerate(columns[:3], start=1):
            body = self._coerce_text(column.get("body")) or "; ".join(self._coerce_bullets(column.get("bullets")))
            if not body:
                continue
            payload = {
                "title": self._coerce_text(column.get("title")) or f"Point {index}",
                "body": body,
            }
            footer = self._coerce_text(column.get("footer") or column.get("tag"))
            if footer:
                payload["footer"] = footer
            cards.append(payload)
        return cards

    def _normalize_faq_items(self, raw_items: object) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        if not isinstance(raw_items, list):
            return items
        for item in raw_items:
            if isinstance(item, str):
                cleaned = self._coerce_text(item)
                if cleaned:
                    items.append({"title": cleaned, "body": cleaned})
                continue
            if not isinstance(item, dict):
                continue
            title = self._coerce_text(item.get("title") or item.get("question") or item.get("label"))
            body = self._coerce_text(item.get("body") or item.get("answer") or item.get("content"))
            if title and body:
                items.append({"title": title, "body": body})
        return items

    def normalize_slide_payload(self, slide_payload: dict[str, object], briefing: BriefingInput) -> dict[str, object]:
        slide_kind = str(slide_payload.get("slide") or slide_payload.get("type") or "").strip().lower()
        slide_kind = slide_kind.replace("-", "_").replace(" ", "_")
        data = slide_payload.get("data") if isinstance(slide_payload.get("data"), dict) else slide_payload
        content = data.get("content") or data.get("body")
        fallback_bullets = summarize_text_to_executive_bullets(
            content if isinstance(content, str) else None,
            max_bullets=4,
            max_words=10,
        )

        def bullets_slide(title: str | None) -> dict[str, object]:
            return {
                "type": "bullets",
                "title": title or "Key points",
                "body": content if isinstance(content, str) else None,
                "bullets": fallback_bullets,
            }

        if slide_kind == "title":
            return {
                "type": "title",
                "title": data.get("title"),
                "subtitle": data.get("subtitle"),
                "body": data.get("body"),
            }
        if slide_kind == "section":
            title = data.get("section") or data.get("title") or "Section"
            if content:
                return {"type": "bullets", "title": title, "body": content}
            return {"type": "section", "title": title, "section_label": "Section"}
        if slide_kind == "agenda":
            agenda_bullets = self._coerce_bullets(data.get("bullets") or data.get("items")) or list(briefing.outline[:6])
            return {"type": "agenda", "title": data.get("title") or "Agenda", "bullets": agenda_bullets[:6] or fallback_bullets[:6]}
        if slide_kind == "bullets":
            return {
                "type": "bullets",
                "title": data.get("title") or "Key points",
                "body": content if isinstance(content, str) else None,
                "bullets": self._coerce_bullets(data.get("bullets"))[:6] or fallback_bullets[:6],
            }
        if slide_kind == "cards":
            cards = self._normalize_card_items(data.get("cards") or data.get("items") or [])
            if len(cards) >= 3:
                return {"type": "cards", "title": data.get("title") or "Cards", "cards": cards[:3]}
            return bullets_slide(data.get("title") or "Cards")
        if slide_kind == "metrics":
            metrics = self._normalize_metric_items(data.get("metrics")) or [metric.model_dump(mode="json") for metric in briefing.metrics[:4]]
            if metrics:
                return {"type": "metrics", "title": data.get("title") or "Headline metrics", "metrics": metrics[:4]}
            return bullets_slide(data.get("title") or "Headline metrics")
        if slide_kind == "chart":
            chart_categories = data.get("chart_categories") or data.get("categories") or []
            chart_series = data.get("chart_series") or data.get("series") or []
            if chart_categories and chart_series:
                return {
                    "type": "chart",
                    "title": data.get("title") or "Chart",
                    "chart_categories": chart_categories,
                    "chart_series": chart_series,
                }
            return bullets_slide(data.get("title") or "Chart")
        if slide_kind == "image_text":
            return {
                "type": "image_text",
                "title": data.get("title") or "Image",
                "body": content if isinstance(content, str) else None,
                "bullets": self._coerce_bullets(data.get("bullets"))[:6] or fallback_bullets[:6],
                "image_path": data.get("image_path"),
                "image_caption": data.get("image_caption") or data.get("caption"),
            }
        if slide_kind in {"timeline", "milestones"}:
            raw_items = data.get("timeline_items") or data.get("milestones") or [milestone.model_dump(mode="json") for milestone in briefing.milestones[:5]]
            timeline_items = self._normalize_timeline_items(raw_items)[:5]
            if len(timeline_items) < 2:
                return bullets_slide(data.get("title") or "Execution timeline")
            return {"type": "timeline", "title": data.get("title") or "Execution timeline", "timeline_items": timeline_items}
        if slide_kind == "comparison":
            comparison_columns = self._normalize_comparison_columns(data.get("comparison_columns") or data.get("columns")) or [option.model_dump(mode="json") for option in briefing.options[:2]]
            if len(comparison_columns) == 2:
                return {"type": "comparison", "title": data.get("title") or "Comparison", "comparison_columns": comparison_columns}
            if len(comparison_columns) >= 3:
                cards = self._columns_to_cards(comparison_columns)
                if len(cards) == 3:
                    return {"type": "cards", "title": data.get("title") or "Comparison", "cards": cards}
            return bullets_slide(data.get("title") or "Comparison")
        if slide_kind == "two_column":
            two_column_columns = self._normalize_comparison_columns(data.get("two_column_columns") or data.get("columns")) or [option.model_dump(mode="json") for option in briefing.options[:2]]
            if len(two_column_columns) == 2:
                return {"type": "two_column", "title": data.get("title") or "Two column", "two_column_columns": two_column_columns}
            if len(two_column_columns) >= 3:
                cards = self._columns_to_cards(two_column_columns)
                if len(cards) == 3:
                    return {"type": "cards", "title": data.get("title") or "Two column", "cards": cards}
            return bullets_slide(data.get("title") or "Two column")
        if slide_kind == "table":
            table_columns = data.get("table_columns") or data.get("columns") or []
            table_rows = data.get("table_rows") or data.get("rows") or []
            if (not table_columns or not table_rows) and briefing.metrics:
                table_columns = ["Metric", "Value", "Trend"]
                table_rows = [[metric.label, metric.value, metric.trend or ""] for metric in briefing.metrics[:6]]
            if len(table_columns) < 2 or not table_rows:
                return bullets_slide(data.get("title") or "Table")
            normalized_columns = list(table_columns)[:5]
            return {
                "type": "table",
                "title": data.get("title") or "Table",
                "table_columns": normalized_columns,
                "table_rows": [list(row)[: len(normalized_columns)] for row in table_rows[:8]],
            }
        if slide_kind in {"faq", "faqs"}:
            raw_items = data.get("faq_items") or data.get("faqs") or [{"question": faq.question, "answer": faq.answer} for faq in briefing.faqs[:4]]
            faq_items = self._normalize_faq_items(raw_items)[:4]
            if len(faq_items) < 2:
                return bullets_slide(data.get("title") or "Executive FAQ")
            return {"type": "faq", "title": data.get("title") or "Executive FAQ", "faq_items": faq_items}
        if slide_kind == "summary":
            return {
                "type": "summary",
                "title": data.get("title") or "Executive summary",
                "body": data.get("content") or data.get("body"),
                "bullets": self._coerce_bullets(data.get("bullets"))[:6],
            }
        if slide_kind == "closing":
            return {
                "type": "closing",
                "title": data.get("title") or "Closing thought",
                "quote": data.get("closing_quote") or data.get("quote") or data.get("content"),
            }
        raise ValueError(f"Unsupported slide payload from local model: {slide_kind or 'unknown'}")

    def normalize_generated_payload(
        self,
        payload: dict[str, object],
        briefing: BriefingInput,
        *,
        theme_name: str | None = None,
    ) -> dict[str, object]:
        if "presentation" in payload and "slides" in payload:
            presentation_payload = payload.get("presentation")
            slides_payload = payload.get("slides")
        elif isinstance(payload.get("presentation"), dict) and isinstance(payload["presentation"].get("slides"), list):
            presentation_payload = payload.get("presentation")
            slides_payload = payload["presentation"].get("slides")
        else:
            raise ValueError("Model output did not contain a recognizable presentation/slides payload")

        presentation_dict = presentation_payload if isinstance(presentation_payload, dict) else {}
        slides_list = slides_payload if isinstance(slides_payload, list) else []
        title_slide_data = next(
            (
                item.get("data")
                for item in slides_list
                if isinstance(item, dict)
                and str(item.get("slide") or item.get("type") or "").strip().lower().replace("-", "_") == "title"
                and isinstance(item.get("data"), dict)
            ),
            None,
        )

        normalized_slides = [
            self.normalize_slide_payload(item, briefing)
            for item in slides_list
            if isinstance(item, dict)
        ]
        if not normalized_slides or normalized_slides[0].get("type") != "title":
            normalized_slides.insert(
                0,
                {
                    "type": "title",
                    "title": briefing.title,
                    "subtitle": briefing.subtitle,
                    "body": briefing.objective,
                },
            )

        return {
            "presentation": self.build_presentation_meta(
                presentation_dict,
                briefing,
                theme_name=theme_name,
                title_slide_data=title_slide_data,
            ),
            "slides": normalized_slides,
        }

    def extract_json_payload(self, text: str, *, prompt: str | None = None) -> dict[str, object]:
        cleaned_text = self.clean_model_output(text, prompt=prompt)
        decoder = json.JSONDecoder()
        for index, char in enumerate(cleaned_text):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(cleaned_text[index:])
            except json.JSONDecodeError:
                continue
            if not isinstance(candidate, dict) or "presentation" not in candidate:
                continue
            if "slides" in candidate:
                return candidate
            presentation_payload = candidate.get("presentation")
            if isinstance(presentation_payload, dict) and "slides" in presentation_payload:
                return candidate
        raise ValueError(self._json_extraction_failure_message(cleaned_text, payload_label="presentation"))

    def extract_slide_critiques_payload(self, text: str, *, prompt: str | None = None) -> list[dict[str, object]]:
        cleaned_text = self.clean_model_output(text, prompt=prompt)
        decoder = json.JSONDecoder()
        for index, char in enumerate(cleaned_text):
            if char != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(cleaned_text[index:])
            except json.JSONDecodeError:
                continue
            critiques = candidate.get("slide_critiques") if isinstance(candidate, dict) else None
            if isinstance(critiques, list):
                return [item for item in critiques if isinstance(item, dict)]
        raise ValueError(self._json_extraction_failure_message(cleaned_text, payload_label="slide critique"))

    def normalize_slide_critiques(
        self,
        critiques: list[dict[str, object]],
        *,
        fallback_slide_critiques: list[dict[str, object]],
        max_critiques: int = 8,
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for item in critiques[:max_critiques]:
            slide_number = item.get("slide_number")
            if not isinstance(slide_number, int):
                continue
            normalized.append(
                {
                    "slide_number": slide_number,
                    "slide_type": str(item.get("slide_type") or "slide"),
                    "title": str(item.get("title") or f"Slide {slide_number:02d}"),
                    "risk_level": str(item.get("risk_level") or "medium"),
                    "issues": [str(issue) for issue in (item.get("issues") or []) if str(issue).strip()][:4],
                    "rewrite_guidance": [str(guidance) for guidance in (item.get("rewrite_guidance") or []) if str(guidance).strip()][:4],
                    "visual_guidance": [str(guidance) for guidance in (item.get("visual_guidance") or []) if str(guidance).strip()][:4],
                    "executive_tone_guidance": [str(guidance) for guidance in (item.get("executive_tone_guidance") or []) if str(guidance).strip()][:4],
                }
            )
        return normalized or fallback_slide_critiques[:max_critiques]
