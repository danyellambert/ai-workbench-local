from __future__ import annotations


def _faq_item_weight(renderer, item) -> float:
    return renderer.estimate_content_weight(title=item.title, body=item.body)


def _faq_item_dense(renderer, item) -> bool:
    weight = _faq_item_weight(renderer, item)
    return bool(weight >= 2.8 or len(item.title) > 28 or len(item.body) > 115)


def render(renderer, slide, slide_spec, meta, index, total_slides) -> None:
    g = renderer.theme.grid
    t = renderer.theme.typography
    colors = renderer.theme.colors

    items = slide_spec.faq_items
    dense_faq = len(items) >= 4 or any(_faq_item_dense(renderer, item) for item in items)

    renderer.add_heading(
        slide,
        title=slide_spec.title or "",
        subtitle=slide_spec.subtitle,
        eyebrow=slide_spec.eyebrow or "FAQ",
        left=g.content_left,
        top=g.title_top,
        width=7.8 if dense_faq else 8.0,
        subtitle_width=6.8 if dense_faq else 7.0,
    )

    columns = 2 if len(items) > 1 else 1
    panel_gap = 0.3 if dense_faq else 0.35
    top_start = 2.16
    row_count = (len(items) + columns - 1) // columns
    total_height = 3.72 if row_count > 1 else (1.96 if dense_faq else 1.68)
    row_weights = [
        max(_faq_item_weight(renderer, item) for item in items[row_index * columns : (row_index + 1) * columns])
        for row_index in range(row_count)
    ]
    column_weights = [
        max(
            _faq_item_weight(renderer, item)
            for item in items[column_index::columns]
        )
        for column_index in range(columns)
    ]
    grid_bounds = renderer.build_constrained_panel_grid_content_bounds(
        left=g.content_left,
        top=top_start,
        width=g.content_width,
        height=total_height,
        column_gap=panel_gap,
        row_gap=0.14 if dense_faq else 0.22,
        column_regions=[
            {
                "kind": f"faq_column_{column_index + 1}",
                "min_width": 3.1,
                "target_share": column_weights[column_index],
                "max_width": 5.15 if columns > 1 else g.content_width,
            }
            for column_index in range(columns)
        ],
        row_regions=[
            {
                "kind": f"faq_row_{row_index + 1}",
                "min_height": 1.24 if dense_faq else 1.16,
                "target_share": max(1.0, row_weights[row_index]),
                "max_height": 2.05 if row_count > 1 else total_height,
            }
            for row_index in range(row_count)
        ],
        padding=0.2 if dense_faq else 0.22,
    )

    for idx, item in enumerate(items):
        row = idx // columns
        col = idx % columns
        panel_bounds, content_bounds = grid_bounds[row][col]
        left, top, panel_width, panel_height = panel_bounds
        content_left, content_top, content_width, content_height = content_bounds
        dense_item = _faq_item_dense(renderer, item)
        title_size = t.small_size + (1 if dense_item else 2)
        body_size = t.small_size + (-1 if dense_item else 1)

        renderer.add_panel(
            slide,
            left,
            top,
            panel_width,
            panel_height,
            fill_color=colors.surface,
            line_color=colors.line,
        )
        renderer.add_accent_bar(
            slide,
            left,
            top,
            panel_width,
            renderer.theme.components.accent_bar_height,
            color=colors.accent if idx % 2 else colors.navy,
        )

        for region, (region_left, region_top, region_width, region_height) in renderer.build_constrained_panel_content_stack_bounds(
            left=left,
            top=top,
            width=panel_width,
            height=panel_height,
            regions=[
                {
                    "kind": "title",
                    "min_height": 0.32 if dense_item else 0.28,
                    "max_height": 0.52,
                    "target_share": renderer.estimate_content_weight(title=item.title),
                },
                {
                    "kind": "body",
                    "min_height": 0.72 if dense_item else 0.68,
                    "target_share": renderer.estimate_content_weight(body=item.body),
                },
            ],
            gap=0.05 if dense_item else 0.06,
            padding=0.2 if dense_item else 0.22,
        ):
            if region["kind"] == "title":
                title_box = renderer.textbox(slide, region_left, region_top, region_width, region_height)
                renderer.write_paragraph(
                    title_box.text_frame,
                    item.title,
                    size=title_size,
                    color=colors.navy,
                    bold=True,
                )
                renderer.fit_text_frame(title_box.text_frame, max_size=title_size, min_size=t.small_size, bold=True)
            else:
                body_box = renderer.textbox(slide, region_left, region_top, region_width, region_height)
                renderer.write_paragraph(
                    body_box.text_frame,
                    item.body,
                    size=body_size,
                    color=colors.text,
                )
                renderer.fit_text_frame(body_box.text_frame, max_size=body_size, min_size=t.small_size - 2)