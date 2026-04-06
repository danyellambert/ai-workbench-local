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
from .model_comparison import (
    infer_model_comparison_quantization_family,
    infer_model_comparison_runtime_bucket,
)
from .phase8_5_neural_reranker import (
    score_query_document_pairs,
    supports_local_neural_reranker_runtime,
)
from .phase8_5_operational_metrics import build_operational_metrics_bundle
from .phase8_5_runtime_metadata import build_runtime_family_metadata
from .phase8_5_timeout import time_limit


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
    if smoke:
        candidates = _apply_smoke_limit(candidates, int(smoke_limits.get("max_candidates") or 0))
        pdf_paths = pdf_paths[: max(1, int(smoke_limits.get("max_pdfs") or 1))]
        questions = questions[: max(1, int(smoke_limits.get("max_questions") or 1))]
        repetitions = int(smoke_limits.get("repetitions") or 1)

    cases: list[dict[str, object]] = []
    for candidate in candidates:
        candidate_provider = str(candidate.get("neural_reranker_provider") or embedding_provider).strip().lower()
        candidate_model = str(
            candidate.get("requested_neural_reranker_model")
            or candidate.get("neural_reranker_model")
            or embedding_model
        ).strip()
        if provider_filter and candidate_provider != str(provider_filter).strip().lower() and embedding_provider != str(provider_filter).strip().lower():
            continue
        if model_filter and candidate_model != str(model_filter).strip() and embedding_model != str(model_filter).strip():
            continue
        for repetition in range(1, repetitions + 1):
            identity = {
                "group": "rerankers",
                "candidate_id": candidate.get("candidate_id"),
                "provider": candidate_provider,
                "model": candidate_model,
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
                    "provider": candidate_provider,
                    "requested_model": candidate_model,
                    "requested_runtime_family": candidate.get("requested_runtime_family") or ("ollama_local" if candidate_provider == "ollama" else candidate_provider),
                    "neural_reranker_provider": candidate.get("neural_reranker_provider"),
                    "requested_neural_reranker_model": candidate.get("requested_neural_reranker_model"),
                    "neural_reranker_model": candidate.get("neural_reranker_model"),
                    "neural_reranker_candidate_models": list(candidate.get("neural_reranker_candidate_models") or []),
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
                    "pdf_extraction_mode": dataset.get("pdf_extraction_mode") or "basic",
                    "pdf_docling_enabled": bool(dataset.get("pdf_docling_enabled", False)),
                    "pdf_ocr_fallback_enabled": bool(dataset.get("pdf_ocr_fallback_enabled", False)),
                    "pdf_scan_image_ocr_enabled": bool(dataset.get("pdf_scan_image_ocr_enabled", False)),
                    "pdf_evidence_pipeline_enabled": bool(dataset.get("pdf_evidence_pipeline_enabled", False)),
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
    variant_matrix = [item for item in (ocr_vlm.get("variant_matrix") or []) if isinstance(item, dict)]
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
                    "variant_matrix": variant_matrix,
                }
            )
    return built


def _discover_round2_provider_models(provider_entry: dict[str, object]) -> list[str]:
    provider_instance = provider_entry.get("instance")
    if provider_instance is None:
        return []
    for method_name in ("list_available_models", "list_available_embedding_models"):
        if hasattr(provider_instance, method_name):
            try:
                return list(getattr(provider_instance, method_name)())
            except Exception:
                continue
    return []


def _resolve_round2_candidate_model(case: dict[str, object], provider_entry: dict[str, object]) -> tuple[str, str, list[str]]:
    requested_model = str(case.get("requested_model") or case.get("neural_reranker_model") or case.get("embedding_model") or "").strip()
    candidate_models = [
        str(item).strip()
        for item in (case.get("neural_reranker_candidate_models") or [])
        if str(item).strip()
    ] or [requested_model]
    available_models = _discover_round2_provider_models(provider_entry)
    lowered_available = {str(item).strip().lower(): str(item).strip() for item in available_models if str(item).strip()}
    for candidate_model in [requested_model, *candidate_models]:
        matched = lowered_available.get(str(candidate_model).strip().lower())
        if matched:
            status = "exact" if matched.lower() == requested_model.lower() else "closest_available"
            return matched, status, available_models
    return requested_model, "exact" if requested_model else "skipped", available_models


