# Fase 10.25 — split oficial entre produto em Gradio e AI Lab dashboard

## Objetivo

Formalizar a próxima evolução do projeto como um **split de superfícies**:

- **Gradio** para a superfície de **produto**
- **Streamlit** para a superfície de **AI Lab / dashboard de engenharia**

Esta decisão existe para resolver um problema de posicionamento e de UX:

- o produto não deve continuar parecendo um laboratório genérico
- o laboratório não deve competir com a narrativa de negócio
- a interface precisa refletir a separação entre **resolver uma dor real** e **medir/evoluir o sistema**

---

## Decisão oficial da fase

### Superfícies do ecossistema

O ecossistema passa a ser lido assim:

- **Produto principal** = interface em **Gradio**
- **AI Lab dashboard** = interface em **Streamlit**
- **serviços compartilhados / backend do domínio** = camada comum entre as duas superfícies

### Regra arquitetural

- **Gradio** mostra workflows de negócio
- **Streamlit** mostra benchmark, evals, observabilidade, model comparison, MCP/ops console e superfícies avançadas de engenharia
- a lógica de negócio não deve ficar presa a nenhuma dessas UIs

---

## Produto principal

### Definição oficial

> **Decision workflows grounded em documentos**

Essa passa a ser a definição principal do produto.

### Subworkflows principais do produto

O produto em Gradio deve nascer com quatro workflows principais:

1. **Document Review**
2. **Policy / Contract Comparison**
3. **Action Plan / Evidence Review**
4. **Candidate Review**

### Capability transversal do produto

Além dos quatro workflows, o produto passa a tratar **Executive Deck Generation** como capability transversal.

Isso significa:

- não é um workflow separado competindo pela narrativa principal
- é uma ação/capability que pode aparecer dentro dos workflows principais

Exemplos:

- `Document Review` -> gerar document review deck
- `Policy / Contract Comparison` -> gerar comparison / decision deck
- `Action Plan / Evidence Review` -> gerar action plan deck ou evidence pack deck
- `Candidate Review` -> gerar candidate review deck

---

## Onde `cv_analysis` entra nessa nova leitura

`cv_analysis` deixa de ser tratado como surface principal de produto.

Leitura recomendada:

- `cv_analysis` = **engine interna / capability de base**
- `Candidate Review` = **workflow de negócio exposto no produto**

Na prática:

- o nome técnico `cv_analysis` pode continuar existindo internamente
- a interface de produto deve falar em **Candidate Review**, não em `cv_analysis`

### O que `Candidate Review` deve entregar

- profile summary
- strengths
- gaps
- experiência relevante
- sinais de senioridade / aderência
- recommendation inicial
- deck executivo quando fizer sentido

---

## O que entra no AI Lab dashboard

O dashboard em Streamlit deve concentrar a leitura de engenharia do projeto, incluindo:

- model comparison
- benchmark de parsing / retrieval / embeddings / reranking
- evals e diagnosis
- runtime economics
- routing / guardrails / workflow traces
- observabilidade
- EvidenceOps MCP console e superfícies operacionais avançadas
- experimentação controlada de providers e runtimes

### Regra de UX

O AI Lab não deve ser a homepage do produto.

Ele existe para:

- desenvolver
- inspecionar
- validar
- comparar
- auditar

---

## Decisão recomendada sobre o Streamlit do lab

## Recomendação oficial agora

**Adaptar o Streamlit atual** para virar o primeiro **AI Lab dashboard**.

### Por que essa é a recomendação mais forte agora

- reaproveita a superfície que já concentra controles, benchmark, evals e observabilidade
- evita abrir duas frentes de reconstrução ao mesmo tempo
- reduz custo de transição enquanto o Gradio nasce como superfície de produto
- preserva o valor do app atual como console de engenharia

### O que isso significa na prática

No curto prazo, a direção recomendada é:

- **não criar imediatamente um novo Streamlit do zero**
- reorganizar o Streamlit atual para ele assumir explicitamente o papel de **AI Lab dashboard**

## Quando considerar um novo Streamlit separado

Um novo Streamlit específico para lab só deve ser aberto se, depois da refatoração inicial, aparecer pelo menos um destes sinais:

- o app atual continuar excessivamente misturado entre produto e laboratório
- a navegação continuar confusa mesmo após reposicionamento
- o acoplamento de estado e componentes atrapalhar a evolução do Gradio
- o custo de manter a superfície atual ficar maior do que separar um app novo

### Decision gate recomendado

Primeiro:

1. adaptar o Streamlit atual
2. validar a separação de superfícies
3. só então decidir se o lab merece um app Streamlit dedicado

---

## Como ficará o Streamlit adaptado

