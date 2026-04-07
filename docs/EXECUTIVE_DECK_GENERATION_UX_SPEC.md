# Executive Deck Generation — UX spec

## Objective

Define how the capability should appear to the user in the product.

---

## UX principle

In the interface, this should appear as an AI Workbench capability, not as a separate project.

Recommended naming:

- **Executive Deck Generation**
- **Generate executive deck**
- **Business review decks**

Avoid:

- “use ppt_creator_app”
- “open the PPT app”

---

## Minimum P1 UX in the current app

### Input

The user should be able to:

- trigger generation of the `Benchmark & Eval Executive Review Deck`

### Minimum actions

- generate the deck
- download `.pptx`
- download contract JSON
- download payload JSON
- view operation status
- view failures and warnings

### Expected feedback

- `Generating contract...`
- `Calling renderer...`
- `Downloading artifacts...`
- `Deck ready for download`

---

## Future UX of the capability

### Deck-type selection

The user will be able to choose among:

- benchmark/eval review
- document review
- comparison deck
- action plan
- candidate review
- evidence pack

### History

The product should display:

- recent exports
- status
- deck type
- date/time
- available downloads

### Future workflow-based inputs

- from the benchmark/eval workflow
- from the document-review workflow
- from the comparison workflow
- from the CV-analysis workflow

---

## Interface progression

### Current Streamlit

- first functional UX
- focus on capability and downloads

### Gradio

- a more AI-first showcase
- a clearer flow by deck type

### App web

- explicit deck-type catalog
- export history
- workflows closer to a real product