def _apply_neural_rerank_to_chunks(
    *,
    query: str,
    chunks: list[dict[str, object]],
    model_name: str,
    top_k: int,
) -> list[dict[str, object]]:
    pairs = [(query, str(chunk.get("text") or chunk.get("snippet") or "")) for chunk in chunks]
    scores = score_query_document_pairs(model_name=model_name, pairs=pairs)
    reranked: list[dict[str, object]] = []
    for chunk, score in zip(chunks, scores):
        reranked.append({**chunk, "neural_score": round(float(score), 4), "score": round(float(score), 4)})
    reranked.sort(
        key=lambda item: (
            float(item.get("neural_score") or 0.0),
            float(item.get("vector_score") or item.get("score") or 0.0),
            float(item.get("lexical_score") or 0.0),
        ),
        reverse=True,
    )
    return reranked[:top_k]


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
        pdf_extraction_mode=str(case.get("pdf_extraction_mode") or base.pdf_extraction_mode),
        pdf_docling_enabled=bool(case.get("pdf_docling_enabled", base.pdf_docling_enabled)),
        pdf_ocr_fallback_enabled=bool(case.get("pdf_ocr_fallback_enabled", base.pdf_ocr_fallback_enabled)),
        pdf_scan_image_ocr_enabled=bool(case.get("pdf_scan_image_ocr_enabled", base.pdf_scan_image_ocr_enabled)),
        pdf_evidence_pipeline_enabled=bool(case.get("pdf_evidence_pipeline_enabled", base.pdf_evidence_pipeline_enabled)),
        store_path=case_dir / ".rag_store.json",
        chroma_path=case_dir / ".chroma_rag",
    )


def _inspect_runtime_artifact(
    provider_entry: dict[str, object],
    *,
    capability: str,
    model: str,
    requested_context_window: int | None,
) -> dict[str, object]:
    provider_instance = provider_entry.get("instance")
    if provider_instance is None:
        return {}
    try:
        if capability == "embeddings" and hasattr(provider_instance, "inspect_embedding_context_window"):
            artifact = provider_instance.inspect_embedding_context_window(
                model,
                requested_context_window=requested_context_window,
            )
            return artifact if isinstance(artifact, dict) else {}
    except Exception as error:
        return {"inspection_error": str(error)}
    return {}


