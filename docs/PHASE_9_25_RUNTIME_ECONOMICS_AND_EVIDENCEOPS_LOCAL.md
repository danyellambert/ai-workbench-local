# Phase 9.25 + Phase 9.5 (local) — Runtime economics e EvidenceOps foundation

## Objetivo desta rodada

Adiantar o que já dava para fechar **sem depender** de MCP externo, deploy público, Oracle, Gradio ou integrações adicionais.

O foco desta implementação foi fortalecer duas trilhas locais:

- **Fase 9.25** → runtime economics, usage observability e budget-aware routing
- **Fase 9.5 (fundação local)** → EvidenceOps worklog + evidence pack reaproveitável

---

## O que foi implementado

### 1. Runtime execution log mais rico

O agregado de execuções em `src/storage/runtime_execution_log.py` passou a resumir também:

- `prompt_build_latency_s`
- média de documentos selecionados por run
- média de chunks recuperados por run
- chunks usados vs descartados no contexto final
- taxa de truncamento do contexto
- taxa de auto-degrade do budget routing
- pressão média e máxima de contexto
- contagem de runs com:
  - `evidence_pipeline`
  - OCR
  - Docling
  - VLM
- distribuições agregadas por:
  - `cost_source`
  - `budget_mode`
  - `budget_reason`
  - `context_window_mode`
  - `ocr_backend`

### 2. Sinais documentais operacionais gravados por execução

O app principal (`main_qwen.py`) agora registra no `runtime_execution_log` sinais locais derivados dos documentos selecionados, incluindo:

- quantos documentos acionaram a trilha `evidence_pipeline`
- quantos envolveram OCR
- quantos envolveram Docling
- quantos envolveram VLM
- total de páginas suspeitas
- total de páginas processadas com Docling
- total de regiões VL tentadas / bem-sucedidas
- distribuição de backends OCR usados

Esses sinais entram tanto no fluxo de **chat com RAG** quanto no fluxo **structured**.

### 3. Runtime snapshot expandido

O `src/services/runtime_snapshot.py` agora expõe melhor o estado operacional recente:

#### Chat

- `last_context_chars`
- `last_prompt_context_used_chunks`
- `last_prompt_context_dropped_chunks`
- `last_prompt_context_truncated`
- `last_total_tokens`
- `last_cost_usd`

#### Structured

- `last_context_chars`
- `last_full_document_chars`
- `last_context_strategy`
- `last_total_tokens`
- `last_cost_usd`
- sinais de budget routing da execução estruturada

### 4. Sidebar operacional mais explicável

O painel lateral (`src/ui/sidebar.py`) passou a mostrar melhor:

- sinais recentes de contexto no chat
- sinais recentes de contexto na execução estruturada
- métricas agregadas de runtime economics
- taxa de auto-degrade e truncamento
- métricas de OCR / Docling / VL
- novas distribuições agregadas de custo, budget e OCR backend

### 5. EvidenceOps worklog com evidence pack local

O `src/services/evidenceops_worklog.py` agora gera um bloco `evidence_pack` dentro da entrada do worklog.

Esse pack inclui:

- `review_type`
- `summary`
- `document_ids`
- `source_documents`
- `source_count`
- `findings_count`
- `action_items_count`
- `recommended_actions_count`
- `limitations_count`
- `finding_type_counts`
- `owner_counts`
- `status_counts`
- `due_date_counts`
- `needs_review`
- `needs_review_reason`

Além disso, a entrada principal do worklog agora expõe:

- `source_document_count`
- `finding_count`
- `action_item_count`
- `evidence_pack`

### 6. Sumário agregado do EvidenceOps mais útil

O agregado em `src/storage/phase95_evidenceops_worklog.py` agora também calcula:

- `unique_document_count`
- `finding_type_counts`
- `due_date_counts`

Isso melhora a leitura operacional do histórico local mesmo antes de existir um MCP externo.

