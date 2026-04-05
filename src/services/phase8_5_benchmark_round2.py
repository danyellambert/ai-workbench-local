from __future__ import annotations

import hashlib
import json
import re
import statistics
import time
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from ..config import BASE_DIR, RagSettings, get_rag_settings
from ..evidence_cv.config import build_evidence_config_from_rag_settings
from ..evidence_cv.pipeline.runner import run_cv_pipeline_from_bytes
from ..providers.registry import resolve_provider_runtime_profile
from ..rag.loaders import _extract_pdf_text, _extract_pdf_text_with_evidence_pipeline, load_document
from ..rag.service import retrieve_relevant_chunks_detailed, upsert_documents_in_rag_index


EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


class _LocalUploadedFile:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self._bytes = path.read_bytes()

    def getvalue(self) -> bytes:
        return self._bytes


def _resolve_repo_path(path_value: str | Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return (BASE_DIR / candidate).resolve()


def _stable_case_id(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"case_{hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:16]}"


def _apply_smoke_limit(items: list[dict[str, object]], max_items: int | None) -> list[dict[str, object]]:
    if not isinstance(max_items, int) or max_items <= 0:
        return list(items)
    return list(items[:max_items])


def validate_round2_manifest_groups(manifest: dict[str, object]) -> None:
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}

    rerankers = groups.get("rerankers")
    if rerankers is not None:
        if not isinstance(rerankers, dict):
            raise ValueError("Manifest group 'rerankers' must be an object.")
        dataset = rerankers.get("dataset")
        candidates = rerankers.get("candidates")
        if not isinstance(dataset, dict):
            raise ValueError("Manifest rerankers.dataset must be an object.")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError("Manifest rerankers.candidates must be a non-empty list.")
        pdf_paths = dataset.get("pdf_paths")
        question_set_path = dataset.get("question_set_path")
        if not isinstance(pdf_paths, list) or not pdf_paths:
            raise ValueError("Manifest rerankers.dataset.pdf_paths must be a non-empty list.")
        if not str(dataset.get("embedding_provider") or "").strip() or not str(dataset.get("embedding_model") or "").strip():
            raise ValueError("Manifest rerankers.dataset must define embedding_provider and embedding_model.")
        if not str(question_set_path or "").strip():
            raise ValueError("Manifest rerankers.dataset.question_set_path must be configured.")
        for pdf_path in pdf_paths:
            resolved = _resolve_repo_path(str(pdf_path))
            if not resolved.exists():
                raise ValueError(f"Reranker dataset PDF not found: {resolved}")
        if not _resolve_repo_path(str(question_set_path)).exists():
            raise ValueError(f"Reranker question set not found: {_resolve_repo_path(str(question_set_path))}")

    ocr_vlm = groups.get("ocr_vlm")
    if ocr_vlm is not None:
        if not isinstance(ocr_vlm, dict):
            raise ValueError("Manifest group 'ocr_vlm' must be an object.")
        cases = ocr_vlm.get("cases")
        if not isinstance(cases, list) or not cases:
            raise ValueError("Manifest ocr_vlm.cases must be a non-empty list.")
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError("OCR/VLM case definitions must be objects.")
            pdf_path = _resolve_repo_path(str(case.get("pdf_path") or ""))
            gold_path = _resolve_repo_path(str(case.get("gold_path") or ""))
            if not pdf_path.exists():
                raise ValueError(f"OCR/VLM benchmark PDF not found: {pdf_path}")
            if not gold_path.exists():
                raise ValueError(f"OCR/VLM gold file not found: {gold_path}")


def build_reranker_cases(
    manifest: dict[str, object],
    *,
    smoke: bool,
    provider_filter: str | None = None,
    model_filter: str | None = None,
) -> list[dict[str, object]]:
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    rerankers = groups.get("rerankers") if isinstance(groups.get("rerankers"), dict) else {}
    dataset = rerankers.get("dataset") if isinstance(rerankers.get("dataset"), dict) else {}
    smoke_limits = rerankers.get("smoke_limits") if isinstance(rerankers.get("smoke_limits"), dict) else {}
    candidates = [item for item in (rerankers.get("candidates") or []) if isinstance(item, dict)]
    pdf_paths = [_resolve_repo_path(str(item)) for item in (dataset.get("pdf_paths") or [])]
    question_set_path = _resolve_repo_path(str(dataset.get("question_set_path") or ""))
    question_payload = json.loads(question_set_path.read_text(encoding="utf-8"))
    questions = [item for item in (question_payload.get("questions") or []) if isinstance(item, dict)]
    repetitions = int(rerankers.get("repetitions") or 1)
    embedding_provider = str(dataset.get("embedding_provider") or "").strip().lower()
    embedding_model = str(dataset.get("embedding_model") or "").strip()
    if provider_filter and embedding_provider != str(provider_filter).strip().lower():
        return []
    if model_filter and embedding_model != str(model_filter).strip():
        return []
    if smoke:
        candidates = _apply_smoke_limit(candidates, int(smoke_limits.get("max_candidates") or 0))
        pdf_paths = pdf_paths[: max(1, int(smoke_limits.get("max_pdfs") or 1))]
        questions = questions[: max(1, int(smoke_limits.get("max_questions") or 1))]
        repetitions = int(smoke_limits.get("repetitions") or 1)

    cases: list[dict[str, object]] = []
    for candidate in candidates:
        for repetition in range(1, repetitions + 1):
            identity = {
                "group": "rerankers",
                "candidate_id": candidate.get("candidate_id"),
                "embedding_provider": dataset.get("embedding_provider"),
                "embedding_model": dataset.get("embedding_model"),
                "dataset_id": dataset.get("dataset_id"),
                "question_set_id": dataset.get("question_set_id"),
                "repetition": repetition,
                "retrieval_strategy": candidate.get("retrieval_strategy"),
                "rerank_pool_size": candidate.get("rerank_pool_size"),
                "rerank_lexical_weight": candidate.get("rerank_lexical_weight"),
            }
            cases.append(
                {
                    "case_id": _stable_case_id(identity),
                    "group": "rerankers",
                    "candidate_id": candidate.get("candidate_id"),
                    "candidate_label": candidate.get("label") or candidate.get("candidate_id"),
                    "candidate_role": candidate.get("role") or "challenger",
                    "dataset_id": dataset.get("dataset_id") or "phase8_5_reranker_dataset",
                    "question_set_id": dataset.get("question_set_id") or question_set_path.stem,
                    "embedding_provider": embedding_provider,
                    "embedding_model": embedding_model,
                    "pdf_paths": [str(path) for path in pdf_paths],
                    "questions": questions,
                    "question_set_path": str(question_set_path),
                    "top_k": int(candidate.get("top_k") or dataset.get("top_k") or manifest.get("fairness", {}).get("top_k") or 4),
                    "rerank_pool_size": int(candidate.get("rerank_pool_size") or manifest.get("fairness", {}).get("rerank_pool_size") or 8),
                    "rerank_lexical_weight": float(candidate.get("rerank_lexical_weight") or 0.0),
                    "chunk_size": int(dataset.get("chunk_size") or manifest.get("fairness", {}).get("chunk_size") or 1200),
                    "chunk_overlap": int(dataset.get("chunk_overlap") or manifest.get("fairness", {}).get("chunk_overlap") or 80),
                    "embedding_context_window": int(dataset.get("embedding_context_window") or manifest.get("fairness", {}).get("embedding_context_window") or 512),
                    "embedding_truncate": bool(dataset.get("embedding_truncate", manifest.get("fairness", {}).get("embedding_truncate", True))),
                    "retrieval_strategy": str(candidate.get("retrieval_strategy") or "manual_hybrid"),
                    "repetition": repetition,
                    "support_status": candidate.get("support_status") or "fully_supported",
                }
            )
    return cases


def build_ocr_vlm_cases(
    manifest: dict[str, object],
    *,
    smoke: bool,
    provider_filter: str | None = None,
    model_filter: str | None = None,
) -> list[dict[str, object]]:
    if provider_filter or model_filter:
        return []
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), dict) else {}
    ocr_vlm = groups.get("ocr_vlm") if isinstance(groups.get("ocr_vlm"), dict) else {}
    smoke_limits = ocr_vlm.get("smoke_limits") if isinstance(ocr_vlm.get("smoke_limits"), dict) else {}
    cases = [item for item in (ocr_vlm.get("cases") or []) if isinstance(item, dict)]
    repetitions = int(ocr_vlm.get("repetitions") or 1)
    if smoke:
        cases = _apply_smoke_limit(cases, int(smoke_limits.get("max_cases") or 0))
        repetitions = int(smoke_limits.get("repetitions") or 1)

    built: list[dict[str, object]] = []
    for case in cases:
        pdf_path = _resolve_repo_path(str(case.get("pdf_path") or ""))
        gold_path = _resolve_repo_path(str(case.get("gold_path") or ""))
        for repetition in range(1, repetitions + 1):
            identity = {
                "group": "ocr_vlm",
                "pdf_path": str(pdf_path),
                "gold_path": str(gold_path),
                "case_name": case.get("case_name") or pdf_path.stem,
                "repetition": repetition,
            }
            built.append(
                {
                    "case_id": _stable_case_id(identity),
                    "group": "ocr_vlm",
                    "case_name": case.get("case_name") or pdf_path.stem,
                    "label": case.get("label") or case.get("case_name") or pdf_path.name,
                    "document_type": case.get("document_type") or "cv_resume",
                    "pdf_path": str(pdf_path),
                    "gold_path": str(gold_path),
                    "repetition": repetition,
                    "support_status": case.get("support_status") or "partially_supported",
                }
            )
    return built


