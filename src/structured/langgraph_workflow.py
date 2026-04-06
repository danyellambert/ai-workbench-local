"""Experimental LangGraph workflow for structured task execution."""
from __future__ import annotations

import time
from typing import TypedDict
from uuid import uuid4

from .envelope import StructuredResult, TaskExecutionRequest


def describe_structured_execution_strategy(strategy: str) -> str:
    labels = {
        "direct": "Execução direta",
        "langgraph_context_retry": "LangGraph · retry de contexto (experimental)",
    }
    return labels.get((strategy or "").strip().lower(), strategy or "direct")


def resolve_structured_execution_strategy(strategy: str | None) -> tuple[str, str, str | None]:
    requested = (strategy or "direct").strip().lower() or "direct"
    if requested == "direct":
        return requested, "direct", None
    if requested == "langgraph_context_retry":
        try:
            from langgraph.graph import StateGraph  # noqa: F401
        except Exception:
            return requested, "direct", "langgraph_not_installed"
        return requested, "langgraph_context_retry", None
    return requested, "direct", "unknown_strategy"


class StructuredWorkflowState(TypedDict, total=False):
    workflow_id: str
    request: TaskExecutionRequest
    effective_request: TaskExecutionRequest
    result: StructuredResult
    attempt: int
    max_attempts: int
    attempt_context_strategies: list[str]
    workflow_trace: list[dict[str, object]]
    route_decision: str
    guardrail_decision: str
    retry_reason: str
    needs_review: bool
    needs_review_reason: str
    agent_intent: str
    agent_intent_reason: str
    agent_tool: str
    agent_tool_reason: str
    agent_answer_mode: str


def _append_trace(
    existing: list[dict[str, object]] | None,
    *,
    node: str,
    detail: str,
    attempt: int,
    context_strategy: str,
    success: bool | None = None,
) -> list[dict[str, object]]:
    trace = list(existing or [])
    entry: dict[str, object] = {
        "node": node,
        "detail": detail,
        "attempt": attempt,
        "context_strategy": context_strategy,
    }
    if success is not None:
        entry["success"] = success
    trace.append(entry)
    return trace


def _prepare_request(state: StructuredWorkflowState) -> StructuredWorkflowState:
    request = state["request"]
    effective_request = request.model_copy()
    context_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    return {
        "workflow_id": f"lgw-{uuid4().hex[:8]}",
        "effective_request": effective_request,
        "attempt": 1,
        "max_attempts": 2,
        "attempt_context_strategies": [context_strategy],
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="prepare_request",
            detail="Preparando request inicial para o workflow estruturado",
            attempt=1,
            context_strategy=context_strategy,
        ),
    }


def _select_initial_context_strategy(request: TaskExecutionRequest) -> tuple[str, str]:
    requested = (request.context_strategy or "").strip().lower()
    if requested in {"document_scan", "retrieval"}:
        return requested, f"preserve_requested_strategy:{requested}"
    if not request.use_document_context or not request.source_document_ids:
        return "document_scan", "no_documents_or_context_disabled"

    normalized_input = (request.input_text or "").strip()
    has_meaningful_query = len(normalized_input) >= 24

    if request.task_type in {"summary", "code_analysis"} and has_meaningful_query:
        return "retrieval", "query_driven_task_prefers_retrieval"
    if request.task_type in {"checklist", "extraction", "cv_analysis"}:
        return "document_scan", "coverage_first_task_prefers_document_scan"
    return "document_scan", "default_document_scan"


def _route_context_strategy(state: StructuredWorkflowState) -> StructuredWorkflowState:
    request = state["request"]
    selected_strategy, route_decision = _select_initial_context_strategy(request)
    effective_request = request.model_copy(update={"context_strategy": selected_strategy})
    return {
        "effective_request": effective_request,
        "route_decision": route_decision,
        "attempt_context_strategies": [selected_strategy],
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="route_context_strategy",
            detail=f"Selecionando estratégia inicial de contexto: {route_decision}",
            attempt=int(state.get("attempt", 1)),
            context_strategy=selected_strategy,
        ),
    }


def _prepare_document_agent_request(state: StructuredWorkflowState) -> StructuredWorkflowState:
    request = state["request"]
    effective_request = request.model_copy(update={"telemetry": dict(request.telemetry or {})})
    context_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    return {
        "workflow_id": f"lgw-{uuid4().hex[:8]}",
        "effective_request": effective_request,
        "attempt": 1,
        "max_attempts": 2,
        "attempt_context_strategies": [context_strategy],
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="prepare_agent_request",
            detail="Preparando request inicial do agente documental",
            attempt=1,
            context_strategy=context_strategy,
        ),
    }


