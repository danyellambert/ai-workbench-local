# Phase 5 — exemplos recomendados para capturas de UI

Use estes quatro tipos de exemplo para montar as evidências da Fase 5:

## 1. Exemplo textual limpo com PASS
Objetivo: mostrar que o `cv_analysis` funciona bem em PDF textual.

Exemplo recomendado:
- `modern_two_column` com status `PASS`

Procure um arquivo como:
- `0001_medium_modern_two_column_*.pdf`

O que mostrar na UI:
- documento selecionado
- aba **Documento estruturado**
- task `cv_analysis`
- `Use selected documents`
- `document_scan`
- output com:
  - nome
  - email
  - location
  - skills
  - languages
  - education
  - experience

## 2. Exemplo textual visualmente mais denso com PASS
Objetivo: mostrar robustez além do layout simples.

Exemplo recomendado:
- `compact_sidebar` com status `PASS`
ou
- `dense_executive` com status `PASS`

Procure um arquivo como:
- `0007_medium_compact_sidebar_*.pdf`
- `0003_simple_dense_executive_*.pdf`

O que mostrar:
- mesmo fluxo acima
- destaque que o layout é mais difícil, mas o resultado continua bom

## 3. Exemplo scan-like com OCR fallback e melhoria
Objetivo: mostrar que o OCR fallback está funcionando.

Exemplo recomendado:
- `scan_like_image_pdf` com status `WARN`

Procure um arquivo como:
- `0004_medium_scan_like_image_pdf_*.pdf`
ou
- `0014_hard_scan_like_image_pdf_*.pdf`

O que mostrar:
- documento scan-like selecionado
- resultado estruturado parcial
- observação de que houve OCR fallback
- deixar claro que é um caso image-based

## 4. Exemplo scan-like ainda difícil
Objetivo: documentar limitação conhecida de forma honesta.

Exemplo recomendado:
- `scan_like_image_pdf` com status `FAIL` ou score baixo

Procure um arquivo como:
- `0009_simple_scan_like_image_pdf_*.pdf`

O que mostrar:
- que o pipeline tentou lidar com o caso
- que ainda existe limite em scans difíceis
- que isso é documentado como limitação conhecida

## Pacote mínimo de evidências

Eu recomendo salvar:

- 2 screenshots de casos textuais em PASS
- 1 screenshot de caso scan-like melhorado via OCR
- 1 screenshot de caso scan-like ainda difícil
- 2 JSONs bons exportados pelo app
- 1 trecho do benchmark sintético
- 1 trecho do smoke eval da Fase 5

## Nomes sugeridos dos arquivos

- `phase5_ui_01_textual_pass.png`
- `phase5_ui_02_visual_pass.png`
- `phase5_ui_03_scanlike_ocr_warn.png`
- `phase5_ui_04_scanlike_limit.png`
- `phase5_structured_output_cv_good.json`
- `phase5_structured_output_summary_good.json`
- `phase5_benchmark_resume_excerpt.csv`
- `phase5_smoke_eval_excerpt.txt`
