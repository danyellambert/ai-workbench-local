# Executive Deck Generation — routing e seleção de deck type

## Objetivo

Definir como o produto decide **qual deck type sugerir, permitir ou bloquear** em cada fluxo.

---

## Modos de seleção

### 1. Seleção explícita pelo usuário

Modo preferido para as primeiras versões.

O usuário escolhe diretamente:

- benchmark/eval executive review
- document review
- policy/contract comparison
- action plan
- candidate review
- evidence pack

### 2. Sugestão automática pelo fluxo ativo

O sistema pode sugerir um deck default com base no fluxo atual, mas sem esconder a escolha do usuário.

### 3. Bloqueio por insuficiência de grounding

Se os sinais necessários não existirem, o produto deve bloquear a geração do deck ou marcá-lo como `needs_review`.

---

## Regras de roteamento por fluxo

| fluxo/origem | deck sugerido | condição mínima |
|---|---|---|
| benchmark + evals | `benchmark_eval_executive_review` | leaderboards + snapshots agregados disponíveis |
| summary/extraction sobre documento único | `document_review_deck` | resumo + findings/recommendations mínimas |
| comparação documental | `policy_contract_comparison_deck` | diff/comparison rows disponíveis |
| checklist + owners + due dates | `action_plan_deck` | action items estruturados |
| `cv_analysis` / evidence_cv | `candidate_review_deck` | profile + strengths/gaps/recommendation |
| EvidenceOps / audit review | `evidence_pack_deck` | findings + evidence items + actions |

---

## Policy de bloqueio

O deck **não deve** ser gerado automaticamente quando faltar qualquer um destes itens críticos:

- recommendation inexistente em deck de decisão
- comparison rows inexistentes em comparison deck
- action items inexistentes em action plan deck
- evidence items inexistentes em evidence pack deck

Nesses casos, a UI deve:

- informar por que a geração foi bloqueada
- oferecer download do JSON/resultado bruto se útil

---

## Policy de `needs_review`

Mesmo quando a geração for permitida, o deck deve carregar `needs_review` se:

- o grounding estiver parcial
- a recomendação depender de interpretação ambígua
- houver dados sensíveis ou incompletos