def _classify_document_agent_intent(state: StructuredWorkflowState) -> StructuredWorkflowState:
    from .document_agent import classify_document_agent_intent

    request = state["request"]
    effective_request = state.get("effective_request") or request
    context_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    intent, reason = classify_document_agent_intent(
        request.input_text,
        document_count=len(request.source_document_ids or []),
    )
    return {
        "agent_intent": intent,
        "agent_intent_reason": reason,
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="classify_intent",
            detail=f"Classificando intenção do agente: {reason}",
            attempt=int(state.get("attempt", 1)),
            context_strategy=context_strategy,
        ),
    }


def _select_document_agent_tool_node(state: StructuredWorkflowState) -> StructuredWorkflowState:
    from .document_agent import select_document_agent_tool

    request = state["request"]
    effective_request = state.get("effective_request") or request
    context_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    intent = str(state.get("agent_intent") or "document_question")
    tool_name, answer_mode, tool_reason = select_document_agent_tool(
        intent,
        document_count=len(request.source_document_ids or []),
    )
    telemetry = dict(effective_request.telemetry or {})
    telemetry.update(
        {
            "agent_intent": intent,
            "agent_intent_reason": state.get("agent_intent_reason"),
            "agent_tool": tool_name,
            "agent_tool_reason": tool_reason,
            "agent_answer_mode": answer_mode,
        }
    )
    updated_request = effective_request.model_copy(update={"telemetry": telemetry})
    return {
        "effective_request": updated_request,
        "agent_tool": tool_name,
        "agent_tool_reason": tool_reason,
        "agent_answer_mode": answer_mode,
        "route_decision": f"{intent}->{tool_name}",
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="select_tool",
            detail=f"Selecionando tool do agente: {tool_reason}",
            attempt=int(state.get("attempt", 1)),
            context_strategy=context_strategy,
        ),
    }


def _resolve_document_agent_context_strategy(tool_name: str, request: TaskExecutionRequest) -> tuple[str, str]:
    normalized_query = (request.input_text or "").strip()
    if not request.use_document_context or not request.source_document_ids:
        return "document_scan", "no_documents_or_context_disabled"
    if tool_name == "consult_documents" and normalized_query:
        return "retrieval", "document_question_prefers_retrieval"
    if tool_name == "draft_business_response" and normalized_query:
        return "retrieval", "drafting_prefers_retrieval"
    if tool_name == "compare_documents" and normalized_query and len(request.source_document_ids or []) <= 2:
        return "retrieval", "comparison_prefers_retrieval_when_document_count_is_small"
    return "document_scan", "coverage_first_document_agent"


def _route_document_agent_context_strategy(state: StructuredWorkflowState) -> StructuredWorkflowState:
    request = state["request"]
    effective_request = state.get("effective_request") or request
    tool_name = str(state.get("agent_tool") or "consult_documents")
    selected_strategy, route_decision = _resolve_document_agent_context_strategy(tool_name, request)
    telemetry = dict(effective_request.telemetry or {})
    telemetry["agent_context_strategy"] = selected_strategy
    updated_request = effective_request.model_copy(
        update={
            "context_strategy": selected_strategy,
            "telemetry": telemetry,
        }
    )
    return {
        "effective_request": updated_request,
        "route_decision": route_decision,
        "attempt_context_strategies": [selected_strategy],
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="route_agent_context_strategy",
            detail=f"Selecionando estratégia de contexto do agente: {route_decision}",
            attempt=int(state.get("attempt", 1)),
            context_strategy=selected_strategy,
        ),
    }


def _execute_task(state: StructuredWorkflowState) -> StructuredWorkflowState:
    from .service import structured_service

    effective_request = state["effective_request"]
    context_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    result = structured_service.execute_task(effective_request)
    return {
        "result": result,
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="execute_task",
            detail="Executando structured_service dentro do workflow LangGraph",
            attempt=int(state.get("attempt", 1)),
            context_strategy=context_strategy,
            success=bool(result.success),
        ),
    }


