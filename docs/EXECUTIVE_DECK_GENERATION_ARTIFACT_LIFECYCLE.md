# Executive Deck Generation — artifact lifecycle

## Objective

Define how the capability's artifacts should be created, organized, persisted, and tracked.

---

## Export identity

Each execution must generate a unique identifier:

- `export_id`

Exemplo:

- `deckexp_2026_04_05_001`

---

## Suggested remote structure in `ppt_creator_app`

```text
outputs/ai_workbench_exports/
  <export_id>/
    deck.pptx
    previews/
```

---

## Suggested local structure in AI Workbench

```text
artifacts/presentation_exports/
  <export_id>/
    contract.json
    payload.json
    render_response.json
    deck.pptx
    review.json
    preview_manifest.json
    thumbnail_sheet.png
    metadata.json
```

---

## Minimum provenance

Each export must record:

- `export_id`
- `export_kind`
- `contract_version`
- `created_at`
- `source_refs`
- `renderer_base_url`
- `remote_output_path`
- `local_artifact_dir`
- `status`

---

## Lifecycle states

- `created`
- `contract_built`
- `payload_built`
- `render_requested`
- `render_completed`
- `artifacts_downloaded`
- `completed`
- `failed`
- `partial`

---

## Minimum retention policy

### Initial

- keep recent local exports
- do not delete them automatically while the capability is still maturing

### Future

- retention by quantity or age
- explicit administrative cleanup
- extra protection for exports marked as baseline/demo/reference

---

## Acceptable partial failures

Examples:

- `.pptx` generated, but preview not downloaded
- contract and payload saved, but the renderer is unavailable

In these cases, the export must not “disappear”; it should remain marked as `partial` or `failed` with useful metadata.
