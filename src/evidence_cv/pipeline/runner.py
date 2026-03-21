from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader
from PIL import Image

from ..config import EvidencePipelineConfig
from ..ocr.docling_backend import DoclingBackend
from ..ocr.ocrmypdf_backend import OCRMyPDFBackend
from ..reconcile import reconcile_pages
from ..schemas import CVExtractionResult, EvidenceRef, PageExtraction
from ..vision.ollama_vl import OllamaVLBackend, VLInspectionError


EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
PHONE_RE = re.compile(r"^\+?\d[\d\s().-]{7,}\d$")
REGION_PRIORITY = {
    "header_top_block": 1.0,
    "contact_block": 0.95,
    "top_center": 0.9,
    "top_left": 0.88,
    "top_right": 0.85,
    "sidebar": 0.72,
}

REGION_ORDER = [
    "header_top_block",
    "contact_block",
    "top_center",
    "top_left",
    "top_right",
    "sidebar",
]


def _detect_source_type(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path), strict=False)
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
        non_empty = sum(1 for item in page_texts if item)
        if non_empty == len(page_texts) and non_empty > 0:
            return "digital_pdf"
        if non_empty == 0:
            return "scanned_pdf"
        return "mixed_pdf"
    except Exception:
        return "mixed_pdf"


def _extract_native_pages(pdf_path: Path) -> list[PageExtraction]:
    reader = PdfReader(str(pdf_path), strict=False)
    return [PageExtraction(page=index, native_text=(page.extract_text() or "").strip()) for index, page in enumerate(reader.pages, start=1)]


def _render_pdf_pages(pdf_path: Path, config: EvidencePipelineConfig) -> list[Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="evidence_cv_pages_"))
    output_pattern = temp_dir / "page-%04d.png"
    command = [
        "gs",
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=png16m",
        f"-r{config.vl_render_dpi}",
        f"-sOutputFile={output_pattern}",
        str(pdf_path),
    ]
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return sorted(temp_dir.glob("page-*.png"))


