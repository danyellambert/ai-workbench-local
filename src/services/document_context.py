from __future__ import annotations

from typing import Any, Optional

from ..config import get_rag_settings
from ..rag.service import retrieve_relevant_chunks_detailed


DEFAULT_DOCUMENT_SCAN_CHUNKS = 10
DEFAULT_DOCUMENT_SCAN_CHARS = 18000
DEFAULT_RETRIEVAL_CHUNKS = 8
DEFAULT_RETRIEVAL_CHARS = 14000
DEFAULT_FULL_CV_CHARS = 32000


def _normalize_whitespace(value: str) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def _looks_like_noisy_field_value(value: Any) -> bool:
    text = _normalize_whitespace(str(value or ""))
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


def _value_if_usable(value: Any) -> str | None:
    text = _normalize_whitespace(str(value or ""))
    if not text or _looks_like_noisy_field_value(text):
        return None
    return text


def _append_section(parts: list[str], title: str, lines: list[str]) -> None:
    clean_lines = [line for line in lines if line and line.strip()]
    if clean_lines:
        parts.append(f"[{title}]\n" + "\n".join(clean_lines))


def _serialize_confirmed_fields(confirmed: dict[str, Any]) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for label, key in (("Name", "name"), ("Location", "location")):
        usable = _value_if_usable(confirmed.get(key))
        if usable:
            lines.append(f"{label}: {usable}")
        elif confirmed.get(key):
            dropped.append(f"confirmed_fields.{key}: noisy_or_implausible_value")
    emails = [_normalize_whitespace(item) for item in confirmed.get("emails", []) if _normalize_whitespace(item)]
    phones = [_normalize_whitespace(item) for item in confirmed.get("phones", []) if _normalize_whitespace(item)]
    if emails:
        lines.append(f"Emails: {', '.join(emails)}")
    if phones:
        lines.append(f"Phones: {', '.join(phones)}")
    return lines, dropped


def _serialize_experience_entries(entries: list[Any]) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            dropped.append(f"experience[{index}]: non_dict_entry")
            continue
        title = _value_if_usable(((entry.get("title") or {}).get("value") if isinstance(entry.get("title"), dict) else entry.get("title")))
        company = _value_if_usable(((entry.get("company") or {}).get("value") if isinstance(entry.get("company"), dict) else entry.get("company")))
        date_range = _value_if_usable(((entry.get("date_range") or {}).get("value") if isinstance(entry.get("date_range"), dict) else entry.get("date_range")))
        location = _value_if_usable(((entry.get("location") or {}).get("value") if isinstance(entry.get("location"), dict) else entry.get("location")))
        bullets_raw = entry.get("description_or_bullets") or []
        bullets = []
        for bullet in bullets_raw:
            value = _value_if_usable((bullet.get("value") if isinstance(bullet, dict) else bullet))
            if value:
                bullets.append(value)
        if not any([title, company, date_range, location, bullets]):
            dropped.append(f"experience[{index}]: all_fields_noisy_or_empty")
            continue
        header = " | ".join(item for item in [title, company, date_range, location] if item)
        if header:
            lines.append(f"- {header}")
        for bullet in bullets[:5]:
            lines.append(f"  • {bullet}")
    return lines, dropped


def _serialize_education_entries(entries: list[Any]) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            dropped.append(f"education[{index}]: non_dict_entry")
            continue
        institution = _value_if_usable(((entry.get("institution") or {}).get("value") if isinstance(entry.get("institution"), dict) else entry.get("institution")))
        degree = _value_if_usable(((entry.get("degree") or {}).get("value") if isinstance(entry.get("degree"), dict) else entry.get("degree")))
        date_range = _value_if_usable(((entry.get("date_range") or {}).get("value") if isinstance(entry.get("date_range"), dict) else entry.get("date_range")))
        location = _value_if_usable(((entry.get("location") or {}).get("value") if isinstance(entry.get("location"), dict) else entry.get("location")))
        if not any([institution, degree, date_range, location]):
            dropped.append(f"education[{index}]: all_fields_noisy_or_empty")
            continue
        lines.append("- " + " | ".join(item for item in [degree, institution, date_range, location] if item))
    return lines, dropped


