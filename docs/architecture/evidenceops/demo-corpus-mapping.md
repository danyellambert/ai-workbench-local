# Phase 9.5 — Official demo corpus mapping

## Official decision

The official corpus for the Phase 9.5 demo is now:

- **`data/corpus_revisado/option_b_synthetic_premium`**

The complementary/canonical public validation corpus remains:

- **`data/corpus_revisado/option_a_public_corpus_v2`**

## Role of each corpus

### `option_b_synthetic_premium`

Use as the primary base for:

- the `EvidenceOps MCP` demo
- policy comparison
- `contract gap detection`
- `compliance review`
- `evidence chaining`
- `remediation workflow`

### `option_a_public_corpus_v2`

Use as a complementary base for:

- benchmarking with real public artifacts
- external/canonical validation
- public references and frameworks
- comparison of document realism

## Mapping for external adapters

### Nextcloud / WebDAV

Primarily upload:

- `policies/`
- `contracts/`
- `audit/`
- `templates/`
- `metadata/`

Suggested remote structure:

- `/EvidenceOpsDemo/policies`
- `/EvidenceOpsDemo/contracts`
- `/EvidenceOpsDemo/audit`
- `/EvidenceOpsDemo/templates`
- `/EvidenceOpsDemo/metadata`

### Trello

Use the `storylines` as the base operational cards:

- `SB-01` Policy Change Detection
- `SB-02` Contract Gap Detection
- `SB-03` Compliance Review
- `SB-04` Evidence Chaining and NCR Escalation
- `SB-05` Remediation Workflow and Closure Readiness

Suggested lists:

- `Open`
- `Review`
- `Approved`
- `Done`

### Notion

Use as the register/dashboards for:

- storylines
- document register
- evidence packs / findings / actions

## Practical criterion

If the project needs to choose a single corpus for the enterprise demo of Phase 9.5, use:

- **`option_b_synthetic_premium`**

If it needs to be complemented with public/realistic sources, use:

- **`option_a_public_corpus_v2`**