# Fase 10 — Engenharia profissional

## Objetivo

Fechar a trilha de engenharia profissional com um baseline defendível de execução, confiabilidade, smoke validation, observabilidade e manutenção.

## O que entrou nesta fase

- `Dockerfile` e `.dockerignore` para execução reproduzível do app principal
- logging central em `src/services/app_logging.py`
- padronização mínima de mensagens de erro de UI em `src/services/app_errors.py`
- smoke tests reais de Streamlit com `streamlit.testing.v1`
- extração do painel MCP para `src/ui/evidenceops_mcp_panel.py` para reduzir acoplamento em `main_qwen.py`
- medição agregada de gargalos dominantes de latência no runtime log (`retrieval`, `generation`, `prompt_build`, `other`)
- workflow de CI cobrindo smoke tests e testes focados de observabilidade

## Decisões de engenharia

### 1. Smoke test real da aplicação

Em vez de validar só composição estática, a fase agora cobre as duas entradas principais do produto:

- `main.py` com interação mínima de chat e fallback local sem `OPENAI_API_KEY`
- `main_qwen.py` com renderização completa, tabs operacionais e controles críticos presentes

Isso reduz regressões silenciosas de Streamlit, session state e montagem da interface.

### 2. Falhas controladas no fluxo estruturado

O fluxo de execução estruturada do `main_qwen.py` passou a capturar falhas inesperadas no topo do submit e converter isso em `StructuredResult` controlado via `attempt_controlled_failure`.

Com isso:

- a UI não quebra inteira em erro inesperado
- a execução continua auditável
- o runtime log continua registrando a tentativa
- a sidebar de observabilidade continua coerente

### 3. Padronização de logs e mensagens

Os pontos críticos do app usam logging central e mensagens de erro consistentes para UI.

Direção adotada:

- log detalhado para engenharia
- mensagem curta e consistente para usuário
- fallback explícito quando retrieval / MCP / structured execution falham

### 4. Clareza estrutural

O painel EvidenceOps MCP foi extraído de `main_qwen.py` para um módulo de UI dedicado.

Benefícios:

- reduz o acoplamento do entrypoint principal
- melhora legibilidade do app
- isola um slice funcional inteiro da UI
- facilita evolução e testes futuros do console MCP

### 5. Observabilidade de gargalos

O runtime log agora resume a participação relativa das etapas de latência por execução:

- retrieval
- generation
- prompt build
- other

Além da média de latência absoluta, o app exibe qual estágio domina o tempo total com mais frequência.

## Evidências desta fase

- smoke tests de Streamlit em `tests/test_streamlit_app_smoke_unittest.py`
- observabilidade de runtime em `src/storage/runtime_execution_log.py` e `src/ui/sidebar.py`
- documentação desta decisão em `docs/PHASE_10_ENGINEERING_PROFESSIONAL.md`

## Resultado

A Fase 10 fecha o projeto com um baseline mais profissional para portfólio:

- app executável localmente e via Docker
- CI com smoke + testes focados
- falhas críticas tratadas de forma controlada
- logging centralizado
- melhor separação entre entrypoint e componentes de UI
- métricas operacionais úteis para defender performance e manutenção em entrevista