def _serialize_simple_list_entries(entries: list[Any], section_name: str) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        value = entry.get("value") if isinstance(entry, dict) else entry
        usable = _value_if_usable(value)
        if usable:
            lines.append(f"- {usable.lstrip('- ').strip()}")
        else:
            dropped.append(f"{section_name}[{index}]: noisy_or_empty_value")
    return lines, dropped


def _serialize_languages(entries: list[Any]) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    dropped: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            dropped.append(f"languages[{index}]: non_dict_entry")
            continue
        language = _value_if_usable(((entry.get("language") or {}).get("value") if isinstance(entry.get("language"), dict) else entry.get("language")))
        proficiency = _value_if_usable(((entry.get("proficiency") or {}).get("value") if isinstance(entry.get("proficiency"), dict) else entry.get("proficiency")))
        if language:
            lines.append(f"- {language}" + (f" ({proficiency})" if proficiency else ""))
        else:
            dropped.append(f"languages[{index}]: noisy_or_empty_language")
    return lines, dropped


def _clean_raw_cv_text(raw_text: str) -> str:
    text = _normalize_whitespace(raw_text)
    return text[:12000].strip()


def _build_cv_grounding_bundle(indexing_payload: dict[str, Any]) -> dict[str, Any]:
    confirmed = indexing_payload.get("confirmed_fields") or {}
    structured = indexing_payload.get("structured") or {}
    raw_text = str(indexing_payload.get("raw_text") or "")

    parts: list[str] = []
    diagnostics = {
        "included_sections": [],
        "dropped_sections": [],
        "dropped_reasons": [],
        "raw_text_used": False,
    }

    confirmed_lines, confirmed_dropped = _serialize_confirmed_fields(confirmed)
    if confirmed_lines:
        _append_section(parts, "CV CONFIRMED FIELDS", confirmed_lines)
        diagnostics["included_sections"].append("confirmed_fields")
    elif confirmed or confirmed_dropped:
        diagnostics["dropped_sections"].append("confirmed_fields")
    diagnostics["dropped_reasons"].extend(confirmed_dropped)

    serializers = {
        "experience": _serialize_experience_entries,
        "education": _serialize_education_entries,
        "skills": lambda value: _serialize_simple_list_entries(value, "skills"),
        "languages": _serialize_languages,
    }
    labels = {
        "experience": "CV EXPERIENCE",
        "education": "CV EDUCATION",
        "skills": "CV SKILLS",
        "languages": "CV LANGUAGES",
    }
    for key in ("experience", "education", "skills", "languages"):
        entries = structured.get(key) or []
        if not entries:
            continue
        lines, dropped = serializers[key](entries)
        if lines:
            _append_section(parts, labels[key], lines)
            diagnostics["included_sections"].append(key)
        else:
            diagnostics["dropped_sections"].append(key)
        diagnostics["dropped_reasons"].extend(dropped)

    clean_raw = _clean_raw_cv_text(raw_text)
    if clean_raw:
        _append_section(parts, "CV RAW TEXT", [clean_raw])
        diagnostics["raw_text_used"] = True

    diagnostics["fallback_mostly_raw_text"] = diagnostics["raw_text_used"] and not any(
        section in diagnostics["included_sections"] for section in ("experience", "education", "skills", "languages")
    )
    return {
        "context": "\n\n".join(parts).strip(),
        "diagnostics": diagnostics,
    }


def _get_rag_index() -> dict[str, Any] | None:
    try:
        from .rag_state import get_rag_index
    except Exception:
        get_rag_index = None
    if get_rag_index is not None:
        try:
            index = get_rag_index()
            if isinstance(index, dict):
                return index
        except Exception:
            pass
    try:
        from pathlib import Path
        from ..storage.rag_store import load_rag_store
    except Exception:
        return None
    return load_rag_store(Path(".rag_store.json"))


