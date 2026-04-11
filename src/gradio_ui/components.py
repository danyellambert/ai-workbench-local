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

WORKFLOW_STRATEGY_LABELS = {
    "document_scan": "Full document scan",
    "retrieval": "Targeted retrieval",
}


def _render_list(items: list[object], *, empty_state: str, limit: int = 4) -> str:
    normalized = [escape(str(item)) for item in items if str(item).strip()]
    if not normalized:
        return f'<div class="product-list-card__empty">{escape(empty_state)}</div>'
    return '<ul class="product-list-card__list">' + "".join(f"<li>{item}</li>" for item in normalized[:limit]) + '</ul>'


def _render_chip_row(values: list[str]) -> str:
    return "".join(f'<div class="product-chip">{escape(value)}</div>' for value in values if str(value).strip())


def build_workflow_button_text(definition: ProductWorkflowDefinition, *, active: bool = False) -> str:
    icon = WORKFLOW_ICONS.get(definition.workflow_id, "✦")
    best_for = definition.headline if len(definition.headline) <= 66 else f"{definition.headline[:63].rstrip()}..."
    document_rule = f"Docs: {definition.required_document_count_min}"
    if definition.required_document_count_max is not None:
        document_rule += f"-{definition.required_document_count_max}"
    deliverable = definition.default_export_label or definition.default_export_kind or "Structured output"
    status_line = "✓ Selected workflow" if active else "Select workflow"
    return "\n".join(
        [
            f"{icon} {definition.label}",
            f"Best for: {best_for}",
            f"{document_rule} · {deliverable}",
            status_line,
        ]
    )


def build_step_header_html(*, step: str, title: str, body: str) -> str:
    return f"""
    <div class="product-step-card">
      <div class="product-step-card__eyebrow">{escape(step)}</div>
      <div class="product-step-card__title">{escape(title)}</div>
      <div class="product-step-card__body">{escape(body)}</div>
    </div>
    """


def build_topbar_html(*, app_name: str, show_ai_lab_entry: bool = True) -> str:
    link_html = (
        '<a class="product-link-pill" href="./main.py" target="_blank">Open AI Lab</a>'
        if show_ai_lab_entry
        else ""
    )
    return f"""
    <div class="product-topbar product-shell">
      <div>
        <div class="product-topbar__eyebrow">Executive decision workspace</div>
        <div class="product-topbar__title">{escape(app_name)}</div>
        <div class="product-topbar__hint">Decision workflows grounded in documents</div>
      </div>
      <div>{link_html}</div>
    </div>
    """


