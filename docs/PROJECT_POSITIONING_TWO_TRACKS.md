# Posicionamento do projeto — duas trilhas oficiais

## Objetivo

Documentar de forma explícita como o projeto deve ser entendido daqui para frente para evitar uma leitura confusa entre:

- produto de negócio
- laboratório de modelos / evals / arquitetura

Este documento formaliza a proposta de organizar o ecossistema atual em **duas trilhas oficiais e complementares**.

---

## Problema que este documento resolve

Hoje o repositório já reúne muita coisa valiosa ao mesmo tempo:

- RAG com documentos
- structured outputs
- document agent
- benchmark e evals
- runtime economics
- EvidenceOps
- MCP
- Executive Deck Generation
- CV analysis
- code analysis

O problema não é existir amplitude técnica.
O problema é quando tudo isso aparece com o mesmo peso na narrativa externa.

Sem uma organização explícita, o projeto pode parecer:

- um laboratório genérico sem foco de produto
- ou dois projetos concorrentes dentro do mesmo repositório

Este documento resolve isso definindo a leitura oficial:

> **o projeto tem uma trilha principal de produto para resolver um problema de negócio e uma trilha de AI Engineering Lab para medir, comparar e evoluir os blocos que sustentam esse produto.**

---

## Tese oficial

O **AI Workbench Local** deve ser entendido como uma plataforma de IA aplicada com **duas trilhas complementares**:

1. **Business Workflows / produto**  
   camada orientada a resolver um problema de negócio real

2. **AI Engineering Lab**  
   camada orientada a benchmark, evals, observabilidade, routing e confiabilidade

Essas duas trilhas **não são dois produtos concorrentes**.

A leitura correta é:

- **o produto resolve o problema do usuário**
- **o lab garante que o produto seja confiável, auditável e evoluível**

---

## Trilha 1 — Business Workflows / produto

## Problema de negócio

Empresas têm dificuldade de transformar documentos em:

- respostas grounded
- revisão comparativa
- achados estruturados
- plano de ação
- comunicação executiva pronta para revisão humana

### Leitura de produto recomendada

As leituras mais fortes para esta trilha são:

- **Document Intelligence for Decision Support**
- **Document Operations Copilot**
- **Business workflows grounded em documentos e evidências**

### Produto principal oficial

A formulação oficial do produto passa a ser:

> **Decision workflows grounded em documentos**

### Frase curta recomendada

> Sistema que transforma documentos corporativos em análise grounded, findings estruturados, ações recomendadas e artefatos executivos utilizáveis.

---

## Hero workflows recomendados

Para manter foco de produto, a trilha principal deve priorizar workflows que levem de **documento -> análise -> ação**.

### 1. Document Review

Fluxo:

1. ingestão de documento(s)
2. análise grounded
3. identificação de riscos, gaps e achados
4. saída estruturada pronta para revisão humana

### 2. Policy / Contract Comparison

Fluxo:

1. seleção de duas versões ou documentos relacionados
2. comparação grounded
3. diferenças relevantes e impacto
4. recomendação ou próximos passos

### 3. Action Plan / Evidence Review

Fluxo:

1. consolidação de findings
2. extração de owners, tarefas e prazos
3. registro operacional auditável
4. handoff para acompanhamento humano

### 4. Candidate Review

Fluxo:

1. ingerir currículo(s) e contexto relevante
2. estruturar perfil, strengths e gaps
3. produzir recommendation pronta para revisão humana
4. opcionalmente gerar artefato executivo para hiring manager

### Capability transversal — Executive Deck Generation

Executive Deck Generation continua dentro da trilha de produto, mas passa a ser entendido como **capability transversal** dos workflows, e não como workflow principal separado.

Exemplos:

- Document Review -> document review deck
- Policy / Contract Comparison -> comparison / decision deck
- Action Plan / Evidence Review -> action plan deck ou evidence pack deck
- Candidate Review -> candidate review deck

---

## Capabilities atuais que pertencem à trilha de produto

As capacidades abaixo devem ser entendidas como parte da solução de negócio:

- `document_agent`
- `summary`
- `extraction`
- `checklist`
- comparação documental
- risk/compliance review
- extração de tarefas operacionais
- `candidate_review`
- `cv_analysis` quando usado como engine interna do workflow de `Candidate Review`
- EvidenceOps quando aparece como workflow operacional do produto
- Executive Deck Generation para review, comparison, action plan e evidence handoff
- MCP quando estiver servindo repository/actions/worklog do workflow de negócio

### Regra prática

Tudo o que ajuda o usuário final a sair de:

**documento -> entendimento -> decisão -> ação -> artefato executivo**

pertence à trilha de produto.

---

## O que não deve ser protagonista na trilha de produto

Os itens abaixo podem continuar existindo no produto, mas **não devem liderar a narrativa externa** desta trilha:

- benchmark matrix
- comparação extensa de providers/modelos
- eval store
- runtime economics detalhado
- detalhes internos de routing/guardrails
- logs de shadow workflow

Esses itens pertencem principalmente ao **AI Engineering Lab**.

---

## Trilha 2 — AI Engineering Lab

## Objetivo

Esta trilha existe para responder perguntas de engenharia como:

- qual modelo ou runtime entrega melhor resultado?
- quando usar retrieval, document scan, OCR ou VLM?
- como medir qualidade de forma reprodutível?
- como auditar custo, latência e fallback?
- como promover mudanças sem degradar o comportamento do produto?

### Leitura recomendada

