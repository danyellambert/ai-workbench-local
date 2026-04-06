# Phase 10.25 — Productização do primeiro slice de Executive Deck Generation

## Objetivo

Este documento agora deve ser lido como a **documentação técnica do primeiro slice** da capability maior de **Executive Deck Generation**.

O contexto oficial e o catálogo da capability estão em:

- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

Aqui, o foco fica mais estreito:

- como transformar o `ppt_creator_app` em camada especializada do ecossistema atual
- como fechar o primeiro deck prioritário
- como sair do contrato para integração HTTP e UX mínima

Neste momento, o slice técnico priorizado continua sendo:

- **benchmark/eval -> executive review deck**

O `ppt_creator_app` entra como a **camada especializada de renderização executiva** dentro dessa capability maior.

> Em resumo: `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md` define a capability de produto; este documento detalha a productização técnica do primeiro slice.

Documentos complementares importantes para a implementação completa da capability:

- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENTATION_PLAN.md`
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG.md`
- `docs/EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE.md`
- `docs/EXECUTIVE_DECK_GENERATION_API_CONTRACT.md`
- `docs/EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE.md`
- `docs/EXECUTIVE_DECK_GENERATION_UX_SPEC.md`
- `docs/EXECUTIVE_DECK_GENERATION_TEST_STRATEGY.md`
- `docs/EXECUTIVE_DECK_GENERATION_QUALITY_AND_GOVERNANCE.md`

---

## Relação com a capability maior

O projeto agora deve ser lido assim:

- **AI Workbench Local** = produto principal de IA aplicada
- **Executive Deck Generation** = capability recorrente do produto
- **`ppt_creator_app`** = renderer especializado que viabiliza essa capability

As famílias de decks prioritárias passam a ser:

- summary / executive review decks
- document review decks
- comparison / decision decks
- action-plan decks
- candidate review decks
- evidence / audit decks

Este documento cobre a camada de productização do **P1**:

- **Benchmark & Eval Executive Review Deck**

---

## Why this strengthens the product capability

Essa feature melhora muito a narrativa profissional do projeto porque fecha um ciclo muito forte:

1. o sistema mede qualidade com benchmark/evals
2. consolida resultados em contrato estruturado
3. transforma isso em artefato executivo consumível por negócio
4. mantém separação clara entre domínio, orquestração e renderização

Isso ajuda a mostrar que o projeto não é apenas:

- chat com LLM
- RAG com documentos
- outputs estruturados

Ele passa a mostrar também:

- **product thinking**
- **design de contratos versionados**
- **integração entre serviços especializados**
- **geração de artefatos de negócio**
- **QA e observabilidade de uma feature fim a fim**

Na prática, isso fortalece a leitura de que você sabe fazer a ponte entre:

- camada de IA aplicada
- camada de software/arquitetura
- camada de entrega executiva para stakeholder

---

## Decisão arquitetural oficial

Esta é a decisão que melhor preserva a força do projeto.

### O que continua no AI Workbench Local

O AI Workbench continua sendo a **fonte da verdade** para:

- benchmark
- evals
- EvidenceOps
- structured outputs
- consolidação de métricas
- recomendação executiva

### O que fica no `ppt_creator_app`

O `ppt_creator_app` continua sendo o serviço especializado em:

- validar schema de apresentação
- renderizar `.pptx`
- revisar qualidade visual
- gerar previews
- comparar artefatos

### O boundary correto

O boundary mais forte é:

**AI Workbench Local = inteligência de domínio + orquestração**  
**`ppt_creator_app` = renderização executiva especializada**

### O que não fazer

Para preservar essa arquitetura, a direção recomendada é **não**:

- copiar o código do `ppt_creator_app` para dentro do AI Workbench
- acoplar o AI Workbench ao schema cru do renderer cedo demais
- usar a camada `ppt_creator_ai/` para este slice de benchmark/eval
- transformar exportação de deck em lógica espalhada pela UI

Para este caso de uso, a melhor leitura é **determinística**:

**benchmark/eval -> contrato estruturado -> payload de apresentação -> render `.pptx`**

