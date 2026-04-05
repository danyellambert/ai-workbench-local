# Executive Deck Generation — catálogo oficial de deck types e contracts

## Objetivo

Formalizar o catálogo oficial da capability de **Executive Deck Generation**.

Este documento responde:

- quais deck types existem oficialmente
- qual `export_kind` cada um usa
- qual prioridade cada um tem
- quais fontes do projeto alimentam cada deck
- qual o status documental/implementação de cada contract

---

## Convenções

### Campos oficiais do catálogo

- `deck_family`
- `product_name`
- `export_kind`
- `priority`
- `source_flows`
- `target_audience`
- `status`
- `contract_doc`

### Status possíveis

- `foundation_exists`
- `planned`
- `contract_defined`
- `implemented`
- `implemented_foundation`

---

## Catálogo oficial

| deck_family | product_name | export_kind | priority | source_flows | target_audience | status | contract_doc |
|---|---|---|---|---|---|---|---|
| executive_review | Benchmark & Eval Executive Review Deck | `benchmark_eval_executive_review` | P1 | benchmark, evals, readiness | liderança técnica, produto, stakeholder executivo | implemented | `docs/PRESENTATION_EXPORT_BENCHMARK_EVAL_CONTRACT_V1.md` |
| document_review | Document Review Deck | `document_review_deck` | P2 | summary, extraction, document agent, EvidenceOps | compliance, operações, liderança | implemented_foundation | `docs/DOCUMENT_REVIEW_DECK_CONTRACT_V1.md` |
| comparison | Policy / Contract Comparison Deck | `policy_contract_comparison_deck` | P2 | comparison findings, structured outputs, document agent | jurídico, compliance, procurement | implemented_foundation | `docs/POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1.md` |
| action_plan | Action Plan Deck | `action_plan_deck` | P3 | checklist, findings, owners, due dates | operações, PM, compliance | implemented_foundation | `docs/ACTION_PLAN_DECK_CONTRACT_V1.md` |
| candidate_review | Candidate Review Deck | `candidate_review_deck` | P3 | `cv_analysis`, evidence_cv, candidate comparison | recrutamento, hiring manager | implemented_foundation | `docs/CANDIDATE_REVIEW_DECK_CONTRACT_V1.md` |
| evidence_audit | Evidence Pack / Audit Deck | `evidence_pack_deck` | P3 | EvidenceOps, repository state, action backlog | auditoria, governança, liderança | implemented_foundation | `docs/EVIDENCE_PACK_DECK_CONTRACT_V1.md` |

---

## Nota sobre o naming legado do P1

O código atual já implementado usa a fundação:

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

Esse naming continua aceito como **base técnica existente do P1**.

Estado atual do código:

- o service aceita o alias de produto `benchmark_eval_executive_review`
- a implementação interna continua compatível com o naming legado `benchmark_eval_executive_deck`

Direção recomendada de longo prazo:

- capability/catálogo usam o naming de produto acima
- a implementação pode manter compatibilidade com o naming legado até o momento de uma migração explícita

---

## Critério para promover um deck type de `planned` para `contract_defined`

Um deck type só deve ser tratado como realmente pronto para implementação quando houver:

1. objetivo de produto claro
2. `export_kind` definido
3. input sources explícitas
4. JSON contract v1 documentado
5. slide recipe inicial documentada
6. critérios mínimos de qualidade/review

## Estado real atual da implementação

Hoje já existe no código:

- builders multi-deck em `src/services/presentation_export.py`
- service genérico em `src/services/presentation_export_service.py`
- UI Streamlit com seleção de deck type em `src/ui/executive_deck_generation.py`
- unit tests de builders/adapters em `tests/test_presentation_export_unittest.py`

Leitura recomendada dos status:

- `implemented` = deck type com fluxo principal já consolidado no produto atual
- `implemented_foundation` = deck type já presente em código, UI e testes unitários, mas ainda pedindo smoke tests/hardening operacional antes de ser tratado como totalmente fechado

---

## Ordem recomendada de fechamento do catálogo

### Agora
- `benchmark_eval_executive_review`

### Em seguida
- `document_review_deck`
- `policy_contract_comparison_deck`

### Depois
- `action_plan_deck`
- `candidate_review_deck`
- `evidence_pack_deck`
