# Executive Deck Generation — lifecycle de artefatos

## Objetivo

Definir como os artefatos da capability devem ser criados, organizados, persistidos e rastreados.

---

## Identidade do export

Cada execução deve gerar um identificador único:

- `export_id`

Exemplo:

- `deckexp_2026_04_05_001`

---

## Estrutura remota sugerida no `ppt_creator_app`

```text
outputs/ai_workbench_exports/
  <export_id>/
    deck.pptx
    previews/
```

---

## Estrutura local sugerida no AI Workbench

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

## Proveniência mínima

Cada export deve registrar:

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

## Estados do lifecycle

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

## Política mínima de retenção

### Inicial

- manter exports locais recentes
- não apagar automaticamente enquanto a capability estiver amadurecendo

### Futuro

- retenção por quantidade ou idade
- limpeza administrativa explícita
- proteção extra para exports marcados como baseline/demo/reference

---

## Falhas parciais aceitáveis

Exemplos:

- `.pptx` gerado, mas preview não baixado
- contrato e payload salvos, mas renderer indisponível

Nesses casos, o export não deve “sumir”; ele deve ficar marcado como `partial` ou `failed` com metadados úteis.
