from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from src.structured.base import AgentSource, DocumentAgentPayload
from src.structured.document_agent import classify_document_agent_intent, select_document_agent_tool
from src.structured.envelope import StructuredResult, TaskExecutionRequest
import src.structured.langgraph_workflow as workflow


def load_phase8_agent_workflow_cases(path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid Phase 8 agent/workflow fixture: {path}")
    return {
        "routing_cases": [item for item in payload.get("routing_cases", []) if isinstance(item, dict)],
        "workflow_cases": [item for item in payload.get("workflow_cases", []) if isinstance(item, dict)],
    }


def _make_document_ids(count: int) -> list[str]:
    return [f"doc-{index + 1}" for index in range(max(0, int(count)))]


def _build_request(*, task_type: str, input_text: str, document_count: int, context_strategy: str) -> TaskExecutionRequest:
    return TaskExecutionRequest(
        task_type=task_type,
        input_text=input_text,
        use_document_context=document_count > 0,
        source_document_ids=_make_document_ids(document_count),
        context_strategy=context_strategy,
        provider="eval",
        model="heuristic",
    )


def _build_structured_result(case_result: dict[str, Any], *, task_type: str) -> StructuredResult:
    parse_recovery_used = bool(case_result.get("parse_recovery_used"))
    return StructuredResult(
        success=bool(case_result.get("success", True)),
        task_type=task_type,
        parsed_json={},
        execution_metadata={
            "telemetry": {
                "parse_recovery": {
                    "used": parse_recovery_used,
                    "final_success": bool(case_result.get("success", True)),
                    "attempt_count": 2 if parse_recovery_used else 1,
                }
            }
        },
        quality_score=float(case_result.get("quality_score")) if isinstance(case_result.get("quality_score"), (int, float)) else None,
    )


def _build_document_agent_result(case_result: dict[str, Any]) -> StructuredResult:
    sources_count = max(0, int(case_result.get("sources_count") or 0))
    confidence = float(case_result.get("confidence") or 0.0)
    needs_review = bool(case_result.get("needs_review"))
    needs_review_reason = str(case_result.get("needs_review_reason") or "").strip() or None
    payload = DocumentAgentPayload(
        user_intent="document_question",
        answer_mode="friendly",
        tool_used="consult_documents",
        summary="Synthetic evaluation payload.",
        confidence=confidence,
        needs_review=needs_review,
        needs_review_reason=needs_review_reason,
        sources=[
            AgentSource(source=f"doc-{index + 1}.pdf", document_id=f"doc-{index + 1}", file_type="pdf", chunk_id=index + 1, snippet="grounded snippet")
            for index in range(sources_count)
        ],
    )
    return StructuredResult(
        success=bool(case_result.get("success", True)),
        task_type="document_agent",
        parsed_json={},
        validated_output=payload,
        execution_metadata={
            "agent_source_count": sources_count,
            **({"needs_review": needs_review} if needs_review else {}),
            **({"needs_review_reason": needs_review_reason} if needs_review_reason else {}),
        },
        quality_score=confidence,
        overall_confidence=confidence,
    )


def evaluate_routing_case(case: dict[str, Any]) -> dict[str, Any]:
    input_text = str(case.get("input_text") or "")
    document_count = int(case.get("document_count") or 0)
    request = _build_request(
        task_type="document_agent",
        input_text=input_text,
        document_count=document_count,
        context_strategy="document_scan",
    )

    started_at = time.perf_counter()
    actual_intent, actual_intent_reason = classify_document_agent_intent(input_text, document_count=document_count)
    actual_tool, actual_answer_mode, actual_tool_reason = select_document_agent_tool(actual_intent, document_count=document_count)
    actual_context_strategy, actual_context_reason = workflow._resolve_document_agent_context_strategy(actual_tool, request)
    latency_s = round(time.perf_counter() - started_at, 6)

    checks = {
        "intent_correct": actual_intent == str(case.get("expected_intent") or ""),
        "tool_correct": actual_tool == str(case.get("expected_tool") or ""),
        "answer_mode_correct": actual_answer_mode == str(case.get("expected_answer_mode") or ""),
        "context_strategy_correct": actual_context_strategy == str(case.get("expected_context_strategy") or ""),
    }
    score = sum(1 for value in checks.values() if value)
    max_score = len(checks)
    status = "PASS" if score == max_score else "WARN" if score >= max_score - 1 else "FAIL"
    reasons = [name for name, ok in checks.items() if not ok]

    return {
        "suite_name": "document_agent_routing_eval",
        "task_type": "document_agent_routing",
        "case_name": str(case.get("case_id") or "routing_case"),
        "status": status,
        "score": score,
        "max_score": max_score,
        "latency_s": latency_s,
        "metrics": {
            **checks,
            "intent_accuracy": 1.0 if checks["intent_correct"] else 0.0,
            "tool_accuracy": 1.0 if checks["tool_correct"] else 0.0,
            "answer_mode_accuracy": 1.0 if checks["answer_mode_correct"] else 0.0,
            "context_strategy_accuracy": 1.0 if checks["context_strategy_correct"] else 0.0,
        },
        "reasons": reasons,
        "metadata": {
            "input_text": input_text,
            "document_count": document_count,
            "expected_intent": case.get("expected_intent"),
            "actual_intent": actual_intent,
            "actual_intent_reason": actual_intent_reason,
            "expected_tool": case.get("expected_tool"),
            "actual_tool": actual_tool,
            "actual_tool_reason": actual_tool_reason,
            "expected_answer_mode": case.get("expected_answer_mode"),
            "actual_answer_mode": actual_answer_mode,
            "expected_context_strategy": case.get("expected_context_strategy"),
            "actual_context_strategy": actual_context_strategy,
            "actual_context_reason": actual_context_reason,
        },
    }


def evaluate_workflow_case(case: dict[str, Any]) -> dict[str, Any]:
    workflow_type = str(case.get("workflow_type") or "structured")
    task_type = str(case.get("task_type") or ("document_agent" if workflow_type == "document_agent" else "summary"))
    input_text = str(case.get("input_text") or "synthetic eval")
    document_count = int(case.get("document_count") or 0)
    context_strategy = str(case.get("context_strategy") or "document_scan")
    request = _build_request(
        task_type=task_type,
        input_text=input_text,
        document_count=document_count,
        context_strategy=context_strategy,
    )

    if workflow_type == "document_agent":
        result = _build_document_agent_result(case.get("result") or {})
        state = {
            "result": result,
            "effective_request": request,
            "attempt": int(case.get("attempt") or 1),
            "max_attempts": int(case.get("max_attempts") or 2),
            "workflow_trace": [],
        }
        started_at = time.perf_counter()
        updated = workflow._evaluate_document_agent_guardrails(state)
        latency_s = round(time.perf_counter() - started_at, 6)
    else:
        result = _build_structured_result(case.get("result") or {}, task_type=task_type)
        state = {
            "result": result,
            "effective_request": request,
            "attempt": int(case.get("attempt") or 1),
            "max_attempts": int(case.get("max_attempts") or 2),
            "workflow_trace": [],
        }
        started_at = time.perf_counter()
        updated = workflow._evaluate_guardrails(state)
        latency_s = round(time.perf_counter() - started_at, 6)

    actual_decision = str(updated.get("guardrail_decision") or "")
    actual_transition = workflow._guardrail_transition(updated)
    actual_retry = actual_transition == "retry_with_retrieval"
    actual_needs_review = bool(updated.get("needs_review")) or actual_transition == "mark_needs_review"
    expected_retry = bool(case.get("retry_expected"))
    expected_needs_review = bool(case.get("needs_review_expected"))

    checks = {
        "guardrail_decision_correct": actual_decision == str(case.get("expected_guardrail_decision") or ""),
        "transition_correct": actual_transition == str(case.get("expected_transition") or ""),
        "retry_expectation_correct": actual_retry == expected_retry,
        "needs_review_expectation_correct": actual_needs_review == expected_needs_review,
    }
    score = sum(1 for value in checks.values() if value)
    max_score = len(checks)
    status = "PASS" if score == max_score else "WARN" if score >= max_score - 1 else "FAIL"
    reasons = [name for name, ok in checks.items() if not ok]

    return {
        "suite_name": "langgraph_workflow_eval",
        "task_type": "langgraph_guardrails",
        "case_name": str(case.get("case_id") or "workflow_case"),
        "status": status,
        "score": score,
        "max_score": max_score,
        "latency_s": latency_s,
        "needs_review": actual_needs_review,
        "metrics": {
            **checks,
            "retry_expected": expected_retry,
            "retry_actual": actual_retry,
            "useful_retry": 1.0 if expected_retry and actual_retry else 0.0,
            "unnecessary_retry": 1.0 if (not expected_retry and actual_retry) else 0.0,
        },
        "reasons": reasons,
        "metadata": {
            "workflow_type": workflow_type,
            "task_type_under_test": task_type,
            "expected_guardrail_decision": case.get("expected_guardrail_decision"),
            "actual_guardrail_decision": actual_decision,
            "expected_transition": case.get("expected_transition"),
            "actual_transition": actual_transition,
            "expected_retry": expected_retry,
            "actual_retry": actual_retry,
            "expected_needs_review": expected_needs_review,
            "actual_needs_review": actual_needs_review,
        },
    }


def summarize_phase8_case_results(results: list[dict[str, Any]], *, suite_name: str) -> dict[str, Any]:
    if not results:
        return {
            "suite_name": suite_name,
            "total_cases": 0,
            "pass_rate": 0.0,
            "warn_rate": 0.0,
            "fail_rate": 0.0,
            "avg_score_ratio": 0.0,
            "avg_latency_s": 0.0,
            "reasons": [],
        }

    status_counts: dict[str, int] = {"PASS": 0, "WARN": 0, "FAIL": 0}
    score_ratios: list[float] = []
    latencies: list[float] = []
    reason_counter: dict[str, int] = {}
    for item in results:
        status = str(item.get("status") or "FAIL").upper()
        status_counts[status] = status_counts.get(status, 0) + 1
        score = item.get("score")
        max_score = item.get("max_score")
        if isinstance(score, (int, float)) and isinstance(max_score, (int, float)) and float(max_score) > 0:
            score_ratios.append(float(score) / float(max_score))
        latency_s = item.get("latency_s")
        if isinstance(latency_s, (int, float)):
            latencies.append(float(latency_s))
        for reason in item.get("reasons") or []:
            key = str(reason or "").strip()
            if key:
                reason_counter[key] = reason_counter.get(key, 0) + 1

    total_cases = len(results)
    return {
        "suite_name": suite_name,
        "total_cases": total_cases,
        "pass_rate": round(status_counts.get("PASS", 0) / max(total_cases, 1), 3),
        "warn_rate": round(status_counts.get("WARN", 0) / max(total_cases, 1), 3),
        "fail_rate": round(status_counts.get("FAIL", 0) / max(total_cases, 1), 3),
        "avg_score_ratio": round(sum(score_ratios) / max(len(score_ratios), 1), 3) if score_ratios else 0.0,
        "avg_latency_s": round(sum(latencies) / max(len(latencies), 1), 6) if latencies else 0.0,
        "reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(reason_counter.items(), key=lambda item: (-int(item[1]), str(item[0])))[:10]
        ],
    }