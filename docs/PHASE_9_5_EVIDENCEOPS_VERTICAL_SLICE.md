# Phase 9.5 — EvidenceOps vertical slice 1B

## Objetivo desta rodada

Fechar o **slice 1B** da Fase 9.5 sem depender de infraestrutura externa, fortalecendo a vertical EvidenceOps em cima de `filesystem + SQLite`.

## O que foi adicionado

- **repository search mais forte**
  - filtros por `category`, `suffix` e `document_id`
  - scoring local por múltiplos termos
- **snapshot + drift documental**
  - snapshot local persistido em `.phase95_evidenceops_repository_snapshot.json`
  - diff com contagem de documentos `new`, `changed` e `removed`
- **guardrails auditáveis no action store**
  - updates sensíveis exigem `approval_status="approved"`, `approval_reason` e `approved_by`
  - histórico de atualização salvo em `metadata.update_history`
- **fachada operacional local mais completa**
  - busca, sumário e comparação de estado do repository
  - sumário de actions/worklog pronto para futura promoção a adapter MCP/HTTP
- **observabilidade melhor na sidebar/runtime snapshot**
  - métricas de drift documental
  - métricas de governança (`review_required`, `approved`, `pending approval`, `overdue`)

## Leitura arquitetural

Esta entrega **ainda não é o Slice 2**. Ela continua 100% no escopo do **Slice 1**:

- repositório documental local
- worklog local
- action store local
- governança/human-in-the-loop em writes sensíveis

O ganho é que a vertical passa a ficar **“MCP-shaped”**:

- contratos locais mais claros
- observabilidade melhor
- comparação de estado documental
- trilha auditável para writes

## O que isso prepara para depois

Com essa base, o próximo passo pode trocar adapters sem reescrever a vertical:

- `filesystem` -> `Nextcloud/WebDAV`
- `SQLite local` -> `GitHub Issues` / fila externa
- fachada local -> MCP server/adapter HTTP

## Evidência de pronto

Esta rodada deve permitir demonstrar localmente:

1. busca e listagem do corpus EvidenceOps
2. detecção de drift documental entre snapshots
3. registro e atualização auditável de actions
4. bloqueio de writes sensíveis sem aprovação explícita
5. exposição desses sinais no runtime snapshot/sidebar