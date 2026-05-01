from __future__ import annotations


def _summary_char_count(slide_spec) -> int:
    return sum(
        len(text)
        for text in [slide_spec.title, slide_spec.subtitle, slide_spec.body, *slide_spec.bullets]
        if text
    )


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors
    asset = renderer.resolve_asset(slide_spec.image_path)
    focal_x, focal_y = renderer.resolve_image_focal_point(slide_spec)

    has_body = bool(slide_spec.body)
    has_bullets = bool(slide_spec.bullets)
    narrative_weight = renderer.estimate_content_weight(title=slide_spec.title, body=slide_spec.body)
    takeaway_weight = renderer.estimate_content_weight(bullets=slide_spec.bullets)
    combined_density = _summary_char_count(slide_spec) / max(1.0, g.content_width * 3.2)
    dense_summary = bool(
        (has_body and has_bullets and (narrative_weight + takeaway_weight) >= 5.1)
        or combined_density >= 12.5
        or any(len(bullet) > 80 for bullet in slide_spec.bullets)
    )

    renderer.add_heading(
        slide,
        title=slide_spec.title or "",
        subtitle=slide_spec.subtitle,
        eyebrow=slide_spec.eyebrow,
        left=g.content_left,
        top=g.title_top,
        width=7.85 if has_body and has_bullets else 8.2,
        subtitle_width=6.8 if has_body and has_bullets else 7.1,
    )

    if has_body and has_bullets:
        if asset:
            split_regions = renderer.build_constrained_columns(
                left=g.content_left,
                width=g.content_width,
                regions=[
                    {
                        "kind": "narrative",
                        "min_width": 4.85,
                        "target_share": narrative_weight,
                    },
                    {
                        "kind": "panel",
                        "min_width": 3.0,
                        "max_width": 4.0,
                        "target_share": takeaway_weight,
                    },
                    {
                        "kind": "visual",
                        "width": 3.05,
                        "min_width": 2.8,
                    },
                ],
                gap=0.28 if dense_summary else 0.3,
            )
            narrative_left, narrative_width = split_regions[0]
            panel_left, panel_width = split_regions[1]
            image_left, image_width = split_regions[2]

            body_box = renderer.textbox(slide, narrative_left, 2.24, narrative_width, 2.18 if dense_summary else 2.02)
            renderer.write_paragraph(
                body_box.text_frame,
                slide_spec.body or "",
                size=t.body_size - (1 if dense_summary else 0),
                color=colors.text,
            )
            renderer.fit_text_frame(
                body_box.text_frame,
                max_size=t.body_size - (1 if dense_summary else 0),
                min_size=t.small_size + 1,
            )

            panel_top = 2.04
            panel_height = 3.36 if dense_summary else 3.24
            renderer.add_panel(
                slide,
                panel_left,
                panel_top,
                panel_width,
                panel_height,
                fill_color=colors.surface,
                line_color=colors.line,
            )
            renderer.add_accent_bar(
                slide,
                panel_left,
                panel_top,
                panel_width,
                renderer.theme.components.accent_bar_height,
                color=colors.accent,
            )
            panel_regions = renderer.build_constrained_panel_content_stack_bounds(
                left=panel_left,
                top=panel_top,
                width=panel_width,
                height=panel_height,
                regions=[
                    {"kind": "heading", "height": 0.28},
                    {
                        "kind": "bullets",
                        "min_height": 2.18 if dense_summary else 2.08,
                        "target_share": takeaway_weight,
                    },
                ],
                gap=0.08,
                padding=0.23 if dense_summary else 0.25,
            )
            heading_left, heading_top, heading_width, heading_height = panel_regions[0][1]
            heading_box = renderer.textbox(slide, heading_left, heading_top, heading_width, heading_height)
            if slide_spec.eyebrow:
                renderer.write_paragraph(
                    heading_box.text_frame,
                    slide_spec.eyebrow,
                    size=t.eyebrow_size,
                    color=colors.muted,
                    bold=True,
                )
                renderer.fit_text_frame(heading_box.text_frame, max_size=t.eyebrow_size, bold=True)
            bullets_left, bullets_top, bullets_width, bullets_height = panel_regions[1][1]
            bullets_box = renderer.textbox(slide, bullets_left, bullets_top, bullets_width, bullets_height)
            tf = bullets_box.text_frame
            for bullet in slide_spec.bullets:
                renderer.write_paragraph(
                    tf,
                    f"• {bullet}",
                    size=t.small_size,
                    color=colors.text,
                    space_after=4 if dense_summary else 6,
                )
            renderer.fit_text_frame(tf, max_size=t.small_size, min_size=t.small_size - 1)

            renderer.add_image_cover(
                slide,
                asset,
                left=image_left,
                top=2.04,
                width=image_width,
                height=3.24,
                focal_x=focal_x,
                focal_y=focal_y,
            )
            if slide_spec.image_caption:
                caption_box = renderer.textbox(slide, image_left, 5.36, image_width, 0.28)
                renderer.write_paragraph(
                    caption_box.text_frame,
                    slide_spec.image_caption,
                    size=t.small_size,
                    color=colors.muted,
                )
                renderer.fit_text_frame(caption_box.text_frame, max_size=t.small_size)
            return

        split_regions = renderer.build_constrained_columns(
            left=g.content_left,
            width=g.content_width,
            regions=[
                {
                    "kind": "narrative",
                    "min_width": 5.95,
                    "target_share": narrative_weight,
                },
                {
                    "kind": "panel",
                    "min_width": 3.45,
                    "max_width": 4.6,
                    "target_share": takeaway_weight,
                },
            ],
            gap=0.32 if dense_summary else 0.35,
        )
        narrative_left, narrative_width = split_regions[0]
        panel_left, panel_width = split_regions[1]

        body_box = renderer.textbox(slide, narrative_left, 2.24, narrative_width, 2.12 if dense_summary else 1.98)
        renderer.write_paragraph(
            body_box.text_frame,
            slide_spec.body or "",
            size=t.body_size - (1 if dense_summary else 0),
            color=colors.text,
        )
        renderer.fit_text_frame(
            body_box.text_frame,
            max_size=t.body_size - (1 if dense_summary else 0),
            min_size=t.small_size + 1,
        )

        panel_top = 2.04
        panel_height = 3.42 if dense_summary else 3.28
        renderer.add_panel(slide, panel_left, panel_top, panel_width, panel_height, fill_color=colors.surface, line_color=colors.line)
        renderer.add_accent_bar(
            slide,
            panel_left,
            panel_top,
            panel_width,
            renderer.theme.components.accent_bar_height,
            color=colors.accent,
        )
        panel_regions = renderer.build_constrained_panel_content_stack_bounds(
            left=panel_left,
            top=panel_top,
            width=panel_width,
            height=panel_height,
            regions=[
                {"kind": "heading", "height": 0.28},
                {
                    "kind": "bullets",
                    "min_height": 2.34 if dense_summary else 2.22,
                    "target_share": takeaway_weight,
                },
            ],
            gap=0.08,
            padding=0.24 if dense_summary else 0.26,
        )
        heading_left, heading_top, heading_width, heading_height = panel_regions[0][1]
        heading_box = renderer.textbox(slide, heading_left, heading_top, heading_width, heading_height)
        if slide_spec.eyebrow:
            renderer.write_paragraph(heading_box.text_frame, slide_spec.eyebrow, size=t.eyebrow_size, color=colors.muted, bold=True)
            renderer.fit_text_frame(heading_box.text_frame, max_size=t.eyebrow_size, bold=True)
        bullets_left, bullets_top, bullets_width, bullets_height = panel_regions[1][1]
        bullets_box = renderer.textbox(slide, bullets_left, bullets_top, bullets_width, bullets_height)
        tf = bullets_box.text_frame
        for bullet in slide_spec.bullets:
            renderer.write_paragraph(
                tf,
                f"• {bullet}",
                size=t.small_size + (0 if dense_summary else 1),
                color=colors.text,
                space_after=4 if dense_summary else 6,
            )
        renderer.fit_text_frame(
            tf,
            max_size=t.small_size + (0 if dense_summary else 1),
            min_size=t.small_size - 1,
        )
        return

    if has_body:
        if asset:
            split_regions = renderer.build_constrained_columns(
                left=g.content_left,
                width=g.content_width,
                regions=[
                    {
                        "kind": "summary_body",
                        "min_width": 6.5,
                        "target_share": narrative_weight,
                    },
                    {
                        "kind": "summary_visual",
                        "width": 3.4,
                        "min_width": 3.0,
                    },
                ],
                gap=0.34,
            )
            body_left, body_width = split_regions[0]
            image_left, image_width = split_regions[1]
            summary_box = renderer.textbox(slide, body_left, 2.24, body_width, 2.18)
            renderer.write_paragraph(
                summary_box.text_frame,
                slide_spec.body or "",
                size=t.body_size - (1 if dense_summary else 0),
                color=colors.text,
            )
            renderer.fit_text_frame(
                summary_box.text_frame,
                max_size=t.body_size - (1 if dense_summary else 0),
                min_size=t.small_size + 1,
            )
            renderer.add_image_cover(
                slide,
                asset,
                left=image_left,
                top=2.14,
                width=image_width,
                height=3.38,
                focal_x=focal_x,
                focal_y=focal_y,
            )
            return

        summary_box = renderer.textbox(slide, g.content_left, 2.24, g.content_width, 2.18)
        renderer.write_paragraph(
            summary_box.text_frame,
            slide_spec.body or "",
            size=t.body_size - (1 if dense_summary else 0),
            color=colors.text,
        )
        renderer.fit_text_frame(
            summary_box.text_frame,
            max_size=t.body_size - (1 if dense_summary else 0),
            min_size=t.small_size + 1,
        )
        return

    if asset:
        split_regions = renderer.build_constrained_columns(
            left=g.content_left,
            width=g.content_width,
            regions=[
                {
                    "kind": "summary_panel",
                    "min_width": 6.3,
                    "target_share": takeaway_weight,
                },
                {
                    "kind": "summary_visual",
                    "width": 3.45,
                    "min_width": 3.1,
                },
            ],
            gap=0.34,
        )
        panel_left, panel_width = split_regions[0]
        image_left, image_width = split_regions[1]
        renderer.add_panel(
            slide,
            panel_left,
            2.2,
            panel_width,
            3.24,
            fill_color=colors.surface,
            line_color=colors.line,
        )
        renderer.add_accent_bar(
            slide,
            panel_left,
            2.2,
            panel_width,
            renderer.theme.components.accent_bar_height,
            color=colors.accent,
        )
        content_regions = renderer.build_constrained_panel_content_stack_bounds(
            left=panel_left,
            top=2.2,
            width=panel_width,
            height=3.24,
            regions=[
                {"kind": "heading", "height": 0.28},
                {
                    "kind": "bullets",
                    "min_height": 2.08,
                    "target_share": takeaway_weight,
                },
            ],
            gap=0.1,
            padding=0.26,
        )
        heading_left, heading_top, heading_width, heading_height = content_regions[0][1]
        heading_box = renderer.textbox(slide, heading_left, heading_top, heading_width, heading_height)
        if slide_spec.eyebrow:
            renderer.write_paragraph(
                heading_box.text_frame,
                slide_spec.eyebrow,
                size=t.eyebrow_size,
                color=colors.muted,
                bold=True,
            )
            renderer.fit_text_frame(heading_box.text_frame, max_size=t.eyebrow_size, bold=True)
        bullets_left, bullets_top, bullets_width, bullets_height = content_regions[1][1]
        bullets_box = renderer.textbox(slide, bullets_left, bullets_top, bullets_width, bullets_height)
        tf = bullets_box.text_frame
        for bullet in slide_spec.bullets:
            renderer.write_paragraph(
                tf,
                f"• {bullet}",
                size=t.body_size - (2 if dense_summary else 1),
                color=colors.text,
                space_after=6 if dense_summary else 8,
            )
        renderer.fit_text_frame(
            tf,
            max_size=t.body_size - (2 if dense_summary else 1),
            min_size=t.small_size,
        )
        renderer.add_image_cover(
            slide,
            asset,
            left=image_left,
            top=2.2,
            width=image_width,
            height=3.24,
            focal_x=focal_x,
            focal_y=focal_y,
        )
        return

    renderer.add_panel(
        slide,
        g.content_left,
        2.2,
        g.content_width,
        3.24,
        fill_color=colors.surface,
        line_color=colors.line,
    )
    renderer.add_accent_bar(
        slide,
        g.content_left,
        2.2,
        g.content_width,
        renderer.theme.components.accent_bar_height,
        color=colors.accent,
    )
    content_regions = renderer.build_constrained_panel_content_stack_bounds(
        left=g.content_left,
        top=2.2,
        width=g.content_width,
        height=3.24,
        regions=[
            {"kind": "heading", "height": 0.28},
            {
                "kind": "bullets",
                "min_height": 2.08,
                "target_share": takeaway_weight,
            },
        ],
        gap=0.1,
        padding=0.26,
    )
    heading_left, heading_top, heading_width, heading_height = content_regions[0][1]
    heading_box = renderer.textbox(slide, heading_left, heading_top, heading_width, heading_height)
    if slide_spec.eyebrow:
        renderer.write_paragraph(heading_box.text_frame, slide_spec.eyebrow, size=t.eyebrow_size, color=colors.muted, bold=True)
        renderer.fit_text_frame(heading_box.text_frame, max_size=t.eyebrow_size, bold=True)
    bullets_left, bullets_top, bullets_width, bullets_height = content_regions[1][1]
    bullets_box = renderer.textbox(slide, bullets_left, bullets_top, bullets_width, bullets_height)
    tf = bullets_box.text_frame
    for bullet in slide_spec.bullets:
        renderer.write_paragraph(
            tf,
            f"• {bullet}",
            size=t.body_size - (2 if dense_summary else 1),
            color=colors.text,
            space_after=6 if dense_summary else 8,
        )
    renderer.fit_text_frame(tf, max_size=t.body_size - (2 if dense_summary else 1), min_size=t.small_size)