# Roadmap Definitivo — AI Workbench Local

## Ajuste tático em andamento — renderer host-native agora, Docker-ready depois

Objetivo desta trilha curta:

- consolidar o `ppt_creator_app` como renderer HTTP externo do AI Workbench
- padronizar o uso **host-native** como operação principal do P1 atual
- deixar o projeto irmão preparado para subir em Docker depois, sem tornar Docker bloqueante agora

### Checklist desta trilha

- [x] configurar `presentation export` no AI Workbench para apontar para `http://127.0.0.1:8787`
- [x] adicionar helper local para subir o renderer host-native a partir deste repositório
- [x] documentar o fluxo operacional recomendado no README do AI Workbench
- [x] preparar o `ppt_creator_app` para Docker service-first no repositório irmão
- [ ] validar smoke test manual completo: `AI Workbench -> /health -> /render -> /artifact`
- [ ] validar `docker compose up --build` no `ppt_creator_app` quando chegar a hora de endurecer a operação
- [ ] decidir quando ativar `PRESENTATION_EXPORT_REQUIRE_REAL_PREVIEWS=true` para o runtime containerizado

## Ajuste tático em andamento — paridade de overrides + sidebar multi-provider

Objetivo desta trilha curta:

- alinhar melhor o comportamento de `huggingface_server` com o que já existia para `ollama`
- deixar mais explícito por que certos providers aparecem ou não na seção de embeddings
- limpar a UX da sidebar para separar melhor geração, embeddings, retrieval/reranking e parsing documental

### Checklist desta trilha

- [x] documentar o plano antes da implementação
- [x] fazer `huggingface_server` reaproveitar melhor os overrides operacionais já usados no app (`temperature`, `context_window`, `embedding_context_window`, `truncate`)
- [x] deixar explícito na sidebar quando `huggingface_server` / `huggingface_inference` não aparecem para embeddings e por quê
- [x] expor controles de reranking já existentes (`rerank_pool_size`, `rerank_lexical_weight`)
- [x] expor controles operacionais de OCR e VLM na sidebar
- [x] melhorar nomenclatura da sidebar para reduzir confusão entre geração, embeddings e backends documentais
- [x] validar com testes focados e atualizar documentação final

## 1. Visão do projeto

### Objetivo principal

Transformar este projeto em um **ativo forte de portfólio**, com impacto real em:

- **GitHub**
- **LinkedIn**
- **currículo**
- **entrevistas técnicas**

O objetivo não é terminar com “mais um chatbot”. O objetivo é construir uma **plataforma de IA aplicada** que demonstre capacidade de produto, engenharia, avaliação, arquitetura e comunicação técnica.

### Tese do projeto

> Construí uma plataforma de IA aplicada para experimentar LLMs locais e integrações opcionais free-tier, conversar com documentos, produzir outputs estruturados, usar tools e agentes, comparar modelos, avaliar respostas e monitorar desempenho.

### Tese profissional mais forte

> O projeto deve mostrar claramente uma progressão de maturidade:
> 
> 1. **fundamentos do pipeline manual**
> 2. **retrieval engineering mais forte**
> 3. **outputs estruturados e confiáveis**
> 4. **evolução explícita para LangChain e LangGraph**
> 5. **agentes orientados a valor de negócio**
> 6. **benchmark, evals e observabilidade**

### Norte estratégico do projeto

O projeto deve deixar claro que eu não sei apenas “chamar um modelo”.
Ele deve provar que eu sei:

- construir UI de produto
- organizar software por camadas
- trabalhar com múltiplos providers/modelos
- montar e evoluir um pipeline de RAG
- validar saídas estruturadas
- medir qualidade
- instrumentar o sistema
- evoluir de implementação manual para stack de mercado
- transformar tudo isso em uma narrativa defendível para recrutador

### Nome sugerido

Escolher um nome com cara de produto ajuda muito na percepção profissional. Sugestões:

- **AI Workbench Local**
- **LLM Workbench**
- **AI Studio Local**
- **Applied AI Workbench**

---

## 2. Proposta de valor

Este projeto deve provar que eu sei construir **aplicações reais com IA**, indo além de apenas chamar uma API.

### O que ele deve demonstrar

- integração com **LLMs locais**
- troca entre **múltiplos modelos**
- **RAG** com documentos
- geração de **outputs estruturados**
- uso de **tools/agentes**
- comparação de desempenho e qualidade entre modelos
- **observabilidade** e rastreabilidade
- organização de software para portfólio profissional

### Casos de uso principais

Para o projeto ter foco e ser defendível em entrevista, ele deve priorizar estes 3 fluxos:

1. **Chat com documentos (RAG)**
   - upload de PDF, TXT, CSV, MD e PY
   - respostas baseadas em contexto recuperado
   - exibição de fontes/trechos usados

2. **Assistente de código**
   - explicação de código
   - refatoração
   - sugestões de melhoria
   - checklist técnico

3. **Extração estruturada de informação**
   - conversão de texto em JSON
   - geração de checklist
   - extração de campos validados

### Caso de uso empresarial-alvo

O caso de uso mais forte para recrutador não é um “chat agent genérico”.
O alvo de maior impacto deve ser algo como:

- **Document Operations Copilot**
- **Enterprise Knowledge & Document Analyst Agent**

Ou seja: um sistema que trabalha em cima de documentos da empresa e consegue:

- responder perguntas com fonte
- resumir documentos
- comparar documentos
- extrair informações estruturadas
- apontar riscos e lacunas
- gerar checklist de ação
- produzir resposta pronta para revisão humana

### Leitura oficial em duas trilhas

Para evitar que o projeto pareça ao mesmo tempo um produto difuso e um laboratório sem foco, a leitura oficial passa a ser:

1. **Business Workflows / produto**
   - document review
   - policy / contract comparison
   - action plan / evidence review
   - candidate review
   - executive deck generation como capability transversal

2. **AI Engineering Lab**
   - benchmark de modelos
   - evals
   - routing e observabilidade
   - runtime economics
   - experimentação controlada de arquitetura

Regra prática:

- a trilha de **produto** resolve a dor de negócio
- a trilha de **lab** garante confiabilidade, auditabilidade e evolução segura

Documento de referência:

- `docs/PROJECT_POSITIONING_TWO_TRACKS.md`

---

## 3. Stack recomendada

### Base gratuita principal

- **Python**
- **Streamlit**
- **Ollama**
- **LangChain**
- **LangGraph**
- **Chroma** ou **FAISS**
- **SQLite**
- **Pydantic**
- **pypdf**
- **pandas**


### Camada de evolução de interface

Para a camada de interface, a leitura mais forte do projeto deve ser progressiva:

- **Streamlit** como UI principal de prototipagem e iteração rápida
- **Gradio** como camada intermediária de demo AI-first para fluxos mais fortes do produto
- **Frontend web real + backend/API** como direção de produto antes do deploy público na Oracle

### Regra prática para UI

A interface não deve ficar acoplada à lógica principal do produto.
A narrativa arquitetural mais forte é:

- começar com **Streamlit** para aprender, validar e iterar rápido
- migrar alguns fluxos para **Gradio** quando fizer sentido melhorar a demo AI-first
- evoluir depois para um **app/website real** antes do deploy público

### Camada opcional free-tier

Usar apenas como extensão opcional, sem depender disso para o projeto funcionar:

- **Gemini** ou **Groq**, se houver camada gratuita disponível
- **Hugging Face Inference**, se fizer sentido em testes, reranking ou benchmarking
- **Langfuse** self-hosted ou free-tier, se compensar

### Camada experimental recomendada

Além da stack principal, o projeto deve abrir espaço para uma trilha de experimentação técnica com **Hugging Face** quando isso gerar valor claro.

Essa camada não substitui o runtime local principal do produto. Ela existe para ampliar o nível de engenharia do projeto em temas como:

- comparação entre modelos open-source fora do catálogo principal do Ollama
- experimentação com **Transformers**
- comparação entre quantizações
- testes com modelos de embedding e reranking
- fine-tuning leve com **PEFT/LoRA**
- avaliação de alternativas de serving ou exportação futura

### Regra prática de posicionamento

A leitura arquitetural mais forte para o projeto é:

- **Ollama** como runtime principal do app local
- **Hugging Face** como trilha de experimentação, adaptação e comparação técnica

### Regra de arquitetura

O sistema deve continuar funcionando **mesmo se todas as integrações cloud forem removidas**.

### Regra de evolução técnica

A evolução do projeto deve provar **duas coisas ao mesmo tempo**:

1. eu entendo o pipeline manual por baixo
2. eu sei migrar esse pipeline para ferramentas de mercado quando isso faz sentido

Ou seja:

- não virar refém de framework
- não reinventar tudo sem necessidade

### Regra adicional de desacoplamento por provider

As próximas fases devem preservar uma separação explícita entre:

- camada de geração
- camada de embeddings
- camada de reranking
- camada de experimentação offline / benchmarking

Isso é importante para que o projeto consiga evoluir mantendo:

- **Ollama** como runtime principal simples e demonstrável
- **OpenAI-compatible** como compatibilidade operacional quando fizer sentido
- **Hugging Face** como trilha de experimentação para modelos, quantizações e adaptação futura

### Configurações importantes do projeto

O projeto deve ter configuração explícita e versionada para pontos críticos, especialmente:

- provider padrão
- modelo padrão
- temperatura
- embedding model
- parâmetros de RAG
- **janela de contexto por provider**

