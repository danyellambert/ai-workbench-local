# Fase 10.25 — Executive Deck Generation como capability do produto

## Objetivo

Definir com clareza a nova direção do projeto: o ecossistema atual não terá apenas uma feature de **presentation export** isolada, mas uma capability recorrente de **Executive Deck Generation**.

Na prática, isso significa que o AI Workbench Local passa a poder gerar, continuamente, **decks executivos grounded** em:

- documentos
- structured outputs
- comparações documentais
- benchmark/evals
- EvidenceOps e action plans

Essa capability deve ser entendida como um dos produtos internos do ecossistema, e não como um side-project desconectado.

---

## Tese oficial

> O AI Workbench Local não apenas conversa com documentos, extrai informação e avalia qualidade. Ele também entrega **decks executivos recorrentes** para review, decisão, operação e comunicação com stakeholders.

Essa é a leitura de produto mais forte porque aproxima o projeto de um caso real de negócio:

1. documentos e sinais entram
2. IA analisa, resume, compara e estrutura
3. o sistema gera um artefato executivo utilizável no fluxo real de trabalho

---

## O que é essa capability

### O que ela é

Executive Deck Generation é a capability de transformar outputs grounded do AI Workbench em apresentações executivas recorrentes.

### O que ela não é

Ela **não** deve ser posicionada como:

- gerador genérico de slides sem contexto
- produto separado competindo com o AI Workbench
- camada puramente cosmética de exportação

O posicionamento correto é:

**grounded deck generation for business workflows**

Ou em PT-BR:

**geração de decks executivos grounded em documentos, análises estruturadas e decisões operacionais**

---

## Boundary arquitetural

### AI Workbench Local

Continua sendo a fonte da verdade para:

- ingestão documental
- RAG
- structured outputs
- agents/workflows
- benchmark/evals
- EvidenceOps
- recommendation logic

### `ppt_creator_app`

Entra como camada especializada de:

- validação de schema de apresentação
- renderização `.pptx`
- preview/review visual
- comparação de artefatos
- packaging final do deck

### Regra de separação

**AI Workbench Local = inteligência, grounding e orquestração**  
**`ppt_creator_app` = renderização executiva especializada**

Essa separação é importante porque mostra maturidade de produto e engenharia:

- o domínio não fica acoplado ao renderer
- o renderer não precisa conhecer a lógica de negócio profunda
- a capability pode crescer por catálogo de decks, não por hacks específicos

---

## Famílias de decks que o produto pode gerar continuamente

O jeito mais forte de pensar essa capability é por **famílias recorrentes de decks**.

## 1. Summary decks

Decks para síntese executiva de um ou mais documentos.

Exemplos:

- executive summary deck
- leadership briefing deck
- monthly/weekly review deck

Inputs típicos:

- documento longo
- corpus documental
- summary estruturado

## 2. Review decks

Decks para revisão de documentos, políticas, contratos ou conjuntos documentais.

Exemplos:

- document review deck
- compliance review deck
- risk review deck

Inputs típicos:

- findings
- risks
- gaps
- recommended actions

## 3. Comparison decks

Decks para comparar versões, opções ou candidatos.

Exemplos:

- policy/contract comparison deck
- option comparison deck
- candidate comparison deck

Inputs típicos:

- comparação estruturada
- diff documental
- scorecards lado a lado

## 4. Decision decks

Decks cuja pergunta principal é: **o que devemos fazer?**

Exemplos:

- decision memo deck
- recommendation deck
- model/runtime decision deck

Inputs típicos:

- trade-offs
- recommendation
- watchouts
- quality gates

## 5. Action-plan decks

Decks operacionais com foco em owner, prazo, prioridade e execução.

Exemplos:

- action plan deck
- remediation plan deck
- operational handoff deck

Inputs típicos:

- checklist
- action items
- owners
- due dates

## 6. Evidence / audit decks

Decks para auditoria, compliance, repositório de evidências e reporting executivo.

Exemplos:

- evidence pack deck
- audit review deck
- EvidenceOps operating review deck

Inputs típicos:

- evidence packs
- findings
- repository state
- action backlog

