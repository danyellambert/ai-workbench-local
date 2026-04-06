from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import BASE_DIR, PresentationExportSettings, RagSettings
from src.providers.registry import resolve_provider_runtime_profile
from src.rag.loaders import LoadedDocument
from src.rag.service import get_indexed_documents, normalize_rag_index, upsert_documents_in_rag_index
from src.services.document_context import build_structured_document_context
from src.services.presentation_export import (
    ACTION_PLAN_EXPORT_KIND,
    CANDIDATE_REVIEW_EXPORT_KIND,
    DOCUMENT_REVIEW_EXPORT_KIND,
    EXECUTIVE_DECK_EXPORT_KIND_LABELS,
    POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
)
from src.services.presentation_export_service import generate_executive_deck
from src.storage.rag_store import load_rag_store, save_rag_store
from src.storage.runtime_paths import (
    get_phase95_evidenceops_action_store_path,
    get_phase95_evidenceops_worklog_path,
)
from src.structured.base import CVAnalysisPayload, DocumentAgentPayload
from src.structured.envelope import StructuredResult, TaskExecutionRequest
from src.structured.langgraph_workflow import run_structured_execution_workflow

from .models import (
    GroundingPreview,
    ProductArtifact,
    ProductDocumentRef,
    ProductWorkflowDefinition,
    ProductWorkflowId,
    ProductWorkflowRequest,
    ProductWorkflowResult,
)

DEFAULT_WORKFLOW_QUERIES: dict[ProductWorkflowId, str] = {
    "document_review": "Review the selected documents and produce a grounded executive summary with key findings, risks, gaps and recommended next actions.",
    "policy_contract_comparison": "Compare the selected documents and identify the most relevant differences, business impact, watchouts and a grounded recommendation.",
    "action_plan_evidence_review": "Review the selected documents and derive a grounded action plan with owners, deadlines, evidence gaps and recommended next steps.",
    "candidate_review": "Review this candidate profile and summarize relevant experience, strengths, gaps, seniority signals and an initial recommendation.",
}

WORKFLOW_CONTRACT_DOCS: dict[ProductWorkflowId, str] = {
    "document_review": "docs/EXECUTIVE_DECK_GENERATION_DOCUMENT_REVIEW_DECK_CONTRACT_V1.md",
    "policy_contract_comparison": "docs/EXECUTIVE_DECK_GENERATION_POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1.md",
    "action_plan_evidence_review": "docs/EXECUTIVE_DECK_GENERATION_ACTION_PLAN_DECK_CONTRACT_V1.md",
    "candidate_review": "docs/EXECUTIVE_DECK_GENERATION_CANDIDATE_REVIEW_DECK_CONTRACT_V1.md",
}

DOCUMENT_AGENT_WORKFLOW_DEFAULTS: dict[ProductWorkflowId, dict[str, str]] = {
    "document_review": {
        "agent_intent": "document_risk_review",
        "agent_tool": "review_document_risks",
        "agent_answer_mode": "friendly",
    },
    "policy_contract_comparison": {
        "agent_intent": "document_comparison",
        "agent_tool": "compare_documents",
        "agent_answer_mode": "comparison_structured",
    },
    "action_plan_evidence_review": {
        "agent_intent": "operational_task_extraction",
        "agent_tool": "extract_operational_tasks",
        "agent_answer_mode": "friendly",
    },
}


