# Fase 5 — Evals, benchmark sintético e estado atual

Este documento registra o que já foi feito na Fase 5 **além do que estava inicialmente documentado no projeto**, com foco em evals, benchmark sintético e implicações arquiteturais.

## 1. O que foi consolidado na Fase 5

Ao longo da implementação da Fase 5, o projeto passou de uma foundation de structured outputs para uma trilha mais completa com:

- foundation técnica em `src/structured/`
- UI base para análises estruturadas
- separação explícita entre:
  - **chat com RAG**
  - **análise estruturada**
- smoke eval automatizado local
- benchmark sintético inicial para `cv_analysis`
- geradores de CVs sintéticos com múltiplos layouts para teste

## 2. Smoke eval automatizado da Fase 5

Foi implementado um smoke eval local para a Fase 5 com:

- `scripts/run_phase5_structured_eval.py`

Esse smoke eval consolidado passou em:

- `extraction`
- `summary`
- `checklist`
- `cv_analysis`
- `code_analysis`

### Interpretação

Isso confirmou que a camada estruturada do projeto está funcional em nível de:
- schema
- parsing
- validação
- execução básica por task

Mas esse smoke eval **não substitui** validação com documentos reais ou benchmarks mais ricos de layout.

## 3. Separação entre chat com RAG e análise estruturada

Foi consolidada uma separação arquitetural importante:

- **Chat com RAG** como fluxo conversacional
- **Documento estruturado** como fluxo orientado a tarefa e schema

A base documental continua compartilhada, mas:
- prompting
- assembly de contexto
- execução
- renderização

foram tratados como pipelines distintos.

### Por que isso importa

Essa separação reduz confusão entre:
- respostas conversacionais abertas
- artefatos estruturados previsíveis

e melhora a narrativa técnica do projeto.

## 4. Benchmark sintético de CVs

Também foi criada uma trilha de benchmark sintético para `cv_analysis` com:

- gerador de CVs sintéticos realistas
- gerador de CVs multi-layout
- benchmark automático de pares PDF/JSON

### Layouts sintéticos usados

Os layouts usados no benchmark incluíram:

- `classic_one_column`
- `modern_two_column`
- `compact_sidebar`
- `dense_executive`
- `scan_like_image_pdf`

### O que o benchmark revelou

O benchmark mostrou que:

- layouts textuais ficaram majoritariamente em `WARN`
- layouts `scan_like_image_pdf` falharam sem OCR
- o gargalo de `cv_analysis` não está principalmente no nome/email/localização/skills
- o gargalo está concentrado em:
  - `languages`
  - `education`
  - `experience_titles`

## 5. Leitura correta do benchmark sintético

O benchmark não indicou que a Fase 5 está “quebrada”.

Ele indicou que:

- a base estruturada funciona
- o `cv_analysis` já extrai bem campos centrais como:
  - `full_name`
  - `email`
  - `location`
  - `skills`
- mas ainda precisa de refinamento para:
  - `languages`
  - `education`
  - `experience_titles`

### Sobre `scan_like_image_pdf`

Os casos `scan_like_image_pdf` devem ser tratados como:

- **OCR-needed**
- não como falha inesperada do pipeline textual atual

Isso é importante para a narrativa final da fase e para não interpretar erroneamente o benchmark.

## 6. O que ainda falta para fechar a fase

Mesmo com a foundation, UI, smoke eval e benchmark sintético já implementados, a Fase 5 ainda não deve ser considerada encerrada.

Os próximos passos corretos são:

1. **polish de UI/UX** da aba de análise estruturada
2. validação com documentos reais
3. refinamento do `cv_analysis` com foco em:
   - `languages`
   - `education`
   - `experience_titles`
4. registro de evidências fortes:
   - screenshots
   - exemplos comparativos
   - mini demo

## 7. Como defender isso em entrevista

Hoje a história técnica mais forte da Fase 5 é:

- o projeto saiu de chat livre para structured outputs
- as saídas passaram a ser validadas e renderizadas
- foi criada uma separação clara entre conversa com RAG e análise estruturada
- a fase já tem smoke eval automatizado
- a fase já tem benchmark sintético inicial que revela gargalos reais
- os próximos refinamentos são guiados por evidência, não por tentativa e erro

## 8. Arquivos e artefatos relevantes

### Estruturados / foundation
- `src/structured/`
- `src/ui/structured_outputs.py`
- `main_qwen.py`

### Evals
- `scripts/run_phase5_structured_eval.py`
- `phase5_eval/reports/`

### Benchmark sintético de CV
- `scripts/run_synthetic_resume_benchmark.py`
- `data/synthetic/resumes_multilayout/`
- `phase5_eval/resume_benchmark*/`

### Geradores sintéticos
- gerador de resumes com PDF
- gerador multi-layout
- benchmark auxiliar com pares PDF/JSON

## 9. Conclusão

A Fase 5 já está em um estado tecnicamente sólido para:
- demonstração local
- iteração guiada por benchmark
- evolução para uma apresentação mais profissional

Mas ela ainda precisa de:
- polish de UX
- validação com documentos reais
- fechamento narrativo e visual

antes de ser tratada como “encerrada” no projeto.
