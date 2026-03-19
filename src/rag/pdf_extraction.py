from __future__ import annotations

import io
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import IndirectObject


logging.getLogger("pypdf").setLevel(logging.ERROR)
logging.getLogger("pypdf._reader").setLevel(logging.ERROR)


BASIC_EXTRACTION_MODES = {"basic", "baseline", "fast", "pypdf", "simple"}
HYBRID_EXTRACTION_MODES = {"hybrid", "smart_hybrid", "auto"}
COMPLETE_EXTRACTION_MODES = {"complete", "page_complete", "full_page", "max_recall", "exhaustive"}
FULL_DOCLING_EXTRACTION_MODES = {"docling", "docling_only"}


@dataclass(frozen=True)
class PdfHybridSettings:
    extraction_mode: str = "hybrid"
    baseline_chars_per_page_threshold: int = 90
    min_text_coverage_ratio: float = 0.65
    suspicious_image_count_threshold: int = 1
    suspicious_image_area_ratio: float = 0.18
    suspicious_low_text_chars: int = 220
    suspicious_page_score_threshold: float = 0.85
    suspicious_pages_trigger_full_docling_ratio: float = 0.45
    suspicious_pages_trigger_full_docling_min_count: int = 6
    max_selective_docling_pages: int = 12
    docling_enabled: bool = True
    docling_ocr_enabled: bool = True
    docling_force_full_page_ocr: bool = False
    docling_picture_description: bool = False
    ocr_fallback_enabled: bool = True
    ocr_fallback_min_chars: int = 120
    ocr_fallback_min_chars_per_page: int = 90
    ocr_fallback_languages: str = "eng+por"
    ocr_fallback_timeout_seconds: int = 180


@dataclass
class PdfPageAnalysis:
    page_number: int
    text: str
    text_chars: int
    image_count: int
    image_area_ratio_estimate: float
    caption_markers: list[str]
    suspicious_reasons: list[str]
    suspicious_score: float
    used_docling: bool = False


@dataclass(frozen=True)
class PdfExtractionResult:
    text: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class _DoclingAvailability:
    available: bool
    converter_cls: object | None = None
    pdf_format_option_cls: object | None = None
    input_format_pdf: object | None = None
    pipeline_options_cls: object | None = None
    error: str | None = None


_DOC_AVAILABILITY: _DoclingAvailability | None = None


def normalize_pdf_extraction_mode(mode: str | None) -> str:
    normalized = (mode or "hybrid").strip().lower()
    if normalized in BASIC_EXTRACTION_MODES:
        return "basic"
    if normalized in COMPLETE_EXTRACTION_MODES:
        return "complete"
    if normalized in FULL_DOCLING_EXTRACTION_MODES:
        return "docling"
    if normalized in HYBRID_EXTRACTION_MODES:
        return "hybrid"
    return "hybrid"


def describe_pdf_extraction_mode(mode: str | None) -> str:
    normalized = normalize_pdf_extraction_mode(mode)
    descriptions = {
        "basic": "Básico · pypdf apenas · mais rápido",
        "hybrid": "Híbrido inteligente · pypdf + Docling seletivo",
        "complete": "Completo por página · cobertura máxima com Docling/OCR",
        "docling": "Docling documento inteiro · prioriza parsing rico",
    }
    return descriptions.get(normalized, descriptions["hybrid"])


def _resolve_indirect(obj):
    if isinstance(obj, IndirectObject):
        try:
            return obj.get_object()
        except Exception:
            return None
    return obj


def _count_images_and_area(page) -> tuple[int, float]:
    image_count = 0
    image_area_ratio = 0.0

    mediabox = getattr(page, "mediabox", None)
    page_width = float(mediabox.width) if mediabox else 0.0
    page_height = float(mediabox.height) if mediabox else 0.0
    page_area = max(page_width * page_height, 1.0)

    resources = _resolve_indirect(page.get("/Resources")) or {}
    xobjects = _resolve_indirect(resources.get("/XObject")) or {}

    if hasattr(xobjects, "items"):
        for _, xobject_ref in xobjects.items():
            xobject = _resolve_indirect(xobject_ref)
            if not xobject:
                continue
            subtype = xobject.get("/Subtype") if hasattr(xobject, "get") else None
            if subtype == "/Image":
                image_count += 1
                width = float(xobject.get("/Width", 0) or 0)
                height = float(xobject.get("/Height", 0) or 0)
                if width > 0 and height > 0:
                    image_area_ratio += min((width * height) / page_area, 1.0)

    return image_count, round(min(image_area_ratio, 1.0), 4)