def _classify_runtime_path(
    *,
    provider_requested: str,
    provider_effective: str,
    model_effective: str,
    runtime_artifact: dict[str, object] | None,
) -> dict[str, object]:
    requested = str(provider_requested or "").strip().lower()
    effective = str(provider_effective or provider_requested or "").strip().lower()
    model = str(model_effective or "").strip()
    artifact = runtime_artifact if isinstance(runtime_artifact, dict) else {}
    backend_provider = str(artifact.get("backend_provider") or "").strip().lower() or None
    backend_model_ref = str(artifact.get("backend_model_ref") or "").strip() or None

    if effective == "ollama":
        runtime_path = "direct_runtime"
        runtime_path_label = "Direct runtime"
        backend_equivalence_type = "native_runtime"
        backend_provider_resolved = "ollama"
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = False
        path_comparison_note = "Direct provider path with no hub-wrapper layer."
    elif effective == "huggingface_server":
        runtime_path = "hub_wrapped_runtime"
        runtime_path_label = "Hub-wrapped runtime"
        backend_equivalence_type = "wrapped_backend"
        backend_provider_resolved = backend_provider
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = True
        if backend_provider == "ollama":
            if requested == "huggingface_server":
                path_comparison_note = (
                    "Backend appears equivalent to direct Ollama embeddings, but requests flow through the local hub and may incur extra HTTP/serving overhead."
                )
            else:
                path_comparison_note = "Requests flow through the local hub layer before reaching the effective embedding backend."
        else:
            path_comparison_note = "Requests flow through the local hub layer before reaching the effective embedding backend."
    elif effective in {"openai", "huggingface_inference"}:
        runtime_path = "cloud_managed_runtime"
        runtime_path_label = "Cloud managed runtime"
        backend_equivalence_type = "managed_service"
        backend_provider_resolved = backend_provider or effective
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = False
        path_comparison_note = "Managed remote serving path; not directly comparable to local direct-runtime overhead."
    elif effective == "huggingface_local":
        runtime_path = "local_native_runtime"
        runtime_path_label = "Local native runtime"
        backend_equivalence_type = "native_runtime"
        backend_provider_resolved = backend_provider or effective
        backend_model_ref_resolved = backend_model_ref or model
        path_overhead_expected = False
        path_comparison_note = "Local native runtime path outside Ollama; backend semantics may differ from Ollama-native execution."
    else:
        runtime_path = "unknown_runtime_path"
        runtime_path_label = "Unknown runtime path"
        backend_equivalence_type = "unknown"
        backend_provider_resolved = backend_provider or effective or requested or None
        backend_model_ref_resolved = backend_model_ref or model or None
        path_overhead_expected = False
        path_comparison_note = "Runtime path could not be classified precisely from the available metadata."

    backend_equivalence_key = None
    if backend_provider_resolved and backend_model_ref_resolved:
        backend_equivalence_key = f"{backend_provider_resolved}::{backend_model_ref_resolved}"
    elif effective and model:
        backend_equivalence_key = f"{effective}::{model}"

    equivalent_direct_runtime_key = None
    if runtime_path == "hub_wrapped_runtime" and backend_provider_resolved == "ollama":
        equivalent_direct_runtime_key = f"ollama::{backend_model_ref_resolved or model}"
    elif runtime_path == "direct_runtime" and backend_provider_resolved == "ollama":
        equivalent_direct_runtime_key = f"ollama::{backend_model_ref_resolved or model}"

    return {
        "runtime_path": runtime_path,
        "runtime_path_label": runtime_path_label,
        "backend_equivalence_type": backend_equivalence_type,
        "backend_provider_resolved": backend_provider_resolved,
        "backend_model_ref_resolved": backend_model_ref_resolved,
        "backend_equivalence_key": backend_equivalence_key,
        "equivalent_direct_runtime_key": equivalent_direct_runtime_key,
        "path_overhead_expected": path_overhead_expected,
        "path_comparison_note": path_comparison_note,
    }


