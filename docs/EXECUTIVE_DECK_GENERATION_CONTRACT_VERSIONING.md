# Executive Deck Generation — contract versioning and naming

## Objective

Define how to version and name the capability's contracts.

---

## Main conventions

### `contract_version`

Recommended direction for the capability:

- `executive_deck_generation.v1`

### `export_kind`

It should be:

- stable
- descriptive
- in `snake_case`
- aligned with the deck's objective

Examples:

- `benchmark_eval_executive_review`
- `document_review_deck`
- `policy_contract_comparison_deck`

---

## P1 legacy naming

The first slice already implemented in the repository uses:

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

This should be treated as:

- **compatible legacy naming**
- an already existing technical base
- still acceptable until an explicit migration happens

---

## Versioning rules

### Compatible change

It may keep the same major version when there is:

- a new optional field
- documentation improvement
- expansion without breaking existing consumers

### Incompatible change

It must bump the major version when there is:

- renaming of required fields
- removal of consumed fields
- structural change in the contract's semantics

---

## Future P1 migration policy

When P1 is migrated to the official naming, the recommended direction is:

- keep a read alias for the legacy naming
- document explicit deprecation
- remove compatibility only after the service is stable