## 7. Candidate / talent decks

Decks de people intelligence usando a trilha de CV e structured extraction.

Exemplos:

- candidate review deck
- candidate comparison deck
- hiring decision deck

Inputs típicos:

- CV structured extraction
- comparison findings
- recommendation

---

## Catálogo inicial recomendado da capability

Para o roadmap ficar objetivo, a capability deve começar com um catálogo explícito de tipos prioritários.

### P1 — Benchmark & Eval Executive Review Deck

Primeiro deck a fechar porque já existe base estruturada e contrato em andamento.

Objetivo:

- traduzir benchmark/evals em visão executiva
- mostrar recomendação, watchouts e próximos passos

### P2 — Document Review Deck

Primeiro deck fortemente enterprise.

Objetivo:

- resumir documento
- destacar riscos/lacunas
- organizar recomendações

### P3 — Policy / Contract Comparison Deck

Extensão natural do produto documental.

Objetivo:

- mostrar diferenças relevantes
- destacar impacto de negócio
- apoiar decisão/revisão humana

### P4 — Action Plan Deck

Objetivo:

- transformar findings e checklists em plano operacional executável

### P5 — Candidate Review Deck

Objetivo:

- aproveitar a trilha `cv_analysis` para gerar deck executivo de avaliação de candidato

### P6 — Evidence Pack / Audit Deck

Objetivo:

- transformar outputs do EvidenceOps em handoff executivo de auditoria/compliance

---

## Prioridade realista para o roadmap

### Agora

1. **Benchmark & Eval Executive Review Deck**

### Em seguida

2. **Document Review Deck**
3. **Policy / Contract Comparison Deck**

### Depois

4. **Action Plan Deck**
5. **Candidate Review Deck**
6. **Evidence Pack / Audit Deck**

Essa ordem é a mais forte porque vai de:

- dados mais estruturados e fáceis de consolidar
- para casos enterprise mais ricos
- e depois para famílias mais premium do catálogo

---

## Modelo de contratos da capability

O produto deve crescer por **catálogo de contratos/versionamentos**, não por lógica solta na UI.

### Conceitos principais

- `contract_version`
- `export_kind`
- `deck_family`

### Catálogo-alvo de `export_kind`

Sugestão de direção oficial:

- `benchmark_eval_executive_review`
- `document_review_deck`
- `policy_contract_comparison_deck`
- `action_plan_deck`
- `candidate_review_deck`
- `evidence_pack_deck`

### Importante sobre o estado atual

Hoje, o primeiro slice técnico já implementado no repositório ainda usa a nomenclatura:

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

Isso deve ser lido como **fundação técnica já existente** do P1, não como naming final da capability inteira.

---

## Estado atual do repositório

Hoje o projeto já tem fundação concreta para o primeiro tipo de deck.

### Já existe

- contrato técnico do slice benchmark/eval
- builder de contrato no AI Workbench
- adapter para payload compatível com o `ppt_creator`
- testes unitários focados
- documentação inicial de productização do primeiro slice

Arquivos principais:

- `src/services/presentation_export.py`
- `tests/test_presentation_export_unittest.py`
- `docs/PRESENTATION_EXPORT_BENCHMARK_EVAL_CONTRACT_V1.md`
- `docs/PHASE_10_25_PRESENTATION_EXPORT_PRODUCTIZATION.md`

### Ainda falta

- service HTTP real para o renderer
- UX explícita no app principal
- catálogo oficial de `export_kind`s
- lifecycle de artefatos por export
- observabilidade específica da capability
- expansão para famílias além de benchmark/eval

---

## Roadmap da capability

## Slice 0 — Foundation do primeiro deck

**Status: já iniciado / parcialmente entregue**

- contrato do benchmark/eval
- builder
- adapter
- testes de fundação

## Slice 1 — Primeiro deck operacional

Fechar o **Benchmark & Eval Executive Review Deck** como primeira capability utilizável no produto.

Entregas:

- `presentation_export_service`
- chamada HTTP ao `ppt_creator_app`
- persistência local dos artefatos
- UX mínima no app atual

