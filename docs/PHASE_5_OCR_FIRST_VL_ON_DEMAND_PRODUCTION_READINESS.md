# OCR-first / VL-on-demand Production Readiness for CV Parsing

## 1. Resumo executivo

O pipeline `evidence_cv` atingiu um estado de **readiness para rollout controlado** em produção para parsing de CVs, com arquitetura OCR-first, acionamento seletivo de VL, política híbrida conservadora de consumo no produto, observabilidade suficiente e fallback operacional seguro.

Síntese da decisão final:
- usar OCR/native extraction como caminho principal
- chamar VL apenas sob necessidade real
- manter consumo automático restrito a `confirmed`
- usar merge híbrido conservador para contatos
- ativar rollout primeiro para CV-like PDFs e scan-like fortes

## 2. Arquitetura final do pipeline

Fluxo final:
1. extração native text + OCR
2. reconciliação evidencial básica
3. roteador OCR-first / VL-on-demand
4. VL seletivo por região somente quando necessário
5. normalização, dedupe e ranking
6. política de consumo do produto
7. shadow rollout / observabilidade / fallback

Arquivos centrais:
- `src/evidence_cv/pipeline/runner.py`
- `src/evidence_cv/vision/ollama_vl.py`
- `src/rag/loaders.py`
- `src/evidence_cv/config.py`

## 3. Política OCR-first / VL-on-demand

### Princípio
OCR/native extraction sempre vem primeiro.
VL não é chamado por default em todo CV.

### Regra final do roteador

#### Em `digital_pdf`
VL só pode ser chamado quando houver:
- `missing_contacts_after_ocr`
- ou problema estrutural forte no topo/header

Na calibração final, isso reduziu drasticamente chamadas desnecessárias de VL em PDFs digitais bons.

#### Em `scanned_pdf` e `mixed_pdf`
O roteador permanece mais permissivo, já que o ganho de VL tende a ser mais real nesses documentos.

### Telemetria do roteador
Metadata por arquivo:
- `vl_router.enabled`
- `vl_router.decision`
- `vl_router.reasons`
- `vl_router.document_signals`
- `vl_router.regions_selected`
- `vl_router.skipped_because`

## 4. Resultados do benchmark multilayout de 60 CVs

Arquivo base:
- `phase5_eval/reports/evidence_cv_multilayout_router_benchmark.json`

### Totais principais
- `files_processed = 60`
- `vl_called = 12`
- `vl_skipped = 48`

### Distribuição por tipo
- `digital_pdf = 48`
- `scanned_pdf = 12`

### Leitura econômica
O roteador ficou economicamente aceitável:
- VL foi pulado na maior parte dos digitais
- VL foi reservado principalmente para scans difíceis

## 5. Resultados dos casos com VL chamado

Arquivo específico:
- `phase5_eval/reports/evidence_cv_vl_called_cases_report.json`

Casos com VL chamado:
- `vl_called_cases = 12`

Distribuição semântica final:
- `vl_called_and_added_value = 8`
- `vl_called_and_added_partial_value = 4`
- `vl_called_but_review_only = 0`
- `vl_called_and_added_noise = 0`
- `vl_called_and_false_positive = 0`

### Interpretação
- a maioria dos casos com VL chamado trouxe ganho real
- os demais trouxeram ganho parcial com ruído residual controlado
- casos semanticamente ruins deixaram de ser promovidos como ganho pleno

## 6. Política final por campo

### `emails`
- usar merge híbrido
- legado confirmado tem precedência
- evidence `confirmed` apenas complementa lacunas

### `phones`
- usar merge híbrido
- legado confirmado tem precedência
- evidence `confirmed` apenas complementa lacunas

### `name`
- usar apenas `confirmed`

### `location`
- usar apenas `confirmed`

## 7. Comportamento de status

### `confirmed`
- consumível automaticamente

### `visual_candidate`
- não consumir automaticamente
- expor para revisão futura / UX assistida

### `needs_review`
- não consumir automaticamente

### `not_found`
- tratar como ausente

## 8. Resiliência operacional e fallback

### Backend VL/Ollama
- timeout mantido em `600s`
- erro estruturado via `VLInspectionError`
- retry curto e conservador para falhas transitórias

### Runner
- falha por região não derruba o PDF inteiro
- se todas as regiões falharem, segue sem enriquecimento VL

### Script/benchmark
- falha de um arquivo não derruba o relatório inteiro
- JSON final continua sendo produzido

### Metadata operacional
- `vl_runtime.enabled`
- `vl_runtime.model`
- `vl_runtime.regions_attempted`
- `vl_runtime.regions_succeeded`
- `vl_runtime.regions_failed`
- `vl_runtime.timeouts`
- `vl_runtime.fallback_used`
- `vl_runtime.warnings`

## 9. Recomendação de rollout controlado

### Recomendação objetiva
Ativar primeiro para:
- CV-like PDFs
- scan-like fortes

### Comportamento em produção
- manter OCR-first como padrão
- usar VL-on-demand apenas quando o roteador mandar
- manter merge híbrido para contatos
- manter `visual_candidate` fora do consumo automático

### Decisão de readiness
**Recomendação: pronto para rollout controlado.**

Não é um parser universal “resolvido”, mas já está maduro o suficiente para produção controlada com telemetria, fallback e política conservadora.

## 10. Próximos passos sugeridos

### 10.1 Rollout / produto
- ativar rollout por feature flag para subset de uploads CV-like
- acompanhar shadow rollout e conflitos reais em produção
- monitorar custo/latência por tipo de documento
- manter dashboard de `vl_called`, `vl_skipped`, `fallback_used`, `timeouts`

### 10.2 Futuras melhorias do parser
- reduzir ruído residual em scans difíceis com ganho parcial
- melhorar semântica de `location` em casos internacionais
- melhorar dedupe e validação de contatos visuais quase duplicados
- só depois considerar expansão para `experience` / `education`

## Conclusão final

O pipeline final recomendado para CVs é:
- OCR-first
- VL-on-demand econômico
- merge híbrido conservador para contatos
- consumo automático apenas de `confirmed`
- fallback seguro e observabilidade suficiente

Em termos práticos: o sistema já está pronto para um rollout controlado e medido em produção.