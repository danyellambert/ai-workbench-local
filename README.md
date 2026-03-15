# AI Workbench Local

Plataforma de IA aplicada para experimentar **LLMs locais**, conversar com documentos, comparar estratégias de ingestão e retrieval, avaliar respostas e evoluir um pipeline de **RAG robusto, explicável e orientado a portfólio**.

---

## Objetivo

Este projeto está sendo evoluído para se tornar um ativo forte de portfólio, demonstrando aplicação prática de IA com foco em:

- chat com modelos locais
- RAG com documentos
- extração robusta de PDFs
- outputs estruturados
- benchmarking, avaliação e observabilidade
- experimentação controlada de arquitetura

---

## Casos de uso principais

1. **Chat com documentos (RAG)**
2. **Assistente de código**
3. **Extração estruturada de informação**
4. **Benchmark de estratégias de parsing e retrieval**

---

## Stack principal

- Python
- Streamlit
- Ollama
- OpenAI-compatible API
- LangChain
- LangGraph
- Chroma
- SQLite
- Pydantic
- PyPDF
- Docling
- Matplotlib

---

## Arquivos principais neste momento

- `main_qwen.py` → app principal local com Ollama
- `main.py` → versão configurável para provider compatível com OpenAI
- `proximos_passos.md` → roadmap oficial do projeto
- `scripts/run_all_phase_4_5_benchmarks.py` → orquestrador completo dos 4 benchmarks da Fase 4.5
- `scripts/run_phase_4_5_benchmark_suite.py` → suíte de embeddings, embedding context window e retrieval tuning
- `scripts/run_pdf_extraction_benchmark_en.py` → benchmark automatizado dos modos de extração de PDF
- `scripts/render_phase_4_5_charts.py` → renderização reprodutível dos gráficos da Fase 4.5
- `docs/PHASE_4_5_BENCHMARK_RESULTS.md` → resultados completos com tabelas, gráficos e decisões
- `docs/PHASE_4_5_VALIDATION.md` → fechamento técnico e operacional da Fase 4.5
- `docs/BENCHMARK_PDF_EXTRACTION_en.md` → benchmark detalhado de extração de PDF

---

## Estrutura atual do projeto

```text
src/
  config.py
  prompt_profiles.py
  providers/
  rag/
  services/
  storage/
  ui/

scripts/
  run_all_phase_4_5_benchmarks.py
  run_phase_4_5_benchmark_suite.py
  run_pdf_extraction_benchmark.py
  run_pdf_extraction_benchmark_en.py
  run_embedding_benchmark.py
  render_phase_4_5_charts.py
  compare_phase_4_5_configs.py
  validate_phase_4_5.py

docs/
  BENCHMARK_PDF_EXTRACTION_en.md
  PHASE_3_NOTES.md
  PHASE_4_NOTES.md
  PHASE_4_5_BENCHMARK_RESULTS.md
  PHASE_4_5_VALIDATION.md
  PUBLICATION_GUIDE.md
  assets/
    phase_4_5/
  data/
    phase_4_5_benchmark_data.json
```

---

## Como rodar localmente

### 1. Instale as dependências

```bash
pip install -r requirements.txt
```

### 2. Revise o arquivo `.env`

Se precisar recriar do zero:

```bash
cp .env.example .env
```

### 3. Garanta que o Ollama esteja disponível

Exemplo de modelos locais:

- geração: `qwen2.5:7b`
- embeddings: modelo configurado no `.env`

### 4. Execute a versão local

```bash
streamlit run main_qwen.py
```

### 5. Execute a versão OpenAI-compatible (opcional)

Preencha `OPENAI_API_KEY` no `.env` e rode:

```bash
streamlit run main.py
```

---

## Modos de extração de PDF

O projeto possui **3 modos explícitos de extração**, selecionáveis na interface e benchmarkados na Fase 4.5.

### 1. Básico

Usa somente `pypdf`.

Melhor para:
- PDFs textuais simples
- ingestão rápida
- comparação de baseline

### 2. Híbrido inteligente

Usa `pypdf` como baseline e aplica enriquecimento seletivo em páginas suspeitas com Docling/OCR.

Melhor para:
- apostilas
- papers com figuras e tabelas
- documentos mistos

### 3. Completo por página

Modo de cobertura máxima.