def _should_retry(state: StructuredWorkflowState) -> bool:
    result = state.get("result")
    effective_request = state.get("effective_request")
    if not isinstance(result, StructuredResult) or not isinstance(effective_request, TaskExecutionRequest):
        return False
    if int(state.get("attempt", 1)) >= int(state.get("max_attempts", 2)):
        return False
    if not effective_request.use_document_context or not effective_request.source_document_ids:
        return False
    current_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    if current_strategy == "retrieval":
        return False
    return True


def _evaluate_guardrails(state: StructuredWorkflowState) -> StructuredWorkflowState:
    result = state.get("result")
    effective_request = state.get("effective_request")
    if not isinstance(result, StructuredResult) or not isinstance(effective_request, TaskExecutionRequest):
        return {
            "guardrail_decision": "finish_missing_result",
            "workflow_trace": _append_trace(
                state.get("workflow_trace"),
                node="evaluate_guardrails",
                detail="Workflow sem resultado estruturado válido; finalizando",
                attempt=int(state.get("attempt", 1)),
                context_strategy=(effective_request.context_strategy if isinstance(effective_request, TaskExecutionRequest) else "document_scan") or "document_scan",
            ),
        }

    context_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    quality_score = result.quality_score if isinstance(result.quality_score, (int, float)) else None
    parse_recovery = {}
    if isinstance(result.execution_metadata, dict):
        telemetry = result.execution_metadata.get("telemetry") if isinstance(result.execution_metadata.get("telemetry"), dict) else {}
        parse_recovery = telemetry.get("parse_recovery") if isinstance(telemetry.get("parse_recovery"), dict) else {}

    decision = "finish_ok"
    retry_reason = None
    needs_review = False
    needs_review_reason = None

    if not result.success and _should_retry(state):
        decision = "retry_with_retrieval_after_failure"
        retry_reason = "structured_result_failed_under_document_scan"
    elif result.success and quality_score is not None and quality_score < 0.6 and _should_retry(state):
        decision = "retry_with_retrieval_low_quality"
        retry_reason = f"quality_score_below_threshold:{quality_score:.3f}"
    elif result.success and quality_score is not None and quality_score < 0.72:
        decision = "finish_needs_review_low_quality"
        needs_review = True
        needs_review_reason = f"quality_score_below_review_threshold:{quality_score:.3f}"
    elif result.success and parse_recovery.get("used"):
        decision = "finish_needs_review_parse_recovery"
        needs_review = True
        needs_review_reason = "structured_parse_recovery_was_required"

    trace_detail = {
        "finish_ok": "Resultado aceito sem guardrail adicional",
        "retry_with_retrieval_after_failure": "Falha na execução; retry controlado com retrieval",
        "retry_with_retrieval_low_quality": "Qualidade baixa; retry controlado com retrieval",
        "finish_needs_review_low_quality": "Resultado marcado como needs_review por qualidade baixa",
        "finish_needs_review_parse_recovery": "Resultado marcado como needs_review porque exigiu parse recovery",
    }.get(decision, decision)

    return {
        "guardrail_decision": decision,
        **({"retry_reason": retry_reason} if retry_reason else {}),
        **({"needs_review": needs_review} if needs_review else {}),
        **({"needs_review_reason": needs_review_reason} if needs_review_reason else {}),
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="evaluate_guardrails",
            detail=trace_detail,
            attempt=int(state.get("attempt", 1)),
            context_strategy=context_strategy,
            success=bool(result.success),
        ),
    }


