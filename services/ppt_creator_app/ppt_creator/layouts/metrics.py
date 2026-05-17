from __future__ import annotations

from ppt_creator.layouts._components import render_metric_card


def _metric_dense(metric, weight: float) -> bool:
    return bool(
        weight >= 2.7
        or len(metric.label) > 28
        or (metric.detail and len(metric.detail) > 78)
    )


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    colors = renderer.theme.colors
    variant = renderer.resolve_layout_variant(slide_spec, "standard")
    default_eyebrow = slide_spec.eyebrow or "Key metrics"
    semantic = renderer.resolve_semantic_layout(slide_spec.type.value, slide_spec.layout_variant)

    renderer.add_heading(
        slide,
        title=slide_spec.title or "",
        subtitle=slide_spec.subtitle,
        eyebrow=default_eyebrow,
        left=g.content_left,
        top=semantic.heading_top,
        width=7.45 if variant == "standard" else 7.15,
        subtitle_width=6.9,
        slide_type=slide_spec.type.value,
        layout_variant=slide_spec.layout_variant,
    )

    metrics = slide_spec.metrics
    metric_weights = [
        renderer.estimate_content_weight(
            title=metric.label,
            body=metric.detail,
            footer=metric.trend,
            tag=metric.value,
        )
        for metric in metrics
    ]
    dense_deck = any(_metric_dense(metric, weight) for metric, weight in zip(metrics, metric_weights, strict=True))
    gap = 0.22 if dense_deck else 0.26
    left = g.content_left
    total_width = g.content_width
    top = semantic.panel_top if variant == "standard" else semantic.panel_top - 0.16
    panel_height = (3.08 if dense_deck else 2.92) if variant == "standard" else (2.42 if dense_deck else 2.30)
    metric_cards = renderer.build_named_panel_row_content_bounds(
        left=left,
        top=top,
        width=total_width,
        height=panel_height,
        gap=gap,
        padding=0.22 if dense_deck else 0.24,
        regions=[
            {
                "kind": f"metric_{idx + 1}",
                "min_width": 1.95,
                "target_share": weight,
                "max_width": 4.35 if len(metrics) <= 3 else 3.5,
            }
            for idx, weight in enumerate(metric_weights)
        ],
    )

    for idx, (metric, weight) in enumerate(zip(metrics, metric_weights, strict=True)):
        dense_metric = _metric_dense(metric, weight)
        panel_bounds = metric_cards[f"metric_{idx + 1}"]["panel"]
        render_metric_card(
            renderer,
            slide,
            metric=metric,
            panel_bounds=panel_bounds,
            accent_color=colors.navy if idx % 2 == 0 else colors.accent,
            variant=variant,
            dense=dense_metric,
        )
