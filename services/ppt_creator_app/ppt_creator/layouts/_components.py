from __future__ import annotations

from ppt_creator.schema import CardItem, MetricItem


def _write_text_region(
    renderer,
    slide,
    bounds: tuple[float, float, float, float],
    *,
    text: str,
    size: int,
    color: str,
    bold: bool = False,
    min_size: int | None = None,
):
    left, top, width, height = bounds
    box = renderer.textbox(slide, left, top, width, height)
    renderer.write_paragraph(box.text_frame, text, size=size, color=color, bold=bold)
    renderer.fit_text_frame(
        box.text_frame,
        max_size=size,
        min_size=min_size if min_size is not None else max(8, size - 3),
        bold=bold,
    )
    return box


def render_metric_card(
    renderer,
    slide,
    *,
    metric: MetricItem,
    panel_bounds: tuple[float, float, float, float],
    accent_color: str,
    variant: str = "standard",
    dense: bool = False,
) -> dict[str, object]:
    t = renderer.theme.typography
    colors = renderer.theme.colors
    panel_left, panel_top, panel_width, panel_height = panel_bounds

    value_size = (t.metric_value_size if variant == "standard" else t.metric_value_size - 4) - (2 if dense else 0)
    label_size = (t.metric_label_size + 1 if variant == "standard" else t.metric_label_size) - (1 if dense else 0)
    detail_size = (t.small_size + 1 if variant == "standard" else t.small_size) - (2 if dense else 1)

    panel_payload = renderer.add_structured_panel(
        slide,
        left=panel_left,
        top=panel_top,
        width=panel_width,
        height=panel_height,
        fill_color=colors.surface,
        line_color=colors.line,
        accent_color=accent_color,
        constrained=True,
        gap=0.06 if dense else 0.08,
        padding=0.22 if dense else 0.24,
        regions=[
            {"kind": "value", "height": 0.5 if dense else 0.56},
            {
                "kind": "label",
                "min_height": 0.34 if dense else 0.30,
                "max_height": 0.56,
                "target_share": renderer.estimate_content_weight(title=metric.label),
            },
            *(
                [
                    {
                        "kind": "detail",
                        "min_height": 0.34 if dense else 0.28,
                        "target_share": renderer.estimate_content_weight(body=metric.detail),
                    }
                ]
                if metric.detail
                else []
            ),
            *([{"kind": "trend", "height": 0.30}] if metric.trend else []),
        ],
    )
    regions = panel_payload["content_regions"]

    _write_text_region(
        renderer,
        slide,
        regions["value"],
        text=metric.value,
        size=value_size,
        color=colors.navy,
        bold=True,
        min_size=t.metric_label_size + 4,
    )
    _write_text_region(
        renderer,
        slide,
        regions["label"],
        text=metric.label,
        size=label_size,
        color=colors.text,
        bold=True,
        min_size=t.small_size + 1,
    )
    if metric.detail:
        _write_text_region(
            renderer,
            slide,
            regions["detail"],
            text=metric.detail,
            size=detail_size,
            color=colors.muted,
            min_size=t.small_size - 2,
        )
    if metric.trend:
        _write_text_region(
            renderer,
            slide,
            regions["trend"],
            text=metric.trend,
            size=detail_size,
            color=colors.accent,
            bold=True,
            min_size=t.small_size - 2,
        )
    return panel_payload


def render_content_card(
    renderer,
    slide,
    *,
    card: CardItem,
    panel_bounds: tuple[float, float, float, float],
    accent_color: str,
    dense: bool = False,
) -> dict[str, object]:
    t = renderer.theme.typography
    colors = renderer.theme.colors
    panel_left, panel_top, panel_width, panel_height = panel_bounds

    title_size = t.body_size - (1 if dense else 0)
    body_size = t.body_size - (2 if dense else 1)
    footer_size = t.small_size

    panel_payload = renderer.add_structured_panel(
        slide,
        left=panel_left,
        top=panel_top,
        width=panel_width,
        height=panel_height,
        fill_color=colors.surface,
        line_color=colors.line,
        accent_color=accent_color,
        gap=0.06 if dense else 0.08,
        padding=0.20 if dense else None,
        min_flex=0.9,
        max_flex=1.35,
        regions=[
            {"kind": "title", "height": 0.38},
            {
                "kind": "body",
                "min_height": 1.15,
                "flex": 1.0,
                "content_weight": renderer.estimate_content_weight(body=card.body),
            },
            *([{"kind": "footer", "height": 0.22}] if card.footer else []),
        ],
    )
    regions = panel_payload["content_regions"]

    _write_text_region(
        renderer,
        slide,
        regions["title"],
        text=card.title,
        size=title_size,
        color=colors.navy,
        bold=True,
        min_size=t.small_size + 1,
    )
    _write_text_region(
        renderer,
        slide,
        regions["body"],
        text=card.body,
        size=body_size,
        color=colors.text,
        min_size=t.small_size,
    )
    if card.footer:
        _write_text_region(
            renderer,
            slide,
            regions["footer"],
            text=card.footer,
            size=footer_size,
            color=colors.muted,
            min_size=max(8, footer_size - 1),
        )
    return panel_payload


def render_numbered_agenda_row(
    renderer,
    slide,
    *,
    row_bounds: tuple[float, float, float, float],
    number: int,
    text: str,
    accent_color: str,
    dense: bool = False,
) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors
    row_left, row_top, row_width, row_height = row_bounds

    renderer.add_panel(
        slide,
        row_left,
        row_top,
        row_width,
        row_height,
        fill_color=colors.surface,
        line_color=colors.line,
    )
    renderer.add_accent_bar(
        slide,
        row_left,
        row_top,
        0.09,
        row_height,
        color=accent_color,
    )

    _write_text_region(
        renderer,
        slide,
        (g.content_left + 0.18, row_top + 0.10, 0.45, max(0.24, row_height - 0.20)),
        text=f"{number:02d}",
        size=t.small_size + 1,
        color=accent_color,
        bold=True,
        min_size=t.small_size,
    )
    _write_text_region(
        renderer,
        slide,
        (g.content_left + 0.72, row_top + 0.09, g.content_width - 0.95, max(0.28, row_height - 0.18)),
        text=text,
        size=t.body_size - (2 if dense else 1),
        color=colors.text,
        bold=number == 1,
        min_size=t.small_size,
    )