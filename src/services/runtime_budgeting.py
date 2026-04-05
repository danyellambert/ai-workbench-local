from __future__ import annotations

from pathlib import Path


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
LOCAL_FALLBACK_PROVIDERS = ["ollama", "huggingface_server", "huggingface_local"]

DEFAULT_BUDGET_THRESHOLDS_BY_SENSITIVITY = {
    "high": {
        "warn_total_tokens": 12000,
        "warn_latency_s": 18.0,
        "warn_cost_usd": 0.03,
        "warn_context_pressure_ratio": 0.92,
    },
    "medium": {
        "warn_total_tokens": 7000,
        "warn_latency_s": 12.0,
        "warn_cost_usd": 0.012,
        "warn_context_pressure_ratio": 0.85,
    },
    "low": {
        "warn_total_tokens": 4000,
        "warn_latency_s": 8.0,
        "warn_cost_usd": 0.006,
        "warn_context_pressure_ratio": 0.75,
    },
}

TASK_BUDGET_THRESHOLD_OVERRIDES = {
    "chat_rag": {"warn_total_tokens": 8000, "warn_latency_s": 10.0},
    "checklist": {"warn_total_tokens": 6000, "warn_latency_s": 10.0},
    "code_analysis": {"warn_total_tokens": 5500, "warn_latency_s": 9.0},
    "summary": {"warn_total_tokens": 14000, "warn_latency_s": 22.0},
    "extraction": {"warn_total_tokens": 10000, "warn_latency_s": 16.0},
    "cv_analysis": {"warn_total_tokens": 10000, "warn_latency_s": 16.0},
    "document_agent": {"warn_total_tokens": 14000, "warn_latency_s": 22.0},
}


def classify_budget_sensitivity(task_type: str) -> str:
    normalized = str(task_type or "").strip().lower()
    if normalized in HIGH_SENSITIVITY_TASKS:
        return "high"
    if normalized in MEDIUM_SENSITIVITY_TASKS:
        return "medium"
    return "low"


def get_budget_thresholds(task_type: str, provider: str | None = None) -> dict[str, object]:
    normalized_task = str(task_type or "").strip().lower()
    normalized_provider = str(provider or "").strip().lower()
    sensitivity = classify_budget_sensitivity(normalized_task)
    thresholds = dict(DEFAULT_BUDGET_THRESHOLDS_BY_SENSITIVITY.get(sensitivity, DEFAULT_BUDGET_THRESHOLDS_BY_SENSITIVITY["medium"]))
    thresholds.update(TASK_BUDGET_THRESHOLD_OVERRIDES.get(normalized_task, {}))
    if normalized_provider in REMOTE_COST_PROVIDERS:
        thresholds["warn_cost_usd"] = round(float(thresholds.get("warn_cost_usd") or 0.0) * 0.8, 6)
    return {
        "task_type": normalized_task or "unknown",
        "provider": normalized_provider,
        "sensitivity": sensitivity,
        **thresholds,
    }


def evaluate_budget_alerts(
    *,
    task_type: str,
    provider: str,
    total_tokens: int | None = None,
    cost_usd: float | None = None,
    latency_s: float | None = None,
    context_pressure_ratio: float | None = None,
    auto_degrade_applied: bool = False,
) -> dict[str, object]:
    thresholds = get_budget_thresholds(task_type, provider)
    alerts: list[dict[str, object]] = []

    warn_total_tokens = int(thresholds.get("warn_total_tokens") or 0)
    warn_latency_s = float(thresholds.get("warn_latency_s") or 0.0)
    warn_cost_usd = float(thresholds.get("warn_cost_usd") or 0.0)
    warn_context_pressure_ratio = float(thresholds.get("warn_context_pressure_ratio") or 0.0)
    sensitivity = str(thresholds.get("sensitivity") or "medium")

    if isinstance(total_tokens, int) and warn_total_tokens > 0 and total_tokens >= warn_total_tokens:
        alerts.append(
            {
                "type": "tokens_threshold_exceeded",
                "severity": "warn",
                "value": total_tokens,
                "threshold": warn_total_tokens,
            }
        )
    if isinstance(latency_s, (int, float)) and warn_latency_s > 0 and float(latency_s) >= warn_latency_s:
        alerts.append(
            {
                "type": "latency_threshold_exceeded",
                "severity": "warn",
                "value": round(float(latency_s), 4),
                "threshold": warn_latency_s,
            }
        )
    if isinstance(cost_usd, (int, float)) and warn_cost_usd > 0 and float(cost_usd) >= warn_cost_usd:
        alerts.append(
            {
                "type": "cost_threshold_exceeded",
                "severity": "warn",
                "value": round(float(cost_usd), 6),
                "threshold": warn_cost_usd,
            }
        )
    if isinstance(context_pressure_ratio, (int, float)) and warn_context_pressure_ratio > 0 and float(context_pressure_ratio) >= warn_context_pressure_ratio:
        alerts.append(
            {
                "type": "context_pressure_threshold_exceeded",
                "severity": "warn",
                "value": round(float(context_pressure_ratio), 3),
                "threshold": warn_context_pressure_ratio,
            }
        )
    if auto_degrade_applied and sensitivity in {"high", "medium"}:
        alerts.append(
            {
                "type": "auto_degrade_applied",
                "severity": "warn",
                "value": True,
                "threshold": False,
            }
        )

    return {
        "status": "warn" if alerts else "ok",
        "alerts": alerts,
        "thresholds": thresholds,
    }


