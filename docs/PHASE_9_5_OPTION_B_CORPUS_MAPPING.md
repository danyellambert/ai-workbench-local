# Phase 9.5 — Official demo corpus mapping

## Decisão oficial

O corpus oficial da demo da Fase 9.5 passa a ser:

- **`data/corpus_revisado/option_b_synthetic_premium`**

O corpus complementar/canônico de validação pública continua sendo:

- **`data/corpus_revisado/option_a_public_corpus_v2`**

## Papel de cada corpus

### `option_b_synthetic_premium`

Usar como base principal para:

- demo do `EvidenceOps MCP`
- comparação de policies
- `contract gap detection`
- `compliance review`
- `evidence chaining`
- `remediation workflow`

### `option_a_public_corpus_v2`

Usar como base complementar para:

- benchmark com artefatos públicos reais
- validação externa/canônica
- referências e frameworks públicos
- comparação de realismo documental

## Mapeamento para adapters externos

### Nextcloud / WebDAV

Subir principalmente:

- `policies/`
- `contracts/`
- `audit/`
- `templates/`
- `metadata/`

Estrutura remota sugerida:

- `/EvidenceOpsDemo/policies`
- `/EvidenceOpsDemo/contracts`
- `/EvidenceOpsDemo/audit`
- `/EvidenceOpsDemo/templates`
- `/EvidenceOpsDemo/metadata`

### Trello

Usar as `storylines` como cards-base de operação:

- `SB-01` Policy Change Detection
- `SB-02` Contract Gap Detection
- `SB-03` Compliance Review
- `SB-04` Evidence Chaining and NCR Escalation
- `SB-05` Remediation Workflow and Closure Readiness

Listas sugeridas:

- `Open`
- `Review`
- `Approved`
- `Done`

### Notion

Usar como register/dashboards de:

- storylines
- document register
- evidence packs / findings / actions

## Critério prático

Se o projeto precisar escolher um único corpus para a demo empresarial da Fase 9.5, usar:

- **`option_b_synthetic_premium`**

Se precisar complementar com fontes públicas/realistas, usar:

- **`option_a_public_corpus_v2`**