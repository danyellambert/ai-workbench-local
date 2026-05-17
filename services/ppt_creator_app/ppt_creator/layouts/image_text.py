from __future__ import annotations


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors
    variant = renderer.resolve_layout_variant(slide_spec, "image_right")

    split_regions = renderer.build_named_columns(
        left=g.content_left,
        width=g.content_width,
        gap=0.42,
        regions=(
            [
                {
                    "kind": "text",
                    "min_width": 5.2,
                    "target_share": renderer.estimate_content_weight(
                        title=slide_spec.title,
                        body=slide_spec.body,
                        bullets=slide_spec.bullets,
                        footer=slide_spec.subtitle,
                        tag=slide_spec.eyebrow,
                    ),
                },
                {"kind": "visual", "width": 5.15, "min_width": 4.8},
            ]
            if variant == "image_right"
            else [
                {"kind": "visual", "width": 5.15, "min_width": 4.8},
                {
                    "kind": "text",
                    "min_width": 5.2,
                    "target_share": renderer.estimate_content_weight(
                        title=slide_spec.title,
                        body=slide_spec.body,
                        bullets=slide_spec.bullets,
                        footer=slide_spec.subtitle,
                        tag=slide_spec.eyebrow,
                    ),
                },
            ]
        ),
    )
    text_left, text_width = split_regions["text"]
    image_left, image_width = split_regions["visual"]

    if slide_spec.eyebrow:
        eyebrow_box = renderer.textbox(slide, text_left, 0.78, min(text_width, 4.8), 0.25)
        renderer.write_paragraph(eyebrow_box.text_frame, slide_spec.eyebrow.upper(), size=t.eyebrow_size, color=colors.accent, bold=True)
        renderer.fit_text_frame(eyebrow_box.text_frame, max_size=t.eyebrow_size, bold=True)

    title_box = renderer.textbox(slide, text_left, 1.02, text_width, 0.8)
    renderer.write_paragraph(title_box.text_frame, slide_spec.title or "", size=t.title_size, color=colors.navy, bold=True)
    renderer.fit_text_frame(title_box.text_frame, max_size=t.title_size, bold=True)

    if slide_spec.subtitle:
        subtitle_box = renderer.textbox(slide, text_left, 1.8, text_width, 0.45)
        renderer.write_paragraph(subtitle_box.text_frame, slide_spec.subtitle, size=t.subtitle_size, color=colors.muted)
        renderer.fit_text_frame(subtitle_box.text_frame, max_size=t.subtitle_size)

    image_top = 1.28
    image_height = 4.95
    renderer.add_visual_slot(
        slide,
        slide_spec,
        left=image_left,
        top=image_top,
        width=image_width,
        height=image_height,
        accent_color=colors.accent,
        padding=0.28,
    )

    if slide_spec.body or slide_spec.bullets:
        text_regions: list[dict[str, float | str]] = []
        if slide_spec.body:
            if slide_spec.bullets:
                text_regions.append(
                    {
                        "kind": "body",
                        "min_height": 0.82,
                        "flex": 1.0,
                        "content_weight": renderer.estimate_content_weight(body=slide_spec.body),
                    }
                )
            else:
                text_regions.append({"kind": "body", "height": 2.35})
        if slide_spec.bullets:
            text_regions.append(
                {
                    "kind": "bullets",
                    "min_height": 1.5 if slide_spec.body else 3.1,
                    "flex": 1.0,
                    "content_weight": renderer.estimate_content_weight(bullets=slide_spec.bullets),
                }
            )

        for region, (region_top, region_height) in renderer.build_content_stack(
            top=2.45,
            height=3.1,
            regions=text_regions,
            gap=0.18,
            min_flex=0.9,
            max_flex=1.35,
        ):
            if region["kind"] == "body":
                body_box = renderer.textbox(slide, text_left, region_top, text_width, region_height)
                renderer.write_paragraph(body_box.text_frame, slide_spec.body or "", size=t.body_size, color=colors.text)
                renderer.fit_text_frame(body_box.text_frame, max_size=t.body_size)
            else:
                bullets_box = renderer.textbox(slide, text_left, region_top, text_width, region_height)
                tf = bullets_box.text_frame
                for bullet in slide_spec.bullets:
                    renderer.write_paragraph(tf, f"• {bullet}", size=t.body_size - 1, color=colors.text, space_after=4)
                renderer.fit_text_frame(tf, max_size=t.body_size - 1)
