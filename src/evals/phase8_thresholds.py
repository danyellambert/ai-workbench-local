from __future__ import annotations

from copy import deepcopy
from typing import Any


STRUCTURED_SMOKE_THRESHOLDS: dict[str, Any] = {
    "max_score": 5,
    "pass_min_score": 5,
    "warn_min_score": 3,
    "notes": "Smoke eval é estrutural e conservador: PASS exige payload validado + sinais mínimos fortes por task.",
}


REAL_DOCUMENT_EVAL_THRESHOLDS: dict[str, dict[str, Any]] = {
    "code_analysis": {
        "pass_ratio": 0.72,
        "warn_ratio": 0.48,
        "notes": "Code analysis privilegia cobertura semântica de issues, refactor plan e test suggestions grounded.",
    },
    "cv_analysis": {
        "pass_ratio": 0.62,
        "warn_ratio": 0.42,
        "notes": "CV analysis tolera pequenas variações de wording, mas exige boa cobertura de identidade, educação e experiência.",
    },
    "extraction": {
        "pass_ratio": 0.62,
        "warn_ratio": 0.40,
        "notes": "Extraction real-document privilegia fields, entities, obligations, risks e clause coverage grounded.",
    },
    "summary": {
        "pass_ratio": 0.58,
        "warn_ratio": 0.40,
        "notes": "Summary real-document privilegia cobertura factual e sinais executivos, não matching textual exato.",
    },
}


CHECKLIST_REGRESSION_THRESHOLDS: dict[str, Any] = {
    "pass_min_coverage": 0.90,
    "warn_min_coverage": 0.75,
    "pass_min_grounded_item_rate": 0.85,
    "warn_min_grounded_item_rate": 0.65,
    "pass_min_citation_precision_proxy": 0.75,
    "warn_min_citation_precision_proxy": 0.55,
    "fail_on_duplicate_ids": True,
    "fail_on_artifact_items": True,
    "fail_on_collapsed_items": True,
    "warn_on_order_breaks": True,
    "warn_on_unexpected_items": True,
    "notes": "Checklist regression prioriza atomicidade, grounding e aderência à sequência esperada do documento-fonte.",
}


EVIDENCE_CV_GOLD_THRESHOLDS: dict[str, Any] = {
    "pass_min_avg_f1": 0.90,
    "warn_min_avg_f1": 0.65,
    "email_f1_target": 0.90,
    "phone_f1_target": 0.90,
    "name_f1_target": 1.00,
    "location_f1_target": 1.00,
    "notes": "Evidence CV gold eval mantém targets altos para contatos e campos de identidade, mas ainda aceita WARN para iteração antes de adaptação.",
}


AGENT_ROUTING_THRESHOLDS: dict[str, Any] = {
    "pass_min_ratio": 1.0,
    "warn_min_ratio": 0.75,
    "notes": "Routing determinístico deve acertar todos os checks no caso ideal; WARN cobre um único desvio em casos limítrofes.",
}


AGENT_WORKFLOW_THRESHOLDS: dict[str, Any] = {
    "pass_min_ratio": 1.0,
    "warn_min_ratio": 0.75,
    "notes": "Workflow determinístico de guardrails deve acertar decisão, transição e expectativa de retry/review.",
}


DIAGNOSIS_THRESHOLDS: dict[str, Any] = {
    "healthy_pass_rate": 0.75,
    "healthy_fail_rate": 0.15,
    "healthy_avg_score_ratio": 0.80,
    "monitor_pass_rate": 0.60,
    "monitor_fail_rate": 0.30,
    "monitor_avg_score_ratio": 0.70,
    "persistent_failure_min_runs": 3,
    "persistent_failure_fail_rate": 0.30,
    "persistent_failure_recent_fail_rate": 0.40,
    "adaptation_high_min_runs": 5,
    "adaptation_high_fail_rate": 0.60,
    "adaptation_high_avg_score_ratio": 0.65,
    "adaptation_medium_min_runs": 5,
    "adaptation_medium_fail_rate": 0.30,
    "adaptation_medium_avg_score_ratio": 0.72,
    "notes": "Diagnosis thresholds separam tasks saudáveis, tarefas em iteração e candidatas à Fase 8.5.",
}


PHASE8_5_DECISION_THRESHOLDS: dict[str, Any] = {
    "runtime_win_min_use_case_fit_delta": 0.03,
    "runtime_win_min_format_delta": 0.05,
    "runtime_win_latency_improvement_ratio": 0.15,
    "runtime_win_max_latency_regression_ratio": 1.35,
    "embedding_win_min_mrr_delta": 0.05,
    "embedding_win_min_hit_at_1_delta": 0.10,
    "embedding_win_max_latency_regression_ratio": 1.50,
    "reranker_win_min_mrr_delta": 0.05,
    "reranker_win_min_groundedness_delta": 0.05,
    "reranker_win_max_latency_regression_ratio": 1.75,
    "notes": "Decision-gate thresholds priorizam ganhos claros e conservadores antes de justificar adaptação leve.",
}


def get_real_document_eval_thresholds(task_type: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base = deepcopy(REAL_DOCUMENT_EVAL_THRESHOLDS.get(task_type, {"pass_ratio": 0.75, "warn_ratio": 0.5}))
    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if value is None:
                continue
            base[key] = value
    return base


def build_phase8_threshold_catalog() -> dict[str, Any]:
    return {
        "structured_smoke_eval": deepcopy(STRUCTURED_SMOKE_THRESHOLDS),
        "structured_real_document_eval": deepcopy(REAL_DOCUMENT_EVAL_THRESHOLDS),
        "checklist_regression": deepcopy(CHECKLIST_REGRESSION_THRESHOLDS),
        "evidence_cv_gold_eval": deepcopy(EVIDENCE_CV_GOLD_THRESHOLDS),
        "document_agent_routing_eval": deepcopy(AGENT_ROUTING_THRESHOLDS),
        "langgraph_workflow_eval": deepcopy(AGENT_WORKFLOW_THRESHOLDS),
        "diagnosis": deepcopy(DIAGNOSIS_THRESHOLDS),
        "phase8_5_decision_gate": deepcopy(PHASE8_5_DECISION_THRESHOLDS),
    }