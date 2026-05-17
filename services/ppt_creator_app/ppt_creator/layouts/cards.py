from __future__ import annotations

from ppt_creator.layouts._components import render_content_card


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    colors = renderer.theme.colors
    card_weights = [
        renderer.estimate_content_weight(
            title=card.title,
            body=card.body,
            footer=card.footer,
        )
        for card in slide_spec.cards
    ]
    dense_cards = any(weight >= 2.25 for weight in card_weights) or any(len(card.body) > 90 for card in slide_spec.cards)

    renderer.add_heading(
        slide,
        title=slide_spec.title or "",
        subtitle=slide_spec.subtitle,
        eyebrow=slide_spec.eyebrow,
        left=g.content_left,
        top=g.title_top,
        width=7.2,
    )

    top = 2.55
    gap = 0.28 if dense_cards else 0.35
    card_flexes = renderer.normalize_content_flexes(card_weights, min_flex=0.95, max_flex=1.25)

    card_bounds = renderer.build_named_panel_row_content_bounds(
        left=g.content_left,
        top=top,
        width=g.content_width,
        height=3.08 if dense_cards else 2.95,
        gap=gap,
        min_width=3.0,
        regions=[
            {"kind": f"card_{index + 1}", "min_width": 3.0, "flex": flex}
            for index, flex in enumerate(card_flexes)
        ],
    )

    for idx, card in enumerate(slide_spec.cards, start=1):
        panel_bounds = card_bounds[f"card_{idx}"]["panel"]
        render_content_card(
            renderer,
            slide,
            card=card,
            panel_bounds=panel_bounds,
            accent_color=colors.accent if idx == 2 else colors.navy,
            dense=dense_cards,
        )
