from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ppt_creator_ai.briefing import BriefingInput


@dataclass(frozen=True)
class BriefingGenerationResult:
    provider_name: str
    payload: dict[str, object]
    analysis: dict[str, object]


@dataclass(frozen=True)
class DeckCritiqueResult:
    provider_name: str
    critiques: list[dict[str, object]]
    analysis: dict[str, object]


class BriefingProvider(Protocol):
    name: str
    description: str

    def generate(
        self,
        briefing: BriefingInput,
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> BriefingGenerationResult: ...

    def revise_generated_deck(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> BriefingGenerationResult: ...

    def critique_generated_deck(
        self,
        briefing: BriefingInput,
        current_payload: dict[str, object],
        review: dict[str, object],
        slide_critiques: list[dict[str, object]],
        *,
        theme_name: str | None = None,
        feedback_messages: list[str] | None = None,
    ) -> DeckCritiqueResult: ...
