# Executive Deck Generation — contrato de API

## Objetivo

Definir o contrato de integração entre:

- AI Workbench Local
- `ppt_creator_app`

e antecipar o contrato interno futuro da capability no backend do produto.

---

## API externa atual usada no `ppt_creator_app`

### 1. `GET /health`

Uso:

- verificar disponibilidade do serviço antes do render

Expectativa mínima do AI Workbench:

- HTTP 200 quando o serviço estiver saudável
- falha clara quando o serviço estiver indisponível

### 2. `POST /render`

Uso:

- renderização principal do deck

Payload mínimo esperado:

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

Uso:

- baixar o `.pptx`
- baixar `preview_manifest`
- baixar `thumbnail_sheet`
- baixar artefatos visuais adicionais quando existirem

### 4. `POST /review`

Uso futuro/opcional:

- review explícito do spec ou do deck gerado

### 5. `POST /preview`

Uso futuro/opcional:

- preview explícito quando necessário fora do render principal

---

## Contrato interno futuro do AI Workbench

### Endpoint recomendado

- `POST /api/executive-decks/generate`

Payload conceitual:

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

Resposta conceitual:

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

## Modelo de erros recomendado

Campos padrão:

- `error_type`
- `message`
- `retryable`
- `export_id`
- `service_status`

Tipos principais:

- `service_unavailable`
- `healthcheck_failed`
- `invalid_contract`
- `invalid_renderer_payload`
- `render_failed`
- `artifact_download_failed`
- `timeout`

---

## Timeouts e política de retry

### Healthcheck
- timeout curto
- retry opcional e conservador

### Render
- timeout maior
- retry automático apenas se a operação for comprovadamente segura

### Download de artefato
- retry leve para falhas transitórias

---

## Idempotência e naming

Cada chamada de geração deve produzir um `export_id` explícito.

O `output_path` remoto deve ser derivado desse `export_id` para evitar colisões.
