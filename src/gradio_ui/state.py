from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from src.product.models import ProductWorkflowId, ProductWorkflowResult


@dataclass
class ProductSessionState:
    selected_workflow: ProductWorkflowId
    indexed_document_ids: list[str] = field(default_factory=list)
    latest_result: ProductWorkflowResult | None = None
    latest_deck_result: dict[str, Any] | None = None
    last_error: str | None = None


def create_initial_product_state(default_workflow: ProductWorkflowId) -> ProductSessionState:
    return ProductSessionState(selected_workflow=default_workflow)


def update_product_state(state: ProductSessionState | None, **changes) -> ProductSessionState:
    current = state if isinstance(state, ProductSessionState) else create_initial_product_state("document_review")
    return replace(current, **changes)