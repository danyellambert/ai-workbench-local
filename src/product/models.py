from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.structured.envelope import StructuredResult

ProductWorkflowId = Literal[
    "document_review",
    "policy_contract_comparison",
    "action_plan_evidence_review",
    "candidate_review",
]

PRODUCT_WORKFLOW_IDS: tuple[ProductWorkflowId, ...] = (
    "document_review",
    "policy_contract_comparison",
    "action_plan_evidence_review",
    "candidate_review",
)


class ProductWorkflowDefinition(BaseModel):
    workflow_id: ProductWorkflowId
    label: str
    headline: str
    description: str
    required_document_count_min: int = 1
    required_document_count_max: int | None = None
    supports_optional_prompt: bool = True
    default_export_kind: str | None = None
    backend_task_types: list[str] = Field(default_factory=list)
    badge_items: list[str] = Field(default_factory=list)


class ProductDocumentRef(BaseModel):
    document_id: str
    name: str
    file_type: str | None = None
    char_count: int = 0
    chunk_count: int = 0
    indexed_at: str | None = None
    loader_strategy_label: str | None = None


class GroundingPreview(BaseModel):
    strategy: str
    document_ids: list[str] = Field(default_factory=list)
    context_chars: int = 0
    source_block_count: int = 0
    preview_text: str = ""
    warnings: list[str] = Field(default_factory=list)


class ProductArtifact(BaseModel):
    artifact_type: Literal["pptx", "contract_json", "payload_json", "review_json", "preview_manifest_json", "thumbnail_sheet"]
    label: str
    path: str | None = None
    download_name: str | None = None
    available: bool = False


class ProductWorkflowRequest(BaseModel):
    workflow_id: ProductWorkflowId
    document_ids: list[str] = Field(default_factory=list)
    input_text: str = ""
    provider: str = "ollama"
    model: str | None = None
    temperature: float = 0.2
    context_window_mode: Literal["auto", "manual"] = "auto"
    context_window: int | None = None
    use_document_context: bool = True
    context_strategy: Literal["document_scan", "retrieval"] = "document_scan"

    @model_validator(mode="after")
    def validate_constraints(self) -> "ProductWorkflowRequest":
        document_count = len(self.document_ids)
        if self.workflow_id == "policy_contract_comparison" and document_count < 2:
            raise ValueError("Policy / Contract Comparison requires at least 2 documents.")
        if self.workflow_id in {"document_review", "candidate_review"} and document_count < 1:
            raise ValueError(f"{self.workflow_id} requires at least 1 document.")
        if self.workflow_id == "candidate_review" and document_count > 1:
            raise ValueError("Candidate Review should run with a single CV at a time.")
        if self.workflow_id == "action_plan_evidence_review" and document_count < 1 and not self.input_text.strip():
            raise ValueError("Action Plan / Evidence Review requires at least one document or explicit input text.")
        if self.context_window_mode == "manual" and self.context_window is not None and self.context_window < 1024:
            raise ValueError("Manual context window must be at least 1024.")
        return self


class ProductWorkflowResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workflow_id: ProductWorkflowId
    workflow_label: str
    status: Literal["completed", "warning", "error"] = "completed"
    summary: str
    highlights: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    structured_result: StructuredResult | None = None
    grounding_preview: GroundingPreview | None = None
    artifacts: list[ProductArtifact] = Field(default_factory=list)
    deck_export_kind: str | None = None
    deck_available: bool = False
    warnings: list[str] = Field(default_factory=list)
    debug_metadata: dict[str, Any] = Field(default_factory=dict)