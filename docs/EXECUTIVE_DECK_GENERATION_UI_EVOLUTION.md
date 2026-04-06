# Executive Deck Generation — evolução de UI

## Objetivo

Descrever como a capability aparece em cada etapa de interface do produto.

---

## Etapa 1 — Streamlit atual

Objetivo:

- provar utilidade funcional da capability
- servir como baseline temporária enquanto a superfície de produto é separada do AI Lab

Capacidades mínimas:

- gerar P1
- baixar `.pptx`
- baixar contract/payload
- ver status/warnings

---

## Etapa 2 — Gradio

Objetivo:

- tornar a demo mais AI-first e orientada a workflows
- assumir a superfície principal do produto

Capacidades desejadas:

- seleção do workflow principal (`Document Review`, `Policy / Contract Comparison`, `Action Plan / Evidence Review`, `Candidate Review`)
- geração de deck como capability transversal dentro de cada workflow
- preview de inputs grounded
- flow mais claro por deck family

Observação:

- a leitura recomendada passa a ser **Gradio = produto**
- o **Streamlit** pode continuar como dashboard do **AI Lab**

---

## Etapa 3 — App web

Objetivo:

- capability com cara de produto real

Capacidades desejadas:

- catálogo explícito de deck types
- histórico de exports
- múltiplos fluxos de entrada
- melhor operação e governança
