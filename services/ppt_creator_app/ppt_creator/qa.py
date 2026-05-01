from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ppt_creator.renderer import PresentationRenderer
from ppt_creator.schema import PresentationInput, Slide


def _issue(severity: str, message: str) -> dict[str, str]:
    return {"severity": severity, "message": message}


def _score_from_issues(issues: list[dict[str, str]]) -> int:
    penalty_map = {"high": 14, "medium": 7, "low": 3}
    score = 100
    for issue in issues:
        score -= penalty_map.get(issue["severity"], 5)
    return max(0, score)


def _severity_counts(issues: list[dict[str, str]]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        severity = issue.get("severity", "low")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def _balance_ratio(weights: list[float]) -> float:
    positive = [weight for weight in weights if weight > 0]
    if len(positive) < 2:
        return 1.0
    low = min(positive)
    high = max(positive)
    return high / low if low else high


def _estimate_text_mass(
    *,
    title: str | None = None,
    body: str | None = None,
    bullets: list[str] | None = None,
    footer: str | None = None,
    tag: str | None = None,
) -> float:
    bullet_items = bullets or []
    mass = 0.0
    if title:
        mass += len(title.split()) * 0.7
    if body:
        mass += len(body.split()) * 1.0
    if footer:
        mass += len(footer.split()) * 0.45
    if tag:
        mass += len(tag.split()) * 0.3
    for bullet in bullet_items:
        mass += len(bullet.split()) * 1.1
    return round(mass, 2)


def _region_density(
    *,
    width: float,
    height: float,
    title: str | None = None,
    body: str | None = None,
    bullets: list[str] | None = None,
    footer: str | None = None,
    tag: str | None = None,
) -> float:
    area = max(0.35, width * height)
    return round(
        _estimate_text_mass(title=title, body=body, bullets=bullets, footer=footer, tag=tag) / area,
        3,
    )


def _region_text_chars(
    *,
    title: str | None = None,
    body: str | None = None,
    bullets: list[str] | None = None,
    footer: str | None = None,
    tag: str | None = None,
) -> int:
    return sum(
        len(text)
        for text in [title, body, footer, tag, *(bullets or [])]
        if text
    )


def _build_layout_pressure_signals(renderer: PresentationRenderer, slide: Slide) -> list[dict[str, object]]:
    g = renderer.theme.grid
    signals: list[dict[str, object]] = []

    def add_signal(*, region: str, density: float, threshold: float, message: str) -> None:
        if density < threshold:
            return
        signals.append(
            {
                "region": region,
                "density": density,
                "threshold": threshold,
                "severity": "high" if density >= threshold * 1.3 else "medium",
                "message": message,
            }
        )

    if slide.type.value == "agenda":
        bullet_weights = [renderer.estimate_content_weight(body=bullet) for bullet in slide.bullets]
        stack_regions: list[dict[str, float | str]] = []
        if slide.body:
            stack_regions.append(
                {
                    "kind": "intro",
                    "min_height": 0.56,
                    "flex": 1.0,
                    "content_weight": renderer.estimate_content_weight(body=slide.body),
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
        content_stack = renderer.build_content_stack(
            top=2.2,
            height=3.9,
            regions=stack_regions,
            gap=0.18,
            min_flex=0.9,
            max_flex=1.25,
        )
        for region, (_, region_height) in content_stack:
            if region["kind"] == "intro" and slide.body:
                density = _region_density(width=g.content_width, height=region_height, body=slide.body)
                add_signal(
                    region="agenda:intro",
                    density=density,
                    threshold=4.1,
                    message="agenda intro region is dense enough to risk vertical crowding",
                )
            elif region["kind"] == "agenda_rows" and slide.bullets:
                row_bounds = renderer.build_weighted_rows(
                    top=0.0,
                    height=region_height,
                    gap=0.16,
                    weights=bullet_weights,
                    min_height=0.46,
                    min_flex=0.9,
                    max_flex=1.2,
                    kind_prefix="agenda_row",
                )
                for index, (bullet, (_, row_height)) in enumerate(zip(slide.bullets, row_bounds, strict=True), start=1):
                    density = _region_density(
                        width=g.content_width - 0.95,
                        height=max(0.28, row_height - 0.18),
                        body=bullet,
                    )
                    add_signal(
                        region=f"agenda:row_{index}",
                        density=density,
                        threshold=3.8,
                        message=f"agenda row {index} is tightly packed and may collide vertically",
                    )

    elif slide.type.value == "bullets":
        variant = renderer.resolve_layout_variant(slide, "insight_panel")
        if variant == "insight_panel":
            split_weights = [
                renderer.estimate_content_weight(title=slide.title, body=slide.body, bullets=slide.bullets),
                renderer.estimate_content_weight(
                    title="Executive lens",
                    body="Keep decision-making crisp, reduce operational drag, and let human sellers spend more time in high-value conversations.",
                    bullets=["clarity", "consistency", "measurable lift"],
                ),
            ]
            split_columns = renderer.build_weighted_columns(
                left=g.content_left,
                width=g.content_width,
                gap=0.35,
                weights=split_weights,
                min_width=3.4,
                min_flex=0.9,
                max_flex=1.3,
                kind_prefix="bullets_split",
            )
            _, left_width = split_columns[0]
        else:
            left_width = g.content_width

        text_regions: list[dict[str, float | str]] = []
        if slide.body:
            if slide.bullets:
                text_regions.append(
                    {
                        "kind": "body",
                        "min_height": 0.92,
                        "flex": 1.0,
                        "content_weight": renderer.estimate_content_weight(body=slide.body),
                    }
                )
            else:
                text_regions.append({"kind": "body", "height": 3.15})
        if slide.bullets:
            text_regions.append(
                {
                    "kind": "bullets",
                    "min_height": 1.45 if slide.body else 3.15,
                    "flex": 1.0,
                    "content_weight": renderer.estimate_content_weight(bullets=slide.bullets),
                }
            )
        for region, (_, region_height) in renderer.build_content_stack(
            top=2.55,
            height=3.15,
            regions=text_regions,
            gap=0.18,
            min_flex=0.9,
            max_flex=1.35,
        ):
            if region["kind"] == "body" and slide.body:
                density = _region_density(width=left_width, height=region_height, body=slide.body)
                add_signal(
                    region="bullets:body",
                    density=density,
                    threshold=4.1,
                    message="bullets narrative region is dense enough to risk text collisions",
                )
            elif region["kind"] == "bullets" and slide.bullets:
                density = _region_density(width=left_width, height=region_height, bullets=slide.bullets)
                add_signal(
                    region="bullets:list",
                    density=density,
                    threshold=3.9,
                    message="bullet list region is dense enough to risk crowding or overlap",
                )

    elif slide.type.value == "metrics" and slide.metrics:
        metric_weights = [
            renderer.estimate_content_weight(title=metric.label, body=metric.detail, footer=metric.trend, tag=metric.value)
            for metric in slide.metrics
        ]
        metric_flexes = renderer.normalize_content_flexes(metric_weights, min_flex=0.9, max_flex=1.25)
        metric_bounds = renderer.build_panel_row_bounds(
            left=g.content_left,
            top=2.45,
            width=g.content_width,
            height=2.25,
            gap=0.28,
            min_width=2.0,
            regions=[
                {"kind": f"metric_{index + 1}", "min_width": 2.0, "flex": flex}
                for index, flex in enumerate(metric_flexes)
            ],
        )
        for index, (metric, (left, panel_top, panel_width, panel_height)) in enumerate(
            zip(slide.metrics, metric_bounds, strict=True),
            start=1,
        ):
            content_left, content_top, content_width, content_height = renderer.panel_inner_bounds(
                left=left,
                top=panel_top,
                width=panel_width,
                height=panel_height,
                padding=0.24,
            )
            density = _region_density(
                width=content_width,
                height=content_height,
                title=metric.label,
                body=metric.detail,
                footer=metric.trend,
                tag=metric.value,
            )
            add_signal(
                region=f"metrics:card_{index}",
                density=density,
                threshold=3.9,
                message=f"metric card {index} is dense enough to risk clipping or cramped KPI composition",
            )
            label_density = _region_density(
                width=content_width,
                height=max(0.34, content_height * 0.24),
                title=metric.label,
                tag=metric.value,
            )
            add_signal(
                region=f"metrics:label_{index}",
                density=label_density,
                threshold=4.7,
                message=f"metric card {index} label stack is dense enough to wrap awkwardly",
            )
            if metric.detail:
                detail_density = _region_density(
                    width=content_width,
                    height=max(0.42, content_height * 0.38),
                    body=metric.detail,
                    footer=metric.trend,
                )
                add_signal(
                    region=f"metrics:detail_{index}",
                    density=detail_density,
                    threshold=4.6,
                    message=f"metric card {index} detail region is dense enough to feel cramped",
                )
                compact_stack_density = _region_density(
                    width=content_width,
                    height=max(0.56, content_height * 0.34),
                    title=metric.label,
                    body=metric.detail,
                    footer=metric.trend,
                )
                add_signal(
                    region=f"metrics:stack_{index}",
                    density=compact_stack_density,
                    threshold=5.15,
                    message=f"metric card {index} combines too much text for its available stack height",
                )

        width_ratio = _balance_ratio([panel_width for _, _, panel_width, _ in metric_bounds])
        imbalance_score = round(_balance_ratio(metric_weights) / max(1.0, width_ratio), 3)
        add_signal(
            region="metrics:row_imbalance",
            density=imbalance_score,
            threshold=1.28,
            message="metric cards are materially imbalanced and may look visually uneven",
        )

    elif slide.type.value == "summary":
        has_body = bool(slide.body)
        has_bullets = bool(slide.bullets)
        if has_body and has_bullets:
            narrative_weight = renderer.estimate_content_weight(title=slide.title, body=slide.body)
            takeaway_weight = renderer.estimate_content_weight(bullets=slide.bullets)
            split_flexes = renderer.normalize_content_flexes(
                [narrative_weight, takeaway_weight],
                min_flex=0.9,
                max_flex=1.4,
            )
            split_regions = renderer.build_columns(
                left=g.content_left,
                width=g.content_width,
                regions=[
                    {"kind": "narrative", "min_width": 6.2, "flex": split_flexes[0]},
                    {"kind": "panel", "min_width": 3.4, "flex": split_flexes[1]},
                ],
                gap=0.35,
            )
            _, narrative_width = split_regions[0]
            panel_left, panel_width = split_regions[1]
            density = _region_density(width=narrative_width, height=1.55, body=slide.body)
            add_signal(
                region="summary:narrative",
                density=density,
                threshold=4.2,
                message="summary narrative region is dense enough to risk crowding",
            )
            width_ratio = _balance_ratio([narrative_width, panel_width])
            imbalance_score = round(_balance_ratio([narrative_weight, takeaway_weight]) / max(1.0, width_ratio), 3)
            add_signal(
                region="summary:split_imbalance",
                density=imbalance_score,
                threshold=0.9,
                message="summary narrative and takeaway panel are imbalanced enough to compete for space",
            )

            content_left, content_top, content_width, content_height = renderer.panel_inner_bounds(
                left=panel_left,
                top=2.1,
                width=panel_width,
                height=3.2,
                padding=0.26,
            )
            panel_regions = renderer.stack_vertical_regions(
                top=content_top,
                height=content_height,
                regions=[
                    {"kind": "heading", "height": 0.28},
                    {"kind": "bullets", "min_height": 2.18, "flex": 1.0},
                ],
                gap=0.08,
            )
            bullet_height = panel_regions[1][1][1]
            density = _region_density(width=content_width, height=bullet_height, bullets=slide.bullets)
            add_signal(
                region="summary:takeaways",
                density=density,
                threshold=3.8,
                message="summary takeaways panel is dense enough to risk clipping",
            )
            compact_takeaway_density = _region_density(
                width=content_width,
                height=max(0.72, bullet_height * 0.55),
                bullets=slide.bullets,
            )
            add_signal(
                region="summary:panel_width_pressure",
                density=compact_takeaway_density,
                threshold=4.2,
                message="summary takeaways are dense enough to overwhelm the side panel width",
            )
            bullet_weights = [renderer.estimate_content_weight(body=bullet) for bullet in slide.bullets]
            bullet_rows = renderer.build_weighted_rows(
                top=0.0,
                height=bullet_height,
                gap=0.08,
                weights=bullet_weights,
                min_height=0.24,
                min_flex=0.9,
                max_flex=1.15,
                kind_prefix="summary_takeaway",
            )
            for index, (bullet, (_, row_height)) in enumerate(zip(slide.bullets, bullet_rows, strict=True), start=1):
                row_density = _region_density(
                    width=content_width,
                    height=max(0.2, row_height - 0.06),
                    body=bullet,
                )
                add_signal(
                    region=f"summary:takeaway_{index}",
                    density=row_density,
                    threshold=4.5,
                    message=f"summary takeaway row {index} is dense enough to risk clipping inside the panel",
                )
        elif has_body:
            density = _region_density(width=g.content_width, height=1.9, body=slide.body)
            add_signal(
                region="summary:body",
                density=density,
                threshold=4.4,
                message="summary body region is dense enough to risk crowding",
            )
        elif has_bullets:
            density = _region_density(width=g.content_width - 0.56, height=1.9, bullets=slide.bullets)
            add_signal(
                region="summary:bullets",
                density=density,
                threshold=3.9,
                message="summary bullet panel is dense enough to risk crowding",
            )

    elif slide.type.value == "comparison":
        columns = slide.comparison_columns
        weights = [
            renderer.estimate_content_weight(
                title=column.title,
                body=column.body,
                bullets=column.bullets,
                footer=column.footer,
                tag=column.tag,
            )
            for column in columns
        ]
        flexes = renderer.normalize_content_flexes(weights, min_flex=0.95, max_flex=1.2)
        panel_bounds = renderer.build_panel_row_bounds(
            left=g.content_left,
            top=2.45,
            width=g.content_width,
            height=3.25,
            gap=0.42,
            min_width=3.6,
            regions=[
                {"kind": f"comparison_{index + 1}", "min_width": 3.6, "flex": flex}
                for index, flex in enumerate(flexes)
            ],
        )
        for index, (column, (left, panel_top, panel_width, panel_height)) in enumerate(zip(columns, panel_bounds, strict=True), start=1):
            content_left, content_top, content_width, content_height = renderer.panel_inner_bounds(
                left=left,
                top=panel_top,
                width=panel_width,
                height=panel_height,
                padding=0.28,
            )
            total_density = _region_density(
                width=content_width,
                height=content_height,
                title=column.title,
                body=column.body,
                bullets=column.bullets,
                footer=column.footer,
                tag=column.tag,
            )
            add_signal(
                region=f"comparison:column_{index}",
                density=total_density,
                threshold=3.7,
                message=f"column '{column.title}' is dense enough to risk internal collisions",
            )
            header_density = _region_density(
                width=content_width,
                height=0.42,
                title=column.title,
                tag=column.tag,
            )
            add_signal(
                region=f"comparison:column_{index}:header",
                density=header_density,
                threshold=4.95,
                message=f"comparison column {index} heading stack is dense enough to wrap awkwardly",
            )
            stack_regions: list[dict[str, float | str]] = [{"kind": "title", "height": 0.36}]
            if column.body:
                stack_regions.append(
                    {
                        "kind": "body",
                        "min_height": 0.7,
                        "flex": 1.0,
                        "content_weight": renderer.estimate_content_weight(body=column.body),
                    }
                )
            if column.bullets:
                stack_regions.append(
                    {
                        "kind": "bullets",
                        "min_height": 0.9,
                        "flex": 1.0,
                        "content_weight": renderer.estimate_content_weight(bullets=column.bullets),
                    }
                )
            if len(stack_regions) > 1:
                for region, (_, region_height) in renderer.build_content_stack(
                    top=content_top,
                    height=content_height,
                    regions=stack_regions,
                    gap=0.08,
                    min_flex=0.9,
                    max_flex=1.15,
                ):
                    if region["kind"] == "body" and column.body:
                        body_density = _region_density(width=content_width, height=region_height, body=column.body)
                        add_signal(
                            region=f"comparison:column_{index}:body",
                            density=body_density,
                            threshold=4.2,
                            message=f"comparison column {index} body is dense enough to crowd the panel",
                        )
                    elif region["kind"] == "bullets" and column.bullets:
                        bullet_density = _region_density(width=content_width, height=region_height, bullets=column.bullets)
                        add_signal(
                            region=f"comparison:column_{index}:bullets",
                            density=bullet_density,
                            threshold=4.0,
                            message=f"comparison column {index} bullets are dense enough to collide vertically",
                        )
                        bullet_weights = [renderer.estimate_content_weight(body=bullet) for bullet in column.bullets]
                        bullet_rows = renderer.build_weighted_rows(
                            top=0.0,
                            height=region_height,
                            gap=0.06,
                            weights=bullet_weights,
                            min_height=0.22,
                            min_flex=0.9,
                            max_flex=1.12,
                            kind_prefix=f"comparison_{index}_bullet",
                        )
                        for bullet_index, (bullet, (_, row_height)) in enumerate(
                            zip(column.bullets, bullet_rows, strict=True),
                            start=1,
                        ):
                            row_density = _region_density(
                                width=content_width,
                                height=max(0.18, row_height - 0.04),
                                body=bullet,
                            )
                            add_signal(
                                region=f"comparison:column_{index}:bullet_{bullet_index}",
                                density=row_density,
                                threshold=4.65,
                                message=f"comparison column {index} bullet row {bullet_index} is dense enough to clip inside the panel",
                            )

        width_ratio = _balance_ratio([panel_width for _, _, panel_width, _ in panel_bounds])
        imbalance_score = round(_balance_ratio(weights) / max(1.0, width_ratio), 3)
        add_signal(
            region="comparison:split_imbalance",
            density=imbalance_score,
            threshold=1.28,
            message="comparison columns are materially imbalanced and may compete for panel space",
        )

    elif slide.type.value == "two_column":
        columns = slide.two_column_columns
        weights = [
            renderer.estimate_content_weight(
                title=column.title,
                body=column.body,
                bullets=column.bullets,
                footer=column.footer,
                tag=column.tag,
            )
            for column in columns
        ]
        flexes = renderer.normalize_content_flexes(weights, min_flex=0.95, max_flex=1.25)
        panel_bounds = renderer.build_panel_row_bounds(
            left=g.content_left,
            top=2.45,
            width=g.content_width,
            height=3.25,
            gap=0.42,
            min_width=3.6,
            regions=[
                {"kind": f"two_column_{index + 1}", "min_width": 3.6, "flex": flex}
                for index, flex in enumerate(flexes)
            ],
        )
        for index, (column, (left, panel_top, panel_width, panel_height)) in enumerate(zip(columns, panel_bounds, strict=True), start=1):
            content_left, content_top, content_width, content_height = renderer.panel_inner_bounds(
                left=left,
                top=panel_top,
                width=panel_width,
                height=panel_height,
                padding=0.28,
            )
            total_density = _region_density(
                width=content_width,
                height=content_height,
                title=column.title,
                body=column.body,
                bullets=column.bullets,
                footer=column.footer,
                tag=column.tag,
            )
            add_signal(
                region=f"two_column:column_{index}",
                density=total_density,
                threshold=3.9,
                message=f"two-column panel {index} is dense enough to risk internal crowding",
            )
            header_density = _region_density(
                width=content_width,
                height=0.42,
                title=column.title,
                tag=column.tag,
            )
            add_signal(
                region=f"two_column:column_{index}:header",
                density=header_density,
                threshold=4.95,
                message=f"two-column panel {index} heading stack is dense enough to wrap awkwardly",
            )
            stack_regions: list[dict[str, float | str]] = [{"kind": "title", "height": 0.36}]
            if column.body:
                stack_regions.append(
                    {
                        "kind": "body",
                        "min_height": 0.82,
                        "flex": 1.0,
                        "content_weight": renderer.estimate_content_weight(body=column.body),
                    }
                )
            if column.bullets:
                stack_regions.append(
                    {
                        "kind": "bullets",
                        "min_height": 0.8,
                        "flex": 1.0,
                        "content_weight": renderer.estimate_content_weight(bullets=column.bullets),
                    }
                )
            if len(stack_regions) > 1:
                for region, (_, region_height) in renderer.build_content_stack(
                    top=content_top,
                    height=content_height,
                    regions=stack_regions,
                    gap=0.08,
                    min_flex=0.9,
                    max_flex=1.2,
                ):
                    if region["kind"] == "body" and column.body:
                        body_density = _region_density(width=content_width, height=region_height, body=column.body)
                        add_signal(
                            region=f"two_column:column_{index}:body",
                            density=body_density,
                            threshold=4.25,
                            message=f"two-column panel {index} body is dense enough to crowd the narrative region",
                        )
                    elif region["kind"] == "bullets" and column.bullets:
                        bullet_density = _region_density(width=content_width, height=region_height, bullets=column.bullets)
                        add_signal(
                            region=f"two_column:column_{index}:bullets",
                            density=bullet_density,
                            threshold=4.1,
                            message=f"two-column panel {index} bullets are dense enough to collide vertically",
                        )
                        bullet_weights = [renderer.estimate_content_weight(body=bullet) for bullet in column.bullets]
                        bullet_rows = renderer.build_weighted_rows(
                            top=0.0,
                            height=region_height,
                            gap=0.06,
                            weights=bullet_weights,
                            min_height=0.22,
                            min_flex=0.9,
                            max_flex=1.12,
                            kind_prefix=f"two_column_{index}_bullet",
                        )
                        for bullet_index, (bullet, (_, row_height)) in enumerate(
                            zip(column.bullets, bullet_rows, strict=True),
                            start=1,
                        ):
                            row_density = _region_density(
                                width=content_width,
                                height=max(0.18, row_height - 0.04),
                                body=bullet,
                            )
                            add_signal(
                                region=f"two_column:column_{index}:bullet_{bullet_index}",
                                density=row_density,
                                threshold=4.7,
                                message=f"two-column panel {index} bullet row {bullet_index} is dense enough to clip inside the panel",
                            )

        width_ratio = _balance_ratio([panel_width for _, _, panel_width, _ in panel_bounds])
        imbalance_score = round(_balance_ratio(weights) / max(1.0, width_ratio), 3)
        add_signal(
            region="two_column:split_imbalance",
            density=imbalance_score,
            threshold=1.32,
            message="two-column panels are materially imbalanced and may compete for space",
        )

    elif slide.type.value == "faq" and slide.faq_items:
        item_weights = [renderer.estimate_content_weight(title=item.title, body=item.body) for item in slide.faq_items]
        column_count = 2 if len(slide.faq_items) > 1 else 1
        row_count = 2 if len(slide.faq_items) > 2 else 1
        dense_faq = len(slide.faq_items) >= 4 or any(len(item.title) > 28 or len(item.body) > 115 for item in slide.faq_items)
        grid = renderer.build_constrained_panel_grid_content_bounds(
            left=g.content_left,
            top=2.2,
            width=g.content_width,
            height=3.28 if row_count > 1 else (1.72 if dense_faq else 1.58),
            column_gap=0.3 if dense_faq else 0.35,
            row_gap=0.18 if dense_faq else 0.24,
            column_regions=[
                {
                    "kind": f"faq_column_{column_index + 1}",
                    "min_width": 3.1,
                    "target_share": max(item_weights[column_index::column_count]),
                    "max_width": 5.15 if column_count > 1 else g.content_width,
                }
                for column_index in range(column_count)
            ],
            row_regions=[
                {
                    "kind": f"faq_row_{row_index + 1}",
                    "min_height": 1.18 if dense_faq else 1.12,
                    "target_share": max(
                        item_weights[row_index * column_count : (row_index + 1) * column_count]
                    ),
                    "max_height": 1.95 if row_count > 1 else (3.28 if dense_faq else 1.72),
                }
                for row_index in range(row_count)
            ],
            padding=0.2 if dense_faq else 0.22,
        )
        for index, item in enumerate(slide.faq_items, start=1):
            row = (index - 1) // column_count
            col = (index - 1) % column_count
            _, (content_left, content_top, content_width, content_height) = grid[row][col]
            density = _region_density(
                width=max(0.8, content_width),
                height=max(0.52, content_height),
                title=item.title,
                body=item.body,
            )
            add_signal(
                region=f"faq:item_{index}",
                density=density,
                threshold=3.4,
                message=f"FAQ item {index} is dense enough to risk cramped panel composition",
            )
            title_density = _region_density(
                width=max(0.8, content_width),
                height=max(0.26, content_height * 0.28),
                title=item.title,
            )
            add_signal(
                region=f"faq:item_{index}:header",
                density=title_density,
                threshold=4.45,
                message=f"FAQ item {index} heading is dense enough to wrap awkwardly",
            )
            body_density = _region_density(
                width=max(0.8, content_width),
                height=max(0.46, content_height * 0.68),
                body=item.body,
            )
            add_signal(
                region=f"faq:item_{index}:body",
                density=body_density,
                threshold=3.6,
                message=f"FAQ item {index} answer is dense enough to crowd the panel body",
            )
        add_signal(
            region="faq:grid_imbalance",
            density=_balance_ratio(item_weights),
            threshold=1.3,
            message="FAQ items are materially imbalanced and may create uneven panels",
        )

    elif slide.type.value == "closing":
        quote_text = slide.quote or slide.body or ""
        next_body = "Approve the narrative, connect your content pipeline, and reuse the same renderer across future decks."
        quote_weight = renderer.estimate_content_weight(
            title=slide.title,
            body=quote_text,
            footer=slide.attribution,
        )
        next_weight = renderer.estimate_content_weight(title="Next actions", body=next_body)
        columns = renderer.build_constrained_columns(
            left=g.content_left + 0.43,
            width=g.content_right - (g.content_left + 0.43),
            gap=0.34,
            regions=[
                {
                    "kind": "quote",
                    "min_width": 5.3,
                    "target_share": quote_weight,
                    "max_width": 7.35,
                },
                {
                    "kind": "panel",
                    "min_width": 2.8,
                    "target_share": next_weight,
                    "max_width": 4.0,
                },
            ],
        )
        quote_width = columns[0][1]
        panel_width = columns[1][1]
        dense_quote = bool(quote_weight >= 4.0 or len(quote_text) > 190)
        quote_density = _region_density(
            width=quote_width,
            height=1.98 if dense_quote else 1.72,
            title=slide.title,
            body=quote_text,
            footer=slide.attribution,
        )
        add_signal(
            region="closing:quote",
            density=quote_density,
            threshold=3.7,
            message="closing quote block is dense enough to lose impact or clip visually",
        )
        next_density = _region_density(
            width=max(1.8, panel_width - 0.6),
            height=2.1,
            title="Next actions",
            body=next_body,
        )
        add_signal(
            region="closing:panel",
            density=next_density,
            threshold=3.45,
            message="closing action panel is dense enough to feel cramped",
        )
        imbalance_score = round(
            _balance_ratio([quote_weight, next_weight]) / max(1.0, _balance_ratio([quote_width, panel_width])),
            3,
        )
        add_signal(
            region="closing:split_imbalance",
            density=imbalance_score,
            threshold=1.1,
            message="closing quote and action panel are imbalanced enough to compete for space",
        )
        if slide.attribution:
            attribution_density = _region_density(
                width=min(quote_width, 4.2),
                height=0.35,
                body=slide.attribution,
            )
            add_signal(
                region="closing:attribution",
                density=attribution_density,
                threshold=5.2,
                message="closing attribution is dense enough to wrap awkwardly below the quote",
            )

    elif slide.type.value == "section":
        semantic = renderer.resolve_semantic_layout(slide.type.value, slide.layout_variant)
        has_visual = bool(slide.image_path)
        section_columns = renderer.build_named_columns(
            left=g.content_left,
            width=g.content_width,
            gap=0.42,
            regions=[
                {
                    "kind": "section_content",
                    "min_width": 6.6 if has_visual else 7.2,
                    "target_share": renderer.estimate_content_weight(
                        title=slide.title,
                        body=slide.subtitle,
                        tag=slide.section_label or slide.eyebrow or "SECTION",
                    ),
                },
                *(
                    [{"kind": "section_visual", "width": 2.55, "min_width": 2.2}]
                    if has_visual
                    else [{"kind": "section_marker", "width": 1.65, "min_width": 1.5}]
                ),
            ],
        )
        content_left, content_width = section_columns["section_content"]
        _ = content_left
        heading_density = _region_density(
            width=content_width,
            height=max(0.9, semantic.body_top - semantic.heading_top + 0.18),
            title=slide.title,
            body=slide.subtitle,
            tag=slide.section_label or slide.eyebrow,
        )
        add_signal(
            region="section:heading",
            density=heading_density,
            threshold=2.35,
            message="section heading stack is dense enough to crowd the chapter transition",
        )

    elif slide.type.value == "cards" and slide.cards:
        card_weights = [
            renderer.estimate_content_weight(title=card.title, body=card.body, footer=card.footer)
            for card in slide.cards
        ]
        dense_cards = any(weight >= 2.25 for weight in card_weights) or any(len(card.body) > 90 for card in slide.cards)
        card_bounds = renderer.build_named_panel_row_content_bounds(
            left=g.content_left,
            top=2.55,
            width=g.content_width,
            height=3.08 if dense_cards else 2.95,
            gap=0.28 if dense_cards else 0.35,
            min_width=3.0,
            regions=[
                {"kind": f"card_{index + 1}", "min_width": 3.0, "flex": flex}
                for index, flex in enumerate(renderer.normalize_content_flexes(card_weights, min_flex=0.95, max_flex=1.25))
            ],
        )
        card_densities: list[float] = []
        for index, card in enumerate(slide.cards, start=1):
            content_bounds = card_bounds[f"card_{index}"]["content"]
            density = _region_density(
                width=content_bounds[2],
                height=content_bounds[3],
                title=card.title,
                body=card.body,
                footer=card.footer,
            )
            card_densities.append(density)
        if card_densities:
            add_signal(
                region="cards:grid_density",
                density=sum(card_densities) / len(card_densities),
                threshold=3.15,
                message="cards grid is dense enough to risk cramped multi-panel composition",
            )

    elif slide.type.value == "chart" and slide.chart_categories:
        chart_density = _region_density(
            width=g.content_width,
            height=0.42,
            body=" ".join(slide.chart_categories),
        )
        add_signal(
            region="chart:category_labels",
            density=chart_density,
            threshold=4.0,
            message="chart category labels are dense enough to wrap awkwardly or collide visually",
        )

    elif slide.type.value == "image_text" and slide.image_path:
        split_regions = renderer.build_named_columns(
            left=g.content_left,
            width=g.content_width,
            gap=0.42,
            regions=[
                {
                    "kind": "text",
                    "min_width": 5.2,
                    "target_share": renderer.estimate_content_weight(
                        title=slide.title,
                        body=slide.body,
                        bullets=slide.bullets,
                        footer=slide.subtitle,
                        tag=slide.eyebrow,
                    ),
                },
                {"kind": "visual", "width": 5.15, "min_width": 4.8},
            ],
        )
        text_width = split_regions["text"][1]
        split_density = _region_density(
            width=text_width,
            height=3.1,
            body=slide.body,
            bullets=slide.bullets,
        )
        add_signal(
            region="image_text:visual_split",
            density=split_density,
            threshold=2.7,
            message="image-text narrative region is dense enough to compete with the visual split",
        )


    elif slide.type.value == "table" and slide.table_rows and slide.table_columns:
        column_flexes = renderer.normalize_content_flexes(
            [
                renderer.estimate_content_weight(
                    title=column,
                    body=" ".join(row[index] for row in slide.table_rows if index < len(row)),
                )
                for index, column in enumerate(slide.table_columns)
            ],
            min_flex=0.85,
            max_flex=1.5,
        )
        column_bounds = renderer.build_columns(
            left=g.content_left,
            width=g.content_width,
            gap=0.06,
            min_width=1.0,
            regions=[
                {"kind": f"column_{index + 1}", "min_width": 1.0, "flex": flex}
                for index, flex in enumerate(column_flexes)
            ],
        )
        estimated_table_height = 0.42 + (0.46 * len(slide.table_rows))
        for col_index, (column_name, (_, column_width)) in enumerate(zip(slide.table_columns, column_bounds, strict=True), start=1):
            column_body = " ".join(row[col_index - 1] for row in slide.table_rows if col_index - 1 < len(row))
            column_density = _region_density(
                width=max(0.4, column_width - 0.12),
                height=max(0.52, estimated_table_height - 0.16),
                title=column_name,
                body=column_body,
            )
            add_signal(
                region=f"table:column_{col_index}",
                density=column_density,
                threshold=2.8,
                message=f"table column {col_index} is dense enough to risk cramped cells across multiple rows",
            )
            header_density = _region_density(
                width=max(0.4, column_width - 0.12),
                height=0.42,
                title=column_name,
            )
            header_threshold = 1.9 if len(column_name) > 22 else 2.45
            add_signal(
                region=f"table:header_{col_index}",
                density=header_density,
                threshold=header_threshold,
                message=f"table header {col_index} is dense enough to wrap awkwardly or steal row space",
            )
        for row_index, row in enumerate(slide.table_rows, start=1):
            row_density = _region_density(
                width=g.content_width,
                height=max(0.34, (estimated_table_height / max(1, len(slide.table_rows))) - 0.06),
                body=" ".join(row),
            )
            add_signal(
                region=f"table:row_{row_index}",
                density=row_density,
                threshold=7.1,
                message=f"table row {row_index} is dense enough to compress vertically",
            )
            for col_index, (cell, (_, column_width)) in enumerate(zip(row, column_bounds, strict=True), start=1):
                density = _region_density(width=max(0.4, column_width - 0.12), height=0.32, body=cell)
                add_signal(
                    region=f"table:r{row_index}c{col_index}",
                    density=density,
                    threshold=8.0,
                    message=f"table cell r{row_index}c{col_index} is dense enough to risk clipping",
                )
        row_weights = [renderer.estimate_content_weight(body=" ".join(row)) for row in slide.table_rows]
        add_signal(
            region="table:row_imbalance",
            density=_balance_ratio(row_weights),
            threshold=1.05,
            message="table rows vary significantly in density and may create visual imbalance",
        )

    return signals


def _slide_content_weight(renderer: PresentationRenderer, slide: Slide) -> float:
    weight = renderer.estimate_content_weight(
        title=slide.title,
        body=slide.body,
        bullets=slide.bullets,
        footer=slide.attribution or slide.image_caption,
        tag=slide.eyebrow or slide.section_label,
    )
    weight += sum(
        renderer.estimate_content_weight(title=card.title, body=card.body, footer=card.footer)
        for card in slide.cards
    )
    weight += sum(
        renderer.estimate_content_weight(title=metric.label, body=metric.detail, footer=metric.trend)
        for metric in slide.metrics
    )
    weight += sum(
        renderer.estimate_content_weight(title=item.title, body=item.body, footer=item.footer, tag=item.tag)
        for item in slide.timeline_items
    )
    weight += sum(
        renderer.estimate_content_weight(
            title=column.title,
            body=column.body,
            bullets=column.bullets,
            footer=column.footer,
            tag=column.tag,
        )
        for column in slide.comparison_columns + slide.two_column_columns
    )
    weight += sum(
        renderer.estimate_content_weight(title=item.title, body=item.body)
        for item in slide.faq_items
    )
    if slide.table_rows:
        weight += sum(renderer.estimate_content_weight(body=" ".join(row)) for row in slide.table_rows)
    if slide.chart_categories:
        weight += renderer.estimate_content_weight(body=" ".join(slide.chart_categories))
    return round(weight, 2)


def _risk_score(slide_review: dict[str, object]) -> float:
    severity_counts = slide_review["severity_counts"]
    return (
        float(slide_review["overflow_risk_count"]) * 2.0
        + float(slide_review["collision_risk_count"]) * 1.7
        + float(slide_review["balance_warning_count"]) * 1.2
        + float(slide_review["layout_pressure_score"]) * 0.45
        + float(severity_counts["high"]) * 2.5
        + float(severity_counts["medium"]) * 1.4
        + float(severity_counts["low"]) * 0.6
    )


def _recompute_slide_review(slide_review: dict[str, object]) -> dict[str, object]:
    slide_review["severity_counts"] = _severity_counts(slide_review["issues"])
    slide_review["score"] = _score_from_issues(slide_review["issues"])
    if slide_review["score"] >= 90:
        slide_review["status"] = "ok"
    elif slide_review["score"] >= 70:
        slide_review["status"] = "review"
    else:
        slide_review["status"] = "attention"

    severity_counts = slide_review["severity_counts"]
    risk_level = "low"
    if (
        int(slide_review["clipping_risk_count"]) >= 2
        or int(slide_review["collision_risk_count"]) >= 2
        or int(severity_counts["high"])
    ):
        risk_level = "high"
    elif (
        int(slide_review["overflow_risk_count"])
        or int(slide_review["collision_risk_count"])
        or int(slide_review["balance_warning_count"])
    ):
        risk_level = "medium"
    slide_review["risk_level"] = risk_level
    slide_review["likely_overflow_regions"] = sorted(set(slide_review["likely_overflow_regions"]))
    slide_review["likely_collision_regions"] = sorted(set(slide_review["likely_collision_regions"]))
    return slide_review


def _rebuild_review_result(review: dict[str, object]) -> dict[str, object]:
    slides = review["slides"]
    all_issues = [
        f"slide {slide['slide_number']:02d} ({slide['title']}): {issue['message']}"
        for slide in slides
        for issue in slide["issues"]
    ]
    average_score = int(sum(int(slide["score"]) for slide in slides) / len(slides)) if slides else 100
    overall_status = "ok" if average_score >= 90 else "review" if average_score >= 70 else "attention"
    severity_counts = {
        "high": sum(int(slide["severity_counts"]["high"]) for slide in slides),
        "medium": sum(int(slide["severity_counts"]["medium"]) for slide in slides),
        "low": sum(int(slide["severity_counts"]["low"]) for slide in slides),
    }
    review.update(
        {
            "average_score": average_score,
            "status": overall_status,
            "issue_count": len(all_issues),
            "warning_count": len(all_issues),
            "severity_counts": severity_counts,
            "overflow_risk_count": sum(int(slide["overflow_risk_count"]) for slide in slides),
            "clipping_risk_count": sum(int(slide["clipping_risk_count"]) for slide in slides),
            "collision_risk_count": sum(int(slide["collision_risk_count"]) for slide in slides),
            "balance_warning_count": sum(int(slide["balance_warning_count"]) for slide in slides),
            "top_risk_slides": [
                {
                    "slide_number": slide["slide_number"],
                    "title": slide["title"],
                    "risk_level": slide["risk_level"],
                    "overflow_risk_count": slide["overflow_risk_count"],
                    "clipping_risk_count": slide["clipping_risk_count"],
                    "collision_risk_count": slide["collision_risk_count"],
                    "balance_warning_count": slide["balance_warning_count"],
                    "layout_pressure_score": slide["layout_pressure_score"],
                }
                for slide in sorted(slides, key=_risk_score, reverse=True)[:5]
                if _risk_score(slide) > 0
            ],
            "issues": all_issues,
            "warnings": all_issues,
        }
    )
    return review


def augment_review_with_preview_artifacts(
    review: dict[str, object],
    preview_result: dict[str, object] | None,
) -> dict[str, object]:
    artifact_review = (preview_result or {}).get("preview_artifact_review") or {}
    artifact_slides = artifact_review.get("slides") or []
    if not artifact_slides:
        return review

    merged = deepcopy(review)
    slide_lookup = {int(slide["slide_number"]): slide for slide in merged.get("slides", [])}

    def _append_issue(
        slide_review: dict[str, object],
        *,
        severity: str,
        message: str,
        overflow_region: str | None = None,
        collision_region: str | None = None,
        clipping: int = 0,
        collision: int = 0,
    ) -> None:
        if not any(issue["message"] == message for issue in slide_review["issues"]):
            slide_review["issues"].append(_issue(severity, message))
        slide_review["clipping_risk_count"] += clipping
        slide_review["collision_risk_count"] += collision
        if overflow_region:
            slide_review["likely_overflow_regions"].append(overflow_region)
            slide_review["overflow_risk_count"] += 1
        if collision_region:
            slide_review["likely_collision_regions"].append(collision_region)

    for artifact_slide in artifact_slides:
        if not isinstance(artifact_slide, dict):
            continue
        slide_review = slide_lookup.get(int(artifact_slide.get("slide_number") or 0))
        if not slide_review:
            continue

        if artifact_slide.get("edge_contact"):
            _append_issue(
                slide_review,
                severity="high",
                message="final preview indicates content touching the slide edge",
                overflow_region="preview_edge",
                collision_region="preview_edge",
                clipping=1,
                collision=1,
            )
        elif artifact_slide.get("safe_margin_warning"):
            _append_issue(
                slide_review,
                severity="low",
                message="final preview indicates content approaching the outer slide margin",
                overflow_region="preview_margin",
                clipping=1,
            )
        if artifact_slide.get("body_edge_contact"):
            _append_issue(
                slide_review,
                severity="high",
                message="final preview indicates body content touching a boundary before the footer",
                overflow_region="preview_body_edge",
                collision_region="preview_body_edge",
                clipping=1,
                collision=1,
            )
        if artifact_slide.get("safe_area_intrusion"):
            _append_issue(
                slide_review,
                severity="high",
                message="final preview indicates unsafe margin intrusion",
                overflow_region="preview_safe_area",
                collision_region="preview_safe_area",
                clipping=1,
                collision=1,
            )
        if artifact_slide.get("footer_intrusion_warning"):
            _append_issue(
                slide_review,
                severity="medium",
                message="final preview indicates crowding near the footer boundary",
                overflow_region="preview_footer",
                collision_region="preview_footer",
                clipping=1,
                collision=1,
            )
        if artifact_slide.get("edge_density_warning"):
            _append_issue(
                slide_review,
                severity="medium",
                message="final preview indicates aggressive edge packing",
                collision_region="preview_edge_density",
                collision=1,
            )
        if artifact_slide.get("corner_density_warning"):
            _append_issue(
                slide_review,
                severity="medium",
                message="final preview indicates dense corner packing that may hide clipping or collisions",
                collision_region="preview_corner_density",
                collision=1,
            )

        _recompute_slide_review(slide_review)

    merged["preview_artifact_review"] = artifact_review
    return _rebuild_review_result(merged)


def review_preview_artifacts(
    preview_result: dict[str, object],
    *,
    input_pptx: str | None = None,
) -> dict[str, object]:
    artifact_review = (preview_result or {}).get("preview_artifact_review") or {}
    visual_regression = (preview_result or {}).get("visual_regression")
    slides: list[dict[str, object]] = []

    for artifact_slide in artifact_review.get("slides") or []:
        slide_number = int(artifact_slide.get("slide_number") or 0)
        issues: list[dict[str, str]] = []
        likely_overflow_regions: list[str] = []
        likely_collision_regions: list[str] = []
        overflow_risk_count = 0
        clipping_risk_count = 0
        collision_risk_count = 0
        balance_warning_count = 0

        def add_issue(
            *,
            severity: str,
            message: str,
            overflow_region: str | None = None,
            collision_region: str | None = None,
            clipping: int = 0,
            collision: int = 0,
        ) -> None:
            issues.append(_issue(severity, message))
            if overflow_region:
                likely_overflow_regions.append(overflow_region)
            if collision_region:
                likely_collision_regions.append(collision_region)
            nonlocal overflow_risk_count, clipping_risk_count, collision_risk_count
            overflow_risk_count += 1 if overflow_region else 0
            clipping_risk_count += clipping
            collision_risk_count += collision

        if artifact_slide.get("edge_contact"):
            add_issue(
                severity="high",
                message="final preview indicates content touching the slide edge",
                overflow_region="preview_edge",
                collision_region="preview_edge",
                clipping=1,
                collision=1,
            )
        elif artifact_slide.get("safe_margin_warning"):
            add_issue(
                severity="low",
                message="final preview indicates content approaching the outer slide margin",
                overflow_region="preview_margin",
                clipping=1,
            )
        if artifact_slide.get("body_edge_contact"):
            add_issue(
                severity="high",
                message="final preview indicates body content touching a boundary before the footer",
                overflow_region="preview_body_edge",
                collision_region="preview_body_edge",
                clipping=1,
                collision=1,
            )
        if artifact_slide.get("safe_area_intrusion"):
            add_issue(
                severity="high",
                message="final preview indicates unsafe margin intrusion",
                overflow_region="preview_safe_area",
                collision_region="preview_safe_area",
                clipping=1,
                collision=1,
            )
        if artifact_slide.get("footer_intrusion_warning"):
            add_issue(
                severity="medium",
                message="final preview indicates crowding near the footer boundary",
                overflow_region="preview_footer",
                collision_region="preview_footer",
                clipping=1,
                collision=1,
            )
        if artifact_slide.get("edge_density_warning"):
            add_issue(
                severity="medium",
                message="final preview indicates aggressive edge packing",
                collision_region="preview_edge_density",
                collision=1,
            )
        if artifact_slide.get("corner_density_warning"):
            add_issue(
                severity="medium",
                message="final preview indicates dense corner packing that may hide clipping or collisions",
                collision_region="preview_corner_density",
                collision=1,
            )

        slides.append(
            _recompute_slide_review(
                {
                    "slide_number": slide_number,
                    "slide_type": "rendered_artifact",
                    "title": f"Slide {slide_number:02d}",
                    "score": 100,
                    "status": "ok",
                    "content_weight": 0.0,
                    "overflow_risk_count": overflow_risk_count,
                    "clipping_risk_count": clipping_risk_count,
                    "collision_risk_count": collision_risk_count,
                    "balance_warning_count": balance_warning_count,
                    "layout_pressure_score": round(
                        float(artifact_slide.get("body_max_edge_ratio") or 0.0)
                        + float(artifact_slide.get("max_corner_ratio") or 0.0),
                        3,
                    ),
                    "risk_level": "low",
                    "likely_overflow_regions": likely_overflow_regions,
                    "likely_collision_regions": likely_collision_regions,
                    "layout_pressure_signals": [],
                    "severity_counts": {"high": 0, "medium": 0, "low": 0},
                    "issues": issues,
                }
            )
        )

    if visual_regression is not None:
        regression_lookup = {
            int(slide_report["slide_number"]): slide_report
            for slide_report in visual_regression.get("slides") or []
            if slide_report.get("regression")
        }
        for slide in slides:
            regression = regression_lookup.get(int(slide["slide_number"]))
            if not regression:
                continue
            slide["issues"].append(_issue("medium", "final preview differs from baseline and needs visual review"))
            slide["collision_risk_count"] += 1
            slide["likely_collision_regions"].append("visual_regression")
            _recompute_slide_review(slide)

    review = _rebuild_review_result(
        {
            "mode": "review-preview-artifacts",
            "presentation_title": input_pptx or preview_result.get("input_pptx") or "Rendered artifact review",
            "theme": preview_result.get("theme") or None,
            "slide_count": int(preview_result.get("preview_count") or len(slides)),
            "slides": slides,
            "missing_assets": [],
        }
    )
    review["preview_artifact_review"] = artifact_review
    review["visual_regression"] = visual_regression
    review["regression_diff_count"] = int((visual_regression or {}).get("diff_count") or 0)
    review["input_pptx"] = input_pptx or preview_result.get("input_pptx")
    return review


def _review_slide(
    slide: Slide,
    *,
    slide_number: int,
    asset_missing: bool,
    renderer: PresentationRenderer,
) -> dict[str, object]:
    issues: list[dict[str, str]] = []
    title = slide.title or slide.type.value
    overflow_risk_count = 0
    clipping_risk_count = 0
    collision_risk_count = 0
    balance_warning_count = 0
    content_weight = _slide_content_weight(renderer, slide)
    likely_overflow_regions: list[str] = []
    likely_collision_regions: list[str] = []

    if len(title) > 72:
        issues.append(_issue("medium", "title is long and may wrap awkwardly"))
    if slide.subtitle and len(slide.subtitle) > 120:
        issues.append(_issue("medium", "subtitle is long and may reduce visual clarity"))
    if slide.body and len(slide.body) > 260:
        issues.append(_issue("high", "body text is dense for a single executive slide"))
        clipping_risk_count += 1
        likely_overflow_regions.append("body")

    if slide.bullets:
        if len(slide.bullets) > 5:
            issues.append(_issue("high", "too many bullets for executive readability"))
            clipping_risk_count += 1
            likely_overflow_regions.append("bullets")
        long_bullets = [bullet for bullet in slide.bullets if len(bullet) > 95]
        if long_bullets:
            issues.append(_issue("medium", "one or more bullets are too long"))
            clipping_risk_count += 1
            likely_overflow_regions.append("bullets")

    if slide.cards:
        verbose_cards = [card.title for card in slide.cards if len(card.body) > 150]
        if verbose_cards:
            issues.append(_issue("medium", f"verbose card bodies: {', '.join(verbose_cards)}"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("cards")
        card_weights = [
            renderer.estimate_content_weight(title=card.title, body=card.body, footer=card.footer)
            for card in slide.cards
        ]
        if _balance_ratio(card_weights) >= 1.55:
            issues.append(_issue("low", "card content looks uneven and may create visual imbalance"))
            balance_warning_count += 1

    if slide.metrics:
        long_metric_labels = [metric.label for metric in slide.metrics if len(metric.label) > 28]
        if long_metric_labels:
            issues.append(_issue("low", "some metric labels are long for compact KPI cards"))
        metric_weights = [
            renderer.estimate_content_weight(title=metric.label, body=metric.detail, footer=metric.trend)
            for metric in slide.metrics
        ]
        if metric_weights and max(metric_weights) > 3.0:
            issues.append(_issue("medium", "one or more metric cards may feel too dense"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("metrics")
        if _balance_ratio(metric_weights) >= 1.45:
            issues.append(_issue("low", "metric cards may feel visually uneven"))
            balance_warning_count += 1

    if slide.timeline_items and len(slide.timeline_items) > 4:
        issues.append(_issue("medium", "timeline may feel crowded with many steps"))
        overflow_risk_count += 1
        clipping_risk_count += 1
        likely_overflow_regions.append("timeline")

    comparison_like = slide.comparison_columns or slide.two_column_columns
    comparison_weights: list[float] = []
    for column in comparison_like:
        if column.body and len(column.body) > 150:
            issues.append(_issue("medium", f"column '{column.title}' body may be too dense"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append(f"column:{column.title}:body")
        if len(column.bullets) > 3:
            issues.append(_issue("medium", f"column '{column.title}' has many bullets"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append(f"column:{column.title}:bullets")
        comparison_weights.append(
            renderer.estimate_content_weight(
                title=column.title,
                body=column.body,
                bullets=column.bullets,
                footer=column.footer,
                tag=column.tag,
            )
        )

    if comparison_weights and _balance_ratio(comparison_weights) >= 1.65:
        issues.append(_issue("medium", "comparison-like columns are imbalanced and may compete for space"))
        balance_warning_count += 1

    if slide.table_rows:
        if len(slide.table_rows) > 6:
            issues.append(_issue("high", "table has many rows and may feel overloaded"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("table")
        if len(slide.table_columns) > 4:
            issues.append(_issue("medium", "table has many columns for executive readability"))
        any_long_cells = any(len(cell) > 38 for row in slide.table_rows for cell in row)
        if any_long_cells:
            issues.append(_issue("medium", "some table cells are likely too long"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("table")
        row_weights = [renderer.estimate_content_weight(body=" ".join(row)) for row in slide.table_rows]
        if _balance_ratio(row_weights) >= 1.75:
            issues.append(_issue("low", "table rows vary significantly in density and may look uneven"))
            balance_warning_count += 1

    if slide.faq_items:
        if len(slide.faq_items) > 3:
            issues.append(_issue("medium", "FAQ slide may feel crowded"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("faq")
        verbose_answers = [item.title for item in slide.faq_items if len(item.body) > 150]
        if verbose_answers:
            issues.append(_issue("medium", "some FAQ answers are too long"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("faq")
        faq_weights = [renderer.estimate_content_weight(title=item.title, body=item.body) for item in slide.faq_items]
        if _balance_ratio(faq_weights) >= 1.7:
            issues.append(_issue("low", "FAQ items are imbalanced and may produce uneven panels"))
            balance_warning_count += 1

    if slide.chart_categories:
        if len(slide.chart_categories) > 6:
            issues.append(_issue("medium", "chart has many categories for a clean executive view"))
        if len(slide.chart_series) > 3:
            issues.append(_issue("low", "chart has many series and may become visually busy"))

    if slide.type.value in {"agenda", "bullets", "image_text", "summary"} and slide.body and slide.bullets:
        mixed_weights = [
            renderer.estimate_content_weight(body=slide.body),
            renderer.estimate_content_weight(bullets=slide.bullets),
        ]
        if _balance_ratio(mixed_weights) >= 1.8:
            issues.append(_issue("low", "body and bullet regions are imbalanced and may compete for vertical space"))
            balance_warning_count += 1
        if sum(mixed_weights) >= 5.4:
            issues.append(_issue("medium", "mixed narrative content is dense and may overflow vertically"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("mixed_text")

    if slide.type.value == "agenda":
        bullet_weights = [renderer.estimate_content_weight(body=bullet) for bullet in slide.bullets]
        if bullet_weights and max(bullet_weights) > 2.1:
            issues.append(_issue("medium", "one or more agenda rows are too verbose"))
            overflow_risk_count += 1
            clipping_risk_count += 1
            likely_overflow_regions.append("agenda_rows")

    if slide.type.value == "closing" and len((slide.quote or slide.body or "")) > 220:
        issues.append(_issue("medium", "closing quote is long and may reduce visual impact"))
        overflow_risk_count += 1
        clipping_risk_count += 1
        likely_overflow_regions.append("closing_quote")

    if asset_missing:
        issues.append(_issue("medium", "image asset is missing and will fall back to placeholder"))

    layout_pressure_signals = _build_layout_pressure_signals(renderer, slide)
    layout_pressure_score = round(
        sum(float(signal["density"]) - float(signal["threshold"]) for signal in layout_pressure_signals),
        2,
    )
    for signal in layout_pressure_signals:
        issues.append(_issue(str(signal["severity"]), str(signal["message"])))
        collision_risk_count += 1
        likely_collision_regions.append(str(signal["region"]))

    score = _score_from_issues(issues)
    if score >= 90:
        status = "ok"
    elif score >= 70:
        status = "review"
    else:
        status = "attention"

    risk_level = "low"
    if clipping_risk_count >= 2 or collision_risk_count >= 2 or _severity_counts(issues)["high"]:
        risk_level = "high"
    elif overflow_risk_count or collision_risk_count or balance_warning_count:
        risk_level = "medium"

    return {
        "slide_number": slide_number,
        "slide_type": slide.type.value,
        "title": title,
        "score": score,
        "status": status,
        "content_weight": content_weight,
        "overflow_risk_count": overflow_risk_count,
        "clipping_risk_count": clipping_risk_count,
        "collision_risk_count": collision_risk_count,
        "balance_warning_count": balance_warning_count,
        "layout_pressure_score": layout_pressure_score,
        "risk_level": risk_level,
        "likely_overflow_regions": sorted(set(likely_overflow_regions)),
        "likely_collision_regions": sorted(set(likely_collision_regions)),
        "layout_pressure_signals": layout_pressure_signals,
        "severity_counts": _severity_counts(issues),
        "issues": issues,
    }


def review_presentation(
    spec: PresentationInput,
    *,
    asset_root: str | Path | None = None,
    theme_name: str | None = None,
) -> dict[str, object]:
    renderer = PresentationRenderer(theme_name=theme_name or spec.presentation.theme, asset_root=asset_root)
    missing_assets = renderer.collect_missing_assets(spec)
    missing_asset_lookup = set(missing_assets)

    slides = []
    for index, slide in enumerate(spec.slides, start=1):
        title = slide.title or slide.type.value
        asset_missing = any(
            message.startswith(f"slide {index:02d} ({title})") or message.startswith(f"slide {index:02d} ({slide.type.value})")
            for message in missing_asset_lookup
        )
        slides.append(
            _review_slide(
                slide,
                slide_number=index,
                asset_missing=asset_missing,
                renderer=renderer,
            )
        )

    return _rebuild_review_result(
        {
        "mode": "review",
        "presentation_title": spec.presentation.title,
        "theme": spec.presentation.theme,
        "slide_count": len(spec.slides),
        "slides": slides,
        "missing_assets": missing_assets,
        }
    )
