# Executive Deck Generation — evidence pack deck contract v1

## Objective

Define the v1 contract for the **Evidence Pack / Audit Deck**, focused on executive reporting for audit, compliance, and document governance.

---

## Contract identity

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "evidence_pack_deck"`
- `deck_family = "evidence_audit"`

---

## Typical AI Workbench sources

- EvidenceOps
- evidence packs
- findings
- owners
- due dates
- action backlog

---

## High-level structure

```json
{
  "contract_version": "executive_deck_generation.v1",
  "export_kind": "evidence_pack_deck",
  "deck_family": "evidence_audit",
  "presentation": {
    "title": "Evidence Pack Review",
    "subtitle": "Audit / compliance executive handoff",
    "author": "AI Workbench Local",
    "date": "2026-04-05",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Evidence Review"
  },
  "executive_summary": "Executive summary of the evidence pack, findings, and required actions.",
  "evidence_snapshot": {
    "documents_reviewed": 12,
    "findings_count": 8,
    "open_actions": 5,
    "critical_items": 1
  },
  "findings": [
    {
      "title": "Missing evidence for annual control",
      "severity": "critical",
      "owner": "Compliance",
      "status": "open"
    }
  ],
  "recommendation": "Address critical findings before the next audit checkpoint.",
  "watchouts": [
    "There are actions without a defined due date."
  ],
  "next_steps": [
    "Close pending owner assignments.",
    "Update the evidence register."
  ],
  "data_sources": [
    "evidence_pack",
    "evidenceops_action_store"
  ]
}
```

---

## Minimum expected slides

1. title
2. executive summary
3. evidence metrics
4. findings table
5. owners / status table
6. risks vs mitigations
7. next steps

---

## Minimum rules

- `executive_summary` is required
- `findings` must contain at least 1 item
- `recommendation` is required
- if there are no findings, the deck must be blocked or treated as a special healthy-status case
