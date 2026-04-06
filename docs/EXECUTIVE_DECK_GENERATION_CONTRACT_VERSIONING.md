# Executive Deck Generation — versionamento e naming de contracts

## Objetivo

Definir como versionar e nomear contracts da capability.

---

## Convenções principais

### `contract_version`

Direção recomendada para a capability:

- `executive_deck_generation.v1`

### `export_kind`

Deve ser:

- estável
- descritivo
- em `snake_case`
- orientado ao objetivo do deck

Exemplos:

- `benchmark_eval_executive_review`
- `document_review_deck`
- `policy_contract_comparison_deck`

---

## Naming legado do P1

O primeiro slice já implementado no repositório usa:

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

Isso deve ser tratado como:

- **naming legado compatível**
- base técnica já existente
- ainda aceitável até a migração explícita

---

## Regras de versionamento

### Mudança compatível

Pode manter a mesma major version quando houver:

- campo opcional novo
- melhoria documental
- expansão sem quebrar consumers existentes

### Mudança incompatível

Deve subir major version quando houver:

- renomeação de campos obrigatórios
- remoção de campos consumidos
- mudança estrutural na semântica do contract

---

## Policy de migração futura do P1

Quando o P1 for migrado para o naming oficial, a direção recomendada é:

- manter alias de leitura do naming legado
- documentar depreciação explícita
- só remover compatibilidade depois de estabilização do service