def _evaluate_document_agent_guardrails(state: StructuredWorkflowState) -> StructuredWorkflowState:
    from .base import DocumentAgentPayload

    result = state.get("result")
    effective_request = state.get("effective_request")
    if not isinstance(result, StructuredResult) or not isinstance(effective_request, TaskExecutionRequest):
        return {
            "guardrail_decision": "finish_missing_result",
            "workflow_trace": _append_trace(
                state.get("workflow_trace"),
                node="evaluate_agent_guardrails",
                detail="Workflow do agente sem resultado válido; finalizando",
                attempt=int(state.get("attempt", 1)),
                context_strategy=(effective_request.context_strategy if isinstance(effective_request, TaskExecutionRequest) else "document_scan") or "document_scan",
            ),
        }

    context_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    payload = result.validated_output if isinstance(result.validated_output, DocumentAgentPayload) else None
    sources_count = len(payload.sources) if payload is not None else int(result.execution_metadata.get("agent_source_count") or 0) if isinstance(result.execution_metadata, dict) else 0
    confidence = payload.confidence if payload is not None else (result.quality_score if isinstance(result.quality_score, (int, float)) else None)
    needs_review = bool(payload.needs_review) if payload is not None else bool(result.execution_metadata.get("needs_review")) if isinstance(result.execution_metadata, dict) else False
    needs_review_reason = payload.needs_review_reason if payload is not None else result.execution_metadata.get("needs_review_reason") if isinstance(result.execution_metadata, dict) else None

    decision = "finish_ok"
    retry_reason = None
    review_flag = False
    review_reason = None

    if not result.success and _should_retry(state):
        decision = "retry_with_retrieval_after_failure"
        retry_reason = "document_agent_failed_under_document_scan"
    elif result.success and sources_count == 0 and _should_retry(state):
        decision = "retry_with_retrieval_missing_sources"
        retry_reason = "document_agent_returned_no_grounded_sources"
    elif result.success and isinstance(confidence, (int, float)) and confidence < 0.62 and _should_retry(state):
        decision = "retry_with_retrieval_low_confidence"
        retry_reason = f"document_agent_confidence_below_retry_threshold:{float(confidence):.3f}"
    elif result.success and (needs_review or (isinstance(confidence, (int, float)) and confidence < 0.72)):
        decision = "finish_needs_review_agent"
        review_flag = True
        review_reason = needs_review_reason or (f"document_agent_confidence_below_review_threshold:{float(confidence):.3f}" if isinstance(confidence, (int, float)) else "document_agent_needs_review")

    trace_detail = {
        "finish_ok": "Resposta do agente aceita sem guardrail adicional",
        "retry_with_retrieval_after_failure": "Falha no agente documental; retry controlado com retrieval",
        "retry_with_retrieval_missing_sources": "Resposta sem fontes; retry controlado com retrieval",
        "retry_with_retrieval_low_confidence": "Confiança baixa; retry controlado com retrieval",
        "finish_needs_review_agent": "Resposta do agente marcada para revisão humana",
    }.get(decision, decision)

    return {
        "guardrail_decision": decision,
        **({"retry_reason": retry_reason} if retry_reason else {}),
        **({"needs_review": review_flag} if review_flag else {}),
        **({"needs_review_reason": review_reason} if review_reason else {}),
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="evaluate_agent_guardrails",
            detail=trace_detail,
            attempt=int(state.get("attempt", 1)),
            context_strategy=context_strategy,
            success=bool(result.success),
        ),
    }


def _guardrail_transition(state: StructuredWorkflowState) -> str:
    decision = (state.get("guardrail_decision") or "").strip().lower()
    if decision.startswith("retry_with_retrieval"):
        return "retry_with_retrieval"
    if decision.startswith("finish_needs_review"):
        return "mark_needs_review"
    return "finish"


def _should_retry_with_retrieval(state: StructuredWorkflowState) -> str:
    result = state.get("result")
    effective_request = state.get("effective_request")
    if not isinstance(result, StructuredResult) or not isinstance(effective_request, TaskExecutionRequest):
        return "finish"
    if result.success:
        return "finish"
    if int(state.get("attempt", 1)) >= int(state.get("max_attempts", 2)):
        return "finish"
    if not effective_request.use_document_context or not effective_request.source_document_ids:
        return "finish"
    current_strategy = (effective_request.context_strategy or "document_scan").strip().lower() or "document_scan"
    if current_strategy == "retrieval":
        return "finish"
    return "retry_with_retrieval"


def _retry_with_retrieval(state: StructuredWorkflowState) -> StructuredWorkflowState:
    request = state.get("effective_request") or state["request"]
    next_attempt = int(state.get("attempt", 1)) + 1
    effective_request = request.model_copy(update={"context_strategy": "retrieval"})
    return {
        "effective_request": effective_request,
        "attempt": next_attempt,
        "attempt_context_strategies": [
            *(state.get("attempt_context_strategies") or []),
            "retrieval",
        ],
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="retry_with_retrieval",
            detail=(state.get("retry_reason") or "Retry controlado com context_strategy=retrieval"),
            attempt=next_attempt,
            context_strategy="retrieval",
        ),
    }


