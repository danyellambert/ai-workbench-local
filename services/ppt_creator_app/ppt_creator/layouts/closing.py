from __future__ import annotations


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors
    asset = renderer.resolve_asset(slide_spec.image_path)

    renderer.add_accent_bar(slide, g.content_left, 0.98, 0.1, 4.95, color=colors.accent)

    title = slide_spec.title or ""
    if title:
        renderer.add_heading(
            slide,
            title=title,
            left=g.content_left + 0.43,
            top=1.12,
            width=g.content_width - 0.43,
            title_size=t.title_size + 2,
        )

    quote_text = slide_spec.quote or slide_spec.body or ""
    if not quote_text:
        return

    dense_quote = len(quote_text) > 190
    quote_left = g.content_left + 0.43
    quote_top = 2.55 if title else 1.9
    quote_width = min(g.content_width - 0.43, 8.6)
    quote_height = 2.55 if dense_quote else 2.15

    if asset:
        split_regions = renderer.build_named_columns(
            left=quote_left,
            width=g.content_width - 0.43,
            gap=0.34,
            regions=[
                {
                    "kind": "closing_quote",
                    "min_width": 5.5,
                    "target_share": renderer.estimate_content_weight(
                        title=title,
                        body=quote_text,
                        footer=slide_spec.attribution,
                    ),
                },
                {
                    "kind": "closing_visual",
                    "width": 3.25,
                    "min_width": 3.0,
                },
            ],
        )
        quote_left, quote_width = split_regions["closing_quote"]
        image_left, image_width = split_regions["closing_visual"]
        renderer.add_visual_slot(
            slide,
            slide_spec,
            left=image_left,
            top=quote_top - 0.15,
            width=image_width,
            height=3.25,
            accent_color=colors.accent,
            padding=0.22,
        )

    renderer.add_quote_block(
        slide,
        quote=quote_text,
        attribution=slide_spec.attribution,
        left=quote_left,
        top=quote_top,
        width=quote_width,
        height=quote_height,
    )
