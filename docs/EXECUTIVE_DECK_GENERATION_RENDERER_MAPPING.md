# Executive Deck Generation — mapping contract -> renderer payload

## Objetivo

Definir como os contracts semânticos da capability devem ser convertidos em payload do `ppt_creator`.

---

## Mapeamento base

### Presentation metadata

Mapear diretamente:

- `presentation.title`
- `presentation.subtitle`
- `presentation.author`
- `presentation.date`
- `presentation.theme`
- `presentation.footer_text`

### Blocos semânticos -> tipos de slide

| bloco semântico | slide type preferido |
|---|---|
| capa | `title` |
| resumo executivo | `summary` ou `bullets` |
| métricas | `metrics` |
| leaderboard / findings estruturados | `table` |
| recommendation vs watchouts | `comparison` |
| próximos passos | `bullets` |
| timeline / plano de ação | `timeline` |
| workstreams / highlights | `cards` |

---

## Regras de truncamento

- evitar parágrafos excessivamente longos em `summary`
- limitar bullets a quantidade executiva razoável
- usar `table` quando a leitura comparativa for mais importante que narrativa corrida

---

## Regras de fallback

- se faltar dado para `metrics`, rebaixar para `bullets`
- se faltar dado para `comparison`, usar `bullets` com separação semântica simples
- se faltar `timeline`, usar `table` ou `bullets` ordenados

---

## Speaker notes

Recomendação inicial:

- sempre registrar contexto de origem do slide quando útil
- usar notes para provenance e guidance de apresentação, não para despejo bruto de dados
