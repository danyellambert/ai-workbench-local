# Roadmap Definitivo — AI Workbench Local

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

### Camada opcional free-tier

Usar apenas como extensão opcional, sem depender disso para o projeto funcionar:

- **Gemini** ou **Groq**, se houver camada gratuita disponível
- **Hugging Face Inference**, se fizer sentido em testes, reranking ou benchmarking
- **Langfuse** self-hosted ou free-tier, se compensar

### Regra de arquitetura

O sistema deve continuar funcionando **mesmo se todas as integrações cloud forem removidas**.

### Regra de evolução técnica

A evolução do projeto deve provar **duas coisas ao mesmo tempo**:

1. eu entendo o pipeline manual por baixo
2. eu sei migrar esse pipeline para ferramentas de mercado quando isso faz sentido

Ou seja:

- não virar refém de framework
- não reinventar tudo sem necessidade

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

### Fase atual em andamento

- **Fase 5 — Outputs estruturados (foundation técnica concluída; UI, renderização e casos reais ainda pendentes)**

### Fase concluída mais recentemente

- **Fase 4.5 — concluída com benchmark, avaliação humana e configuração final recomendada**

### Marco mais recente já iniciado na Fase 5

- **Foundation de outputs estruturados criada em `src/structured/` e compilando corretamente**

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

### Risco técnico importante já identificado

A UI de contexto foi implementada, mas a aplicação do `num_ctx` pelo caminho **OpenAI-compatible** do Ollama ainda não deve ser tratada como 100% validada.

Ou seja:

- a UI muda
- o código tenta enviar o valor
- mas isso ainda precisa de validação técnica mais forte
- `ollama ps` não deve ser tratado sozinho como prova final de que a janela customizada foi aplicada corretamente

### Próximo passo estratégico recomendado

A ordem mais forte continua sendo:

1. **Fase 5 — Outputs estruturados**
2. **Fase 5.5 — Evolução com LangChain e LangGraph**
3. **Fase 6 — Tools e agentes orientados a valor de negócio**
4. **Fase 7+ — Benchmark, evals, observabilidade e engenharia profissional**

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
- [ ] Comparar também modelos cloud opcionais quando fizer sentido

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
- [ ] LangChain como reimplementação explícita em fase posterior
- [ ] Chroma ou FAISS como store vetorial mais robusta na Fase 4.5

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
Mostrar que IA também pode ser usada como componente integrável de sistema.

### Estado real da fase hoje

A Fase 5 **já foi iniciada de forma estrutural**, mas **ainda não está concluída como feature de produto**.

O projeto já possui uma foundation técnica dedicada para outputs estruturados em `src/structured/`, incluindo:

- schemas base e schemas por tarefa
- envelope de execução/resultado
- parser/sanitizer/validator
- validação com Pydantic
- registry de tarefas com metadados de renderização
- service layer dedicada
- stubs para `extraction`, `summary`, `checklist` e `cv_analysis`
- documentação da foundation em `docs/PHASE_5_STRUCTURED_OUTPUT_FOUNDATION.md`

O que **ainda não existe de forma fechada** nesta fase:

- integração visível no app (`main_qwen.py`)
- renderer em `src/ui/` para `json` / `friendly` / `checklist`
- modo de código/refatoração completo
- casos reais documentados e demonstráveis
- fluxo estruturado final operando ponta a ponta na UI

### Checklist da foundation da Fase 5
- [x] Criar módulo dedicado `src/structured/`
- [x] Criar envelope de execução/resultado para outputs estruturados
- [x] Criar parser/sanitizer/validator com falha controlada
- [x] Validar saídas com Pydantic
- [x] Gerar respostas em JSON no backend estruturado
- [x] Definir schemas previsíveis por tarefa
- [x] Registrar metadados de render mode por tarefa
- [x] Documentar decisões da foundation da Fase 5
- [x] Garantir compilação da foundation no projeto atual

### Checklist funcional restante da Fase 5
- [ ] Integrar seleção de modo estruturado na UI
- [ ] Integrar renderização `json` no app
- [ ] Integrar renderização `friendly` no app
- [ ] Integrar renderização `checklist` no app
- [ ] Fechar modo extrator de informações na UI
- [ ] Fechar modo resumidor em tópicos na UI
- [ ] Fechar modo analisador de currículo na UI
- [ ] Fechar modo gerador de checklist na UI
- [ ] Criar modo explicador/refatorador de código
- [ ] Reusar o pipeline RAG atual nos modos que exigem contexto documental
- [ ] Documentar padrões de uso por tipo de saída no nível de produto
- [ ] Criar casos reais de extração estruturada a partir de documentos
- [ ] Criar mini demo reprodutível da Fase 5

