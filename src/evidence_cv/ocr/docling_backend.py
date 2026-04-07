from __future__ import annotations

from pathlib import Path

from ..config import EvidencePipelineConfig
from ..schemas import PageExtraction


class DoclingBackend:
    def __init__(self, config: EvidencePipelineConfig) -> None:
        self.config = config

    def extract(self, pdf_path: Path) -> list[PageExtraction]:
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Docling unavailable: {exc}")

        pipeline_options = PdfPipelineOptions()
        if hasattr(pipeline_options, "do_ocr"):
            pipeline_options.do_ocr = True
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )
        result = converter.convert(str(pdf_path))
        document = getattr(result, "document", result)
        text = document.export_to_markdown() if hasattr(document, "export_to_markdown") else str(document)
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
        return [PageExtraction(page=1, ocr_text=normalized_text)]