## Papel oficial

O Streamlit adaptado passa a ser o **AI Lab dashboard** do ecossistema.

Ele deve ser lido como:

- console de engenharia
- superfície de benchmark/evals/observabilidade
- ambiente de inspeção operacional
- painel para workflows avançados, experimentais ou diagnósticos

### Usuário-alvo do Streamlit

- você como builder do sistema
- entrevistador técnico querendo entender profundidade de engenharia
- operador técnico validando comportamento, custo, routing e qualidade

## Navegação proposta do Streamlit adaptado

### 1. Lab Overview

Objetivo:

- abrir o AI Lab com uma visão resumida do estado atual do sistema

Conteúdo sugerido:

- status geral dos runtimes
- resumo recente de benchmark/evals
- snapshot de observabilidade
- alertas operacionais principais
- atalhos para diagnosis e MCP

### 2. Benchmarks & Model Comparison

Objetivo:

- concentrar tudo que é comparação de modelo, runtime e estratégia

Conteúdo sugerido:

- model comparison
- benchmark de parsing/retrieval/embeddings/reranking
- relatórios agregados de benchmark
- comparação entre providers e quantizações

### 3. Evals & Diagnosis

Objetivo:

- transformar medições em leitura operacional de qualidade

Conteúdo sugerido:

- suites de eval
- histórico e tendências
- diagnosis / falhas persistentes
- quality gates
- sinais para adaptação ou refatoração de pipeline

### 4. Runtime & Observability

Objetivo:

- mostrar latência, custo, routing e traces

Conteúdo sugerido:

- runtime economics
- budget-aware routing
- latência por fluxo
- workflow traces
- gargalos de execução

### 5. Document Agent & Workflow Inspector

Objetivo:

- inspecionar o comportamento interno do agente documental

Conteúdo sugerido:

- intent routing
- tool selection
- guardrails
- needs review
- exemplos recentes de execução do workflow

### 6. EvidenceOps / MCP / Ops Console

Objetivo:

- concentrar a superfície operacional avançada do projeto

Conteúdo sugerido:

- repository state
- actions/worklog
- MCP health
- tools/resources MCP
- operações locais e externas do EvidenceOps

### 7. Structured / Advanced Experiments

Objetivo:

- manter playgrounds técnicos e superfícies experimentais fora da vitrine principal do produto

Conteúdo sugerido:

- extraction playground
- code analysis
- structured debugging
- OCR/VLM experiments
- shadow workflows e comparações experimentais

## O que deve sair da home do Streamlit

Para o Streamlit assumir de vez o papel de AI Lab, a home dele não deve mais parecer a homepage do produto.

Deixar de protagonizar:

- CTA principal de uso de negócio
- linguagem de produto final
- fluxos hero de `Document Review`, `Policy / Contract Comparison`, `Action Plan / Evidence Review` e `Candidate Review`
- geração de decks como call-to-action principal de usuário final

Esses elementos devem migrar para o **Gradio**.

---

## Como ficará o Gradio

## Papel oficial

O Gradio passa a ser a **superfície principal do produto**.

Leitura recomendada:

- experiência AI-first
- interface limpa para workflow de negócio
- superfície demonstrável para usuário não técnico

### Usuário-alvo do Gradio

- analista de negócio
- reviewer documental
- gestor/decisor
- hiring manager

## Shell comum do produto em Gradio

Independentemente do workflow escolhido, a estrutura base do produto deve ser parecida:

1. **home do produto** com os 4 workflows principais
2. **seleção do workflow**
3. **entrada documental** (upload, seleção de corpus ou contexto)
4. **preview grounded** dos insumos
5. **findings / recommendation / action output**
6. **ações finais** (download, export, deck, handoff)

## Workflows principais do Gradio

### 1. Document Review

Entradas:

- um ou mais documentos

Saídas esperadas:

- summary grounded
- risks/gaps
- findings estruturados
- ações recomendadas
- document review deck opcional

### 2. Policy / Contract Comparison

Entradas:

- dois documentos ou duas versões relacionadas

Saídas esperadas:

- diferenças relevantes
- impacto de negócio
- watchouts
- recommendation
- comparison / decision deck opcional

### 3. Action Plan / Evidence Review

Entradas:

- findings existentes
- evidence packs
- documentos operacionais

Saídas esperadas:

- owners
- tarefas
- prazos
- backlog operacional
- action plan deck ou evidence pack deck opcional

### 4. Candidate Review

Entradas:

- currículo(s)
- contexto opcional de vaga/perfil-alvo

Saídas esperadas:

- candidate summary
- strengths
- gaps
- sinais de aderência
- recommendation inicial
- candidate review deck opcional