### Entregável
- Módulo de análises com saída estruturada e validada, integrado à UI e com pelo menos 3 modos demonstráveis

### Evidência para GitHub/LinkedIn
- exemplos antes/depois de saída livre vs. estruturada
- screenshot ou tabela com JSON validado
- mini demo mostrando transformação de documento em checklist/JSON
- screenshot do app com seletor de modo estruturado

### O que preciso saber defender em entrevista
- por que structured output é importante
- como reduzir respostas inconsistentes
- onde Pydantic ajuda confiabilidade
- por que isso prepara o terreno para automação e agentes
- por que a foundation foi separada da UI antes da integração final

---

## Fase 5.5 — Evolução com LangChain e LangGraph

### Objetivo
Mostrar explicitamente a evolução do projeto dos fundamentos manuais para ferramentas amplamente usadas no mercado.

### Por que essa fase existe?

Porque o projeto já prova que eu entendo o pipeline manual.
Agora ele precisa provar também que eu sei usar o ecossistema profissional sem depender cegamente dele.

### Checklist
- [ ] Reimplementar partes-chave do RAG usando LangChain
- [ ] Comparar pipeline manual vs LangChain em clareza, produtividade e extensibilidade
- [ ] Usar loaders/splitters/retrievers do LangChain quando fizer sentido
- [ ] Integrar vector store via LangChain
- [ ] Criar primeiro workflow com LangGraph
- [ ] Modelar estados e transições de um fluxo real
- [ ] Documentar como e por que a arquitetura evoluiu
- [ ] Deixar a comparação explícita para entrevista e portfólio

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
- [ ] **Agente de análise documental**: lê documentos, resume, extrai pontos-chave e identifica riscos
- [ ] **Agente de policy/compliance**: responde com base em documentos e aponta violações ou conflitos
- [ ] **Agente de extração operacional**: transforma documentos em dados estruturados, checklists e tarefas
- [ ] **Agente assistente técnico**: combina RAG + modo programador + outputs estruturados

### Checklist
- [ ] Criar tool para consultar documentos indexados
- [ ] Criar tool para resumir arquivo/documento
- [ ] Criar tool para extração estruturada
- [ ] Criar tool para comparação entre documentos
- [ ] Criar tool para gerar checklist operacional
- [ ] Criar workflow com LangGraph para orquestração do agente
- [ ] Implementar roteador de intenção
- [ ] Registrar logs de decisão do agente
- [ ] Explicar limitações e guardrails
- [ ] Exibir fontes, metadados e necessidade de revisão humana

### O que eu não devo fazer nesta fase
- [ ] evitar multiagente por moda sem necessidade
- [ ] evitar agente “navega tudo sem controle” só para parecer sofisticado
- [ ] evitar demo confusa com muitas tools soltas e pouco valor real

### Entregável
- Agente local com ferramentas reais e workflow definido, orientado a um caso empresarial plausível

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
- [ ] Criar tela de comparação entre modelos
- [ ] Enviar o mesmo prompt para múltiplos modelos
- [ ] Exibir respostas lado a lado
- [ ] Medir latência
- [ ] Medir tamanho da saída
- [ ] Avaliar aderência ao formato
- [ ] Salvar resultados de benchmark
- [ ] Comparar local vs cloud opcional
- [ ] Comparar embeddings e estratégias de retrieval

### Métricas recomendadas
- [ ] Tempo de resposta
- [ ] Tamanho da resposta
- [ ] Aderência ao schema
- [ ] Relevância
- [ ] Groundedness no caso de RAG
- [ ] Precisão de extração estruturada
- [ ] Qualidade percebida por caso de uso

### Entregável
- Módulo de benchmarking com evidência comparativa

### Evidência para GitHub/LinkedIn
- tabela ou gráfico comparando modelos
- documento com principais conclusões do benchmark
- comparação entre embeddings / retrievals / contexto

### O que preciso saber defender em entrevista
- como escolhi o melhor modelo para cada caso
- quais métricas usei e por quê
- por que benchmark sem contexto de uso pode ser enganoso

---

## Fase 8 — Evals

### Objetivo
Criar uma camada de qualidade e repetibilidade.

