# Phase 9.5 — External target architecture

## Decisão oficial desta fase

O alvo oficial para o fechamento externo da Fase 9.5 passa a ser:

- **Nextcloud/WebDAV** para o repositório documental externo
- **Trello** para a fila operacional de actions/worklog humano
- **Notion** para evidence register, dashboard operacional e handoff executivo

O corpus principal oficial da demo passa a ser:

- **`data/corpus_revisado/option_b_synthetic_premium`**

O corpus complementar/canônico passa a ser:

- **`data/corpus_revisado/option_a_public_corpus_v2`**

## Papel de cada integração

### 1. Nextcloud/WebDAV

Responsável por:

- armazenar `policies`, `contracts`, `audit`, `templates` e artefatos correlatos
- servir como base do **Document Repository MCP**
- permitir busca documental externa, leitura de metadados e comparação de drift/versão

### 2. Trello

Responsável por:

- representar `action_items` fora do app
- dar owner, comentários, status e trilha humana às ações
- servir como base do **Worklog / Action MCP**

### 3. Notion

Responsável por:

- guardar evidence packs, dashboards e visões executivas
- funcionar como camada legível para revisão humana e handoff
- concentrar a visão de status, evidências, responsáveis e links para documentos/ações

## Leitura arquitetural final

### O que continua local

- `filesystem + SQLite`
- MCP server local
- cliente MCP do app
- observabilidade MCP
- demo end-to-end local

### O que sobe para camada externa

- documents: `Nextcloud/WebDAV`
- actions/workflow humano: `Trello`
- register/dashboard executivo: `Notion`

## Ordem recomendada de implementação

1. **Nextcloud/WebDAV**
   - listar documentos
   - buscar documentos
   - ler metadados
   - comparar drift/versões

2. **Trello**
   - criar ação
   - atualizar status
   - atribuir owner
   - comentar aprovação/rejeição

3. **Notion**
   - registrar evidence packs
   - gerar visão operacional resumida
   - consolidar links de documentos, ações e evidências

## O que ainda depende do usuário

### Nextcloud/WebDAV

- base URL
- usuário
- senha ou app password
- pasta/base documental alvo

### Trello

- API key
- token
- board alvo
- listas/estados mínimos

### Notion

- integration token
- database IDs ou page IDs
- schema mínimo das tabelas/páginas alvo

## Definição prática de “fase 9.5 completa”

Considerar a fase 9.5 completa quando houver:

1. **MCP local real** funcionando
2. **app usando MCP** no fluxo principal
3. **observabilidade MCP** no runtime
4. **Nextcloud/WebDAV** conectado como repository externo
5. **Trello** conectado como action/worklog externo
6. **Notion** conectado como camada de evidence register/dashboard
7. **demo end-to-end** mostrando documento externo -> análise -> evidence pack -> action -> dashboard