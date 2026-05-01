from __future__ import annotations

from ppt_creator.layouts._components import render_numbered_agenda_row


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors
    dense_agenda = len(slide_spec.bullets) >= 6 or any(len(bullet) > 72 for bullet in slide_spec.bullets)

    renderer.add_heading(
        slide,
        title=slide_spec.title or "",
        subtitle=slide_spec.subtitle,
        eyebrow=slide_spec.eyebrow or "Agenda",
        left=g.content_left,
        top=g.title_top,
        width=8.2,
        subtitle_width=7.0,
    )

    bullet_weights = [renderer.estimate_content_weight(body=bullet) for bullet in slide_spec.bullets]
    stack_regions: list[dict[str, float | str]] = []
    if slide_spec.body:
        stack_regions.append(
            {
                "kind": "intro",
                "min_height": 0.56,
                "flex": 1.0,
                "content_weight": renderer.estimate_content_weight(body=slide_spec.body),
            }
        )
    stack_regions.append(
        {
            "kind": "agenda_rows",
            "min_height": 2.6,
            "flex": 1.0,
            "content_weight": sum(bullet_weights) or 1.0,
        }
    )

    for region, (region_top, region_height) in renderer.build_content_stack(
        top=2.2,
        height=4.0 if dense_agenda else 3.9,
        regions=stack_regions,
        gap=0.18,
        min_flex=0.9,
        max_flex=1.32 if dense_agenda else 1.25,
    ):
        if region["kind"] == "intro":
            intro_box = renderer.textbox(slide, g.content_left, region_top, g.content_width, region_height)
            renderer.write_paragraph(
                intro_box.text_frame,
                slide_spec.body or "",
                size=t.body_size - (2 if dense_agenda else 1),
                color=colors.text,
            )
            renderer.fit_text_frame(
                intro_box.text_frame,
                max_size=t.body_size - (2 if dense_agenda else 1),
                min_size=t.small_size,
            )
            continue

        row_flexes = renderer.normalize_content_flexes(
            bullet_weights,
            min_flex=0.9,
            max_flex=1.26 if dense_agenda else 1.2,
        )
        row_bounds = renderer.build_named_rows(
            top=region_top,
            height=region_height,
            gap=0.12 if dense_agenda else 0.16,
            min_height=0.40 if dense_agenda else 0.46,
            regions=[
                {
                    "kind": f"agenda_row_{index + 1}",
                    "min_height": 0.40 if dense_agenda else 0.46,
                    "flex": flex,
                }
                for index, flex in enumerate(row_flexes)
            ],
        )
        for idx, bullet in enumerate(slide_spec.bullets, start=1):
            row_top, row_height = row_bounds[f"agenda_row_{idx}"]
            render_numbered_agenda_row(
                renderer,
                slide,
                row_bounds=(g.content_left, row_top, g.content_width, row_height),
                number=idx,
                text=bullet,
                accent_color=colors.accent if idx == 1 else colors.navy,
                dense=dense_agenda,
            )