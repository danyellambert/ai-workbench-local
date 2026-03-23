import csv
import hashlib
import io
import re
from dataclasses import dataclass, field

from src.config import RagSettings
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.evidence_cv.pipeline.runner import run_cv_pipeline_from_bytes
from src.rag.pdf_extraction import PdfHybridSettings, extract_pdf_text_hybrid, normalize_pdf_extraction_mode


CV_SECTION_HINTS = ["experience", "education", "skills", "languages", "profile", "summary"]
CV_PRIMARY_SECTION_HINTS = ["experience", "education", "skills", "languages"]
NON_CV_DOCUMENT_HINTS = [
    "financial report",
    "agency financial report",
    "fiscal year",
    "annual report",
    "statement of",
    "appendix",
    "table of contents",
    "management discussion",
    "independent auditor",
    "performance data",
    "notes to the financial statements",
]
DATE_RANGE_RE = re.compile(
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|(?:19|20)\d{2}\s*[-–/]\s*(?:present|current|(?:19|20)\d{2})",
    re.I,
)
CONTACT_RE = re.compile(r"(?:@|linkedin|github|\+?\d[\d\s().-]{7,}\d)", re.I)


@dataclass(frozen=True)
class LoadedDocument:
    name: str
    file_type: str
    file_hash: str
    text: str
    metadata: dict[str, object] = field(default_factory=dict)