def _mark_needs_review(state: StructuredWorkflowState) -> StructuredWorkflowState:
    from .base import DocumentAgentPayload

    result = state.get("result")
    effective_request = state.get("effective_request")
    if not isinstance(result, StructuredResult) or not isinstance(effective_request, TaskExecutionRequest):
        return {}

    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
    result.execution_metadata = {
        **metadata,
        "needs_review": True,
        "needs_review_reason": state.get("needs_review_reason") or "workflow_guardrail",
    }
    if isinstance(result.validated_output, DocumentAgentPayload):
        result.validated_output = result.validated_output.model_copy(
            update={
                "needs_review": True,
                "needs_review_reason": state.get("needs_review_reason") or "workflow_guardrail",
            }
        )
    return {
        "result": result,
        "workflow_trace": _append_trace(
            state.get("workflow_trace"),
            node="mark_needs_review",
            detail=(state.get("needs_review_reason") or "Marcando saída para revisão humana"),
            attempt=int(state.get("attempt", 1)),
            context_strategy=(effective_request.context_strategy or "document_scan").strip().lower() or "document_scan",
            success=bool(result.success),
        ),
    }


def _build_langgraph_app():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(StructuredWorkflowState)
    graph.add_node("prepare_request", _prepare_request)
    graph.add_node("route_context_strategy", _route_context_strategy)
    graph.add_node("execute_task", _execute_task)
    graph.add_node("evaluate_guardrails", _evaluate_guardrails)
    graph.add_node("retry_with_retrieval", _retry_with_retrieval)
    graph.add_node("mark_needs_review", _mark_needs_review)
    graph.set_entry_point("prepare_request")
    graph.add_edge("prepare_request", "route_context_strategy")
    graph.add_edge("route_context_strategy", "execute_task")
    graph.add_edge("execute_task", "evaluate_guardrails")
    graph.add_conditional_edges(
        "evaluate_guardrails",
        _guardrail_transition,
        {
            "retry_with_retrieval": "retry_with_retrieval",
            "mark_needs_review": "mark_needs_review",
            "finish": END,
        },
    )
    graph.add_edge("retry_with_retrieval", "execute_task")
    graph.add_edge("mark_needs_review", END)
    return graph.compile()


def _build_document_agent_langgraph_app():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(StructuredWorkflowState)
    graph.add_node("prepare_agent_request", _prepare_document_agent_request)
    graph.add_node("classify_intent", _classify_document_agent_intent)
    graph.add_node("select_tool", _select_document_agent_tool_node)
    graph.add_node("route_agent_context_strategy", _route_document_agent_context_strategy)
    graph.add_node("execute_task", _execute_task)
    graph.add_node("evaluate_agent_guardrails", _evaluate_document_agent_guardrails)
    graph.add_node("retry_with_retrieval", _retry_with_retrieval)
    graph.add_node("mark_needs_review", _mark_needs_review)
    graph.set_entry_point("prepare_agent_request")
    graph.add_edge("prepare_agent_request", "classify_intent")
    graph.add_edge("classify_intent", "select_tool")
    graph.add_edge("select_tool", "route_agent_context_strategy")
    graph.add_edge("route_agent_context_strategy", "execute_task")
    graph.add_edge("execute_task", "evaluate_agent_guardrails")
    graph.add_conditional_edges(
        "evaluate_agent_guardrails",
        _guardrail_transition,
        {
            "retry_with_retrieval": "retry_with_retrieval",
            "mark_needs_review": "mark_needs_review",
            "finish": END,
        },
    )
    graph.add_edge("retry_with_retrieval", "execute_task")
    graph.add_edge("mark_needs_review", END)
    return graph.compile()


def _build_langgraph_app_for_request(request: TaskExecutionRequest):
    if request.task_type == "document_agent":
        return _build_document_agent_langgraph_app()
    return _build_langgraph_app()


def _annotate_result(
    result: StructuredResult,
    *,
    workflow_total_s: float | None,
    workflow_id: str | None,
    requested_strategy: str,
    used_strategy: str,
    fallback_reason: str | None,
    route_decision: str | None,
    guardrail_decision: str | None,
    attempt_context_strategies: list[str] | None,
    workflow_trace: list[dict[str, object]] | None,
    needs_review: bool | None = None,
    needs_review_reason: str | None = None,
) -> StructuredResult:
    metadata = result.execution_metadata if isinstance(result.execution_metadata, dict) else {}
    result.execution_metadata = {
        **metadata,
        **({"workflow_total_s": round(float(workflow_total_s), 4)} if workflow_total_s is not None else {}),
        **({"workflow_id": workflow_id} if workflow_id else {}),
        "execution_strategy_requested": requested_strategy,
        "execution_strategy_used": used_strategy,
        **({"execution_strategy_fallback_reason": fallback_reason} if fallback_reason else {}),
        **({"workflow_route_decision": route_decision} if route_decision else {}),
        **({"workflow_guardrail_decision": guardrail_decision} if guardrail_decision else {}),
        "workflow_attempts": len(attempt_context_strategies or []),
        "workflow_context_strategies": list(attempt_context_strategies or []),
        "workflow_trace": list(workflow_trace or []),
        "workflow_node_count": len(workflow_trace or []),
        **({"needs_review": needs_review} if needs_review is not None else {}),
        **({"needs_review_reason": needs_review_reason} if needs_review_reason else {}),
    }
    return result


