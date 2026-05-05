# Phase 4.5 Chart Assets

This directory stores the versioned visual assets generated for the Phase 4.5 benchmark documentation.

## Regenerate

```bash
python scripts/render_phase_4_5_charts.py
```

## Source data

```text
docs/data/phase_4_5_benchmark_data.json
```

## Coverage

- `01`–`04` → PDF extraction aggregate benchmark
- `05`–`08` → PDF extraction document-level benchmark
- `09`–`12` → embedding model benchmark
- `13`–`16` → embedding context window benchmark
- `17`–`20` → retrieval tuning benchmark
- `21`–`23` → executive summary visuals
