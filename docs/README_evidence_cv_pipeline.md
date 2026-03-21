# Evidence-grounded CV extraction pipeline

Pipeline paralelo ao app principal, focado em extração auditável de currículos.

## Objetivo

- priorizar rastreabilidade
- evitar alucinação
- separar evidência confirmada de candidatos visuais/ambíguos

## Como rodar

```bash
python -m src.evidence_cv.cli parse caminho/do/cv.pdf --out out.json
```

## Como o pipeline entra no app atual

Nesta etapa, o `evidence_cv` foi integrado **sem substituir globalmente** o pipeline existente.

### Ponto de entrada no produto
- `src/rag/loaders.py`
- função principal do app: `load_document(...)`

### Comportamento atual
Para uploads PDF, o fluxo agora decide entre:

1. **pipeline legado** (`src/rag/pdf_extraction.py`)
2. **pipeline novo paralelo** (`src/evidence_cv/`)

### Quando o pipeline novo pode ser usado
Ele só entra quando a feature flag estiver ativa:

- `RAG_PDF_EVIDENCE_PIPELINE_ENABLED=true`

E, além disso, quando ao menos uma das condições abaixo for verdadeira:

1. o arquivo parecer CV/resume pelo nome
   - controlado por `RAG_PDF_EVIDENCE_PIPELINE_USE_FOR_CV_LIKE`
2. o documento parecer fortemente scan-like
   - controlado por `RAG_PDF_EVIDENCE_PIPELINE_USE_FOR_STRONG_SCAN_LIKE`
   - usando o threshold `RAG_PDF_EVIDENCE_PIPELINE_MIN_SCAN_SUSPICIOUS_RATIO`

### Quando cai para fallback
O app volta para o pipeline legado quando:
- a feature flag está desligada
- o PDF não atende aos critérios acima
- ou o pipeline novo falha em runtime

Nesse caso, o metadata do documento registra:
- `evidence_pipeline_error`
- `evidence_pipeline_fallback_used=true`

### O que o restante do sistema recebe
Mesmo usando o pipeline novo, o app continua recebendo algo compatível com o fluxo atual:

- `text`: texto consolidado extraído
- `metadata.source_type`: `digital_pdf`, `scanned_pdf` ou `mixed_pdf`
- `metadata.warnings`: avisos do pipeline novo
- `metadata.evidence_summary`: resumo consumível pelo restante do produto
- `metadata.product_consumption`: política explícita de uso no produto

Ou seja, a integração foi feita como **camada de extração adaptada ao contrato existente do app**.

## Política de consumo no produto

O pipeline agora expõe uma política explícita em `metadata.product_consumption`:

- `confirmed` → pode ser usado diretamente
- `visual_candidate` → revisão necessária por padrão
- `needs_review` → revisão necessária
- `not_found` → ausente

Por padrão, o app deve consumir automaticamente apenas `confirmed`.
Os demais estados continuam acessíveis no metadata para UX futura e revisão assistida.

## Quando o VL é chamado

Nesta etapa, o backend VL é usado de forma **seletiva e controlada**, não full-page por padrão.

Ele é chamado apenas quando o runner considera que o documento é potencialmente difícil, por exemplo:
- `scanned_pdf`
- páginas com pouco texto útil
- layout que parece difícil para OCR puro

O uso inicial está restrito a regiões/casos de maior valor:
- header / top block
- contact block
- sidebar / áreas com baixa evidência textual

## Quando o VL não é chamado

Ele não deve entrar indiscriminadamente em todas as páginas.

Se o documento já parece suficientemente legível por native text + OCR, o pipeline continua priorizando evidência textual antes de recorrer ao VL.

## Como um campo passa de `visual_candidate` para `confirmed`

Regra atual da etapa inicial:

1. VL detecta um candidato visual (nome, email, telefone, localização)
2. O pipeline tenta uma verificação secundária literal sobre o texto já extraído
3. Só vira `confirmed` se houver suporte textual suficiente
4. Caso contrário, permanece `visual_candidate`

Isso preserva a regra central do projeto: **não confirmar sem evidência**.

## Hierarquia heurística atual de regiões

Nesta fase de hardening, os crops passam por uma hierarquia simples:

1. `header_top_block`
2. `contact_block`
3. `top_center`
4. `top_left`
5. `top_right`
6. `sidebar`