def run_structured_execution_workflow(
    request: TaskExecutionRequest,
    *,
    strategy: str = "direct",
) -> StructuredResult:
    from .service import structured_service

    started_at = time.perf_counter()
    requested_strategy, used_strategy, fallback_reason = resolve_structured_execution_strategy(strategy)
    if used_strategy == "direct":
        result = structured_service.execute_task(request)
        return _annotate_result(
            result,
            workflow_total_s=time.perf_counter() - started_at,
            workflow_id=None,
            requested_strategy=requested_strategy,
            used_strategy="direct",
            fallback_reason=fallback_reason,
            route_decision=None,
            guardrail_decision="direct_execution",
            attempt_context_strategies=[(request.context_strategy or "document_scan").strip().lower() or "document_scan"],
            workflow_trace=[
                {
                    "node": "direct_execution",
                    "detail": "Fluxo estruturado executado sem LangGraph",
                    "attempt": 1,
                    "context_strategy": (request.context_strategy or "document_scan").strip().lower() or "document_scan",
                    "success": bool(result.success),
                }
            ],
        )

    try:
        app = _build_langgraph_app_for_request(request)
        final_state = app.invoke({"request": request})
        result = final_state.get("result") if isinstance(final_state, dict) else None
        if not isinstance(result, StructuredResult):
            result = structured_service.execute_task(request)
            return _annotate_result(
                result,
                workflow_total_s=time.perf_counter() - started_at,
                workflow_id=final_state.get("workflow_id") if isinstance(final_state, dict) else None,
                requested_strategy=requested_strategy,
                used_strategy="direct",
                fallback_reason="langgraph_returned_no_result",
                route_decision=final_state.get("route_decision") if isinstance(final_state, dict) else None,
                guardrail_decision="langgraph_returned_no_result",
                attempt_context_strategies=[(request.context_strategy or "document_scan").strip().lower() or "document_scan"],
                workflow_trace=[
                    {
                        "node": "direct_execution",
                        "detail": "LangGraph não retornou resultado final; fallback para execução direta",
                        "attempt": 1,
                        "context_strategy": (request.context_strategy or "document_scan").strip().lower() or "document_scan",
                        "success": bool(result.success),
                    }
                ],
            )
        return _annotate_result(
            result,
            workflow_total_s=time.perf_counter() - started_at,
            workflow_id=final_state.get("workflow_id") if isinstance(final_state, dict) else None,
            requested_strategy=requested_strategy,
            used_strategy="langgraph_context_retry",
            fallback_reason=fallback_reason,
            route_decision=final_state.get("route_decision") if isinstance(final_state, dict) else None,
            guardrail_decision=final_state.get("guardrail_decision") if isinstance(final_state, dict) else None,
            attempt_context_strategies=final_state.get("attempt_context_strategies") if isinstance(final_state, dict) else None,
            workflow_trace=final_state.get("workflow_trace") if isinstance(final_state, dict) else None,
            needs_review=final_state.get("needs_review") if isinstance(final_state, dict) else None,
            needs_review_reason=final_state.get("needs_review_reason") if isinstance(final_state, dict) else None,
        )
    except Exception as error:
        result = structured_service.execute_task(request)
        return _annotate_result(
            result,
            workflow_total_s=time.perf_counter() - started_at,
            workflow_id=None,
            requested_strategy=requested_strategy,
            used_strategy="direct",
            fallback_reason=f"langgraph_runtime_error:{error}",
            route_decision=None,
            guardrail_decision="langgraph_runtime_error",
            attempt_context_strategies=[(request.context_strategy or "document_scan").strip().lower() or "document_scan"],
            workflow_trace=[
                {
                    "node": "direct_execution",
                    "detail": "Erro no workflow LangGraph; fallback para execução direta",
                    "attempt": 1,
                    "context_strategy": (request.context_strategy or "document_scan").strip().lower() or "document_scan",
                    "success": bool(result.success),
                }
            ],
        )