def build_product_workflow_catalog() -> dict[ProductWorkflowId, ProductWorkflowDefinition]:
    return {
        "document_review": ProductWorkflowDefinition(
            workflow_id="document_review",
            label="Document Review",
            headline="Grounded review of key findings, risks and next actions.",
            description="Summarize complex documents into review-ready findings, risks, gaps and recommended next steps.",
            required_document_count_min=1,
            default_export_kind=DOCUMENT_REVIEW_EXPORT_KIND,
            default_export_label=EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(DOCUMENT_REVIEW_EXPORT_KIND),
            backend_task_types=["document_agent", "summary", "extraction"],
            badge_items=["Grounded", "Structured", "Deck-ready"],
            preferred_context_strategy="retrieval",
            input_placeholder="Ask for a grounded review focus, such as risks, obligations, findings, gaps or executive summary angle.",
            example_prompts=[
                "Highlight the main risks, obligations and missing information in this document.",
                "Produce an executive review with key findings, watchouts and next actions for leadership.",
                "Summarize the document with the most relevant operational takeaways and evidence gaps.",
            ],
            expected_outputs=[
                "Executive review summary",
                "Grounded findings and risks",
                "Recommended next actions",
                "Document Review deck artifact",
            ],
            workflow_contract=WORKFLOW_CONTRACT_DOCS["document_review"],
        ),
        "policy_contract_comparison": ProductWorkflowDefinition(
            workflow_id="policy_contract_comparison",
            label="Policy / Contract Comparison",
            headline="Compare versions, surface impact and support a grounded decision.",
            description="Identify the most relevant differences between documents and frame their business impact with evidence.",
            required_document_count_min=2,
            default_export_kind=POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
            default_export_label=EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(POLICY_CONTRACT_COMPARISON_EXPORT_KIND),
            backend_task_types=["document_agent"],
            badge_items=["Comparison", "Grounded", "Decision-ready"],
            preferred_context_strategy="retrieval",
            input_placeholder="Specify the comparison lens: obligations, policy changes, contract deltas, business impact or decision criteria.",
            example_prompts=[
                "Compare the two policies and surface the most material obligation changes.",
                "Identify what changed between these contracts and explain the business impact of each difference.",
                "Produce a grounded recommendation with watchouts before legal or compliance review.",
            ],
            expected_outputs=[
                "Comparison findings",
                "Business impact and watchouts",
                "Decision-ready recommendation",
                "Comparison deck artifact",
            ],
            workflow_contract=WORKFLOW_CONTRACT_DOCS["policy_contract_comparison"],
        ),
        "action_plan_evidence_review": ProductWorkflowDefinition(
            workflow_id="action_plan_evidence_review",
            label="Action Plan / Evidence Review",
            headline="Turn findings into owners, deadlines and operational follow-up.",
            description="Extract actionable next steps, operational backlog and evidence-backed follow-up guidance.",
            required_document_count_min=1,
            default_export_kind=ACTION_PLAN_EXPORT_KIND,
            default_export_label=EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(ACTION_PLAN_EXPORT_KIND),
            backend_task_types=["document_agent", "checklist"],
            badge_items=["Actionable", "Operational", "Evidence-backed"],
            preferred_context_strategy="document_scan",
            input_placeholder="Describe the execution objective, owners, deadlines or evidence gaps that should drive the action plan.",
            example_prompts=[
                "Turn the findings into an action plan with owners, due dates and evidence gaps.",
                "Extract an operational backlog from this audit review and prioritize the next steps.",
                "Summarize open actions, missing evidence and approval gates before execution starts.",
            ],
            expected_outputs=[
                "Operational backlog",
                "Owners and due dates",
                "Evidence gaps and blockers",
                "Action Plan deck artifact",
            ],
            workflow_contract=WORKFLOW_CONTRACT_DOCS["action_plan_evidence_review"],
        ),
        "candidate_review": ProductWorkflowDefinition(
            workflow_id="candidate_review",
            label="Candidate Review",
            headline="Summarize candidate fit, strengths and gaps for hiring decisions.",
            description="Analyze a CV into a hiring-friendly review with strengths, gaps, experience signals and recommendation.",
            required_document_count_min=1,
            required_document_count_max=1,
            default_export_kind=CANDIDATE_REVIEW_EXPORT_KIND,
            default_export_label=EXECUTIVE_DECK_EXPORT_KIND_LABELS.get(CANDIDATE_REVIEW_EXPORT_KIND),
            backend_task_types=["cv_analysis"],
            badge_items=["Hiring", "Grounded", "Executive-ready"],
            preferred_context_strategy="document_scan",
            input_placeholder="Add hiring context, target role, seniority expectations or signals to validate in the candidate review.",
            example_prompts=[
                "Evaluate this CV for a senior applied AI role and highlight strengths, gaps and interview priorities.",
                "Summarize the candidate fit for hiring discussion, including seniority signals and watchouts.",
                "Produce a hiring-friendly recommendation grounded in the CV evidence only.",
            ],
            expected_outputs=[
                "Candidate profile summary",
                "Strengths and watchouts",
                "Interview next steps",
                "Candidate Review deck artifact",
            ],
            workflow_contract=WORKFLOW_CONTRACT_DOCS["candidate_review"],
        ),
    }


