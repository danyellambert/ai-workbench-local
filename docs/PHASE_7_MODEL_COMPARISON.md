## Phase 7 — Model Comparison and Benchmarking

### Goal

Close the local/technical benchmarking phase with a reusable comparison layer that goes beyond side-by-side output inspection.

### What was delivered

- Streamlit comparison workflow for multiple `provider/model` candidates on the same prompt
- execution metrics per candidate:
  - `latency_s`
  - `output_chars`
  - `output_words`
  - `format_adherence`
  - `groundedness_score` (heuristic, when documents are used)
  - `schema_adherence` (heuristic, especially for JSON / structured extraction)
  - `use_case_fit_score` (heuristic fit to the selected benchmark preset)
  - `used_chunks`
- consolidated ranking per run via `comparison_score`
- local audit log in `.phase7_model_comparison_log.json`
- aggregated leaderboards in the Phase 7 log/report by:
  - provider
  - model
  - response format
  - runtime bucket (`local`, `cloud`, `experimental_local`)
  - quantization family (`q4`, `q8`, `int4`, `fp16`, `cloud_managed`, etc.)
  - retrieval strategy
  - embedding provider
  - embedding model
  - prompt profile
  - benchmark use case preset
  - document usage (`with_documents`, `without_documents`)
- explicit reuse of adjacent benchmark evidence:
  - retrieval shadow (`manual_hybrid` vs `langchain_chroma`)
  - structured execution shadow (`direct` vs `langgraph_context_retry`)

### Benchmark presets by use case

Phase 7 now supports repeatable benchmark presets for common workloads:

- `executive_summary`
- `risk_review`
- `policy_compliance`
- `structured_extraction`
- `technical_review`
- `ad_hoc`

This helps avoid benchmark drift caused by arbitrary prompts and makes the benchmark layer easier to reproduce and reason about.

### Quantization interpretation

Phase 7 now classifies model names into quantization families whenever the runtime/model naming exposes them, such as:

- `q4`, `q8`
- `int4`, `int8`
- `fp16`, `fp32`
- `cloud_managed`

This is a practical local benchmark layer, not a guarantee that every environment already contains all quantized variants.

### Runtime interpretation

The project now distinguishes benchmark candidates by runtime bucket:

- `local`: normal local runtime, mainly Ollama-hosted local models
- `cloud`: cloud or cloud-like routed models
- `experimental_local`: experimental local runtime through Hugging Face/Transformers

This makes the benchmark more rigorous because it separates:

- model quality
- runtime class
- operational trade-offs

### Current benchmark position

Phase 7 can be considered **closed locally/technically** because the project now has:

- executable benchmark UI
- persistent local benchmark history
- reusable JSON report
- aggregate summaries by model/runtime/retrieval/embedding/use-case/quantization context
- explicit comparative view for adjacent strategies already built in earlier phases

### Ollama vs Hugging Face guidance

Current recommended interpretation:

- **Ollama** remains the primary runtime for stable local serving and product-style comparison in the app
- **Hugging Face local** remains the experimental track for model variation, alternative runtimes and future adaptation work

So in Phase 7:

- Ollama is the main operational benchmark baseline
- Hugging Face local is the experimental benchmark lane
- cloud-style models are treated as a separate runtime class for comparison, not as a replacement for the local-first thesis

### What remains as future empirical expansion

These items are not blocking the local closure of Phase 7, but remain useful as future benchmark campaigns:

- quantization-focused comparisons when local model variants are available
- broader per-use-case benchmark suites
- larger empirical campaigns comparing Ollama-served models vs Hugging Face local variants under the same workload

### Practical commands

Generate the Phase 7 report:

```bash
python scripts/report_phase7_model_comparison_log.py
```

Run focused validation:

```bash
python -m unittest tests.test_model_comparison_service_unittest tests.test_phase7_model_comparison_log
```