def _get_embedding_provider():
    try:
        from ..providers.registry import build_provider_registry
    except Exception:
        return None
    registry = build_provider_registry()
    return registry.get("ollama", {}).get("instance")


def _filtered_chunks(rag_index: dict[str, Any], document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    chunks = rag_index.get("chunks", []) if isinstance(rag_index, dict) else []
    normalized = [chunk for chunk in chunks if isinstance(chunk, dict)]
    if document_ids:
        allowed = {str(item) for item in document_ids if item}
        normalized = [
            chunk
            for chunk in normalized
            if str(chunk.get("document_id") or chunk.get("file_hash") or "") in allowed
        ]
    return normalized


def _find_documents(rag_index: dict[str, Any], document_ids: list[str] | None = None) -> list[dict[str, Any]]:
    documents = rag_index.get("documents", []) if isinstance(rag_index, dict) else []
    normalized = [doc for doc in documents if isinstance(doc, dict)]
    if document_ids:
        allowed = {str(item) for item in document_ids if item}
        normalized = [
            doc for doc in normalized
            if str(doc.get("document_id") or doc.get("file_hash") or "") in allowed
        ]
    return normalized


def _is_cv_document(document: dict[str, Any]) -> bool:
    name = str(document.get("name") or "").lower()
    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    indexing_payload = metadata.get("indexing_payload") if isinstance(metadata.get("indexing_payload"), dict) else {}
    if metadata.get("evidence_pipeline_used") and indexing_payload:
        return True
    return any(token in name for token in ("cv", "resume", "curriculo", "currículo"))


def _serialize_indexing_payload(indexing_payload: dict[str, Any]) -> str:
    return str(_build_cv_grounding_bundle(indexing_payload).get("context") or "").strip()


def build_full_cv_context(
    document_ids: list[str] | None = None,
    max_chars: int = DEFAULT_FULL_CV_CHARS,
) -> str:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    documents = _find_documents(rag_index, document_ids)
    if len(documents) != 1:
        return ""
    document = documents[0]
    if not _is_cv_document(document):
        return ""

    metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
    indexing_payload = metadata.get("indexing_payload") if isinstance(metadata.get("indexing_payload"), dict) else {}
    full_text = ""
    if indexing_payload:
        full_text = _serialize_indexing_payload(indexing_payload)
    if not full_text:
        chunks = _ordered_chunks(_filtered_chunks(rag_index, document_ids))
        full_text = "\n\n".join(
            str(chunk.get("text") or chunk.get("snippet") or "").strip()
            for chunk in chunks
            if str(chunk.get("text") or chunk.get("snippet") or "").strip()
        ).strip()
    return full_text[:max_chars].strip()


def _ordered_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(chunk: dict[str, Any]) -> tuple[str, int, int]:
        return (
            str(chunk.get("document_id") or chunk.get("file_hash") or "document"),
            int(chunk.get("chunk_id") or 0),
            int(chunk.get("start_char") or 0),
        )

    return sorted(chunks, key=_key)


def _join_chunk_context(chunks: list[dict[str, Any]], max_chars: int) -> str:
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        snippet = str(chunk.get("snippet") or chunk.get("text") or "").strip()
        if not snippet:
            continue
        source = str(chunk.get("source") or chunk.get("document_id") or "document")
        block = f"[Source: {source}]\n{snippet}"
        if used and used + len(block) + 2 > max_chars:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


def build_document_scan_context(
    document_ids: list[str] | None = None,
    max_chunks: int = DEFAULT_DOCUMENT_SCAN_CHUNKS,
    max_chars: int = DEFAULT_DOCUMENT_SCAN_CHARS,
) -> str:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    chunks = _ordered_chunks(_filtered_chunks(rag_index, document_ids))
    if not chunks:
        return ""
    return _join_chunk_context(chunks[:max_chunks], max_chars=max_chars)


def build_retrieval_context(
    query: str,
    document_ids: list[str] | None = None,
    max_chunks: int = DEFAULT_RETRIEVAL_CHUNKS,
    max_chars: int = DEFAULT_RETRIEVAL_CHARS,
) -> str:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return ""
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)

    embedding_provider = _get_embedding_provider()
    if embedding_provider is None:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)

    retrieval = retrieve_relevant_chunks_detailed(
        query=cleaned_query,
        rag_index=rag_index,
        settings=get_rag_settings(),
        embedding_provider=embedding_provider,
        document_ids=document_ids,
    )
    chunks = retrieval.get("chunks", []) if isinstance(retrieval, dict) else []
    if not chunks:
        return build_document_scan_context(document_ids=document_ids, max_chunks=max_chunks, max_chars=max_chars)
    return _join_chunk_context(chunks[:max_chunks], max_chars=max_chars)


