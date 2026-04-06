# Phase 5 — OCR fallback e benchmark sintético de CVs

## Estado consolidado

A Fase 5 está forte para documentos textuais e agora possui fallback OCR inicial para documentos scan-like.

## O que já está validado

- smoke eval da Fase 5 com PASS em:
  - extraction
  - summary
  - checklist
  - cv_analysis
  - code_analysis
- benchmark sintético multilayout com PASS consistente nos layouts textuais:
  - classic_one_column
  - modern_two_column
  - compact_sidebar
  - dense_executive
- casos scan-like agora passam por OCR fallback quando o texto inicial é insuficiente

## Leitura correta do estado atual

### Forte
- structured outputs em documentos textuais
- cv_analysis em layouts textuais
- separação entre chat com RAG e documento estruturado
- benchmark sintético multilayout
- observabilidade de OCR fallback

### Parcialmente forte
- scan-like / image-based PDFs com OCR fallback

### Limitação conhecida
- alguns scan-like continuam fracos mesmo com OCR
- OCR melhora parte dos casos, mas não resolve todos os scans difíceis
- isso deve ser tratado como limitação conhecida, não como erro silencioso

## Narrativa recomendada

> O sistema é robusto para documentos com texto extraível.
> Para documentos image-based, o pipeline tenta OCR fallback.
> Parte desses casos melhora e passa a ser analisável, mas a qualidade ainda depende do tipo de scan e da qualidade do OCR.

## Próximos passos restantes da Fase 5

- validar com documentos reais além dos fixtures e resumes sintéticos
- registrar evidências visuais fortes da fase
- documentar claramente o limite atual do OCR fallback
- decidir depois se vale uma trilha OCR mais forte