def _run_reranker_questions(
    *,
    questions: list[dict[str, object]],
    rag_index: dict[str, object],
    settings: RagSettings,
    embedding_provider: object,
    neural_reranker_model: str | None = None,
    query_timeout_s: int | None = None,
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
        with time_limit(
            query_timeout_s,
            f"reranker query timeout after {query_timeout_s}s",
        ):
            if neural_reranker_model:
                pool_size = max(int(settings.rerank_pool_size or settings.top_k), int(settings.top_k or 1))
                pool_settings = replace(
                    settings,
                    top_k=pool_size,
                    rerank_pool_size=pool_size,
                    rerank_lexical_weight=0.0,
                )
                details = retrieve_relevant_chunks_detailed(
                    query=question,
                    rag_index=rag_index,
                    settings=pool_settings,
                    embedding_provider=embedding_provider,
                )
                pool_chunks = list(details.get("chunks") or [])
                reranked_chunks = _apply_neural_rerank_to_chunks(
                    query=question,
                    chunks=pool_chunks,
                    model_name=neural_reranker_model,
                    top_k=int(settings.top_k or 1),
                )
                details = {
                    **details,
                    "chunks": reranked_chunks,
                    "candidate_pool_size": len(pool_chunks),
                    "reranking_applied": True,
                    "rerank_strategy": {
                        "type": "neural_cross_encoder",
                        "model": neural_reranker_model,
                        "candidate_pool_size": len(pool_chunks),
                    },
                    "retrieval_strategy_used": f"{details.get('retrieval_strategy_used') or settings.retrieval_strategy}+neural_reranker",
                }
            else:
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
    indexing_timeout_s: int | None = None,
    query_timeout_s: int | None = None,
) -> dict[str, object]:
    provider_requested = str(case.get("provider") or case.get("embedding_provider") or "")
    model_requested = str(case.get("requested_model") or case.get("embedding_model") or "")
    candidate_role = str(case.get("candidate_role") or "")
    runtime_profile = resolve_provider_runtime_profile(registry, provider_requested, capability="embeddings", fallback_provider=None)
    effective_provider = str(runtime_profile.get("effective_provider") or provider_requested)
    if provider_requested and effective_provider != provider_requested:
        runtime_profile = {
            **runtime_profile,
            "effective_provider": provider_requested,
            "provider_entry": {},
            "provider_instance": None,
            "fallback_reason": f"requested_provider_unavailable:{provider_requested}",
        }
    provider_entry = runtime_profile.get("provider_entry") if isinstance(runtime_profile.get("provider_entry"), dict) else {}
    provider_instance = provider_entry.get("instance")
    index_provider_requested = str(case.get("embedding_provider") or provider_requested)
    index_runtime_profile = resolve_provider_runtime_profile(registry, index_provider_requested, capability="embeddings", fallback_provider=None)
    index_effective_provider = str(index_runtime_profile.get("effective_provider") or index_provider_requested)
    if index_provider_requested and index_effective_provider != index_provider_requested:
        index_runtime_profile = {
            **index_runtime_profile,
            "effective_provider": index_provider_requested,
            "provider_entry": {},
            "provider_instance": None,
            "fallback_reason": f"requested_provider_unavailable:{index_provider_requested}",
        }
    index_provider_entry = index_runtime_profile.get("provider_entry") if isinstance(index_runtime_profile.get("provider_entry"), dict) else {}
    index_provider_instance = index_provider_entry.get("instance")
    model_effective, model_resolution_status, available_models = _resolve_round2_candidate_model(case, provider_entry)
    runtime_artifact = _inspect_runtime_artifact(
        provider_entry,
        capability="embeddings",
        model=model_effective,
        requested_context_window=int(case.get("embedding_context_window") or 0) or None,
    )
    started_at = time.time()
    event_started_perf = time.perf_counter()
    event: dict[str, object] = {
        "event_type": "case_result",
        "run_id": run_id,
        "case_id": case.get("case_id"),
        "status": "failed",
        "group": "rerankers",
        "started_at": started_at,
        "provider_requested": provider_requested,
        "provider_effective": runtime_profile.get("effective_provider") or provider_requested,
        "embedding_provider_requested": index_provider_requested,
        "embedding_provider_effective": index_runtime_profile.get("effective_provider") or index_provider_requested,
        "embedding_model_requested": case.get("embedding_model"),
        "embedding_model_effective": case.get("embedding_model"),
        "model_requested": model_requested,
        "model_effective": model_effective,
        "requested_runtime_family": case.get("requested_runtime_family"),
        "model_resolution_status": model_resolution_status,
        "model_resolution_source": "provider_inventory" if available_models else "manifest_assumption_without_inventory",
        "requested_model_candidates": case.get("neural_reranker_candidate_models") or [model_requested],
        "candidate_id": case.get("candidate_id"),
        "candidate_label": case.get("candidate_label"),
        "candidate_role": case.get("candidate_role"),
        "dataset_id": case.get("dataset_id"),
        "question_set_id": case.get("question_set_id"),
        "document_count": len(case.get("pdf_paths") or []),
        "embedding_context_window": case.get("embedding_context_window"),
        "embedding_truncate": case.get("embedding_truncate"),
        "chunk_size": case.get("chunk_size"),
        "chunk_overlap": case.get("chunk_overlap"),
        "top_k": case.get("top_k"),
        "repetition": case.get("repetition"),
        "retrieval_strategy": case.get("retrieval_strategy"),
        "rerank_pool_size": case.get("rerank_pool_size"),
        "rerank_lexical_weight": case.get("rerank_lexical_weight"),
        "pdf_extraction_mode": case.get("pdf_extraction_mode"),
        "pdf_docling_enabled": case.get("pdf_docling_enabled"),
        "pdf_ocr_fallback_enabled": case.get("pdf_ocr_fallback_enabled"),
        "pdf_scan_image_ocr_enabled": case.get("pdf_scan_image_ocr_enabled"),
        "pdf_evidence_pipeline_enabled": case.get("pdf_evidence_pipeline_enabled"),
        "support_status": case.get("support_status"),
        "runtime_bucket": infer_model_comparison_runtime_bucket(provider_requested, model_effective),
        "quantization_family": infer_model_comparison_quantization_family(provider_requested, model_effective),
        "runtime_artifact": runtime_artifact,
        "error": None,
    }
    event.update(
        _classify_runtime_path(
            provider_requested=provider_requested,
            provider_effective=str(runtime_profile.get("effective_provider") or provider_requested),
            model_effective=model_effective,
            runtime_artifact=runtime_artifact,
        )
    )
    event.update(
        build_runtime_family_metadata(
            requested_runtime_family=str(case.get("requested_runtime_family") or "") or None,
            provider_effective=str(runtime_profile.get("effective_provider") or provider_requested),
            model_effective=model_effective,
            runtime_artifact=runtime_artifact,
        )
    )
    if index_provider_instance is None:
        event["finished_at"] = time.time()
        event["status"] = "skipped"
        event["error"] = index_runtime_profile.get("fallback_reason") or "embedding_provider_unavailable"
        event.update(
            build_operational_metrics_bundle(
                total_wall_time_s=time.perf_counter() - event_started_perf,
                repetition=int(case.get("repetition") or 1),
            )
        )
        return event

    if case.get("candidate_role") == "challenger_neural" and not supports_local_neural_reranker_runtime():
        event["finished_at"] = time.time()
        event["status"] = "skipped"
        event["error"] = "neural_reranker_runtime_unavailable"
        event.update(
            build_operational_metrics_bundle(
                total_wall_time_s=time.perf_counter() - event_started_perf,
                repetition=int(case.get("repetition") or 1),
            )
        )
        return event

    case_dir = run_output_dir / "cases" / str(case.get("case_id"))
    case_dir.mkdir(parents=True, exist_ok=True)
    settings = _build_reranker_settings(case, case_dir)
    try:
        indexing_started = time.perf_counter()
        with time_limit(
            indexing_timeout_s,
            f"reranker indexing timeout after {indexing_timeout_s}s",
        ):
            documents = [load_document(_LocalUploadedFile(Path(path)), settings) for path in case.get("pdf_paths") or []]
            rag_index, sync_status = upsert_documents_in_rag_index(
                documents=documents,
                settings=settings,
                embedding_provider=index_provider_instance,
                rag_index=None,
            )
        indexing_seconds = time.perf_counter() - indexing_started
        question_rows, aggregate = _run_reranker_questions(
            questions=list(case.get("questions") or []),
            rag_index=rag_index,
            settings=settings,
            embedding_provider=index_provider_instance,
            neural_reranker_model=(model_effective if candidate_role == "challenger_neural" else None),
            query_timeout_s=query_timeout_s,
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
        if candidate_role == "challenger_neural":
            event["status"] = "skipped"
            event["error"] = f"neural_reranker_unavailable:{error}"
        else:
            event["error"] = str(error)
    event.update(
        build_operational_metrics_bundle(
            total_wall_time_s=time.perf_counter() - event_started_perf,
            repetition=int(case.get("repetition") or 1),
        )
    )
    return event


def _extract_evidence_variant(
    file_bytes: bytes,
    filename: str,
    settings: RagSettings,
    variant_spec: dict[str, object],
) -> dict[str, object]:
    enable_vl = bool(variant_spec.get("enable_vl", False))
    enable_docling = bool(variant_spec.get("enable_docling", settings.pdf_docling_enabled))
    ocr_backend = str(variant_spec.get("ocr_backend") or settings.evidence_ocr_backend)
    vl_model = str(variant_spec.get("vl_model") or settings.evidence_vl_model)
    variant_settings = replace(
        settings,
        pdf_docling_enabled=enable_docling,
        evidence_ocr_backend=ocr_backend,
        evidence_vl_model=vl_model,
    )
    if enable_vl:
        _, metadata = _extract_pdf_text_with_evidence_pipeline(file_bytes, filename, variant_settings)
        summary = metadata.get("evidence_summary") if isinstance(metadata.get("evidence_summary"), dict) else {}
        return {
            "variant": str(variant_spec.get("variant") or "evidence_with_vl"),
            "name": summary.get("name_value"),
            "location": summary.get("location_value"),
            "emails": _normalize_email_list(summary.get("emails") or []),
            "phones": _normalize_phone_list(summary.get("phones") or []),
            "name_status": summary.get("name_status"),
            "location_status": summary.get("location_status"),
            "metadata": metadata,
        }

    config = build_evidence_config_from_rag_settings(variant_settings)
    config = config.__class__(
        **{
            **config.__dict__,
            "enable_vl": False,
            "enable_docling": enable_docling,
            "ocr_backend": ocr_backend,
            "vl_model": vl_model,
        }
    )
    result = run_cv_pipeline_from_bytes(file_bytes, ".pdf", config)
    return {
        "variant": str(variant_spec.get("variant") or "evidence_no_vl"),
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
            "enable_docling": enable_docling,
            "enable_vl": False,
            "ocr_backend": ocr_backend,
        },
    }


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