Sem LLM no meio da etapa final de exportação do deck executivo.

Isso é importante porque transmite disciplina de engenharia e reduz risco de ruído/hallucination na última milha.

---

## Estado atual já existente

### No AI Workbench Local

Já existe fundação concreta para o primeiro slice.

#### Documento-base do slice técnico atual

- `docs/EXECUTIVE_DECK_GENERATION_BENCHMARK_EVAL_CONTRACT_V1.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

#### Serviço de contrato e adapter já implementados

- `src/services/presentation_export.py`

Hoje ele já entrega:

- contrato versionado `presentation_export.v1`
- `export_kind = "benchmark_eval_executive_deck"`
- builder a partir de agregados/logs do projeto
- adapter para payload compatível com o `ppt_creator`

Funções já existentes:

- `build_benchmark_eval_contract(...)`
- `build_benchmark_eval_contract_from_logs(...)`
- `build_ppt_creator_payload_from_benchmark_eval_contract(...)`

#### Testes já existentes

- `tests/test_presentation_export_unittest.py`

Esses testes já validam:

- criação do contrato concreto a partir dos logs
- presença de métricas/highlights/leaderboards
- sequência esperada de slides no payload do `ppt_creator`

### No `ppt_creator_app`

O projeto irmão já está suficientemente maduro para entrar como serviço especializado.

#### Documentação principal

- `/Users/danyellambert/ppt_creator_app/README.md`
- `/Users/danyellambert/ppt_creator_app/NEXT_STEPS.md`

#### Capabilities já disponíveis

- renderer `.pptx`
- schema com `pydantic`
- API HTTP local
- review de qualidade
- preview
- compare de `.pptx`
- artifact serving
- playground/editor local

#### Endpoints úteis já existentes

Segundo o `README.md` e `ppt_creator/api.py`, já existem endpoints como:

- `GET /health`
- `GET /artifact`
- `POST /validate`
- `POST /review`
- `POST /preview`
- `POST /render`

#### Compatibilidade de schema relevante

O `ppt_creator/schema.py` já suporta os tipos de slide que o slice atual usa:

- `title`
- `summary`
- `metrics`
- `table`
- `comparison`
- `bullets`

Ou seja: a compatibilidade estrutural principal do primeiro slice já existe.

---

## Gap real entre o estado atual e a feature de produto

Apesar da fundação já existir, ainda faltam camadas importantes para isso virar feature real do AI Workbench.

### Gap 1 — integração HTTP ainda não existe

Hoje o AI Workbench:

- gera contrato
- gera payload

Mas ainda **não chama** o `ppt_creator_app` por HTTP.

### Gap 2 — configuração ainda não existe

Ainda não há no projeto atual uma configuração explícita para presentation export, por exemplo:

- base URL do serviço
- timeout
- diretórios remotos de output/preview
- política de artefatos

### Gap 3 — UX ainda não existe

Ainda não existe no app principal:

- ação explícita de exportar deck executivo
- download do `.pptx`
- visualização do status do export
- fallback quando o serviço de decks estiver offline

### Gap 4 — ciclo de artefato ainda não existe

Ainda não existe fluxo padrão para persistir:

- contrato JSON
- payload enviado ao renderer
- resposta do renderer
- `.pptx` final
- review/previews relacionados

### Gap 5 — observabilidade específica da feature ainda não existe

Ainda faltam sinais operacionais da exportação, como:

- sucesso/falha por export
- latência do renderer
- tamanho do artefato
- quantos previews foram gerados
- taxa de indisponibilidade do serviço

### Gap 6 — integração de produto ainda não existe

A feature ainda não foi encaixada de forma clara na trilha:

- Streamlit atual
- futura UI em Gradio
- futuro app web/backend HTTP da Fase 10.25

---

## Tese oficial da feature

O `ppt_creator_app` **não** deve aparecer como um produto paralelo dentro do AI Workbench.

Ele deve ser posicionado como uma capability do produto:

> O AI Workbench Local transforma sinais de benchmark, eval, EvidenceOps e outputs estruturados em artefatos executivos reproduzíveis.

No primeiro slice, isso significa:

> A partir dos logs e agregados de benchmark/eval, o sistema gera um deck executivo `.pptx` pronto para revisão, compartilhamento e demonstração.

Essa tese é forte porque mostra que o projeto sabe:

- medir qualidade
- consolidar evidências
- traduzir sinais técnicos em narrativa executiva
- gerar entregável de negócio reutilizável

---

## Ordem recomendada de implementação

Esta é a ordem mais forte para produto, engenharia e portfólio.

### Slice 0 — fundação de contrato e adapter

**Status:** já entregue.

- [x] contrato versionado
- [x] builder no AI Workbench
- [x] adapter para payload compatível com `ppt_creator`
- [x] testes unitários da fundação

### Slice 1 — integração síncrona por HTTP

**Próximo passo recomendado.**

Objetivo: sair de “payload pronto” para “deck `.pptx` gerado sob demanda”.

Entrega mínima:

- [x] criar `presentation_export_service` no AI Workbench
- [x] chamar `GET /health` do `ppt_creator_app` antes do render
- [x] chamar `POST /render` com payload do deck executivo
- [x] baixar o `.pptx` via `GET /artifact`
- [x] salvar artefatos locais do export no AI Workbench
- [x] retornar resultado estruturado para a UI

### Slice 2 — UX no app atual (Streamlit)

Objetivo: transformar a integração em feature visível de produto.

Entrega mínima:

- [x] botão **Exportar deck executivo**
- [x] download do `.pptx`
- [x] download do contrato JSON
- [x] download do payload JSON
- [x] exibir status/erro de forma amigável

### Slice 3 — endurecimento do ciclo de artefatos

Objetivo: tornar a feature auditável e reaproveitável.

Entrega mínima:

- [ ] diretório/versionamento local por `export_id`
- [ ] persistência de metadados do export
- [ ] retention/limpeza de artefatos antigos
- [ ] log operacional da feature

### Slice 4 — integração na Fase 10.25

Objetivo: encaixar a feature no backend HTTP e na evolução Streamlit -> Gradio -> app web.

Entrega mínima:

- [ ] endpoint de export no backend do AI Workbench
- [ ] exposição da capability na UI intermediária
- [ ] ação explícita no futuro app web

### Slice 5 — expansão de `export_kind`

Depois do slice benchmark/eval estar sólido, ampliar para novos decks.

Ordem sugerida:

1. `benchmark_eval_executive_deck`
2. `evidenceops_document_review_deck`
3. `phase_closure_or_project_review_deck`

### Slice 6 — endurecimento operacional

Só depois da feature já ser útil e estável:

- [ ] Docker/compose do `ppt_creator_app`
- [ ] timeouts e retries mais fortes
- [ ] fila assíncrona para renders pesados
- [ ] estratégia de deploy híbrido

---

## O menor slice demonstrável com melhor custo/benefício

Se a meta for fechar o **melhor MVP demonstrável** dessa feature sem abrir escopo demais, a recomendação é:

1. manter o contrato v1 atual
2. criar `presentation_export_service`
3. fazer export síncrono do deck de benchmark/eval
4. salvar localmente:
   - contrato
   - payload
   - resposta do render
   - `.pptx`
5. expor um botão na UI atual
6. adicionar testes focados do service

Esse slice já é suficiente para demonstrar:

- design de contrato
- integração entre serviços
- geração de artefato real
- UX de produto
- capacidade de traduzir benchmark/eval em deck executivo

---

## Design recomendado da integração no AI Workbench

## 1. Camada de configuração

Adicionar uma configuração dedicada para a feature.

### Variáveis sugeridas

```env
PRESENTATION_EXPORT_ENABLED=true
PRESENTATION_EXPORT_BASE_URL=http://127.0.0.1:8787
PRESENTATION_EXPORT_TIMEOUT_SECONDS=120
PRESENTATION_EXPORT_REMOTE_OUTPUT_DIR=outputs/ai_workbench_exports
PRESENTATION_EXPORT_REMOTE_PREVIEW_DIR=outputs/ai_workbench_export_previews
PRESENTATION_EXPORT_LOCAL_ARTIFACT_DIR=artifacts/presentation_exports
PRESENTATION_EXPORT_INCLUDE_REVIEW=true
PRESENTATION_EXPORT_PREVIEW_BACKEND=auto
PRESENTATION_EXPORT_REQUIRE_REAL_PREVIEWS=false
PRESENTATION_EXPORT_FAIL_ON_REGRESSION=false
```

### Onde isso entra

- `src/config.py`
- `.env.example`

### Por que isso importa

Isso transforma exportação executiva em **parte do produto**, e não em detalhe hardcoded da máquina local.

---

## 2. Camada de serviço

Criar um serviço dedicado no AI Workbench, por exemplo:

- `src/services/presentation_export_service.py`

### Responsabilidades desse serviço

- validar se a feature está habilitada
- verificar saúde do `ppt_creator_app`
- montar contrato e payload
- decidir nomes/diretórios remotos dos artefatos
- chamar o renderer por HTTP
- baixar artefatos relevantes
- persistir cópias locais e metadados
- devolver resultado estruturado para a UI e para futuros endpoints

### Recomendação de boundary

O service **não** deve saber montar slides “na mão”.

Ele deve delegar isso para o fluxo já existente:

- `build_benchmark_eval_contract_from_logs(...)`
- `build_ppt_creator_payload_from_benchmark_eval_contract(...)`

### Recomendação de cliente HTTP

Preferir uma implementação leve e consistente com o resto do projeto.

Como o repositório já usa `urllib` em outras integrações, a escolha mais coerente para o primeiro slice é:

- `urllib.request`

Isso evita adicionar dependência nova só para essa feature.

---

## 3. Estratégia de paths e artefatos

Esse ponto é importante.

Pelo comportamento atual do `ppt_creator/api.py`, o fluxo mais natural é:

1. o AI Workbench pede render com `output_path` remoto
2. o `ppt_creator_app` salva o arquivo dentro do workspace dele
3. o AI Workbench baixa o artefato via `GET /artifact`
4. o AI Workbench persiste uma cópia local como artefato próprio

### Por que essa estratégia é a melhor para o primeiro slice

Porque ela:

- reaproveita a API já existente
- evita shared volume cedo demais
- evita mudar o renderer para retornar bytes agora
- preserva o boundary HTTP-first definido no roadmap

### Estrutura remota sugerida no `ppt_creator_app`

```text
outputs/ai_workbench_exports/
  <export_id>/
    benchmark_eval_deck.pptx
    previews/
