# Fase 5.5 — Evolução com LangChain e LangGraph

## Objetivo deste slice

Este documento registra o primeiro passo concreto da Fase 5.5: introduzir componentes do ecossistema LangChain sem abandonar o pipeline manual que já sustenta o produto.

A decisão arquitetural foi manter o pipeline manual como **baseline operacional** e abrir caminhos experimentais, selecionáveis e auditáveis, para comparação controlada.

## O que já foi implementado

### 1. Chunking experimental via LangChain

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

### 2. Retrieval experimental via LangChain + Chroma

Foi adicionada a configuração:

- `RAG_RETRIEVAL_STRATEGY=manual_hybrid|langchain_chroma`

Comportamento atual:

- `manual_hybrid`: continua usando o retrieval vetorial atual + reranking lexical híbrido
- `langchain_chroma`: usa um adaptador experimental com `langchain-chroma` sobre a mesma persistência local do Chroma
- fallback automático para `manual_hybrid` quando a dependência não estiver instalada, quando o caminho experimental falhar ou quando não retornar resultado útil

### 3. Comparação shadow entre caminhos manual e LangChain

Quando o debug de retrieval está habilitado no chat, o app agora executa também uma **comparação shadow** com a estratégia alternativa.

Isso permite observar, para a mesma pergunta:

- estratégia primária usada
- estratégia alternativa usada
- backend efetivo
- motivo de fallback
- sobreposição entre chunks recuperados
- igualdade ou divergência entre top-1 e top-3

Essa comparação foi feita para tornar a evolução manual → framework explícita e auditável, sem trocar o pipeline principal cedo demais.

### 4. Histórico agregado das comparações

As comparações shadow agora também podem ser persistidas em um log local:

- `.phase55_langchain_shadow_log.json`

Esse histórico agrega rodadas de comparação e permite acompanhar, ao longo do uso:

- taxa de concordância no top-1
- taxa de concordância no top-3
- overlap médio entre os conjuntos recuperados
- frequência de fallback da estratégia experimental

Isso ajuda a transformar a comparação manual vs LangChain em evidência acumulada, e não apenas em inspeção pontual por pergunta.

## Como usar

Na sidebar do app:

1. escolha a estratégia de chunking
2. escolha a estratégia de retrieval
3. indexe ou reindexe documentos quando mudar o chunking
4. habilite `Mostrar debug de retrieval` para ver a comparação shadow
5. gere um relatório agregado com:

```bash
python /Users/danyellambert/Downloads/Aula\ 4\ -\ Criacao\ de\ Chatbot\ com\ IA\ em\ Tempo\ Real/scripts/report_phase55_langchain_shadow_log.py
```

## Dependências adicionadas

- `langchain-text-splitters`
- `langchain-chroma`

## Por que isso fortalece a Fase 5.5

Este slice já demonstra três pontos importantes:

1. o projeto continua provando que a base manual existe e funciona
2. a evolução para framework acontece por comparação controlada, e não por substituição cega
3. a arquitetura começa a separar melhor baseline operacional de trilhas experimentais

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
- introduzir um primeiro workflow real com LangGraph
- reforçar abstrações para geração, embeddings, reranking e experimentação offline
- documentar explicitamente trade-offs de clareza, produtividade e extensibilidade