def build_product_workflow_frontend_contract() -> dict[str, Any]:
    catalog = build_product_workflow_catalog()
    return {
        "contract_version": "product_workflows.v1",
        "product_headline": "Decision workflows grounded in documents",
        "workflow_count": len(catalog),
        "executive_deck_catalog": [
            {"export_kind": export_kind, "label": label}
            for export_kind, label in EXECUTIVE_DECK_EXPORT_KIND_LABELS.items()
        ],
        "workflows": [
            {
                "workflow_id": workflow_id,
                **definition.model_dump(mode="json"),
            }
            for workflow_id, definition in catalog.items()
        ],
    }


def _load_current_rag_index(rag_settings: RagSettings) -> dict[str, object] | None:
    return normalize_rag_index(load_rag_store(rag_settings.store_path), rag_settings)


def list_product_documents(rag_settings: RagSettings) -> list[ProductDocumentRef]:
    rag_index = _load_current_rag_index(rag_settings)
    documents = get_indexed_documents(rag_index, rag_settings) if rag_index else []
    normalized: list[ProductDocumentRef] = []
    for document in documents:
        loader_metadata = document.get("loader_metadata") if isinstance(document.get("loader_metadata"), dict) else {}
        normalized.append(
            ProductDocumentRef(
                document_id=str(document.get("document_id") or document.get("file_hash") or "document"),
                name=str(document.get("name") or "document"),
                file_type=str(document.get("file_type") or "").strip() or None,
                char_count=int(document.get("char_count") or 0),
                chunk_count=int(document.get("chunk_count") or 0),
                indexed_at=str(document.get("indexed_at") or "").strip() or None,
                loader_strategy_label=str(loader_metadata.get("loader_strategy_label") or loader_metadata.get("strategy_label") or "").strip() or None,
            )
        )
    return normalized


def index_loaded_documents(
    documents: list[LoadedDocument],
    *,
    rag_settings: RagSettings,
    provider_registry: dict[str, dict[str, object]],
) -> tuple[list[ProductDocumentRef], dict[str, object]]:
    if not documents:
        return list_product_documents(rag_settings), {"ok": False, "message": "No documents were provided for indexing."}
    runtime_profile = resolve_provider_runtime_profile(
        provider_registry,
        rag_settings.embedding_provider,
        capability="embeddings",
        fallback_provider="ollama",
    )
    embedding_provider = runtime_profile.get("provider_instance")
    if embedding_provider is None:
        raise RuntimeError("No embedding provider is available to index the uploaded documents.")
    rag_index = _load_current_rag_index(rag_settings)
    updated_index, sync_status = upsert_documents_in_rag_index(
        documents=documents,
        settings=rag_settings,
        embedding_provider=embedding_provider,
        rag_index=rag_index,
    )
    save_rag_store(rag_settings.store_path, updated_index)
    documents_after = list_product_documents(rag_settings)
    return documents_after, {
        "ok": True,
        "message": f"{len(documents)} document(s) indexed successfully.",
        "embedding_provider": runtime_profile.get("effective_provider"),
        "sync_status": sync_status,
    }


def build_grounding_preview(
    *,
    query: str,
    document_ids: list[str],
    strategy: str,
) -> GroundingPreview:
    preview_text = build_structured_document_context(
        query=query,
        document_ids=document_ids,
        strategy=strategy,
    )
    warnings: list[str] = []
    if not preview_text:
        warnings.append("No grounded context could be assembled with the current document selection.")
    if len(document_ids) > 3:
        warnings.append("Multiple documents selected: review the preview carefully before running the workflow.")
    return GroundingPreview(
        strategy=strategy,
        document_ids=list(document_ids),
        context_chars=len(preview_text),
        source_block_count=preview_text.count("[Source:"),
        preview_text=preview_text,
        warnings=warnings,
    )