### Variáveis que devem existir e ser tratadas como parte do produto

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_AVAILABLE_MODELS`
- `OLLAMA_TEMPERATURE`
- `OLLAMA_CONTEXT_WINDOW`
- `OLLAMA_EMBEDDING_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_CONTEXT_WINDOW`
- `OPENAI_AVAILABLE_MODELS`
- `HUGGINGFACE_MODEL` (opcional em fase posterior)
- `HUGGINGFACE_AVAILABLE_MODELS` (opcional em fase posterior)
- `HUGGINGFACE_CONTEXT_WINDOW` (opcional em fase posterior)
- `RAG_CHUNK_SIZE`
- `RAG_CHUNK_OVERLAP`
- `RAG_TOP_K`

### Posição atual recomendada para embeddings

Para o projeto em português e multilíngue, a direção mais forte discutida foi usar:

- **`embeddinggemma:300m`** como embedding model principal após a rodada de benchmark da Fase 4.5

Mantendo `bge-m3` como baseline forte e deixando espaço para comparações futuras com:

- `nomic-embed-text`
- `mxbai-embed-large`
- outros embeddings locais/open-source

---

## 4. Princípios do projeto

### Princípio 1 — Free-first
A fundação do projeto deve ser totalmente funcional sem custo.

### Princípio 2 — Free-tier-aware
Integrações pagas com camada grátis entram apenas como comparação, nunca como dependência estrutural.

### Princípio 3 — Portfólio orientado a evidência
Cada fase deve gerar artefatos visíveis: screenshot, GIF, doc, benchmark, README, release ou demo.

### Princípio 4 — Produto + engenharia
O projeto precisa equilibrar:

- experiência do usuário
- arquitetura de software
- medição de qualidade
- comunicação técnica

### Princípio 5 — Evolução técnica explícita
O roadmap deve mostrar progressão clara:

- manual primeiro
- retrieval mais sofisticado depois
- framework de mercado depois
- agente empresarial depois

### Princípio 5.5 — Runtime e experimentação não são a mesma coisa
O projeto fica mais forte quando separa claramente:

- **runtime principal do produto**
- **camada experimental de modelos**
- **camada de benchmark/evals**
- **camada de adaptação de modelos**

Isso evita trocar a stack principal cedo demais e permite incorporar Hugging Face sem perder a narrativa local-first do projeto.

### Princípio 6 — Agente com valor real de negócio
Evitar agente “show-off” sem foco. Priorizar:

- utilidade real
- previsibilidade
- observabilidade
- estrutura

### Princípio 7 — Honestidade técnica
O roadmap deve registrar não só funcionalidades desejadas, mas também:

- pontos já entregues
- pontos ainda incompletos
- riscos conhecidos
- áreas que precisam de validação real

---

## 5. Critérios de impacto profissional

Ao final, o projeto deve deixar claro que eu consigo trabalhar com:

- **produto**: caso de uso claro, interface útil e experiência coerente
- **engenharia**: organização por módulos, testes, configuração, tratamento de falhas
- **IA aplicada**: RAG, structured outputs, agentes, avaliação e benchmark
- **apresentação profissional**: README, docs, demo, narrativa para entrevista

### O que um recrutador deve enxergar

Ao olhar este projeto, a leitura ideal deve ser:

> essa pessoa sabe começar simples, evoluir arquitetura, melhorar retrieval, estruturar saídas, instrumentar o sistema e transformar isso em um caso de uso empresarial.

---

## 6. Estado atual do projeto

### Fases já concluídas

- **Fase 0 — Publicação segura e posicionamento**
- **Fase 0.5 — Preparação de publicação e governança mínima do repositório**
- **Fase 1 — Base do produto com melhor experiência**
- **Fase 2 — Arquitetura modular**
- **Fase 3 — Multi-modelo e perfis de prompt**
- **Fase 4 — Chat com documentos (RAG)**
- **Fase 4.5 — Robustez, tuning e observabilidade do RAG**
- **Fase 5 — Outputs estruturados + trilha `evidence_cv`**

### Fase atual em andamento

- **Fase 8 — Evals**
  - próxima fase estratégica após o fechamento técnico/local da Fase 7
  - foco em transformar os benchmarks e workflows já entregues em critérios repetíveis de qualidade

### Fase concluída mais recentemente

- **Fase 7 — concluída tecnicamente/localmente com comparação lado a lado entre modelos/providers, ranking por execução, leaderboards agregados por runtime/retrieval/embedding/prompt profile e visão unificada de strategy benchmarks**

### O que já foi entregue na Fase 4.5

- [x] base para múltiplos documentos no índice RAG
- [x] preparação do índice para coleção documental, não só arquivo isolado
- [x] upload múltiplo de arquivos
- [x] lógica de **upsert** documental
- [x] lógica de remoção seletiva de documento no índice
- [x] filtros por documento/tipo na recuperação
- [x] metadados mais ricos por documento e por chunk
- [x] configuração explícita de janela de contexto no projeto
- [x] `OLLAMA_CONTEXT_WINDOW` no `.env.example` / `.env`
- [x] `OPENAI_CONTEXT_WINDOW` no `.env.example` / `.env`
- [x] leitura centralizada dessas variáveis em `src/config.py`
- [x] controle visível de contexto na sidebar quando provider = Ollama
- [x] registro do contexto como metadado da conversa
- [x] escolha explícita do embedding model com benchmark comparativo e recomendação final (`embeddinggemma:300m`)
- [x] compactação e normalização do `.rag_store.json`
- [x] evitar reload desnecessário do índice a cada rerun
- [x] remoção dos warnings de `use_container_width`
- [x] melhoria parcial da performance do RAG local
- [x] controles visíveis de `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP` e `RAG_TOP_K` para testes no app
- [x] métricas visíveis de documentos, chunks e tipos indexados
- [x] telemetria básica de retrieval exibida no chat (`retrieval_latency`, chunks recuperados e top-k)
- [x] debug leve de retrieval no app
- [x] UX refinada para indexação/reindexação seletiva dos uploads atuais
- [x] remoção em lote com base em seleção explícita ou filtro atual
- [x] painel de validação técnica do contexto do Ollama (`/api/chat`, `/api/show` e `ollama ps`)

### O que já está funcional hoje

- upload múltiplo
- estrutura interna de índice para vários documentos
- filtros por documento/tipo
- remoção seletiva de documento
- controle visual de contexto no Ollama
- contexto como metadado
- compactação e migração do índice local

### O que foi fechado experimentalmente na Fase 4.5

- [x] comparação prática entre embeddings
- [x] comparação prática entre janelas de contexto de embedding
- [x] benchmark final de tuning (`RAG_CHUNK_SIZE`, `RAG_TOP_K`, `RAG_CHUNK_OVERLAP`, `RAG_RERANK_POOL_SIZE`)
- [x] benchmark de extração de PDF com revisão humana (`basic`, `hybrid`, `complete`)
- [x] documentação visual reprodutível da Fase 4.5 com gráficos versionados
- [x] script dedicado para regenerar os gráficos da Fase 4.5 a partir de dados versionados
- [x] configuração final recomendada do pipeline baseada em trade-off entre qualidade, custo e robustez

### O que já considero fechado nesta rodada final da Fase 4.5

- [x] catálogo multi-arquivo mais refinado na UI
- [x] UX melhor para remoção/reindexação seletiva
- [x] vector store mais robusta com Chroma local e fallback seguro
- [x] clear físico do backend persistido ao limpar o índice
- [x] reranking híbrido leve acima do ranking vetorial bruto
- [x] limitação inteligente do contexto recuperado por orçamento real de prompt
- [x] validação técnica do `num_ctx` pelo caminho nativo
- [x] caminho **Ollama native** para parâmetros avançados
- [x] debug/inspeção leve mostrando o `num_ctx` pedido, contexto declarado do modelo e sinal auxiliar de runtime

### O que já foi entregue na Fase 5

- [x] foundation de outputs estruturados em `src/structured/`
- [x] payload schemas por tarefa e envelope de execução separado
- [x] registry de tasks com metadata de renderização (`json`, `friendly`, `checklist`)
- [x] parser/sanitizer/validator com validação Pydantic e falha controlada
- [x] documentação técnica inicial da foundation de structured outputs
- [x] painel de structured outputs no app (`main_qwen.py`)
- [x] renderer base para JSON / friendly view / checklist
- [x] execução inicial de `extraction`, `summary`, `checklist` e `cv_analysis`
- [x] uso opcional do contexto documental atual na UI da Fase 5
- [x] smoke eval automatizado local com `scripts/run_phase5_structured_eval.py`

### Resultado mais recente da smoke eval da Fase 5

- [x] `summary` — **PASS**
- [x] `checklist` — **PASS**
- [x] `cv_analysis` — **PASS**
- [x] `extraction` — **PASS**
- [x] `code_analysis` — **PASS**

### Observação de encerramento da Fase 5

A Fase 5 pode ser tratada como concluída do ponto de vista técnico/local.

Critérios já cumpridos:

- smoke eval com `PASS` em `extraction`, `summary`, `checklist`, `cv_analysis` e `code_analysis`
- trilha `evidence_cv` integrada ao fluxo real de upload/indexação
- rollout controlado local sob feature flag com auto-rollout, semantic gate e telemetria operacional versionada
- decisão documental adotada: a Fase 5 fica encerrada como **pacote unificado de produto**, com `structured outputs` e `evidence_cv` como subtrilhas da mesma fase

O que fica para fases posteriores, sem bloquear o encerramento da Fase 5:

- screenshots finais, mini demo e narrativa de portfólio/README/LinkedIn → **Fase 11**, depois da evolução para app web e do deploy público
- deploy público do app/web sem levar os modelos locais para a Oracle Always Free → **Fases 10.25 e 10.5**
- observabilidade contínua em ambiente público → **Fases 9 e 10.5**

### Próximo passo estratégico recomendado

A ordem mais forte agora passa a ser:

1. **Fase 6 — Tools e agentes orientados a valor de negócio**
2. **Fase 7 — Benchmark e comparação entre modelos**
3. **Fase 8 — Evals**
4. **Fase 8.5 — Adaptação de modelos com Hugging Face, quantização e fine-tuning leve**
5. **Fase 9 — Observabilidade**
6. **Fase 9.25 — AI runtime economics, usage observability e budget-aware routing**
7. **Fase 9.5 — MCPs e integrações operacionais empresariais**
8. **Fase 10 — Engenharia profissional**
9. **Fase 10.25 — Split oficial entre AI Lab e produto: Streamlit -> Gradio -> App Web**
10. **Fase 10.5 — Deploy híbrido demonstrável (Oracle + Cloudflare Tunnel + Ollama local)**
11. **Fase 11 — Pacote final de portfólio**

---

## 7. Sequência estratégica recomendada

> Regra prática: concluir uma fase por vez, registrar evidências e só depois avançar.

A melhor história para entrevista não é “fui adicionando features aleatórias”.
A melhor história é:

1. montei a base segura
2. melhorei a UX
3. modularizei arquitetura
4. suportei múltiplos modelos/providers
5. construí o RAG manualmente
6. evoluí para uma base documental mais forte
7. transformei saídas em formatos integráveis
8. mostrei maturidade com LangChain/LangGraph
9. criei um agente empresarial de verdade
10. medi tudo com benchmark, evals e observabilidade
11. endureci a engenharia e a confiabilidade do app
12. evoluí a interface de protótipo para demo AI-first e depois para uma camada web mais sólida
13. publiquei uma demo híbrida tecnicamente defendível
14. só então empacotei tudo para portfólio final

---

## 8. Checklist executável por fases

---

## Fase 0 — Publicação segura e posicionamento

### Objetivo
Preparar o projeto para ser público e profissional.

### Checklist
- [x] Remover segredos hardcoded do código
- [x] Configurar variáveis de ambiente com `.env`
- [x] Criar `.env.example`
- [x] Revisar `.gitignore`
- [x] Rotacionar/revogar qualquer chave já exposta anteriormente
- [x] Definir nome oficial do projeto
- [x] Escrever a descrição curta do projeto em 1 frase
- [x] Definir os 3 casos de uso principais

### Entregável
- Repositório seguro e pronto para publicação

### Evidência para GitHub/LinkedIn
- commit de saneamento do projeto
- primeiro README curto com visão geral

### O que preciso saber defender em entrevista
- por que segurança básica e gestão de segredos importam
- por que o projeto tem foco em 3 casos de uso e não em features soltas

---

## Fase 0.5 — Publicação controlada e governança mínima

### Objetivo
Organizar o repositório para crescer de forma profissional antes da abertura pública.

### Checklist
- [x] Inicializar Git local corretamente
- [x] Definir branch principal como `main`
- [x] Preparar branch de integração (`dev`) como convenção futura
- [x] Definir política de manter o repositório privado até maturidade suficiente
- [x] Adicionar `LICENSE`
- [x] Criar guia mínimo de publicação
- [x] Garantir que `materials_local/` e materiais de curso fiquem fora do versionamento
- [x] Alinhar README com política de publicação privada temporária

### Entregável
- Repositório com governança mínima, política de publicação e estrutura segura para crescer

### Evidência para GitHub/LinkedIn
- `LICENSE`
- `docs/PUBLICATION_GUIDE.md`
- README alinhado à política de publicação

### O que preciso saber defender em entrevista
- por que repositório privado pode ser melhor em fases iniciais
- como separar material autoral de material de curso
- como preparar um projeto pessoal para futura exposição profissional

---

## Fase 1 — Base do produto com melhor experiência

### Objetivo
Transformar o app atual em um produto mais utilizável.

### Checklist
- [x] Implementar streaming da resposta
- [x] Adicionar botão de limpar conversa
- [x] Criar sidebar com configurações
- [x] Adicionar seletor de modelo
- [x] Adicionar parâmetros básicos, como temperatura
- [x] Persistir histórico simples
- [x] Medir tempo de resposta
- [x] Exibir erros de forma amigável

### Entregável
- Chat local com melhor UX e cara de produto

### Evidência para GitHub/LinkedIn
- screenshot da interface
- GIF curto do chat respondendo em streaming

### O que preciso saber defender em entrevista
- decisões de UX no chat
- por que streaming melhora percepção de velocidade
- como o estado da conversa é mantido

---

## Fase 2 — Arquitetura modular

### Objetivo
Sair de um arquivo único e construir uma base escalável.

### Checklist
- [x] Criar estrutura de pastas por responsabilidade
- [x] Separar camada de UI
- [x] Separar camada de providers/modelos
- [x] Separar camada de serviços
- [x] Separar camada de persistência
- [x] Centralizar configurações do projeto
- [x] Criar utilitários reutilizáveis

### Estrutura sugerida

```text
src/
  app/
  providers/
  services/
  rag/
  agents/
  storage/
  ui/
  utils/