def assess_budget_quality_gate(
    *,
    task_type: str,
    eval_db_path: str | Path | None,
    recent_limit: int = 50,
) -> dict[str, object]:
    normalized_task = str(task_type or "").strip().lower()
    if not eval_db_path:
        return {
            "task_type": normalized_task or "unknown",
            "status": "unavailable",
            "reason": "no_eval_db_path",
            "recent_runs": 0,
            "pass_rate": None,
            "min_pass_rate": None,
        }

    try:
        from ..storage.phase8_eval_store import load_eval_runs
    except Exception:
        return {
            "task_type": normalized_task or "unknown",
            "status": "unavailable",
            "reason": "eval_store_unavailable",
            "recent_runs": 0,
            "pass_rate": None,
            "min_pass_rate": None,
        }

    entries = load_eval_runs(Path(eval_db_path), task_type=normalized_task, limit=recent_limit)
    if not entries:
        return {
            "task_type": normalized_task or "unknown",
            "status": "insufficient_data",
            "reason": "no_recent_eval_runs_for_task",
            "recent_runs": 0,
            "pass_rate": None,
            "min_pass_rate": None,
        }

    statuses = [str(item.get("status") or "").strip().upper() for item in entries]
    counted_statuses = [status for status in statuses if status]
    pass_count = sum(1 for status in counted_statuses if status == "PASS")
    pass_rate = round(pass_count / max(len(counted_statuses), 1), 3)
    sensitivity = classify_budget_sensitivity(normalized_task)
    min_pass_rate = {
        "high": 0.85,
        "medium": 0.75,
        "low": 0.65,
    }.get(sensitivity, 0.75)
    return {
        "task_type": normalized_task or "unknown",
        "status": "pass" if pass_rate >= min_pass_rate else "warn",
        "reason": "pass_rate_meets_quality_floor" if pass_rate >= min_pass_rate else "pass_rate_below_quality_floor",
        "recent_runs": len(counted_statuses),
        "pass_rate": pass_rate,
        "min_pass_rate": min_pass_rate,
    }


def resolve_budget_provider_routing(
    *,
    selected_provider: str,
    task_type: str,
    available_chat_providers: list[str],
    routing_decision: dict[str, object] | None = None,
    quality_gate: dict[str, object] | None = None,
    auto_switch_enabled: bool = True,
) -> dict[str, object]:
    normalized_provider = str(selected_provider or "").strip().lower()
    available = [str(provider).strip().lower() for provider in available_chat_providers if str(provider).strip()]
    decision = routing_decision if isinstance(routing_decision, dict) else {}
    quality = quality_gate if isinstance(quality_gate, dict) else {}
    sensitivity = str(decision.get("sensitivity") or classify_budget_sensitivity(task_type)).strip().lower()
    pressure_ratio = float(decision.get("context_pressure_ratio") or 0.0)

    fallback_provider = next((provider for provider in LOCAL_FALLBACK_PROVIDERS if provider in available), normalized_provider)
    result = {
        "requested_provider": normalized_provider,
        "effective_provider": normalized_provider,
        "provider_switch_applied": False,
        "reason": "selected_provider_preserved",
    }

    if not auto_switch_enabled:
        result["reason"] = "budget_provider_switch_disabled"
        return result
    if normalized_provider not in REMOTE_COST_PROVIDERS:
        result["reason"] = "provider_already_local_or_not_remote_costed"
        return result
    if fallback_provider == normalized_provider:
        result["reason"] = "no_local_fallback_provider_available"
        return result
    if sensitivity == "high":
        result["reason"] = "high_sensitivity_preserves_selected_provider"
        return result

    quality_status = str(quality.get("status") or "unavailable").strip().lower()
    if sensitivity == "medium" and quality_status != "pass":
        if normalized_task := str(task_type or "").strip().lower():
            if normalized_task == "chat_rag" and quality_status in {"insufficient_data", "unavailable"}:
                pass
            else:
                result["reason"] = f"quality_gate_not_met:{quality_status or 'unknown'}"
                return result
        else:
            result["reason"] = f"quality_gate_not_met:{quality_status or 'unknown'}"
            return result

    if pressure_ratio >= 0.75 or str(decision.get("reason") or "") == "remote_cost_pressure":
        result.update(
            {
                "effective_provider": fallback_provider,
                "provider_switch_applied": True,
                "reason": "remote_to_local_budget_policy",
            }
        )
        return result

    result["reason"] = "remote_provider_within_budget_thresholds"
    return result


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