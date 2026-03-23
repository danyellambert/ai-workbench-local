## Fase 5 — pacote de evidências de funcionamento

Este documento reúne as evidências mais fortes, reprodutíveis e úteis para mostrar que o módulo de **structured outputs** funciona no projeto, alinhado ao roadmap em `proximos_passos.md`.

---

## 1. Evidência automatizada principal

### Smoke eval local mais recente

Comando executado:

```bash
python scripts/run_phase5_structured_eval.py --task all
```

Resultado:

```text
[PASS] extraction: 5/5
[PASS] summary: 5/5
[PASS] checklist: 5/5
[PASS] cv_analysis: 5/5
[PASS] code_analysis: 5/5
```

Relatório gerado:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

Por que essa é a melhor evidência base:

- é **reprodutível**
- cobre as 5 tasks estruturadas da fase
- gera um artefato versionável em JSON
- prova não só JSON válido, mas utilidade mínima por task

---

## 2. O que o smoke eval prova

O relatório mais recente comprova, com `PASS`, que o app consegue executar com sucesso:

1. `extraction`
2. `summary`
3. `checklist`
4. `cv_analysis`
5. `code_analysis`

Isso está alinhado com o objetivo da Fase 5 no roadmap:

- outputs estruturados previsíveis
- validação por schema
- uso como componente integrável, não apenas chat livre

---

## 3. Evidências concretas por task

### 3.1 Extraction

No relatório recente, `extraction` passou com `5/5` e retornou:

- `main_subject`
- `entities`
- `extracted_fields`
- `important_dates`
- `risks`
- `action_items`

Arquivo-evidência:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### 3.2 Summary

`summary` passou com `5/5` e retornou:

- tópicos
- `executive_summary`
- `key_insights`
- `reading_time_minutes`

Arquivo-evidência:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### 3.3 Checklist

`checklist` passou com `5/5` e retornou:

- título
- descrição
- itens estruturados
- prioridade
- dependências
- tempo estimado

Arquivo-evidência:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### 3.4 CV analysis

O smoke eval atual também passou com `5/5` em `cv_analysis` para o fixture textual.

Além disso, existe um caso real salvo para referência:

- `phase5_eval/CV - Lucas -gen.json`

Esse caso real é útil como evidência complementar porque mostra:

- uso do fluxo em um CV real
- saída estruturada com `education_entries` e `experience_entries`
- limites reais do pipeline atual

Limitações honestas observáveis nesse JSON real:

- `full_name` ficou `null`
- `email` saiu truncado (`as.souza-ferreira@student-cs.fr`)
- há duplicidade em `experience_entries`

Isso é bom para portfólio porque permite demonstrar **funcionamento + honestidade técnica**, exatamente como o roadmap pede.

### 3.4.1 Rollout reforçado do `evidence_cv` com gate semântico

Além do smoke eval textual, a fase agora também possui evidência de rollout reforçado do parser `evidence_cv` com:

- guardrails operacionais
- promoção automática por etapas
- semantic gate com CVs mais próximos de casos reais em `data/materials_demo/cv_analysis`

Arquivos-evidência principais:

- `phase5_eval/reports/evidence_cv_auto_rollout_decision.json`
- `phase5_eval/reports/evidence_cv_auto_rollout.log`

Leitura atual mais importante:

- o rollout reforçado terminou sem falhas operacionais críticas
- o gate semântico passou com `3/3` amostras reais/demo contendo nome confirmado
- a correção de nome resolveu os casos `Francis B. Taylor` e `Nathaly Ortiz`, que antes apareciam como `not_found`

Isso fortalece a narrativa da Fase 5 porque o rollout deixa de validar só estabilidade operacional e passa a exigir uma checagem semântica mínima antes de considerar a ativação automática saudável.

### 3.4.2 Nota sobre `sections` vazio em `cv_analysis`

Durante a investigação do rollout reforçado, apareceu um comportamento importante no payload de `cv_analysis`: em alguns casos, `education_entries`, `experience_entries`, `skills` e `languages` vinham preenchidos, mas `sections` podia ficar vazio.

Isso não significava necessariamente ausência de conteúdo útil. O pipeline já conseguia estruturar dados no topo do payload, mas nem sempre o modelo devolvia `sections` preenchido.

Após o hardening recente, a camada de renderização da UI passa a sintetizar seções derivadas de:

- `experience`
- `education`
- `skills`
- `languages`

quando esses blocos existirem no payload mesmo que o modelo não tenha preenchido `sections` diretamente.

Na prática, isso melhora a coerência entre:

- métricas da UI (`Sections`)
- expansores de seção
- campos top-level como `experience_entries` e `education_entries`

### 3.5 Code analysis

`code_analysis` passou com `5/5` e retornou:

- `snippet_summary`
- `main_purpose`
- `detected_issues`
- `refactor_plan`
- `test_suggestions`

Arquivo-evidência:

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

---

## 4. Evidências visuais recomendadas para UI

O projeto já possui um guia explícito para capturas:

- `docs/PHASE_5_UI_EXAMPLES_GUIDE.md`

E também já possui um manifesto de exemplos selecionados:

- `phase5_eval/ui_examples_manifest.json`

Os 4 casos mais fortes para screenshot/documentação são:

1. **textual_pass**
   - PDF: `0001_medium_modern_two_column_gabriel.gomes.almeida.pdf`
   - status: `PASS`

2. **visual_pass**
   - PDF: `0002_hard_compact_sidebar_marina.gomes.ribeiro.pdf`
   - status: `PASS`

3. **scan_warn**
   - PDF: `0004_medium_scan_like_image_pdf_beatriz.barbosa.martins.pdf`
   - status: `WARN`

4. **scan_fail_or_low**
   - PDF: `0009_simple_scan_like_image_pdf_matheus.araujo.carvalho.pdf`
   - status: `FAIL`

Esses quatro exemplos formam o melhor pacote visual porque mostram:

- caso bom textual
- caso bom visualmente denso
- caso parcialmente melhorado com OCR/scan-like
- caso limite ainda difícil

---

## 5. Pacote mínimo recomendado para documentar depois

Se o objetivo for montar README, docs ou post de LinkedIn depois, o pacote mínimo mais forte é:

### A. Evidência automatizada

- `phase5_eval/reports/phase5_structured_eval_20260319_082813.json`

### B. Evidência real complementar

- `phase5_eval/CV - Lucas -gen.json`

### C. Evidência visual da UI

- 2 screenshots de casos `PASS`
- 1 screenshot de `WARN` scan-like
- 1 screenshot de caso limite

### D. Seleção pronta dos casos visuais

- `phase5_eval/ui_examples_manifest.json`
- `docs/PHASE_5_UI_EXAMPLES_GUIDE.md`

---

## 6. Como eu recomendaria apresentar isso na documentação

### Versão curta

> A Fase 5 foi validada por um smoke eval local reprodutível cobrindo `extraction`, `summary`, `checklist`, `cv_analysis` e `code_analysis`, todos com `PASS`. Além disso, o projeto mantém exemplos reais e um conjunto curado de casos de UI para demonstrar sucesso em documentos textuais, comportamento parcial em scan-like e limites conhecidos do pipeline.

### Versão mais forte para portfólio

> O módulo de structured outputs não foi avaliado só por “parece funcionar”. Ele possui smoke eval automatizado, casos reais versionados, exemplos de UI selecionados e documentação explícita de limites. Isso permite demonstrar previsibilidade, validação por schema e maturidade de engenharia na transição de chat livre para saídas integráveis.

---

## 7. Comandos curtos para reproduzir as evidências

Rodar a smoke eval completa:

```bash
python scripts/run_phase5_structured_eval.py --task all
```

Abrir o relatório recente:

```bash
code phase5_eval/reports/phase5_structured_eval_20260319_082813.json
```

Abrir o caso real do Lucas:

```bash
code "phase5_eval/CV - Lucas -gen.json"
```

Abrir o guia de screenshots da fase:

```bash
code docs/PHASE_5_UI_EXAMPLES_GUIDE.md
```

---

## 8. Conclusão

Hoje, a melhor evidência de que o aplicativo de estruturado funciona é a combinação de:

1. **smoke eval automatizado com PASS em todas as tasks**
2. **artefato JSON versionado do relatório**
3. **caso real versionado (`CV - Lucas -gen.json`)**
4. **manifesto de exemplos de UI para screenshots reprodutíveis**

Esse conjunto é o mais alinhado ao roadmap porque entrega exatamente o que a fase ainda pede para fechar: **evidências reais, screenshots, mini demo e documentação honesta dos limites atuais**.