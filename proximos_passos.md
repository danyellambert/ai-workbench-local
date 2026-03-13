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

- **`bge-m3`** como embedding model principal

Mantendo espaço para comparar depois com alternativas como:

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

- **Fase 4.5 — RAG avançado e base documental**

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
- [x] escolha explícita de `OLLAMA_EMBEDDING_MODEL=bge-m3`
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

### O que ainda não considero fechado na Fase 4.5

- [ ] comparação prática entre embeddings
- [ ] reranking mais forte do que o ranking vetorial atual
- [ ] limitação inteligente do contexto recuperado por orçamento real de prompt
- [ ] benchmark final de tuning (`RAG_CHUNK_SIZE`, `RAG_TOP_K`, quantidade de chunks enviados)

### O que já considero fechado nesta rodada final da Fase 4.5

- [x] catálogo multi-arquivo mais refinado na UI
- [x] UX melhor para remoção/reindexação seletiva
- [x] vector store mais robusta com Chroma local e fallback seguro
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

1. **Fechar a Fase 4.5**
2. **Fase 5 — Outputs estruturados**
3. **Fase 5.5 — Evolução com LangChain e LangGraph**
4. **Fase 6 — Tools e agentes orientados a valor de negócio**

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

## Fase 4.5 — RAG avançado e base documental

### Objetivo
Transformar o RAG básico em uma **base documental local mais próxima de um caso real de empresa**, com melhor engenharia de retrieval, melhor UX operacional e melhor controle de contexto.

### Por que essa fase existe?

Porque a Fase 4 prova o pipeline completo de RAG de forma controlada.
A Fase 4.5 existe para mostrar evolução real de AI Engineering, cobrindo:

- múltiplos documentos
- retrieval engineering mais forte
- comparação de embeddings
- tuning de contexto
- preparação concreta para LangChain, LangGraph e agentes futuros

### O que já foi entregue
- [x] índice preparado para múltiplos documentos
- [x] upload múltiplo
- [x] upsert documental
- [x] remoção seletiva
- [x] filtros por documento/tipo
- [x] metadados mais ricos
- [x] configuração explícita de contexto por provider
- [x] contexto visível na sidebar para Ollama
- [x] `OLLAMA_EMBEDDING_MODEL=bge-m3`
- [x] compactação e normalização do índice local
- [x] melhoria parcial de performance e warnings do Streamlit

### Checklist para considerar a Fase 4.5 fechada
- [x] Estruturar o índice como coleção documental e não só um arquivo
- [x] Permitir upload de múltiplos arquivos
- [x] Implementar `upsert_documents_in_rag_index(...)`
- [x] Implementar `remove_documents_from_rag_index(...)`
- [x] Permitir filtros por documento na recuperação
- [x] Permitir filtros por tipo de arquivo na recuperação
- [x] Enriquecer metadados por documento e por chunk
- [x] Introduzir `OLLAMA_CONTEXT_WINDOW`
- [x] Introduzir `OPENAI_CONTEXT_WINDOW`
- [x] Carregar defaults de contexto em `src/config.py`
- [x] Expor ajuste de contexto na sidebar quando provider = Ollama
- [x] Registrar `context_window` como metadado de execução
- [x] Ajustar `OLLAMA_EMBEDDING_MODEL` para `bge-m3`
- [x] Reduzir reload desnecessário do `.rag_store.json`
- [x] Compactar e normalizar o store local
- [x] Refinar catálogo visual de documentos indexados
- [x] Melhorar UX de remoção/reindexação seletiva
- [x] Mostrar claramente quantidade de documentos, chunks e tipos indexados
- [x] Introduzir store vetorial mais robusta com **Chroma** persistido e sincronizado com fallback local
- [ ] Comparar embeddings na prática (`bge-m3` vs alternativas)
- [ ] Adicionar **reranking**
- [ ] Limitar melhor o contexto documental enviado para geração
- [x] Reduzir custo do pipeline com melhor tuning de `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP` e `RAG_TOP_K`
- [x] Medir latência separadamente para retrieval e geração
- [x] Adicionar debug leve de retrieval no app
- [x] Validar tecnicamente o caminho nativo de `num_ctx` e publicar fechamento prático
- [x] Criar caminho **Ollama native** para parâmetros avançados (`num_ctx` e outros)
- [x] Documentar claramente a diferença entre caminho OpenAI-compatible e Ollama native