```

### Entregável
- Projeto organizado e preparado para crescer

### Evidência para GitHub/LinkedIn
- diagrama simples da arquitetura
- commit/release marcando a reorganização do projeto

### O que preciso saber defender em entrevista
- separação de responsabilidades
- como a arquitetura ajuda manutenção e escalabilidade

---

## Fase 3 — Multi-modelo e perfis de prompt

### Objetivo
Transformar o projeto em um laboratório de experimentação.

### Checklist
- [x] Implementar alternância entre modelos locais
- [x] Adicionar perfis de prompt: professor, programador, resumidor e extrator
- [x] Registrar qual modelo foi usado em cada resposta
- [x] Registrar qual perfil de prompt foi usado
- [x] Comparar comportamento entre modelos
- [x] Adicionar 1 provider cloud/free-tier opcional para benchmarking

### Modelos sugeridos
- [x] `qwen2.5-coder:7b`
- [x] `qwen2.5-coder:14b`
- [x] `deepseek-coder:6.7b`
- [x] Deixar a comparação prática local vs cloud explicitamente reposicionada para a **Fase 7**, depois da base multi-provider ficar pronta

### Entregável
- Plataforma multi-modelo com perfis reutilizáveis

### Evidência para GitHub/LinkedIn
- tabela simples comparando modelos
- vídeo curto mostrando troca de modelo e perfis

### O que preciso saber defender em entrevista
- trade-offs entre modelos menores e maiores
- diferença entre local e cloud
- por que abstrair provider/modelo é importante
- por que o cliente `openai` pode ser usado como cliente HTTP compatível para Ollama

---

## Fase 4 — Chat com documentos (RAG)

### Objetivo
Adicionar a feature de maior valor para uso real em empresas.

### Checklist
- [x] Adicionar upload de PDF
- [x] Adicionar upload de TXT
- [x] Adicionar upload de CSV
- [x] Adicionar upload de MD
- [x] Adicionar upload de PY
- [x] Extrair texto dos arquivos
- [x] Implementar chunking
- [x] Gerar embeddings locais
- [x] Criar vector store local inicial
- [x] Implementar recuperação semântica
- [x] Exibir fontes/trechos usados na resposta
- [x] Criar modo “Chat com documentos”

### Ferramentas sugeridas
- [x] Embeddings locais via Ollama ou modelo open-source
- [x] Reimplementação explícita com LangChain reposicionada para a **Fase 5.5**, e não mais tratada como pendência da Fase 4
- [x] Chroma local como store vetorial mais robusta foi consolidado na **Fase 4.5**

### Entregável
- Módulo de RAG funcional e demonstrável

### Evidência para GitHub/LinkedIn
- GIF de upload de documento + resposta com fontes
- documento de arquitetura do fluxo de RAG

### O que preciso saber defender em entrevista
- como funciona chunking
- por que usar vector store
- como garantir que a resposta está baseada no documento
- por que começar manualmente ajuda entendimento do pipeline

---

## Fase 4.5 — Robustez, tuning e observabilidade do RAG

Objetivo desta fase: sair de um RAG apenas funcional para um pipeline mais robusto, explicável e comparável, com melhor gestão do índice, backend vetorial persistido, observabilidade de retrieval, suporte a tuning e validação técnica da integração com Ollama.

### Já concluído

- [x] Revisar o estado atual da Fase 4.5 e consolidar a direção arquitetural
- [x] Formalizar o índice local/JSON como fonte canônica do estado RAG
- [x] Integrar Chroma local como backend vetorial persistido com fallback seguro
- [x] Tratar o Chroma como espelho sincronizado do índice canônico
- [x] Corrigir IDs únicos por chunk no backend vetorial
- [x] Melhorar a UX de indexação, reindexação e remoção seletiva de documentos
- [x] Expor debug leve de retrieval no app
- [x] Mostrar claramente qual backend vetorial foi usado no retrieval
- [x] Expor status de sincronização entre JSON canônico e Chroma persistido
- [x] Implementar reranking híbrido leve (vetorial + lexical)
- [x] Introduzir candidate pool maior que o top-k final para reranking
- [x] Limitar o contexto documental enviado ao prompt com budget operacional
- [x] Expor métricas de contexto usado, truncamento e chunks descartados
- [x] Implementar caminho funcional com provider Ollama e validação técnica operacional do uso de contexto
- [x] Documentar a distinção entre caminho OpenAI-compatible e caminho nativo do Ollama
- [x] Separar clear lógico do índice de reset físico do persist dir do Chroma
- [x] Tornar o fluxo normal de limpeza seguro, evitando problemas de `readonly database`
- [x] Criar reset físico explícito do Chroma como ação administrativa separada do clear normal
- [x] Criar scripts e documentação de apoio para validação da Fase 4.5
- [x] Expor escolha do modelo de embedding na UI com validação de compatibilidade do índice
  - [x] Mostrar embedding ativo na configuração atual
  - [x] Mostrar embedding com que o índice existente foi construído
  - [x] Detectar incompatibilidade entre embeddings
  - [x] Bloquear uso enganoso do índice quando houver mismatch
  - [x] Exigir reindexação segura ao trocar de embedding model
- [x] Expor janela de contexto do embedding na UI
  - [x] Permitir configurar `num_ctx` do embedding separadamente do `num_ctx` do LLM
  - [x] Usar o endpoint nativo de embedding do Ollama para enviar `options.num_ctx`
  - [x] Tratar `embedding_context_window` como parte da compatibilidade do índice
  - [x] Exigir reindexação segura ao trocar a janela de contexto do embedding
- [x] Expor inspeção técnica operacional do embedding na UI
  - [x] Mostrar modelo de embedding ativo
  - [x] Mostrar janela de contexto do embedding ativa
  - [x] Mostrar metadados de compatibilidade entre configuração atual e índice existente
- [x] Impedir mistura silenciosa de espaços vetoriais incompatíveis
  - [x] Bloquear uso de índice criado com embedding model diferente
  - [x] Bloquear uso de índice criado com `embedding_context_window` diferente

### Feito estruturalmente, mas depende de validação prática contínua no ambiente local

- [x] Validar tecnicamente o caminho nativo do Ollama para parâmetros avançados (`num_ctx` e afins)
- [x] Expor sinais operacionais de contexto usado, backend empregado e estado do retrieval
- [x] Preparar infraestrutura para comparação prática entre embeddings
- [x] Preparar infraestrutura para benchmark fino de retrieval e tuning
- [x] Preparar infraestrutura para comparação prática de janelas de contexto de embedding
- [x] Tornar observável a compatibilidade entre configuração de embedding e índice persistido

### Fechamento experimental da Fase 4.5

- [x] Comparar embeddings na prática no dataset real
  - [x] Definir conjunto fixo de perguntas de teste
  - [x] Rodar as mesmas perguntas com embeddings diferentes
  - [x] Comparar qualidade das fontes recuperadas
  - [x] Comparar latência de retrieval
  - [x] Registrar evidências locais do resultado

- [x] Comparar janelas de contexto de embedding na prática
  - [x] Definir múltiplas configurações de `embedding_context_window`
  - [x] Reindexar com cada configuração
  - [x] Comparar impacto nas fontes recuperadas
  - [x] Comparar impacto na latência e estabilidade operacional
  - [x] Registrar evidências locais do comportamento

- [x] Executar benchmark prático de tuning de retrieval
  - [x] Comparar combinações de `chunk_size`
  - [x] Comparar combinações de `chunk_overlap`
  - [x] Comparar `top_k`
  - [x] Comparar `candidate_pool_size`
  - [x] Observar impacto do reranking híbrido
  - [x] Registrar configuração final recomendada

- [x] Executar benchmark de extração de PDF com revisão humana
  - [x] Consolidar revisão manual dos 12 packets
  - [x] Comparar custo e qualidade entre `basic`, `hybrid` e `complete`
  - [x] Registrar modo padrão recomendado para o projeto

### Achados finais da Fase 4.5

- **Extração de PDF padrão:** `hybrid`
  - `avg_manual_score = 1.0625`
  - `avg_extraction_seconds = 22.0248`
  - decisão tomada por trade-off, já que `complete` teve `1.1094`, porém com `1485.38 s` de extração média
- **Embedding padrão:** `embeddinggemma:300m`
  - `Hit@1 = 1.0`
  - `MRR = 1.0`
  - `avg_retrieval_seconds = 0.7259`
- **Janela de contexto do embedding:** `512`
  - melhor run: `embeddinggemma:300m + 512`
  - `avg_retrieval_seconds = 0.6932`
- **Retrieval recomendado:** `chunk_size=1200`, `chunk_overlap=80`, `top_k=4`, `rerank_pool_size=8`
  - melhor run: `lower_overlap`
  - `avg_retrieval_seconds = 0.8449`
  - melhor do que o baseline (`0.9102`) sem perder qualidade
- **Justificativa:** melhor equilíbrio entre qualidade de recuperação, robustez documental e custo operacional
- **Documentação de apoio:** `docs/PHASE_4_5_BENCHMARK_RESULTS.md`, `docs/PHASE_4_5_VALIDATION.md`, `docs/BENCHMARK_PDF_EXTRACTION_en.md`
- **Assets visuais versionados:** `docs/assets/phase_4_5/`
- **Renderização reprodutível dos gráficos:** `scripts/render_phase_4_5_charts.py` + `docs/data/phase_4_5_benchmark_data.json`

### Critério de encerramento da Fase 4.5

A Fase 4.5 está considerada encerrada porque:
- o backend Chroma permaneceu estável no fluxo normal de uso
- a remoção/reindexação segue coerente com o índice canônico
- a UI deixa claro o backend usado, o embedding ativo, a janela de contexto do embedding e o status do retrieval
- a comparação prática entre embeddings foi realizada com evidência local
- a comparação prática entre janelas de contexto de embedding foi realizada com evidência local
- o benchmark final de tuning foi executado e documentado
- o benchmark de extração foi executado com revisão humana consolidada

---

## Fase 5 — Outputs estruturados

### Objetivo
Mostrar que IA também pode ser usada como componente integrável de sistema, com saídas previsíveis, validadas e reutilizáveis além do chat livre.

### Status atual da fase

A Fase 5 já está funcional e validada em múltiplas camadas.

Hoje o projeto já tem:

- foundation técnica de structured outputs em `src/structured/`
- UI separada de chat com RAG e documento estruturado, mantendo base documental compartilhada
- renderização em múltiplos formatos
- smoke eval automatizado
- benchmark sintético multilayout para `cv_analysis`
- `summary`, `checklist`, `extraction`, `cv_analysis` e `code_analysis` validados no smoke eval local
- `cv_analysis` validado em layouts textuais sintéticos
- fallback OCR opcional para documentos com texto insuficiente
- benchmark completo pós-OCR mostrando layouts textuais robustos e melhoria parcial em casos scan-like
- [x] integração do pipeline paralelo `evidence_cv` ao fluxo real de upload/indexação via `src/rag/loaders.py`
- [x] feature flags para ativar o pipeline evidence apenas para CV-like PDFs e scan-like fortes
- [x] serialização estruturada de CV em `runtime_metadata.indexing_payload` para indexação mais auditável
- [x] fundação de full CV structured extraction no `evidence_cv` com blocos e seções (`header`, `summary`, `experience`, `education`, `skills`, `languages`, `projects`)
- [x] OCR-first / VL-on-demand com roteador seletivo por documento e por região
- [x] backends OCR dedicados (`docling` e `ocrmypdf`) e suporte VL via Ollama para casos difíceis
- [x] metadata operacional do roteador VL (`decision`, `reasons`, `document_signals`, `regions_selected`, `fallback_used`)
- [x] política explícita de consumo no produto (`confirmed`, `visual_candidate`, `needs_review`, `not_found`)
- [x] merge híbrido conservador para contatos no shadow rollout (`emails` e `phones`)
- [x] adjudicação dos casos divergentes de contatos com separação entre erro de gold set e erro real do pipeline
- [x] relatório de shadow rollout com contagem de `agreements`, `email_complements`, `phone_complements` e conflitos
- [x] documentação de readiness para rollout controlado do parser OCR-first / VL-on-demand
- [x] `cv_analysis` endurecido no pós-processamento com deduplicação/canonicalização de education, experience e skills
- [x] grounding do structured analysis ajustado para CV único usar contexto completo do CV, em vez de chunk curto de retrieval
- [x] guardrails de grounding para evitar placeholders sob contexto fraco e reduzir saídas inventadas
- [x] limpeza upstream de `CV EDUCATION`, `CV SKILLS` e supressão de `CV PROJECTS` espúrio no contexto enviado ao modelo
- [x] preservação final de `education_entries` com deduplicação canônica, `date_range`, `location` e wording mais forte para USP

A Fase 5 está encerrada do ponto de vista técnico/local.

Critérios já cumpridos:

- smoke eval com `PASS` em `extraction`, `summary`, `checklist`, `cv_analysis` e `code_analysis`
- trilha `evidence_cv` integrada ao fluxo real de upload/indexação
- rollout controlado local sob feature flag com auto-rollout, semantic gate e telemetria operacional versionada
- encerramento documental definido como **pacote unificado de produto**, com `structured outputs` e `evidence_cv` como subtrilhas da mesma fase

O que sobe para fases posteriores, sem bloquear o encerramento da Fase 5:

- screenshots finais, mini demo e narrativa de portfólio/README/LinkedIn → **Fase 11**, depois da evolução para app web e do deploy público
- deploy público do app/web sem levar os modelos locais para a Oracle Always Free → **Fases 10.25 e 10.5**
- observabilidade contínua em ambiente público → **Fases 9 e 10.5**

### Checklist

#### Foundation e infraestrutura
- [x] Criar foundation de structured outputs em módulo dedicado
- [x] Validar saídas com Pydantic
- [x] Gerar respostas em JSON
- [x] Definir schemas previsíveis por tarefa
- [x] Garantir que os schemas e validadores sejam independentes do provider
- [x] Preparar a camada de saída estruturada para reutilização futura com Ollama e Hugging Face

#### UI e renderização
- [x] Gerar respostas em checklist
- [x] Integrar painel de structured outputs na UI
- [x] Separar explicitamente os fluxos de chat com RAG e análise estruturada
- [x] Adicionar renderer base para `json`, `friendly` e `checklist`
- [x] Fazer polish inicial da UI/UX da aba de análise estruturada
- [x] Tornar o checklist interativo com persistência local em sessão e botão de reset
- [x] Restaurar a distinção entre `friendly view` e modo `checklist` interativo

#### Tasks já implementadas
- [x] Criar modo resumidor em tópicos
- [x] Criar modo analisador de currículo
- [x] Criar modo gerador de checklist
- [x] Criar modo extrator de informações
- [x] Criar modo explicador/refatorador de código

#### Robustez já implementada na fase
- [x] Revalidar `extraction` com PASS no smoke eval automatizado
- [x] Validar `code_analysis` com PASS no smoke eval automatizado
- [x] Implementar auto-recovery estruturado com `repair_json`, `retry_generation` e telemetria de parse recovery
- [x] Fazer hardening e polish de `code_analysis` com UI em PT-BR, ordenação por severidade, categorias estáveis (`input_mutation`, `shared_reference`, `type_validation`) e recomendações coerentes
- [x] Promover `languages`, `education` e `experience entries` a campos explícitos do schema de CV
- [x] Adicionar normalização pós-modelo para consolidar dados vindos de `sections`
- [x] Criar benchmark sintético multilayout para `cv_analysis`
- [x] Implementar fallback OCR opcional para PDFs com texto insuficiente quando `ocrmypdf` estiver disponível localmente
- [x] Confirmar benchmark completo pós-OCR com layouts textuais robustos e melhoria parcial em casos scan-like

#### Trilha evidence_cv / parsing auditável de CV
- [x] Criar pacote `src/evidence_cv/` com `schemas`, `config`, `reconcile`, `pipeline/runner`, `cli`, OCR backends e VL support
- [x] Integrar o pipeline evidence ao app atual sem substituir globalmente o pipeline legado
- [x] Garantir fallback seguro para o fluxo legado quando a feature flag estiver desligada ou quando o pipeline novo falhar
- [x] Adicionar `evidence_summary`, `product_consumption` e warnings estruturados ao metadata consumido pelo app
- [x] Implementar roteador OCR-first / VL-on-demand com ativação seletiva em `digital_pdf`, `mixed_pdf` e `scanned_pdf`
- [x] Executar benchmark multilayout do roteador e registrar casos com ganho real, ganho parcial e ausência de ruído catastrófico
- [x] Criar mini gold set e relatório de adjudicação para contatos (`emails`, `phones`, `name`, `location`)
- [x] Endurecer a avaliação de contatos com normalização canônica, TP/FP/FN e debug por arquivo
- [x] Validar shadow rollout da política híbrida de contatos sem conflitos quantitativos nesta rodada
- [x] Documentar readiness para rollout controlado com OCR-first, VL-on-demand e consumo automático restrito a `confirmed`

#### Hardening recente de grounding e `cv_analysis`
- [x] Fazer o structured analysis detectar quando a fonte é um único CV e priorizar o contexto completo do documento
- [x] Preferir `runtime_metadata.indexing_payload` e texto serializado do CV como grounding primário
- [x] Rebaixar retrieval chunks para papel secundário de suporte no caminho de structured analysis
- [x] Bloquear placeholders como `Company X` sob baixo grounding com guardrail explícito
- [x] Reconstruir o grounding de educação a partir de linhas canônicas mais completas e menos truncadas
- [x] Limpar e deduplicar grounding de skills upstream para reduzir fragmentos OCR quebrados
- [x] Remover `CV PROJECTS` falso quando ele for derivado de educação/GPA/double-degree em vez de projetos reais
- [x] Canonicalizar `education_entries` no output final para manter apenas as 2 entradas reais do CV de Danyel, com datas, localizações e wording forte da USP

#### Fechamento da fase
- [x] Validar a fase com documentos reais complementares ao benchmark sintético (`CV - Lucas -gen.json`, corpus multilayout, casos scan-like e trilha `evidence_cv`)
- [x] Refinar prompts, contexto e grounding do `cv_analysis` com base nesses testes reais
- [x] Documentar os limites atuais do OCR fallback e do parser OCR-first / VL-on-demand
- [x] Executar rollout controlado local do `evidence_cv` sob feature flag, com auto-rollout, semantic gate e telemetria operacional versionada no fluxo real de upload/indexação
- [x] Encerrar a Fase 5 como pacote unificado de produto, com `structured outputs` + `evidence_cv` documentados na mesma fase
- [x] Reposicionar screenshots finais, mini demo e narrativa curta de portfólio para a **Fase 11**, após app web + deploy público

### Entregável
- Módulo de análises estruturadas validado no app principal + pipeline paralelo `evidence_cv` auditável para parsing de currículos, ambos sustentados por smoke eval, benchmark multilayout, OCR fallback e readiness de rollout controlado

### Evidência técnica já disponível
- relatório local de smoke eval da Fase 5
- benchmark sintético mostrando `cv_analysis` robusto em layouts textuais
- exemplo de documento scan-like melhorado via OCR fallback
- relatório de evidências da fase em `docs/PHASE_5_EVIDENCE_PACK.md`
- relatório de avaliação evidence em `docs/PHASE_5_EVIDENCE_EVAL_REPORT.md`
- documentação de readiness em `docs/PHASE_5_OCR_FIRST_VL_ON_DEMAND_PRODUCTION_READINESS.md`
- documentação operacional do pipeline em `docs/README_evidence_cv_pipeline.md`
- relatório de shadow rollout e adjudicação de contatos em `phase5_eval/reports/`

O pacote visual final para README/LinkedIn/demo pública fica propositalmente para a **Fase 11**, depois da evolução para app web e deploy público.

### O que preciso saber defender em entrevista
- por que structured output é importante
- como reduzir respostas inconsistentes
- onde Pydantic ajuda confiabilidade
- por que isso prepara o terreno para automação e agentes
- por que smoke eval local ajuda a sair do “parece funcionar” para “tenho uma verificação mínima reproduzível”
- por que benchmark sintético multilayout ajuda a testar robustez estrutural de CVs
- por que o fallback OCR é útil em documentos image-based
- por que OCR fallback melhora parte dos casos, mas ainda não resolve todos os scans difíceis


## Fase 5.5 — Evolução com LangChain e LangGraph

### Objetivo
Mostrar explicitamente a evolução do projeto dos fundamentos manuais para ferramentas amplamente usadas no mercado.

### Por que essa fase existe?

Porque o projeto já prova que eu entendo o pipeline manual.
Agora ele precisa provar também que eu sei usar o ecossistema profissional sem depender cegamente dele.

### Checklist
- [x] Reimplementar partes-chave do RAG usando LangChain
- [x] Comparar pipeline manual vs LangChain em clareza, produtividade e extensibilidade
- [x] Usar loaders/splitters/retrievers do LangChain quando fizer sentido
- [x] Integrar vector store via LangChain
- [x] Criar primeiro workflow com LangGraph
- [x] Modelar estados e transições de um fluxo real
- [x] Expandir o workflow LangGraph de retry de contexto para roteamento explícito de estratégias e guardrails
- [x] Comparar execução direta vs workflow LangGraph em robustez, latência e previsibilidade operacional
- [x] Fortalecer a abstração de provider para suportar runtimes além de Ollama/OpenAI-compatible
- [x] Separar explicitamente geração, embeddings, reranking e experimentação offline na arquitetura
- [x] Preparar caminho para backend local alternativo via ecossistema Hugging Face sem quebrar a UX atual
- [x] Documentar como e por que a arquitetura evoluiu
- [x] Deixar a comparação explícita para entrevista e portfólio
- [x] Avaliar chains auxiliares do LangChain para tasks estruturadas quando houver ganho claro
- [x] Adicionar tracing/telemetria explícita para fluxos LangChain/LangGraph
- [x] Fortalecer a abstração de provider para suportar runtimes diferentes além de Ollama/OpenAI-compatible
- [x] Separar claramente camada de geração, embeddings, reranking e experimentação offline
- [x] Preparar a arquitetura para incorporar fluxos locais do ecossistema Hugging Face sem acoplá-los cedo demais ao app principal

### Progresso local já entregue

- [x] Adicionar `RAG_LOADER_STRATEGY` com caminho experimental `langchain_basic` e fallback seguro para `manual` em `TXT`/`CSV`/`MD`/`PY`, preservando `PDF` no pipeline customizado
- [x] Adicionar `RAG_CHUNKING_STRATEGY` com caminho experimental `langchain_recursive` e fallback seguro para `manual`
- [x] Adicionar `RAG_RETRIEVAL_STRATEGY` com caminho experimental `langchain_chroma` e fallback seguro para `manual_hybrid`
- [x] Adicionar estratégia experimental `langgraph_context_retry` para orquestrar tasks estruturadas com retry controlado de contexto
- [x] Registrar `workflow_attempts`, `workflow_context_strategies` e `workflow_trace` para tornar o fluxo LangGraph auditável no runtime da execução estruturada
- [x] Adicionar roteamento explícito de estratégia inicial, decisão de guardrail e marcação de `needs_review` no workflow LangGraph
- [x] Expor comparação shadow `direct` vs `langgraph_context_retry` com log local e relatório agregado para medir robustez, latência e qualidade
- [x] Separar resolução de provider de geração vs provider de embeddings com capability explícita e fallback seguro
- [x] Fazer a compatibilidade do índice considerar também o provider de embeddings, além do modelo e da janela de contexto
- [x] Extrair a lógica de reranking híbrido para módulo dedicado, separando melhor retrieval bruto da camada de reranking
- [x] Adicionar testes unitários em `unittest` para reranking e resolução de provider, reduzindo dependência de `pytest` para validar esse slice
- [x] Preparar provider local experimental `huggingface_local` para reduzir acoplamento ao runtime principal e abrir trilha para testes via Transformers
- [x] Endurecer a resolução de provider das tasks estruturadas com capability explícita e telemetria de fallback
- [x] Alinhar `document_context` e retrieval estruturado às configurações efetivas de RAG/embedding da sessão, evitando divergência entre UI e runtime interno
- [x] Expor na UI a seleção explícita do provider de embedding, fechando melhor a separação geração vs embeddings
- [x] Reduzir hardcodes remanescentes na camada estruturada, usando provider/context window efetivos em vez de defaults implícitos do Ollama
- [x] Centralizar a resolução de runtime multi-provider em helpers compartilhados do registry, reduzindo duplicação entre app, `document_context` e camada estruturada
- [x] Extrair a montagem do snapshot operacional da UI para serviço dedicado, reduzindo acoplamento do `main_qwen.py`
- [x] Expor na UI a seleção de chunking e retrieval experimental para comparar a evolução do pipeline manual
- [x] Expor shadow comparison no debug do chat para comparar recuperação manual vs recuperação via LangChain + Chroma na mesma pergunta
- [x] Persistir histórico local das comparações shadow com resumo agregado para apoiar a comparação manual vs LangChain
- [x] Adicionar script de relatório do shadow log para transformar a comparação local em evidência reaproveitável
- [x] Documentar o slice atual em `docs/PHASE_5_5_LANGCHAIN_EVOLUTION.md`

### Entregável
- Pipeline evoluído com LangChain e primeiro workflow controlado com LangGraph

### Evidência para GitHub/LinkedIn
- diagrama comparando pipeline manual vs framework
- commit/release mostrando a evolução
- README com seção “por que LangChain/LangGraph entrou agora e não antes”

### O que preciso saber defender em entrevista
- por que comecei manualmente
- quando faz sentido abstrair com framework
- diferença entre LangChain e LangGraph
- como decidir entre controle manual e produtividade do ecossistema

---

## Fase 6 — Tools e agentes orientados a valor de negócio

### Objetivo
Introduzir tools e agentes de forma coerente com o projeto atual, focando em valor empresarial e não só em “agente por agente”.

### Direção recomendada

Em vez de um agente genérico, priorizar algo que recrutador consiga mapear para uso real em empresa.

### Papel recomendado do LangGraph nesta fase

Nesta fase, o LangGraph deve ser o orquestrador preferencial dos fluxos com estado explícito, especialmente para:

- roteamento de intenção
- seleção de tools
- fallback quando o contexto vier fraco
- guardrails antes da resposta final
- estados de `needs_review` / `human_in_the_loop`
- trilha auditável de decisões do agente

### Agente-alvo recomendado

#### **Document Operations Copilot**

Um agente que:

- entende a intenção do usuário
- consulta documentos indexados
- extrai informação estruturada
- compara documentos
- gera resumo executivo
- cria checklist de ação
- responde com fontes
- aponta confiança e necessidade de revisão humana

### Fluxo recomendado do agente

1. **Classificar intenção**
   - pergunta documental
   - resumo
   - comparação
   - extração estruturada
   - checklist de ação
   - elaboração de resposta

2. **Recuperar contexto**
   - buscar chunks relevantes
   - aplicar filtros
   - rerankear quando existir reranker

3. **Escolher modo de resposta**
   - explicação livre
   - JSON
   - checklist
   - comparação estruturada

4. **Validar / enriquecer**
   - validar schema
   - garantir fontes
   - estimar confiança
   - marcar necessidade de revisão humana

5. **Mostrar saída final**
   - resposta principal
   - fontes
   - metadados
   - confiança / revisão humana

### Exemplos de agentes mais interessantes
- [x] **Agente de análise documental**: lê documentos, resume, extrai pontos-chave e identifica riscos
- [x] **Agente de policy/compliance**: responde com base em documentos e aponta violações ou conflitos
- [x] **Agente de extração operacional**: transforma documentos em dados estruturados, checklists e tarefas
- [x] **Agente assistente técnico**: combina RAG + modo programador + outputs estruturados

### Checklist
- [x] Criar tool para consultar documentos indexados
- [x] Criar tool para resumir arquivo/documento
- [x] Criar tool para extração estruturada
- [x] Criar tool para comparação entre documentos
- [x] Criar tool para gerar checklist operacional
- [x] Criar workflow com LangGraph para orquestração do agente
- [x] Modelar no LangGraph os estados do agente documental: intenção, recuperação, decisão de tool, validação e resposta final
- [x] Adicionar nós de guardrail e fallback no LangGraph para grounding fraco, falha de tool e saída inválida
- [x] Adicionar estado explícito de revisão humana (`needs_review`) no workflow do agente
- [x] Implementar roteador de intenção
- [x] Registrar logs de decisão do agente
- [x] Explicar limitações e guardrails
- [x] Exibir fontes, metadados e necessidade de revisão humana

### O que eu não devo fazer nesta fase
- [ ] evitar multiagente por moda sem necessidade
- [ ] evitar agente “navega tudo sem controle” só para parecer sofisticado
- [ ] evitar demo confusa com muitas tools soltas e pouco valor real

### Entregável
- Agente local com ferramentas reais e workflow definido, orientado a um caso empresarial plausível

### Status atual da fase

A Fase 6 pode ser tratada como concluída do ponto de vista técnico/local.

Critérios já cumpridos:

- catálogo explícito de tools do `Document Operations Copilot` com disponibilidade por contexto documental
- roteamento de intenção e seleção de tool com LangGraph
- guardrails de grounding, fallback e `needs_review` no workflow do agente
- resposta final com fontes, tool runs, metadados auditáveis e explicabilidade operacional
- UI friendly e runtime snapshot/sidebar expondo tools avaliadas, limitações, guardrails e próximos passos
- testes unitários cobrindo roteamento, handler do agente, snapshot e guardrails do workflow
- persistência local auditável das execuções do agente documental, com resumo agregado e script dedicado de relatório

### Evidência para GitHub/LinkedIn
- GIF mostrando decisão de ferramenta
- diagrama simples do workflow do agente
- demo de comparação de documentos / extração em JSON / resumo executivo

### O que preciso saber defender em entrevista
- diferença entre chatbot simples e agente com tools
- por que workflow controlado é melhor que “autonomia irrestrita”
- por que um agente documental é mais forte para empresa do que um agente genérico de conversa

---

## Fase 7 — Benchmark e comparação entre modelos

### Objetivo
Mostrar critério técnico, não apenas acúmulo de features.

### Checklist
 - [x] Criar tela de comparação entre modelos
 - [x] Enviar o mesmo prompt para múltiplos modelos
 - [x] Exibir respostas lado a lado
 - [x] Medir latência
 - [x] Medir tamanho da saída
 - [x] Avaliar aderência ao formato
 - [x] Salvar resultados de benchmark
- [x] Comparar local vs cloud opcional
- [x] Comparar embeddings e estratégias de retrieval
- [x] Comparar fluxo direto vs workflow LangGraph em latência, taxa de sucesso e previsibilidade operacional
- [x] Comparar modelos servidos via Ollama vs modelos experimentados pelo ecossistema Hugging Face
- [x] Comparar quantizações quando isso fizer diferença real no hardware local
- [x] Comparar stacks por caso de uso, e não só por benchmark genérico
- [x] Documentar quando Ollama é melhor como runtime e quando Hugging Face é melhor como ambiente de experimentação

Observação: nesta rodada, isso foi fechado no **escopo técnico/local** por meio de classificação de famílias de quantização, presets repetíveis por caso de uso e guidance arquitetural/documental. Campanhas empíricas maiores continuam possíveis depois, mas já não bloqueiam o encerramento da Fase 7.

### Métricas recomendadas
- [x] Tempo de resposta
- [x] Tamanho da resposta
- [x] Aderência ao schema
- [x] Relevância
- [x] Groundedness no caso de RAG
- [x] Precisão de extração estruturada
- [x] Qualidade percebida por caso de uso
- [ ] Tempo de inicialização/carregamento do modelo
- [ ] Consumo de RAM/VRAM
- [x] Flexibilidade para testar quantizações
- [x] Facilidade de serving local
- [ ] Facilidade de futura adaptação/fine-tuning

### Entregável
- Módulo de benchmarking com evidência comparativa

### Status atual da fase

A Fase 7 pode ser tratada como concluída do ponto de vista técnico/local.

Critérios já cumpridos:

- comparação lado a lado entre múltiplos providers/modelos no app
- métricas por execução e por candidato para latência, tamanho de saída e aderência ao formato
- heurísticas adicionais para groundedness, schema adherence e use-case fit
- benchmark por caso de uso com presets repetíveis
- classificação por runtime bucket e família de quantização
- suporte arquitetural a `ollama`, `huggingface_server`, `huggingface_inference` e trilha experimental `huggingface_local`
- logs persistidos, leaderboards agregados e relatório JSON reaproveitável
- benchmark de estratégias adjacentes reaproveitando retrieval shadow e direct vs LangGraph
- documentação dedicada da fase e guidance explícito sobre Ollama vs Hugging Face

O que permanece fora do fechamento técnico/local da Fase 7 e sobe como trabalho futuro/empírico:

- campanhas maiores de benchmark com mais modelos reais e mais hardware/perfis de serving
- medição de inicialização de modelo, RAM/VRAM e custo operacional mais fino
- comparação empírica expandida de adaptação/fine-tuning, que já encosta na Fase 8.5

### Evidência para GitHub/LinkedIn
- tabela ou gráfico comparando modelos
- documento com principais conclusões do benchmark
- comparação entre embeddings / retrievals / contexto

### O que preciso saber defender em entrevista
- como escolhi o melhor modelo para cada caso
- quais métricas usei e por quê
- como diferenciei benchmark de produto vs benchmark de experimentação
- por que benchmark sem contexto de uso pode ser enganoso

---

## Fase 8 — Evals

### Objetivo
Criar uma camada de qualidade e repetibilidade.

### Status atual da fase

A Fase 8 foi iniciada com uma fundação local de evals persistidos.

O que já ficou pronto nesta primeira rodada:

- [x] store local em SQLite para registrar execuções de eval (`.phase8_eval_runs.sqlite3`)
- [x] persistência automática das execuções do `structured_smoke_eval`
- [x] persistência automática das execuções do `checklist_regression`
- [x] persistência automática das execuções do `evidence_cv_gold_eval`
- [x] script de relatório agregado para o store local de evals
- [x] teste unitário da camada de storage/sumarização dos evals
- [x] documentação inicial da foundation de evals em `docs/PHASE_8_EVAL_FOUNDATION.md`
- [x] filtros por suite/task no relatório agregado da Fase 8
- [x] importador de histórico para backfill dos JSONs antigos no store SQLite, com deduplicação por `run_key`
- [x] camada diagnóstica para destacar falhas persistentes, tasks saudáveis e candidatos de adaptação/fine-tuning
- [x] suite determinística para avaliar roteamento do agente documental e decisões/transições do workflow LangGraph
- [x] workflow separado para evals live dependentes de ambiente (`.github/workflows/phase8-evals-live.yml`)
- [x] runner consolidado de evals reais com preflight, indexação opcional e execução em lote (`scripts/run_phase8_live_evals.py`)
- [x] registro reproduzível de materiais públicos extras e helper de download para fortalecer os casos reais de eval
- [x] indexação dos documentos faltantes do manifesto real e rerun do ciclo live completo com nova evidência no SQLite
- [x] correção do falso positivo de `collapsed_items` no `checklist_regression`
- [x] melhoria da trilha `evidence_cv_gold_eval` com recuperação melhor de `name`/`location` em casos reais de CV

O que isso significa na prática:

- a Fase 8 já deixou de depender só de JSONs soltos
- agora existe uma base reaproveitável para acumular resultados de qualidade ao longo do tempo
- os próximos passos naturais são expandir o catálogo de suites/casos e começar a avaliar critérios semânticos com mais profundidade

### Checklist
- [x] Montar conjunto de testes para documentos
- [x] Montar conjunto de testes para tarefas de código
- [x] Montar conjunto de testes para extração estruturada
- [x] Montar conjunto de testes para resumo
- [x] Montar conjunto de testes para comparação documental
- [x] Avaliar formato correto
- [x] Avaliar relevância
- [x] Avaliar consistência
- [x] Avaliar cobertura da resposta
- [x] Avaliar groundedness em RAG
- [x] Avaliar precisão de citações/fontes
- [x] Avaliar acurácia do roteamento de intenção
- [x] Avaliar acurácia das transições e decisões do workflow LangGraph
- [x] Avaliar taxa de retries úteis vs retries desnecessários nos fluxos LangGraph
- [x] Avaliar tempo de resposta
- [x] Salvar resultados em SQLite
- [x] Considerar integração com DeepEval depois da base própria pronta
- [x] Definir critérios objetivos para decidir se fine-tuning é realmente necessário
- [x] Medir falhas persistentes por tarefa mesmo após ajustes de prompt, retrieval e schema
- [x] Identificar tarefas candidatas a adaptação de modelo: extração estruturada, classificação, reranking ou embeddings
- [x] Registrar explicitamente quando prompt + RAG + reranking já são suficientes e quando não são

### Entregável
- Módulo de avaliação contínua e reproduzível

### Evidência para GitHub/LinkedIn
- tabela com casos de teste
- screenshot do painel de resultados de avaliação
- documento mostrando antes/depois de melhorias guiadas por evals

### O que preciso saber defender em entrevista
- como validar qualidade de IA em um time real
- diferença entre avaliar manualmente e medir com critérios repetíveis
- como usei evals para decidir se valia ou não adaptar modelos
- por que evals precisam estar ligados a casos de uso reais

---

## Fase 8.5 — Adaptação de modelos com Hugging Face, quantização e fine-tuning leve

### Objetivo
Transformar benchmark + evals em uma decisão técnica sobre **quando comparar runtimes/modelos/quantizações**, **quando ajustar embeddings ou rerankers** e **quando realmente vale adaptar modelo** em vez de continuar iterando prompt + RAG + schema.

### Por que essa fase existe?

Porque o projeto já terá benchmark, evals e casos de uso mais claros.
Assim, adaptação de modelo deixa de ser “feature por moda” e passa a ser uma decisão técnica justificável.

### Papel do `hf_local_llm_service` nesta fase

Nesta fase, o `hf_local_llm_service` deve ser tratado como **hub local de experimentação**, não como novo runtime obrigatório do produto.

Leitura arquitetural recomendada:

- **`ollama` continua como runtime default** do app principal
- **`hf_local_llm_service` entra como camada de comparação e experimentação**
- o serviço pode expor runtimes/aliases para:
  - `huggingface_server`
  - `huggingface_local`
  - `huggingface_mlx`
  - `llama_cpp`
  - `ollama`
- o app principal continua funcionando mesmo sem expandir mais o serviço

Ou seja: melhorias futuras no serviço ajudam a 8.5, mas **não bloqueiam** o início da fase.

### Direção recomendada

A prioridade desta fase deve ser:

1. comparação de runtimes, variantes e quantizações locais
2. experimentação com embeddings e rerankers antes de mexer no LLM
3. decisão explícita sobre quando prompt + RAG + reranking já são suficientes
4. fine-tuning leve com LoRA/PEFT apenas em tarefa específica e bem delimitada
5. documentação honesta de custo, ganho e complexidade

### Ordem recomendada dentro da fase

#### 8.5A — comparação de runtime/modelo
- comparar `ollama`, `huggingface_server`, `huggingface_local`, `huggingface_mlx` e `llama_cpp` quando fizer sentido no hardware local
- comparar famílias de modelo e especializações por caso de uso
- comparar quantizações relevantes para latência, memória e estabilidade

#### 8.5B — retrieval/embedding adaptation first
- testar embeddings e rerankers antes de concluir que o LLM precisa ser adaptado
- medir se o ganho real vem mais de retrieval do que de mudança/adaptação do gerador

#### 8.5C — decision gate orientado por evals
- usar a Fase 8 para provar falha persistente
- só promover adaptação quando prompt + RAG + schema + reranking não fecharem o gap

#### 8.5D — adaptação leve somente se justificada
- executar um experimento pequeno de LoRA/PEFT em task específica
- comparar baseline vs adaptado com critérios explícitos
- registrar honestamente quando **não** vale seguir com a adaptação

### Critério de entrada para adaptação

A adaptação só deve entrar quando houver evidência clara de pelo menos parte destes sinais:

- falha persistente em evals após iterações de prompt, grounding, schema e retrieval
- task estreita e repetível, com hipótese clara de melhoria
- métrica objetiva de sucesso (`pass_rate`, `schema_adherence`, `groundedness`, `use-case fit` ou similar)
- baseline já documentado para comparação justa

### Rodada 0 — audit / preflight de fechamento

- [x] consolidar audit do que já existia na Fase 8.5 antes de fechar a fase
- [x] gerar artefato de readiness/closure com benchmark + eval + diagnosis
- [x] explicitar o que está totalmente suportado vs parcialmente suportado no bundle final

### O que priorizar
- [x] fechar a trilha Hugging Face do ecossistema atual com catálogo seguro e suporte HTTP/local já existente no repositório
- [x] usar o `hf_local_llm_service` / `huggingface_server` como hub de experimentação sob contrato HTTP único onde o path já é limpo
- [x] comparar os runtimes atualmente suportados no repo (`ollama`, `huggingface_server`, `huggingface_local`) e registrar explicitamente os runtimes fora do fechamento atual (`huggingface_mlx`, `llama_cpp`)
- [x] classificar runtime bucket / quantização / path operacional nas saídas de benchmark
- [x] avaliar tarefas estruturadas e estreitas via decision gate em vez de pular direto para treino pesado
- [x] comparar embeddings e rerankers antes de ajustar o LLM inteiro
- [x] criar scaffold conservador para adaptação leve por task específica, sem executar jobs pesados nesta fase
- [x] comparar baseline vs prompt/RAG/schema vs retrieval/reranker vs troca de runtime/modelo e registrar quando modelo adaptado ainda não é necessário
- [x] documentar custo operacional, complexidade e ganho real
- [x] avaliar se embeddings ou rerankers ajustados geram mais valor do que ajustar o LLM inteiro
- [x] registrar claramente quando **não** vale adotar a adaptação
- [x] montar matriz comparativa por runtime/modelo/quantização com qualidade, latência, complexidade operacional e limites explícitos do bundle atual

### Backlog opcional do `hf_local_llm_service` para fortalecer a 8.5

Esses itens ajudam, mas **não são pré-requisito** para começar a fase:

- [ ] suportar múltiplos presets nomeados por alias/provider
- [ ] adicionar editor visual dedicado desses presets na UI do serviço
- [ ] padronizar melhor as métricas entre runtimes diferentes
- [ ] adicionar store/log simples de experimentos comparativos no serviço

### O que evitar nesta fase
- [x] Evitar full fine-tuning grande de LLM como foco principal do projeto
- [x] Evitar abrir uma frente pesada sem evidência dos evals
- [x] Evitar treinar “por treinar” sem hipótese e sem métrica de sucesso
- [x] Evitar transformar o `hf_local_llm_service` em um produto paralelo antes de provar o valor experimental da fase
- [x] Evitar adaptar o LLM antes de testar direito embeddings, rerankers e troca de runtime/modelo

### Candidatos mais inteligentes para adaptação identificados nesta fase
- [x] Extração estruturada
- [x] Extração/contatos de CV
- [ ] Classificação de intenção
- [ ] Reranking
- [ ] Embeddings
- [ ] Formatação rígida de saída

### Status final da fase

- [x] Round 0 — audit/preflight de fechamento implementada
- [x] Round 1 — benchmark core de geração/runtime + embeddings integrado ao workflow resumable
- [x] Round 2 — rerankers + OCR/VLM fallback integrados ao workflow resumable
- [x] Round 3 — decision gate implementada com resumo JSON + markdown
- [x] expansão incremental documentada: embeddings com subsets general/code, rerankers neurais locais condicionais e matriz OCR/VLM configurável com runtime-family explícita
- [x] scaffold conservador de adaptação leve implementado como artefato/configuração, sem treinamento pesado
- [x] relatório final de closure da Fase 8.5 implementado com distinção entre fully supported vs partially supported
- [x] documentação e testes focados atualizados para sustentar a narrativa técnica da fase

### Extensão recomendada — benchmark automation expandido da Fase 8.5

Para um alvo mais ambicioso de portfólio, a fase pode continuar evoluindo como um **fully automated, reproducible local benchmarking system**. O que entra nessa expansão:

- matriz explícita requested-vs-resolved para modelos locais
  - `qwen3.5:4b`
  - `phi4-mini:3.8b`
  - `qwen2.5-coder:7b`
  - equivalentes locais HF/MLX quando disponíveis
- challengers locais de embeddings com política de substituição documentada
- ranking requested-vs-resolved transparente em relatórios finais
- benchmark mais forte de HF local / MLX local quando o path estiver limpo no ambiente
- métricas operacionais mais profundas (`cold start`, `warm start`, `TTFT`, throughput, memória) quando houver instrumentação confiável por runtime

Regra importante de honestidade:

- a implementação atual da 8.5 **não deve fingir suporte universal** a todas as famílias de runtime/modelo do prompt expandido
- o que não tiver path limpo no repo deve permanecer como:
  - `closest_available`
  - `skipped`
  - ou `support boundary` explícita

### Limites atuais que ainda podem subir como trabalho futuro

- ampliar benchmark neural de rerankers além do baseline híbrido já limpo no repo
- ampliar benchmark OCR/VLM com mais runtimes locais dedicados
- validar HF local / MLX local com catálogos maiores e chat-template fairness mais forte
- adicionar métricas operacionais mais profundas por provider/runtime

### Roadmap explícito para finalizar a 8.5 expandida

- [x] documentar a expansão recomendada e os limites atuais
- [x] registrar política explícita de requested-vs-resolved model mapping
- [x] fechar suporte limpo às famílias de runtime HF local / HF service / MLX local que realmente existirem no ambiente atual e registrar limites explícitos para os demais paths
- [x] investigar e explicar a divergência do `embeddinggemma` via `hf_local_llm_service` quando o serviço passar isoladamente mas falhar no benchmark
- [x] adicionar métricas operacionais mais profundas (`cold start`, `warm start`, `TTFT`, throughput, memória)
- [x] ampliar rerankers neurais quando houver path local limpo
- [x] ampliar OCR/VLM fallback matrix quando houver runtimes locais limpos
- [x] rerodar benchmark expandido smoke-safe + audit + decision gate + closure
- [x] rerodar campanha expandida non-smoke por grupos em ordem estável + audit + decision gate + closure

Documento detalhado de execução dessa finalização:

- `docs/PHASE_8_5_EXPANDED_COMPLETION_ROADMAP.md`

### Pacotes de trabalho para fechar a 8.5 expandida

#### A. Runtime-family normalization e inventory hardening
- [x] inventariar com clareza os runtimes locais realmente disponíveis para benchmark
  - [x] `ollama`
  - [x] `huggingface_local`
  - [x] `huggingface_server`
  - [x] equivalentes `MLX local` quando houver path limpo no ambiente
- [x] diferenciar explicitamente `requested_runtime_family` vs `resolved_runtime_family`, e não só `requested_model` vs `resolved_model`
- [x] endurecer os metadados de benchmark para registrar motivo de resolução/substituição
- [x] validar fairness de chat template no caminho HF local antes de comparar com Ollama
- [x] reproduzir e explicar/corrigir a divergência do `embeddinggemma` via `hf_local_llm_service`

#### B. Métricas operacionais mais profundas
- [x] adicionar slice inicial de métricas operacionais em geração com:
  - `total wall time`
  - `TTFT`
  - `throughput tokens/s`
- [x] marcar status de métrica como `measured` vs `not_supported` nas saídas atuais
- [x] expor esse slice inicial em raw events, CSVs normalizados, sumários agregados e markdown report
- [x] adicionar contrato explícito de métricas para:
  - [x] `cold start`
  - [x] `warm start`
  - [x] `TTFT`
  - [x] `total wall time`
  - [x] `throughput`
  - [x] `memory snapshot / peak estimate`
- [x] marcar cada métrica como:
  - [x] `measured`
  - [x] `estimated`
  - [x] `not_supported`
- [x] expor essas métricas em raw events, CSVs normalizados, sumários agregados e markdown report

#### C. Embedding expansion
- [x] fechar benchmark explícito de embeddings gerais + code subset
- [x] adicionar challengers HF/MLX locais quando houver path executável limpo
- [x] documentar quando um embedding geral estiver sendo reutilizado como melhor fallback disponível para código

#### D. Neural reranker expansion
- [x] criar adapter pequeno e limpo para challengers de reranker neural locais
- [x] benchmarkar baseline atual, híbrido atual e challengers neurais realmente disponíveis
- [x] manter `skipped` explícito para challengers indisponíveis ou sem path limpo

#### E. OCR / VLM expanded fallback matrix
- [x] manter `hybrid` e `complete` como baseline
- [x] adicionar fallbacks OCR/VLM locais adicionais quando houver suporte limpo
- [x] comparar qualidade por campo + custo de latência + ganho real do fallback

#### F. Rerun final + closure expandida
- [x] rerodar `preflight`
- [x] rerodar `smoke`
- [x] suportar e executar campanha expandida por grupos em ordem estável via `--staged-campaign` com bundles merged smoke-safe e non-smoke
- [x] regenerar `audit`, `decision gate` e `closure`
- [x] só declarar a 8.5 expandida como concluída quando esses artefatos estiverem consistentes com o escopo maior

### Critério explícito para considerar a 8.5 expandida totalmente concluída

- [x] generation matrix forte com requested-vs-resolved auditável
- [x] embedding matrix forte incluindo code subset
- [x] reranker matrix com baseline + challengers neurais locais quando suportados
- [x] OCR/VLM matrix ampliada com fallback trade-offs documentados
- [x] métricas operacionais mais ricas do que apenas wall-time simples
- [x] closure final coerente com o escopo expandido, sem overclaim de runtimes sem path limpo

### Ordem recomendada de execução no hardware atual

1. `preflight` de todos os grupos
2. `smoke` de todos os grupos
3. full run de `generation`
4. full run de `embeddings`
5. full run de `rerankers`
6. full run de `ocr_vlm`
7. `decision gate`
8. `closure`

Nota importante de honestidade operacional:

- a **implementação** da Fase 8.5 está fechada do ponto de vista técnico/local
- o bundle final de closure pode continuar marcando **suporte parcial de Round 2** enquanto o benchmark mais recente ainda não incluir uma execução real com `rerankers` + `ocr_vlm`
- isso não significa que o workflow esteja incompleto; significa apenas que a **evidência empírica mais recente** ainda depende de rodar esse slice quando for apropriado executar benchmarks

### Entregável
- Relatório técnico mostrando quando Hugging Face, troca de runtime, quantização, embeddings/rerankers e fine-tuning leve geram ganho real — e quando **não** compensam

### Evidência para GitHub/LinkedIn
- gráfico comparando runtimes/modelos/quantizações ou baseline vs adaptado
- tabela de trade-offs entre qualidade, custo, latência, footprint e complexidade
- write-up explicando por que a adaptação foi ou não foi adotada
- registro explícito de quando trocar embedding/reranker foi mais útil do que adaptar o gerador

### O que preciso saber defender em entrevista
- por que não comecei com fine-tuning
- por que tratei o `hf_local_llm_service` como hub de experimentação, e não como novo default do produto
- como decidi que valia adaptar
- por que LoRA/PEFT fez mais sentido do que treino completo
- quando Hugging Face agrega mais do que Ollama
- por que embeddings e rerankers podem gerar mais ROI do que ajustar o LLM inteiro
- como medi custo vs ganho

---

## Fase 9 — Observabilidade

### Objetivo
Monitorar o comportamento do sistema de IA.

### Checklist
- [x] Registrar provider/modelo usado
- [x] Registrar prompt profile
- [x] Registrar `context_window`
- [x] Registrar embedding model usado
- [x] Registrar parâmetros de RAG
- [x] Registrar arquivos consultados
- [x] Registrar chunks recuperados
- [x] Registrar tool usada
- [x] Registrar tempo de retrieval
- [x] Registrar tempo de geração
- [x] Registrar `workflow_id`, nós percorridos, transições, retries e fallback reasons dos fluxos LangGraph
- [x] Registrar resultado da avaliação
- [x] Registrar erros
- [x] Criar dashboard local com métricas
- [x] Criar visualização de histórico de execuções

### Entregável
- Painel local de logs e métricas

### Evidência para GitHub/LinkedIn
- screenshot do dashboard
- documento resumindo observabilidade e rastreabilidade

### O que preciso saber defender em entrevista
- como diagnosticar problemas em apps com LLM
- por que observabilidade importa mesmo em protótipos
- como relacionar latência, retrieval, contexto e qualidade da resposta

---

## Fase 9.25 — AI runtime economics, usage observability e budget-aware routing

### Objetivo
Transformar a observabilidade atual em uma camada explícita de consumo operacional, custo estimado e roteamento orientado a budget.

### Por que essa fase existe

O objetivo do projeto não é só responder bem, mas também se comportar como um **produto de IA útil para negócios**. Isso exige responder perguntas como:

- quanto custa cada fluxo do app
- quantos tokens são consumidos por tipo de task
- quando vale usar local vs cloud
- quando OCR/VLM realmente se paga
- quando o sistema deve degradar para um caminho mais barato e previsível

Essa fase entra **depois da Fase 9**, porque depende da base de observabilidade já criada, e **antes da Fase 9.5**, porque integrar MCP sem visibilidade de consumo/custo tende a tornar o produto mais caro e mais difícil de governar.

### Direção recomendada

- consolidar métricas de uso em um modelo unificado de execução
- transformar `prompt_tokens`, `completion_tokens`, `total_tokens`, chars de contexto, OCR/VLM usage e latência em métricas operacionais do produto
- criar políticas explícitas de budget por task/fluxo/provider
- usar essas métricas para decidir roteamento, fallback e degradação controlada
- começar em **rollout conservador**, com visibilidade e quality floor antes de qualquer corte agressivo

### Princípios do budget-aware routing

- **qualidade primeiro, otimização depois**
- tasks de alta sensibilidade devem operar em modo `quality_first`
- degradação automática só deve começar em tasks de baixa/média sensibilidade e com evidência de que o impacto é aceitável
- toda decisão de budget routing deve ser auditável (`mode`, `reason`, `quality_floor`, `auto_degrade_applied`)
- budgets só devem virar automação permanente depois de comparação controlada em evals/benchmarks

### Sensibilidade por task

#### Alta sensibilidade
- `document_agent`
- `summary`
- `extraction`
- `cv_analysis`
- fluxos de `policy/compliance/risk review`

Nessas tasks, a expectativa é priorizar qualidade e grounding, mesmo quando o custo operacional for maior.

#### Média sensibilidade
- `chat_rag`
- `checklist`
- `code_analysis`

Nessas tasks, o budget routing pode atuar primeiro em knobs mais seguros, como candidate pool e ajustes conservadores de contexto.

#### Baixa sensibilidade
- roteamentos auxiliares
- flows comparativos rápidos
- heurísticas operacionais não críticas

Nessas tasks, a automação de economia pode ser mais agressiva, desde que continue observável.

### Checklist
- [x] consolidar uma camada única de usage/runtime metrics por execução
- [x] registrar `prompt_tokens`, `completion_tokens`/`generation_tokens` e `total_tokens` quando o provider/runtime expuser esses dados
- [x] registrar custo estimado por execução para providers pagos/opcionais
- [x] registrar chars de contexto enviados, chunks usados/descartados e impacto do truncamento
- [x] registrar quando OCR, Docling e VLM foram acionados e com que impacto operacional
- [ ] criar visão agregada de consumo por fluxo (`chat`, `structured`, `document_agent`, `comparison`)
- [x] criar visão agregada de consumo por provider/modelo
- [x] introduzir budgets por task e thresholds de alerta
- [x] implementar **budget-aware routing** (ex.: preferir caminho mais barato quando suficiente)
- [ ] definir política de fallback local/cloud orientada a custo, latência e qualidade
- [ ] documentar trade-offs de custo vs qualidade por caso de uso
- [ ] validar budget-aware routing contra evals para confirmar que não derruba tasks críticas abaixo do quality floor

### Status local adiantado nesta rodada

- histórico agregado de execução enriquecido com latência de build de prompt, pressão de contexto, truncamento, auto-degrade e sinais documentais (OCR/Docling/VLM)
- runtime snapshot/sidebar agora mostram melhor o estado operacional recente de chat e structured
- captura de usage nativo quando o provider expõe telemetria e estimativa de custo por execução para providers pagos/opcionais
- budgets por task, thresholds de alerta e budget-aware routing já existem localmente com trilha auditável no runtime
- ainda falta fechar budgets explícitos por task, policy de fallback e validação sistemática contra evals

### Métricas alvo
- [x] tokens por request
- [x] custo estimado por request
- [ ] custo estimado por task
- [ ] custo estimado por provider/modelo
- [ ] latência por fluxo
- [ ] uso de OCR/VLM por fluxo
- [ ] taxa de fallback para caminhos mais caros
- [ ] taxa de sucesso sob budget

### Entregável
- camada de cost & usage observability integrada ao app, com budget-aware routing e evidência clara de custo operacional por fluxo

### Evidência para GitHub/LinkedIn
- dashboard mostrando tokens, custo estimado e latência por fluxo
- tabela comparando local vs cloud por custo/qualidade
- write-up curto explicando como o produto decide entre caminhos mais baratos e mais caros

### O que preciso saber defender em entrevista
- por que custo em IA não é só preço de API, mas também contexto, OCR, reranking e latência
- como medi consumo operacional do app
- como defini budget-aware routing
- como equilibrei qualidade, custo e previsibilidade para um produto de negócio

---

## Fase 9.5 — MCPs e integrações operacionais empresariais

### Objetivo
Conectar o copiloto documental a fontes e sistemas externos via MCP, com foco em casos de uso empresariais úteis, auditáveis e de baixo custo operacional.

### Tese desta fase
Esta fase transforma o projeto de uma aplicação de IA com base documental em um **copiloto operacional empresarial** capaz de:

- consultar bases documentais externas
- comparar versões de documentos e políticas
- extrair gaps, riscos, obrigações e próximos passos
- gerar evidence packs e checklists operacionais
- registrar pendências com trilha auditável

### Por que esta fase entra aqui

Ela faz mais sentido **depois da Fase 9**, porque o projeto já passa a ter:

- observabilidade suficiente para medir latência, qualidade e custo operacional
- agente documental e tools já estabelecidos
- evals e guardrails suficientes para suportar integração com sistemas reais

E faz mais sentido **antes das fases finais de engenharia, deploy e portfólio**, para que o MCP já faça parte da identidade do produto antes da versão pública/demonstrável.

### Vertical recomendada

Começar com uma vertical principal, gratuita e muito alinhada ao projeto atual:

- **EvidenceOps MCP**

Essa vertical mira cenários de:

- compliance
- auditoria
- procurement
- governança documental

### Decisão de direção já tomada nesta trilha

Para o fechamento da Fase 9.5, a direção oficial do projeto passa a ser:

- **`Nextcloud/WebDAV`** como alvo principal do **Document Repository MCP**
- **`Trello`** como alvo principal do **Worklog / Action MCP**
- **`Notion`** como camada de **evidence register / dashboard operacional / handoff executivo**

Leitura arquitetural desejada:

- `filesystem + SQLite` continuam como **baseline local e fallback auditável**
- `Nextcloud/WebDAV + Trello + Notion` passam a ser a **tríade externa-alvo** da fase
- `GitHub Issues` deixa de ser a direção principal e vira apenas uma opção secundária para contextos mais dev-centric

### Decisão oficial de corpus da demo 9.5

O corpus principal oficial da demo da Fase 9.5 passa a ser:

- **`data/corpus_revisado/option_b_synthetic_premium`**

O corpus complementar/canônico de validação pública continua sendo:

- **`data/corpus_revisado/option_a_public_corpus_v2`**

Mapeamento-alvo:

- `option_b_synthetic_premium` -> base principal de `Nextcloud/WebDAV`, storylines de `Trello` e registers de `Notion`
- `option_a_public_corpus_v2` -> complemento público/canônico para benchmark, validação e referências
- operações com forte dependência de evidências e revisão humana

### Direção recomendada

- começar com **1 vertical forte**, não com muitas integrações dispersas
- priorizar integrações gratuitas / self-hosted
- manter human-in-the-loop em ações sensíveis
- usar MCP para consulta + ação operacional leve, sempre com grounding e rastreabilidade

### Checklist
- [x] definir o caso principal do MCP (`EvidenceOps MCP`)
- [x] definir a tríade externa-alvo da fase 9.5 (`Nextcloud/WebDAV` + `Trello` + `Notion`)
- [x] promover a vertical local para **MCP server real** + **cliente MCP do app**
- [ ] criar um **Document Repository MCP** usando target oficial `Nextcloud/WebDAV`
- [ ] criar um **Worklog / Action MCP** usando target oficial `Trello`
- [ ] criar uma camada `Notion` para evidence register, dashboard operacional e handoff executivo
- [ ] criar um corpus de demo curado para negócio (`policies`, `contracts`, `audit`, `templates`, `gold_sets`)
- [ ] suportar busca documental externa e recuperação com fontes via MCP
- [ ] suportar comparação de versões e drift documental (policy/contract/template)
- [ ] extrair gaps, obrigações, riscos, owners e prazos em output estruturado
- [ ] gerar checklist operacional com fontes rastreáveis
- [x] montar evidence pack estruturado reaproveitável
- [x] registrar pendências/ações em store auditável
- [ ] adicionar guardrails, permissões e revisão humana nas ações sensíveis
- [x] medir latência, consumo e custo operacional por fluxo MCP local
- [x] criar demo end-to-end local do caso empresarial via MCP
- [ ] criar demo end-to-end com adapters externos (`Nextcloud/WebDAV` + `Trello` + `Notion`)

### Status local adiantado nesta rodada

- o worklog local do EvidenceOps agora gera `evidence_pack` estruturado com contagens por finding/action/owner/status/due_date
- o agregado local já resume melhor documentos únicos, tipos de finding e distribuição operacional
- agora também existe store auditável local em `SQLite` para pendências/ações derivadas do worklog (`.phase95_evidenceops_actions.sqlite3`)
- a vertical foi promovida para **MCP server real em stdio** com tools/resources de repository, worklog e action store
- o app agora tem **cliente MCP próprio** e já usa MCP no fluxo principal do `document_agent`
- a observabilidade agora já mede **métricas específicas de MCP** no runtime snapshot/sidebar
- existe demo end-to-end local por script e também console operacional do MCP dentro do app
- a parte de adapters externos (`Nextcloud/WebDAV`, `Trello`, `Notion`) continua pendente e depende de credenciais/configuração

### Stack gratuita sugerida
- `filesystem` local como baseline
- `Nextcloud` / `WebDAV` para base documental remota sem custo
- `Trello` para fila operacional, owners, comentários e fluxo humano de ações
- `Notion` para evidence register, dashboard operacional e visibilidade executiva
- `SQLite` para store operacional local/fallback auditável
- `GitHub Issues` apenas como opção secundária se o contexto do time for fortemente dev-centric
- `Ollama` / `hf_local_llm_service` como camada principal de inferência local

### O que ainda depende de setup externo

Para fechar a fase completa no sentido do roadmap, ainda serão necessários:

- **Nextcloud/WebDAV**
  - base URL
  - usuário
  - senha ou app password
  - pasta/base documental alvo
- **Trello**
  - API key
  - token
  - board alvo
  - listas/estados mínimos (`Open`, `Review`, `Approved`, `Done` ou equivalente)
- **Notion**
  - integration token
  - database IDs ou page IDs
  - definição mínima do schema para evidence packs, status, owner, due date e links de origem

### Entregável
- primeiro MCP empresarial útil e auditável, integrado ao copiloto documental, com caso de uso demonstrável de negócio

### Evidência para GitHub/LinkedIn
- diagrama do MCP e do fluxo end-to-end
- GIF ou vídeo curto mostrando busca externa + comparação + checklist + registro de gap
- corpus de demo curado para negócio
- documentação da arquitetura e das limitações do MCP

### O que preciso saber defender em entrevista
- por que MCP entra depois de evals e observabilidade
- por que comecei com uma vertical forte em vez de muitas integrações ao mesmo tempo
- como garanti grounding, trilha auditável e revisão humana
- por que esse MCP resolve problema real em compliance/auditoria/operações sem depender de stack paga

---

## Fase 10 — Engenharia profissional

### Objetivo
Transformar o projeto em algo tecnicamente defendível.

### Checklist
- [x] Criar testes unitários das partes críticas
- [x] Criar testes smoke da aplicação
- [x] Criar testes dos fluxos de RAG
- [x] Criar testes dos schemas estruturados
- [x] Criar testes do roteador de intenção
- [x] Criar testes dos grafos LangGraph e das transições críticas de estado
- [x] Criar testes dos caminhos de retry, fallback e revisão humana nos workflows LangGraph
- [x] Adicionar `Dockerfile`
- [x] Criar GitHub Actions para checks/testes
- [x] Padronizar tratamento de falhas
- [x] Criar arquivo central de configuração
- [x] Padronizar logs
- [x] Revisar estrutura do código para clareza e manutenção
- [x] Medir gargalos de performance de retrieval e geração

### Entregável
- [x] Repositório com padrão profissional de engenharia

### Evidência para GitHub/LinkedIn
- [x] badge de CI no README
- [ ] screenshot ou trecho do pipeline rodando
- [x] documento curto de decisões arquiteturais

### O que preciso saber defender em entrevista
- o que mudaria para produção
- como garantir mais confiabilidade e manutenibilidade
- como eu trataria configuração, falhas e evolução do sistema

---


## Fase 10.25 — Split oficial entre AI Lab e produto: Streamlit -> Gradio -> App Web

### Objetivo
Evoluir a interface do projeto separando formalmente:

- **Streamlit** como **AI Lab dashboard**
- **Gradio** como superfície de **produto**
- **app/web** como evolução posterior mais próxima de produto real antes do deploy na Oracle

### Decisão adicional já tomada nesta trilha

Dentro desta fase, a leitura oficial da interface passa a ser:

- o **produto principal** será apresentado como **Decision workflows grounded em documentos**
- a superfície de **produto** ficará no **Gradio**
- a superfície de **AI Lab** ficará no **Streamlit**
- o Streamlit atual deve ser **adaptado primeiro** para assumir o papel de dashboard de engenharia, antes de abrir um novo app Streamlit separado
- os quatro subworkflows principais do produto passam a ser:
  1. **Document Review**
  2. **Policy / Contract Comparison**
  3. **Action Plan / Evidence Review**
  4. **Candidate Review**
- `cv_analysis` deixa de ser surface de produto e passa a ser entendido como **engine interna** do workflow **Candidate Review**
- **Executive Deck Generation** passa a ser capability transversal desses workflows, e não workflow concorrente

Documento de referência desta decisão:

- `docs/PHASE_10_25_PRODUCT_SPLIT_GRADIO_AI_LAB.md`

Dentro da evolução para backend HTTP + app web, a direção adotada passa a incluir explicitamente uma capability de **Executive Deck Generation** usando o `ppt_creator_app` como serviço/renderizador especializado.

Leitura arquitetural decidida:

- o **AI Workbench Local** continua como fonte da verdade de benchmark, eval, EvidenceOps e outputs estruturados
- o **`ppt_creator_app`** entra como camada especializada de **renderização executiva** (`JSON estruturado -> deck .pptx`)
- a capability deve ser entendida como um subproduto recorrente do ecossistema, e não como export isolado
- as famílias de decks prioritárias passam a ser:
  1. **summary / executive review decks**
  2. **document review decks**
  3. **comparison / decision decks**
  4. **action-plan decks**
  5. **candidate review decks**
  6. **evidence / audit decks**
- o primeiro slice priorizado dessa capability continua sendo:
  - **benchmark/eval -> executive review deck**
- a ordem recomendada dessa trilha passa a ser:
  1. capability map e catálogo oficial de deck types
  2. contrato intermediário versionado para o primeiro deck
  3. adapter local no AI Workbench
  4. chamada HTTP para o serviço de decks
  5. UX mínima no app atual
  6. só depois Docker/porta/volume como caminho operacional padrão

Documentação inicial desta decisão:

- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`
- `docs/PRESENTATION_EXPORT_BENCHMARK_EVAL_CONTRACT_V1.md`
- `docs/PHASE_10_25_PRESENTATION_EXPORT_PRODUCTIZATION.md`
- `docs/EXECUTIVE_DECK_GENERATION_DOCUMENTATION_PLAN.md`
- `docs/EXECUTIVE_DECK_GENERATION_CONTRACT_CATALOG.md`
- `docs/EXECUTIVE_DECK_GENERATION_SERVICE_ARCHITECTURE.md`
- `docs/EXECUTIVE_DECK_GENERATION_API_CONTRACT.md`
- `docs/EXECUTIVE_DECK_GENERATION_ARTIFACT_LIFECYCLE.md`
- `docs/EXECUTIVE_DECK_GENERATION_UX_SPEC.md`
- `docs/EXECUTIVE_DECK_GENERATION_TEST_STRATEGY.md`
- `docs/EXECUTIVE_DECK_GENERATION_QUALITY_AND_GOVERNANCE.md`