def build_structured_document_context(
    *,
    query: str,
    document_ids: list[str] | None = None,
    strategy: str = "document_scan",
    max_chunks: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> str:
    grounding = get_document_grounding_profile(document_ids)
    if grounding.get("single_cv_document"):
        full_cv_context = str(grounding.get("full_cv_context") or "").strip()
        if full_cv_context:
            retrieval_support = build_retrieval_context(
                query=query,
                document_ids=document_ids,
                max_chunks=min(max_chunks or DEFAULT_RETRIEVAL_CHUNKS, 4),
                max_chars=min(max_chars or DEFAULT_RETRIEVAL_CHARS, 6000),
            ).strip()
            retrieval_support = _filter_secondary_retrieval_support(retrieval_support, full_cv_context)
            if retrieval_support and retrieval_support not in full_cv_context:
                return (
                    f"[FULL CV GROUNDING]\n{full_cv_context}\n\n"
                    f"[SECONDARY RETRIEVAL SUPPORT]\n{retrieval_support}"
                ).strip()
            return f"[FULL CV GROUNDING]\n{full_cv_context}".strip()

    strategy = (strategy or "document_scan").strip().lower()
    if strategy == "retrieval":
        return build_retrieval_context(
            query=query,
            document_ids=document_ids,
            max_chunks=max_chunks or DEFAULT_RETRIEVAL_CHUNKS,
            max_chars=max_chars or DEFAULT_RETRIEVAL_CHARS,
        )
    return build_document_scan_context(
        document_ids=document_ids,
        max_chunks=max_chunks or DEFAULT_DOCUMENT_SCAN_CHUNKS,
        max_chars=max_chars or DEFAULT_DOCUMENT_SCAN_CHARS,
    )


def get_document_grounding_profile(document_ids: list[str] | None = None) -> dict[str, Any]:
    rag_index = _get_rag_index()
    if not isinstance(rag_index, dict):
        return {"single_cv_document": False, "full_cv_context": "", "retrieval_context": ""}
    documents = _find_documents(rag_index, document_ids)
    single_cv_document = len(documents) == 1 and _is_cv_document(documents[0])
    return {
        "single_cv_document": single_cv_document,
        "full_cv_context": build_full_cv_context(document_ids=document_ids) if single_cv_document else "",
        "grounding_diagnostics": _build_cv_grounding_bundle(
            ((documents[0].get("loader_metadata") or {}).get("indexing_payload") or {})
        ).get("diagnostics", {}) if single_cv_document and documents else {},
    }


def _filter_secondary_retrieval_support(retrieval_support: str, full_cv_context: str) -> str:
    support = (retrieval_support or "").strip()
    if not support:
        return ""
    normalized_full = _normalize_whitespace(full_cv_context)
    blocks = [block.strip() for block in support.split("\n\n") if block.strip()]
    kept: list[str] = []
    for block in blocks:
        normalized_block = _normalize_whitespace(block)
        if not normalized_block:
            continue
        if normalized_block in normalized_full:
            continue
        if _looks_like_noisy_field_value(normalized_block):
            continue
        kept.append(block)
    return "\n\n".join(kept).strip()
