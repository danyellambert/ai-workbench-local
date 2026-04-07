"""Phase 6 helpers for the document operations copilot."""
from __future__ import annotations

from dataclasses import dataclass
import re


DOCUMENT_AGENT_INTENT_LABELS = {
    "document_question": "Document question",
    "executive_summary": "Executive summary",
    "business_response_drafting": "Business response drafting",
    "structured_extraction": "Structured extraction",
    "document_comparison": "Document comparison",
    "operational_checklist": "Operational checklist",
    "policy_compliance_review": "Policy/compliance review",
    "document_risk_review": "Document risk review",
    "operational_task_extraction": "Operational task extraction",
    "technical_assistance": "Technical assistance",
}

DOCUMENT_AGENT_TOOL_LABELS = {
    "consult_documents": "Consult indexed documents",
    "summarize_document": "Summarize document",
    "draft_business_response": "Draft document-grounded response",
    "extract_structured_data": "Extract structured information",
    "compare_documents": "Compare documents",
    "generate_operational_checklist": "Generate operational checklist",
    "review_policy_compliance": "Review policy/compliance",
    "review_document_risks": "Review risks and gaps",
    "extract_operational_tasks": "Extract operational tasks",
    "assist_technical_document": "Assist technical document",
}


@dataclass(frozen=True)
class DocumentAgentToolDefinition:
    name: str
    label: str
    description: str
    answer_mode: str
    min_document_count: int = 1
    requires_document_context: bool = True


DOCUMENT_AGENT_TOOL_DEFINITIONS = {
    "consult_documents": DocumentAgentToolDefinition(
        name="consult_documents",
        label=DOCUMENT_AGENT_TOOL_LABELS["consult_documents"],
        description="Consult indexed documents, retrieve relevant excerpts, and answer with grounding and sources.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "summarize_document": DocumentAgentToolDefinition(
        name="summarize_document",
        label=DOCUMENT_AGENT_TOOL_LABELS["summarize_document"],
        description="Generate a grounded executive summary for the selected document or document set.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "draft_business_response": DocumentAgentToolDefinition(
        name="draft_business_response",
        label=DOCUMENT_AGENT_TOOL_LABELS["draft_business_response"],
        description="Draft a response, email, or short position based only on the selected documents and ready for human review.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "extract_structured_data": DocumentAgentToolDefinition(
        name="extract_structured_data",
        label=DOCUMENT_AGENT_TOOL_LABELS["extract_structured_data"],
        description="Extract fields, entities, risks, and actions in a structured and auditable format.",
        answer_mode="json",
        min_document_count=1,
    ),
    "compare_documents": DocumentAgentToolDefinition(
        name="compare_documents",
        label=DOCUMENT_AGENT_TOOL_LABELS["compare_documents"],
        description="Compare selected documents and highlight differences, convergences, and relevant findings.",
        answer_mode="comparison_structured",
        min_document_count=2,
    ),
    "generate_operational_checklist": DocumentAgentToolDefinition(
        name="generate_operational_checklist",
        label=DOCUMENT_AGENT_TOOL_LABELS["generate_operational_checklist"],
        description="Turn the document into an actionable operational checklist without inferring steps beyond the text.",
        answer_mode="checklist",
        min_document_count=1,
    ),
    "review_policy_compliance": DocumentAgentToolDefinition(
        name="review_policy_compliance",
        label=DOCUMENT_AGENT_TOOL_LABELS["review_policy_compliance"],
        description="Review clauses, obligations, restrictions, and compliance risks with document grounding.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "review_document_risks": DocumentAgentToolDefinition(
        name="review_document_risks",
        label=DOCUMENT_AGENT_TOOL_LABELS["review_document_risks"],
        description="Analyze risks, gaps, pending items, and possible red flags explicitly present in the document.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "extract_operational_tasks": DocumentAgentToolDefinition(
        name="extract_operational_tasks",
        label=DOCUMENT_AGENT_TOOL_LABELS["extract_operational_tasks"],
        description="Extract actionable tasks, next steps, dates, and operational dependencies from the document.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "assist_technical_document": DocumentAgentToolDefinition(
        name="assist_technical_document",
        label=DOCUMENT_AGENT_TOOL_LABELS["assist_technical_document"],
        description="Analyze technical documents or code excerpts with a focus on bugs, risks, refactoring, and tests.",
        answer_mode="friendly",
        min_document_count=1,
    ),
}


def describe_document_agent_intent(intent: str) -> str:
    return DOCUMENT_AGENT_INTENT_LABELS.get((intent or "").strip().lower(), intent or "document_question")


def describe_document_agent_tool(tool_name: str) -> str:
    return DOCUMENT_AGENT_TOOL_LABELS.get((tool_name or "").strip().lower(), tool_name or "consult_documents")


def get_document_agent_tool_definition(tool_name: str) -> DocumentAgentToolDefinition | None:
    normalized = (tool_name or "").strip().lower()
    return DOCUMENT_AGENT_TOOL_DEFINITIONS.get(normalized)


def list_document_agent_tools(*, document_count: int = 0, use_document_context: bool = True) -> list[dict[str, object]]:
    tools: list[dict[str, object]] = []
    for definition in DOCUMENT_AGENT_TOOL_DEFINITIONS.values():
        available = True
        reason = "ready"
        if definition.requires_document_context and not use_document_context:
            available = False
            reason = "document_context_disabled"
        elif document_count < definition.min_document_count:
            available = False
            reason = f"requires_at_least_{definition.min_document_count}_documents"
        tools.append(
            {
                "name": definition.name,
                "label": definition.label,
                "description": definition.description,
                "answer_mode": definition.answer_mode,
                "min_document_count": definition.min_document_count,
                "available": available,
                "availability_reason": reason,
            }
        )
    return tools


