from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader

from ..config import EvidencePipelineConfig
from ..schemas import PageExtraction


class OCRMyPDFBackend:
    def __init__(self, config: EvidencePipelineConfig) -> None:
        self.config = config

    def extract(self, pdf_path: Path) -> list[PageExtraction]:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_pdf = Path(temp_dir) / "ocr.pdf"
            sidecar = Path(temp_dir) / "ocr.txt"
            command = [
                "ocrmypdf",
                "--force-ocr",
                "--skip-big",
                "50",
                "--output-type",
                "pdf",
                "--sidecar",
                str(sidecar),
                str(pdf_path),
                str(out_pdf),
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            sidecar_text = sidecar.read_text(encoding="utf-8", errors="ignore") if sidecar.exists() else ""
            reader = PdfReader(str(pdf_path), strict=False)
            pages: list[PageExtraction] = []
            chunks = sidecar_text.split("\f") if sidecar_text else []
            for idx, _ in enumerate(reader.pages, start=1):
                page_text = chunks[idx - 1].strip() if idx - 1 < len(chunks) else ""
                pages.append(PageExtraction(page=idx, ocr_text=page_text))
            return pages