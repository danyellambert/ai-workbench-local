# Executive Deck Generation — rollout e governança

## Objetivo

Definir como a capability cresce com controle.

---

## Fases de rollout

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

## Critério para liberar novo deck type

Cada novo deck type deve ter:

1. contract documentado
2. slide recipe definida
3. service mapping definido
4. UX mínima definida
5. testes mínimos definidos

---

## Feature flags recomendadas

- capability global on/off
- enable por `export_kind`
- review/previews opcionais

## Estado atual das feature flags

- capability global on/off — **implementado** via `PRESENTATION_EXPORT_ENABLED`
- review/previews opcionais — **implementado** via `PRESENTATION_EXPORT_INCLUDE_REVIEW`, `PRESENTATION_EXPORT_PREVIEW_BACKEND`, `PRESENTATION_EXPORT_REQUIRE_REAL_PREVIEWS` e `PRESENTATION_EXPORT_FAIL_ON_REGRESSION`
- enable por `export_kind` — **implementado** via `PRESENTATION_EXPORT_ENABLED_EXPORT_KINDS`

Exemplo:

```env
PRESENTATION_EXPORT_ENABLED_EXPORT_KINDS=benchmark_eval_executive_review,document_review_deck
```

Observação:

- o service aceita tanto o alias de produto `benchmark_eval_executive_review` quanto o naming legado compatível `benchmark_eval_executive_deck`

---

## Governança de naming legado

O naming legado do P1 deve permanecer compatível até migração explícita.