```

### Estrutura local sugerida no AI Workbench

```text
artifacts/presentation_exports/
  <export_id>/
    contract.json
    ppt_creator_payload.json
    render_response.json
    benchmark_eval_deck.pptx
    review.json
    preview_manifest.json
    thumbnail_sheet.png
```

### Resultado

Assim, o AI Workbench passa a ter rastreabilidade completa da feature sem depender do filesystem interno do serviço de decks.

---

## 4. Fluxo HTTP recomendado

### Preflight

Primeiro, o AI Workbench consulta:

- `GET /health`

Se o serviço estiver offline:

- a UI deve falhar de forma amigável
- o usuário ainda deve poder baixar `contract.json` e `payload.json`

### Render

Depois, chama:

- `POST /render`

Payload recomendado para o primeiro slice:

```json
{
  "spec": {
    "presentation": {
      "title": "AI Workbench Local — Benchmark & Eval Review",
      "subtitle": "Resumo executivo da rodada atual",
      "author": "AI Workbench Local",
      "date": "2026-04-05",
      "theme": "executive_premium_minimal",
      "footer_text": "AI Workbench Local • Benchmark & Eval Review"
    },
    "slides": []
  },
  "output_path": "outputs/ai_workbench_exports/<export_id>/benchmark_eval_deck.pptx",
  "include_review": true,
  "preview_output_dir": "outputs/ai_workbench_exports/<export_id>/previews",
  "preview_backend": "auto",
  "preview_require_real": false,
  "preview_fail_on_regression": false
}
```

### Download dos artefatos

Depois do render:

- baixar o `.pptx` via `GET /artifact?path=...`
- persistir `render_response.json`
- se existirem caminhos de preview/manifest/thumbnail relevantes, salvá-los também

---

## 5. Resultado estruturado da feature

O `presentation_export_service` deve devolver algo estruturado, e não um dicionário cru da API.

Exemplo de campos úteis do resultado:

- `export_id`
- `export_kind`
- `contract_version`
- `status`
- `service_health`
- `remote_output_path`
- `local_artifact_dir`
- `local_pptx_path`
- `local_contract_path`
- `local_payload_path`
- `local_render_response_path`
- `local_review_path`
- `local_preview_manifest_path`
- `thumbnail_sheet_path`
- `warnings`
- `error_message`

Isso ajuda muito a evitar acoplamento da UI a detalhes internos da chamada HTTP.

---

## Como a feature deve aparecer na UI

## Princípio de produto

Na UI, a capability deve aparecer como algo do produto, por exemplo:

- **Exportar deck executivo**
- **Executive artifacts**

E não como:

- “abrir ppt_creator_app”
- “usar projeto irmão”

### Melhor ponto de entrada inicial

Pelo estado atual do projeto, o melhor ponto de entrada inicial é perto da área onde benchmark/evals já são lidos como sinais executivos.

Como `src/ui/sidebar.py` já expõe sinais agregados de eval/readiness, o primeiro encaixe forte pode ser:

- um expander/painel dedicado de exportação executiva
- ou um painel visual separado no fluxo de benchmark/evals

### Ações mínimas da UI

No primeiro slice, a UI deve permitir:

- gerar deck
- baixar `.pptx`
- baixar contrato
- baixar payload
- ver status do export
- ver warnings/fallbacks

### Ações desejáveis depois

- abrir thumbnail sheet
- baixar review do deck
- listar exports recentes
- reexecutar export do mesmo snapshot

---

## Por que não usar `ppt_creator_ai/` neste slice

Isso é uma decisão importante.

O `ppt_creator_app` tem uma camada opcional `ppt_creator_ai/`, mas **ela não deve ser parte do primeiro slice do AI Workbench**.

### Motivo

Neste caso de uso, o AI Workbench já tem os dados e a inteligência de domínio.

Ele já sabe:

- qual é o top model
- qual é o PASS rate
- quais watchouts existem
- quais são os próximos passos

Logo, o caminho mais forte é:

**determinístico e auditável**, não generativo.

### Benefício profissional

Isso mostra maturidade de AI Engineer porque demonstra que você sabe:

- onde usar LLM
- onde **não** usar LLM
- quando preferir contrato estruturado e render determinístico

---

## Testes necessários para a feature completa

## O que já existe

- [x] teste do builder do contrato
- [x] teste do adapter para payload

## O que ainda precisa existir

### Testes unitários do service

- [x] `tests/test_presentation_export_service_unittest.py`

Deve cobrir pelo menos:

- montagem de paths remotos
- render request correto
- tratamento de indisponibilidade do serviço
- timeout HTTP
- persistência local de artefatos
- fallback quando `/health` falha

### Testes de integração opcionais

- [ ] smoke test com `ppt_creator_app` rodando localmente

Esse teste não precisa rodar sempre no CI principal se o serviço irmão não fizer parte do ambiente padrão. Mas deve existir como trilha reproduzível local.

### Testes de UI

- [ ] smoke test do painel de exportação executiva

O objetivo não é testar rendering real do `.pptx` na UI, e sim:

- botão presente
- status tratado
- download/fallback coerentes

---

## Observabilidade da feature

Para essa capability ficar profissional, é importante instrumentar a exportação.

### Sinais mínimos

- `export_id`
- `export_kind`
- `contract_version`
- `service_available`
- `render_latency_s`
- `artifact_download_latency_s`
- `pptx_size_bytes`
- `preview_count`
- `export_status`
- `error_type`

### Onde registrar

Esses sinais podem entrar em um log leve/versionado do AI Workbench, sem depender de observabilidade pesada nesta fase.

### Por que isso importa

This makes it clearer that the feature was not added as an isolated integration, but as a capability with an explicit technical boundary:

- monitorada
- auditável
- preparada para crescer

---

## Como essa feature se encaixa na Fase 10.25

No roadmap, a Fase 10.25 é a evolução:

- Streamlit -> Gradio -> app web

O export executivo entra muito bem aqui porque ele é uma capability transversal de interface e backend.

### Leitura correta

Essa feature é mais forte quando evolui assim:

1. **primeiro**: export no app atual, com UX simples e comprovada
2. **depois**: endpoint interno do AI Workbench para export
3. **depois**: superfície em Gradio/web
4. **só depois**: Docker/deploy híbrido do serviço especializado

### Por que essa ordem é a melhor

Porque ela preserva a narrativa de engenharia madura:

- primeiro fundação de domínio
- depois integração entre serviços
- depois UX
- depois deploy

---

## Expansão futura recomendada de `export_kind`

Depois do slice benchmark/eval, a direção mais forte é reaproveitar a mesma fundação para novos artefatos.

### 1. `benchmark_eval_executive_deck`

Primeiro porque já existe base pronta.

### 2. `evidenceops_document_review_deck`

Muito forte para demonstração de produto empresarial.

Exemplos de blocos futuros:

- executive summary
- risks and obligations
- evidence-backed findings
- recommended actions
- owners and due dates

### 3. `project_phase_closure_deck`

Útil para mostrar o próprio projeto como caso de engenharia profissional.

Exemplos de blocos futuros:

- entregas concluídas
- benchmarks/evals da fase
- trade-offs
- próximos passos

---

## Critério de done por nível

## Done técnico mínimo

Podemos considerar a feature tecnicamente integrada quando existir:

- [x] export síncrono funcionando do AI Workbench para o `ppt_creator_app`
- [x] download do `.pptx`
- [x] persistência local de contrato/payload/response
- [x] testes do service
- [x] UI mínima com ação explícita de export

## Done de produto

A feature começa a ter cara de produto quando existir:

- [ ] naming correto de capability
- [ ] UX clara de sucesso/falha/download
- [ ] exports recentes ou artefatos organizados
- [ ] documentação da feature no repositório

## Done de portfólio

A feature vira evidência forte de AI Engineer quando existir:

- [ ] screenshot/GIF do export acontecendo
- [ ] deck real gerado a partir de benchmark/eval
- [ ] diagrama da arquitetura `domain contract -> renderer service`
- [ ] write-up curto explicando o porquê da separação entre AI Workbench e `ppt_creator_app`

---

## O que essa feature prova sobre você como AI Engineer

Se implementada nessa direção, essa feature ajuda a provar que você sabe:

- transformar sinais técnicos em artefatos de negócio
- projetar contratos versionados entre serviços
- evitar acoplamento precoce entre domínio e renderer
- escolher caminho determinístico quando isso é melhor que usar LLM
- encaixar uma capability nova na evolução de produto e interface
- pensar em observabilidade, QA e lifecycle de artefatos

Em outras palavras, a leitura desejada passa a ser:

> esta pessoa não só constrói pipelines de IA e mede qualidade; ela também sabe empacotar os resultados em uma capability de produto clara, defensável e útil para stakeholders.

---

## Resumo executivo da recomendação

O caminho mais forte é manter o que já foi decidido:

- **AI Workbench Local** continua como cérebro e fonte da verdade
- **`ppt_creator_app`** entra como serviço especializado de artefatos executivos
- o primeiro slice oficial continua sendo **benchmark/eval -> executive deck**
- a implementação correta é **HTTP first**, **Docker depois**
- o primeiro caminho de produto deve ser **determinístico**, sem depender de `ppt_creator_ai/`

### Próxima entrega recomendada

Se for escolher apenas uma próxima entrega concreta, a melhor é:

> implementar `presentation_export_service` + botão de exportação executiva no app atual + persistência local dos artefatos do render.

Esse é o menor slice que já transforma a fundação atual em uma feature real, demonstrável e muito forte para portfólio.