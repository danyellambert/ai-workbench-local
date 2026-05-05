# Executive Deck Generation — routing and deck-type selection

## Objective

Define how the product decides **which deck type to suggest, allow, or block** in each workflow.

---

## Selection modes

### 1. Explicit user selection

Preferred mode for early versions.

The user chooses directly:

- benchmark/eval executive review
- document review
- policy/contract comparison
- action plan
- candidate review
- evidence pack

### 2. Automatic suggestion based on the active workflow

The system may suggest a default deck based on the current workflow, but without hiding the user's choice.

### 3. Blocking due to insufficient grounding

If the required signals do not exist, the product should block deck generation or mark it as `needs_review`.

---

## Workflow routing rules

| workflow/source | suggested deck | minimum condition |
|---|---|---|
| benchmark + evals | `benchmark_eval_executive_review` | aggregated leaderboards + snapshots available |
| summary/extraction on a single document | `document_review_deck` | summary + minimum findings/recommendations |
| document comparison | `policy_contract_comparison_deck` | diff/comparison rows available |
| checklist + owners + due dates | `action_plan_deck` | structured action items |
| `cv_analysis` / evidence_cv | `candidate_review_deck` | profile + strengths/gaps/recommendation |
| EvidenceOps / audit review | `evidence_pack_deck` | findings + evidence items + actions |

---

## Blocking policy

The deck **must not** be generated automatically when any of these critical items is missing:

- missing recommendation in a decision deck
- missing comparison rows in a comparison deck
- missing action items in an action-plan deck
- missing evidence items in an evidence-pack deck

In those cases, the UI should:

- explain why generation was blocked
- offer download of the raw JSON/result if useful

---

## `needs_review` policy

Even when generation is allowed, the deck should carry `needs_review` if:

- grounding is partial
- the recommendation depends on ambiguous interpretation
- there is sensitive or incomplete data
