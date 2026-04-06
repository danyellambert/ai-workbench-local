from __future__ import annotations

from html import escape
from typing import Any

from src.product.models import GroundingPreview, ProductWorkflowDefinition, ProductWorkflowResult
from src.product.presenters import build_product_result_sections


WORKFLOW_ICONS = {
    "document_review": "📄",
    "policy_contract_comparison": "⚖️",
    "action_plan_evidence_review": "🗂️",
    "candidate_review": "🧑‍💼",
}


def _render_list(items: list[object], *, empty_state: str, limit: int = 4) -> str:
    normalized = [escape(str(item)) for item in items if str(item).strip()]
    if not normalized:
        return f'<div class="product-list-card__empty">{escape(empty_state)}</div>'
    return '<ul class="product-list-card__list">' + "".join(f"<li>{item}</li>" for item in normalized[:limit]) + '</ul>'


def _render_chip_row(values: list[str]) -> str:
    return "".join(f'<div class="product-chip">{escape(value)}</div>' for value in values if str(value).strip())


def build_topbar_html(*, app_name: str, show_ai_lab_entry: bool = True) -> str:
    link_html = (
        '<a class="product-link-pill" href="./main.py" target="_blank">Open AI Lab</a>'
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
        <div class="product-hero__cta-note">Use the workflow cards below to pick a decision flow, attach your documents, preview the grounding and run the analysis.</div>
      </div>
      <div class="product-panel">
        <div class="product-kpi-grid">
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
        icon = WORKFLOW_ICONS.get(workflow_id, "✦")
        cards.append(
            f"""
            <div class="product-workflow-card{active_class}">
              <div class="product-workflow-card__icon">{icon}</div>
              <div class="product-workflow-card__title">{escape(definition.label)}</div>
              <div class="product-workflow-card__headline">{escape(definition.headline)}</div>
              <div class="product-workflow-card__description">{escape(definition.description)}</div>
              <ul class="product-workflow-card__list">{bullets}</ul>
              <div class="product-workflow-card__cta">Select below → add docs → preview grounding → run workflow</div>
            </div>
            """
        )
    return f'<div class="product-workflow-card-grid product-shell">{"".join(cards)}</div>'


def build_how_it_works_html() -> str:
    return """
    <div class="product-how-shell product-shell">
      <div class="product-how-card">
        <div class="product-how-card__step">1</div>
        <div class="product-how-card__title">Pick a workflow</div>
        <div class="product-how-card__body">Choose the decision flow that matches the business problem you want to solve.</div>
      </div>
      <div class="product-how-card">
        <div class="product-how-card__step">2</div>
        <div class="product-how-card__title">Add documents and context</div>
        <div class="product-how-card__body">Index your files, set the workflow instructions and preview the grounded context before execution.</div>
      </div>
      <div class="product-how-card">
        <div class="product-how-card__step">3</div>
        <div class="product-how-card__title">Review outcome and export</div>
        <div class="product-how-card__body">Read findings, evidence and next actions in a decision-ready format, then generate artifacts when needed.</div>
      </div>
    </div>
    """


def build_workflow_detail_html(definition: ProductWorkflowDefinition, *, selected_documents: int = 0) -> str:
    doc_rule = f"Min docs: {definition.required_document_count_min}"
    if definition.required_document_count_max is not None:
        doc_rule += f" · Max docs: {definition.required_document_count_max}"
    task_types = ", ".join(definition.backend_task_types) if definition.backend_task_types else "n/a"
    deck_label = definition.default_export_label or definition.default_export_kind or "No deck export mapped yet"
    prompt_policy = "Optional workflow prompt" if definition.supports_optional_prompt else "Prompt fixed by workflow"
    input_guidance = definition.input_placeholder or "Add business context, constraints or decision criteria for this workflow."
    examples_html = "".join(
        f"<li>{escape(item)}</li>" for item in definition.example_prompts[:3] if str(item).strip()
    ) or "<li>No example prompt registered yet.</li>"
    outputs_html = "".join(
        f"<li>{escape(item)}</li>" for item in definition.expected_outputs[:4] if str(item).strip()
    ) or "<li>No expected outputs registered yet.</li>"
    contract_line = (
        f'<div class="product-section-subtitle"><strong>Workflow contract:</strong> {escape(definition.workflow_contract)}</div>'
        if definition.workflow_contract
        else '<div class="product-section-subtitle"><strong>Workflow contract:</strong> not registered yet</div>'
    )
    return f"""
    <div class="product-panel product-shell">
      <div class="product-section-title">{escape(definition.label)}</div>
      <div class="product-section-subtitle">{escape(definition.description)}</div>
      <div class="product-chip-row">
        <div class="product-chip">{escape(doc_rule)}</div>
        <div class="product-chip">Selected docs: {selected_documents}</div>
        <div class="product-chip">Grounding: {escape(definition.preferred_context_strategy)}</div>
        <div class="product-chip">Engine: {escape(task_types)}</div>
        <div class="product-chip">Deck: {escape(deck_label)}</div>
        <div class="product-chip">{escape(prompt_policy)}</div>
      </div>
      <div class="product-detail-grid">
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Example prompts</strong></div>
          <ul class="product-workflow-card__list">{examples_html}</ul>
        </div>
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Expected outputs</strong></div>
          <ul class="product-workflow-card__list">{outputs_html}</ul>
        </div>
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Input guidance</strong></div>
          <div class="product-section-subtitle">{escape(input_guidance)}</div>
          {contract_line}
        </div>
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
      <div class="product-section-subtitle">This preview shows the exact grounded context that will inform the workflow outcome.</div>
      {warning_block}
    </div>
    """


def build_contract_snapshot_html(contract_entry: dict[str, Any] | None) -> str:
    entry = contract_entry if isinstance(contract_entry, dict) else {}
    expected_outputs = entry.get("expected_outputs") if isinstance(entry.get("expected_outputs"), list) else []
    prompts = entry.get("example_prompts") if isinstance(entry.get("example_prompts"), list) else []
    chip_values = [
        f"Strategy: {entry.get('preferred_context_strategy') or 'n/a'}",
        f"Prompt: {'Optional' if entry.get('supports_optional_prompt', True) else 'Fixed'}",
        f"Deck: {entry.get('default_export_label') or entry.get('default_export_kind') or 'n/a'}",
    ]
    contract_line = escape(str(entry.get("workflow_contract") or "Not registered yet"))
    return f"""
    <div class="product-panel">
      <div class="product-section-title">Workflow contract snapshot</div>
      <div class="product-section-subtitle">A compact frontend contract summary for this workflow. Use the JSON below only when you need the raw payload details.</div>
      <div class="product-chip-row">{_render_chip_row(chip_values)}</div>
      <div class="product-detail-grid">
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Expected outputs</strong></div>
          {_render_list(list(expected_outputs), empty_state="No expected output registered.", limit=4)}
        </div>
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Example prompts</strong></div>
          {_render_list(list(prompts), empty_state="No example prompt registered.", limit=3)}
        </div>
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Contract reference</strong></div>
          <div class="product-section-subtitle">{contract_line}</div>
        </div>
      </div>
    </div>
    """


def build_result_summary_html(result: ProductWorkflowResult | None) -> str:
    if result is None:
        return '<div class="product-empty-state">Run a workflow to see grounded findings, actions and artifacts here.</div>'
    sections = build_product_result_sections(result)
    status_class = f"product-status-pill product-status-pill--{escape(result.status)}"
    recommendation_html = (
        f"<div class=\"product-section-subtitle\"><strong>Recommendation:</strong> {escape(result.recommendation)}</div>"
        if result.recommendation
        else ""
    )

    chip_values = [
        f"Highlights: {len(sections.get('highlights') or [])}",
        f"Watchouts: {len(sections.get('warnings') or [])}",
        f"Artifacts: {len(result.artifacts or [])}",
        f"Deck: {'Ready' if result.deck_available else 'Pending'}",
    ]

    candidate_profile = sections.get("candidate_profile") if isinstance(sections.get("candidate_profile"), dict) else None

    candidate_html = ""
    if candidate_profile:
        chips = [
            f'<div class="product-chip">Candidate: {escape(str(candidate_profile.get("name") or "Candidate"))}</div>',
            f'<div class="product-chip">Headline: {escape(str(candidate_profile.get("headline") or "Profile under review"))}</div>',
            f'<div class="product-chip">Location: {escape(str(candidate_profile.get("location") or "Location not explicit"))}</div>',
        ]
        candidate_html = f"""
          <div class="product-chip-row">{''.join(chips)}</div>
          <div class="product-detail-grid">
            <div class="product-detail-section">
              <div class="product-section-subtitle"><strong>Strengths</strong></div>
              {_render_list(list(sections.get("strengths") or sections.get("highlights") or []), empty_state="No grounded strengths were captured yet.", limit=4)}
            </div>
            <div class="product-detail-section">
              <div class="product-section-subtitle"><strong>Watchouts</strong></div>
              {_render_list(list(sections.get("watchouts") or sections.get("warnings") or []), empty_state="No critical watchout was captured.", limit=4)}
            </div>
            <div class="product-detail-section">
              <div class="product-section-subtitle"><strong>Next steps</strong></div>
              {_render_list(list(sections.get("next_steps") or []), empty_state="No next step suggestion was generated.", limit=4)}
            </div>
          </div>
        """
    return f"""
    <div class="product-panel product-panel--strong">
      <div class="{status_class}">{escape(result.workflow_label)} · {escape(result.status.title())}</div>
      <div class="product-section-title">Decision-ready summary</div>
      <div class="product-section-subtitle">{escape(result.summary)}</div>
      {recommendation_html}
      <div class="product-chip-row">{_render_chip_row(chip_values)}</div>
      {candidate_html}
    </div>
    """


def build_result_panels_html(result: ProductWorkflowResult | None) -> str:
    if result is None:
        return '<div class="product-empty-state">Outcome cards will appear here once a workflow has been executed.</div>'
    sections = build_product_result_sections(result)
    highlights = list(sections.get("strengths") or sections.get("highlights") or [])
    watchouts = list(sections.get("watchouts") or sections.get("warnings") or [])
    next_steps = list(sections.get("next_steps") or ([result.recommendation] if result.recommendation else []))
    evidence_rows = sections.get("evidence_highlights") if isinstance(sections.get("evidence_highlights"), list) else []
    evidence_text = [
        f"{row[0]} · {row[1]} · {row[3]}"
        for row in evidence_rows[:3]
        if isinstance(row, list) and len(row) >= 4
    ]
    cards = [
        {
            "title": "Highlights",
            "body": _render_list(highlights, empty_state="No high-confidence highlight was captured yet.", limit=4),
        },
        {
            "title": "Watchouts",
            "body": _render_list(watchouts, empty_state="No critical watchout is active for this run.", limit=4),
        },
        {
            "title": "Next steps",
            "body": _render_list(next_steps, empty_state="No next-step recommendation was generated yet.", limit=4),
        },
        {
            "title": "Evidence signals",
            "body": _render_list(evidence_text, empty_state="No concise evidence signal card was generated yet.", limit=3),
        },
    ]
    return '<div class="product-result-grid">' + ''.join(
        f'<div class="product-list-card"><div class="product-list-card__title">{escape(card["title"])}</div>{card["body"]}</div>'
        for card in cards
    ) + '</div>'


def build_artifact_panel_html(result: ProductWorkflowResult | None, deck_result: dict[str, Any] | None = None) -> str:
    if result is None:
        return '<div class="product-empty-state">Generate a workflow outcome first. Artifact downloads and deck status will appear here.</div>'
    artifacts = result.artifacts or []
    if not artifacts and not deck_result:
        return '<div class="product-empty-state">No workflow artifact is available yet. Run a workflow and then generate the executive deck if needed.</div>'
    status_line = ""
    if isinstance(deck_result, dict):
        export_status = escape(str(deck_result.get("status") or "unknown"))
        export_id = escape(str(deck_result.get("export_id") or "n/d"))
        status_line = f'<div class="product-section-subtitle"><strong>Deck export:</strong> status={export_status} · export_id={export_id}</div>'
    items_html = ''.join(
        f'<div class="product-artifact-item"><div class="product-artifact-item__label">{escape(artifact.label)}</div><div class="product-artifact-item__meta">{escape(artifact.download_name or artifact.path or "artifact")}</div></div>'
        for artifact in artifacts if artifact.available
    )
    if not items_html:
        items_html = '<div class="product-artifact-item"><div class="product-artifact-item__label">Deck generation pending</div><div class="product-artifact-item__meta">Generate the executive deck to unlock downloadables.</div></div>'
    return f"""
    <div class="product-panel">
      <div class="product-section-title">Artifacts and downloads</div>
      <div class="product-section-subtitle">Use this area to review the workflow outputs you can hand off or download.</div>
      {status_line}
      <div class="product-artifact-list">{items_html}</div>
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