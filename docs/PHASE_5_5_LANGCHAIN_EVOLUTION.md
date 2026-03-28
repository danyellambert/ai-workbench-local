# Fase 5.5 — Evolução com LangChain e LangGraph

## Objetivo deste slice

Este documento registra o primeiro passo concreto da Fase 5.5: introduzir componentes do ecossistema LangChain sem abandonar o pipeline manual que já sustenta o produto.

A decisão arquitetural foi manter o pipeline manual como **baseline operacional** e abrir caminhos experimentais, selecionáveis e auditáveis, para comparação controlada.

## O que já foi implementado

### 1. Loaders experimentais via LangChain

Foi adicionada a configuração:

- `RAG_LOADER_STRATEGY=manual|langchain_basic`

Comportamento atual:

- `manual`: mantém os loaders locais atuais do projeto
- `langchain_basic`: usa loaders básicos do ecossistema LangChain para `TXT`, `MD`, `PY` e `CSV` quando `langchain-community` estiver disponível
- `PDF`: continua deliberadamente no pipeline customizado do projeto, porque já existe uma trilha mais forte com extração híbrida, OCR, `evidence_cv` e fallback controlado
- fallback automático para `manual` quando a dependência opcional não estiver instalada, quando o tipo de arquivo não for suportado pelo caminho experimental ou quando o arquivo precisar permanecer no pipeline customizado

Além disso, o índice passa a registrar:

- estratégia de loader pedida
- estratégia de loader efetivamente usada
- motivo de fallback, quando houver

### 2. Chunking experimental via LangChain

Foi adicionada a configuração:

- `RAG_CHUNKING_STRATEGY=manual|langchain_recursive`

Comportamento atual:

- `manual`: mantém o chunking local original do projeto
- `langchain_recursive`: usa `RecursiveCharacterTextSplitter` quando `langchain-text-splitters` estiver disponível
- fallback automático para `manual` quando a dependência não estiver instalada ou a estratégia pedida não puder ser usada

Além disso, o índice passa a registrar:

- estratégia pedida
- estratégia efetivamente usada
- motivo de fallback, quando houver

### 3. Retrieval experimental via LangChain + Chroma

Foi adicionada a configuração:

- `RAG_RETRIEVAL_STRATEGY=manual_hybrid|langchain_chroma`

Comportamento atual:

- `manual_hybrid`: continua usando o retrieval vetorial atual + reranking lexical híbrido
- `langchain_chroma`: usa um adaptador experimental com `langchain-chroma` sobre a mesma persistência local do Chroma
- fallback automático para `manual_hybrid` quando a dependência não estiver instalada, quando o caminho experimental falhar ou quando não retornar resultado útil

### 4. Comparação shadow entre caminhos manual e LangChain

Quando o debug de retrieval está habilitado no chat, o app agora executa também uma **comparação shadow** com a estratégia alternativa.

Isso permite observar, para a mesma pergunta:

- estratégia primária usada
- estratégia alternativa usada
- backend efetivo
- motivo de fallback
- sobreposição entre chunks recuperados
- igualdade ou divergência entre top-1 e top-3

Essa comparação foi feita para tornar a evolução manual → framework explícita e auditável, sem trocar o pipeline principal cedo demais.

### 5. Histórico agregado das comparações

As comparações shadow agora também podem ser persistidas em um log local:

- `.phase55_langchain_shadow_log.json`

Esse histórico agrega rodadas de comparação e permite acompanhar, ao longo do uso:

- taxa de concordância no top-1
- taxa de concordância no top-3
- overlap médio entre os conjuntos recuperados
- frequência de fallback da estratégia experimental

Isso ajuda a transformar a comparação manual vs LangChain em evidência acumulada, e não apenas em inspeção pontual por pergunta.

### 6. Primeiro workflow experimental via LangGraph

Foi adicionado um caminho experimental para a aba de saídas estruturadas:

- `direct`
- `langgraph_context_retry`

Comportamento atual:

- `direct`: mantém a execução estruturada atual
- `langgraph_context_retry`: usa um workflow com estados e transições explícitas para:
  - preparar a request
  - rotear explicitamente a estratégia inicial de contexto
  - executar a task estruturada
  - avaliar sucesso/fracasso e qualidade mínima do resultado
  - aplicar guardrails leves de `needs_review`
  - tentar novamente com `context_strategy=retrieval` quando a primeira tentativa falha ou vem com qualidade muito baixa sob `document_scan`
