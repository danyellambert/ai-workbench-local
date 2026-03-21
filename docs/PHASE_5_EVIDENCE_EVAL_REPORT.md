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

## Evaluation hardening for contacts

Esta fase focou em alinhar corretamente a avaliação de `emails` e `phones` entre:
- valores previstos
- gold set manual
- normalização usada na comparação
- métricas agregadas e por arquivo

### Forma canônica final para emails
- comparação case-insensitive
- trim de espaços
- remoção de duplicatas pela forma normalizada
- emails inválidos/incompletos são descartados da comparação

Forma usada para comparar:
- `local@domain.tld` em lowercase

### Forma canônica final para telefones
- comparação por dígitos normalizados
- remoção de espaços, parênteses, hífens e símbolos decorativos
- deduplicação por sequência numérica final
- sequências curtas/implausíveis são descartadas

Forma usada para comparar:
- string apenas com dígitos
- aceitando DDI/DDDs quando presentes no documento

### O que estava desalinhado antes
- diferenças cosméticas entravam como erro
- o relatório de contatos não mostrava claramente TP/FP/FN por arquivo
- havia pouco material de debug para inspeção rápida

### O que foi corrigido
- normalização explícita e consistente nos dois lados
- debug por arquivo com contatos previstos, gold normalizado, matches, falsos positivos e falsos negativos
- métricas agregadas de `predicted_total`, `gold_total`, `tp`, `fp`, `fn`, `precision`, `recall`

### Leitura prática do estado atual
- a avaliação agora está mais coerente e reproduzível
- ainda existe desalinhamento entre corpus sintético e valores de contato previstos em alguns documentos
- isso indica que a infraestrutura de avaliação está melhor, mas parte do ruído agora é realmente de extração/dados, não apenas de comparação

### Conclusão desta fase
Para rollout controlado:
- `confirmed` continua pronto para consumo automático
- `visual_candidate` continua devendo revisão
- a avaliação de contatos já está significativamente mais auditável
- porém ainda não deve ser tratada como totalmente resolvida enquanto houver divergência forte entre contatos previstos e gold set em parte do corpus sintético

## Adjudicação dos casos divergentes de contatos

Arquivo gerado:
- `phase5_eval/reports/evidence_cv_contact_adjudication.json`

### Causas raiz encontradas

Após inspeção dos casos divergentes:

- `gold_set_incorrect`: **6** divergências de contato
- `corpus_inconsistent`: **0**
- `pipeline_false_positive`: **2**
- `pipeline_false_negative`: **0**
- `normalization_mismatch`: **0**
- `ambiguous_document`: **0**

### Leitura objetiva

Os casos de Gabriel, Marina e Beatriz mostraram que a maior parte do erro anterior estava no **gold set**, não na comparação nem necessariamente no pipeline.

O caso de Matheus continua sendo o principal exemplo de **falso positivo do pipeline** em scan-like difícil, especialmente quando o VL entra e propõe contatos não sustentados pelo documento.

### Métricas finais após adjudicação

#### Legacy
- emails: precision **1.0**, recall **1.0**
- phones: precision **1.0**, recall **1.0**

#### Evidence sem VL
- emails: precision **1.0**, recall **0.6**
- phones: precision **0.2727**, recall **0.6**

#### Evidence com VL
- emails: precision **0.7143**, recall **1.0**
- phones: precision **0.8333**, recall **1.0**

### Conclusão de rollout para contatos

Com adjudicação aplicada:
- a avaliação de contatos ficou suficientemente confiável para orientar rollout
- o ganho do caminho VL em **recall** de contatos é real
- o principal risco residual está concentrado em scan-like difíceis como Matheus

Recomendação prática:
- manter rollout controlado do pipeline evidence para **CV-like PDFs** e **scan-like fortes**
- continuar consumindo automaticamente apenas `confirmed`
- manter `visual_candidate` fora do consumo automático até nova rodada de refinamento de precisão para casos extremos

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

## Política híbrida de consumo e shadow rollout

Nesta fase, o produto passa a operar com política híbrida para contatos:

### Merge híbrido para contatos
- `emails`:
  - legado confirmado tem precedência
  - evidence `confirmed` entra apenas para preencher lacunas
- `phones`:
  - legado confirmado tem precedência
  - evidence `confirmed` entra apenas para preencher lacunas

### Campos singulares
- `name`: consumir apenas `evidence confirmed`
- `location`: consumir apenas `evidence confirmed`

### Shadow rollout
O metadata agora registra:
- quando legado e evidence concordam
- quando evidence apenas complementa
- quando há conflito

Campos disponíveis no upload pipeline:
- `metadata.hybrid_contact_policy`
- `metadata.shadow_rollout`

## Recomendação final de rollout por campo

- `emails`: usar merge híbrido
- `phones`: usar merge híbrido
- `name`: manter conservador, só `confirmed`
- `location`: manter conservador, só `confirmed`

## Relatório de shadow rollout

Script:
- `scripts/report_evidence_shadow_rollout.py`

Saída padrão:
- `phase5_eval/reports/evidence_cv_shadow_rollout_report.json`

## Observabilidade final do shadow rollout

Após ajustar a propagação dos metadados e alinhar o script com o mesmo caminho de carga/extração do fluxo real, o relatório de shadow rollout passou a refletir quantitativamente o comportamento híbrido.

### Totais atuais
- `agreements`: **2**
- `email_complements`: **5**
- `phone_complements`: **5**
- `email_conflicts`: **0**
- `phone_conflicts`: **0**

### Exemplos concretos

#### Complemento
- `0001_medium_modern_two_column_gabriel.gomes.almeida.pdf`
  - email_complement = 1
  - phone_complement = 1

- `0002_hard_compact_sidebar_marina.gomes.ribeiro.pdf`
  - email_complement = 1
  - phone_complement = 1

- `0004_medium_scan_like_image_pdf_beatriz.barbosa.martins.pdf`
  - email_complement = 3
  - phone_complement = 3

#### Agreement
- `0009_simple_scan_like_image_pdf_matheus.araujo.carvalho.pdf`
  - agreements = 2
  - nenhum contato foi promovido pelo merge híbrido

#### Conflict
- nesta rodada de shadow rollout: **nenhum conflito quantitativo apareceu**

### Conclusão desta etapa
A telemetria de shadow rollout agora está **completa e confiável** para:
- agreement
- complement
- conflict

Isso fecha a observabilidade mínima necessária para rollout controlado da política híbrida no produto.