def _score_page(text: str, image_count: int, image_area_ratio: float, settings: PdfHybridSettings) -> tuple[float, list[str], list[str]]:
    score = 0.0
    reasons: list[str] = []
    caption_markers: list[str] = []
    lowered = text.lower()
    text_chars = len(text.strip())

    for marker in ("figura", "figure", "gráfico", "grafico", "table", "tabela", "esquema", "fluxograma", "chart"):
        if marker in lowered:
            caption_markers.append(marker)

    if text_chars <= settings.suspicious_low_text_chars:
        score += 0.35
        reasons.append("baixo texto extraído")

    if image_count >= settings.suspicious_image_count_threshold:
        score += 0.28
        reasons.append("possui imagens")

    if image_area_ratio >= settings.suspicious_image_area_ratio:
        score += 0.35
        reasons.append("área visual relevante")

    if caption_markers:
        score += 0.2
        reasons.append("marcadores de figura/tabela")

    if image_count >= 3:
        score += 0.18
        reasons.append("múltiplos elementos visuais")

    if image_count > 0 and text_chars > settings.baseline_chars_per_page_threshold * 2 and caption_markers:
        score += 0.1
        reasons.append("página mista texto+figura")

    return round(score, 4), reasons, caption_markers


def _build_page_heading(page_number: int) -> str:
    return f"[Página {page_number}]"


def _normalize_page_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _join_pages(page_texts: list[tuple[int, str]]) -> str:
    sections: list[str] = []
    for page_number, text in page_texts:
        normalized = _normalize_page_text(text)
        if not normalized:
            continue
        sections.append(f"{_build_page_heading(page_number)}\n{normalized}")
    return "\n\n".join(sections).strip()


def _docling_components() -> _DoclingAvailability:
    global _DOC_AVAILABILITY
    if _DOC_AVAILABILITY is not None:
        return _DOC_AVAILABILITY

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        _DOC_AVAILABILITY = _DoclingAvailability(
            available=True,
            converter_cls=DocumentConverter,
            pdf_format_option_cls=PdfFormatOption,
            input_format_pdf=InputFormat.PDF,
            pipeline_options_cls=PdfPipelineOptions,
        )
        return _DOC_AVAILABILITY
    except Exception as error:
        _DOC_AVAILABILITY = _DoclingAvailability(available=False, error=str(error))
        return _DOC_AVAILABILITY


def _create_docling_converter(settings: PdfHybridSettings):
    availability = _docling_components()
    if not availability.available:
        raise RuntimeError(availability.error or "Docling indisponível.")

    pipeline_options = availability.pipeline_options_cls()
    if hasattr(pipeline_options, "do_ocr"):
        pipeline_options.do_ocr = settings.docling_ocr_enabled

    ocr_options = getattr(pipeline_options, "ocr_options", None)
    if ocr_options is not None and settings.docling_force_full_page_ocr:
        for attr_name in ("force_full_page_ocr", "force_ocr"):
            if hasattr(ocr_options, attr_name):
                setattr(ocr_options, attr_name, True)

    if hasattr(pipeline_options, "do_picture_description"):
        pipeline_options.do_picture_description = settings.docling_picture_description

    return availability.converter_cls(
        format_options={
            availability.input_format_pdf: availability.pdf_format_option_cls(pipeline_options=pipeline_options)
        }
    )


def _docling_extract_pdf_text(file_bytes: bytes, settings: PdfHybridSettings) -> str:
    converter = _create_docling_converter(settings)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
        temp_pdf.write(file_bytes)
        temp_path = Path(temp_pdf.name)

    try:
        result = converter.convert(str(temp_path))
        document = getattr(result, "document", result)
        for method_name in ("export_to_markdown", "export_to_text", "export_to_dict"):
            if not hasattr(document, method_name):
                continue
            exported = getattr(document, method_name)()
            if isinstance(exported, str):
                return exported
            if isinstance(exported, dict):
                return str(exported)
        return str(document)
    finally:
        temp_path.unlink(missing_ok=True)




