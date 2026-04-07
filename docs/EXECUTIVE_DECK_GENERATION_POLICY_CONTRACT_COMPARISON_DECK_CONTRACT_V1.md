# Executive Deck Generation — policy / contract comparison deck contract v1

## Objective

Define the v1 contract for the **Policy / Contract Comparison Deck**, focused on executive comparison between two documents or versions.

---

## Contract identity

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "policy_contract_comparison_deck"`
- `deck_family = "comparison"`

---

## Target audience

- legal
- compliance
- procurement
- decision leadership

---

## Typical AI Workbench sources

- structured document comparison
- difference findings
- change summary
- impact assessment

---

## High-level structure

```json
{
  "contract_version": "executive_deck_generation.v1",
  "export_kind": "policy_contract_comparison_deck",
  "deck_family": "comparison",
  "presentation": {
    "title": "Policy Comparison Review",
    "subtitle": "Version A vs Version B",
    "author": "AI Workbench Local",
    "date": "2026-04-05",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Comparison Review"
  },
  "comparison_context": {
    "left_document": "Policy 2025",
    "right_document": "Policy 2026",
    "comparison_scope": "supplier approval controls"
  },
  "executive_summary": "Executive summary of the most relevant differences and their operational impact.",
  "comparison_highlights": [
    "A new formal-approval requirement appears in the 2026 document.",
    "The review deadline was reduced."
  ],
  "comparison_rows": [
    {
      "topic": "Supplier approval",
      "left_value": "Opcional",
      "right_value": "Required",
      "impact": "More control, more operational friction"
    }
  ],
  "recommendation": "Adopt the new policy with an operational adaptation plan.",
  "watchouts": [
    "The deadline change may require a process adjustment."
  ],
  "next_steps": [
    "Validate the operational impact.",
    "Adjust owners and SLA."
  ],
  "data_sources": [
    "document_comparison",
    "comparison_findings"
  ]
}
```

---

## Minimum expected slides

1. title
2. comparison summary
3. comparison table
4. impact analysis
5. recommendation vs watchouts
6. next steps

---

## Minimum rules

- `comparison_context.left_document` and `right_document` are required
- `comparison_rows` must contain at least 1 row
- `recommendation` is required
- without `comparison_rows`, the deck must be blocked
