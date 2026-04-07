# Executive Deck Generation — action plan deck contract v1

## Objective

Define the v1 contract for the **Action Plan Deck**, focused on owners, priorities, deadlines, and execution sequence.

---

## Contract identity

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "action_plan_deck"`
- `deck_family = "action_plan"`

---

## Typical AI Workbench sources

- checklist
- action items
- owners
- due dates
- blockers

---

## High-level structure

```json
{
  "contract_version": "executive_deck_generation.v1",
  "export_kind": "action_plan_deck",
  "deck_family": "action_plan",
  "presentation": {
    "title": "Action Plan",
    "subtitle": "Operational execution plan",
    "author": "AI Workbench Local",
    "date": "2026-04-05",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Action Plan"
  },
  "executive_summary": "Executive action plan derived from findings and structured checklists.",
  "priority_snapshot": {
    "p0_count": 1,
    "p1_count": 3,
    "p2_count": 4,
    "blocked_count": 1
  },
  "actions": [
    {
      "title": "Define the owner of the annual control",
      "priority": "P0",
      "owner": "Compliance Lead",
      "due_date": "2026-04-12",
      "status": "open"
    }
  ],
  "blockers": [
    "Final owner has not been confirmed yet."
  ],
  "next_steps": [
    "Approve owners.",
    "Execute the plan within 2 weeks."
  ],
  "data_sources": [
    "structured_checklist",
    "action_items"
  ]
}
```

---

## Minimum expected slides

1. title
2. executive summary
3. priority metrics
4. action table
5. timeline or phased plan
6. blockers vs mitigations

---

## Minimum rules

- `actions` must contain at least 1 item
- `owner` and `priority` must exist for critical items
- if `actions` does not exist, the deck must be blocked