def build_hero_html() -> str:
    return """
    <div class="product-hero product-shell">
      <div class="product-masthead">
        <div class="product-hero__eyebrow">Decision workflows grounded in documents</div>
        <h1 class="product-hero__title">Move from document evidence to executive decision in one focused workspace.</h1>
        <div class="product-hero__subtitle">
          Review documents, compare policies, generate action plans and evaluate candidates with a calmer product surface that keeps evidence, recommendation and handoff aligned.
        </div>
        <div class="product-chip-row">
          <div class="product-chip">Evidence-first</div>
          <div class="product-chip">Decision-ready</div>
          <div class="product-chip">Executive handoff</div>
        </div>
        <div class="product-hero__cta-note">Use the left setup rail to scope the workflow and evidence, then read the decision summary, evidence and deliverables on the right insight canvas.</div>
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
    strategy_label = WORKFLOW_STRATEGY_LABELS.get(definition.preferred_context_strategy, definition.preferred_context_strategy)
    primary_example = next((str(item).strip() for item in definition.example_prompts if str(item).strip()), "")
    examples_html = "".join(f"<li>{escape(item)}</li>" for item in definition.example_prompts[:3] if str(item).strip()) or "<li>No example prompt registered yet.</li>"
    outputs_html = "".join(
        f"<li>{escape(item)}</li>" for item in definition.expected_outputs[:4] if str(item).strip()
    ) or "<li>No expected outputs registered yet.</li>"
    technical_meta = "".join(
        f"<li><strong>{label}</strong> {escape(value)}</li>"
        for label, value in [
            ("Engine:", task_types),
            ("Evidence mode:", strategy_label),
            ("Deliverable:", deck_label),
            ("Prompt policy:", prompt_policy),
            ("Workflow contract:", definition.workflow_contract or "Not registered yet"),
        ]
    )
    return f"""
    <div class="product-panel product-workflow-detail-shell">
      <div class="product-section-title">{escape(definition.label)}</div>
      <div class="product-section-subtitle">{escape(definition.description)}</div>
      <div class="product-chip-row">
        <div class="product-chip">{escape(doc_rule)}</div>
        <div class="product-chip">Selected docs: {selected_documents}</div>
        <div class="product-chip">Evidence mode: {escape(strategy_label)}</div>
        <div class="product-chip">{escape(prompt_policy)}</div>
      </div>
      <div class="product-detail-grid product-detail-grid--compact">
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>When to use</strong></div>
          <div class="product-section-subtitle">{escape(definition.headline)}</div>
        </div>
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Prompt starter</strong></div>
          <div class="product-quote-card">{escape(primary_example or input_guidance)}</div>
          <div class="product-section-subtitle">{escape(input_guidance)}</div>
        </div>
        <div class="product-detail-section">
          <div class="product-section-subtitle"><strong>Expected outputs</strong></div>
          <ul class="product-workflow-card__list">{outputs_html}</ul>
        </div>
      </div>
      <details class="product-inline-details">
        <summary>Show technical workflow details</summary>
        <div class="product-inline-details__body">
          <ul class="product-inline-meta-list">{technical_meta}</ul>
          <div class="product-detail-section">
            <div class="product-section-subtitle"><strong>Example prompts</strong></div>
            <ul class="product-workflow-card__list">{examples_html}</ul>
          </div>
        </div>
      </details>
    </div>
    """


def build_document_status_html(*, title: str, body: str, stats: list[str] | None = None, tone: str = "neutral") -> str:
    tone_class = f" product-status-card--{escape(tone)}" if tone else ""
    stats_html = f'<div class="product-chip-row">{_render_chip_row(list(stats or []))}</div>' if stats else ""
    return f"""
    <div class="product-status-card{tone_class}">
      <div class="product-status-card__eyebrow">Document intake</div>
      <div class="product-status-card__title">{escape(title)}</div>
      <div class="product-status-card__body">{escape(body)}</div>
      {stats_html}
    </div>
    """


def build_grounding_preview_html(preview: GroundingPreview | None) -> str:
    if preview is None:
        return '<div class="product-empty-state">Evidence preview will appear here once you preview or run a workflow.</div>'
    warnings_html = "".join(f"<li>{escape(item)}</li>" for item in preview.warnings)
    warning_block = f'<div class="product-callout product-callout--warning"><div class="product-callout__title">Review before running</div><ul class="product-workflow-card__list">{warnings_html}</ul></div>' if warnings_html else ""
    strategy_label = WORKFLOW_STRATEGY_LABELS.get(preview.strategy, preview.strategy)
    return f"""
    <div class="product-panel">
      <div class="product-section-title">Evidence readiness</div>
      <div class="product-section-subtitle">This run is currently grounded in {len(preview.document_ids)} document(s) and {preview.source_block_count} evidence block(s) before generation starts.</div>
      <div class="product-chip-row">
        <div class="product-chip">Evidence mode: {escape(strategy_label)}</div>
        <div class="product-chip">Documents in scope: {len(preview.document_ids)}</div>
        <div class="product-chip">Context size: {preview.context_chars} chars</div>
        <div class="product-chip">Evidence blocks: {preview.source_block_count}</div>
      </div>
      <div class="product-section-subtitle">Use this view to confirm why the workflow should be trusted before you run it and open the full table only when needed.</div>
      {warning_block}
    </div>
    """


def build_contract_snapshot_html(contract_entry: dict[str, Any] | None) -> str:
    entry = contract_entry if isinstance(contract_entry, dict) else {}
    expected_outputs = entry.get("expected_outputs") if isinstance(entry.get("expected_outputs"), list) else []
    prompts = entry.get("example_prompts") if isinstance(entry.get("example_prompts"), list) else []
    chip_values = [
        f"Evidence mode: {WORKFLOW_STRATEGY_LABELS.get(str(entry.get('preferred_context_strategy') or ''), str(entry.get('preferred_context_strategy') or 'n/a'))}",
        f"Prompt: {'Optional' if entry.get('supports_optional_prompt', True) else 'Fixed'}",
        f"Deliverable: {entry.get('default_export_label') or entry.get('default_export_kind') or 'n/a'}",
    ]
    contract_line = escape(str(entry.get("workflow_contract") or "Not registered yet"))
    return f"""
    <div class="product-panel">
      <div class="product-section-title">Technical workflow details</div>
      <div class="product-section-subtitle">Reference contract, expected outputs and implementation hints for this workflow. Use the raw JSON only when you need the payload details.</div>
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
        return '<div class="product-empty-state">Run a workflow to see the decision summary, evidence signals and deliverables here.</div>'
    sections = build_product_result_sections(result)
    status_class = f"product-status-pill product-status-pill--{escape(result.status)}"

    chip_values = [
        f"Highlights: {len(sections.get('highlights') or [])}",
        f"Watchouts: {len(sections.get('warnings') or [])}",
        f"Artifacts: {len(result.artifacts or [])}",
        f"Deck: {'Ready' if result.deck_available else 'Pending'}",
    ]
    grounding = result.grounding_preview
    confidence_html = ""
    if grounding is not None:
        confidence_html = f"""
        <div class="product-summary-confidence">
          Grounded in {len(grounding.document_ids)} document(s) · {grounding.source_block_count} evidence block(s) · {grounding.context_chars} chars of supporting context
        </div>
        """

    candidate_profile = sections.get("candidate_profile") if isinstance(sections.get("candidate_profile"), dict) else None

    candidate_html = ""
    if candidate_profile:
        candidate_html = f"""
          <div class="product-summary-identity">
            <div class="product-summary-identity__title">Candidate: {escape(str(candidate_profile.get("name") or "Candidate"))}</div>
            <div class="product-summary-identity__meta">Headline: {escape(str(candidate_profile.get("headline") or "Profile under review"))}</div>
            <div class="product-summary-identity__meta">Location: {escape(str(candidate_profile.get("location") or "Location not explicit"))}</div>
          </div>
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
    <div class="product-panel product-panel--strong product-summary-hero">
      <div class="{status_class}">{escape(result.workflow_label)} · {escape(result.status.title())}</div>
      <div class="product-summary-hero__eyebrow">Decision-ready summary</div>
      <div class="product-summary-hero__title">{escape(result.summary)}</div>
      <div class="product-summary-hero__recommendation"><strong>Recommendation:</strong> {escape(result.recommendation or 'Review the evidence and confirm the next action.')}</div>
      {confidence_html}
      <div class="product-chip-row">{_render_chip_row(chip_values)}</div>
      {candidate_html}
    </div>
    """


def build_result_panels_html(result: ProductWorkflowResult | None) -> str:
    if result is None:
        return '<div class="product-empty-state">Executive finding cards will appear here once a workflow has been executed.</div>'
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
            "title": "Key findings",
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
        return '<div class="product-empty-state">Generate a workflow outcome first. Deliverables and exports will appear here.</div>'
    artifacts = result.artifacts or []
    if not artifacts and not deck_result:
        return '<div class="product-empty-state">No deliverable is available yet. Run a workflow and then generate the executive deck if needed.</div>'
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
      <div class="product-section-title">Deliverables and downloads</div>
      <div class="product-section-subtitle">Use this area as the executive handoff layer: confirm what is ready, what still depends on export and which file can be shared next.</div>
      {status_line}
      <div class="product-artifact-list">{items_html}</div>
    </div>
    """


def build_credibility_band_html() -> str:
    return """
    <div class="product-shell product-proof-band">
      <div class="product-proof-row">
        <div class="product-proof-chip">Grounded by document context</div>
        <div class="product-proof-chip">Structured outputs</div>
        <div class="product-proof-chip">Actionable recommendations</div>
        <div class="product-proof-chip">Executive handoff ready</div>
      </div>
    </div>
    """