Essa ordem influencia o ranking dos candidatos quando há conflito entre regiões.

## Roteador OCR-first / VL-on-demand

Nesta fase, o pipeline passa a decidir de forma explícita quando chamar VL.

### Heurísticas principais do roteador
- `scanned_pdf`
- `mixed_pdf`
- `low_text_coverage`
- `missing_contacts_after_ocr`
- `header_fields_missing`

### Metadata do roteador
O resultado agora inclui `runtime_metadata.vl_router` com:
- `enabled`
- `decision`
- `reasons`
- `document_signals`
- `regions_selected`
- `skipped_because`

### Seleção seletiva por região
As regiões continuam dentro do conjunto:
- `header_top_block`
- `contact_block`
- `top_center`
- `top_left`
- `top_right`
- `sidebar`

Mas o roteador pode selecionar apenas um subconjunto, dependendo dos sinais do documento.

## Benchmark multilayout do roteador

Script:
- `scripts/benchmark_vl_router_multilayout.py`

Corpus principal:
- `data/synthetic/resumes_multilayout/pdf`

Exemplo de execução completa:

```bash
python scripts/benchmark_vl_router_multilayout.py \
  --pdf-dir data/synthetic/resumes_multilayout/pdf \
  --out phase5_eval/reports/evidence_cv_multilayout_router_benchmark.json
```

Smoke test pequeno:

```bash
python scripts/benchmark_vl_router_multilayout.py \
  --pdf-dir data/synthetic/resumes_multilayout/pdf \
  --limit 3 \
  --out phase5_eval/reports/evidence_cv_multilayout_router_benchmark_smoke.json
```

## Regras de hardening atuais

### Deduplicação
- emails repetidos em múltiplos crops são consolidados
- telefones repetidos são consolidados pela versão normalizada em dígitos

### Ranking
- candidatos com suporte textual confirmado recebem prioridade maior
- regiões mais fortes (`header_top_block`, `contact_block`) recebem mais peso
- `sidebar` continua útil, mas perde em conflito para regiões superiores

### Campos singulares
Para campos como:
- `name`
- `location`

o pipeline escolhe apenas o melhor candidato principal.

### Filtros adicionais
Foram fortalecidos filtros para:
- email válido
- telefone com faixa aceitável de dígitos
- nome sem números / sem padrão de contato
- localização sem termos óbvios de ruído

## Leitura do benchmark atual

O script `scripts/compare_pdf_extraction_paths.py` agora produz:
- comparação por arquivo
- agregado total
- comparação `without_vl` vs `with_vl`
- contagem adicional de ruído incremental (`duplicates_or_noise`)

### Principais sinais do benchmark atual
- documentos fáceis permaneceram estáveis
- documentos difíceis ganharam recall adicional
- ainda existe ruído residual em scans difíceis, especialmente em emails falsamente candidatos
- a heurística de ranking e deduplicação reduziu a explosão inicial de candidatos

### Onde houve melhoria real
- `0004_medium_scan_like_image_pdf_beatriz.barbosa.martins.pdf`
  - `name_status: confirmed`
  - `location_status: confirmed`
  - emails recuperados aumentaram de 1 para 2

### Onde ainda há ruído
- `0009_simple_scan_like_image_pdf_matheus.araujo.carvalho.pdf`
  - ganho de recall ainda vem acompanhado de candidatos visuais com revisão pendente
  - o campo continua auditável, mas ainda precisa refinamento adicional para reduzir ruído

## Critérios de aceitação mais fortes nesta fase

### Email
- precisa casar com regex completa de email
- tokens parciais ou quebrados são descartados
- duplicatas entre regiões são consolidadas

### Telefone
- precisa casar com regex de telefone plausível
- precisa ter entre 8 e 15 dígitos normalizados
- duplicatas são deduplicadas pela forma numérica

### Nome
- não pode conter dígitos
- não pode parecer contato
- precisa ter comprimento mínimo útil

### Localização
- não pode conter dígitos
- não pode parecer label de contato ou ruído estrutural
- só é promovida quando houver suporte textual suficiente

## Mini gold set de validação manual

Arquivo:
- `phase5_eval/reports/evidence_cv_mini_gold_set.json`