- fallback automático para `direct` quando `langgraph` não estiver instalado ou quando o workflow experimental falhar

Além disso, a execução passa a registrar:

- estratégia pedida
- estratégia efetivamente usada
- motivo de fallback, quando houver
- decisão de roteamento inicial
- decisão de guardrail
- número de tentativas
- trilha resumida dos nós/etapas percorridos no workflow
- marcação de `needs_review` quando o fluxo entende que a saída ainda exige revisão humana

### 7. Comparação shadow entre execução direta e workflow LangGraph

Além do shadow comparison já existente no retrieval, a aba de saídas estruturadas agora também pode executar uma comparação local entre:

- `direct`
- `langgraph_context_retry`

Isso permite observar, para a mesma task estruturada:

- se os dois caminhos chegaram ao mesmo sucesso/fracasso
- diferença de latência entre execução direta e workflow LangGraph
- diferença de `quality_score`
- se o caminho alternativo evitou ou introduziu `needs_review`
- estratégia efetivamente usada, fallback e guardrails aplicados

Essa comparação também pode ser persistida em um log local dedicado:

- `.phase55_langgraph_shadow_log.json`

E existe um relatório agregado para transformar essas execuções em evidência reaproveitável:

```bash
python /Users/danyellambert/Downloads/Aula\ 4\ -\ Criacao\ de\ Chatbot\ com\ IA\ em\ Tempo\ Real/scripts/report_phase55_langgraph_shadow_log.py
```

### 8. Separação explícita entre provider de geração e provider de embeddings

Foi dado mais um passo na abstração de provider do projeto:

- a geração continua podendo usar um provider principal
- o pipeline de embeddings passa a ter um **provider configurável e resolvido separadamente**

Configuração atual:

- `RAG_EMBEDDING_PROVIDER=ollama|openai`

Comportamento atual:

- o app deixa de assumir Ollama como provider fixo de embeddings em todos os pontos internos
- a resolução do provider de embeddings agora usa capability explícita (`supports_embeddings`) com fallback seguro
- a compatibilidade do índice passa a considerar também **qual provider gerou os embeddings**, e não só o nome do modelo
- o runtime passa a expor melhor a distinção entre:
  - provider de geração
  - provider de embeddings

Isso fortalece a evolução da arquitetura sem ainda acoplar o projeto a uma explosão de runtimes novos cedo demais.

### 9. Camada de reranking extraída do serviço principal

Outro micro-slice entregue foi a separação explícita da lógica de reranking híbrido para um módulo dedicado:

- `src/rag/reranking.py`

Com isso, o `src/rag/service.py` deixa de concentrar ao mesmo tempo:

- recuperação vetorial
- fallback de backend
- compatibilidade do índice
- heurísticas de reranking lexical/híbrido

Benefícios práticos desta separação:

- deixa mais clara a fronteira entre **retrieval bruto** e **reranking**
- reduz o acoplamento da camada principal de serviço
- facilita futuros testes e experimentos offline de ranking
- prepara o terreno para comparar melhor heurísticas locais vs componentes externos de reranking

### 10. Caminho opcional para runtime local via ecossistema Hugging Face

O projeto agora também prepara um caminho experimental adicional para geração local fora do runtime principal do Ollama:

- `huggingface_local`

Objetivo deste slice:

- reduzir acoplamento do app ao runtime principal
- abrir espaço para testar modelos locais via Transformers sem trocar o baseline oficial cedo demais
- manter essa trilha **opcional** e controlada

Configuração atual:

- `HUGGINGFACE_MODEL`
- `HUGGINGFACE_AVAILABLE_MODELS`
- `HUGGINGFACE_CONTEXT_WINDOW`
- `HUGGINGFACE_GENERATION_TASK`
- `HUGGINGFACE_MAX_NEW_TOKENS`

Leitura arquitetural:

- `ollama` continua como baseline operacional principal
- `openai` continua como provider cloud opcional
- `huggingface_local` entra como trilha experimental de runtime local alternativo

O provider só vira opção de chat quando a dependência necessária estiver disponível no ambiente, preservando segurança operacional da UI.

### 11. Resolução de provider estruturado com capability explícita e telemetria de fallback

Também foi endurecida a camada de tasks estruturadas para não assumir que o `request.provider` sempre existe no registry final do ambiente.

Agora:

- a resolução do provider para tasks estruturadas também usa capability explícita (`chat`)
- existe fallback seguro para `ollama` quando o provider pedido não estiver disponível
- a telemetria passa a registrar:
  - `provider_requested`
  - `provider_effective`
  - `provider_fallback_reason`

Isso melhora a auditabilidade e reduz o risco de divergência entre configuração desejada e runtime realmente disponível.

### 12. Contexto estruturado e retrieval alinhados às configurações efetivas da sessão

Outro ajuste importante foi alinhar `document_context` às configurações efetivas de RAG/embedding da sessão do app, em vez de depender apenas do `.env` carregado no boot.

Na prática:

- o app agora registra `effective_rag_settings` no estado da sessão
- `document_context` passa a preferir essas configurações runtime quando monta retrieval/contexto estruturado
- isso reduz o risco de a UI mostrar um embedding/configuração e o pipeline interno consultar outra configuração herdada do ambiente

Esse slice fortalece a separação entre:

- configuração estática de ambiente
- configuração operacional efetiva da sessão atual

### 13. Seleção explícita do provider de embedding na UI

Para tornar a separação entre geração e embeddings realmente visível no produto, a sidebar agora também expõe:

- provider de embedding
- modelo de embedding correspondente

Com isso, o usuário consegue testar combinações como:

- geração via `ollama` + embeddings via `ollama`
- geração via `openai` + embeddings via `ollama`
- geração via `ollama` + embeddings via `huggingface_local` (quando disponível)

Esse ajuste fecha melhor o ciclo entre:

- configuração de UI
- `effective_rag_settings`
- retrieval/contexto estruturado
- compatibilidade do índice

### 14. Camada estruturada com provider/context window efetivos, não só defaults do Ollama

Outro hardening importante foi reduzir resíduos de acoplamento ao runtime padrão dentro de `StructuredOutputService`.

Agora a camada estruturada também:

- resolve provider efetivo antes de escolher defaults operacionais
- usa `default_model` e `default_context_window` do provider efetivamente disponível
- registra em metadata a diferença entre:
  - `provider_requested`
  - `provider_effective`
  - `provider_fallback_reason`
- aplica a lógica de cap de contexto considerando o provider efetivo, inclusive no fallback

Isso deixa a execução estruturada mais coerente com a arquitetura multi-provider da Fase 5.5.

### 15. Helper compartilhado para resolução de runtime multi-provider

Para reduzir duplicação entre app principal, `document_context` e camada estruturada, a resolução de runtime agora também foi consolidada em helpers reutilizáveis do `registry`.

Em especial:

- `filter_registry_by_capability(...)`
- `resolve_provider_runtime_profile(...)`

Isso simplifica pontos que antes repetiam manualmente:

- filtragem de providers por capability
- fallback para provider disponível
- leitura de label/model/context window efetivos
- exposição uniforme de `requested_provider`, `effective_provider` e `fallback_reason`

O ganho principal aqui é arquitetural: menos lógica duplicada e menos risco de divergência silenciosa entre camadas.

### 16. Snapshot operacional extraído da UI principal

Outro passo para reduzir acoplamento foi tirar da UI principal a responsabilidade por consolidar o snapshot operacional do app.

Agora existe um serviço dedicado para isso:

- `src/services/runtime_snapshot.py`

Ele centraliza:

- resumo da rota ativa de provider
- distinção entre dependência local e dependência remota
- fotografia operacional do chat com RAG
- fotografia operacional das tasks estruturadas
- fotografia do estado documental, OCR e VL

Isso melhora a legibilidade do `main_qwen.py` e reforça a separação entre:

- montagem de estado operacional
- renderização da sidebar
- fluxo principal da UI

### 17. Avaliação explícita de chains auxiliares do LangChain para structured outputs

Também foi feita uma avaliação arquitetural explícita sobre usar chains auxiliares do LangChain nas tasks estruturadas.

Decisão atual:

- **não promover chains auxiliares do LangChain para o caminho principal agora**

Motivo:

- o projeto já tem envelope, parser, recovery, pós-processamento e renderização próprios em `src/structured/`
- neste momento, isso oferece mais clareza operacional e mais controle do que introduzir uma abstração adicional sem ganho funcional claro

Ou seja: o item foi avaliado e a decisão foi **deferir a adoção**, não por limitação técnica, mas por critério arquitetural.

## Conclusão prática da Fase 5.5

A Fase 5.5 pode ser considerada **concluída tecnicamente/localmente**.

