# Executive Deck Generation — action plan deck contract v1

## Objetivo

Definir o contract v1 do **Action Plan Deck**, focado em owners, prioridades, prazos e sequência de execução.

---

## Identidade do contract

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "action_plan_deck"`
- `deck_family = "action_plan"`

---

## Fontes típicas do AI Workbench

- checklist
- action items
- owners
- due dates
- blockers

---

## Estrutura de alto nível

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
  "executive_summary": "Plano executivo de ação derivado dos findings e checklists estruturados.",
  "priority_snapshot": {
    "p0_count": 1,
    "p1_count": 3,
    "p2_count": 4,
    "blocked_count": 1
  },
  "actions": [
    {
      "title": "Definir owner do controle anual",
      "priority": "P0",
      "owner": "Compliance Lead",
      "due_date": "2026-04-12",
      "status": "open"
    }
  ],
  "blockers": [
    "Owner final ainda não confirmado."
  ],
  "next_steps": [
    "Aprovar owners.",
    "Executar plano em 2 semanas."
  ],
  "data_sources": [
    "structured_checklist",
    "action_items"
  ]
}
```

---

## Slides mínimos esperados

1. title
2. executive summary
3. priority metrics
4. action table
5. timeline or phased plan
6. blockers vs mitigations

---

## Regras mínimas

- `actions` deve ter pelo menos 1 item
- `owner` e `priority` devem existir nos itens críticos
- se `actions` não existir, o deck deve ser bloqueado
