from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ppt_creator.preview import render_previews_for_rendered_artifact
from ppt_creator.qa import review_presentation
from ppt_creator.renderer import PresentationRenderer
from ppt_creator.schema import PresentationInput


AUDITED_LAYOUTS = [
    "title",
    "metrics",
    "comparison",
    "two_column",
    "table",
    "faq",
    "summary",
    "closing",
]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    input_path = root / "examples" / "layout_showcase.json"
    output_dir = root / "docs" / "layout_audit"
    output_dir.mkdir(parents=True, exist_ok=True)

    spec = PresentationInput.from_path(input_path)
    review = review_presentation(spec, asset_root=root / "examples", theme_name=spec.presentation.theme)

    with TemporaryDirectory(prefix="ppt_creator_layout_audit_") as tmpdir:
        temp_pptx = Path(tmpdir) / "layout_showcase.pptx"
        PresentationRenderer(theme_name=spec.presentation.theme, asset_root=root / "examples").render(spec, temp_pptx)
        preview_result, preview_source = render_previews_for_rendered_artifact(
            spec,
            output_dir,
            rendered_pptx=temp_pptx,
            theme_name=spec.presentation.theme,
            asset_root=root / "examples",
            basename="layout_showcase_audit",
            backend="auto",
        )

    slide_lookup = {slide["slide_type"]: slide for slide in review["slides"]}
    audited = [
        {
            "layout": layout,
            "status": slide_lookup[layout]["status"],
            "score": slide_lookup[layout]["score"],
            "risk_level": slide_lookup[layout]["risk_level"],
            "issues": slide_lookup[layout]["issues"],
            "likely_overflow_regions": slide_lookup[layout]["likely_overflow_regions"],
            "likely_collision_regions": slide_lookup[layout]["likely_collision_regions"],
        }
        for layout in AUDITED_LAYOUTS
        if layout in slide_lookup
    ]

    report = {
        "mode": "layout-audit",
        "input": str(input_path.relative_to(root)),
        "theme": spec.presentation.theme,
        "preview_source": preview_source,
        "preview_manifest": preview_result.get("preview_manifest"),
        "thumbnail_sheet": preview_result.get("thumbnail_sheet"),
        "review_status": review["status"],
        "average_score": review["average_score"],
        "audited_layouts": audited,
    }
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Layout audit",
        "",
        f"- input: `{input_path.relative_to(root)}`",
        f"- theme: `{spec.presentation.theme}`",
        f"- preview source: `{preview_source}`",
        f"- average score: `{review['average_score']}`",
        "",
    ]
    if preview_result.get("thumbnail_sheet"):
        thumb = Path(str(preview_result["thumbnail_sheet"])).relative_to(root)
        lines.extend(["## Thumbnail sheet", "", f"![Layout audit]({thumb.as_posix()})", ""])
    lines.extend(["## Audited layouts", ""])
    for item in audited:
        lines.append(f"### {item['layout']}")
        lines.append("")
        lines.append(f"- status: `{item['status']}`")
        lines.append(f"- score: `{item['score']}`")
        lines.append(f"- risk level: `{item['risk_level']}`")
        if item["likely_overflow_regions"]:
            lines.append(f"- overflow regions: `{', '.join(item['likely_overflow_regions'])}`")
        if item["likely_collision_regions"]:
            lines.append(f"- collision regions: `{', '.join(item['likely_collision_regions'])}`")
        if item["issues"]:
            lines.append("- issues:")
            for issue in item["issues"]:
                lines.append(f"  - [{issue['severity']}] {issue['message']}")
        else:
            lines.append("- issues: none")
        lines.append("")
    (output_dir / "report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    print(f"[OK] Layout audit written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())