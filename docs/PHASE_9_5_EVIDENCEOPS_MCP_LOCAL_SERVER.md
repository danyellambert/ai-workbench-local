# Phase 9.5 — EvidenceOps MCP server local

## O que esta entrega adiciona

Esta rodada promove a vertical EvidenceOps local para um **MCP server real em stdio**, sem depender de SDK externo e sem sair do stack atual `filesystem + SQLite`.

## Onde está o servidor

- implementação principal: `src/mcp/evidenceops_server.py`
- transporte/framing JSON-RPC stdio: `src/mcp/jsonrpc_stdio.py`
- entrypoint simples: `scripts/run_evidenceops_mcp_server.py`

## Tools expostas

- `list_documents`
- `search_documents`
- `get_document`
- `summarize_repository`
- `compare_repository_state`
- `register_evidenceops_entry`
- `list_actions`
- `summarize_actions`
- `update_action`
- `summarize_worklog`

## Resources expostos

- `evidenceops://repository/summary`
- `evidenceops://repository/drift`
- `evidenceops://actions/summary`
- `evidenceops://worklog/summary`

## Como rodar localmente

```bash
python /Users/danyellambert/Downloads/Aula\ 4\ -\ Criacao\ de\ Chatbot\ com\ IA\ em\ Tempo\ Real/scripts/run_evidenceops_mcp_server.py
```

## Registro no Cline

O registro do servidor no Cline é **opcional**.

- ele pode ser útil para debug/manual testing com o Cline como cliente MCP
- mas **não faz parte do core do produto**
- o fluxo principal do projeto continua sendo:
  - MCP server local
  - cliente MCP do app
  - integration with `main.py`

Se você não quiser misturar a infraestrutura do projeto com a infraestrutura do assistente, pode deixar o Cline **sem esse registro**.

## Variáveis de ambiente suportadas

- `EVIDENCEOPS_REPOSITORY_ROOT`
- `EVIDENCEOPS_REPOSITORY_BACKEND` (`local` ou `nextcloud_webdav`)
- `EVIDENCEOPS_REPOSITORY_SNAPSHOT_PATH`
- `EVIDENCEOPS_ACTION_STORE_PATH`
- `EVIDENCEOPS_WORKLOG_PATH`

Quando `EVIDENCEOPS_REPOSITORY_BACKEND=nextcloud_webdav`, o **Document Repository MCP** passa a usar o adapter real do Nextcloud/WebDAV para as tools de repository (`list_documents`, `search_documents`, `get_document`, `summarize_repository`, `compare_repository_state`), preservando o fallback local quando o backend continua em `local`.

Se não forem definidas, o servidor usa os paths locais padrão do projeto.

## Demo local

Existe uma demo determinística que sobe o servidor, inicializa o cliente MCP e chama as tools principais:

```bash
python /Users/danyellambert/Downloads/Aula\ 4\ -\ Criacao\ de\ Chatbot\ com\ IA\ em\ Tempo\ Real/scripts/demo_phase95_evidenceops_mcp.py
```

Ela demonstra:

1. `initialize`
2. `tools/list`
3. `list_documents`
4. `register_evidenceops_entry`
5. `list_actions`
6. `compare_repository_state`
7. `update_action`
8. `resources/read`

## Integração atual no produto

Além do servidor local em si, a fase agora já tem:

- **cliente MCP reutilizável no app** (`src/services/evidenceops_mcp_client.py`)
- uso do MCP no fluxo principal do `document_agent`
- **telemetria MCP** no runtime execution log e na sidebar
- uma aba **"EvidenceOps MCP"** no app para operar repository/actions/worklog via MCP real

## Leitura correta desta entrega

Isto ainda continua dentro do **slice 1** da fase 9.5:

- o servidor é **MCP real**
- mas os adapters continuam **locais**
- ou seja: a engine segue em `filesystem + SQLite`

## Arquitetura-alvo oficial da fase 9.5

Depois desta rodada, o alvo oficial da fase passa a ser:

- **`Nextcloud/WebDAV`** para o repository documental externo
- **`Trello`** para actions, owners, comentários e fluxo humano
- **`Notion`** para evidence register, dashboard operacional e handoff executivo

Leitura recomendada:

- o baseline local (`filesystem + SQLite`) continua como fallback e trilha de debug
- a tríade externa (`Nextcloud/WebDAV + Trello + Notion`) vira a direção principal do slice externo da fase

## O que ainda depende de setup externo

Para fechar a fase completa com adapters externos reais, ainda serão necessários:

- **Nextcloud/WebDAV**
  - base URL
  - usuário
  - senha ou app password
  - pasta/base documental alvo
- **Trello**
  - API key
  - token
  - board alvo
  - mapeamento mínimo de listas/status
- **Notion**
  - integration token
  - database IDs ou page IDs
  - schema mínimo para evidence packs, status, owner, due date e links de origem

## Próximo passo natural

O próximo passo natural já não é mais genérico. Ele passa a ser abrir os adapters externos em ordem:

1. `Nextcloud/WebDAV`
2. `Trello`
3. `Notion`