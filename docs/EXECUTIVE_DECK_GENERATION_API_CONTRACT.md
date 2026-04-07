# Executive Deck Generation — API contract

## Objective

Define the integration contract between:

- AI Workbench Local
- `ppt_creator_app`

and anticipate the capability's future internal contract in the product backend.

---

## Current external API used in `ppt_creator_app`

### 1. `GET /health`

Usage:

- verify service availability before rendering

Minimum expectation for AI Workbench:

- HTTP 200 when the service is healthy
- a clear failure when the service is unavailable

### 2. `POST /render`

Usage:

- main deck rendering

Minimum expected payload:

```json
{
  "spec": {
    "presentation": {},
    "slides": []
  },
  "output_path": "outputs/ai_workbench_exports/<export_id>/deck.pptx",
  "include_review": true,
  "preview_output_dir": "outputs/ai_workbench_exports/<export_id>/previews",
  "preview_backend": "auto",
  "preview_require_real": false,
  "preview_fail_on_regression": false
}
```

### 3. `GET /artifact`

Usage:

- download the `.pptx`
- download `preview_manifest`
- download `thumbnail_sheet`
- download additional visual artifacts when they exist

### 4. `POST /review`

Future/optional usage:

- explicit review of the spec or the generated deck

### 5. `POST /preview`

Future/optional usage:

- explicit preview when needed outside the main render flow

---

## Future internal AI Workbench contract

### Recommended endpoint

- `POST /api/executive-decks/generate`

Conceptual payload:

```json
{
  "export_kind": "benchmark_eval_executive_review",
  "input_ref": {
    "source": "phase7_phase8_latest"
  },
  "options": {
    "include_review": true,
    "generate_previews": true
  }
}
```

Conceptual response:

```json
{
  "export_id": "exp_20260405_001",
  "status": "completed",
  "export_kind": "benchmark_eval_executive_review",
  "artifact_paths": {
    "pptx": "artifacts/presentation_exports/exp_20260405_001/deck.pptx",
    "contract": "artifacts/presentation_exports/exp_20260405_001/contract.json",
    "payload": "artifacts/presentation_exports/exp_20260405_001/payload.json"
  },
  "warnings": []
}
```

---

## Recommended error model

Standard fields:

- `error_type`
- `message`
- `retryable`
- `export_id`
- `service_status`

Main types:

- `service_unavailable`
- `healthcheck_failed`
- `invalid_contract`
- `invalid_renderer_payload`
- `render_failed`
- `artifact_download_failed`
- `timeout`

---

## Timeouts and retry policy

### Healthcheck
- short timeout
- optional and conservative retry

### Render
- longer timeout
- automatic retry only if the operation is proven safe

### Download de artefato
- lightweight retry for transient failures

---

## Idempotency and naming

Each generation call must produce an explicit `export_id`.

The remote `output_path` should be derived from that `export_id` to avoid collisions.
