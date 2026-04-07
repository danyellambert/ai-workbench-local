# Executive Deck Generation — observability

## Objective

Define what the capability should record so it becomes auditable and defensible.

---

## Minimum metrics per export

- `export_id`
- `export_kind`
- `contract_version`
- `status`
- `render_latency_s`
- `artifact_download_latency_s`
- `pptx_size_bytes`
- `preview_count`
- `service_available`
- `error_type`

---

## Main events

- export created
- contract generated
- payload generated
- renderer called
- render completed
- artifacts downloaded
- export failed
- partial export

---

## Operational objective

Make it possible to answer:

- how many decks were generated
- which deck types fail most often
- which stage fails most often
- how long each export takes