### Roadmap específico da capability

Prioridade recomendada do catálogo:

#### P1 — fechar agora

1. **Benchmark & Eval Executive Review Deck**

#### P2 — subir em seguida

2. **Document Review Deck**
3. **Policy / Contract Comparison Deck**

#### P3 — expansão do subproduto

4. **Action Plan Deck**
5. **Candidate Review Deck**
6. **Evidence Pack / Audit Deck**

### Tese desta fase
Esta fase existe para provar maturidade de produto e de arquitetura de interface.
A ideia não é migrar cedo demais, e sim mostrar uma progressão defendível:

- **Streamlit** para velocidade de iteração
- **Gradio** para demo AI-first mais clara
- **app/website real** para uma camada de produto mais sólida antes do deploy público

### Como ficará o Streamlit adaptado

O Streamlit atual deve ser reorganizado para virar o **AI Lab dashboard**, com uma navegação orientada a engenharia.

Estrutura recomendada:

1. **Lab Overview**
2. **Benchmarks & Model Comparison**
3. **Evals & Diagnosis**
4. **Runtime & Observability**
5. **Document Agent & Workflow Inspector**
6. **EvidenceOps / MCP / Ops Console**
7. **Structured / Advanced Experiments**

Regra prática:

- o Streamlit deixa de ser a homepage do produto
- ele vira a superfície oficial de benchmark, evals, observabilidade, tracing e operações avançadas

