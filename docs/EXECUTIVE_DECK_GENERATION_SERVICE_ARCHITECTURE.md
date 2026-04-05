# Executive Deck Generation — arquitetura de serviço

## Objetivo

Descrever como a capability de **Executive Deck Generation** deve ser implementada no ecossistema atual.

---

## Princípio arquitetural

### AI Workbench Local

Responsável por:

- grounding
- consolidação de sinais
- montagem de contracts
- orquestração da capability
- persistência local de artefatos e logs

### `ppt_creator_app`

Responsável por:

- validação do spec de apresentação
- renderização `.pptx`
- preview/review visual
- artifact serving

---

## Componentes principais no AI Workbench

### 1. Contract builders

Responsáveis por transformar sinais do produto em contracts por `export_kind`.

Exemplo inicial já existente:

- `src/services/presentation_export.py`

### 2. Renderer adapters

Responsáveis por transformar contract do domínio em payload compatível com o `ppt_creator`.

### 3. `presentation_export_service`

Componente orquestrador da capability.

Responsabilidades:

- verificar feature flag/config
- verificar saúde do renderer
- montar contract
- montar payload
- chamar API do `ppt_creator_app`
- baixar artefatos
- persistir cópias locais
- devolver resultado estruturado para UI/backend

### 4. Artifact store local

Diretório/versionamento local com:

- contract
- payload
- render response
- `.pptx`
- review/previews relacionados

### 5. UI integration layer

Camada que expõe a capability para:

- Streamlit atual
- futura UI em Gradio
- futuro app web

---

## Fluxo síncrono recomendado para o P1

1. usuário aciona geração do deck
2. AI Workbench resolve `export_kind`
3. builder gera contract
4. adapter gera payload do renderer
5. `presentation_export_service` chama `GET /health`
6. `presentation_export_service` chama `POST /render`
7. AI Workbench baixa o `.pptx` via `GET /artifact`
8. AI Workbench persiste artefatos locais
9. UI recebe resultado estruturado e downloads

---

## Evolução arquitetural recomendada

### Fase 1

- fluxo síncrono
- um deck type principal
- artifact store local

### Fase 2

- múltiplos `export_kind`
- histórico de exports
- integração mais clara ao backend HTTP do produto

### Fase 3

- jobs assíncronos se necessário
- preview/review mais forte
- recorrência / geração programada

---

## Boundary de código recomendado

### AI Workbench

Arquivos/áreas alvo:

- `src/services/presentation_export.py` — builders/adapters atuais
- `src/services/presentation_export_service.py` — novo service
- `src/config.py` — configuração da capability
- `src/ui/...` — superfície de produto

### `ppt_creator_app`

Reaproveitar endpoints já existentes. Evitar mover lógica de domínio para o renderer.

---

## O que não fazer

- copiar renderer para dentro do AI Workbench
- misturar lógica do deck diretamente na UI
- acoplar domínio ao schema cru do renderer cedo demais
- usar LLM no último passo do P1 quando o caminho pode ser determinístico
