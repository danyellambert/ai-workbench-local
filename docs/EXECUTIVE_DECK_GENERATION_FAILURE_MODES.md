# Executive Deck Generation — failure modes e fallback strategy

## Objetivo

Definir falhas esperadas e como a capability deve reagir.

---

## Falhas principais

### 1. `service_unavailable`

Situação:

- `ppt_creator_app` offline

Comportamento:

- falhar de forma amigável
- permitir baixar contract/payload quando possível

### 2. `healthcheck_failed`

Situação:

- `GET /health` não responde como esperado

Comportamento:

- bloquear render
- registrar erro operacional

### 3. `invalid_contract`

Situação:

- contract do domínio inconsistente

Comportamento:

- não chamar o renderer
- expor mensagem clara de erro

### 4. `render_failed`

Situação:

- `POST /render` falhou

Comportamento:

- salvar request/response útil para debug
- marcar export como `failed`

### 5. `artifact_download_failed`

Situação:

- render terminou, mas download do `.pptx` falhou

Comportamento:

- marcar export como `partial`

### 6. `preview_failed`

Situação:

- `.pptx` gerado, preview/review não pôde ser baixado

Comportamento:

- manter deck disponível
- marcar warning

---

## Política de partial success

Se o `.pptx` existir, o export não deve ser tratado como perda total, mesmo que previews/review falhem.