### Checklist
- [ ] Montar conjunto de testes para documentos
- [ ] Montar conjunto de testes para tarefas de código
- [ ] Montar conjunto de testes para extração estruturada
- [ ] Montar conjunto de testes para resumo
- [ ] Montar conjunto de testes para comparação documental
- [ ] Avaliar formato correto
- [ ] Avaliar relevância
- [ ] Avaliar consistência
- [ ] Avaliar cobertura da resposta
- [ ] Avaliar groundedness em RAG
- [ ] Avaliar precisão de citações/fontes
- [ ] Avaliar acurácia do roteamento de intenção
- [ ] Avaliar tempo de resposta
- [ ] Salvar resultados em SQLite
- [ ] Considerar integração com DeepEval depois da base própria pronta

### Entregável
- Módulo de avaliação contínua e reproduzível

### Evidência para GitHub/LinkedIn
- tabela com casos de teste
- screenshot do painel de resultados de avaliação
- documento mostrando antes/depois de melhorias guiadas por evals

### O que preciso saber defender em entrevista
- como validar qualidade de IA em um time real
- diferença entre avaliar manualmente e medir com critérios repetíveis
- por que evals precisam estar ligados a casos de uso reais

---

## Fase 9 — Observabilidade

### Objetivo
Monitorar o comportamento do sistema de IA.

### Checklist
- [ ] Registrar provider/modelo usado
- [ ] Registrar prompt profile
- [ ] Registrar `context_window`
- [ ] Registrar embedding model usado
- [ ] Registrar parâmetros de RAG
- [ ] Registrar arquivos consultados
- [ ] Registrar chunks recuperados
- [ ] Registrar tool usada
- [ ] Registrar tempo de retrieval
- [ ] Registrar tempo de geração
- [ ] Registrar resultado da avaliação
- [ ] Registrar erros
- [ ] Criar dashboard local com métricas
- [ ] Criar visualização de histórico de execuções

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

## Fase 10 — Engenharia profissional

### Objetivo
Transformar o projeto em algo tecnicamente defendível.

### Checklist
- [ ] Criar testes unitários das partes críticas
- [ ] Criar testes smoke da aplicação
- [ ] Criar testes dos fluxos de RAG
- [ ] Criar testes dos schemas estruturados
- [ ] Criar testes do roteador de intenção
- [ ] Adicionar `Dockerfile`
- [ ] Criar GitHub Actions para checks/testes
- [ ] Padronizar tratamento de falhas
- [ ] Criar arquivo central de configuração
- [ ] Padronizar logs
- [ ] Revisar estrutura do código para clareza e manutenção
- [ ] Medir gargalos de performance de retrieval e geração

### Entregável
- Repositório com padrão profissional de engenharia

### Evidência para GitHub/LinkedIn
- badge de CI no README
- screenshot ou trecho do pipeline rodando
- documento curto de decisões arquiteturais

### O que preciso saber defender em entrevista
- o que mudaria para produção
- como garantir mais confiabilidade e manutenibilidade
- como eu trataria configuração, falhas e evolução do sistema

---

## Fase 11 — Pacote final de portfólio

### Objetivo
Maximizar impacto em GitHub, LinkedIn, currículo e entrevista.

### Checklist
- [ ] Escrever `README.md` forte
- [ ] Adicionar screenshots
- [ ] Criar GIF ou vídeo curto de demonstração
- [ ] Criar diagrama de arquitetura
- [ ] Documentar features principais
- [ ] Documentar casos de uso
- [ ] Documentar benchmarks
- [ ] Documentar limitações conhecidas
- [ ] Documentar próximos passos
- [ ] Escrever instruções de instalação
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
- repositório com documentação forte
- release publicada

### O que preciso saber defender em entrevista
- o valor do projeto como produto
- decisões técnicas principais
- limitações e próximos passos realistas

---

## 9. Resumo executivo final

### Em uma frase

Este projeto deve evoluir de um chat local com LLM para uma **plataforma de IA aplicada com base documental, outputs estruturados, workflows controlados e agente empresarial orientado a valor real de negócio**.

### Ordem recomendada daqui para frente

1. **Fechar a integração da Fase 5 no app (UI + renderer + 3 modos demonstráveis)**
2. **Fase 5.5 — LangChain e LangGraph**
3. **Fase 6 — Tools e agentes orientados a valor de negócio**
4. **Fase 7+ — Benchmark, evals, observabilidade e engenharia profissional**
5. **Fase 11 — Pacote final de portfólio**

### Métrica de sucesso do roadmap

O roadmap está bom se, ao final, eu conseguir dizer com honestidade:

> Construí uma aplicação de IA que começou com fundamentos locais, evoluiu para RAG real com base documental, passou a produzir saídas estruturadas, foi instrumentada com benchmarking/evals/observabilidade e culminou em um agente documental com utilidade empresarial concreta.
