# Executive Deck Generation — failure modes and fallback strategy

## Objective

Define expected failures and how the capability should react.

---

## Main failure modes

### 1. `service_unavailable`

Situation:

- `ppt_creator_app` offline

Behavior:

- fail gracefully
- allow downloading the contract/payload when possible

### 2. `healthcheck_failed`

Situation:

- `GET /health` does not respond as expected

Behavior:

- block rendering
- record an operational error

### 3. `invalid_contract`

Situation:

- inconsistent domain contract

Behavior:

- do not call the renderer
- expose a clear error message

### 4. `render_failed`

Situation:

- `POST /render` failed

Behavior:

- save useful request/response data for debugging
- mark the export as `failed`

### 5. `artifact_download_failed`

Situation:

- rendering finished, but the `.pptx` download failed

Behavior:

- mark the export as `partial`

### 6. `preview_failed`

Situation:

- `.pptx` was generated, but the preview/review could not be downloaded

Behavior:

- keep the deck available
- mark a warning

---

## Partial-success policy

If the `.pptx` exists, the export should not be treated as a total loss, even if previews/review fail.
