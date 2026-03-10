# Fase 4 — Chat com documentos (RAG)

## Objetivo da fase

Permitir que o chatbot responda usando conteúdo de arquivos enviados pelo usuário, com recuperação de contexto relevante e exibição das fontes utilizadas.

## O que foi implementado

- upload de documentos suportando:
  - PDF
  - TXT
  - CSV
  - MD
  - PY
- extração de texto por tipo de arquivo
- chunking local com controle de tamanho e overlap
- geração de embeddings locais
- armazenamento do índice RAG em arquivo local (`.rag_store.json`)
- recuperação por similaridade com vetor local
- injeção do contexto recuperado no prompt do modelo
- exibição de fontes utilizadas na resposta

## Componentes introduzidos

- `src/rag/loaders.py`
- `src/rag/chunking.py`
- `src/rag/vector_store.py`
- `src/rag/prompting.py`
- `src/rag/service.py`
- `src/storage/rag_store.py`
- `src/services/rag_state.py`

## Estratégia adotada

- embeddings locais via provider Ollama
- vector store local simples em JSON
- retrieval baseado em similaridade cosseno
- contexto recuperado inserido no prompt antes da geração da resposta

## Benefícios dessa abordagem

- zero custo adicional
- controle local do índice e do documento
- base compatível com evolução futura para vetores/DBs mais sofisticados

## Próxima fase

**Fase 5 — Outputs estruturados**