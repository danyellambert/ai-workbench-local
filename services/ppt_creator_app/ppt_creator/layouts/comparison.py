from __future__ import annotations

from ppt_creator.layouts._column_panels import render_column_panels


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    render_column_panels(
        renderer,
        slide,
        slide_spec,
        columns=slide_spec.comparison_columns,
        heading_width=7.85,
        subtitle_width=6.9,
        panel_height=3.52,
        gap=0.32,
        accent_mode="top",
        panel_max_width=5.18,
        panel_padding=0.28,
        body_min_height=0.76,
        body_fixed_height=1.56,
        bullets_min_height=0.50,
        eyebrow_default="Strategic comparison",
    )