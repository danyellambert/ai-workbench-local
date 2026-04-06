# Executive Deck Generation — observabilidade

## Objetivo

Definir o que a capability deve registrar para ficar auditável e defendível.

---

## Métricas mínimas por export

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

## Eventos principais

- export criado
- contract gerado
- payload gerado
- renderer chamado
- render concluído
- artefatos baixados
- export falhou
- export parcial

---

## Objetivo operacional

Permitir responder:

- quantos decks foram gerados
- quais deck types mais falham
- qual etapa mais falha
- quanto tempo cada export leva