### Configuração e contexto

Esta fase deve consolidar dois pontos de controle explícitos para contexto:

1. **default versionado**
   - `.env.example`
   - `.env`
   - leitura centralizada em `src/config.py`

2. **ajuste visível de execução**
   - sidebar quando provider = Ollama

### Fechamento prático publicado

Nesta rodada final, o fechamento prático da Fase 4.5 passou a ficar registrado em:

- `docs/PHASE_4_5_VALIDATION.md`
- `scripts/validate_phase_4_5.py`

A ideia é separar claramente:

- o que já foi **validado tecnicamente por script**
- o que ainda depende de **rodada comparativa local** (principalmente embeddings e benchmark fino de retrieval)

### Observação técnica importante

A implementação atual trata o caminho nativo do Ollama como principal para parâmetros avançados.

### Fechamento honesto deste ponto
- [x] manter compatibilidade OpenAI-compatible como camada de interoperabilidade
- [x] criar integração nativa com o Ollama para controle fino de parâmetros avançados
- [x] usar o caminho nativo quando contexto customizado ou outros parâmetros avançados forem relevantes

Observação: isso configura **validação técnica operacional**, não prova exaustiva do runtime interno do modelo.

### Entregável
- Base documental local com múltiplos arquivos, retrieval mais forte, configuração explícita de contexto e caminho claro para evolução profissional do RAG

### Evidência para GitHub/LinkedIn
- GIF mostrando upload múltiplo + recuperação com fontes
- screenshot do catálogo de documentos indexados
- documento curto explicando a evolução de Fase 4 para Fase 4.5
- comparação entre comportamento do RAG antes e depois da base documental

### O que preciso saber defender em entrevista
- diferença entre RAG básico e base documental mais madura
- por que retrieval não termina em embeddings
- por que filtros, metadados e reranking melhoram o sistema
- como controlar custo/latência do contexto
- por que `ollama ps` não deve ser a única prova da aplicação de `num_ctx`
- por que, para parâmetros avançados, um caminho nativo do Ollama pode ser mais robusto que o OpenAI-compatible

---

## Fase 5 — Outputs estruturados

### Objetivo
Mostrar que IA também pode ser usada como componente integrável de sistema.

### Checklist
- [ ] Criar modo extrator de informações
- [ ] Criar modo resumidor em tópicos
- [ ] Criar modo analisador de currículo
- [ ] Criar modo gerador de checklist
- [ ] Criar modo explicador/refatorador de código
- [ ] Validar saídas com Pydantic
- [ ] Gerar respostas em JSON
- [ ] Gerar respostas em checklist
- [ ] Definir schemas previsíveis por tarefa
- [ ] Documentar padrões de uso por tipo de saída
- [ ] Criar casos reais de extração estruturada a partir de documentos

### Entregável
- Módulo de análises com saída estruturada e validada

### Evidência para GitHub/LinkedIn
- exemplos antes/depois de saída livre vs. estruturada
- screenshot ou tabela com JSON validado
- mini demo mostrando transformação de documento em checklist/JSON

### O que preciso saber defender em entrevista
- por que structured output é importante
- como reduzir respostas inconsistentes
- onde Pydantic ajuda confiabilidade
- por que isso prepara o terreno para automação e agentes

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

1. **Fechar Fase 4.5**
2. **Fase 5 — Outputs estruturados**
3. **Fase 5.5 — LangChain e LangGraph**
4. **Fase 6 — Tools e agentes orientados a valor de negócio**
5. **Fase 7+ — Benchmark, evals, observabilidade e engenharia profissional**

### Métrica de sucesso do roadmap

O roadmap está bom se, ao final, eu conseguir dizer com honestidade:

> Construí uma aplicação de IA que começou com fundamentos locais, evoluiu para RAG real com base documental, passou a produzir saídas estruturadas, foi instrumentada com benchmarking/evals/observabilidade e culminou em um agente documental com utilidade empresarial concreta.
