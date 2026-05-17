from __future__ import annotations


def _column_weight(renderer, column) -> float:
    return renderer.estimate_content_weight(
        title=column.title,
        body=column.body,
        bullets=column.bullets,
        footer=column.footer,
        tag=column.tag,
    )


def _column_text_char_count(column) -> int:
    return sum(
        len(text)
        for text in [column.title, column.body, column.footer, column.tag, *column.bullets]
        if text
    )


def render_column_panels(
    renderer,
    slide,
    slide_spec,
    *,
    columns,
    heading_width: float = 8.0,
    subtitle_width: float,
    panel_top: float | None = None,
    panel_height: float,
    gap: float = 0.42,
    min_width: float = 3.6,
    panel_max_width: float | None = None,
    accent_mode: str = "top",
    panel_padding: float = 0.28,
    title_height: float | None = None,
    body_min_height: float = 0.72,
    body_fixed_height: float = 1.48,
    bullets_min_height: float = 0.44,
    eyebrow_default: str | None = None,
) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors
    semantic = renderer.resolve_semantic_layout(slide_spec.type.value, slide_spec.layout_variant)
    resolved_panel_top = panel_top if panel_top is not None else semantic.panel_top
    base_title_height = title_height if title_height is not None else semantic.panel_title_height

    renderer.add_heading(
        slide,
        title=slide_spec.title or "",
        subtitle=slide_spec.subtitle,
        eyebrow=slide_spec.eyebrow or eyebrow_default,
        left=g.content_left,
        top=semantic.heading_top,
        width=min(heading_width, 7.4),
        subtitle_width=subtitle_width,
        slide_type=slide_spec.type.value,
        layout_variant=slide_spec.layout_variant,
    )

    weights = [_column_weight(renderer, column) for column in columns]
    panel_bounds = renderer.build_constrained_panel_row_bounds(
        left=g.content_left,
        top=resolved_panel_top,
        width=g.content_width,
        height=panel_height,
        gap=gap,
        regions=[
            {
                "kind": f"column_panel_{index + 1}",
                "min_width": min_width,
                "target_share": weight,
                **({"max_width": panel_max_width} if panel_max_width is not None else {}),
            }
            for index, weight in enumerate(weights)
        ],
    )

    for idx, (column, (left, top, width, height)) in enumerate(zip(columns, panel_bounds, strict=True)):
        accent = colors.navy if idx == 0 else colors.accent
        weight = weights[idx]
        text_chars = _column_text_char_count(column)
        area = max(1.1, width * height)
        density = text_chars / area
        dense = bool(weight >= 3.0 or density >= 28 or (width < 4.15 and weight >= 2.7) or len(column.bullets) >= 4)
        very_dense = bool(weight >= 3.8 or density >= 38 or len(column.bullets) >= 5 or len(column.body or "") > 220)

        resolved_padding = max(0.20, panel_padding - (0.05 if very_dense else 0.03 if dense else 0.0))
        resolved_gap = 0.05 if very_dense else 0.06
        resolved_title_height = base_title_height + (0.06 if len(column.title) > 28 else 0.0)
        resolved_body_min_height = body_min_height + (0.10 if dense and column.bullets else 0.0)
        resolved_body_fixed_height = body_fixed_height + (0.16 if dense and not column.bullets else 0.0)
        resolved_bullets_min_height = bullets_min_height + (0.12 if len(column.bullets) >= 3 else 0.04 if column.bullets else 0.0)

        title_size = max(t.small_size + 2, t.body_size + (0 if dense else 1))
        body_size = max(t.small_size + 1, t.body_size - (2 if very_dense else 1 if dense else 0))
        bullet_size = max(t.small_size - 1, t.small_size + (0 if dense else 1) - (1 if very_dense else 0))
        tag_size = max(t.small_size - 1, t.small_size - (1 if very_dense else 0))
        footer_size = max(t.small_size - 1, t.small_size - (1 if very_dense else 0))

        renderer.add_panel(
            slide,
            left,
            top,
            width,
            height,
            fill_color=colors.surface,
            line_color=colors.line,
        )
        if accent_mode == "left":
            renderer.add_accent_bar(slide, left, top, 0.08, height, color=accent)
        else:
            renderer.add_accent_bar(
                slide,
                left,
                top,
                width,
                0.05,
                color=accent,
            )

        if idx == 0:
            renderer.add_rule(slide, left + 0.18, top + 0.24, left + min(width * 0.42, 1.8), top + 0.24, color=colors.line, width_pt=0.9)

        regions: list[dict[str, float | str]] = []
        if column.tag:
            regions.append({"kind": "tag", "height": 0.20})
        regions.append({"kind": "title", "height": resolved_title_height})
        if column.body:
            if column.bullets:
                regions.append(
                    {
                        "kind": "body",
                        "min_height": resolved_body_min_height,
                        "target_share": renderer.estimate_content_weight(body=column.body),
                    }
                )
            else:
                regions.append({"kind": "body", "height": resolved_body_fixed_height})
        if column.bullets:
            regions.append(
                {
                    "kind": "bullets",
                    "min_height": resolved_bullets_min_height,
                    "target_share": renderer.estimate_content_weight(bullets=column.bullets),
                }
            )
        if column.footer:
            regions.append({"kind": "footer", "height": 0.22})

        for region, (content_left, region_top, content_width, region_height) in renderer.build_constrained_panel_content_stack_bounds(
            left=left,
            top=top,
            width=width,
            height=height,
            regions=regions,
            gap=resolved_gap,
            padding=resolved_padding,
        ):
            kind = region["kind"]
            if kind == "tag":
                tag_box = renderer.textbox(slide, content_left, region_top, content_width, region_height)
                renderer.write_paragraph(tag_box.text_frame, column.tag or "", size=tag_size, color=colors.muted, bold=True)
                renderer.fit_text_frame(tag_box.text_frame, max_size=tag_size, min_size=max(8, tag_size - 1), bold=True)
            elif kind == "title":
                title_box = renderer.textbox(slide, content_left, region_top, content_width, region_height)
                renderer.write_paragraph(title_box.text_frame, column.title, size=title_size, color=colors.navy, bold=True)
                renderer.fit_text_frame(title_box.text_frame, max_size=title_size, min_size=t.small_size + 2, bold=True)
            elif kind == "body":
                body_box = renderer.textbox(slide, content_left, region_top, content_width, region_height)
                renderer.write_paragraph(body_box.text_frame, column.body or "", size=body_size, color=colors.text)
                renderer.fit_text_frame(body_box.text_frame, max_size=body_size, min_size=t.small_size)
            elif kind == "bullets":
                bullets_box = renderer.textbox(slide, content_left, region_top, content_width, region_height)
                tf = bullets_box.text_frame
                for bullet in column.bullets:
                    renderer.write_paragraph(
                        tf,
                        f"• {bullet}",
                        size=bullet_size,
                        color=colors.text,
                        space_after=3 if dense else 5,
                    )
                renderer.fit_text_frame(tf, max_size=bullet_size, min_size=t.small_size - 1)
            elif kind == "footer":
                footer_box = renderer.textbox(slide, content_left, region_top, content_width, region_height)
                renderer.write_paragraph(footer_box.text_frame, column.footer or "", size=footer_size, color=accent, bold=True)
                renderer.fit_text_frame(footer_box.text_frame, max_size=footer_size, min_size=max(8, footer_size - 1), bold=True)