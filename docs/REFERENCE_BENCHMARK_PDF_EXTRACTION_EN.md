# PDF Extraction Benchmark

## Goal

This benchmark compares three extraction strategies for PDF ingestion:

- `basic`
- `hybrid`
- `complete`

The purpose is to understand the trade-off between:

- answer quality after ingestion
- extraction cost
- indexing cost
- document-level behavior on mixed PDF types

This benchmark was part of the Phase 4.5 closure and is supported by **manual review** rather than by automatic metrics alone.

---

## Pipeline under test

The benchmark runner:

1. selects one or more PDFs
2. extracts content with each configured mode
3. rebuilds the RAG index for that run
4. runs a fixed question set
5. optionally generates answers with the configured model
6. saves outputs as JSON, CSV and Markdown for manual review

### Main script

```bash
python scripts/run_pdf_extraction_benchmark_en.py
```

### Compatibility alias

```bash
python scripts/run_pdf_extraction_benchmark.py
```

### Example command

```bash
python scripts/run_pdf_extraction_benchmark_en.py \
  --pdfs \
  benchmark_pdfs/2025-HB-44-20250106-Final-508.pdf \
  benchmark_pdfs/kaur-2016-ijca-911367.pdf \
  benchmark_pdfs/Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf \
  benchmark_pdfs/c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf
```

### Run without answer generation

```bash
python scripts/run_pdf_extraction_benchmark_en.py --no-generate
```

---

## Manual-review workflow

The benchmark uses a review file where each answer is scored manually:

- `0` = unsupported / incorrect
- `1` = partially correct / partially grounded
- `2` = well supported / correct

The final consolidation used:

- 12 review packets
- 192 manual judgments

---

## Aggregate results by mode

| Mode | Avg manual score | Normalized quality | Avg extraction (s) | Avg indexing (s) |
| --- | ---: | ---: | ---: | ---: |
| `basic` | 1.0938 | 54.7% | 2.7385 | 40.6925 |
| `hybrid` | 1.0625 | 53.1% | 22.0248 | 40.8867 |
| `complete` | 1.1094 | 55.5% | 1485.3800 | 127.1430 |

### Aggregate visuals

![Average manual score by extraction mode](assets/phase_4_5/01_pdf_extraction_aggregate_manual_score.png)

![Quality vs extraction cost](assets/phase_4_5/02_pdf_extraction_aggregate_quality_vs_cost.png)

![Average indexing time by extraction mode](assets/phase_4_5/03_pdf_extraction_aggregate_indexing_time.png)

![Manual-review coverage by extraction mode](assets/phase_4_5/04_pdf_extraction_aggregate_review_coverage.png)

### Aggregate interpretation

- `complete` achieved the highest average manual score, but only by a **very small margin**.
- The quality gap between `complete` and `basic` was only **0.0156** points.
- The quality gap between `complete` and `hybrid` was only **0.0469** points.
- That tiny quality gain came with an extreme runtime increase: `complete` required **1485.38 s** of average extraction time versus **22.0248 s** for `hybrid` and **2.7385 s** for `basic`.

This means the benchmark should not be read as “complete is best”; it should be read as “complete is only slightly better on average, but operationally much more expensive”.

---

## Document-level results

### Manual score by document and mode

| Document | `basic` | `hybrid` | `complete` | Winner |
| --- | ---: | ---: | ---: | --- |
| `2025-HB-44-20250106-Final-508.pdf` | 0.8750 | 0.9375 | 0.7500 | `hybrid` |
| `kaur-2016-ijca-911367.pdf` | 1.2500 | 1.1875 | 1.1875 | `basic` |
| `Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf` | 1.1250 | 0.9375 | 1.2500 | `complete` |
| `c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf` | 1.1250 | 1.1875 | 1.2500 | `complete` |

### Document-level visuals

![Manual score by document and mode](assets/phase_4_5/05_pdf_extraction_doc_level_manual_score.png)

![Extraction time by document and mode](assets/phase_4_5/06_pdf_extraction_doc_level_extraction_time.png)

![Character count by document and mode](assets/phase_4_5/07_pdf_extraction_doc_level_char_count.png)

![Chunk count by document and mode](assets/phase_4_5/08_pdf_extraction_doc_level_chunk_count.png)

### Document-level interpretation

The extraction benchmark is **document-dependent**:

- `hybrid` wins on `2025-HB-44-20250106-Final-508.pdf`
- `basic` wins on `kaur-2016-ijca-911367.pdf`
- `complete` wins on `Meng_Extraction_of_Virtual_ICCV_2015_paper.pdf`
- `complete` also wins on `c9c938dc-08e0-4f18-bf1d-a5d513c93ed8.pdf`

That means no single mode is globally best for every document profile.

The benchmark also shows that **more extracted text does not automatically mean better quality**. For example, `2025-HB complete` produced far more characters and chunks than the other modes, but still had the lowest manual score for that document.

---

## Operational policy selected from the benchmark

### Default mode

Use **`hybrid`** as the project default.

Reason:
- it stays in the same overall quality band as `complete`
- it avoids the cost explosion of `complete`
- it is more robust than `basic` for mixed-document corpora

### Fast baseline / sanity check

Use **`basic`** when:
- the PDF is clearly text-heavy
- the goal is a quick baseline run
- you want the cheapest possible ingestion path

### Escalation mode

Use **`complete`** when:
- the PDF is OCR-heavy
- the PDF is strongly image-based
- the document has diagrams or page layouts that basic parsing misses
- a failure case explicitly justifies paying the extra cost

---

## Final decision from Phase 4.5

The extraction benchmark supports this project-level decision:

```env
RAG_PDF_EXTRACTION_MODE=hybrid
```

This is not because `hybrid` had the highest aggregate manual score. It did not. The reason is that it offered the **best engineering trade-off** once quality, extraction cost, indexing cost, and mixed-document behavior were considered together.

For the broader benchmark context, see:

- `docs/PHASE_4_5_BENCHMARK_RESULTS.md`
- `docs/PHASE_4_5_VALIDATION.md`
