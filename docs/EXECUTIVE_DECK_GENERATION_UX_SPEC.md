# Executive Deck Generation — UX spec

## Objetivo

Definir como a capability deve aparecer para o usuário no produto.

---

## Princípio de UX

Na interface, isso deve aparecer como capability do AI Workbench, e não como projeto separado.

Naming recomendado:

- **Executive Deck Generation**
- **Generate executive deck**
- **Business review decks**

Evitar:

- “usar ppt_creator_app”
- “abrir app de PPT”

---

## UX mínima do P1 no app atual

### Entrada

O usuário deve conseguir:

- acionar a geração do `Benchmark & Eval Executive Review Deck`

### Ações mínimas

- gerar deck
- baixar `.pptx`
- baixar contract JSON
- baixar payload JSON
- ver status da operação
- ver falhas e warnings

### Feedback esperado

- `Gerando contract...`
- `Chamando renderer...`
- `Baixando artefatos...`
- `Deck pronto para download`

---

## UX futura da capability

### Seleção de deck type

O usuário poderá escolher entre:

- benchmark/eval review
- document review
- comparison deck
- action plan
- candidate review
- evidence pack

### Histórico

O produto deve exibir:

- exports recentes
- status
- deck type
- data/hora
- downloads disponíveis

### Entradas futuras por fluxo

- a partir do fluxo de benchmark/eval
- a partir do fluxo de document review
- a partir do fluxo de comparison
- a partir do fluxo de CV analysis

---

## Progressão de interface

### Streamlit atual

- primeira UX funcional
- foco em capability e downloads

### Gradio

- showcase mais AI-first
- fluxo mais claro por deck type

### App web

- catálogo explícito de deck types
- histórico de exports
- workflows mais próximos de produto real