Critérios que sustentam esse fechamento:

- pipeline manual continua funcionando como baseline
- caminhos LangChain entram como trilhas experimentais auditáveis
- LangGraph já participa da execução estruturada com fallback, retry e guardrails
- provider/runtime multi-provider ficou mais coerente e menos acoplado
- a UI já expõe comparações suficientes para justificar a narrativa da fase em portfólio e entrevista

Com isso, o próximo passo natural deixa de ser “evoluir framework” e passa a ser **usar essa base para construir o agente documental da Fase 6**.

## Como usar

Na sidebar do app:

1. escolha a estratégia de loader
2. escolha a estratégia de chunking
3. escolha a estratégia de retrieval
4. na aba estruturada, escolha a estratégia de execução (`direct` ou `langgraph_context_retry`)
5. indexe ou reindexe documentos quando mudar o loader ou o chunking
6. habilite `Mostrar debug de retrieval` para ver a comparação shadow
7. se quiser comparar `direct` vs `langgraph_context_retry`, habilite a comparação shadow na aba estruturada
8. gere os relatórios agregados com:

```bash
python /Users/danyellambert/Downloads/Aula\ 4\ -\ Criacao\ de\ Chatbot\ com\ IA\ em\ Tempo\ Real/scripts/report_phase55_langchain_shadow_log.py

python /Users/danyellambert/Downloads/Aula\ 4\ -\ Criacao\ de\ Chatbot\ com\ IA\ em\ Tempo\ Real/scripts/report_phase55_langgraph_shadow_log.py
```

## Dependências adicionadas

- `langchain-community`
- `langchain-text-splitters`
- `langchain-chroma`
- `langgraph`

## Por que isso fortalece a Fase 5.5

Este slice já demonstra três pontos importantes:

1. o projeto continua provando que a base manual existe e funciona
2. loaders, splitters e retrievers do ecossistema já entram de forma seletiva, onde fazem sentido
3. a evolução para framework acontece por comparação controlada, e não por substituição cega
4. a arquitetura começa a separar melhor baseline operacional de trilhas experimentais
5. a fase já mostra um primeiro passo concreto em workflow orientado por estado, com routing, guardrails e retry controlado, sem migrar o app inteiro para LangGraph cedo demais

## Comparação inicial: manual vs LangChain

| Dimensão | Pipeline manual atual | Caminhos experimentais LangChain | Leitura atual |
|---|---|---|---|
| Clareza operacional | Mais explícito e previsível no código principal | Mais conciso nos pontos integrados ao ecossistema | Manual ainda é melhor para explicar o fluxo base em entrevista |
| Produtividade | Exige mais código próprio para cada evolução | Acelera experimentos de splitter e retriever | LangChain já reduz esforço para testar alternativas |
| Extensibilidade | Alta, mas com custo maior de manutenção manual | Alta para integrar componentes do ecossistema | Híbrido faz mais sentido do que migração total imediata |
| Risco de acoplamento | Menor | Maior se virar dependência cedo demais | Por isso os caminhos LangChain seguem opcionais e auditáveis |
| Valor atual para o portfólio | Prova domínio dos fundamentos | Prova maturidade de stack e critério de adoção | A combinação das duas histórias é a leitura mais forte |

### Conclusão provisória

Neste momento, o melhor posicionamento do projeto é:

- **manual como baseline oficial**
- **LangChain como trilha experimental comparável**

Isso permite defender, com honestidade técnica, que a evolução para framework está acontecendo por evidência e controle arquitetural, e não por modismo.

## O que ainda falta nesta fase

Os próximos passos naturais continuam sendo:

- ampliar a comparação manual vs LangChain para mais partes do RAG
- decidir se algum loader/retriever do ecossistema merece promoção para o caminho principal
- ampliar o uso de LangGraph para um fluxo mais próximo do futuro agente documental
- avançar da separação inicial entre geração e embeddings para uma separação mais clara também de reranking e experimentação offline
- transformar a separação inicial de reranking em uma trilha mais explícita de experimentação offline e comparação de estratégias
- expandir o provider `huggingface_local` com mais capacidades locais quando houver ganho real e sem enfraquecer o baseline do app
- avaliar chains auxiliares do LangChain para structured outputs quando houver ganho real
- consolidar melhor a leitura comparativa entre `direct` e `langgraph_context_retry` por task, documento e tipo de falha
- documentar explicitamente trade-offs de clareza, produtividade e extensibilidade