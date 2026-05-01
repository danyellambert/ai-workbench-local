# AI layer

The app keeps the rendering engine and the LLM runtime independent on purpose.

Current boundary:

- `ppt_creator` / `ppt_creator_ai` stay inside the app
- the recommended production boundary for real model execution stays outside the app, behind `local_service`
- the app also exposes `ollama_local` as a first-class local provider for direct local authoring/debugging
- Ollama remains an external dependency, not something bundled into the app container

Practical interpretation:

- **recommended path**: `local_service` for stable app/service separation
- **supported direct local path**: `ollama_local` when you want the app to talk straight to a local Ollama daemon

## Recommended Ollama setup

Use the external service bridge with the local model:

```bash
export PPT_CREATOR_AI_SERVICE_URL=http://127.0.0.1:8788
export PPT_CREATOR_AI_SERVICE_PROVIDER=ollama
export PPT_CREATOR_AI_SERVICE_MODEL=nemotron-3-nano:30b-cloud
export PPT_CREATOR_AI_SERVICE_TIMEOUT_SECONDS=180
```

## Why the app now sends a generation contract

Direct raw prompts to Ollama tend to miss required schema details like slide `type`.

The safer approach is:

1. keep Ollama behind `hf_local_llm_service`
2. call the service through the generic `/v1/generate` boundary
3. send the briefing plus the app's explicit generation contract inside the prompt/request
4. require JSON-only output when the use case is deck generation
5. validate the result with `PresentationInput` inside the app

In other words:

- the **service** serves models and returns raw text/JSON
- the **app** interprets that output as a deck and validates domain schema

## Automated benchmark

The optional AI CLI now includes a benchmark to stress the prompt-to-deck path across multiple scenarios:

```bash
python -m ppt_creator_ai.cli benchmark outputs/ai_benchmark \
  --provider local_service \
  --write-json-decks \
  --report-json outputs/ai_benchmark/report.json
```

This reports:

- valid vs failed generations
- slide-type coverage
- QA review status / issue counts per scenario
- optional persisted deck JSON outputs for inspection

You can also compare providers side by side:

```bash
python -m ppt_creator_ai.cli benchmark outputs/ai_benchmark_compare \
  --provider local_service \
  --compare-provider ollama_local \
  --report-json outputs/ai_benchmark_compare/report.json
```

The comparison report includes:

- per-scenario provider outcomes
- fallback rate per provider
- repair-loop rate per provider
- average issue count per provider

## Repair loop before fallback

Model-backed providers now try a stronger **repair loop** before falling back to the heuristic path.

That means the app will:

1. detect invalid/incomplete JSON or quality-gate failure
2. send repair-oriented feedback back to the model
3. ask for a corrected full JSON object preserving the requested structure
4. only fall back when the repair loop still cannot recover a valid deck