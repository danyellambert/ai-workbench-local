# Executive Deck Generation — service architecture

## Objective

Describe how the **Executive Deck Generation** capability should be implemented in the current ecosystem.

---

## Architectural principle

### AI Workbench Local

Responsible for:

- grounding
- signal consolidation
- contract assembly
- capability orchestration
- local persistence of artifacts and logs

### `ppt_creator_app`

Responsible for:

- presentation spec validation
- `.pptx` rendering
- visual preview/review
- artifact serving

---

## Main components in AI Workbench

### 1. Contract builders

Responsible for transforming product signals into contracts by `export_kind`.

Existing initial example:

- `src/services/presentation_export.py`

### 2. Renderer adapters

Responsible for transforming a domain contract into a payload compatible with `ppt_creator`.

### 3. `presentation_export_service`

Capability orchestration component.

Responsibilities:

- verify feature flags/config
- verify renderer health
- build the contract
- build the payload
- call the `ppt_creator_app` API
- download artifacts
- persist local copies
- return structured results to the UI/backend

### 4. Local artifact store

Local directory/versioning containing:

- contract
- payload
- render response
- `.pptx`
- related review/previews

### 5. UI integration layer

Layer that exposes the capability to:

- current Streamlit
- future Gradio UI
- future web app

---

## Recommended synchronous flow for P1

1. the user triggers deck generation
2. AI Workbench resolves `export_kind`
3. the builder generates the contract
4. the adapter generates the renderer payload
5. `presentation_export_service` calls `GET /health`
6. `presentation_export_service` calls `POST /render`
7. AI Workbench downloads the `.pptx` via `GET /artifact`
8. AI Workbench persists local artifacts
9. the UI receives structured results and downloads

---

## Recommended architectural evolution

### Phase 1

- synchronous flow
- one primary deck type
- local artifact store

### Phase 2

- multiple `export_kind` values
- export history
- clearer integration with the product HTTP backend

### Phase 3

- asynchronous jobs if needed
- stronger preview/review
- recurrence / scheduled generation

---

## Recommended code boundary

### AI Workbench

Target files/areas:

- `src/services/presentation_export.py` — current builders/adapters
- `src/services/presentation_export_service.py` — new service
- `src/config.py` — capability configuration
- `src/ui/...` — product surface

### `ppt_creator_app`

Reuse the existing endpoints. Avoid moving domain logic into the renderer.

---

## What not to do

- copy the renderer into AI Workbench
- mix deck logic directly into the UI
- couple the domain to the raw renderer schema too early
- use an LLM in the last P1 step when the path can be deterministic
