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

## Decisão de embeddings para português

Para este projeto, foi considerada explicitamente a configuração:

```env
OLLAMA_EMBEDDING_MODEL=bge-m3
```

quando o foco for português.

### Por que isso faz sentido?

O `bge-m3` é uma opção muito coerente para cenários multilíngues e tende a melhorar a recuperação semântica quando:

- os documentos estão em português
- as perguntas do usuário também estão em português
- existe variação de vocabulário entre pergunta e trecho original

### O que isso melhora na prática?

- recuperação mais semântica e menos literal
- melhor alinhamento entre a pergunta e os trechos recuperados
- melhor potencial de qualidade no RAG para conteúdo em português

### O que isso NÃO muda?

Essa escolha não muda a arquitetura do pipeline. Ela melhora a qualidade da etapa de embeddings dentro da arquitetura já existente.

Em outras palavras:

> trocar o embedding model é uma otimização da recuperação, não uma mudança estrutural do sistema.

## Benefícios dessa abordagem

- zero custo adicional
- controle local do índice e do documento
- base compatível com evolução futura para vetores/DBs mais sofisticados

## Limitações atuais da Fase 4

Esta fase foi implementada de forma propositalmente controlada e didática. Por isso, ela ainda não cobre:

- múltiplos documentos indexados ao mesmo tempo
- vector DB dedicada (Chroma/FAISS/Qdrant/etc.)
- LangChain no pipeline principal
- LangGraph em fluxos de retrieval/orquestração
- reranking mais sofisticado
- avaliação de retrieval em separado da avaliação da resposta

Esses pontos entram muito bem na nova **Fase 4.5 — RAG avançado e base documental**.

## Próxima fase

**Fase 5 — Outputs estruturados**

## Evolução estratégica sugerida

Além da Fase 5, o roadmap passa a prever explicitamente uma nova:

**Fase 4.5 — RAG avançado e base documental**

Essa fase deve cobrir:

- múltiplos arquivos indexados
- store vetorial mais robusta
- comparação entre embeddings
- aprendizado explícito de LangChain
- preparação/uso de LangGraph em fluxos de retrieval mais completos