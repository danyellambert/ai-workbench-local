from __future__ import annotations


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors
    variant = renderer.resolve_layout_variant(slide_spec, "insight_panel")
    dense_bullets = bool(len(slide_spec.bullets) >= 4 or any(len(bullet) > 88 for bullet in slide_spec.bullets))
    insight_heading = slide_spec.subtitle or slide_spec.eyebrow or ""
    insight_body = slide_spec.body or (slide_spec.bullets[0] if slide_spec.bullets else "")
    insight_points = slide_spec.bullets[1:4] if len(slide_spec.bullets) > 1 else []

    if variant == "insight_panel":
        split_columns = renderer.build_named_columns(
            left=g.content_left,
            width=g.content_width,
            gap=0.35,
            regions=[
                {
                    "kind": "text",
                    "min_width": 4.8,
                    "target_share": renderer.estimate_content_weight(
                        title=slide_spec.title,
                        body=slide_spec.body,
                        bullets=slide_spec.bullets,
                    ),
                },
                {
                    "kind": "insight",
                    "min_width": 3.4,
                    "max_width": 4.4,
                    "target_share": renderer.estimate_content_weight(
                        title=insight_heading,
                        body=insight_body,
                        bullets=insight_points,
                    ),
                },
            ],
        )
        text_left, left_width = split_columns["text"]
        side_left, side_width = split_columns["insight"]
    else:
        text_left = g.content_left
        left_width = g.content_width
        side_left = side_width = 0.0

    if slide_spec.eyebrow:
        eyebrow_box = renderer.textbox(slide, text_left, 0.78, min(left_width, 5.4), 0.25)
        renderer.write_paragraph(eyebrow_box.text_frame, slide_spec.eyebrow.upper(), size=t.eyebrow_size, color=colors.accent, bold=True)
        renderer.fit_text_frame(eyebrow_box.text_frame, max_size=t.eyebrow_size, bold=True)

    title_box = renderer.textbox(slide, text_left, 1.02, min(left_width, 6.4), 0.85)
    renderer.write_paragraph(title_box.text_frame, slide_spec.title or "", size=t.title_size, color=colors.navy, bold=True)
    renderer.fit_text_frame(title_box.text_frame, max_size=t.title_size, bold=True)

    if slide_spec.subtitle:
        subtitle_box = renderer.textbox(slide, text_left, 1.82, min(left_width, 5.8), 0.45)
        renderer.write_paragraph(subtitle_box.text_frame, slide_spec.subtitle, size=t.subtitle_size, color=colors.muted)
        renderer.fit_text_frame(subtitle_box.text_frame, max_size=t.subtitle_size)

    text_regions: list[dict[str, float | str]] = []
    if slide_spec.body:
        if slide_spec.bullets:
            text_regions.append(
                {
                    "kind": "body",
                    "min_height": 0.92,
                    "flex": 1.0,
                    "content_weight": renderer.estimate_content_weight(body=slide_spec.body),
                }
            )
        else:
            text_regions.append({"kind": "body", "height": 3.15})
    if slide_spec.bullets:
        text_regions.append(
            {
                "kind": "bullets",
                "min_height": 1.45 if slide_spec.body else 3.15,
                "flex": 1.0,
                "content_weight": renderer.estimate_content_weight(bullets=slide_spec.bullets),
            }
        )

    for region, (region_top, region_height) in renderer.build_content_stack(
        top=2.55,
        height=3.35 if dense_bullets else 3.15,
        regions=text_regions,
        gap=0.14 if dense_bullets else 0.18,
        min_flex=0.9,
        max_flex=1.42 if dense_bullets else 1.35,
    ):
        if region["kind"] == "body":
            body_box = renderer.textbox(slide, text_left, region_top, left_width, region_height)
            renderer.write_paragraph(
                body_box.text_frame,
                slide_spec.body or "",
                size=t.body_size - (1 if dense_bullets else 0),
                color=colors.text,
            )
            renderer.fit_text_frame(
                body_box.text_frame,
                max_size=t.body_size - (1 if dense_bullets else 0),
                min_size=t.small_size,
            )
        else:
            bullets_box = renderer.textbox(slide, text_left, region_top, left_width, region_height)
            tf = bullets_box.text_frame
            for bullet in slide_spec.bullets:
                renderer.write_paragraph(
                    tf,
                    f"• {bullet}",
                    size=t.body_size - (2 if dense_bullets else 1),
                    color=colors.text,
                    space_after=4 if dense_bullets else 6,
                )
            renderer.fit_text_frame(
                tf,
                max_size=t.body_size - (2 if dense_bullets else 1),
                min_size=t.small_size,
            )

    if variant == "insight_panel":
        insight_payload = renderer.add_structured_panel(
            slide,
            left=side_left,
            top=1.05,
            width=side_width,
            height=4.95,
            fill_color=colors.surface,
            line_color=colors.line,
            accent_color=colors.accent,
            padding=0.28,
            gap=0.10,
            min_flex=0.9,
            max_flex=1.3,
            regions=[
                *([{"kind": "heading", "height": 0.24}] if insight_heading else []),
                *(
                    [
                        {
                            "kind": "body",
                            "min_height": 0.8,
                            "flex": 1.0,
                            "content_weight": renderer.estimate_content_weight(body=insight_body),
                        }
                    ]
                    if insight_body
                    else []
                ),
                *(
                    [
                        {
                            "kind": "points",
                            "min_height": 0.9,
                            "flex": 1.0,
                            "content_weight": renderer.estimate_content_weight(bullets=insight_points),
                        }
                    ]
                    if insight_points
                    else []
                ),
            ],
        )
        content_regions = insight_payload["content_regions"]
        if insight_heading:
            heading_left, heading_top, heading_width, heading_height = content_regions["heading"]
            heading_box = renderer.textbox(slide, heading_left, heading_top, heading_width, heading_height)
            renderer.write_paragraph(heading_box.text_frame, insight_heading, size=t.eyebrow_size, color=colors.muted, bold=True)
            renderer.fit_text_frame(heading_box.text_frame, max_size=t.eyebrow_size, min_size=t.small_size, bold=True)
        if insight_body:
            body_left, body_top, body_width, body_height = content_regions["body"]
            body_box = renderer.textbox(slide, body_left, body_top, body_width, body_height)
            renderer.write_paragraph(
                body_box.text_frame,
                insight_body,
                size=t.body_size - (2 if dense_bullets else 1),
                color=colors.text,
            )
            renderer.fit_text_frame(
                body_box.text_frame,
                max_size=t.body_size - (2 if dense_bullets else 1),
                min_size=t.small_size,
            )
        if insight_points:
            points_left, points_top, points_width, points_height = content_regions["points"]
            points_box = renderer.textbox(slide, points_left, points_top, points_width, points_height)
            tf = points_box.text_frame
            for bullet in insight_points:
                renderer.write_paragraph(
                    tf,
                    f"• {bullet}",
                    size=t.body_size - (2 if dense_bullets else 1),
                    color=colors.navy,
                    space_after=3 if dense_bullets else 4,
                )
            renderer.fit_text_frame(
                tf,
                max_size=t.body_size - (2 if dense_bullets else 1),
                min_size=t.small_size,
            )
    else:
        renderer.add_rule(
            slide,
            g.content_left,
            2.22,
            g.content_right,
            2.22,
            color=colors.line,
            width_pt=1.0,
        )
        callout_text = slide_spec.subtitle or slide_spec.eyebrow or ""
        if callout_text:
            callout = renderer.textbox(slide, g.content_left, 5.9, g.content_width, 0.45)
            renderer.write_paragraph(
                callout.text_frame,
                callout_text,
                size=t.small_size + 1,
                color=colors.muted,
            )
            renderer.fit_text_frame(callout.text_frame, max_size=t.small_size + 1)