### 7. Foundation local da Fase 9.5 para repository + action store

Além do worklog, esta rodada passou a expor melhor a espinha dorsal local do `EvidenceOps`:

- `src/services/evidenceops_repository.py`
  - listagem local do corpus por `filesystem`
  - classificação por categoria (`policies`, `contracts`, `audit`, `templates`)
  - extração de `document_id`, título, extensão, tamanho e caminho relativo
  - sumário agregado do corpus local

- `src/storage/phase95_evidenceops_action_store.py`
  - update local de ações já persistidas no `SQLite`
  - patch incremental de metadata para trilha auditável

- `src/services/evidenceops_local_ops.py`
  - camada de consulta local reaproveitável para futuro MCP/adapter HTTP
  - listagem e resolução de documentos do repositório local
  - listagem filtrável de ações por `status`, `owner` e `review_type`
  - atualização local de ação (`status`, `owner`, `due_date`, metadata)

- `src/services/runtime_snapshot.py`
  - novo resumo agregado de `evidenceops_actions`
  - novo resumo agregado de `evidenceops_repository`

- `src/ui/sidebar.py`
  - novo painel para o `action store local`
  - novo painel para o `document repository local`

Na prática, isso fecha um primeiro slice local de **Document Repository + Action Store foundation**, ainda sem MCP server real, mas já pronto para ser promovido a adapter externo depois.

---

## Testes adicionados / atualizados

Foram atualizados testes focados para cobrir as mudanças:

- `tests/test_runtime_execution_log_unittest.py`
- `tests/test_phase95_evidenceops_worklog.py`
- `tests/test_runtime_snapshot_unittest.py`
- `tests/test_phase95_evidenceops_local_ops.py`

Esses testes agora validam:

- novas agregações de runtime economics
- evidence pack e contagens adicionais do EvidenceOps
- exposição dos novos sinais no runtime snapshot
- listagem/consulta do repositório local de documentos
- listagem/atualização do action store local

---

## O que foi documentado como entregue parcialmente no roadmap

### Fase 9.25

Entregue nesta rodada:

- camada local mais unificada de métricas por execução
- registro de chars de contexto, chunks usados/descartados e truncamento
- registro de acionamento de OCR / Docling / VLM em nível operacional local
- visão agregada por provider/modelo no histórico agregado

### Fase 9.5 (fundação local)

Entregue nesta rodada:

- evidence pack estruturado reaproveitável em nível local
- action store local em `SQLite` com leitura, atualização e trilha auditável
- document repository local em `filesystem` sobre o corpus sintético de negócio
- camada de serviços locais pronta para futura exposição via MCP/HTTP
- snapshot/sidebar com leitura operacional do repository e do action store

---

## O que **não** foi implementado ainda

Estas partes continuam pendentes e foram mantidas como trabalho futuro:

### Runtime economics / budget-aware routing

- capturar tokens nativos quando o provider expuser telemetria real, em vez de depender principalmente de estimativa por caracteres
- budgets por task com thresholds explícitos de alerta
- política automática de fallback local/cloud orientada a custo
- validação sistemática do budget-aware routing contra evals
- visão agregada completa incluindo também o fluxo de `comparison`

### EvidenceOps / Phase 9.5

- MCP externo real (`Document Repository MCP`, `Worklog / Action MCP` etc.)
- MCP server local real em stdio/configuração externa
- busca documental externa via MCP
- comparação de versões via MCP
- permissões e human-in-the-loop para ações sensíveis em integração externa
- diff/versionamento documental mais forte dentro do repository adapter

---

## Leitura arquitetural correta desta rodada

O que existe agora é uma **fundação local forte** para as fases 9.25 e 9.5.

Ainda não é a fase MCP completa, mas já existe uma base prática para:

- observar custo/uso de forma mais útil
- auditar melhor o comportamento documental
- reaproveitar evidence packs no futuro
- preparar a transição para integrações operacionais reais sem perder rastreabilidade