def _extract_pdf_pipeline_contacts(file_bytes: bytes, settings: RagSettings, extraction_mode: str, variant_name: str) -> dict[str, object]:
    pipeline_settings = replace(
        settings,
        pdf_extraction_mode=str(extraction_mode).strip().lower() or settings.pdf_extraction_mode,
        pdf_evidence_pipeline_enabled=False,
    )
    text, metadata = _extract_pdf_text(file_bytes, pipeline_settings)
    emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    phones = re.findall(r"\+?\d[\d\s().-]{7,}\d", text)
    evidence_summary = metadata.get("evidence_summary") if isinstance(metadata.get("evidence_summary"), dict) else {}
    return {
        "variant": variant_name,
        "name": evidence_summary.get("name_value"),
        "location": evidence_summary.get("location_value"),
        "emails": _normalize_email_list(emails),
        "phones": _normalize_phone_list(phones),
        "name_status": evidence_summary.get("name_status") or "not_found",
        "location_status": evidence_summary.get("location_status") or "not_found",
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
    event_started_perf = time.perf_counter()
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
        variant_specs = [item for item in (case.get("variant_matrix") or []) if isinstance(item, dict)] or [
            {"variant": "legacy_pdf", "kind": "legacy_pdf", "requested_runtime_family": "legacy_pdf_text_extraction"},
            {"variant": "evidence_no_vl", "kind": "evidence_pipeline", "enable_vl": False, "requested_runtime_family": "evidence_pipeline_local"},
            {"variant": "evidence_with_vl", "kind": "evidence_pipeline", "enable_vl": True, "requested_runtime_family": "ollama_vl_local"},
        ]
        for variant_spec in variant_specs:
            start = time.perf_counter()
            if str(variant_spec.get("kind") or "") == "legacy_pdf":
                variant = _extract_legacy_contacts(file_bytes, settings)
                runtime_artifact = {
                    "runtime": "legacy_pdf_text_extraction",
                    "backend_provider": "legacy_pdf",
                    "backend_model_ref": "basic_pdf_text_extractor",
                }
                provider_effective = "legacy_pdf"
                model_effective = "basic_pdf_text_extractor"
            elif str(variant_spec.get("kind") or "") == "pdf_pipeline":
                extraction_mode = str(variant_spec.get("pdf_extraction_mode") or "hybrid").strip().lower() or "hybrid"
                variant_name = str(variant_spec.get("variant") or f"pdf_{extraction_mode}")
                variant = _extract_pdf_pipeline_contacts(file_bytes, settings, extraction_mode, variant_name)
                runtime_artifact = {
                    "runtime": str(variant_spec.get("requested_runtime_family") or f"pdf_{extraction_mode}_local"),
                    "backend_provider": "pdf_pipeline",
                    "backend_model_ref": extraction_mode,
                    "pdf_extraction_mode": extraction_mode,
                }
                provider_effective = "pdf_pipeline"
                model_effective = extraction_mode
            else:
                variant = _extract_evidence_variant(file_bytes, pdf_path.name, settings, variant_spec)
                runtime_artifact = {
                    "runtime": str(variant_spec.get("requested_runtime_family") or "evidence_pipeline_local"),
                    "backend_provider": "ollama" if bool(variant_spec.get("enable_vl")) else "evidence_pipeline",
                    "backend_model_ref": str(variant_spec.get("vl_model") or variant_spec.get("ocr_backend") or "evidence_pipeline"),
                    "enable_vl": bool(variant_spec.get("enable_vl", False)),
                    "enable_docling": bool(variant_spec.get("enable_docling", settings.pdf_docling_enabled)),
                    "ocr_backend": str(variant_spec.get("ocr_backend") or settings.evidence_ocr_backend),
                }
                provider_effective = "ollama" if bool(variant_spec.get("enable_vl")) else "huggingface_local"
                model_effective = str(variant_spec.get("vl_model") or variant_spec.get("ocr_backend") or "evidence_pipeline")
            elapsed = time.perf_counter() - start
            runtime_family_metadata = build_runtime_family_metadata(
                requested_runtime_family=str(variant_spec.get("requested_runtime_family") or "") or None,
                provider_effective=provider_effective,
                model_effective=model_effective,
                runtime_artifact=runtime_artifact,
            )
            variants.append(
                {
                    **variant,
                    "latency_s": round(elapsed, 4),
                    "runtime_artifact": runtime_artifact,
                    **runtime_family_metadata,
                    **build_operational_metrics_bundle(total_wall_time_s=elapsed, repetition=int(case.get("repetition") or 1)),
                }
            )

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
    event.update(
        build_operational_metrics_bundle(
            total_wall_time_s=time.perf_counter() - event_started_perf,
            repetition=int(case.get("repetition") or 1),
        )
    )
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
                    "requested_runtime_family": event.get("requested_runtime_family"),
                    "resolved_runtime_family": event.get("resolved_runtime_family"),
                    "runtime_family_resolution_status": event.get("runtime_family_resolution_status"),
                    "document_count": event.get("document_count"),
                    "embedding_context_window": event.get("embedding_context_window"),
                    "embedding_truncate": event.get("embedding_truncate"),
                    "chunk_size": event.get("chunk_size"),
                    "chunk_overlap": event.get("chunk_overlap"),
                    "top_k": event.get("top_k"),
                    "retrieval_strategy": event.get("retrieval_strategy"),
                    "rerank_pool_size": event.get("rerank_pool_size"),
                    "rerank_lexical_weight": event.get("rerank_lexical_weight"),
                    "runtime_bucket": event.get("runtime_bucket"),
                    "quantization_family": event.get("quantization_family"),
                    "runtime_path": event.get("runtime_path"),
                    "runtime_path_label": event.get("runtime_path_label"),
                    "backend_equivalence_type": event.get("backend_equivalence_type"),
                    "backend_provider_resolved": event.get("backend_provider_resolved"),
                    "backend_model_ref_resolved": event.get("backend_model_ref_resolved"),
                    "backend_equivalence_key": event.get("backend_equivalence_key"),
                    "equivalent_direct_runtime_key": event.get("equivalent_direct_runtime_key"),
                    "path_overhead_expected": event.get("path_overhead_expected"),
                    "path_comparison_note": event.get("path_comparison_note"),
                    "indexing_seconds": event.get("indexing_seconds"),
                    "question_count": aggregate.get("question_count", event.get("question_count")),
                    "hit_at_1": aggregate.get("hit_at_1", event.get("hit_at_1")),
                    "hit_at_k": aggregate.get("hit_at_k", event.get("hit_at_k")),
                    "mrr": aggregate.get("mrr", event.get("mrr")),
                    "average_retrieval_seconds": aggregate.get("average_retrieval_seconds", event.get("average_retrieval_seconds")),
                    "median_retrieval_seconds": aggregate.get("median_retrieval_seconds", event.get("median_retrieval_seconds")),
                    "avg_groundedness_proxy": aggregate.get("avg_groundedness_proxy", event.get("avg_groundedness_proxy")),
                    "support_status": event.get("support_status"),
                    "total_wall_time_s": event.get("total_wall_time_s"),
                    "total_wall_time_status": event.get("total_wall_time_status"),
                    "cold_start_wall_time_s": event.get("cold_start_wall_time_s"),
                    "cold_start_status": event.get("cold_start_status"),
                    "warm_start_wall_time_s": event.get("warm_start_wall_time_s"),
                    "warm_start_status": event.get("warm_start_status"),
                    "memory_peak_estimate_mb": event.get("memory_peak_estimate_mb"),
                    "memory_status": event.get("memory_status"),
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
                        "provider_requested": event.get("provider_requested"),
                        "model_requested": event.get("model_requested"),
                        "runtime_family_resolution_status": event.get("runtime_family_resolution_status"),
                        "runtime_path": event.get("runtime_path"),
                        "backend_equivalence_key": event.get("backend_equivalence_key"),
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
                        "requested_runtime_family": variant.get("requested_runtime_family"),
                        "resolved_runtime_family": variant.get("resolved_runtime_family"),
                        "runtime_family_resolution_status": variant.get("runtime_family_resolution_status"),
                        "latency_s": variant.get("latency_s"),
                        "total_wall_time_s": variant.get("total_wall_time_s"),
                        "total_wall_time_status": variant.get("total_wall_time_status"),
                        "cold_start_status": variant.get("cold_start_status"),
                        "warm_start_status": variant.get("warm_start_status"),
                        "memory_status": variant.get("memory_status"),
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
                "runtime_path": candidate_events[0].get("runtime_path"),
                "runtime_path_label": candidate_events[0].get("runtime_path_label"),
                "backend_equivalence_type": candidate_events[0].get("backend_equivalence_type"),
                "backend_provider_resolved": candidate_events[0].get("backend_provider_resolved"),
                "backend_model_ref_resolved": candidate_events[0].get("backend_model_ref_resolved"),
                "backend_equivalence_key": candidate_events[0].get("backend_equivalence_key"),
                "equivalent_direct_runtime_key": candidate_events[0].get("equivalent_direct_runtime_key"),
                "path_overhead_expected": candidate_events[0].get("path_overhead_expected"),
                "case_count": len(candidate_events),
                "support_status": candidate_events[0].get("support_status"),
                "success_rate": round(len(successful) / max(len(candidate_events), 1), 4),
                "requested_runtime_family": candidate_events[0].get("requested_runtime_family"),
                "resolved_runtime_family": candidate_events[0].get("resolved_runtime_family"),
                "avg_hit_at_1": _average([float(item.get("hit_at_1")) for item in successful if isinstance(item.get("hit_at_1"), (int, float))]),
                "avg_hit_at_k": _average([float(item.get("hit_at_k")) for item in successful if isinstance(item.get("hit_at_k"), (int, float))]),
                "avg_mrr": _average([float(item.get("mrr")) for item in successful if isinstance(item.get("mrr"), (int, float))]),
                "avg_retrieval_seconds": _average([float(item.get("average_retrieval_seconds")) for item in successful if isinstance(item.get("average_retrieval_seconds"), (int, float))]),
                "avg_groundedness_proxy": _average([float(item.get("avg_groundedness_proxy")) for item in successful if isinstance(item.get("avg_groundedness_proxy"), (int, float))]),
                "avg_total_wall_time_s": _average([float(item.get("total_wall_time_s")) for item in successful if isinstance(item.get("total_wall_time_s"), (int, float))]),
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
                "requested_runtime_family": variant_rows[0].get("requested_runtime_family"),
                "resolved_runtime_family": variant_rows[0].get("resolved_runtime_family"),
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
            "| Rank | Candidate | Provider | Model | Runtime path | Runtime family | Role | Avg MRR | Avg Hit@1 | Avg retrieval (s) | Avg groundedness proxy |",
            "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for index, item in enumerate(rerankers.get("candidate_ranking") or [], start=1):
        lines.append(
            f"| {index} | `{item.get('candidate_id')}` | `{item.get('provider')}` | `{item.get('model')}` | `{item.get('runtime_path') or '-'}` | `{item.get('resolved_runtime_family') or '-'}` | `{item.get('candidate_role')}` | {float(item.get('avg_mrr') or 0.0):.4f} | {float(item.get('avg_hit_at_1') or 0.0):.4f} | {float(item.get('avg_retrieval_seconds') or 0.0):.4f} | {float(item.get('avg_groundedness_proxy') or 0.0):.4f} |"
        )
    lines.extend(
        [
            "",
            "## OCR / VLM leaderboard",
            "",
            "| Rank | Variant | Runtime family | Avg F1 | Avg latency (s) | Helped cases |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for index, item in enumerate(ocr_vlm.get("variant_ranking") or [], start=1):
        lines.append(
            f"| {index} | `{item.get('variant')}` | `{item.get('resolved_runtime_family') or '-'}` | {float(item.get('avg_f1') or 0.0):.4f} | {float(item.get('avg_latency_s') or 0.0):.4f} | {int(item.get('helped_cases') or 0)} |"
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
