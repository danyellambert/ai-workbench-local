from __future__ import annotations

from ppt_creator_ai.briefing import (
    BriefingInput,
    build_briefing_analysis,
    generate_presentation_payload_from_briefing,
)
from ppt_creator_ai.providers.base import BriefingGenerationResult, DeckCritiqueResult
from ppt_creator_ai.refine import refine_presentation_payload


class HeuristicBriefingProvider:
    name = "heuristic"
    description = "Rule-based provider that generates deck JSON and analysis without external LLM calls."

    def generate(
        self,
        briefing: BriefingInput,
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> BriefingGenerationResult:
        payload = generate_presentation_payload_from_briefing(
            briefing,
            theme_name=theme_name,
            feedback_messages=feedback_messages,
        )
        analysis = build_briefing_analysis(
            briefing,
            theme_name=theme_name,
            feedback_messages=feedback_messages,
        )
        return BriefingGenerationResult(
            provider_name=self.name,
            payload=payload,
            analysis=analysis,
        )

    def revise_generated_deck(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> BriefingGenerationResult:
        payload = refine_presentation_payload(
            current_payload,
            review=review,
            briefing=briefing,
            slide_critiques=slide_critiques,
        )
        analysis = build_briefing_analysis(
            briefing,
            theme_name=theme_name,
            feedback_messages=feedback_messages,
        )
        analysis.update(
            {
                "provider": self.name,
                "revision_mode": "heuristic_review",
                "source_issue_count": review.get("issue_count"),
                "slide_critique_count": len(slide_critiques),
            }
        )
        return BriefingGenerationResult(
            provider_name=self.name,
            payload=payload,
            analysis=analysis,
        )

    def critique_generated_deck(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> DeckCritiqueResult:
        return DeckCritiqueResult(
            provider_name=self.name,
            critiques=slide_critiques,
            analysis={
                "provider": self.name,
                "critique_mode": "heuristic_slide_critique",
                "feedback_messages": feedback_messages or [],
                "fallback_used": True,
                "critique_count": len(slide_critiques),
            },
        )
