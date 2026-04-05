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
    POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
)
from src.services.presentation_export_service import generate_executive_deck
from src.storage.rag_store import load_rag_store, save_rag_store
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


def build_product_workflow_catalog() -> dict[ProductWorkflowId, ProductWorkflowDefinition]:
    return {
        "document_review": ProductWorkflowDefinition(
            workflow_id="document_review",
            label="Document Review",
            headline="Grounded review of key findings, risks and next actions.",
            description="Summarize complex documents into review-ready findings, risks, gaps and recommended next steps.",
            required_document_count_min=1,
            default_export_kind=DOCUMENT_REVIEW_EXPORT_KIND,
            backend_task_types=["document_agent", "summary", "extraction"],
            badge_items=["Grounded", "Structured", "Deck-ready"],
        ),
        "policy_contract_comparison": ProductWorkflowDefinition(
            workflow_id="policy_contract_comparison",
            label="Policy / Contract Comparison",
            headline="Compare versions, surface impact and support a grounded decision.",
            description="Identify the most relevant differences between documents and frame their business impact with evidence.",
            required_document_count_min=2,
            default_export_kind=POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
            backend_task_types=["document_agent"],
            badge_items=["Comparison", "Grounded", "Decision-ready"],
        ),
        "action_plan_evidence_review": ProductWorkflowDefinition(
            workflow_id="action_plan_evidence_review",
            label="Action Plan / Evidence Review",
            headline="Turn findings into owners, deadlines and operational follow-up.",
            description="Extract actionable next steps, operational backlog and evidence-backed follow-up guidance.",
            required_document_count_min=1,
            default_export_kind=ACTION_PLAN_EXPORT_KIND,
            backend_task_types=["document_agent", "checklist"],
            badge_items=["Actionable", "Operational", "Evidence-backed"],
        ),
        "candidate_review": ProductWorkflowDefinition(
            workflow_id="candidate_review",
            label="Candidate Review",
            headline="Summarize candidate fit, strengths and gaps for hiring decisions.",
            description="Analyze a CV into a hiring-friendly review with strengths, gaps, experience signals and recommendation.",
            required_document_count_min=1,
            required_document_count_max=1,
            default_export_kind=CANDIDATE_REVIEW_EXPORT_KIND,
            backend_task_types=["cv_analysis"],
            badge_items=["Hiring", "Grounded", "Executive-ready"],
        ),
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
    if workflow_id == "policy_contract_comparison" and input_text.strip():
        return "retrieval"
    if workflow_id == "document_review" and input_text.strip():
        return "retrieval"
    return "document_scan"


def _build_recommendation(payload: object, workflow_id: ProductWorkflowId) -> str | None:
    if isinstance(payload, DocumentAgentPayload):
        if payload.recommended_actions:
            return payload.recommended_actions[0]
        if workflow_id == "policy_contract_comparison":
            return "Validate the critical differences with a final human review before making the decision."
        return "Use the grounded findings to drive the next human review step."
    if isinstance(payload, CVAnalysisPayload):
        if len(payload.strengths or []) >= len(payload.improvement_areas or []):
            return "Advance the candidate with a focused validation of ownership, scope and leadership signals."
        return "Keep the candidate under review until the identified gaps are clarified."
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
        candidate_name = payload.personal_info.full_name if payload.personal_info else None
        summary = (
            f"{candidate_name or 'Candidate'} presents {payload.experience_years:.1f} estimated year(s) of experience, "
            f"{len(payload.skills or [])} mapped skill(s) and {len(payload.experience_entries or [])} structured experience entries."
        )
        highlights = [*(payload.strengths or []), *(payload.skills or [])]
        warnings.extend(list(payload.improvement_areas or []))
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
    effective_query = request.input_text.strip() or DEFAULT_WORKFLOW_QUERIES[request.workflow_id]
    strategy = request.context_strategy or _default_context_strategy(request.workflow_id, effective_query)
    grounding_preview = build_grounding_preview(query=effective_query, document_ids=request.document_ids, strategy=strategy)
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
        telemetry={
            "product_workflow_id": request.workflow_id,
            "product_surface": "gradio",
        },
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
        phase95_evidenceops_worklog_path=(workspace_root or BASE_DIR) / ".phase95_evidenceops_worklog.json",
        phase95_evidenceops_action_store_path=(workspace_root or BASE_DIR) / ".phase95_evidenceops_actions.sqlite3",
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