Esse conjunto pequeno serve para acompanhar precisão/recall aproximados de:
- `name`
- `email`
- `phone`
- `location`

Ele foi expandido para incluir exemplos de:
- documentos digitais fáceis
- scan-like médios
- scan-like difíceis
- layouts multilayout do projeto

Ele foi introduzido como benchmark pragmático de hardening antes de layout understanding mais sofisticado.

## Limitações atuais desta fase

- o runner ainda usa uma integração inicial seletiva do VL
- a verificação secundária ainda é simples
- ainda não há reconstrução avançada de layout
- ainda não há cobertura completa de todas as seções do CV

## Script de comparação entre fluxo antigo e novo

Para comparar extração antiga vs nova em PDFs reais:

```bash
python scripts/compare_pdf_extraction_paths.py \
  data/synthetic/resumes_ui_test/0009_simple_scan_like_image_pdf_matheus.araujo.carvalho.pdf \
  data/synthetic/resumes_ui_test/0002_hard_compact_sidebar_marina.gomes.ribeiro.pdf
```

Ou salvando em JSON:

```bash
python scripts/compare_pdf_extraction_paths.py \
  data/synthetic/resumes_ui_test/0009_simple_scan_like_image_pdf_matheus.araujo.carvalho.pdf \
  data/synthetic/resumes_ui_test/0002_hard_compact_sidebar_marina.gomes.ribeiro.pdf \
  --out phase5_eval/reports/evidence_vs_legacy_comparison.json
```

## Backends OCR

- `ocrmypdf`
- `docling`

## Status dos campos

- `confirmed`
- `visual_candidate`
- `needs_review`
- `not_found`

## Limitações atuais

Esta primeira versão é um MVP paralelo:
- OCR + native text + reconciliação básica
- estrutura pronta para backend VL e verificação secundária
- integração com app principal ainda não realizada

## Full CV structured extraction foundation

Esta fase adiciona a fundação para parsing estruturado do CV inteiro dentro do próprio `evidence_cv`.

### Representação intermediária
Agora o pipeline cria `evidence_blocks`, uma representação intermediária por bloco com:
- `text`
- `page`
- `bbox`
- `source_type`
- `probable_section`
- `confidence`
- `notes`

### Seções atualmente suportadas
- `header`
- `summary`
- `experience`
- `education`
- `skills`
- `languages`
- `certifications`
- `projects`
- `other`

### Extração estruturada inicial suportada
- `experience`
  - `company`
  - `title`
  - `date_range`
  - `location`
  - `description_or_bullets`
- `education`
  - `institution`
  - `degree`
  - `date_range`
  - `location`
  - `notes`
- `skills`
  - skills explícitas
- `languages`
  - `language`
  - `proficiency` quando explícita

### Serializer para futura indexação
O pipeline agora também produz uma serialização-base em `runtime_metadata.indexing_payload` com:
- `raw_text`
- campos confirmados
- entradas estruturadas de `experience`, `education`, `skills`, `languages`

## Real CV indexing flow

No fluxo real de indexação, quando `indexing_payload` estiver disponível, o texto indexável do CV passa a ser montado a partir de:
- `[CV CONFIRMED FIELDS]`
- `[CV EXPERIENCE]`
- `[CV EDUCATION]`
- `[CV SKILLS]`
- `[CV LANGUAGES]`
- `[CV RAW TEXT]`

Somente conteúdo confirmado/estruturado entra nas seções principais do texto indexável.
Conteúdo fraco, `visual_candidate` ou não confirmado permanece fora do corpo principal indexado e continua disponível apenas em metadata.

### Por que isso é melhor que raw-text-only indexing
- melhora legibilidade semântica do conteúdo indexado
- prioriza campos e entradas mais confiáveis
- preserva o raw text completo como fallback contextual
- mantém compatibilidade com o fallback legado

### Como reindexar CVs existentes
Reenvie os PDFs pelo fluxo atual do app com o `evidence_cv` habilitado, ou reindexe o corpus de CVs usando o mesmo caminho de upload/indexação já existente. O texto salvo no índice passará a usar a montagem estruturada automaticamente quando `indexing_payload` estiver presente.

### Limitações atuais desta fundação
- agrupamento ainda é heurístico e de primeira passada
- não busca perfeição de schema final
- preserva evidência e honestidade de status para evolução futura