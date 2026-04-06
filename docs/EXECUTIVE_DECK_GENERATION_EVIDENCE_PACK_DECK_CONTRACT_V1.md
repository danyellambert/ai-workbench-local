# Executive Deck Generation — evidence pack deck contract v1

## Objetivo

Definir o contract v1 do **Evidence Pack / Audit Deck**, focado em reporting executivo de auditoria, compliance e governança documental.

---

## Identidade do contract

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "evidence_pack_deck"`
- `deck_family = "evidence_audit"`

---

## Fontes típicas do AI Workbench

- EvidenceOps
- evidence packs
- findings
- owners
- due dates
- action backlog

---

## Estrutura de alto nível

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
  "executive_summary": "Resumo executivo do evidence pack, findings e ações necessárias.",
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
  "recommendation": "Tratar findings críticos antes do próximo checkpoint de auditoria.",
  "watchouts": [
    "Há ações sem due date definido."
  ],
  "next_steps": [
    "Fechar owners pendentes.",
    "Atualizar evidence register."
  ],
  "data_sources": [
    "evidence_pack",
    "evidenceops_action_store"
  ]
}
```

---

## Slides mínimos esperados

1. title
2. executive summary
3. evidence metrics
4. findings table
5. owners / status table
6. risks vs mitigations
7. next steps

---

## Regras mínimas

- `executive_summary` é obrigatória
- `findings` deve ter pelo menos 1 item
- `recommendation` é obrigatória
- se não houver findings, o deck deve ser bloqueado ou tratado como caso especial de status saudável