def _default_context_strategy(workflow_id: ProductWorkflowId, input_text: str) -> str:
    definition = build_product_workflow_catalog().get(workflow_id)
    if definition is not None:
        return definition.preferred_context_strategy
    if workflow_id == "policy_contract_comparison" and input_text.strip():
        return "retrieval"
    if workflow_id == "document_review" and input_text.strip():
        return "retrieval"
    return "document_scan"


def _build_document_agent_workflow_telemetry(workflow_id: ProductWorkflowId) -> dict[str, object]:
    defaults = DOCUMENT_AGENT_WORKFLOW_DEFAULTS.get(workflow_id)
    if not isinstance(defaults, dict):
        return {}
    reason = f"product_workflow_default:{workflow_id}"
    return {
        **defaults,
        "agent_intent_reason": reason,
        "agent_tool_reason": reason,
    }


def _clean_candidate_text(value: object) -> str | None:
    cleaned = " ".join(str(value or "").split()).strip()
    return cleaned or None


def _dedupe_candidate_texts(values: list[object], *, limit: int = 8) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_candidate_text(value)
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


def _candidate_signal_haystack(payload: CVAnalysisPayload) -> str:
    fragments: list[str] = []
    for values in (
        payload.skills,
        payload.languages,
        payload.strengths,
        payload.improvement_areas,
        payload.projects,
    ):
        fragments.extend(str(item or "") for item in (values or []))
    for entry in payload.experience_entries:
        fragments.extend(
            [
                str(entry.title or ""),
                str(entry.organization or ""),
                str(entry.location or ""),
                str(entry.date_range or ""),
                str(entry.description or ""),
                *(str(item or "") for item in (entry.bullets or [])),
            ]
        )
    return " ".join(fragments).lower()


def _candidate_has_signal(payload: CVAnalysisPayload, keywords: tuple[str, ...]) -> bool:
    haystack = _candidate_signal_haystack(payload)
    return any(keyword in haystack for keyword in keywords)


def _candidate_name(payload: CVAnalysisPayload) -> str:
    personal_info = payload.personal_info
    return _clean_candidate_text(getattr(personal_info, "full_name", None)) or "Candidate"


def _candidate_location(payload: CVAnalysisPayload) -> str | None:
    personal_info = payload.personal_info
    return _clean_candidate_text(getattr(personal_info, "location", None))


def _candidate_headline(payload: CVAnalysisPayload) -> str:
    primary_role = next(
        (
            title
            for title in (_clean_candidate_text(entry.title) for entry in payload.experience_entries)
            if title
        ),
        None,
    )
    core_skills = _dedupe_candidate_texts(list(payload.skills or []), limit=3)
    if primary_role and core_skills:
        return f"{primary_role} · {', '.join(core_skills[:2])}"
    if primary_role:
        return primary_role
    if core_skills:
        return ", ".join(core_skills)
    return "Profile under review"


def _candidate_seniority_band(payload: CVAnalysisPayload) -> str:
    years = float(payload.experience_years or 0.0)
    if years >= 8:
        return "senior-to-lead"
    if years >= 5:
        return "senior"
    if years >= 3:
        return "mid-level"
    if years > 0:
        return "early-career"
    if len(payload.experience_entries or []) >= 2:
        return "experienced"
    return "emerging"