### Nota importante sobre `cv_analysis`

No Gradio, o usuário não interage com uma task chamada `cv_analysis`.

O correto é:

- `cv_analysis` permanece no backend como engine interna
- a surface do produto mostra apenas **Candidate Review**

## O que não deve entrar no Gradio como protagonista

Para o Gradio manter cara de produto, não deve exibir como superfície principal:

- benchmark matrix
- model comparison detalhado
- provider knobs avançados
- OCR/VLM debug
- workflow trace técnico
- MCP console operacional
- shadow logs

### Exceção controlada

Elementos como grounding, status e warnings podem aparecer, desde que apresentados com linguagem de produto e não com cara de console técnico.

## Papel do chat livre após o split

O chat livre com documentos pode continuar existindo, mas não deve mais ser a homepage do produto.

Leitura recomendada:

- modo assistivo secundário dentro de workflows
- ou utilidade avançada preservada no AI Lab

---

## Mapa inicial de migração das superfícies

### Vai para o Streamlit adaptado

- model comparison
- benchmark reports
- eval suites e diagnosis
- runtime economics
- workflow traces
- MCP / EvidenceOps console
- superfícies avançadas de structured/debug
- code analysis e experimentação técnica adjacente

### Vai para o Gradio

- Document Review
- Policy / Contract Comparison
- Action Plan / Evidence Review
- Candidate Review
- downloads e artefatos finais dos workflows
- Executive Deck Generation como ação transversal do produto

### Permanece no backend compartilhado

- document ingestion
- grounding / retrieval
- structured outputs
- document agent / orchestration
- `cv_analysis`
- presentation export service
- adapters / contracts / observability

---

## Roadmap recomendado dentro da fase 10.25

## Slice 10.25A — split de superfícies e reposicionamento

Objetivo:

- separar oficialmente produto e lab
- definir o papel do Streamlit atual
- preparar contratos e boundaries para o Gradio

Checklist sugerido:

- classificar telas/controles atuais entre **produto** e **AI Lab**
- transformar o Streamlit atual em baseline oficial do AI Lab dashboard
- remover da narrativa principal do Streamlit os fluxos que devem migrar para o produto em Gradio
- extrair serviços compartilhados para evitar duplicação entre UIs
- formalizar o contract de cada workflow de negócio

## Slice 10.25B — produto em Gradio

Objetivo:

- criar a primeira superfície de produto clara e AI-first

Checklist sugerido:

- construir a home do produto em torno de **Decision workflows grounded em documentos**
- expor os quatro workflows principais
- integrar capability transversal de Executive Deck Generation
- promover `cv_analysis` para engine interna de `Candidate Review`
- manter feedback de status, grounding e downloads de artefatos

## Slice 10.25C — backend HTTP e app web

Objetivo:

- desacoplar definitivamente UI, backend e serviços especializados

Checklist sugerido:

- definir contratos HTTP claros entre frontend e backend
- mover integrações de deck generation para services de backend
- preparar a evolução de Gradio para app web
- manter o AI Lab como superfície paralela de engenharia

---

## Checklist consolidado da mudança

- [ ] mapear tudo o que hoje aparece no app atual entre **produto** e **AI Lab**
- [ ] definir navegação e home do Streamlit atual como dashboard de engenharia
- [ ] decidir o que sai da home do Streamlit e vai para o produto em Gradio
- [ ] formalizar `Decision workflows grounded em documentos` como headline do produto
- [ ] implementar os 4 workflows principais no Gradio
- [ ] promover `cv_analysis` para o workflow `Candidate Review`
- [ ] tratar Executive Deck Generation como capability transversal dos workflows
- [ ] desacoplar backend/serviços compartilhados das duas superfícies
- [ ] definir decision gate para saber se o Streamlit atual basta como AI Lab ou se um novo app será necessário

---

## Entregáveis esperados

- **AI Lab dashboard** em Streamlit, com foco em engenharia
- **produto em Gradio**, com foco em workflows de negócio
- boundary claro entre produto, lab e backend compartilhado
- roadmap explícito para a evolução posterior para app web

---

## O que preciso saber defender em entrevista

- por que separar produto e laboratório fortalece a narrativa do projeto
- por que o produto foi organizado em workflows de decisão grounded em documentos
- por que `Candidate Review` entra no produto, mas `cv_analysis` continua como engine interna
- por que o Streamlit atual foi reaproveitado primeiro como AI Lab dashboard
- por que Gradio foi escolhido como superfície intermediária de produto

---

## Documentos relacionados

- `docs/PROJECT_POSITIONING_TWO_TRACKS.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_UI_EVOLUTION.md`
- `proximos_passos.md`