## Slice 2 — Primeiro deck enterprise documental

Fechar o **Document Review Deck**.

Entregas:

- contrato dedicado
- mapping de findings/riscos/recommendations
- deck executivo de review

## Slice 3 — Comparison / decision layer

Fechar o **Policy / Contract Comparison Deck** e preparar a base para **Decision Decks**.

## Slice 4 — Operational action layer

Fechar o **Action Plan Deck**.

## Slice 5 — Talent / EvidenceOps expansion

Fechar:

- Candidate Review Deck
- Evidence Pack / Audit Deck

## Slice 6 — UI e recorrência do produto

Transformar a capability em superfície real do produto:

- catálogo visível de deck types
- acionamento por fluxo
- histórico de decks gerados
- integração com Gradio / app web

---

## UX esperada do produto

Na UI, isso não deve aparecer como “usar projeto de PPT”.

Deve aparecer como capability do AI Workbench, por exemplo:

- **Executive Deck Generation**
- **Generate executive deck**
- **Business review decks**

### O que a UX deve permitir no futuro

- escolher o tipo de deck
- revisar o input grounded
- gerar o deck
- baixar `.pptx`
- baixar contrato/payload
- consultar exports recentes

---

## Por que isso fortalece o projeto como produto de AI para negócios

Porque negócio não quer só:

- chat
- JSON
- análise técnica crua

Negócio quer:

- síntese executiva
- recommendation
- decision support
- action plan
- handoff apresentável

Executive Deck Generation fecha exatamente essa lacuna.

---

## Critério de sucesso

Essa capability estará bem definida quando o roadmap deixar claro:

1. quais famílias de decks existem
2. quais são P1, P2 e P3
3. qual é o boundary entre AI Workbench e `ppt_creator_app`
4. como os contratos crescem por `export_kind`
5. como isso vira produto recorrente, e não apenas export isolado

---

## Documentos relacionados

- `proximos_passos.md`
- `docs/PRESENTATION_EXPORT_BENCHMARK_EVAL_CONTRACT_V1.md`
- `docs/PHASE_10_25_PRESENTATION_EXPORT_PRODUCTIZATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENTATION_PLAN.md`
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG.md`
- `docs/EXECUTIVE_DECK_GENERATION_ROUTING.md`
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_VERSIONING.md`
- `docs/EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE.md`
- `docs/EXECUTIVE_DECK_GENERATION_API_CONTRACT.md`
- `docs/EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE.md`
- `docs/EXECUTIVE_DECK_GENERATION_SLIDE_RECIPES.md`
- `docs/EXECUTIVE_DECK_GENERATION_RENDERER_MAPPING.md`
- `docs/EXECUTIVE_DECK_GENERATION_BRANDING_POLICY.md`
- `docs/EXECUTIVE_DECK_GENERATION_FAILURE_MODES.md`
- `docs/EXECUTIVE_DECK_GENERATION_UX_SPEC.md`
- `docs/EXECUTIVE_DECK_GENERATION_UI_EVOLUTION.md`
- `docs/EXECUTIVE_DECK_GENERATION_USER_JOURNEYS.md`
- `docs/EXECUTIVE_DECK_GENERATION_TEST_STRATEGY.md`
- `docs/EXECUTIVE_DECK_GENERATION_QUALITY_AND_GOVERNANCE.md`
- `docs/EXECUTIVE_DECK_GENERATION_OBSERVABILITY.md`
- `docs/EXECUTIVE_DECK_GENERATION_SECURITY_AND_PII.md`
- `docs/EXECUTIVE_DECK_GENERATION_ROLLOUT_AND_GOVERNANCE.md`
- `docs/DOCUMENT_REVIEW_DECK_CONTRACT_V1.md`
- `docs/POLICY_CONTRACT_COMPARISON_DECK_CONTRACT_V1.md`
- `docs/ACTION_PLAN_DECK_CONTRACT_V1.md`
- `docs/CANDIDATE_REVIEW_DECK_CONTRACT_V1.md`
- `docs/EVIDENCE_PACK_DECK_CONTRACT_V1.md`