def _candidate_seniority_signals(payload: CVAnalysisPayload) -> list[str]:
    years = float(payload.experience_years or 0.0)
    has_leadership = _candidate_has_signal(
        payload,
        ("lead", "leader", "leadership", "manager", "head", "principal", "staff", "ownership", "owner", "mentor"),
    )
    has_product = _candidate_has_signal(
        payload,
        ("product", "stakeholder", "customer", "business", "roadmap", "strategy"),
    )
    has_scale = _candidate_has_signal(
        payload,
        (
            "production",
            "scale",
            "scalability",
            "architecture",
            "platform",
            "deployment",
            "observability",
            "mlops",
            "rag",
            "eval",
        ),
    )
    signals: list[object] = []
    if years >= 8:
        signals.append(f"Career depth suggests senior / lead-level scope with roughly {years:.1f} years of grounded experience.")
    elif years >= 5:
        signals.append(f"Grounded experience suggests a solid senior execution profile ({years:.1f} years).")
    elif years >= 3:
        signals.append(f"The profile shows intermediate execution depth across roughly {years:.1f} years of experience.")
    if len(payload.experience_entries or []) >= 3:
        signals.append("Multiple structured roles are present, which suggests visible career progression.")
    if has_leadership:
        signals.append("Leadership / ownership language appears explicitly in the role history or strengths.")
    if has_product:
        signals.append("Product or stakeholder-facing work is visible in the current CV evidence.")
    if has_scale:
        signals.append("The CV references technical depth, platform work, or production-scale delivery signals.")
    if len(payload.languages or []) >= 2:
        signals.append("More than one language is listed, which broadens communication coverage.")
    return _dedupe_candidate_texts(signals, limit=4)


def _candidate_watchouts(payload: CVAnalysisPayload) -> list[str]:
    has_leadership = _candidate_has_signal(
        payload,
        ("lead", "leader", "leadership", "manager", "head", "principal", "staff", "ownership", "owner", "mentor"),
    )
    has_product = _candidate_has_signal(
        payload,
        ("product", "stakeholder", "customer", "business", "roadmap", "strategy"),
    )
    watchouts: list[object] = [*(payload.improvement_areas or [])]
    if not payload.experience_entries:
        watchouts.append("Experience history is sparse or weakly structured in the current CV grounding.")
    if not payload.skills:
        watchouts.append("The CV exposes limited explicit skill evidence for a confident fit assessment.")
    if float(payload.experience_years or 0.0) < 2 and payload.experience_entries:
        watchouts.append("Seniority should be validated against autonomy, ownership and delivery complexity.")
    if payload.experience_entries and not has_leadership:
        watchouts.append("Leadership and ownership signals are not yet explicit in the current CV.")
    if payload.experience_entries and not has_product:
        watchouts.append("Product thinking / stakeholder management should be validated with concrete examples.")
    return _dedupe_candidate_texts(watchouts, limit=5)


