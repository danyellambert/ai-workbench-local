# Executive Deck Generation — plano documental completo

## Objetivo

Consolidar **absolutamente tudo o que precisa ser documentado** para implementar a capability de **Executive Deck Generation** por completo no ecossistema do AI Workbench Local.

Este documento existe para responder, de forma operacional, quatro perguntas:

1. o que já está documentado
2. o que ainda falta documentar
3. o que é obrigatório antes de implementar o P1
4. o que pode ser documentado em paralelo à implementação dos próximos deck types

---

## Estado atual

### Já documentado

#### Capability / visão de produto
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

#### Productização técnica do primeiro slice
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`

#### Contrato concreto do P1
- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`

#### Roadmap principal
- `ROADMAP.md`

### Escopo documental complementar fechado nesta rodada

- catálogo oficial de deck types e `export_kind`
- arquitetura de serviço da capability
- contrato de API entre AI Workbench e `ppt_creator_app`
- lifecycle de artefatos
- UX mínima e progressão de UI
- estratégia de testes
- políticas de qualidade, observabilidade, segurança e rollout
- docs auxiliares de roteamento, versionamento, recipes e mapping
- contratos dedicados para P2/P3/P4/P5/P6 ainda pendentes de escrita específica

---

## Pacote documental completo da capability

## 1. Capability / produto

### 1.1 Capability map
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

### 1.2 Plano documental completo
- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENTATION_PLAN.md`

### 1.3 Catálogo oficial de deck types
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG.md`

### 1.4 Routing policy
- `docs/EXECUTIVE_DECK_GENERATION_ROUTING.md`

### 1.5 Contract versioning
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_VERSIONING.md`

---

## 2. Contratos de dados por deck type

### P1 — já iniciado
- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`

### P2/P3/P4/P5/P6 — necessários para capability completa
- `docs/DOCUMENT_REVIEW_DECK_CONTRACT_V1.md`
- `docs/POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1.md`
- `docs/ACTION_PLAN_DECK_CONTRACT_V1.md`
- `docs/CANDIDATE_REVIEW_DECK_CONTRACT_V1.md`
- `docs/EVIDENCE_PACK_DECK_CONTRACT_V1.md`

---

## 3. Arquitetura e integração

- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE.md`
- `docs/EXECUTIVE_DECK_GENERATION_API_CONTRACT.md`
- `docs/EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE.md`
- `docs/EXECUTIVE_DECK_GENERATION_RENDERER_MAPPING.md`
- `docs/EXECUTIVE_DECK_GENERATION_SLIDE_RECIPES.md`
- `docs/EXECUTIVE_DECK_GENERATION_BRANDING_POLICY.md`
- `docs/EXECUTIVE_DECK_GENERATION_FAILURE_MODES.md`

---

## 4. Produto / UX

- `docs/EXECUTIVE_DECK_GENERATION_UX_SPEC.md`
- `docs/EXECUTIVE_DECK_GENERATION_UI_EVOLUTION.md`
- `docs/EXECUTIVE_DECK_GENERATION_USER_JOURNEYS.md`

---

## 5. Qualidade, testes e governança

- `docs/EXECUTIVE_DECK_GENERATION_TEST_STRATEGY.md`
- `docs/EXECUTIVE_DECK_GENERATION_QUALITY_AND_GOVERNANCE.md`
- `docs/EXECUTIVE_DECK_GENERATION_OBSERVABILITY.md`
- `docs/EXECUTIVE_DECK_GENERATION_SECURITY_AND_PII.md`
- `docs/EXECUTIVE_DECK_GENERATION_ROLLOUT_AND_GOVERNANCE.md`

---

## O que é obrigatório antes de implementar o P1

Para começar a implementação do **Benchmark & Eval Executive Review Deck** com segurança, o mínimo documental obrigatório é:

1. capability map
2. productização técnica do primeiro slice
3. contrato v1 do P1
4. catálogo oficial de deck types
5. arquitetura de serviço
6. API contract
7. artifact lifecycle
8. UX spec mínima
9. test strategy

Em outras palavras: o P1 não depende dos contratos completos de todos os decks futuros, mas depende da infraestrutura documental que define a capability como sistema coerente.

---

## O que pode ser documentado em paralelo ao P1

Os itens abaixo não bloqueiam o início do P1, mas bloqueiam a ideia de **capability completa**:

- contract v1 do `document_review_deck`
- contract v1 do `policy_contract_comparison_deck`
- contract v1 do `action_plan_deck`
- contract v1 do `candidate_review_deck`
- contract v1 do `evidence_pack_deck`
- policy completa de quality/governance/PII

---

## Ordem recomendada de documentação

### Fase documental A — obrigatória antes do P1

1. `EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG`
2. `EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE`
3. `EXECUTIVE_DECK_GENERATION_API_CONTRACT`
4. `EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE`
5. `EXECUTIVE_DECK_GENERATION_UX_SPEC`
6. `EXECUTIVE_DECK_GENERATION_TEST_STRATEGY`

### Fase documental B — necessária para capability completa

7. `DOCUMENT_REVIEW_DECK_CONTRACT_V1`
8. `POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1`
9. `ACTION_PLAN_DECK_CONTRACT_V1`
10. `CANDIDATE_REVIEW_DECK_CONTRACT_V1`
11. `EVIDENCE_PACK_DECK_CONTRACT_V1`

---

## Critério de documentação “done”

Podemos considerar a capability documentalmente pronta quando:

- os deck types P1/P2/P3/P4/P5/P6 estiverem nomeados e catalogados
- houver contrato concreto para cada deck prioritário
- houver arquitetura de serviço definida
- houver API contract explícito com o `ppt_creator_app`
- houver lifecycle de artefatos/proveniência definido
- houver UX mínima descrita
- houver estratégia de testes e política de rollout/qualidade

---

## Resumo executivo

Hoje o projeto já tinha documentação suficiente para o **P1 técnico**.  
Com este pacote, a meta passa a ser fechar também a documentação necessária para a **capability completa** de Executive Deck Generation.

O princípio central é simples:

> não basta documentar um export isolado; é preciso documentar o catálogo, os contratos, a arquitetura, a UX, os artefatos, os testes e a governança de uma capability recorrente de produto.
