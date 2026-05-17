from __future__ import annotations

import json
import shutil
from pathlib import Path

from ppt_creator.preview import render_previews
from ppt_creator.schema import PresentationInput


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    examples_dir = root / "examples"
    gallery_dir = root / "docs" / "gallery"
    gallery_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, object]] = []
    for example_path in sorted(path for path in examples_dir.glob("*.json") if not path.name.startswith("briefing_")):
        spec = PresentationInput.from_path(example_path)
        output_dir = gallery_dir / example_path.stem
        if output_dir.exists():
            shutil.rmtree(output_dir)
        result = render_previews(
            spec,
            output_dir,
            theme_name=spec.presentation.theme,
            asset_root=examples_dir,
            basename=example_path.stem,
            backend="synthetic",
        )
        manifest.append(
            {
                "example": example_path.name,
                "title": spec.presentation.title,
                "slide_count": len(spec.slides),
                "thumbnail_sheet": str(Path(result["thumbnail_sheet"]).relative_to(root)),
                "preview_dir": str(output_dir.relative_to(root)),
            }
        )

    (gallery_dir / "manifest.json").write_text(
        json.dumps({"items": manifest}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] Gallery generated in {gallery_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())