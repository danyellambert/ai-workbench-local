# Executive Deck Generation — Candidate Review Deck Contract v1

## Goal

Define the v1 contract for the **Candidate Review Deck**, using the `cv_analysis` and `evidence_cv` tracks as structured input sources.

---

## Contract identity

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "candidate_review_deck"`
- `deck_family = "candidate_review"`

---

## Typical AI Workbench sources

- `cv_analysis`
- `evidence_cv`
- comparison findings between candidates or profiles
- recommendation outputs

---

## High-level structure

```json
{
  "contract_version": "executive_deck_generation.v1",
  "export_kind": "candidate_review_deck",
  "deck_family": "candidate_review",
  "presentation": {
    "title": "Candidate Review",
    "subtitle": "Executive profile summary",
    "author": "AI Workbench Local",
    "date": "2026-04-05",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Candidate Review"
  },
  "candidate_profile": {
    "name": "Candidate Name",
    "headline": "Senior Machine Learning Platform Specialist",
    "location": "Sao Paulo"
  },
  "executive_summary": "Executive summary of the profile, major strengths, and key review points.",
  "strengths": [
    "Strong background in applied AI and system architecture.",
    "Clear combination of product and engineering capabilities."
  ],
  "gaps": [
    "Formal leadership scope is not fully explicit in the source material."
  ],
  "evidence_highlights": [
    {
      "label": "Experience",
      "value": "5+ years",
      "detail": "RAG, structured outputs, evals"
    }
  ],
  "recommendation": "Advance to the next review stage with emphasis on product thinking and technical leadership.",
  "watchouts": [
    "Validate depth in scale and production-oriented environments."
  ],
  "next_steps": [
    "Schedule the next structured review stage.",
    "Validate leadership scope and ownership expectations."
  ],
  "data_sources": [
    "cv_analysis",
    "evidence_cv"
  ]
}
```

---

## Minimum expected slides

1. title / candidate snapshot
2. executive summary
3. strengths
4. gaps / risks
5. evidence highlights
6. recommendation vs watchouts
7. next steps

---

## Minimum rules

- `candidate_profile.name` is required
- `executive_summary` is required
- `recommendation` is required
- either `strengths` or `evidence_highlights` must exist