def _safe_extract_page_text(page) -> tuple[str, str | None]:
    try:
        return (page.extract_text() or '').strip(), None
    except Exception as error:  # pragma: no cover - defensive guard for malformed PDFs
        return '', f"{error.__class__.__name__}: {error}"

def _extract_single_page_pdf(file_bytes: bytes, page_index: int) -> bytes:
    reader = PdfReader(io.BytesIO(file_bytes), strict=False)
    writer = PdfWriter()
    writer.add_page(reader.pages[page_index])
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _docling_extract_page(file_bytes: bytes, page_index: int, settings: PdfHybridSettings) -> str:
    page_pdf = _extract_single_page_pdf(file_bytes, page_index)
    return _docling_extract_pdf_text(page_pdf, settings)


def _should_run_full_docling(page_analyses: list[PdfPageAnalysis], settings: PdfHybridSettings) -> bool:
    if not page_analyses:
        return False

    suspicious_pages = [page for page in page_analyses if page.suspicious_score >= settings.suspicious_page_score_threshold]
    if len(suspicious_pages) >= settings.suspicious_pages_trigger_full_docling_min_count:
        ratio = len(suspicious_pages) / max(len(page_analyses), 1)
        if ratio >= settings.suspicious_pages_trigger_full_docling_ratio:
            return True

    coverage_ratio = sum(1 for page in page_analyses if page.text_chars >= settings.baseline_chars_per_page_threshold) / max(len(page_analyses), 1)
    return coverage_ratio < settings.min_text_coverage_ratio


def _merge_page_texts(base_text: str, enriched_text: str, heading: str) -> tuple[str, bool]:
    normalized_base = _normalize_page_text(base_text)
    normalized_enriched = _normalize_page_text(enriched_text)
    if not normalized_enriched:
        return normalized_base, False
    if not normalized_base:
        return normalized_enriched, True
    if normalized_enriched == normalized_base or normalized_enriched in normalized_base:
        return normalized_base, False
    if normalized_base in normalized_enriched and len(normalized_enriched) >= len(normalized_base):
        return normalized_enriched, True
    merged = f"{normalized_base}\n\n[{heading}]\n{normalized_enriched}".strip()
    return merged, True


def _build_complete_docling_settings(settings: PdfHybridSettings) -> PdfHybridSettings:
    return PdfHybridSettings(
        extraction_mode="complete",
        baseline_chars_per_page_threshold=settings.baseline_chars_per_page_threshold,
        min_text_coverage_ratio=settings.min_text_coverage_ratio,
        suspicious_image_count_threshold=settings.suspicious_image_count_threshold,
        suspicious_image_area_ratio=settings.suspicious_image_area_ratio,
        suspicious_low_text_chars=settings.suspicious_low_text_chars,
        suspicious_page_score_threshold=settings.suspicious_page_score_threshold,
        suspicious_pages_trigger_full_docling_ratio=settings.suspicious_pages_trigger_full_docling_ratio,
        suspicious_pages_trigger_full_docling_min_count=settings.suspicious_pages_trigger_full_docling_min_count,
        max_selective_docling_pages=settings.max_selective_docling_pages,
        docling_enabled=settings.docling_enabled,
        docling_ocr_enabled=True,
        docling_force_full_page_ocr=True,
        docling_picture_description=True,
        ocr_fallback_enabled=settings.ocr_fallback_enabled,
        ocr_fallback_min_chars=settings.ocr_fallback_min_chars,
        ocr_fallback_min_chars_per_page=settings.ocr_fallback_min_chars_per_page,
        ocr_fallback_languages=settings.ocr_fallback_languages,
        ocr_fallback_timeout_seconds=settings.ocr_fallback_timeout_seconds,
    )




def _should_run_ocr_fallback(current_text: str, page_analyses: list[PdfPageAnalysis], settings: PdfHybridSettings) -> tuple[bool, str]:
    normalized = _normalize_page_text(current_text)
    total_chars = len(normalized)
    page_count = max(len(page_analyses), 1)
    chars_per_page = total_chars / page_count
    if total_chars == 0:
        return True, "no_text_extracted"
    if total_chars < settings.ocr_fallback_min_chars:
        return True, "low_total_text"
    if chars_per_page < settings.ocr_fallback_min_chars_per_page:
        return True, "low_chars_per_page"
    suspicious_pages = sum(1 for page in page_analyses if page.suspicious_score >= settings.suspicious_page_score_threshold)
    if suspicious_pages == len(page_analyses) and page_count > 0:
        return True, "all_pages_suspicious"
    return False, ""


