"""Phase 6 helpers for the document operations copilot."""
from __future__ import annotations

from dataclasses import dataclass
import re


DOCUMENT_AGENT_INTENT_LABELS = {
    "document_question": "Pergunta documental",
    "executive_summary": "Resumo executivo",
    "structured_extraction": "Extração estruturada",
    "document_comparison": "Comparação documental",
    "operational_checklist": "Checklist operacional",
    "policy_compliance_review": "Revisão de policy/compliance",
    "document_risk_review": "Análise documental de riscos",
    "operational_task_extraction": "Extração operacional",
    "technical_assistance": "Assistência técnica",
}

DOCUMENT_AGENT_TOOL_LABELS = {
    "consult_documents": "Consultar documentos indexados",
    "summarize_document": "Resumir documento",
    "extract_structured_data": "Extrair informação estruturada",
    "compare_documents": "Comparar documentos",
    "generate_operational_checklist": "Gerar checklist operacional",
    "review_policy_compliance": "Revisar policy/compliance",
    "review_document_risks": "Analisar riscos e lacunas",
    "extract_operational_tasks": "Extrair tarefas operacionais",
    "assist_technical_document": "Assistir documento técnico",
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
        description="Consulta documentos indexados, recupera trechos relevantes e responde com grounding e fontes.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "summarize_document": DocumentAgentToolDefinition(
        name="summarize_document",
        label=DOCUMENT_AGENT_TOOL_LABELS["summarize_document"],
        description="Gera resumo executivo grounded do documento ou conjunto documental selecionado.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "extract_structured_data": DocumentAgentToolDefinition(
        name="extract_structured_data",
        label=DOCUMENT_AGENT_TOOL_LABELS["extract_structured_data"],
        description="Extrai campos, entidades, riscos e ações em formato estruturado e auditável.",
        answer_mode="json",
        min_document_count=1,
    ),
    "compare_documents": DocumentAgentToolDefinition(
        name="compare_documents",
        label=DOCUMENT_AGENT_TOOL_LABELS["compare_documents"],
        description="Compara documentos selecionados e destaca diferenças, convergências e achados relevantes.",
        answer_mode="comparison_structured",
        min_document_count=2,
    ),
    "generate_operational_checklist": DocumentAgentToolDefinition(
        name="generate_operational_checklist",
        label=DOCUMENT_AGENT_TOOL_LABELS["generate_operational_checklist"],
        description="Transforma o documento em checklist operacional acionável, sem inferir passos fora do texto.",
        answer_mode="checklist",
        min_document_count=1,
    ),
    "review_policy_compliance": DocumentAgentToolDefinition(
        name="review_policy_compliance",
        label=DOCUMENT_AGENT_TOOL_LABELS["review_policy_compliance"],
        description="Revisa cláusulas, obrigações, restrições e riscos de compliance com grounding documental.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "review_document_risks": DocumentAgentToolDefinition(
        name="review_document_risks",
        label=DOCUMENT_AGENT_TOOL_LABELS["review_document_risks"],
        description="Analisa riscos, lacunas, pendências e possíveis red flags explicitamente presentes no documento.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "extract_operational_tasks": DocumentAgentToolDefinition(
        name="extract_operational_tasks",
        label=DOCUMENT_AGENT_TOOL_LABELS["extract_operational_tasks"],
        description="Extrai tarefas acionáveis, próximos passos, datas e dependências operacionais do documento.",
        answer_mode="friendly",
        min_document_count=1,
    ),
    "assist_technical_document": DocumentAgentToolDefinition(
        name="assist_technical_document",
        label=DOCUMENT_AGENT_TOOL_LABELS["assist_technical_document"],
        description="Analisa documentos técnicos ou trechos de código com foco em bugs, riscos, refatoração e testes.",
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
        "comparar",
        "comparação",
        "comparacao",
        "diferença",
        "diferenca",
        "diferenças",
        "diferencas",
        "versus",
        " vs ",
    )
    checklist_tokens = (
        "checklist",
        "plano de ação",
        "plano de acao",
        "passos",
        "tarefas",
        "ações",
        "acoes",
        "to-do",
        "todo",
    )
    extraction_tokens = (
        "extrair",
        "extraia",
        "extração",
        "extracao",
        "json",
        "campos",
        "dados estruturados",
        "informações estruturadas",
        "informacoes estruturadas",
    )
    risk_review_tokens = (
        "análise de riscos",
        "analise de riscos",
        "review de riscos",
        "revisão de riscos",
        "revisao de riscos",
        "listar riscos",
        "liste os riscos",
        "mapa de risco",
        "mapa de riscos",
        "gap",
        "gaps",
        "lacuna",
        "lacunas",
        "red flag",
        "red flags",
        "pendência",
        "pendencia",
        "pendências",
        "pendencias",
        "ponto de atenção",
        "pontos de atenção",
        "alerta",
        "alertas",
    )
    operational_task_tokens = (
        "action items",
        "itens acionáveis",
        "itens acionaveis",
        "próximas ações",
        "proximas acoes",
        "próximas etapas",
        "proximas etapas",
        "ações operacionais",
        "acoes operacionais",
        "tarefas operacionais",
        "deliverables operacionais",
    )
    compliance_tokens = (
        "compliance",
        "conformidade",
        "policy",
        "política",
        "politica",
        "violação",
        "violacao",
        "cláusula",
        "clausula",
        "cláusulas",
        "clausulas",
        "obrigação",
        "obrigacao",
        "obrigações",
        "obrigacoes",
        "confidencialidade",
        "confidentiality",
        "retenção",
        "retencao",
        "non-compete",
        "não concorrência",
        "nao concorrencia",
        "restrição",
        "restricao",
        "restrições",
        "restricoes",
    )
    technical_tokens = (
        "código",
        "codigo",
        "code",
        "api",
        "função",
        "funcao",
        "funções",
        "funcoes",
        "refator",
        "bug",
        "erro técnico",
        "erro tecnico",
        "readability",
        "maintainability",
        "teste unitário",
        "teste unitario",
    )
    summary_tokens = (
        "resuma",
        "resumo",
        "sumarize",
        "sumarizar",
        "sumário executivo",
        "sumario executivo",
        "overview",
        "executive summary",
    )
    question_prefixes = (
        "qual",
        "quais",
        "como",
        "onde",
        "quando",
        "quem",
        "what",
        "which",
        "how",
        "when",
        "where",
        "who",
    )

    if document_count >= 2 and any(token in normalized for token in comparison_tokens):
        return "document_comparison", "comparison_keywords_with_multiple_documents"
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