def _build_region_specs(width: int, height: int) -> list[tuple[str, tuple[int, int, int, int]]]:
    top_h = int(height * 0.22)
    sidebar_w = int(width * 0.32)
    return [
        ("header_top_block", (0, 0, width, top_h)),
        ("top_left", (0, 0, width // 2, top_h)),
        ("top_center", (width // 4, 0, width * 3 // 4, top_h)),
        ("top_right", (width // 2, 0, width, top_h)),
        ("sidebar", (0, 0, sidebar_w, height)),
        ("contact_block", (0, 0, width, int(height * 0.32))),
    ]


def _generate_priority_crops(page_images: list[Path], config: EvidencePipelineConfig) -> list[tuple[int, str, Path]]:
    crops: list[tuple[int, str, Path]] = []
    for page_index, image_path in enumerate(page_images, start=1):
        with Image.open(image_path) as image:
            width, height = image.size
            region_specs = _build_region_specs(width, height)[: config.vl_max_regions_per_page + 3]
            page_crop_dir = image_path.parent / f"crops_page_{page_index:04d}"
            page_crop_dir.mkdir(parents=True, exist_ok=True)
            for region_label, box in region_specs:
                crop = image.crop(box)
                crop_path = page_crop_dir / f"{region_label}.png"
                crop.save(crop_path)
                crops.append((page_index, region_label, crop_path))
    return crops


def _build_vl_router_metadata(source_type: str, pages: list[PageExtraction], result: CVExtractionResult, config: EvidencePipelineConfig) -> dict[str, object]:
    combined_text_lengths = [len((page.native_text or page.ocr_text or "").strip()) for page in pages]
    low_text_pages = sum(1 for value in combined_text_lengths if value < config.vl_router_low_text_threshold)
    contacts_found = len(result.resume.emails) + len(result.resume.phones)
    name_missing = result.resume.name.status == "not_found"
    location_missing = result.resume.location.status == "not_found"
    header_missing = name_missing or location_missing
    top_page_text = (pages[0].native_text or pages[0].ocr_text or "") if pages else ""
    top_lines = [line.strip() for line in top_page_text.splitlines() if line.strip()][:12]
    short_top_lines = sum(1 for line in top_lines if len(line) <= 24)
    top_fragmented = len(top_lines) >= 6 and short_top_lines >= 4
    header_contact_hits = sum(1 for line in top_lines if "@" in line or re.search(r"\+?\d[\d\s().-]{7,}\d", line))
    strong_header_structure_problem = bool(name_missing and location_missing and top_fragmented and header_contact_hits == 0)
    hard_layout_signal = source_type in {"mixed_pdf", "scanned_pdf"}
    reasons: list[str] = []
    skipped_because: list[str] = []

    if source_type == "scanned_pdf":
        reasons.append("scanned_pdf")
    if source_type == "mixed_pdf":
        reasons.append("mixed_pdf")
    if low_text_pages >= config.vl_scan_like_min_pages:
        reasons.append("low_text_coverage")
    if contacts_found < config.vl_router_min_contact_count:
        reasons.append("missing_contacts_after_ocr")
    if source_type in {"scanned_pdf", "mixed_pdf"} and header_missing:
        reasons.append("header_fields_missing")
    elif source_type == "digital_pdf" and contacts_found < config.vl_router_min_contact_count:
        reasons.append("missing_contacts_after_ocr")
    elif source_type == "digital_pdf" and strong_header_structure_problem:
        reasons.append("strong_header_structure_problem")
    if source_type == "digital_pdf" and False:
        reasons.append("layout_difficult")

    enabled = bool(config.enable_vl and config.vl_router_enabled and reasons)
    if not enabled:
        skipped_because.append("digital_pdf_with_good_ocr_skip_vl")

    if source_type == "scanned_pdf":
        region_count = config.vl_router_force_regions_for_scan_like
    elif reasons:
        region_count = config.vl_router_default_regions_for_partial_docs
    else:
        region_count = 0

    regions_selected = REGION_ORDER[:region_count]
    decision = "call_vl" if enabled else "skip_vl"

    return {
        "enabled": enabled,
        "decision": decision,
        "reasons": reasons,
        "document_signals": {
            "source_type": source_type,
            "low_text_pages": low_text_pages,
            "contacts_found_after_ocr": contacts_found,
            "name_missing": name_missing,
            "location_missing": location_missing,
            "header_missing": header_missing,
            "top_fragmented": top_fragmented,
            "header_contact_hits": header_contact_hits,
            "strong_header_structure_problem": strong_header_structure_problem,
        },
        "regions_selected": regions_selected,
        "skipped_because": skipped_because,
    }


def _filter_region_crops(region_crops: list[tuple[int, str, Path]], selected_regions: list[str]) -> list[tuple[int, str, Path]]:
    if not selected_regions:
        return []
    selected = set(selected_regions)
    return [item for item in region_crops if item[1] in selected]


def _looks_like_scan_or_layout_hard(source_type: str, pages: list[PageExtraction], config: EvidencePipelineConfig) -> bool:
    if source_type == "scanned_pdf":
        return True
    low_text_pages = sum(1 for page in pages if len((page.native_text or page.ocr_text or "").strip()) < 120)
    return low_text_pages >= config.vl_scan_like_min_pages


def _secondary_verify_literal(candidate: str | None, pages: list[PageExtraction]) -> bool:
    if not candidate:
        return False
    lowered = candidate.strip().lower()
    if not lowered:
        return False
    for page in pages:
        combined = f"{page.native_text or ''}\n{page.ocr_text or ''}".lower()
        if lowered in combined:
            return True
    return False


def _normalize_email_candidate(value: object) -> str | None:
    text = str(value or "").strip().strip(",;|")
    if text.lower().endswith(".co"):
        return None
    return text if EMAIL_RE.match(text) else None


def _normalize_phone_candidate(value: object) -> str | None:
    text = str(value or "").strip().strip(",;|")
    digits = re.sub(r"\D", "", text)
    if len(digits) < 8 or len(digits) > 15:
        return None
    if len(set(digits)) <= 2:
        return None
    return text if PHONE_RE.match(text) else None


def _normalize_name_candidate(value: object) -> str | None:
    text = " ".join(str(value or "").strip().split())
    blocked = {"present", "remote", "hybrid", "onsite", "current"}
    lowered = text.lower()
    if len(text) < 4 or "@" in text or any(ch.isdigit() for ch in text):
        return None
    if lowered in blocked:
        return None
    if any(token in lowered for token in ["engineer", "developer", "manager", "analyst"]):
        return None
    return text


def _normalize_location_candidate(value: object) -> str | None:
    raw = str(value or "").strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw.strip("[]").strip().strip("'").strip('"')
    text = " ".join(raw.split())
    if len(text) < 2 or "@" in text or any(ch.isdigit() for ch in text):
        return None
    blocked = {"email", "phone", "linkedin", "github", "resume", "curriculum vitae"}
    blocked_location = {"remote", "hybrid", "onsite", "present"}
    if text.lower() in blocked:
        return None
    if text.lower() in blocked_location:
        return None
    return text


def _candidate_score(region_label: str, confirmed: bool, confidence: float) -> float:
    return REGION_PRIORITY.get(region_label, 0.5) + (0.5 if confirmed else 0.0) + confidence


def _dedupe_evidence_refs(items: list[EvidenceRef], kind: str) -> list[EvidenceRef]:
    best_by_key: dict[str, EvidenceRef] = {}
    for item in items:
        if not item.value:
            continue
        key = item.value.lower().strip()
        if kind == "phone":
            key = re.sub(r"\D", "", key)
        existing = best_by_key.get(key)
        if existing is None or float(item.confidence or 0) > float(existing.confidence or 0):
            best_by_key[key] = item
    return list(best_by_key.values())


def _choose_best_singular(items: list[EvidenceRef]) -> EvidenceRef:
    if not items:
        return EvidenceRef()
    ranked = sorted(items, key=lambda item: float(item.confidence or 0), reverse=True)
    return ranked[0]


def _build_product_consumption(result: CVExtractionResult, config: EvidencePipelineConfig) -> dict[str, object]:
    def field_policy(ref: EvidenceRef) -> dict[str, object]:
        directly_usable = ref.status == "confirmed"
        if ref.status == "visual_candidate" and config.product_consume_visual_candidates:
            directly_usable = True
        if ref.status == "needs_review" and config.product_consume_needs_review:
            directly_usable = True
        return {
            "status": ref.status,
            "directly_usable": directly_usable,
            "value": ref.value if directly_usable else None,
        }

    return {
        "policy": {
            "confirmed": "usable",
            "visual_candidate": "review_required" if not config.product_consume_visual_candidates else "conditionally_usable",
            "needs_review": "review_required" if not config.product_consume_needs_review else "conditionally_usable",
            "not_found": "missing",
        },
        "name": field_policy(result.resume.name),
        "location": field_policy(result.resume.location),
        "emails": [field_policy(item) for item in result.resume.emails],
        "phones": [field_policy(item) for item in result.resume.phones],
    }


def _init_vl_runtime(config: EvidencePipelineConfig) -> dict[str, object]:
    return {
        "enabled": bool(config.enable_vl),
        "model": config.vl_model,
        "regions_attempted": 0,
        "regions_succeeded": 0,
        "regions_failed": 0,
        "timeouts": 0,
        "fallback_used": False,
        "warnings": [],
    }


def _apply_vl_contact_enrichment(result: CVExtractionResult, region_crops: list[tuple[int, str, Path]], config: EvidencePipelineConfig) -> tuple[CVExtractionResult, dict[str, object]]:
    vl_runtime = _init_vl_runtime(config)
    if not config.enable_vl or not region_crops:
        return result, vl_runtime

    vl = OllamaVLBackend(config)
    name_candidates: list[EvidenceRef] = []
    location_candidates: list[EvidenceRef] = []
    email_candidates: list[EvidenceRef] = list(result.resume.emails)
    phone_candidates: list[EvidenceRef] = list(result.resume.phones)

    for index, region_label, image_path in region_crops:
        vl_runtime["regions_attempted"] += 1
        try:
            candidates = vl.extract_contact_candidates_from_region(image_path, region_label)
            vl_runtime["regions_succeeded"] += 1
        except VLInspectionError as error:
            vl_runtime["regions_failed"] += 1
            if error.error_type in {"timeout_error", "socket_timeout"}:
                vl_runtime["timeouts"] += 1
            vl_runtime["fallback_used"] = True
            vl_runtime["warnings"].append(f"{region_label}: {error.message}")
            continue
        except Exception as error:
            vl_runtime["regions_failed"] += 1
            vl_runtime["fallback_used"] = True
            vl_runtime["warnings"].append(f"{region_label}: unexpected VL failure: {error}")
            continue

        if candidates.get("name"):
            name_value = _normalize_name_candidate(candidates.get("name"))
            if name_value:
                confirmed = _secondary_verify_literal(name_value, result.pages)
                confidence = _candidate_score(region_label, confirmed, 0.3 if confirmed else 0.12)
                name_candidates.append(EvidenceRef(
                value=name_value,
                status="confirmed" if confirmed else "visual_candidate",
                evidence_text=name_value,
                source_type="ocr+vl" if confirmed else "vl",
                page=index,
                confidence=confidence,
                notes=f"{region_label} candidate from selective VL",
                ))

        if candidates.get("location"):
            location_value = _normalize_location_candidate(candidates.get("location"))
            if location_value:
                confirmed = _secondary_verify_literal(location_value, result.pages)
                confidence = _candidate_score(region_label, confirmed, 0.25 if confirmed else 0.1)
                location_candidates.append(EvidenceRef(
                value=location_value,
                status="confirmed" if confirmed else "visual_candidate",
                evidence_text=location_value,
                source_type="ocr+vl" if confirmed else "vl",
                page=index,
                confidence=confidence,
                notes=f"Location explicitly visible in {region_label}" if location_value else None,
                ))

        existing_emails = {item.value for item in result.resume.emails if item.value}
        added_emails = 0
        for email in candidates.get("emails") or []:
            email_value = _normalize_email_candidate(email)
            if not email_value or email_value in existing_emails:
                continue
            confirmed = _secondary_verify_literal(email_value, result.pages)
            email_candidates.append(EvidenceRef(
                    value=email_value,
                    status="confirmed" if confirmed else "visual_candidate",
                    evidence_text=email_value,
                    source_type="ocr+vl" if confirmed else "vl",
                    page=index,
                    confidence=_candidate_score(region_label, confirmed, 0.35 if confirmed else 0.12),
                    notes=f"{region_label} candidate from selective VL",
                ))
            existing_emails.add(email_value)
            added_emails += 1
            if added_emails >= 3:
                break

        existing_phones = {item.value for item in result.resume.phones if item.value}
        added_phones = 0
        for phone in candidates.get("phones") or []:
            phone_value = _normalize_phone_candidate(phone)
            if not phone_value or phone_value in existing_phones:
                continue
            confirmed = _secondary_verify_literal(phone_value, result.pages)
            phone_candidates.append(EvidenceRef(
                    value=phone_value,
                    status="confirmed" if confirmed else "visual_candidate",
                    evidence_text=phone_value,
                    source_type="ocr+vl" if confirmed else "vl",
                    page=index,
                    confidence=_candidate_score(region_label, confirmed, 0.3 if confirmed else 0.1),
                    notes=f"{region_label} candidate from selective VL",
                ))
            existing_phones.add(phone_value)
            added_phones += 1
            if added_phones >= 3:
                break

    result.resume.emails = _dedupe_evidence_refs(email_candidates, "email")
    result.resume.phones = _dedupe_evidence_refs(phone_candidates, "phone")
    best_name = _choose_best_singular(name_candidates)
    if best_name.value:
        result.resume.name = best_name
    best_location = _choose_best_singular(location_candidates)
    if best_location.value:
        result.resume.location = best_location

    return result, vl_runtime


def run_cv_pipeline(pdf_path: str | Path, config: EvidencePipelineConfig) -> CVExtractionResult:
    path = Path(pdf_path)
    source_type = _detect_source_type(path)
    native_pages = _extract_native_pages(path)

    if config.ocr_backend == "docling":
        ocr_backend = DoclingBackend(config)
    else:
        ocr_backend = OCRMyPDFBackend(config)

    ocr_pages = ocr_backend.extract(path)
    merged_pages: list[PageExtraction] = []
    max_pages = max(len(native_pages), len(ocr_pages))
    for idx in range(max_pages):
        native = native_pages[idx] if idx < len(native_pages) else PageExtraction(page=idx + 1)
        ocr = ocr_pages[idx] if idx < len(ocr_pages) else PageExtraction(page=idx + 1)
        merged_pages.append(
            PageExtraction(
                page=idx + 1,
                native_text=native.native_text,
                ocr_text=ocr.ocr_text,
                blocks=ocr.blocks or native.blocks,
                warnings=[*native.warnings, *ocr.warnings],
            )
        )

    document_id = hashlib.sha256(path.read_bytes()).hexdigest()
    result = reconcile_pages(merged_pages, document_id=document_id, source_type=source_type)
    vl_runtime = _init_vl_runtime(config)
    vl_router = _build_vl_router_metadata(source_type, merged_pages, result, config)
    if vl_router["enabled"]:
        page_images = _render_pdf_pages(path, config)
        region_crops = _generate_priority_crops(page_images, config)
        region_crops = _filter_region_crops(region_crops, vl_router.get("regions_selected", []))
        result, vl_runtime = _apply_vl_contact_enrichment(result, region_crops, config)
        if any(item.status == "visual_candidate" for item in [result.resume.name, result.resume.location]):
            result.warnings.append("VL selective added visual candidates that still need review")
        elif result.resume.name.status == "confirmed" or result.resume.location.status == "confirmed":
            result.warnings.append("VL selective helped confirm header/contact information")
        if vl_runtime.get("warnings"):
            result.warnings.extend(vl_runtime["warnings"])
    result.product_consumption = _build_product_consumption(result, config)
    result.product_consumption["vl_runtime"] = vl_runtime
    result.runtime_metadata["vl_router"] = vl_router
    return result


def run_cv_pipeline_from_bytes(file_bytes: bytes, suffix: str, config: EvidencePipelineConfig) -> CVExtractionResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / f"document.{suffix.lstrip('.') or 'pdf'}"
        path.write_bytes(file_bytes)
        return run_cv_pipeline(path, config)