def _ocrmypdf_available() -> bool:
    return shutil.which("ocrmypdf") is not None


def _extract_pdf_text_with_pypdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes), strict=False)
        texts: list[str] = []
        for page in reader.pages:
            text, _ = _safe_extract_page_text(page)
            texts.append(text)
        return _join_pages([(idx + 1, text) for idx, text in enumerate(texts)])
    except Exception:
        return ""


def _ocrmypdf_extract_pdf_text(file_bytes: bytes, settings: PdfHybridSettings) -> tuple[str, str | None]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as input_pdf:
        input_pdf.write(file_bytes)
        input_path = Path(input_pdf.name)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as output_pdf:
        output_path = Path(output_pdf.name)

    try:
        command = [
            "ocrmypdf",
            "--force-ocr",
            "--skip-big",
            "50",
            "--output-type",
            "pdf",
            "--language",
            settings.ocr_fallback_languages,
            str(input_path),
            str(output_path),
        ]
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=settings.ocr_fallback_timeout_seconds,
        )
        processed_bytes = output_path.read_bytes()
        return _extract_pdf_text_with_pypdf(processed_bytes), None
    except FileNotFoundError as error:
        return "", f"ocrmypdf indisponível: {error}"
    except subprocess.TimeoutExpired as error:
        return "", f"ocrmypdf timeout: {error}"
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode("utf-8", errors="ignore") if error.stderr else ""
        return "", f"ocrmypdf failed ({error.returncode}): {stderr.strip()}"
    except Exception as error:
        return "", str(error)
    finally:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