### Como ficará o Gradio de produto

O Gradio deve nascer como a superfície principal de **Decision workflows grounded em documentos**.

Shell comum recomendado:

1. home com os 4 workflows
2. seleção do workflow
3. entrada documental
4. preview grounded
5. findings / recommendation
6. ações finais (`download`, `export`, `deck`, `handoff`)

Workflows principais:

1. **Document Review**
2. **Policy / Contract Comparison**
3. **Action Plan / Evidence Review**
4. **Candidate Review**

Regra prática:

- `cv_analysis` continua interno
- o produto expõe **Candidate Review**
- `Executive Deck Generation` entra como capability transversal, não como workflow separado

### Mapa inicial de migração

Vai para o **Streamlit / AI Lab**:

- model comparison
- benchmark/evals
- diagnosis
- runtime economics
- workflow traces
- MCP / EvidenceOps console
- superfícies avançadas e experimentais

Vai para o **Gradio / produto**:

- Document Review
- Policy / Contract Comparison
- Action Plan / Evidence Review
- Candidate Review
- artefatos finais e deck generation do produto

### Quando executar
Executar apenas quando:

- a Fase 10 já estiver concluída ou suficientemente madura
- os fluxos principais do produto já estiverem estáveis
- structured outputs, benchmark, evals e observabilidade já estiverem defensáveis

