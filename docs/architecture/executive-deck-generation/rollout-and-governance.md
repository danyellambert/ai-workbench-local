# Executive Deck Generation — rollout and governance

## Objective

Define how the capability grows in a controlled way.

---

## Rollout phases

### P1
- benchmark/eval executive review

### P2
- document review
- policy/contract comparison

### P3
- action plan
- candidate review
- evidence pack

---

## Criteria to release a new deck type

Each new deck type must have:

1. a documented contract
2. a defined slide recipe
3. a defined service mapping
4. a minimum UX definition
5. minimum tests defined

---

## Recommended feature flags

- capability global on/off
- enable por `export_kind`
- review/previews opcionais

## Current feature-flag status

- global capability on/off — **implemented** via `PRESENTATION_EXPORT_ENABLED`
- optional review/previews — **implemented** via `PRESENTATION_EXPORT_INCLUDE_REVIEW`, `PRESENTATION_EXPORT_PREVIEW_BACKEND`, `PRESENTATION_EXPORT_REQUIRE_REAL_PREVIEWS`, and `PRESENTATION_EXPORT_FAIL_ON_REGRESSION`
- enablement by `export_kind` — **implemented** via `PRESENTATION_EXPORT_ENABLED_EXPORT_KINDS`

Exemplo:

```env
PRESENTATION_EXPORT_ENABLED_EXPORT_KINDS=benchmark_eval_executive_review,document_review_deck
```

Note:

- the service accepts both the product alias `benchmark_eval_executive_review` and the compatible legacy naming `benchmark_eval_executive_deck`

---

## Legacy naming governance

The P1 legacy naming must remain compatible until an explicit migration happens.
