from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import EvidencePipelineConfig
from .pipeline.runner import run_cv_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Evidence-grounded CV extraction pipeline")
    parser.add_argument("parse", nargs="?")
    parser.add_argument("pdf_path")
    parser.add_argument("--out", required=True)
    parser.add_argument("--ocr-backend", choices=["ocrmypdf", "docling"], default="ocrmypdf")
    parser.add_argument("--debug-dir", default=None)
    args = parser.parse_args()

    config = EvidencePipelineConfig(
        ocr_backend=args.ocr_backend,
        debug_dir=Path(args.debug_dir) if args.debug_dir else None,
    )
    result = run_cv_pipeline(args.pdf_path, config)
    Path(args.out).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())