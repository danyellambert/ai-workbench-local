from __future__ import annotations

from ppt_creator.layouts._column_panels import render_column_panels


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    render_column_panels(
        renderer,
        slide,
        slide_spec,
        columns=slide_spec.two_column_columns,
        heading_width=7.85,
        subtitle_width=6.75,
        panel_top=2.22,
        panel_height=3.56,
        gap=0.32,
        accent_mode="left",
        panel_padding=0.26,
        title_height=0.42,
        body_min_height=0.82,
        body_fixed_height=1.62,
        bullets_min_height=0.50,
        eyebrow_default="Executive narrative",
    )