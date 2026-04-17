from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import BASE_DIR


PHASE8_5_DECISION_SUMMARY_PATH = BASE_DIR / "phase5_eval" / "reports" / "phase8_5_decision_summary.json"

PRODUCT_WORKFLOW_PREFERENCE_IDS = {
    "document_review": "document-review",
    "policy_contract_comparison": "comparison",
    "action_plan_evidence_review": "action-plan",
    "candidate_review": "candidate-review",
}

WORKFLOW_TO_USE_CASE = {
    "document-review": "release_candidate_risk_review",
    "comparison": "release_candidate_risk_review",
    "action-plan": "ops_update_summary",
    "candidate-review": "cv_structured_extraction",
    "chat-experiments": "code_quality_review",
    "workflow-inspector": "cv_structured_extraction",
}


def load_phase8_5_decision_summary(path: Path | None = None) -> dict[str, Any] | None:
    resolved_path = path or PHASE8_5_DECISION_SUMMARY_PATH
    if not resolved_path.exists():
        return None
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _split_candidate(value: str | None) -> tuple[str | None, str | None, str | None]:
    candidate = str(value or "").strip()
    if not candidate:
        return None, None, None
    parts = candidate.split("::")
    provider = parts[0].strip() if len(parts) >= 1 else None
    model = parts[1].strip() if len(parts) >= 2 else None
    variant = parts[2].strip() if len(parts) >= 3 else None
    return provider or None, model or None, variant or None


def build_benchmark_recommendations(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = summary or load_phase8_5_decision_summary()
    if not isinstance(payload, dict):
        return {
            "preferred_model_by_connection": {},
            "workflow_winners": {},
            "embedding_winner": None,
            "reranker_winner": None,
            "ocr_vlm_recommendations": {},
        }

    preferred_model_by_connection: dict[str, str] = {}
    workflow_winners: dict[str, dict[str, str]] = {}

    runtime_decisions = payload.get("runtime_model_decisions") if isinstance(payload.get("runtime_model_decisions"), dict) else {}
    for item in runtime_decisions.get("best_local_runtime_by_use_case") or []:
        if not isinstance(item, dict):
            continue
        use_case_id = str(item.get("use_case_id") or "").strip()
        winner_candidate = str(item.get("winner_candidate") or "").strip()
        provider, model, _ = _split_candidate(winner_candidate)
        if not provider or not model:
            continue
        preferred_model_by_connection.setdefault(provider, model)
        workflow_winners[use_case_id] = {
            "provider": provider,
            "model": model,
            "reason": str(item.get("reason") or "").strip(),
        }

    embedding_decisions = payload.get("embedding_decisions") if isinstance(payload.get("embedding_decisions"), dict) else {}
    embedding_provider, embedding_model, embedding_variant = _split_candidate(str(embedding_decisions.get("winner_candidate") or ""))
    embedding_winner = (
        {
            "provider": embedding_provider,
            "model": embedding_model,
            "variant": embedding_variant,
            "reason": str(embedding_decisions.get("reason") or "").strip(),
        }
        if embedding_provider and embedding_model
        else None
    )

    reranker_decisions = payload.get("reranker_decisions") if isinstance(payload.get("reranker_decisions"), dict) else {}
    reranker_winner = None
    if str(reranker_decisions.get("winner_candidate") or "").strip():
        reranker_winner = {
            "candidate": str(reranker_decisions.get("winner_candidate") or "").strip(),
            "reason": str(reranker_decisions.get("reason") or "").strip(),
        }

    ocr_vlm_recommendations = {
        "ocr": {"candidate": "evidence_no_vl", "reason": "best OCR tradeoff"},
        "vlm": {"candidate": "evidence_with_vl", "reason": "best VLM tradeoff when escalation is justified"},
    }

    return {
        "preferred_model_by_connection": preferred_model_by_connection,
        "workflow_winners": workflow_winners,
        "embedding_winner": embedding_winner,
        "reranker_winner": reranker_winner,
        "ocr_vlm_recommendations": ocr_vlm_recommendations,
    }