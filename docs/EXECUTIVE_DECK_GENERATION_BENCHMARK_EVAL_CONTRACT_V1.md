# Executive Deck Generation — Benchmark/Eval Executive Review Contract v1

## Objetivo desta entrega

Documentar e iniciar a implementação do primeiro slice técnico da capability de **Executive Deck Generation** entre:

- **AI Workbench Local**
- **`ppt_creator_app`**

> Para a leitura completa de produto, catálogo de decks e roadmap da capability, ver também: `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`

> Para a leitura técnica de productização do primeiro slice no ecossistema atual, ver também: `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`

O foco desta rodada continua sendo o caminho:

**benchmark/eval -> contrato estruturado -> payload compatível com `ppt_creator`**

Este documento deve ser lido como:

- o **P1 técnico** da capability de Executive Deck Generation
- especificamente o deck de **benchmark/eval executive review**

As próximas famílias de decks previstas pela capability maior incluem:

- document review deck
- policy/contract comparison deck
- action plan deck
- candidate review deck
- evidence pack deck

## O que vamos fazer nesta rodada

### Escopo incluído agora

1. criar um **contrato JSON v1** para o slice `benchmark/eval -> executive deck`
2. criar um **builder** que converte agregados do projeto atual em um contrato estável
3. criar um **adapter** que transforma esse contrato em um payload compatível com o schema esperado pelo `ppt_creator`
4. adicionar **testes unitários focados** para garantir estabilidade da fundação

### Escopo explicitamente fora desta rodada

Ainda **não** entra agora:

- chamada HTTP real para o `ppt_creator_app`
- Docker / porta / volume compartilhado
- UI para exportar deck pelo app principal
- fila assíncrona de renderização
- preview real / review remoto / download de artefatos

Esses pontos ficam para o próximo slice, quando o contrato já estiver estável.

## Leitura arquitetural

Nesta fase, a separação fica assim:

- **AI Workbench Local**
  - continua como fonte da verdade dos benchmarks/evals
  - consolida os agregados do domínio
  - gera o contrato intermediário de apresentação
- **`ppt_creator_app`**
  - continua como serviço/renderizador especializado
  - receberá depois um payload já estruturado para `.pptx`

Ou seja: **a fundação entra primeiro no domínio e só depois sobe para API/Docker**.

## Contrato JSON v1

### Nome do contrato

> Nota de honestidade técnica: o slice já implementado em código ainda usa o naming de fundação `presentation_export.v1` / `benchmark_eval_executive_deck`. Isso continua válido como base atual, mesmo com a capability maior agora posicionada como **Executive Deck Generation**.

- `contract_version = "presentation_export.v1"`
- `export_kind = "benchmark_eval_executive_deck"`

### Estrutura de alto nível

```json
{
  "contract_version": "presentation_export.v1",
  "export_kind": "benchmark_eval_executive_deck",
  "presentation": {
    "title": "AI Workbench Local — Benchmark & Eval Review",
    "subtitle": "Resumo executivo da rodada atual",
    "author": "AI Workbench Local",
    "date": "2026-04-04",
    "theme": "executive_premium_minimal",
    "footer_text": "AI Workbench Local • Benchmark & Eval Review"
  },
  "model_comparison_snapshot": {
    "total_runs": 4,
    "total_candidates": 12,
    "success_rate": 0.917,
    "avg_latency_s": 1.284,
    "avg_format_adherence": 0.944,
    "avg_use_case_fit_score": 0.902,
    "top_model": "qwen2.5:7b",
    "top_runtime_bucket": "local"
  },
  "eval_snapshot": {
    "total_runs": 18,
    "pass_rate": 0.778,
    "warn_rate": 0.167,
    "fail_rate": 0.056,
    "avg_score_ratio": 0.912,
    "avg_latency_s": 1.537,
    "needs_review_rate": 0.111,
    "top_suite_name": "structured_real_document_eval"
  },
  "executive_summary": "Top candidate and eval health in one executive package.",
  "key_highlights": [
    "Top benchmark candidate atual: qwen2.5:7b.",
    "PASS rate de eval acima de 75% na rodada atual."
  ],
  "key_metrics": [
    {
      "label": "Benchmark candidates",
      "value": "12",
      "detail": "Top model: qwen2.5:7b"
    }
  ],
  "model_leaderboard": [
    {
      "rank": 1,
      "model": "qwen2.5:7b",
      "provider": "ollama",
      "runtime_bucket": "local",
      "comparison_score": 0.941,
      "avg_latency_s": 1.08,
      "format_adherence": 0.98,
      "use_case_fit_score": 0.93,
      "success_rate": 1.0
    }
  ],
  "eval_suite_leaderboard": [
    {
      "rank": 1,
      "suite_name": "structured_real_document_eval",
      "pass_rate": 1.0,
      "avg_score_ratio": 0.96,
      "avg_latency_s": 1.12,
      "total_runs": 6
    }
  ],
  "recommendation": "Promover o candidato líder para a próxima rodada controlada.",
  "watchouts": [
    "Ainda existem suites em WARN/FAIL que exigem hardening."
  ],
  "next_steps": [
    "Revisar suites WARN/FAIL.",
    "Serializar este contrato e chamar o serviço de decks via API."
  ],
  "data_sources": [
    "phase7_model_comparison_log",
    "phase8_eval_store"
  ]
}
```

## Mapeamento para o `ppt_creator`

O adapter desta rodada vai transformar o contrato acima em um payload de apresentação com os seguintes blocos:

1. `title`
2. `summary`
3. `metrics`
4. `table` de leaderboard de modelos
5. `table` de leaderboard de eval suites
6. `comparison` com recomendação vs watchouts
7. `bullets` com próximos passos

## Por que esse desenho

Esse formato é forte porque:

- preserva um contrato de domínio claro no AI Workbench
- evita acoplar cedo demais o projeto ao schema cru do `ppt_creator`
- já deixa o payload suficientemente próximo do renderizador final
- facilita a próxima etapa de integração por API HTTP

## Próximo slice depois desta entrega

Depois que esse contrato estiver estável e coberto por testes, o próximo passo recomendado é:

1. criar um `presentation_export_service`
2. chamar o `ppt_creator_app` por HTTP
3. externalizar URL/timeouts por configuração
4. decidir estratégia de artefato (`bytes` vs `volume/path`)
5. só então subir o `ppt_creator_app` em Docker como serviço separado

## Documento complementar

Este documento continua propositalmente focado no **primeiro slice técnico** (`benchmark/eval -> contrato -> payload compatível com o renderer`).

Para o processo completo da capability dentro do AI Workbench Local, incluindo:

- posicionamento de produto
- catálogo de famílias de deck
- priorização P1/P2/P3
- boundary arquitetural
- integração HTTP
- UX
- artefatos
- observabilidade
- encaixe na Fase 10.25

consultar:

- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION.md`
- `docs/PHASE_10_25_EXECUTIVE_DECK_GENERATION_PRODUCTIZATION.md`