### Checklist
- [ ] Classificar a UI atual entre **Business Workflows / produto** e **AI Lab**
- [ ] Adaptar o Streamlit atual para ele assumir explicitamente o papel de **AI Lab dashboard**
- [ ] Definir a navegação oficial do Streamlit adaptado (`Lab Overview`, `Benchmarks`, `Evals`, `Runtime`, `Workflow Inspector`, `MCP`, `Advanced`)
- [ ] Definir um decision gate para decidir se a adaptação do Streamlit atual basta ou se um novo app Streamlit do lab será necessário
- [ ] Garantir que a lógica de negócio esteja desacoplada da UI Streamlit atual
- [ ] Formalizar o produto principal como **Decision workflows grounded em documentos**
- [ ] Identificar os 4 subworkflows principais que precisam existir na interface intermediária
- [ ] Promover `cv_analysis` a engine interna de `Candidate Review`
- [ ] Definir o shell comum do Gradio (`workflow selector`, `grounded preview`, `findings`, `artifacts`)
- [ ] Formalizar o catálogo oficial de deck types da capability `Executive Deck Generation`
- [ ] Fechar o P1 `Benchmark & Eval Executive Review Deck`
- [ ] Planejar o P2 `Document Review Deck`
- [ ] Planejar o P2 `Policy / Contract Comparison Deck`
- [ ] Planejar o P2 `Action Plan / Evidence Review`
- [ ] Planejar o P2 `Candidate Review`
- [ ] Criar uma primeira UI em Gradio para os 4 workflows principais do produto
- [ ] Comparar Streamlit vs Gradio em velocidade de iteração, clareza da demo e aderência ao caso de uso
- [ ] Documentar por que Gradio entrou e o que melhorou
- [ ] Extrair backend HTTP claro para suportar frontend desacoplado
- [ ] Definir contratos explícitos entre frontend e backend
- [ ] Integrar a capability `Executive Deck Generation` ao backend do produto via contratos intermediários versionados
- [ ] Implementar `presentation_export_service` chamando o `ppt_creator_app` por HTTP
- [ ] Externalizar configuração da integração (`PRESENTATION_EXPORT_BASE_URL`, timeout e estratégia de artefatos)
- [ ] Criar frontend web mais próximo de produto real
- [ ] Desacoplar estado de sessão, autenticação futura e chamadas de inferência da UI original
- [ ] Expor na UI catálogo explícito de geração de decks executivos, começando por benchmark/eval e depois document review/comparison
- [ ] Preparar o sistema para deploy com separação clara entre frontend, backend e bridge de inferência local

