# Executive Deck Generation — policy / contract comparison deck contract v1

## Objetivo

Definir o contract v1 do **Policy / Contract Comparison Deck**, voltado para comparação executiva entre dois documentos ou versões.

---

## Identidade do contract

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "policy_contract_comparison_deck"`
- `deck_family = "comparison"`

---

## Público-alvo

- jurídico
- compliance
- procurement
- liderança de decisão

---

## Fontes típicas do AI Workbench

- comparação documental estruturada
- findings de diferença
- change summary
- impact assessment

---

## Estrutura de alto nível

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
  "executive_summary": "Resumo executivo das diferenças mais relevantes e do impacto operacional.",
  "comparison_highlights": [
    "Nova exigência de aprovação formal no documento 2026.",
    "Prazo de revisão foi reduzido."
  ],
  "comparison_rows": [
    {
      "topic": "Aprovação de fornecedor",
      "left_value": "Opcional",
      "right_value": "Obrigatória",
      "impact": "Maior controle, mais atrito operacional"
    }
  ],
  "recommendation": "Adotar a nova política com plano de adequação operacional.",
  "watchouts": [
    "Mudança de prazo pode exigir ajuste de processo."
  ],
  "next_steps": [
    "Validar impacto operacional.",
    "Ajustar owners e SLA."
  ],
  "data_sources": [
    "document_comparison",
    "comparison_findings"
  ]
}
```

---

## Slides mínimos esperados

1. title
2. comparison summary
3. comparison table
4. impact analysis
5. recommendation vs watchouts
6. next steps

---

## Regras mínimas

- `comparison_context.left_document` e `right_document` são obrigatórios
- `comparison_rows` deve ter pelo menos 1 linha
- `recommendation` é obrigatória
- sem `comparison_rows`, o deck deve ser bloqueado
