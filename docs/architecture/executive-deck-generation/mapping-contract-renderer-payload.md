# Executive Deck Generation — mapping contract -> renderer payload

## Objective

Define how the capability's semantic contracts should be converted into `ppt_creator` payloads.

---

## Base mapping

### Presentation metadata

Map directly:

- `presentation.title`
- `presentation.subtitle`
- `presentation.author`
- `presentation.date`
- `presentation.theme`
- `presentation.footer_text`

### Semantic blocks -> slide types

| semantic block | preferred slide type |
|---|---|
| cover | `title` |
| executive summary | `summary` or `bullets` |
| metrics | `metrics` |
| leaderboard / structured findings | `table` |
| recommendation vs watchouts | `comparison` |
| next steps | `bullets` |
| timeline / action plan | `timeline` |
| workstreams / highlights | `cards` |

---

## Truncation rules

- avoid excessively long paragraphs in `summary`
- limit bullets to a reasonable executive quantity
- use `table` when comparative reading is more important than narrative flow

---

## Fallback rules

- if data is missing for `metrics`, downgrade to `bullets`
- if data is missing for `comparison`, use `bullets` with simple semantic separation
- if `timeline` is missing, use `table` or ordered `bullets`

---

## Speaker notes

Initial recommendation:

- always record the source context of the slide when useful
- use notes for provenance and presentation guidance, not for raw data dumping