def _normalize_index_text(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").split()).strip()


def _looks_like_bad_index_field(value: str | None) -> bool:
    text = _normalize_index_text(value)
    if not text:
        return True
    upper = text.upper()
    if len(text) > 120:
        return True
    if text.count("|") >= 3:
        return True
    if text.count(" - ") >= 3:
        return True
    if sum(1 for marker in ("SUMMARY", "SKILLS", "EDUCATION", "LANGUAGES", "EXPERIENCE") if marker in upper) >= 2:
        return True
    if text.startswith("{") or text.startswith("["):
        return True
    return False


def _usable_index_field(value: str | None) -> str | None:
    text = _normalize_index_text(value)
    if not text or _looks_like_bad_index_field(text):
        return None
    return text


def _build_cv_indexable_text(indexing_payload: dict[str, object]) -> tuple[str, dict[str, object]]:
    confirmed = indexing_payload.get("confirmed_fields") or {}
    structured = indexing_payload.get("structured") or {}
    raw_text = _normalize_index_text(str(indexing_payload.get("raw_text") or ""))

    parts: list[str] = []
    included_sections: list[str] = []
    dropped_sections: list[str] = []
    dropped_reasons: list[str] = []

    confirmed_lines: list[str] = []
    name = _usable_index_field(confirmed.get("name"))
    location = _usable_index_field(confirmed.get("location"))
    if name:
        confirmed_lines.append(f"Name: {name}")
    elif confirmed.get("name"):
        dropped_reasons.append("confirmed_fields.name: noisy_or_implausible_value")
    if location:
        confirmed_lines.append(f"Location: {location}")
    elif confirmed.get("location"):
        dropped_reasons.append("confirmed_fields.location: noisy_or_implausible_value")
    emails = [_normalize_index_text(item) for item in confirmed.get("emails", []) if _normalize_index_text(item)]
    phones = [_normalize_index_text(item) for item in confirmed.get("phones", []) if _normalize_index_text(item)]
    if emails:
        confirmed_lines.append(f"Emails: {', '.join(emails)}")
    if phones:
        confirmed_lines.append(f"Phones: {', '.join(phones)}")
    if confirmed_lines:
        parts.append("[CV CONFIRMED FIELDS]\n" + "\n".join(confirmed_lines))
        included_sections.append("confirmed_fields")
    elif confirmed:
        dropped_sections.append("confirmed_fields")

    experience_entries = structured.get("experience") or []
    if experience_entries:
        exp_lines: list[str] = []
        for index, entry in enumerate(experience_entries, start=1):
            company = _usable_index_field((entry.get("company") or {}).get("value") or "")
            title = _usable_index_field((entry.get("title") or {}).get("value") or "")
            date_range = _usable_index_field((entry.get("date_range") or {}).get("value") or "")
            location = _usable_index_field((entry.get("location") or {}).get("value") or "")
            bullets = [
                _usable_index_field(item.get("value") or "")
                for item in (entry.get("description_or_bullets") or [])
                if item.get("status") == "confirmed"
            ]
            bullets = [item for item in bullets if item]
            if not any([company, title, date_range, location, bullets]):
                dropped_reasons.append(f"experience[{index}]: all_fields_noisy_or_empty")
                continue
            header = " | ".join(item for item in [title, company, date_range, location] if item)
            if header:
                exp_lines.append(f"- {header}")
            for bullet in bullets:
                exp_lines.append(f"  • {bullet}")
        if exp_lines:
            parts.append("[CV EXPERIENCE]\n" + "\n".join(exp_lines))
            included_sections.append("experience")
        else:
            dropped_sections.append("experience")

    education_entries = structured.get("education") or []
    if education_entries:
        edu_lines: list[str] = []
        for index, entry in enumerate(education_entries, start=1):
            institution = _usable_index_field((entry.get("institution") or {}).get("value") or "")
            degree = _usable_index_field((entry.get("degree") or {}).get("value") or "")
            date_range = _usable_index_field((entry.get("date_range") or {}).get("value") or "")
            location = _usable_index_field((entry.get("location") or {}).get("value") or "")
            notes = [
                _usable_index_field(item.get("value") or "")
                for item in (entry.get("notes") or [])
                if item.get("status") == "confirmed"
            ]
            notes = [item for item in notes if item]
            if not any([institution, degree, date_range, location, notes]):
                dropped_reasons.append(f"education[{index}]: all_fields_noisy_or_empty")
                continue
            header = " | ".join(item for item in [degree, institution, date_range, location] if item)
            if header:
                edu_lines.append(f"- {header}")
            for note in notes:
                edu_lines.append(f"  • {note}")
        if edu_lines:
            parts.append("[CV EDUCATION]\n" + "\n".join(edu_lines))
            included_sections.append("education")
        else:
            dropped_sections.append("education")

    skills = [
        _usable_index_field(item.get("value") or "")
        for item in (structured.get("skills") or [])
        if item.get("status") == "confirmed"
    ]
    skills = [item for item in skills if item]
    if skills:
        parts.append("[CV SKILLS]\n" + "\n".join(f"- {item}" for item in skills))
        included_sections.append("skills")
    elif structured.get("skills"):
        dropped_sections.append("skills")
        dropped_reasons.append("skills: all_values_noisy_or_empty")

    languages = []
    for index, item in enumerate((structured.get("languages") or []), start=1):
        language = _usable_index_field((item.get("language") or {}).get("value") or "")
        proficiency = _usable_index_field((item.get("proficiency") or {}).get("value") or "")
        if language:
            languages.append(f"- {language}" + (f" ({proficiency})" if proficiency else ""))
        else:
            dropped_reasons.append(f"languages[{index}]: noisy_or_empty_language")
    if languages:
        parts.append("[CV LANGUAGES]\n" + "\n".join(languages))
        included_sections.append("languages")
    elif structured.get("languages"):
        dropped_sections.append("languages")

    if raw_text:
        parts.append("[CV RAW TEXT]\n" + raw_text)
    payload_quality = {
        "confirmed_fields_usable": bool(confirmed_lines),
        "included_structured_sections": included_sections,
        "dropped_structured_sections": list(dict.fromkeys(dropped_sections)),
        "dropped_section_reasons": dropped_reasons,
        "raw_text_present": bool(raw_text),
        "structured_payload_usable": bool(confirmed_lines or any(section in included_sections for section in ("experience", "education", "skills", "languages"))),
    }
    return "\n\n".join(parts).strip(), payload_quality


def _merge_contact_lists(legacy_values: list[str], evidence_values: list[str]) -> tuple[list[str], dict[str, int]]:
    legacy = [item for item in legacy_values if item]
    evidence = [item for item in evidence_values if item]
    merged = list(legacy)
    complements = 0
    conflicts = 0
    for item in evidence:
        if item in legacy:
            continue
        if legacy:
            conflicts += 1
            continue
        merged.append(item)
        complements += 1
    return merged, {"complements": complements, "conflicts": conflicts}


def _build_shadow_rollout_report(legacy_metadata: dict[str, object], evidence_metadata: dict[str, object]) -> dict[str, object]:
    legacy_summary = legacy_metadata.get("evidence_summary") or {}
    evidence_summary = evidence_metadata.get("evidence_summary") or {}

    legacy_emails = [item for item in legacy_summary.get("emails", []) if item]
    legacy_phones = [item for item in legacy_summary.get("phones", []) if item]
    evidence_emails = [item for item in evidence_summary.get("emails", []) if item]
    evidence_phones = [item for item in evidence_summary.get("phones", []) if item]

    _, email_stats = _merge_contact_lists(legacy_emails, evidence_emails)
    _, phone_stats = _merge_contact_lists(legacy_phones, evidence_phones)

    agreements = 0
    if set(legacy_emails) == set(evidence_emails):
        agreements += 1
    if set(legacy_phones) == set(evidence_phones):
        agreements += 1

    return {
        "agreements": agreements,
        "email_complements": email_stats["complements"],
        "phone_complements": phone_stats["complements"],
        "email_conflicts": email_stats["conflicts"],
        "phone_conflicts": phone_stats["conflicts"],
    }


def _apply_hybrid_contact_policy(legacy_metadata: dict[str, object], evidence_metadata: dict[str, object]) -> dict[str, object]:
    legacy_summary = legacy_metadata.get("evidence_summary") or {}
    evidence_summary = evidence_metadata.get("evidence_summary") or {}

    merged_emails, email_stats = _merge_contact_lists(
        legacy_summary.get("emails", []),
        evidence_summary.get("emails", []),
    )
    merged_phones, phone_stats = _merge_contact_lists(
        legacy_summary.get("phones", []),
        evidence_summary.get("phones", []),
    )

    return {
        "emails": merged_emails,
        "phones": merged_phones,
        "name": evidence_summary.get("name_value") if evidence_summary.get("name_status") == "confirmed" else None,
        "location": evidence_summary.get("location_value") if evidence_summary.get("location_status") == "confirmed" else None,
        "policy": {
            "emails": "legacy_confirmed_first_fill_from_evidence_confirmed",
            "phones": "legacy_confirmed_first_fill_from_evidence_confirmed",
            "name": "use_evidence_confirmed_only",
            "location": "use_evidence_confirmed_only",
        },
        "stats": {
            "email_complements": email_stats["complements"],
            "phone_complements": phone_stats["complements"],
            "email_conflicts": email_stats["conflicts"],
            "phone_conflicts": phone_stats["conflicts"],
        },
    }


def _looks_like_cv_filename(filename: str) -> bool:
    lowered = filename.lower()
    return any(token in lowered for token in ["cv", "resume", "curriculo", "currículo"])


def _compute_evidence_rollout_bucket(file_bytes: bytes, filename: str) -> int:
    digest = hashlib.sha256(filename.encode("utf-8", errors="ignore") + b"\0" + file_bytes).hexdigest()
    return int(digest[:8], 16) % 100


def _detect_cv_like_content(file_bytes: bytes, filename: str, rag_settings: RagSettings) -> tuple[bool, list[str]]:
    text, metadata = _extract_pdf_text(file_bytes, rag_settings)
    normalized = text.lower()
    top_text = "\n".join(text.splitlines()[:30])
    reasons: list[str] = []
    filename_hint = _looks_like_cv_filename(filename)

    negative_hits = [hint for hint in NON_CV_DOCUMENT_HINTS if hint in normalized]
    if len(negative_hits) >= 2 and not filename_hint:
        reasons.append("report_like_document_detected")
        return False, reasons

    if CONTACT_RE.search(top_text):
        reasons.append("top_contact_profile_structure")

    section_hits = [term for term in CV_SECTION_HINTS if term in normalized]
    primary_section_hits = [term for term in CV_PRIMARY_SECTION_HINTS if term in normalized]
    if len(primary_section_hits) >= 2:
        reasons.append("cv_like_sections_detected")

    if len(DATE_RANGE_RE.findall(normalized)) >= 2:
        reasons.append("resume_like_date_ranges")

    if metadata.get("page_count") and len(normalized.split()) > 120:
        reasons.append("sufficient_resume_like_content")

    contact_detected = "top_contact_profile_structure" in reasons
    sections_detected = "cv_like_sections_detected" in reasons
    dates_detected = "resume_like_date_ranges" in reasons

    if filename_hint and (contact_detected or sections_detected):
        return True, reasons

    if contact_detected and sections_detected and dates_detected:
        return True, reasons

    return False, reasons


def _build_evidence_routing_diagnostics(
    file_bytes: bytes,
    filename: str,
    rag_settings: RagSettings | None,
) -> tuple[bool, dict[str, object]]:
    filename_hint = _looks_like_cv_filename(filename)
    diagnostics: dict[str, object] = {
        "feature_flag_enabled": bool(getattr(rag_settings, "pdf_evidence_pipeline_enabled", False)) if rag_settings else False,
        "filename_hint": filename_hint,
        "cv_like_content_detected": False,
        "cv_like_reasons": [],
        "strong_scan_like": False,
    }

    if rag_settings is None or not getattr(rag_settings, "pdf_evidence_pipeline_enabled", False):
        diagnostics.update(
            {
                "rollout_percentage": 0,
                "rollout_selected": False,
                "decision": "legacy_path",
                "reason": "feature_flag_disabled",
            }
        )
        return False, diagnostics

    rollout_percentage = int(getattr(rag_settings, "pdf_evidence_pipeline_rollout_percentage", 100))
    rollout_bucket = _compute_evidence_rollout_bucket(file_bytes, filename)
    rollout_selected = rollout_bucket < rollout_percentage
    diagnostics.update(
        {
            "rollout_percentage": rollout_percentage,
            "rollout_bucket": rollout_bucket,
            "rollout_selected": rollout_selected,
        }
    )

    if not rollout_selected:
        diagnostics.update(
            {
                "decision": "legacy_path",
                "reason": "rollout_percentage_filtered",
            }
        )
        return False, diagnostics

    if getattr(rag_settings, "pdf_evidence_pipeline_use_for_cv_like", True):
        cv_like_content, cv_like_reasons = _detect_cv_like_content(file_bytes, filename, rag_settings)
        diagnostics["cv_like_content_detected"] = cv_like_content
        diagnostics["cv_like_reasons"] = cv_like_reasons
        if cv_like_content:
            diagnostics.update(
                {
                    "decision": "evidence_path",
                    "reason": "cv_like_match",
                }
            )
            return True, diagnostics

    if getattr(rag_settings, "pdf_evidence_pipeline_use_for_strong_scan_like", True):
        settings = PdfHybridSettings(
            extraction_mode=normalize_pdf_extraction_mode(rag_settings.pdf_extraction_mode),
            baseline_chars_per_page_threshold=rag_settings.pdf_baseline_chars_per_page_threshold,
            min_text_coverage_ratio=rag_settings.pdf_min_text_coverage_ratio,
            suspicious_image_count_threshold=rag_settings.pdf_suspicious_image_count_threshold,
            suspicious_image_area_ratio=rag_settings.pdf_suspicious_image_area_ratio,
            suspicious_low_text_chars=rag_settings.pdf_suspicious_low_text_chars,
            suspicious_page_score_threshold=rag_settings.pdf_suspicious_page_score_threshold,
            suspicious_pages_trigger_full_docling_ratio=rag_settings.pdf_suspicious_pages_trigger_full_docling_ratio,
            suspicious_pages_trigger_full_docling_min_count=rag_settings.pdf_suspicious_pages_trigger_full_docling_min_count,
            max_selective_docling_pages=rag_settings.pdf_max_selective_docling_pages,
            docling_enabled=rag_settings.pdf_docling_enabled,
            docling_ocr_enabled=rag_settings.pdf_docling_ocr_enabled,
            docling_force_full_page_ocr=rag_settings.pdf_docling_force_full_page_ocr,
            docling_picture_description=rag_settings.pdf_docling_picture_description,
            ocr_fallback_enabled=rag_settings.pdf_ocr_fallback_enabled,
            ocr_fallback_min_chars=rag_settings.pdf_ocr_fallback_min_chars,
            ocr_fallback_min_chars_per_page=rag_settings.pdf_ocr_fallback_min_chars_per_page,
            ocr_fallback_languages=rag_settings.pdf_ocr_fallback_languages,
            ocr_fallback_timeout_seconds=rag_settings.pdf_ocr_fallback_timeout_seconds,
            scan_image_ocr_enabled=rag_settings.pdf_scan_image_ocr_enabled,
            scan_image_ocr_min_suspicious_ratio=rag_settings.pdf_scan_image_ocr_min_suspicious_ratio,
            scan_image_ocr_min_suspicious_count=rag_settings.pdf_scan_image_ocr_min_suspicious_count,
            scan_image_ocr_oversample_dpi=rag_settings.pdf_scan_image_ocr_oversample_dpi,
        )
        result = extract_pdf_text_hybrid(file_bytes, settings)
        suspicious_pages = int(result.metadata.get("suspicious_pages") or 0)
        page_count = int(result.metadata.get("page_count") or 1)
        suspicious_ratio = suspicious_pages / max(page_count, 1)
        suspicious_ratio_threshold = float(getattr(rag_settings, "pdf_evidence_pipeline_min_scan_suspicious_ratio", 0.8))
        strong_scan_like = suspicious_ratio >= suspicious_ratio_threshold
        diagnostics.update(
            {
                "strong_scan_like": strong_scan_like,
                "scan_suspicious_ratio": suspicious_ratio,
                "scan_suspicious_ratio_threshold": suspicious_ratio_threshold,
            }
        )
        if strong_scan_like:
            diagnostics.update(
                {
                    "decision": "evidence_path",
                    "reason": "strong_scan_like_match",
                }
            )
            return True, diagnostics

    diagnostics.update(
        {
            "decision": "legacy_path",
            "reason": "generic_pdf_legacy_path",
        }
    )
    return False, diagnostics


def _extract_pdf_text_with_evidence_pipeline(
    file_bytes: bytes,
    filename: str,
    rag_settings: RagSettings,
    routing_diagnostics: dict[str, object] | None = None,
) -> tuple[str, dict[str, object]]:
    config = build_evidence_config_from_rag_settings(rag_settings)
    result = run_cv_pipeline_from_bytes(file_bytes, ".pdf", config)
    evidence_summary = {
        "document_id": result.document_id,
        "source_type": result.source_type,
        "warnings": result.warnings,
        "emails_found": len(result.resume.emails),
        "phones_found": len(result.resume.phones),
        "name_status": result.resume.name.status,
        "location_status": result.resume.location.status,
        "name_value": result.resume.name.value,
        "location_value": result.resume.location.value,
        "emails": [item.value for item in result.resume.emails if item.value],
        "phones": [item.value for item in result.resume.phones if item.value],
    }
    indexing_payload = result.runtime_metadata.get("indexing_payload", {}) if isinstance(result.runtime_metadata, dict) else {}
    structured_index_text, payload_quality = _build_cv_indexable_text(indexing_payload) if indexing_payload else ("", {})
    page_texts = [page.native_text or page.ocr_text or "" for page in result.pages]
    raw_page_text = "\n\n".join(item.strip() for item in page_texts if item and item.strip())
    use_structured_payload = bool(payload_quality.get("structured_payload_usable") and structured_index_text)
    if use_structured_payload:
        text = structured_index_text
        indexing_text_strategy = "structured_payload"
    elif payload_quality.get("confirmed_fields_usable") and raw_page_text:
        confirmed_only_text, _ = _build_cv_indexable_text({
            "confirmed_fields": indexing_payload.get("confirmed_fields") or {},
            "structured": {},
            "raw_text": raw_page_text,
        })
        text = confirmed_only_text or raw_page_text
        indexing_text_strategy = "raw_text_plus_confirmed_fields"
    else:
        text = raw_page_text
        indexing_text_strategy = "raw_text_only"
    routing_info = dict(routing_diagnostics or {})
    routing_info.setdefault("feature_flag_enabled", bool(getattr(rag_settings, "pdf_evidence_pipeline_enabled", False)))
    routing_info.setdefault("filename_hint", _looks_like_cv_filename(filename))
    routing_info.setdefault("cv_like_content_detected", False)
    routing_info.setdefault("cv_like_reasons", [])
    routing_info.setdefault("strong_scan_like", result.source_type == "scanned_pdf")
    routing_info["decision"] = "evidence_path"
    routing_info.setdefault("reason", "evidence_path_selected")
    metadata = {
        "extractor": "evidence_cv_pipeline",
        "strategy": "evidence_parallel",
        "strategy_label": "Evidence CV pipeline",
        "evidence_pipeline_used": True,
        "evidence_summary": evidence_summary,
        "source_type": result.source_type,
        "warnings": result.warnings,
        "page_count": len(result.pages),
        "product_consumption": result.product_consumption,
        "vl_runtime": result.product_consumption.get("vl_runtime", {}),
        "vl_router": result.runtime_metadata.get("vl_router", {}),
        "indexing_payload": indexing_payload,
        "indexing_text_strategy": indexing_text_strategy,
        "indexing_payload_quality": payload_quality,
        "included_structured_sections": payload_quality.get("included_structured_sections", []),
        "dropped_structured_sections": payload_quality.get("dropped_structured_sections", []),
        "dropped_section_reasons": payload_quality.get("dropped_section_reasons", []),
        "routing_diagnostics": routing_info,
    }
    return text, metadata


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
    metadata = result.metadata or {}
    metadata.setdefault("evidence_summary", {
        "emails": [],
        "phones": [],
        "name_value": None,
        "location_value": None,
    })
    return result.text, metadata


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
        use_evidence_pipeline, routing_diagnostics = _build_evidence_routing_diagnostics(file_bytes, uploaded_file.name, rag_settings)
        if use_evidence_pipeline:
            try:
                legacy_text, legacy_metadata = _extract_pdf_text(file_bytes, rag_settings)
                text, metadata = _extract_pdf_text_with_evidence_pipeline(
                    file_bytes,
                    uploaded_file.name,
                    rag_settings,
                    routing_diagnostics=routing_diagnostics,
                )
                metadata["hybrid_contact_policy"] = _apply_hybrid_contact_policy(legacy_metadata, metadata)
                metadata["shadow_rollout"] = _build_shadow_rollout_report(legacy_metadata, metadata)
                metadata["legacy_shadow_reference"] = {
                    "extractor": legacy_metadata.get("extractor"),
                    "strategy": legacy_metadata.get("strategy"),
                }
                if not text.strip():
                    text = legacy_text
                metadata["fallback_available"] = True
            except Exception as error:
                text, metadata = _extract_pdf_text(file_bytes, rag_settings)
                metadata["evidence_pipeline_error"] = str(error)
                metadata["evidence_pipeline_fallback_used"] = True
                metadata["routing_diagnostics"] = {
                    **routing_diagnostics,
                    "decision": "legacy_path",
                    "reason": "evidence_pipeline_runtime_error",
                }
        else:
            text, metadata = _extract_pdf_text(file_bytes, rag_settings)
            metadata["routing_diagnostics"] = routing_diagnostics
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
