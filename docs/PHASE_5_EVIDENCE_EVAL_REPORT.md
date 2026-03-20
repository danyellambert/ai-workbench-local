# Phase 5 Evidence CV Evaluation Report

## Objetivo

Consolidar a avaliação do pipeline `evidence_cv` com métricas por campo e orientar decisão de rollout.

## Comparação avaliada

- legado
- evidence sem VL
- evidence com VL

Campos avaliados:
- `name`
- `emails`
- `phones`
- `location`

## Uso no produto

Política recomendada nesta fase:
- usar automaticamente apenas `confirmed`
- manter `visual_candidate` e `needs_review` fora do consumo automático
- expor esses estados apenas como metadata/revisão

## Onde o VL agrega mais valor

Melhor custo/benefício atual:
- PDFs `scanned_pdf`
- scan-like médios
- documentos com header/contact difíceis para OCR puro

Menor benefício atual:
- PDFs digitais já legíveis
- documentos em que OCR/native text já recuperam contato com boa qualidade

## Onde ainda há ruído

Casos mais difíceis ainda apresentam:
- `visual_candidate` extras
- falso positivo residual em contato
- localização incerta em scans degradados

## Recomendação objetiva de rollout

Ativar por padrão primeiro para:
- CV-like PDFs
- scan-like fortes

Manter desligado por padrão para todos os PDFs genéricos até nova rodada de refinamento.