# Executive Deck Generation — quality, grounding, and governance

## Objective

Define the minimum quality and governance policies for the capability.

---

## Main rule

Decks executivos do AI Workbench devem ser **grounded first**.

That means:

- use structured and auditable inputs whenever possible
- avoid free-form generation in the last mile of priority decks
- require evidence for relevant claims

---

## Deterministic vs generative

### Recommended path for P1/P2/P3

- prefer a deterministic path
- structured contract
- structured payload
- specialized renderer

### When to consider a generative layer

Only when there is:

- a clear gain hypothesis
- specific evaluation
- explicit guardrails

---

## `needs_review` policy

A deck should be marked as `needs_review` when there is:

- insufficient evidence
- missing critical data
- inconclusive comparison
- high risk of incorrect interpretation

---

## PII / sensitivity policy

Especially important for:

- CVs
- contracts
- internal documents
- sensitive findings

Minimum direction:

- record the origin of the data
- allow future redaction
- do not treat decks containing PII as disposable artifacts without governance

---

## Rollout policy

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

## Done criteria by deck type

Each deck type should only be promoted to real usage when there is:

1. a documented contract
2. a stable slide recipe
3. minimum tests
4. defined fallback behavior
5. a minimum UX definition
