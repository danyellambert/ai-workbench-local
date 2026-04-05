# Executive Deck Generation — candidate review deck contract v1

## Objetivo

Definir o contract v1 do **Candidate Review Deck**, aproveitando a trilha `cv_analysis` e `evidence_cv`.

---

## Identidade do contract

- `contract_version = "executive_deck_generation.v1"`
- `export_kind = "candidate_review_deck"`
- `deck_family = "candidate_review"`

---

## Fontes típicas do AI Workbench

- `cv_analysis`
- `evidence_cv`
- comparison findings entre candidatos
- recommendation

---

## Estrutura de alto nível

```json
{
  "contract_version": "executive_deck_generation.v1",
  "export_kind": "candidate_review_deck",
  "deck_family": "candidate_review",
  "presentation": {
    "title": "Candidate Review",
    "subtitle": "Executive hiring summary",
    "author": "AI Workbench Local",
    "date": "2026-04-05",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Candidate Review"
  },
  "candidate_profile": {
    "name": "Candidate Name",
    "headline": "Senior Applied AI Engineer",
    "location": "São Paulo"
  },
  "executive_summary": "Resumo executivo do perfil, principais diferenciais e riscos da candidatura.",
  "strengths": [
    "Experiência forte em IA aplicada e arquitetura.",
    "Boa capacidade de produto e engenharia."
  ],
  "gaps": [
    "Falta detalhe explícito de liderança formal."
  ],
  "evidence_highlights": [
    {
      "label": "Experience",
      "value": "5+ years",
      "detail": "RAG, structured outputs, evals"
    }
  ],
  "recommendation": "Avançar para próxima etapa com foco em product thinking e liderança técnica.",
  "watchouts": [
    "Validar profundidade em escala/produção."
  ],
  "next_steps": [
    "Agendar entrevista técnica.",
    "Validar liderança e ownership."
  ],
  "data_sources": [
    "cv_analysis",
    "evidence_cv"
  ]
}
```

---

## Slides mínimos esperados

1. title / candidate snapshot
2. executive summary
3. strengths
4. gaps / risks
5. evidence highlights
6. recommendation vs watchouts
7. next steps

---

## Regras mínimas

- `candidate_profile.name` é obrigatório
- `executive_summary` é obrigatória
- `recommendation` é obrigatória
- `strengths` ou `evidence_highlights` devem existir