- **AI Engineering Lab**
- **Model & RAG Evaluation Lab**
- **Reliability / Evaluation Layer**

### Frase curta recomendada

> Camada de engenharia que mede, compara e evolui modelos, rotas, parsing e workflows para sustentar um produto de IA mais confiável.

---

## Capabilities atuais que pertencem ao lab

- benchmark de modelos
- benchmark de parsing, retrieval, embeddings e reranking
- evals automatizados
- decision gate da fase 8.5
- runtime economics
- budget-aware routing
- OCR/VLM routing benchmark
- LangGraph shadow workflow
- provider/model comparison
- synthetic benchmarks e gold sets
- benchmark/eval executive review deck

### Regra prática

Tudo o que responde:

**como sabemos que este workflow está bom, quanto custa e como ele evolui com segurança?**

pertence ao lab.

---

## Capacidades adjacentes, incubadas e engines internas

Algumas partes do repositório são valiosas, mas não devem competir pela headline da narrativa principal neste momento.

### `cv_analysis`

`cv_analysis` deixa de ser tratado como surface primária de produto.

Leitura recomendada:

- `cv_analysis` = **engine interna**
- `Candidate Review` = **workflow exposto no produto**

Ou seja: o nome técnico pode continuar existindo internamente, mas a experiência de produto deve falar em **Candidate Review**.

### `code_analysis`

Hoje deve ser tratado como:

- capability secundária
- demonstração técnica complementar
- fluxo útil, porém fora do problema central de documentos enterprise

### Regra de posicionamento

Capacidades adjacentes podem continuar no repositório sem virar a vitrine principal do produto.

---

## Onde agent e MCP entram nessa organização

## Agent

Hoje o componente mais claro é um **document agent**, não um router universal do sistema inteiro.

Leitura correta:

- agente = orquestrador especializado de workflows documentais
- não = “agente que cobre todas as capabilities do projeto”

Isso é importante porque evita inflar o escopo do agente artificialmente.

## MCP

O MCP entra como:

- camada padronizada de acesso a repository, actions e worklog
- base de integração futura com sistemas externos
- infraestrutura habilitadora do workflow

Leitura correta:

- MCP = integração / tool layer
- não = headline principal de produto

### Resumo curto

- **agent pensa o fluxo**
- **MCP conecta tools e sistemas operacionais**

---

## Implicações para README, demo e entrevistas

## Como abrir a narrativa

O projeto deve ser apresentado primeiro como:

> **um produto de Document Intelligence para transformar documentos corporativos em análise grounded e artefatos acionáveis.**

Depois disso, a trilha de lab entra como prova de maturidade:

> **por trás do produto existe uma camada de evals, benchmark, observabilidade, routing e EvidenceOps para garantir confiabilidade.**

## O que evitar

Evitar abrir a explicação do projeto com:

- benchmark de modelos
- MCP server
- comparação de provider
- detalhes de runtime

Esses itens são importantes, mas devem aparecer como **sustentação**, não como **headline**.

---

## Implicações para a evolução em Gradio e para a fase 10.25

Se a interface evoluir para Gradio, a primeira leitura da UI deve ser da **trilha de produto**, não da trilha de lab.

### Split oficial de superfícies

A direção recomendada passa a ser:

- **Gradio** = superfície do produto
- **Streamlit** = AI Lab dashboard

### O que a UI em Gradio deve priorizar

- document review
- policy / contract comparison
- action plan / evidence review
- candidate review
- executive deck generation como capability transversal

### O que a UI principal não deve priorizar

- benchmark matrix
- comparação extensa de modelos
- dashboards de eval interno
- detalhes operacionais do runtime

### Regra recomendada

- **Gradio** = showcase AI-first dos workflows de negócio
- **lab** = área avançada, documentação técnica ou superfície separada

---

## Leitura recomendada dos decks da fase 10.25

Nem todo deck tem o mesmo papel estratégico.

### Decks com cara de produto

- document review deck
- policy / contract comparison deck
- action plan deck
- evidence pack / audit deck

### Deck com cara de lab / engenharia

- benchmark & eval executive review deck

Este último continua valioso, mas deve ser tratado como artefato da trilha **AI Engineering Lab**, e não como o principal hero flow da experiência de produto.

---

## Estrutura oficial resumida

### A. Business Workflows / produto

- document review
- policy / contract comparison
- action plan / evidence review
- candidate review
- executive deck generation como capability transversal

### B. AI Engineering Lab

- model comparison
- evals
- runtime economics
- routing experiments
- OCR/VLM experiments
- benchmark workflows
- synthetic datasets

### C. Capacidades adjacentes

- `code_analysis`

### D. Engines internas importantes

- `cv_analysis` como base do workflow `Candidate Review`

---

## Resultado esperado desta organização

Ao adotar esta leitura, o projeto deixa de parecer:

- um laboratório genérico que faz de tudo
- ou um repositório com duas narrativas concorrentes

E passa a parecer:

- **um produto com problema de negócio claro**
- sustentado por **uma fundação séria de AI engineering**

---

## Documentos relacionados

- `proximos_passos.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`
- `docs/PHASE_10_25_PRESENTATION_EXPORT_PRODUCTIZATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_UI_EVOLUTION.md`
- `docs/PHASE_9_5_EVIDENCEOPS_MCP_LOCAL_SERVER.md`
- `docs/PHASE_9_25_RUNTIME_ECONOMICS_AND_EVIDENCEOPS_LOCAL.md`