def _build_reranker_settings(case: dict[str, object], case_dir: Path) -> RagSettings:
    base = get_rag_settings()
    return replace(
        base,
        embedding_provider=str(case.get("embedding_provider") or base.embedding_provider),
        embedding_model=str(case.get("embedding_model") or base.embedding_model),
        embedding_context_window=int(case.get("embedding_context_window") or base.embedding_context_window),
        embedding_truncate=bool(case.get("embedding_truncate", base.embedding_truncate)),
        chunk_size=int(case.get("chunk_size") or base.chunk_size),
        chunk_overlap=int(case.get("chunk_overlap") or base.chunk_overlap),
        top_k=int(case.get("top_k") or base.top_k),
        rerank_pool_size=int(case.get("rerank_pool_size") or base.rerank_pool_size),
        rerank_lexical_weight=float(case.get("rerank_lexical_weight") or 0.0),
        retrieval_strategy=str(case.get("retrieval_strategy") or base.retrieval_strategy),
        store_path=case_dir / ".rag_store.json",
        chroma_path=case_dir / ".chroma_rag",
    )


def _run_reranker_questions(
    *,
    questions: list[dict[str, object]],
    rag_index: dict[str, object],
    settings: RagSettings,
    embedding_provider: object,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    retrieval_seconds: list[float] = []
    hit_at_1_values: list[int] = []
    hit_at_k_values: list[int] = []
    reciprocal_ranks: list[float] = []
    groundedness_values: list[float] = []
    question_rows: list[dict[str, object]] = []

    for item in questions:
        question = str(item.get("question") or "")
        expected_document_names = {str(name) for name in item.get("expected_document_names", [])}
        started_at = time.perf_counter()
        details = retrieve_relevant_chunks_detailed(
            query=question,
            rag_index=rag_index,
            settings=settings,
            embedding_provider=embedding_provider,
        )
        elapsed = time.perf_counter() - started_at
        retrieval_seconds.append(elapsed)
        chunks = details.get("chunks") if isinstance(details.get("chunks"), list) else []
        retrieved_names = [str(chunk.get("source") or "") for chunk in chunks if isinstance(chunk, dict)]
        hit_at_1 = bool(retrieved_names[:1] and retrieved_names[0] in expected_document_names)
        hit_at_k = any(name in expected_document_names for name in retrieved_names[: settings.top_k])
        reciprocal_rank = 0.0
        first_relevant_rank = None
        for rank, name in enumerate(retrieved_names, start=1):
            if name in expected_document_names:
                reciprocal_rank = 1.0 / rank
                first_relevant_rank = rank
                break
        groundedness = round(sum(1 for name in retrieved_names if name in expected_document_names) / max(len(retrieved_names), 1), 4) if retrieved_names else 0.0

        hit_at_1_values.append(1 if hit_at_1 else 0)
        hit_at_k_values.append(1 if hit_at_k else 0)
        reciprocal_ranks.append(reciprocal_rank)
        groundedness_values.append(groundedness)
        question_rows.append(
            {
                "question": question,
                "expected_document_names": sorted(expected_document_names),
                "retrieved_names": retrieved_names,
                "hit_at_1": hit_at_1,
                "hit_at_k": hit_at_k,
                "reciprocal_rank": round(reciprocal_rank, 4),
                "first_relevant_rank": first_relevant_rank,
                "retrieval_seconds": round(elapsed, 4),
                "backend_used": details.get("backend_used"),
                "candidate_pool_size": details.get("candidate_pool_size"),
                "reranking_applied": details.get("reranking_applied"),
                "retrieval_strategy_used": details.get("retrieval_strategy_used"),
                "rerank_strategy": details.get("rerank_strategy"),
                "groundedness_proxy": groundedness,
            }
        )

    aggregate = {
        "question_count": len(questions),
        "hit_at_1": round(sum(hit_at_1_values) / max(len(hit_at_1_values), 1), 4) if hit_at_1_values else 0.0,
        "hit_at_k": round(sum(hit_at_k_values) / max(len(hit_at_k_values), 1), 4) if hit_at_k_values else 0.0,
        "mrr": round(sum(reciprocal_ranks) / max(len(reciprocal_ranks), 1), 4) if reciprocal_ranks else 0.0,
        "average_retrieval_seconds": round(statistics.mean(retrieval_seconds), 4) if retrieval_seconds else 0.0,
        "median_retrieval_seconds": round(statistics.median(retrieval_seconds), 4) if retrieval_seconds else 0.0,
        "avg_groundedness_proxy": round(sum(groundedness_values) / max(len(groundedness_values), 1), 4) if groundedness_values else 0.0,
    }
    return question_rows, aggregate


def execute_reranker_case(
    case: dict[str, object],
    *,
    run_id: str,
    registry: dict[str, dict[str, object]],
    run_output_dir: Path,
) -> dict[str, object]:
    provider_requested = str(case.get("embedding_provider") or "")
    model_requested = str(case.get("embedding_model") or "")
    runtime_profile = resolve_provider_runtime_profile(registry, provider_requested, capability="embeddings", fallback_provider=None)
    provider_entry = runtime_profile.get("provider_entry") if isinstance(runtime_profile.get("provider_entry"), dict) else {}
    provider_instance = provider_entry.get("instance")
    started_at = time.time()
    event: dict[str, object] = {
        "event_type": "case_result",
        "run_id": run_id,
        "case_id": case.get("case_id"),
        "status": "failed",
        "group": "rerankers",
        "started_at": started_at,
        "provider_requested": provider_requested,
        "provider_effective": runtime_profile.get("effective_provider") or provider_requested,
        "model_requested": model_requested,
        "model_effective": model_requested,
        "candidate_id": case.get("candidate_id"),
        "candidate_label": case.get("candidate_label"),
        "candidate_role": case.get("candidate_role"),
        "dataset_id": case.get("dataset_id"),
        "question_set_id": case.get("question_set_id"),
        "repetition": case.get("repetition"),
        "retrieval_strategy": case.get("retrieval_strategy"),
        "rerank_pool_size": case.get("rerank_pool_size"),
        "rerank_lexical_weight": case.get("rerank_lexical_weight"),
        "support_status": case.get("support_status"),
        "error": None,
    }
    if provider_instance is None:
        event["finished_at"] = time.time()
        event["error"] = runtime_profile.get("fallback_reason") or "embedding_provider_unavailable"
        return event

    case_dir = run_output_dir / "cases" / str(case.get("case_id"))
    case_dir.mkdir(parents=True, exist_ok=True)
    settings = _build_reranker_settings(case, case_dir)
    try:
        documents = [load_document(_LocalUploadedFile(Path(path)), settings) for path in case.get("pdf_paths") or []]
        indexing_started = time.perf_counter()
        rag_index, sync_status = upsert_documents_in_rag_index(
            documents=documents,
            settings=settings,
            embedding_provider=provider_instance,
            rag_index=None,
        )
        indexing_seconds = time.perf_counter() - indexing_started
        question_rows, aggregate = _run_reranker_questions(
            questions=list(case.get("questions") or []),
            rag_index=rag_index,
            settings=settings,
            embedding_provider=provider_instance,
        )
        event.update(
            {
                "status": "success",
                "finished_at": time.time(),
                "indexing_seconds": round(indexing_seconds, 4),
                "sync_status": sync_status,
                "aggregate_metrics": aggregate,
                "per_question_results": question_rows,
                "question_count": aggregate.get("question_count"),
                "hit_at_1": aggregate.get("hit_at_1"),
                "hit_at_k": aggregate.get("hit_at_k"),
                "mrr": aggregate.get("mrr"),
                "average_retrieval_seconds": aggregate.get("average_retrieval_seconds"),
                "median_retrieval_seconds": aggregate.get("median_retrieval_seconds"),
                "avg_groundedness_proxy": aggregate.get("avg_groundedness_proxy"),
            }
        )
    except Exception as error:
        event["finished_at"] = time.time()
        event["error"] = str(error)
    return event


def _normalize_email(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if EMAIL_PATTERN.match(normalized) else ""


def _normalize_phone(value: str) -> str:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return digits if 8 <= len(digits) <= 15 else ""


def _normalize_email_list(values: list[str]) -> list[str]:
    return sorted({item for item in (_normalize_email(value) for value in values) if item})


def _normalize_phone_list(values: list[str]) -> list[str]:
    return sorted({item for item in (_normalize_phone(value) for value in values) if item})


def _score_list(predicted: list[str], expected: list[str]) -> dict[str, object]:
    pred = set(predicted)
    gold = set(expected)
    tp = len(pred & gold)
    fp = len(pred - gold)
    fn = len(gold - pred)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _score_single_alias(predicted: str | None, aliases: list[str], status: str | None = None) -> dict[str, object]:
    normalized_prediction = str(predicted or "").strip().lower()
    matched = bool(normalized_prediction) and any(
        alias.strip().lower() in normalized_prediction or normalized_prediction in alias.strip().lower()
        for alias in aliases
        if str(alias).strip()
    )
    tp = int(matched)
    fp = int(bool(normalized_prediction) and not matched)
    fn = int(bool(aliases) and not matched)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if precision + recall else 0.0
    return {
        "predicted": predicted,
        "status": status,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _extract_legacy_contacts(file_bytes: bytes, settings: RagSettings) -> dict[str, object]:
    text, metadata = _extract_pdf_text(file_bytes, settings)
    emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    phones = re.findall(r"\+?\d[\d\s().-]{7,}\d", text)
    return {
        "variant": "legacy_pdf",
        "name": None,
        "location": None,
        "emails": _normalize_email_list(emails),
        "phones": _normalize_phone_list(phones),
        "name_status": "not_found",
        "location_status": "not_found",
        "metadata": metadata,
    }


def _extract_evidence_no_vl(file_bytes: bytes, settings: RagSettings) -> dict[str, object]:
    config = build_evidence_config_from_rag_settings(settings)
    config = config.__class__(**{**config.__dict__, "enable_vl": False, "ocr_backend": settings.evidence_ocr_backend})
    result = run_cv_pipeline_from_bytes(file_bytes, ".pdf", config)
    return {
        "variant": "evidence_no_vl",
        "name": result.resume.name.value,
        "location": result.resume.location.value,
        "emails": _normalize_email_list([item.value for item in result.resume.emails if item.value]),
        "phones": _normalize_phone_list([item.value for item in result.resume.phones if item.value]),
        "name_status": result.resume.name.status,
        "location_status": result.resume.location.status,
        "metadata": {
            "source_type": result.source_type,
            "warnings": result.warnings,
            "vl_router": result.runtime_metadata.get("vl_router") if isinstance(result.runtime_metadata, dict) else None,
        },
    }


def _extract_evidence_with_vl(file_bytes: bytes, filename: str, settings: RagSettings) -> dict[str, object]:
    _, metadata = _extract_pdf_text_with_evidence_pipeline(file_bytes, filename, settings)
    summary = metadata.get("evidence_summary") if isinstance(metadata.get("evidence_summary"), dict) else {}
    return {
        "variant": "evidence_with_vl",
        "name": summary.get("name_value"),
        "location": summary.get("location_value"),
        "emails": _normalize_email_list(summary.get("emails") or []),
        "phones": _normalize_phone_list(summary.get("phones") or []),
        "name_status": summary.get("name_status"),
        "location_status": summary.get("location_status"),
        "metadata": metadata,
    }


def execute_ocr_vlm_case(
    case: dict[str, object],
    *,
    run_id: str,
) -> dict[str, object]:
    settings = get_rag_settings()
    pdf_path = Path(str(case.get("pdf_path") or ""))
    gold_path = Path(str(case.get("gold_path") or ""))
    file_bytes = pdf_path.read_bytes()
    gold_payload = json.loads(gold_path.read_text(encoding="utf-8"))
    expected = gold_payload.get("expected") if isinstance(gold_payload.get("expected"), dict) else {}
    personal = expected.get("expected_personal_info") if isinstance(expected.get("expected_personal_info"), dict) else {}
    gold_emails = _normalize_email_list(personal.get("email_aliases") or [])
    gold_name_aliases = [str(item) for item in (personal.get("full_name_aliases") or []) if str(item).strip()]
    gold_location_aliases = [str(item) for item in (personal.get("location_aliases") or []) if str(item).strip()]

    started_at = time.time()
    event: dict[str, object] = {
        "event_type": "case_result",
        "run_id": run_id,
        "case_id": case.get("case_id"),
        "status": "failed",
        "group": "ocr_vlm",
        "started_at": started_at,
        "case_name": case.get("case_name"),
        "label": case.get("label"),
        "document_type": case.get("document_type"),
        "pdf_path": str(pdf_path),
        "gold_path": str(gold_path),
        "repetition": case.get("repetition"),
        "support_status": case.get("support_status"),
        "error": None,
    }
    try:
        variants: list[dict[str, object]] = []
        start = time.perf_counter()
        legacy = _extract_legacy_contacts(file_bytes, settings)
        legacy_elapsed = time.perf_counter() - start
        variants.append({**legacy, "latency_s": round(legacy_elapsed, 4)})

        start = time.perf_counter()
        no_vl = _extract_evidence_no_vl(file_bytes, settings)
        no_vl_elapsed = time.perf_counter() - start
        variants.append({**no_vl, "latency_s": round(no_vl_elapsed, 4)})

        start = time.perf_counter()
        with_vl = _extract_evidence_with_vl(file_bytes, pdf_path.name, settings)
        with_vl_elapsed = time.perf_counter() - start
        variants.append({**with_vl, "latency_s": round(with_vl_elapsed, 4)})

        for variant in variants:
            email_score = _score_list(variant.get("emails") or [], gold_emails)
            phone_score = _score_list(variant.get("phones") or [], [])
            name_score = _score_single_alias(variant.get("name"), gold_name_aliases, status=str(variant.get("name_status") or ""))
            location_score = _score_single_alias(variant.get("location"), gold_location_aliases, status=str(variant.get("location_status") or ""))
            avg_f1 = round((float(email_score["f1"]) + float(phone_score["f1"]) + float(name_score["f1"]) + float(location_score["f1"])) / 4, 4)
            variant["scores"] = {
                "emails": email_score,
                "phones": phone_score,
                "name": name_score,
                "location": location_score,
                "avg_f1": avg_f1,
            }

        baseline_f1 = float((variants[0].get("scores") or {}).get("avg_f1") or 0.0)
        for variant in variants:
            variant["helped_vs_legacy"] = float((variant.get("scores") or {}).get("avg_f1") or 0.0) > baseline_f1

        best_variant = max(variants, key=lambda item: float((item.get("scores") or {}).get("avg_f1") or 0.0), default=None)
        event.update(
            {
                "status": "success",
                "finished_at": time.time(),
                "variant_results": variants,
                "best_variant": (best_variant or {}).get("variant"),
                "best_avg_f1": (best_variant or {}).get("scores", {}).get("avg_f1") if isinstance((best_variant or {}).get("scores"), dict) else None,
            }
        )
    except Exception as error:
        event["finished_at"] = time.time()
        event["error"] = str(error)
    return event


def normalize_round2_case_results(events: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    reranker_rows: list[dict[str, object]] = []
    reranker_question_rows: list[dict[str, object]] = []
    ocr_vlm_rows: list[dict[str, object]] = []
    for event in events:
        group = str(event.get("group") or "")
        if group == "rerankers":
            aggregate = event.get("aggregate_metrics") if isinstance(event.get("aggregate_metrics"), dict) else {}
            reranker_rows.append(
                {
                    "run_id": event.get("run_id"),
                    "case_id": event.get("case_id"),
                    "status": event.get("status"),
                    "candidate_id": event.get("candidate_id"),
                    "candidate_label": event.get("candidate_label"),
                    "candidate_role": event.get("candidate_role"),
                    "dataset_id": event.get("dataset_id"),
                    "question_set_id": event.get("question_set_id"),
                    "provider_requested": event.get("provider_requested"),
                    "provider_effective": event.get("provider_effective"),
                    "model_requested": event.get("model_requested"),
                    "model_effective": event.get("model_effective"),
                    "retrieval_strategy": event.get("retrieval_strategy"),
                    "rerank_pool_size": event.get("rerank_pool_size"),
                    "rerank_lexical_weight": event.get("rerank_lexical_weight"),
                    "indexing_seconds": event.get("indexing_seconds"),
                    "question_count": aggregate.get("question_count", event.get("question_count")),
                    "hit_at_1": aggregate.get("hit_at_1", event.get("hit_at_1")),
                    "hit_at_k": aggregate.get("hit_at_k", event.get("hit_at_k")),
                    "mrr": aggregate.get("mrr", event.get("mrr")),
                    "average_retrieval_seconds": aggregate.get("average_retrieval_seconds", event.get("average_retrieval_seconds")),
                    "median_retrieval_seconds": aggregate.get("median_retrieval_seconds", event.get("median_retrieval_seconds")),
                    "avg_groundedness_proxy": aggregate.get("avg_groundedness_proxy", event.get("avg_groundedness_proxy")),
                    "support_status": event.get("support_status"),
                    "error": event.get("error"),
                }
            )
            for question in event.get("per_question_results") or []:
                if not isinstance(question, dict):
                    continue
                reranker_question_rows.append(
                    {
                        "run_id": event.get("run_id"),
                        "case_id": event.get("case_id"),
                        "candidate_id": event.get("candidate_id"),
                        "question": question.get("question"),
                        "hit_at_1": question.get("hit_at_1"),
                        "hit_at_k": question.get("hit_at_k"),
                        "reciprocal_rank": question.get("reciprocal_rank"),
                        "retrieval_seconds": question.get("retrieval_seconds"),
                        "backend_used": question.get("backend_used"),
                        "groundedness_proxy": question.get("groundedness_proxy"),
                    }
                )
        elif group == "ocr_vlm":
            for variant in event.get("variant_results") or []:
                if not isinstance(variant, dict):
                    continue
                scores = variant.get("scores") if isinstance(variant.get("scores"), dict) else {}
                ocr_vlm_rows.append(
                    {
                        "run_id": event.get("run_id"),
                        "case_id": event.get("case_id"),
                        "status": event.get("status"),
                        "case_name": event.get("case_name"),
                        "document_type": event.get("document_type"),
                        "variant": variant.get("variant"),
                        "latency_s": variant.get("latency_s"),
                        "avg_f1": scores.get("avg_f1"),
                        "emails_f1": (scores.get("emails") or {}).get("f1") if isinstance(scores.get("emails"), dict) else None,
                        "phones_f1": (scores.get("phones") or {}).get("f1") if isinstance(scores.get("phones"), dict) else None,
                        "name_f1": (scores.get("name") or {}).get("f1") if isinstance(scores.get("name"), dict) else None,
                        "location_f1": (scores.get("location") or {}).get("f1") if isinstance(scores.get("location"), dict) else None,
                        "helped_vs_legacy": variant.get("helped_vs_legacy"),
                        "name_status": variant.get("name_status"),
                        "location_status": variant.get("location_status"),
                        "support_status": event.get("support_status"),
                        "error": event.get("error"),
                    }
                )
    return {
        "rerankers": reranker_rows,
        "reranker_questions": reranker_question_rows,
        "ocr_vlm": ocr_vlm_rows,
    }


def _average(values: list[float]) -> float:
    return round(sum(values) / max(len(values), 1), 4) if values else 0.0


def aggregate_reranker_events(events: list[dict[str, object]]) -> dict[str, object]:
    by_candidate: dict[str, list[dict[str, object]]] = defaultdict(list)
    for event in events:
        by_candidate[str(event.get("candidate_id") or "candidate")].append(event)
    ranking: list[dict[str, object]] = []
    for candidate_id, candidate_events in by_candidate.items():
        successful = [item for item in candidate_events if item.get("status") == "success"]
        ranking.append(
            {
                "candidate_id": candidate_id,
                "candidate_label": candidate_events[0].get("candidate_label"),
                "candidate_role": candidate_events[0].get("candidate_role"),
                "provider": candidate_events[0].get("provider_requested"),
                "model": candidate_events[0].get("model_requested"),
                "case_count": len(candidate_events),
                "support_status": candidate_events[0].get("support_status"),
                "success_rate": round(len(successful) / max(len(candidate_events), 1), 4),
                "avg_hit_at_1": _average([float(item.get("hit_at_1")) for item in successful if isinstance(item.get("hit_at_1"), (int, float))]),
                "avg_hit_at_k": _average([float(item.get("hit_at_k")) for item in successful if isinstance(item.get("hit_at_k"), (int, float))]),
                "avg_mrr": _average([float(item.get("mrr")) for item in successful if isinstance(item.get("mrr"), (int, float))]),
                "avg_retrieval_seconds": _average([float(item.get("average_retrieval_seconds")) for item in successful if isinstance(item.get("average_retrieval_seconds"), (int, float))]),
                "avg_groundedness_proxy": _average([float(item.get("avg_groundedness_proxy")) for item in successful if isinstance(item.get("avg_groundedness_proxy"), (int, float))]),
            }
        )
    ranking.sort(key=lambda item: (-float(item.get("avg_mrr") or 0.0), float(item.get("avg_retrieval_seconds") or 10**9)))
    return {
        "total_cases": len(events),
        "successful_cases": sum(1 for item in events if item.get("status") == "success"),
        "failed_cases": sum(1 for item in events if item.get("status") != "success"),
        "candidate_ranking": ranking,
        "best_tradeoff": ranking[0] if ranking else None,
        "support_level": "fully_supported" if ranking else "scaffolded_only",
    }


def aggregate_ocr_vlm_events(events: list[dict[str, object]]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for event in events:
        for variant in event.get("variant_results") or []:
            if isinstance(variant, dict):
                rows.append({"case_name": event.get("case_name"), **variant})
    by_variant: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_variant[str(row.get("variant") or "variant")].append(row)
    ranking: list[dict[str, object]] = []
    for variant_name, variant_rows in by_variant.items():
        ranking.append(
            {
                "variant": variant_name,
                "case_count": len(variant_rows),
                "avg_latency_s": _average([float(item.get("latency_s")) for item in variant_rows if isinstance(item.get("latency_s"), (int, float))]),
                "avg_f1": _average([float((item.get("scores") or {}).get("avg_f1")) for item in variant_rows if isinstance((item.get("scores") or {}).get("avg_f1"), (int, float))]),
                "helped_cases": sum(1 for item in variant_rows if bool(item.get("helped_vs_legacy"))),
            }
        )
    ranking.sort(key=lambda item: (-float(item.get("avg_f1") or 0.0), float(item.get("avg_latency_s") or 10**9)))
    return {
        "total_cases": len(events),
        "successful_cases": sum(1 for item in events if item.get("status") == "success"),
        "failed_cases": sum(1 for item in events if item.get("status") != "success"),
        "variant_ranking": ranking,
        "best_ocr_tradeoff": next((item for item in ranking if item.get("variant") == "evidence_no_vl"), None),
        "best_vlm_tradeoff": next((item for item in ranking if item.get("variant") == "evidence_with_vl"), None),
        "support_level": "partially_supported" if ranking else "scaffolded_only",
    }


def build_round2_report_sections(aggregated: dict[str, object]) -> list[str]:
    lines: list[str] = []
    rerankers = aggregated.get("rerankers") if isinstance(aggregated.get("rerankers"), dict) else {}
    ocr_vlm = aggregated.get("ocr_vlm") if isinstance(aggregated.get("ocr_vlm"), dict) else {}
    lines.extend(
        [
            "## Reranker leaderboard",
            "",
            "| Rank | Candidate | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) | Avg groundedness proxy |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for index, item in enumerate(rerankers.get("candidate_ranking") or [], start=1):
        lines.append(
            f"| {index} | `{item.get('candidate_id')}` | `{item.get('candidate_role')}` | {float(item.get('avg_mrr') or 0.0):.4f} | {float(item.get('avg_hit_at_1') or 0.0):.4f} | {float(item.get('avg_retrieval_seconds') or 0.0):.4f} | {float(item.get('avg_groundedness_proxy') or 0.0):.4f} |"
        )
    lines.extend(
        [
            "",
            "## OCR / VLM leaderboard",
            "",
            "| Rank | Variant | Avg F1 | Avg latency (s) | Helped cases |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for index, item in enumerate(ocr_vlm.get("variant_ranking") or [], start=1):
        lines.append(
            f"| {index} | `{item.get('variant')}` | {float(item.get('avg_f1') or 0.0):.4f} | {float(item.get('avg_latency_s') or 0.0):.4f} | {int(item.get('helped_cases') or 0)} |"
        )
    lines.extend(
        [
            "",
            "## Round 2 tradeoff notes",
            "",
            f"- Best reranker tradeoff: `{((rerankers.get('best_tradeoff') or {}).get('candidate_id')) or 'n/a'}`",
            f"- Best OCR fallback tradeoff: `{((ocr_vlm.get('best_ocr_tradeoff') or {}).get('variant')) or 'n/a'}`",
            f"- Best VLM fallback tradeoff: `{((ocr_vlm.get('best_vlm_tradeoff') or {}).get('variant')) or 'n/a'}`",
            "- Support is intentionally incremental: reranker comparisons are fully local and executable; OCR/VLM comparisons focus on reusable CV/contact-evidence slices already present in the repo.",
            "",
        ]
    )
    return lines
