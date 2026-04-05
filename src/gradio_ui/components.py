from __future__ import annotations

from html import escape

from src.product.models import GroundingPreview, ProductWorkflowDefinition, ProductWorkflowResult


def build_topbar_html(*, app_name: str, show_ai_lab_entry: bool = True) -> str:
    link_html = (
        '<a class="product-link-pill" href="./main_qwen.py" target="_blank">Open AI Lab</a>'
        if show_ai_lab_entry
        else ""
    )
    return f"""
    <div class="product-topbar product-shell">
      <div>
        <div class="product-topbar__eyebrow">AI Workbench Product</div>
        <div class="product-topbar__title">{escape(app_name)}</div>
        <div class="product-topbar__hint">Decision workflows grounded in documents</div>
      </div>
      <div>{link_html}</div>
    </div>
    """


def build_hero_html() -> str:
    return """
    <div class="product-hero product-shell">
      <div class="product-panel product-panel--strong">
        <div class="product-hero__eyebrow">AI-first product surface</div>
        <h1 class="product-hero__title">Turn documents into grounded decisions, actions and executive-ready outputs.</h1>
        <div class="product-hero__subtitle">
          Review, compare, extract actions and evaluate candidates with workflows that stay grounded in source material while producing handoff-ready outputs.
        </div>
        <div class="product-chip-row">
          <div class="product-chip">Grounded outputs</div>
          <div class="product-chip">Structured workflows</div>
          <div class="product-chip">Executive-ready artifacts</div>
        </div>
      </div>
      <div class="product-panel">
        <div class="product-hero-stat">
          <div class="product-hero-stat__label">Core workflows</div>
          <div class="product-hero-stat__value">4</div>
        </div>
        <div class="product-hero-stat">
          <div class="product-hero-stat__label">Product reading</div>
          <div class="product-hero-stat__value">Grounded decision support</div>
        </div>
        <div class="product-hero-stat">
          <div class="product-hero-stat__label">Surface split</div>
          <div class="product-hero-stat__value">Product + AI Lab</div>
        </div>
      </div>
    </div>
    """


def build_workflow_cards_html(
    workflow_catalog: dict[str, ProductWorkflowDefinition],
    *,
    active_workflow: str | None,
) -> str:
    cards = []
    for workflow_id, definition in workflow_catalog.items():
        active_class = " product-workflow-card--active" if workflow_id == active_workflow else ""
        bullets = "".join(f"<li>{escape(item)}</li>" for item in definition.badge_items[:3])
        cards.append(
            f"""
            <div class="product-workflow-card{active_class}">
              <div class="product-workflow-card__title">{escape(definition.label)}</div>
              <div class="product-workflow-card__headline">{escape(definition.headline)}</div>
              <ul class="product-workflow-card__list">{bullets}</ul>
            </div>
            """
        )
    return f'<div class="product-workflow-card-grid product-shell">{"".join(cards)}</div>'


def build_workflow_detail_html(definition: ProductWorkflowDefinition, *, selected_documents: int = 0) -> str:
    doc_rule = f"Min docs: {definition.required_document_count_min}"
    if definition.required_document_count_max is not None:
        doc_rule += f" · Max docs: {definition.required_document_count_max}"
    return f"""
    <div class="product-panel product-shell">
      <div class="product-section-title">{escape(definition.label)}</div>
      <div class="product-section-subtitle">{escape(definition.description)}</div>
      <div class="product-chip-row">
        <div class="product-chip">{escape(doc_rule)}</div>
        <div class="product-chip">Selected docs: {selected_documents}</div>
        <div class="product-chip">Deck-ready: {'Yes' if definition.default_export_kind else 'No'}</div>
      </div>
    </div>
    """


def build_grounding_preview_html(preview: GroundingPreview | None) -> str:
    if preview is None:
        return '<div class="product-empty-state">No grounding preview has been generated yet.</div>'
    warnings_html = "".join(f"<li>{escape(item)}</li>" for item in preview.warnings)
    warning_block = f"<ul class=\"product-workflow-card__list\">{warnings_html}</ul>" if warnings_html else ""
    return f"""
    <div class="product-panel">
      <div class="product-section-title">Grounding preview</div>
      <div class="product-section-subtitle">Review the actual context that will be sent to the workflow before running it.</div>
      <div class="product-chip-row">
        <div class="product-chip">Strategy: {escape(preview.strategy)}</div>
        <div class="product-chip">Documents: {len(preview.document_ids)}</div>
        <div class="product-chip">Chars: {preview.context_chars}</div>
        <div class="product-chip">Source blocks: {preview.source_block_count}</div>
      </div>
      {warning_block}
    </div>
    """


def build_result_summary_html(result: ProductWorkflowResult | None) -> str:
    if result is None:
        return '<div class="product-empty-state">Run a workflow to see grounded findings, actions and artifacts here.</div>'
    status_class = f"product-status-pill product-status-pill--{escape(result.status)}"
    recommendation_html = (
        f"<div class=\"product-section-subtitle\"><strong>Recommendation:</strong> {escape(result.recommendation)}</div>"
        if result.recommendation
        else ""
    )
    return f"""
    <div class="product-panel product-panel--strong">
      <div class="{status_class}">{escape(result.workflow_label)} · {escape(result.status.title())}</div>
      <div class="product-section-title">Decision-ready summary</div>
      <div class="product-section-subtitle">{escape(result.summary)}</div>
      {recommendation_html}
    </div>
    """


def build_credibility_band_html() -> str:
    return """
    <div class="product-panel product-shell">
      <div class="product-proof-row">
        <div class="product-proof-chip">Grounded by document context</div>
        <div class="product-proof-chip">Structured outputs</div>
        <div class="product-proof-chip">Actionable recommendations</div>
        <div class="product-proof-chip">Product + AI Lab split</div>
      </div>
    </div>
    """