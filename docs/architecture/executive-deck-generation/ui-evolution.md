# Executive Deck Generation — UI evolution

## Objective

Describe how the capability appears in each stage of the product interface.

---

## Stage 1 — Current Streamlit

Objective:

- prove the functional value of the capability
- serve as a temporary baseline while the product surface is separated from the AI Lab

Minimum capabilities:

- generate P1
- download `.pptx`
- download contract/payload
- view status/warnings

---

## Stage 2 — Gradio

Objective:

- make the demo more AI-first and workflow-oriented
- become the product's main surface

Desired capabilities:

- selection of the main workflow (`Document Review`, `Policy / Contract Comparison`, `Action Plan / Evidence Review`, `Candidate Review`)
- deck generation as a cross-cutting capability within each workflow
- preview of grounded inputs
- clearer flow by deck family

Note:

- the recommended interpretation becomes **Gradio = product**
- **Streamlit** can continue as the **AI Lab** dashboard

---

## Stage 3 — Web app

Objective:

- a capability with the feel of a real product

Desired capabilities:

- explicit deck type catalog
- export history
- multiple input flows
- better operations and governance
