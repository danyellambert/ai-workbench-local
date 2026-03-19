import csv
import hashlib
import io
from dataclasses import dataclass, field

from src.config import RagSettings
from src.rag.pdf_extraction import PdfHybridSettings, extract_pdf_text_hybrid, normalize_pdf_extraction_mode


@dataclass(frozen=True)
class LoadedDocument:
    name: str
    file_type: str
    file_hash: str
    text: str
    metadata: dict[str, object] = field(default_factory=dict)


def _extract_pdf_text(file_bytes: bytes, rag_settings: RagSettings | None = None) -> tuple[str, dict[str, object]]:
    settings = PdfHybridSettings(
        extraction_mode=normalize_pdf_extraction_mode(rag_settings.pdf_extraction_mode if rag_settings else "hybrid"),
        baseline_chars_per_page_threshold=(rag_settings.pdf_baseline_chars_per_page_threshold if rag_settings else 90),
        min_text_coverage_ratio=(rag_settings.pdf_min_text_coverage_ratio if rag_settings else 0.65),
        suspicious_image_count_threshold=(rag_settings.pdf_suspicious_image_count_threshold if rag_settings else 1),
        suspicious_image_area_ratio=(rag_settings.pdf_suspicious_image_area_ratio if rag_settings else 0.18),
        suspicious_low_text_chars=(rag_settings.pdf_suspicious_low_text_chars if rag_settings else 220),
        suspicious_page_score_threshold=(rag_settings.pdf_suspicious_page_score_threshold if rag_settings else 0.85),
        suspicious_pages_trigger_full_docling_ratio=(rag_settings.pdf_suspicious_pages_trigger_full_docling_ratio if rag_settings else 0.45),
        suspicious_pages_trigger_full_docling_min_count=(rag_settings.pdf_suspicious_pages_trigger_full_docling_min_count if rag_settings else 6),
        max_selective_docling_pages=(rag_settings.pdf_max_selective_docling_pages if rag_settings else 12),
        docling_enabled=(rag_settings.pdf_docling_enabled if rag_settings else True),
        docling_ocr_enabled=(rag_settings.pdf_docling_ocr_enabled if rag_settings else True),
        docling_force_full_page_ocr=(rag_settings.pdf_docling_force_full_page_ocr if rag_settings else False),
        docling_picture_description=(rag_settings.pdf_docling_picture_description if rag_settings else False),
        ocr_fallback_enabled=(rag_settings.pdf_ocr_fallback_enabled if rag_settings else True),
        ocr_fallback_min_chars=(rag_settings.pdf_ocr_fallback_min_chars if rag_settings else 120),
        ocr_fallback_min_chars_per_page=(rag_settings.pdf_ocr_fallback_min_chars_per_page if rag_settings else 90),
        ocr_fallback_languages=(rag_settings.pdf_ocr_fallback_languages if rag_settings else "eng+por"),
        ocr_fallback_timeout_seconds=(rag_settings.pdf_ocr_fallback_timeout_seconds if rag_settings else 180),
        scan_image_ocr_enabled=(rag_settings.pdf_scan_image_ocr_enabled if rag_settings else True),
        scan_image_ocr_min_suspicious_ratio=(rag_settings.pdf_scan_image_ocr_min_suspicious_ratio if rag_settings else 0.8),
        scan_image_ocr_min_suspicious_count=(rag_settings.pdf_scan_image_ocr_min_suspicious_count if rag_settings else 2),
        scan_image_ocr_oversample_dpi=(rag_settings.pdf_scan_image_ocr_oversample_dpi if rag_settings else 300),
    )
    result = extract_pdf_text_hybrid(file_bytes, settings)
    return result.text, result.metadata


def _extract_csv_text(file_bytes: bytes) -> str:
    text = file_bytes.decode("utf-8", errors="ignore")
    rows = list(csv.reader(io.StringIO(text)))
    return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows if row)


def _extract_txt_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def load_document(uploaded_file, rag_settings: RagSettings | None = None) -> LoadedDocument:
    file_bytes = uploaded_file.getvalue()
    suffix = uploaded_file.name.lower().rsplit(".", 1)[-1] if "." in uploaded_file.name else ""

    metadata: dict[str, object] = {}

    if suffix == "pdf":
        text, metadata = _extract_pdf_text(file_bytes, rag_settings)
        file_type = "pdf"
    elif suffix == "csv":
        text = _extract_csv_text(file_bytes)
        file_type = "csv"
    elif suffix in {"txt", "md", "py"}:
        text = _extract_txt_text(file_bytes)
        file_type = suffix
    else:
        raise RuntimeError("Formato não suportado. Use PDF, TXT, CSV, MD ou PY.")

    cleaned_text = text.strip()
    if not cleaned_text:
        raise RuntimeError("Não foi possível extrair conteúdo útil do arquivo enviado.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return LoadedDocument(
        name=uploaded_file.name,
        file_type=file_type,
        file_hash=file_hash,
        text=cleaned_text,
        metadata=metadata,
    )