Melhor para:
- scans
- manuais antigos
- PDFs image-heavy
- testes de recall máximo

---

## Fase 4.5 concluída

A Fase 4.5 foi encerrada com **quatro trilhas de benchmark** executadas no mesmo corpus local de quatro PDFs, incluindo **revisão humana** para o benchmark de extração.

### Corpus e métricas usados

Corpus fixo da suíte:

- `2025-HB-44-20250106-Final-508.pdf`
- `kaur-2016-ijca-911367.pdf`
- `Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf`
- `c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf`

Métricas usadas:

- **PDF extraction:** `manual_score` (0–2), tempo de extração e tempo de indexação
- **retrieval benchmarks:** `Hit@1`, `Hit@K`, `MRR`, `avg_retrieval_seconds`, `indexing_seconds`

### Configuração recomendada após a Fase 4.5

```env
OLLAMA_EMBEDDING_MODEL=embeddinggemma:300m
OLLAMA_EMBEDDING_CONTEXT_WINDOW=512
RAG_CHUNK_SIZE=1200
RAG_CHUNK_OVERLAP=80
RAG_TOP_K=4
RAG_RERANK_POOL_SIZE=8
RAG_PDF_EXTRACTION_MODE=hybrid
```

### Benchmark highlights

#### 1) PDF extraction: quality vs extraction cost

![PDF extraction quality vs cost](docs/assets/phase_4_5/02_pdf_extraction_aggregate_quality_vs_cost.png)

`complete` obteve a melhor qualidade média agregada (**1.1094**), mas exigiu **1485.38 s** de extração média, contra **22.0248 s** de `hybrid`. A diferença de qualidade foi pequena demais para justificar esse custo como default.

#### 2) Embedding models: quality vs retrieval latency

![Embedding models quality vs latency](docs/assets/phase_4_5/09_embedding_models_quality_vs_latency.png)

`embeddinggemma:300m` atingiu **MRR = 1.0** e ficou no melhor ponto de trade-off entre qualidade e latência entre os modelos perfeitos.

#### 3) Embedding context window: practical optimum

![Embedding context retrieval vs window](docs/assets/phase_4_5/13_embedding_ctx_retrieval_vs_window.png)

No trilho vencedor, `embeddinggemma:300m + 512` entregou **MRR = 1.0** com a menor latência média (**0.6932 s**). O benchmark mostrou que contexto maior não foi automaticamente melhor.

#### 4) Retrieval tuning: winner vs baseline

![Retrieval tuning quality vs latency](docs/assets/phase_4_5/17_retrieval_tuning_quality_vs_latency.png)

`lower_overlap` manteve **MRR = 1.0** e melhorou latência e indexação em relação ao baseline. Isso justificou a troca de `chunk_overlap=200` para `80` como default.

#### 5) Executive summary

![Phase 4.5 winner matrix](docs/assets/phase_4_5/21_phase_4_5_winner_matrix.png)

A decisão final foi feita por **trade-off entre qualidade, custo e robustez**, não por score bruto isolado.

### Como regenerar os gráficos da Fase 4.5

```bash
python scripts/render_phase_4_5_charts.py
```

Os dados-base versionados usados na renderização estão em:

```text
docs/data/phase_4_5_benchmark_data.json
```

Para a análise completa, veja:
- `docs/PHASE_4_5_BENCHMARK_RESULTS.md`
- `docs/PHASE_4_5_VALIDATION.md`
- `docs/BENCHMARK_PDF_EXTRACTION_en.md`

---

## Próximo passo estratégico

Com a Fase 4.5 encerrada, o roadmap oficial segue para:

1. **Fase 5 — Outputs estruturados**
2. **Fase 5.5 — Evolução com LangChain e LangGraph**
3. **Fase 6 — Tools e agentes orientados a valor de negócio**

---

## Valor de portfólio

Este projeto não foi fechado como “um chatbot com RAG”. A Fase 4.5 consolidou o repositório como um artefato de portfólio de **AI Engineer**, mostrando:

- benchmark de ingestão com validação humana
- benchmark de representação vetorial
- benchmark de tuning de contexto de embedding
- benchmark de retrieval tuning
- defaults finais escolhidos por evidência
- assets visuais e script reprodutível de benchmark

Isso aumenta a auditabilidade do projeto e facilita defender as decisões técnicas em entrevista.
