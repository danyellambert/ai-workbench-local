# Fase 4.5 — validação técnica e fechamento prático

Este documento registra o que já foi efetivamente validado na Fase 4.5 e o que ainda depende de benchmark comparativo local.

## O que foi fechado nesta rodada

- Chroma local como backend vetorial persistente sincronizado com o JSON canônico, com fallback seguro para store local
- clear físico da pasta `.chroma_rag/` quando o índice é limpo
- UX refinada para indexação e reindexação seletiva dos uploads atuais
- remoção em lote de documentos indexados
- debug leve de retrieval
- reranking híbrido leve (vetorial + lexical) antes da seleção final dos chunks
- budget operacional do prompt para limitar o contexto documental antes da geração
- caminho nativo do Ollama em `/api/chat` para parâmetros avançados como `num_ctx`
- painel de inspeção técnica do contexto do Ollama no app
- documentação do estado real da Fase 4.5 no `README.md` e no `proximos_passos.md`

## Validação técnica automatizada

O projeto agora inclui o script:

```bash
python scripts/validate_phase_4_5.py
```

Esse script valida automaticamente:

1. indexação multi-arquivo
2. filtros por documento e tipo
3. remoção seletiva
4. sincronização total entre JSON local e Chroma persistido
5. clear físico do persist dir do Chroma
6. geração de metadados de fontes
7. reranking híbrido com candidate pool explícito
8. limitação do contexto por budget operacional do prompt
9. envio de `num_ctx` no payload nativo do Ollama
10. inspeção técnica combinando `/api/chat`, `/api/show` e `ollama ps`
11. exposição explícita do backend vetorial usado no retrieval

## Evidência técnica mínima esperada

Ao rodar o script, a saída esperada deve conter algo próximo de:

```text
[ok] Fluxo RAG multi-arquivo validado com Chroma, reranking híbrido, budget de contexto e clear físico.
[ok] Caminho nativo do Ollama validado com envio de num_ctx e inspeção técnica.
[ok] Fase 4.5: validação técnica automatizada concluída.
```

## Como fechar a validação prática local

Além do script, o fechamento prático ideal desta fase deve incluir uma rodada manual no app:

```bash
streamlit run main_qwen.py
```

Checklist recomendado:

- indexar 2 ou mais documentos diferentes
- usar o filtro por documento e por tipo
- remover documentos em lote sem limpar toda a base
- reindexar apenas os uploads atuais ao mudar `chunk_size` ou `chunk_overlap`
- confirmar que `Limpar índice` apaga o JSON local e remove a pasta `.chroma_rag/`
- abrir o painel **Validação de contexto do Ollama**
- abrir o debug de retrieval e confirmar:
  - backend vetorial usado (`chroma` ou `local_fallback`)
  - candidate pool do reranking
  - budget operacional do prompt
  - quantos chunks entraram de fato no contexto final

## O que ainda continua em aberto na Fase 4.5

Esses itens não devem ser marcados como completamente encerrados só por causa desta validação:

- comparação prática entre embeddings (`bge-m3` vs alternativas)
- benchmark fino de retrieval/performance com screenshots e evidência de portfólio

Para ajudar nessa rodada prática, o projeto agora inclui também:

```bash
python scripts/compare_phase_4_5_configs.py --output docs/phase_4_5_eval_template.json
```

Esse helper gera um template local para você registrar as perguntas fixas, os runs comparados e as evidências da comparação prática.

## Como defender essa fase em entrevista

A narrativa mais forte agora é:

- o projeto saiu de um RAG simples para uma base documental operacional
- a UX já suporta operações reais de manutenção do índice
- o retrieval deixou de depender só do ranking vetorial bruto
- o prompt passou a ter budget operacional explícito para reduzir excesso de contexto
- o caminho nativo do Ollama foi adotado quando o projeto passou a exigir controle fino de contexto
- a validação publicada é técnica e operacional; ela não vende uma certeza impossível sobre o runtime interno
- a validação não depende só de percepção visual; existe checagem técnica explícita e roteiro de evidência prática
