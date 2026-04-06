# Executive Deck Generation — estratégia de testes

## Objetivo

Definir a estratégia mínima de testes para a capability.

---

## Camadas de teste

## 1. Unit tests de builders e adapters

Cobrir:

- contract builders
- payload adapters
- validação de campos obrigatórios

Situação atual:

- builders e adapters do P1/P2/P3 já possuem cobertura em `tests/test_presentation_export_unittest.py`

---

## 2. Service tests

Arquivo sugerido:

- `tests/test_presentation_export_service_unittest.py`

Cobrir:

- healthcheck
- render request
- timeouts
- artifact downloads
- persistência local
- falhas parciais

Situação atual:

- `tests/test_presentation_export_service_unittest.py` já cobre o P1
- o mesmo arquivo agora também cobre os deck types `document_review_deck`, `policy_contract_comparison_deck`, `action_plan_deck`, `candidate_review_deck` e `evidence_pack_deck`
- também existe cobertura para alias de naming do P1 e feature flag por `export_kind`

---

## 3. Contract tests por deck type

Cada contract v1 novo deve ter testes focados:

- `document_review_deck`
- `policy_contract_comparison_deck`
- `action_plan_deck`
- `candidate_review_deck`
- `evidence_pack_deck`

Situação atual:

- esses deck types já possuem cobertura unitária de builder/adapter em `tests/test_presentation_export_unittest.py`

---

## 4. Smoke tests com `ppt_creator_app`

Testes opcionais/reproduzíveis localmente:

- serviço sobe
- `GET /health` responde
- `POST /render` responde
- `.pptx` é baixado com sucesso

Situação atual:

- ainda pendente como smoke/integration test manual reproduzível com o `ppt_creator_app` rodando de verdade

---

## 5. UI smoke tests

Cobrir:

- presença do entrypoint da capability
- botão de geração
- estado de loading
- erro amigável
- downloads presentes quando sucesso

Situação atual:

- a UI Streamlit já expõe seleção de deck type, geração e downloads
- smoke tests específicos da capability ainda seguem como trilha pendente

---

## 6. Artefatos e regressão

Para evolução posterior:

- golden payloads por deck type
- comparação de manifest/review response
- opcionalmente regressão visual reaproveitando capacidades do `ppt_creator_app`

---

## Critério mínimo para considerar um deck type testado

Um deck type só deve ser tratado como implementado quando houver:

1. unit test do contract builder
2. unit test do payload adapter
3. service test do fluxo de geração
4. smoke/integration test local reproduzível

## Estado atual resumido

- **já feito:** unit tests de builders/adapters multi-deck
- **já feito:** service tests do fluxo de geração para os deck types atualmente suportados
- **ainda faltando:** smoke test real com `ppt_creator_app` e smoke tests específicos da UI da capability
