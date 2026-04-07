# Executive Deck Generation — document review deck contract v1

## Objective

Define the v1 contract for the **Document Review Deck**, designed to turn document analysis into an executive review deck.

---

## Contract identity

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "document_review_deck"`
- `deck_family = "review"`

---

## Target audience

- leadership
- compliance
- operations
- human reviewers

---

## Typical AI Workbench sources

- `summary`
- `extraction`
- `document_agent`
- structured findings
- recommendations
- evidence metadata

---

## High-level structure

```json
{
  "contract_version": "executive_deck_generation.v1",
  "export_kind": "document_review_deck",
  "deck_family": "review",
  "presentation": {
    "title": "Document Review",
    "subtitle": "Executive review of the analyzed document",
    "author": "AI Workbench Local",
    "date": "2026-04-05",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Document Review"
  },
  "document_context": {
    "document_title": "Supplier Policy 2026",
    "document_type": "policy_pdf",
    "source_count": 1,
    "source_refs": ["repository://policy/supplier_policy_2026.pdf"]
  },
  "executive_summary": "Executive summary of the document and what truly matters for decision-making.",
  "risk_snapshot": {
    "critical_count": 1,
    "high_count": 2,
    "medium_count": 3,
    "needs_review": true
  },
  "key_highlights": [
    "The document introduces new approval obligations.",
    "There is an owner gap in critical controls."
  ],
  "top_findings": [
    {
      "title": "Owner not defined for the annual review",
      "severity": "high",
      "impact": "It may block consistent execution of the control.",
      "evidence_ref": "page:12"
    }
  ],
  "recommendation": "Approve only after owners are defined and critical clauses are adjusted.",
  "watchouts": [
    "Some sections require additional legal validation."
  ],
  "next_steps": [
    "Define control owners.",
    "Review critical clauses with legal.",
  ],
  "data_sources": [
    "structured_summary",
    "document_agent",
    "evidence_findings"
  ]
}
```

---

## Minimum expected slides

1. title
2. executive summary
3. risk snapshot metrics
4. top findings table
5. recommendation vs watchouts
6. next steps

---

## Minimum rules

- `executive_summary` is required
- `document_context.document_title` is required
- `top_findings` must contain at least 1 item for the deck to be fully useful
- `recommendation` is required
- if `top_findings` does not exist, the deck must be blocked or marked as `needs_review`