def classify_document_agent_intent(user_input: str, *, document_count: int = 0) -> tuple[str, str]:
    normalized = " ".join(str(user_input or "").split()).strip().lower()

    comparison_tokens = (
        "compare",
        "comparison",
        "difference",
        "differences",
        "versus",
        " vs ",
    )
    checklist_tokens = (
        "checklist",
        "action plan",
        "steps",
        "tasks",
        "actions",
        "to-do",
        "todo",
    )
    drafting_tokens = (
        "draft",
        "draft a reply",
        "draft reply",
        "draft response",
        "draft an email",
        "draft a response email",
        "write a response",
        "write an email",
        "reply to",
        "reply to the client",
        "response to the client",
        "email to the client",
    )
    extraction_tokens = (
        "extract",
        "json",
        "fields",
        "structured data",
        "structured information",
    )
    risk_review_tokens = (
        "risk analysis",
        "risk review",
        "list risks",
        "list the risks",
        "risk map",
        "risks map",
        "gap",
        "gaps",
        "red flag",
        "red flags",
        "pending item",
        "pending items",
        "point of attention",
        "points of attention",
        "alert",
        "alerts",
    )
    operational_task_tokens = (
        "action plan",
        "owners",
        "owner",
        "deadline",
        "deadlines",
        "due date",
        "due dates",
        "next steps",
        "action items",
        "next actions",
        "next stages",
        "operational actions",
        "operational tasks",
        "operational deliverables",
    )
    compliance_tokens = (
        "compliance",
        "policy",
        "violation",
        "violations",
        "clause",
        "clauses",
        "obligation",
        "obligations",
        "confidentiality",
        "retention",
        "non-compete",
        "restriction",
        "restrictions",
    )
    technical_tokens = (
        "code",
        "api",
        "function",
        "functions",
        "refactor",
        "refactoring",
        "bug",
        "technical error",
        "readability",
        "maintainability",
        "unit test",
    )
    summary_tokens = (
        "summarize",
        "summary",
        "executive summary",
        "overview",
    )
    question_prefixes = (
        "what",
        "which",
        "how",
        "when",
        "where",
        "who",
    )

    if document_count >= 2 and any(token in normalized for token in comparison_tokens):
        return "document_comparison", "comparison_keywords_with_multiple_documents"
    if any(token in normalized for token in drafting_tokens):
        return "business_response_drafting", "drafting_keywords_detected"
    if any(token in normalized for token in operational_task_tokens):
        return "operational_task_extraction", "operational_task_keywords_detected"
    if any(token in normalized for token in checklist_tokens):
        return "operational_checklist", "checklist_keywords_detected"
    if any(token in normalized for token in extraction_tokens):
        return "structured_extraction", "extraction_keywords_detected"
    if any(token in normalized for token in risk_review_tokens):
        return "document_risk_review", "risk_review_keywords_detected"
    if any(token in normalized for token in compliance_tokens):
        return "policy_compliance_review", "policy_compliance_keywords_detected"
    if any(token in normalized for token in technical_tokens):
        return "technical_assistance", "technical_keywords_detected"
    if any(token in normalized for token in summary_tokens):
        return "executive_summary", "summary_keywords_detected"
    if "?" in normalized or any(normalized.startswith(prefix) for prefix in question_prefixes):
        return "document_question", "question_like_request_detected"
    if document_count >= 2:
        return "document_comparison", "multiple_documents_default_to_comparison"
    if document_count >= 1:
        return "document_question", "single_document_default_to_question_answering"
    return "executive_summary", "fallback_to_summary"


def select_document_agent_tool(intent: str, *, document_count: int = 0) -> tuple[str, str, str]:
    normalized_intent = (intent or "document_question").strip().lower() or "document_question"

    if normalized_intent == "document_comparison":
        if document_count >= 2:
            return "compare_documents", "comparison_structured", "comparison_intent"
        return "summarize_document", "friendly", "comparison_requires_multiple_documents_fallback_to_summary"
    if normalized_intent == "business_response_drafting":
        return "draft_business_response", "friendly", "business_response_drafting_intent"
    if normalized_intent == "document_risk_review":
        return "review_document_risks", "friendly", "document_risk_review_intent"
    if normalized_intent == "operational_task_extraction":
        return "extract_operational_tasks", "friendly", "operational_task_extraction_intent"
    if normalized_intent == "policy_compliance_review":
        return "review_policy_compliance", "friendly", "policy_compliance_review_intent"
    if normalized_intent == "technical_assistance":
        return "assist_technical_document", "friendly", "technical_assistance_intent"
    if normalized_intent == "structured_extraction":
        return "extract_structured_data", "json", "extraction_intent"
    if normalized_intent == "operational_checklist":
        return "generate_operational_checklist", "checklist", "checklist_intent"
    if normalized_intent == "executive_summary":
        return "summarize_document", "friendly", "summary_intent"
    return "consult_documents", "friendly", "question_answering_intent"


def normalize_agent_bullet_points(values: list[str] | None, *, limit: int = 6) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        cleaned = " ".join(str(value or "").split()).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
        if len(normalized) >= limit:
            break
    return normalized


def extract_bullet_points_from_text(text: str, *, limit: int = 6) -> list[str]:
    lines = [line.strip("-• ").strip() for line in str(text or "").splitlines() if line.strip()]
    candidates = [line for line in lines if len(line.split()) >= 3]
    if not candidates:
        sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", str(text or "")) if segment.strip()]
        candidates = sentences
    return normalize_agent_bullet_points(candidates, limit=limit)