### Entregável
- dashboard **AI Lab** funcional em Streamlit
- versão Gradio funcional para demo AI-first
- versão Gradio com os 4 workflows principais do produto
- versão web mais próxima de produto real preparada para deploy
- Executive Deck Generation preparada como capability recorrente do produto via backend HTTP
- documentação da evolução da interface

### Evidência para GitHub/LinkedIn
- screenshot do dashboard do AI Lab
- screenshot comparando Streamlit e Gradio
- vídeo curto mostrando a evolução da UI
- screenshot do app/web final antes do deploy
- screenshot/GIF mostrando geração de decks executivos recorrentes a partir de benchmark/eval e fluxos documentais
- diagrama da evolução da arquitetura de interface

### O que preciso saber defender em entrevista
- por que separei produto e AI Lab em superfícies diferentes
- por que adaptei primeiro o Streamlit atual como dashboard de engenharia
- por que comecei com Streamlit
- por que Gradio fez sentido como etapa intermediária
- por que um app/web real foi necessário antes do deploy público
- como mantive a lógica de negócio desacoplada da camada de interface
- por que o produto foi organizado em 4 workflows grounded em documentos
- por que `Candidate Review` entra no produto enquanto `cv_analysis` continua como engine interna
- por que tratei Executive Deck Generation como capability do produto, e não como export isolado
- por que mantive o `ppt_creator_app` como serviço especializado de artefatos em vez de misturar essa lógica ao core do runtime de IA