def extract_pdf_text_hybrid(file_bytes: bytes, settings: PdfHybridSettings) -> PdfExtractionResult:
    resolved_mode = normalize_pdf_extraction_mode(settings.extraction_mode)
    effective_settings = _build_complete_docling_settings(settings) if resolved_mode == "complete" else settings

    reader = PdfReader(io.BytesIO(file_bytes), strict=False)
    page_analyses: list[PdfPageAnalysis] = []
    baseline_pages: list[tuple[int, str]] = []

    baseline_page_errors: list[dict[str, object]] = []

    for page_index, page in enumerate(reader.pages, start=1):
        text, baseline_error = _safe_extract_page_text(page)
        image_count, image_area_ratio = _count_images_and_area(page)
        score, reasons, caption_markers = _score_page(text, image_count, image_area_ratio, effective_settings)
        analysis = PdfPageAnalysis(
            page_number=page_index,
            text=text,
            text_chars=len(text),
            image_count=image_count,
            image_area_ratio_estimate=image_area_ratio,
            caption_markers=caption_markers,
            suspicious_reasons=reasons,
            suspicious_score=score,
        )
        page_analyses.append(analysis)
        baseline_pages.append((page_index, text))
        if baseline_error:
            baseline_page_errors.append({
                'page_number': page_index,
                'error': baseline_error,
            })

    baseline_text = _join_pages(baseline_pages)
    coverage_ratio = sum(1 for page in page_analyses if page.text_chars >= effective_settings.baseline_chars_per_page_threshold) / max(len(page_analyses), 1)
    suspicious_pages = [page for page in page_analyses if page.suspicious_score >= effective_settings.suspicious_page_score_threshold]

    docling_attempted = False
    docling_mode = "none"
    docling_error = None
    merged_pages = {page_number: text for page_number, text in baseline_pages}

    if effective_settings.docling_enabled and resolved_mode in {"hybrid", "complete", "docling"}:
        try:
            if resolved_mode == "complete":
                docling_attempted = True
                docling_mode = "page_complete"
                complete_docling_text = _docling_extract_pdf_text(file_bytes, effective_settings).strip()
                for page in page_analyses:
                    enriched = _docling_extract_page(file_bytes, page.page_number - 1, effective_settings).strip()
                    merged_text, changed = _merge_page_texts(
                        base_text=merged_pages.get(page.page_number, ""),
                        enriched_text=enriched,
                        heading="Extração completa Docling/OCR",
                    )
                    merged_pages[page.page_number] = merged_text
                    if changed:
                        page.used_docling = True
                baseline_text = _join_pages(sorted(merged_pages.items()))
                normalized_complete = _normalize_page_text(complete_docling_text)
                normalized_baseline = _normalize_page_text(baseline_text)
                if normalized_complete and normalized_complete not in normalized_baseline and len(normalized_complete) > len(normalized_baseline) * 0.55:
                    baseline_text = f"{baseline_text}\n\n[Docling documento completo]\n{normalized_complete}".strip()
                    for page in page_analyses:
                        page.used_docling = True
            elif resolved_mode == "docling" or _should_run_full_docling(page_analyses, effective_settings):
                docling_attempted = True
                docling_mode = "full_document"
                docling_text = _docling_extract_pdf_text(file_bytes, effective_settings).strip()
                if len(docling_text) > len(baseline_text) * 0.7:
                    baseline_text = docling_text
                    for page in page_analyses:
                        page.used_docling = True
                else:
                    docling_mode = "full_document_discarded"
            elif suspicious_pages:
                docling_attempted = True
                docling_mode = "selective_pages"
                pages_to_enrich = suspicious_pages[: effective_settings.max_selective_docling_pages]
                for page in pages_to_enrich:
                    enriched = _docling_extract_page(file_bytes, page.page_number - 1, effective_settings).strip()
                    merged_text, changed = _merge_page_texts(
                        base_text=merged_pages.get(page.page_number, ""),
                        enriched_text=enriched,
                        heading="Enriquecimento visual/OCR",
                    )
                    merged_pages[page.page_number] = merged_text
                    if changed:
                        page.used_docling = True
                baseline_text = _join_pages(sorted(merged_pages.items()))
        except Exception as error:
            docling_error = str(error)
            docling_mode = f"fallback::{docling_mode or 'unknown'}"

    ocr_fallback_attempted = False
    ocr_fallback_applied = False
    ocr_fallback_reason = None
    ocr_fallback_error = None
    ocr_backend = None

    should_ocr, ocr_reason = _should_run_ocr_fallback(baseline_text, page_analyses, effective_settings)
    if effective_settings.ocr_fallback_enabled and should_ocr:
        ocr_fallback_attempted = True
        ocr_fallback_reason = ocr_reason
        if _ocrmypdf_available():
            ocr_backend = "ocrmypdf"
            ocr_text, ocr_error = _ocrmypdf_extract_pdf_text(file_bytes, effective_settings)
            ocr_fallback_error = ocr_error
            normalized_ocr = _normalize_page_text(ocr_text)
            normalized_base = _normalize_page_text(baseline_text)
            if len(normalized_ocr) > len(normalized_base):
                baseline_text = normalized_ocr
                ocr_fallback_applied = True
        else:
            ocr_backend = "ocrmypdf_unavailable"
            ocr_fallback_error = "ocrmypdf command not found"

    metadata = {
        "extractor": "pdf_hybrid",
        "strategy": resolved_mode,
        "strategy_label": describe_pdf_extraction_mode(resolved_mode),
        "page_count": len(page_analyses),
        "baseline_text_chars": len(_join_pages(baseline_pages)),
        "final_text_chars": len(baseline_text),
        "baseline_text_coverage_ratio": round(coverage_ratio, 4),
        "suspicious_pages": len(suspicious_pages),
        "suspicious_page_numbers": [page.page_number for page in suspicious_pages],
        "docling_enabled": effective_settings.docling_enabled,
        "docling_attempted": docling_attempted,
        "docling_mode": docling_mode,
        "docling_error": docling_error,
        "docling_pages_used": [page.page_number for page in page_analyses if page.used_docling],
        "baseline_page_errors": baseline_page_errors,
        "baseline_page_error_count": len(baseline_page_errors),
        "docling_force_full_page_ocr": effective_settings.docling_force_full_page_ocr,
        "docling_picture_description": effective_settings.docling_picture_description,
        "pages_analysis": [
            {
                "page_number": page.page_number,
                "text_chars": page.text_chars,
                "image_count": page.image_count,
                "image_area_ratio_estimate": page.image_area_ratio_estimate,
                "caption_markers": page.caption_markers,
                "suspicious_score": page.suspicious_score,
                "suspicious_reasons": page.suspicious_reasons,
                "used_docling": page.used_docling,
            }
            for page in page_analyses
        ],
    }
    return PdfExtractionResult(text=baseline_text.strip(), metadata=metadata)
