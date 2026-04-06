# Executive Deck Generation — qualidade, grounding e governança

## Objetivo

Definir as políticas mínimas de qualidade e governança da capability.

---

## Regra principal

Decks executivos do AI Workbench devem ser **grounded first**.

Isso significa:

- usar inputs estruturados e auditáveis quando possível
- evitar geração livre na última milha dos decks prioritários
- exigir evidência para claims relevantes

---

## Determinístico vs generativo

### Caminho recomendado para P1/P2/P3

- preferir caminho determinístico
- contract estruturado
- payload estruturado
- renderizador especializado

### Quando considerar camada generativa

Somente quando houver:

- hipótese clara de ganho
- avaliação específica
- guardrails explícitos

---

## Policy de `needs_review`

Um deck deve ser marcado como `needs_review` quando houver:

- falta de evidência suficiente
- dados críticos ausentes
- comparação inconclusiva
- risco alto de interpretação errada

---

## Policy de PII / sensibilidade

Especialmente importante para:

- CVs
- contratos
- documentos internos
- findings sensíveis

Direção mínima:

- registrar origem do dado
- permitir redaction no futuro
- não tratar decks contendo PII como artefatos descartáveis sem governança

---

## Policy de rollout

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

## Critério de done por deck type

Cada deck type só deve ser promovido para uso real quando houver:

1. contract documentado
2. slide recipe estável
3. testes mínimos
4. fallback behavior definido
5. UX mínima definida