def _candidate_next_steps(payload: CVAnalysisPayload) -> list[str]:
    watchouts = _candidate_watchouts(payload)
    next_steps: list[object] = []
    for item in watchouts[:2]:
        cleaned = _clean_candidate_text(item)
        if not cleaned:
            continue
        normalized = cleaned.rstrip(".")
        lowered = normalized.lower()
        if lowered.startswith(("validate", "confirm", "probe", "assess", "review")):
            next_steps.append(normalized)
        else:
            next_steps.append(f"Validate {normalized[0].lower() + normalized[1:]}")
    if _candidate_has_signal(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        next_steps.append("Probe measurable scope, business impact and decision-making ownership in the next interview.")
    else:
        next_steps.append("Run a focused interview on leadership, ownership and stakeholder management examples.")
    if _candidate_has_signal(payload, ("production", "scale", "architecture", "platform", "rag", "mlops", "eval")):
        next_steps.append("Validate production depth, architecture trade-offs and delivery at scale with concrete scenarios.")
    else:
        next_steps.append("Use a technical screen to validate delivery depth, implementation quality and problem-solving range.")
    return _dedupe_candidate_texts(next_steps, limit=4)


def _candidate_operational_warnings(payload: CVAnalysisPayload) -> list[str]:
    warnings: list[object] = []
    if _candidate_name(payload) == "Candidate":
        warnings.append("Candidate name could not be confidently extracted from the current CV.")
    if not payload.experience_entries:
        warnings.append("The CV does not expose structured experience entries, so fit assessment remains partially constrained.")
    if not payload.skills:
        warnings.append("The CV exposes too few explicit skills for a confident fit assessment.")
    if float(payload.experience_years or 0.0) <= 0 and not payload.experience_entries:
        warnings.append("Seniority evidence is too thin in the current CV grounding.")
    if len(payload.improvement_areas or []) >= 4:
        warnings.append("Several relevant gaps still require manual validation before advancing this profile.")
    if not (payload.strengths or []) and len(payload.skills or []) < 2:
        warnings.append("Grounded differentiation is limited; use interview evidence before making a hiring recommendation.")
    return _dedupe_candidate_texts(warnings, limit=4)


def _candidate_recommendation(payload: CVAnalysisPayload) -> str:
    strengths = len(payload.strengths or [])
    skills = len(payload.skills or [])
    years = float(payload.experience_years or 0.0)
    experience_entries = len(payload.experience_entries or [])
    gaps = len(payload.improvement_areas or [])
    positive_score = 0
    risk_score = 0

    if years >= 7:
        positive_score += 2
    elif years >= 3:
        positive_score += 1
    if experience_entries >= 2:
        positive_score += 1
    if strengths:
        positive_score += 1
    if skills >= 4:
        positive_score += 1
    if _candidate_has_signal(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership", "principal", "staff")):
        positive_score += 1
    if _candidate_has_signal(payload, ("product", "stakeholder", "customer", "business", "roadmap", "strategy")):
        positive_score += 1
    if _candidate_has_signal(payload, ("production", "scale", "architecture", "platform", "mlops", "rag", "eval")):
        positive_score += 1

    if not payload.experience_entries:
        risk_score += 2
    if not payload.skills:
        risk_score += 1
    if years > 0 and years < 2:
        risk_score += 1
    if gaps >= max(strengths + 2, 3):
        risk_score += 2
    if not _candidate_has_signal(payload, ("lead", "leader", "leadership", "manager", "owner", "ownership")):
        risk_score += 1

    if positive_score >= 4 and risk_score <= 1 and gaps <= max(strengths + 1, 2):
        return "Advance the candidate to the next stage with focused validation of leadership, scope and business impact." 
    if positive_score >= 3 and risk_score <= 3:
        return "Keep the candidate in the active pipeline and run a targeted interview on ownership, stakeholder management and delivery depth."
    return "Hold before advancing and validate the current gaps with a focused technical and hiring screen."


def _candidate_summary(payload: CVAnalysisPayload) -> str:
    name = _candidate_name(payload)
    location = _candidate_location(payload)
    headline = _candidate_headline(payload)
    seniority_band = _candidate_seniority_band(payload)
    years = float(payload.experience_years or 0.0)
    experience_entries = len(payload.experience_entries or [])
    strengths = _dedupe_candidate_texts(list(payload.strengths or []), limit=2)
    watchouts = _candidate_watchouts(payload)
    top_skills = _dedupe_candidate_texts(list(payload.skills or []), limit=3)

    opening = f"{name} currently reads as a {seniority_band} hiring profile"
    if location:
        opening += f" based in {location}"
    if headline and headline != "Profile under review":
        opening += f", with strongest evidence around {headline}"
    opening += "."

    evidence = "The CV exposes limited explicit duration signals"
    if years > 0:
        evidence = f"The CV shows about {years:.1f} year(s) of grounded experience"
    if experience_entries:
        evidence += f" across {experience_entries} structured role(s)"
    if top_skills:
        evidence += f", with core skills in {', '.join(top_skills)}"
    evidence += "."

    trailing: list[str] = []
    if strengths:
        trailing.append(f"Top positive signals: {'; '.join(strengths)}.")
    if watchouts:
        trailing.append(f"Main validation area: {watchouts[0]}.")
    return " ".join([opening, evidence, *trailing]).strip()


def _build_recommendation(payload: object, workflow_id: ProductWorkflowId) -> str | None:
    if isinstance(payload, DocumentAgentPayload):
        if payload.recommended_actions:
            return payload.recommended_actions[0]
        if workflow_id == "policy_contract_comparison":
            return "Validate the critical differences with a final human review before making the decision."
        return "Use the grounded findings to drive the next human review step."
    if isinstance(payload, CVAnalysisPayload):
        return _candidate_recommendation(payload)
    return None


def _summarize_payload(
    *,
    workflow_id: ProductWorkflowId,
    structured_result: StructuredResult,
) -> tuple[str, list[str], str | None, list[str]]:
    payload = structured_result.validated_output
    warnings: list[str] = []
    if not structured_result.success:
        warnings.extend(
            [
                item
                for item in [
                    structured_result.validation_error,
                    structured_result.parsing_error,
                    structured_result.error.message if structured_result.error else None,
                ]
                if item
            ]
        )
        return (structured_result.raw_output_text or "The workflow could not produce a validated structured result.").strip(), [], None, warnings

    if isinstance(payload, DocumentAgentPayload):
        highlights = list(payload.key_points or [])
        if workflow_id == "policy_contract_comparison":
            highlights.extend(finding.title for finding in payload.comparison_findings)
        warnings.extend(list(payload.limitations or []))
        if payload.needs_review and payload.needs_review_reason:
            warnings.insert(0, payload.needs_review_reason)
        return payload.summary, highlights[:6], _build_recommendation(payload, workflow_id), warnings

    if isinstance(payload, CVAnalysisPayload):
        summary = _candidate_summary(payload)
        highlights = _dedupe_candidate_texts(
            [
                *(payload.strengths or []),
                *_candidate_seniority_signals(payload),
                *(payload.skills or []),
            ],
            limit=6,
        )
        warnings.extend(_candidate_operational_warnings(payload))
        return summary, highlights[:6], _build_recommendation(payload, workflow_id), warnings

    summary = structured_result.raw_output_text or "Structured result generated successfully."
    return summary.strip(), [], None, warnings


def _run_structured_product_workflow(
    request: ProductWorkflowRequest,
    *,
    task_type: str,
    workflow_label: str,
    deck_export_kind: str | None,
) -> ProductWorkflowResult:
    workflow_definition = build_product_workflow_catalog()[request.workflow_id]
    effective_query = request.input_text.strip() or DEFAULT_WORKFLOW_QUERIES[request.workflow_id]
    strategy = request.context_strategy or _default_context_strategy(request.workflow_id, effective_query)
    grounding_preview = build_grounding_preview(query=effective_query, document_ids=request.document_ids, strategy=strategy)
    telemetry: dict[str, object] = {
        "product_workflow_id": request.workflow_id,
        "product_workflow_label": workflow_label,
        "product_surface": "gradio",
        "product_workflow_contract": workflow_definition.workflow_contract,
        "product_workflow_expected_outputs": list(workflow_definition.expected_outputs),
        "product_deck_export_kind": deck_export_kind,
    }
    if task_type == "document_agent":
        telemetry.update(_build_document_agent_workflow_telemetry(request.workflow_id))
    structured_request = TaskExecutionRequest(
        task_type=task_type,
        input_text=effective_query,
        use_rag_context=False,
        use_document_context=bool(request.use_document_context and request.document_ids),
        source_document_ids=list(request.document_ids),
        context_strategy=strategy,
        provider=request.provider,
        model=request.model,
        temperature=request.temperature,
        context_window=(request.context_window if request.context_window_mode == "manual" else None),
        telemetry=telemetry,
    )
    structured_result = run_structured_execution_workflow(
        structured_request,
        strategy="langgraph_context_retry" if task_type == "document_agent" else "direct",
    )
    summary, highlights, recommendation, warnings = _summarize_payload(
        workflow_id=request.workflow_id,
        structured_result=structured_result,
    )
    status = "completed" if structured_result.success else "error"
    if status == "completed" and warnings:
        status = "warning"
    if request.workflow_id == "candidate_review" and len(request.document_ids) > 1:
        warnings.insert(0, "Candidate Review is designed for one CV at a time.")
        status = "warning"
    return ProductWorkflowResult(
        workflow_id=request.workflow_id,
        workflow_label=workflow_label,
        status=status,
        summary=summary,
        highlights=highlights,
        recommendation=recommendation,
        structured_result=structured_result,
        grounding_preview=grounding_preview,
        artifacts=[],
        deck_export_kind=deck_export_kind,
        deck_available=bool(deck_export_kind and structured_result.success),
        warnings=warnings,
        debug_metadata={
            "task_type": task_type,
            "provider": request.provider,
            "model": request.model,
            "context_strategy": strategy,
            "source_documents": list(request.document_ids),
            "workflow_contract": workflow_definition.workflow_contract,
            "expected_outputs": list(workflow_definition.expected_outputs),
            "preferred_context_strategy": workflow_definition.preferred_context_strategy,
            "deck_export_label": workflow_definition.default_export_label,
        },
    )


def run_document_review_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult:
    return _run_structured_product_workflow(
        request,
        task_type="document_agent",
        workflow_label="Document Review",
        deck_export_kind=DOCUMENT_REVIEW_EXPORT_KIND,
    )


def run_policy_contract_comparison_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult:
    return _run_structured_product_workflow(
        request,
        task_type="document_agent",
        workflow_label="Policy / Contract Comparison",
        deck_export_kind=POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
    )


def run_action_plan_evidence_review_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult:
    return _run_structured_product_workflow(
        request,
        task_type="document_agent",
        workflow_label="Action Plan / Evidence Review",
        deck_export_kind=ACTION_PLAN_EXPORT_KIND,
    )


def run_candidate_review_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult:
    return _run_structured_product_workflow(
        request,
        task_type="cv_analysis",
        workflow_label="Candidate Review",
        deck_export_kind=CANDIDATE_REVIEW_EXPORT_KIND,
    )


def run_product_workflow(request: ProductWorkflowRequest) -> ProductWorkflowResult:
    if request.workflow_id == "document_review":
        return run_document_review_workflow(request)
    if request.workflow_id == "policy_contract_comparison":
        return run_policy_contract_comparison_workflow(request)
    if request.workflow_id == "action_plan_evidence_review":
        return run_action_plan_evidence_review_workflow(request)
    return run_candidate_review_workflow(request)


def _artifact_or_none(artifact_type: str, label: str, path_value: object) -> ProductArtifact | None:
    normalized = str(path_value or "").strip()
    if not normalized:
        return None
    path = Path(normalized)
    if not path.exists() or not path.is_file():
        return None
    return ProductArtifact(
        artifact_type=artifact_type,  # type: ignore[arg-type]
        label=label,
        path=str(path),
        download_name=path.name,
        available=True,
    )


def generate_product_workflow_deck(
    result: ProductWorkflowResult,
    *,
    settings: PresentationExportSettings,
    workspace_root: Path | None = None,
) -> tuple[dict[str, Any], list[ProductArtifact]]:
    if not result.deck_export_kind:
        raise ValueError("This workflow does not expose a deck export kind.")
    export_result = generate_executive_deck(
        export_kind=result.deck_export_kind,
        structured_result=result.structured_result,
        phase95_evidenceops_worklog_path=get_phase95_evidenceops_worklog_path(workspace_root or BASE_DIR),
        phase95_evidenceops_action_store_path=get_phase95_evidenceops_action_store_path(workspace_root or BASE_DIR),
        settings=settings,
    )
    artifacts = [
        artifact
        for artifact in [
            _artifact_or_none("pptx", "Presentation deck (.pptx)", export_result.get("local_pptx_path")),
            _artifact_or_none("contract_json", "Contract JSON", export_result.get("local_contract_path")),
            _artifact_or_none("payload_json", "Renderer payload JSON", export_result.get("local_payload_path")),
            _artifact_or_none("review_json", "Review JSON", export_result.get("local_review_path")),
            _artifact_or_none("preview_manifest_json", "Preview manifest JSON", export_result.get("local_preview_manifest_path")),
            _artifact_or_none("thumbnail_sheet", "Thumbnail sheet", export_result.get("local_thumbnail_sheet_path")),
        ]
        if artifact is not None
    ]
    return export_result, artifacts