---

## Fase 10.5 — Deploy híbrido demonstrável (Oracle + Cloudflare Tunnel + Ollama local)

### Objetivo
Criar uma implantação pública opcional, tecnicamente defensável e boa para demo, mantendo o app hospedado na Oracle e a inferência dos modelos locais no próprio computador via Ollama.

### Tese desta fase
Esta fase não existe para transformar o projeto em produção real 24/7.
Ela existe para provar capacidade de arquitetura de sistema, deploy, segurança básica de borda e integração entre runtime local e app público.

### Quando executar
Executar apenas quando o app já estiver estável do ponto de vista de produto, engenharia e avaliação.

A ordem recomendada é:
- Fase 9 concluída ou suficientemente madura
- Fase 10 concluída ou quase concluída
- principais fluxos do app já demonstráveis
- evidências de benchmark/evals já prontas

### Arquitetura-alvo
Fluxo desejado:

```text
Usuário
  ↓
Frontend (Oracle)
  ↓
Backend/API (Oracle)
  ↓ HTTPS
Cloudflare Tunnel
  ↓
Bridge local no Mac
  ↓
Ollama API (localhost:11434)
```

### Por que essa fase fortalece o projeto
- adiciona uma história forte de deploy e arquitetura híbrida
- cria link público demonstrável sem abandonar o runtime local-first
- mostra preocupação com segurança, isolamento e desacoplamento
- prepara uma demo mais convincente para entrevistas e portfólio

### Checklist
- [ ] Definir a arquitetura oficial de deploy híbrido em `docs/DEPLOYMENT_ARCHITECTURE.md`
- [ ] Criar backend preparado para chamar um `OLLAMA_BRIDGE_URL` externo
- [ ] Isolar a chamada a modelo atrás de interface/configuração explícita
- [ ] Adicionar variáveis de ambiente para bridge remoto e segredos associados
- [ ] Implementar bridge local intermediário para o Ollama
- [ ] Proteger o bridge com autenticação por chave e allowlist de modelos
- [ ] Adicionar timeout, validação de payload, limite de tamanho e logs básicos no bridge
- [ ] Preparar execução local do bridge com FastAPI ou equivalente
- [ ] Configurar Cloudflare Tunnel para publicar apenas o bridge local
- [ ] Garantir que o Ollama permaneça acessível apenas localmente
- [ ] Subir frontend e backend do app em VM Oracle Always Free
- [ ] Garantir que o deploy Oracle use a UI evoluída (Gradio ou app web final), e não apenas a interface de prototipagem original
- [ ] Colocar Nginx ou Caddy na frente do app público
- [ ] Configurar domínio e HTTPS para a aplicação principal
- [ ] Criar endpoint simples de healthcheck fim a fim para testar Oracle → bridge → Ollama
- [ ] Documentar ordem oficial de testes: local, bridge, tunnel, backend Oracle e UI completa
- [ ] Documentar claramente a diferença entre UI de desenvolvimento, UI de demo e UI de deploy público
- [ ] Automatizar restart mínimo dos serviços críticos no reboot
- [ ] Registrar limitações explícitas da arquitetura: dependência do notebook, latência e baixa concorrência

### Variáveis/configurações que passam a importar
- [ ] `OLLAMA_BRIDGE_URL`
- [ ] `OLLAMA_BRIDGE_API_KEY`
- [ ] `OLLAMA_BRIDGE_ALLOWED_MODELS`
- [ ] `APP_BASE_URL`
- [ ] `PUBLIC_DEMO_MODE`

### Entregável
- deploy híbrido opcional funcionando com link público de demonstração
- documentação de arquitetura e operação
- checklist reproduzível de implantação

### Evidência para GitHub/LinkedIn
- screenshot da aplicação pública no domínio
- diagrama da arquitetura Oracle + Tunnel + Mac + Ollama
- pequeno vídeo mostrando uma pergunta percorrendo o fluxo fim a fim
- write-up explicando por que essa solução é boa para demo, mas não é produção de alta disponibilidade

### O que preciso saber defender em entrevista
- por que separar app público de inferência local
- por que usar bridge intermediário em vez de expor o Ollama cru
- trade-offs entre custo, latência, disponibilidade e simplicidade
- por que essa arquitetura é boa para demo técnica e MVP, mas limitada para multiusuário e 24/7
- como eu evoluiria isso depois para uma arquitetura mais próxima de produção

---

## Fase 11 — Pacote final de portfólio

### Objetivo
Maximizar impacto em GitHub, LinkedIn, currículo e entrevista.

### Checklist
- [ ] Escrever `README.md` forte
- [ ] Adicionar screenshots da aplicação já na interface web/deploy público, e não só da UI local de prototipagem
- [ ] Mostrar a evolução da interface (Streamlit -> Gradio -> app/web final)
- [ ] Criar GIF ou vídeo curto da aplicação já no fluxo web/deploy público
- [ ] Criar diagrama de arquitetura
- [ ] Documentar features principais
- [ ] Documentar casos de uso
- [ ] Documentar benchmarks
- [ ] Documentar limitações conhecidas
- [ ] Documentar próximos passos
- [ ] Escrever instruções de instalação
- [ ] Escrever narrativa curta pronta para README/LinkedIn baseada na aplicação web e no deploy demonstrável
- [ ] Criar release `v1.0.0`

### Arquivos de documentação recomendados
- [ ] `README.md`
- [ ] `docs/ARCHITECTURE.md`
- [ ] `docs/DECISIONS.md`
- [ ] `docs/EVALS.md`
- [ ] `docs/BENCHMARKS.md`
- [ ] `docs/LIMITATIONS.md`
- [ ] `docs/DEMO_SCRIPT.md`

### Entregável
- Projeto pronto para divulgação e defesa profissional

### Evidência para GitHub/LinkedIn
- post com demo
- comparação visual entre Streamlit, Gradio e app/web final
- repositório com documentação forte
- release publicada

### O que preciso saber defender em entrevista
- o valor do projeto como produto
- decisões técnicas principais
- limitações e próximos passos realistas

---

## 9. Resumo executivo final

### Em uma frase

Este projeto deve evoluir de um chat local com LLM para uma **plataforma de IA aplicada com base documental, outputs estruturados, workflows controlados, agente empresarial orientado a valor real de negócio e trilha experimental madura para comparação/adaptação de modelos quando isso for justificado por evidência**.

### Ordem recomendada daqui para frente

1. **Fase 6 — Tools e agentes orientados a valor de negócio**
2. **Fase 7 — Benchmark e comparação entre modelos**
3. **Fase 8 — Evals**
4. **Fase 8.5 — Adaptação de modelos com Hugging Face, quantização e fine-tuning leve**
5. **Fase 9 — Observabilidade**
6. **Fase 9.25 — AI runtime economics, usage observability e budget-aware routing**
7. **Fase 9.5 — MCPs e integrações operacionais empresariais**
8. **Fase 10 — Engenharia profissional**
9. **Fase 10.25 — Split oficial entre AI Lab e produto: Streamlit -> Gradio -> App Web**
10. **Fase 10.5 — Deploy híbrido demonstrável (Oracle + Cloudflare Tunnel + Ollama local)**
11. **Fase 11 — Pacote final de portfólio**

### Métrica de sucesso do roadmap

O roadmap está bom se, ao final, eu conseguir dizer com honestidade:

> Construí uma aplicação de IA que começou com fundamentos locais, evoluiu para RAG real com base documental, passou a produzir saídas estruturadas, foi instrumentada com benchmarking/evals/observabilidade e depois ganhou uma camada explícita de cost/usage observability com budget-aware routing. Só então conectei o produto a integrações empresariais via MCP com grounding e trilha auditável. Também evoluí a interface de prototipagem para demo AI-first e depois para uma camada web mais próxima de produto antes do deploy público.


### Atualização local recente
- [x] Robustecer `cv_analysis` com campos explícitos para `languages`, `education_entries` e `experience_entries`
- [x] Implementar fallback OCR opcional para PDFs com texto insuficiente
- [x] Validar smoke eval da Fase 5 com PASS em `extraction`, `summary`, `checklist`, `cv_analysis` e `code_analysis`
- [x] Validar benchmark sintético multilayout com PASS nos layouts textuais
- [x] Validar benchmark completo pós-OCR com melhoria parcial em casos scan-like
- [x] Integrar e endurecer o pipeline `evidence_cv` com OCR-first, VL-on-demand, shadow rollout e readiness para rollout controlado
- [x] Ajustar o grounding do structured analysis para CV único usar contexto completo do documento e reduzir placeholders
- [x] Canonicalizar o output final de educação do `cv_analysis` com datas, localizações e wording forte da USP
- [x] Melhorar o pós-processamento de `summary` para reduzir casos de tópico único gigante
- [x] Reestruturar summaries colapsados via LLM, evitando categorias fixas hardcoded como solução final
- [x] Recalibrar `reading_time_minutes` para refletir o esforço de leitura do summary, não do documento inteiro
- [x] Recalibrar `completeness_score` para ficar menos otimista em documentos longos
- [x] Refinar prompts e pós-processamento de `summary` para reduzir títulos genéricos e melhorar a legibilidade executiva
- [x] Adicionar barra de progresso e status textual durante a indexação de documentos no app
- [x] Implementar resolução automática de `context_window` para structured outputs conforme task, estratégia e tamanho do documento
- [x] Expor na UI da aba estruturada o `context_window` resolvido, o cap aplicado e a estimativa de chars do documento
- [x] Criar modo `auto` vs `manual` para `context_window` na sidebar do app
- [x] Corrigir o modo `auto` para não ficar preso ao default baixo de `OLLAMA_CONTEXT_WINDOW=8192`
- [x] Definir caps automáticos por provider para o `context_window` (incluindo Ollama)
- [x] Estender a lógica de `context_window` automático também para o fluxo de chat com RAG
- [x] Expor no chat o `context_window` efetivo/resolvido para dar transparência operacional ao usuário
- [x] Tornar o checklist interativo com persistência local em sessão e botão de reset
- [x] Fazer polish da UI e do pós-processamento de `code_analysis`, com categorias estáveis (`input_mutation`, `shared_reference`, `type_validation`) e recomendações coerentes
- [x] Implementar auto-recovery estruturado com `repair_json`, `retry_generation` e telemetria de parse recovery
- [x] Encerrar tecnicamente a Fase 5 como pacote unificado (`structured outputs` + `evidence_cv`) e mover o pacote visual final para a Fase 11, após app web + deploy
- [x] Adicionar comparação shadow `direct` vs `langgraph_context_retry` com log local, relatório agregado e sinais visuais na UI estruturada
- [x] Adicionar testes focados para roteamento, guardrails, retry, fallback e revisão humana do workflow LangGraph
- [x] Estender o workflow LangGraph para a task `document_agent`, com classificação de intenção, seleção de tool, retry com `retrieval` e marcação explícita de revisão humana
- [x] Adicionar renderer friendly do `Document Operations Copilot`, incluindo fontes, tool runs, findings de comparação e sinalização de `needs_review`
- [x] Expor metadados do agente documental no runtime snapshot/sidebar para auditoria operacional durante a execução
- [x] Adicionar ao payload do agente limitações conhecidas, guardrails aplicados e próximos passos recomendados para melhorar a explicabilidade operacional
- [x] Formalizar catálogo reutilizável das tools do agente documental, com disponibilidade por contexto e exposição explícita das tools avaliadas na UI/runtime
- [x] Persistir log local do `Document Operations Copilot`, com agregação de métricas por intenção/tool/revisão humana e relatório reaproveitável
- [x] Aprofundar o `Document Operations Copilot` com uma trilha explícita de revisão de policy/compliance, cobrindo cláusulas, obrigações, restrições, riscos e lacunas de revisão
- [x] Iniciar a Fase 7 com comparação lado a lado entre modelos/providers no app, incluindo métricas de latência, tamanho de saída, aderência ao formato, ranking consolidado e relatório local com leaderboards agregados
- [x] Consolidar a Fase 7 localmente com recorte explícito local/cloud/experimental, benchmarks agregados por retrieval/embedding/prompt profile e visão unificada de estratégia para retrieval shadow e direct vs LangGraph
- [x] Encerrar a Fase 7 tecnicamente/localmente com documentação dedicada do benchmark, posicionamento explícito de runtime e reporte reaproveitável para portfólio/entrevista
- [x] Aprofundar o `Document Operations Copilot` com fluxos explícitos de análise de riscos, extração operacional e assistência técnica sobre documentos
- [x] Iniciar a Fase 8 com store local em SQLite para evals, persistência do smoke eval/checklist regression e script de relatório agregado
- [x] Expandir a fundação da Fase 8 com integração do `evidence_cv_gold_eval`, filtros no relatório e documentação dedicada da camada de evals
- [x] Adicionar backfill histórico da Fase 8 para importar relatórios legados JSON no store SQLite sem duplicação
- [x] Adicionar camada diagnóstica da Fase 8 para transformar histórico de evals em prioridades de iteração e sinalização de adaptação
- [x] Completar a Fase 8 no escopo técnico/local com suites para roteamento/guardrails, cobertura explícita dos critérios de avaliação e decisão documentada sobre DeepEval
- [x] Adicionar workflow live separado da Fase 8 para evals dependentes de ambiente preparado
- [x] Adicionar runner consolidado com `preflight`, `--index-missing` e execução em lote de evals reais
- [x] Indexar os documentos faltantes do manifesto real e sincronizar o backend Chroma sem divergência com o store canônico
- [x] Corrigir a regressão do `checklist_regression` (falso positivo em `collapsed_items`) e voltar o suite para `PASS`
- [x] Melhorar a recuperação de `name`/`location` na trilha `evidence_cv` e elevar o recall do mini gold set para 1.0 nesses campos
- [x] Rerodar o ciclo live completo da Fase 8 com geração de nova evidência persistida no SQLite
- [x] Adicionar histórico agregado local de execuções do app (chat + structured), com parâmetros de RAG, erros, latências e visualização resumida na sidebar