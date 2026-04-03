from __future__ import annotations


HIGH_SENSITIVITY_TASKS = {
    "document_agent",
    "summary",
    "extraction",
    "cv_analysis",
    "document_comparison",
    "document_risk_review",
    "policy_compliance_review",
    "structured_extraction",
    "executive_summary",
}

MEDIUM_SENSITIVITY_TASKS = {
    "chat_rag",
    "checklist",
    "code_analysis",
    "technical_assistance",
    "operational_checklist",
}

REMOTE_COST_PROVIDERS = {"openai", "huggingface_inference"}


def classify_budget_sensitivity(task_type: str) -> str:
    normalized = str(task_type or "").strip().lower()
    if normalized in HIGH_SENSITIVITY_TASKS:
        return "high"
    if normalized in MEDIUM_SENSITIVITY_TASKS:
        return "medium"
    return "low"


def build_budget_routing_decision(
    *,
    task_type: str,
    provider: str,
    has_document_context: bool,
    document_count: int,
    requested_top_k: int,
    requested_rerank_pool_size: int,
    context_budget_chars: int,
    estimated_context_chars: int,
    prompt_chars: int,
    allow_auto_degrade: bool,
) -> dict[str, object]:
    sensitivity = classify_budget_sensitivity(task_type)
    normalized_provider = str(provider or "").strip().lower()
    requested_top_k = max(int(requested_top_k or 0), 1)
    requested_rerank_pool_size = max(int(requested_rerank_pool_size or 0), requested_top_k)
    context_budget_chars = max(int(context_budget_chars or 0), 1)
    estimated_context_chars = max(int(estimated_context_chars or 0), 0)
    prompt_chars = max(int(prompt_chars or 0), 0)

    pressure_ratio = round(estimated_context_chars / max(context_budget_chars, 1), 3)
    remote_cost_pressure = normalized_provider in REMOTE_COST_PROVIDERS

    quality_floor = {
        "high": "strict",
        "medium": "guarded",
        "low": "flexible",
    }.get(sensitivity, "guarded")

    decision: dict[str, object] = {
        "task_type": str(task_type or "unknown"),
        "provider": normalized_provider,
        "sensitivity": sensitivity,
        "quality_floor": quality_floor,
        "routing_mode": "quality_first" if sensitivity == "high" else "balanced",
        "reason": "high_sensitivity_task" if sensitivity == "high" else "balanced_default",
        "context_budget_chars": context_budget_chars,
        "estimated_context_chars": estimated_context_chars,
        "context_pressure_ratio": pressure_ratio,
        "prompt_chars": prompt_chars,
        "has_document_context": bool(has_document_context),
        "document_count": int(document_count or 0),
        "requested_top_k": requested_top_k,
        "requested_rerank_pool_size": requested_rerank_pool_size,
        "top_k_effective": requested_top_k,
        "rerank_pool_size_effective": requested_rerank_pool_size,
        "remote_cost_pressure": remote_cost_pressure,
        "auto_degrade_allowed": bool(allow_auto_degrade),
        "auto_degrade_applied": False,
    }

    if sensitivity == "high" or not allow_auto_degrade:
        if not allow_auto_degrade and sensitivity != "high":
            decision["reason"] = "alerts_only_mode"
        return decision

    if not has_document_context:
        decision["routing_mode"] = "balanced"
        decision["reason"] = "no_document_context"
        return decision

    if pressure_ratio >= 1.0 or (remote_cost_pressure and pressure_ratio >= 0.75):
        rerank_pool_size_effective = max(requested_top_k, min(requested_rerank_pool_size, requested_top_k + 2))
        top_k_effective = requested_top_k

        if sensitivity == "low" and requested_top_k > 3:
            top_k_effective = requested_top_k - 1
            rerank_pool_size_effective = max(top_k_effective, min(rerank_pool_size_effective, top_k_effective + 2))

        decision.update(
            {
                "routing_mode": "budget_guarded",
                "reason": "remote_cost_pressure" if remote_cost_pressure and pressure_ratio >= 0.75 else "high_context_pressure",
                "top_k_effective": int(top_k_effective),
                "rerank_pool_size_effective": int(rerank_pool_size_effective),
                "auto_degrade_applied": (
                    int(top_k_effective) != int(requested_top_k)
                    or int(rerank_pool_size_effective) != int(requested_rerank_pool_size)
                ),
            }
        )

    return decision