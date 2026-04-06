# Executive Deck Generation — document review deck contract v1

## Objetivo

Definir o contract v1 do **Document Review Deck**, voltado para transformar a análise de um documento em um deck executivo de review.

---

## Identidade do contract

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "document_review_deck"`
- `deck_family = "review"`

---

## Público-alvo

- liderança
- compliance
- operações
- reviewers humanos

---

## Fontes típicas do AI Workbench

- `summary`
- `extraction`
- `document_agent`
- findings estruturados
- recommendations
- evidence metadata

---

## Estrutura de alto nível

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
  "executive_summary": "Resumo executivo do documento e do que realmente importa para decisão.",
  "risk_snapshot": {
    "critical_count": 1,
    "high_count": 2,
    "medium_count": 3,
    "needs_review": true
  },
  "key_highlights": [
    "Documento introduz obrigações novas de aprovação.",
    "Há lacuna de owner em controles críticos."
  ],
  "top_findings": [
    {
      "title": "Owner não definido para revisão anual",
      "severity": "high",
      "impact": "Pode bloquear execução consistente do controle.",
      "evidence_ref": "page:12"
    }
  ],
  "recommendation": "Aprovar somente após definição de owners e ajuste das cláusulas críticas.",
  "watchouts": [
    "Há trechos que exigem validação jurídica adicional."
  ],
  "next_steps": [
    "Definir owners dos controles.",
    "Revisar cláusulas críticas com jurídico."
  ],
  "data_sources": [
    "structured_summary",
    "document_agent",
    "evidence_findings"
  ]
}
```

---

## Slides mínimos esperados

1. title
2. executive summary
3. risk snapshot metrics
4. top findings table
5. recommendation vs watchouts
6. next steps

---

## Regras mínimas

- `executive_summary` é obrigatório
- `document_context.document_title` é obrigatório
- `top_findings` deve ter pelo menos 1 item para o deck ser plenamente útil
- `recommendation` é obrigatória
- se `top_findings` não existir, o deck deve ser bloqueado ou marcado como `needs_review`
