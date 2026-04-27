# Preindexed Nextcloud import for the public demo

This patch keeps the normal ingestion pipeline intact, but adds a fast path for the fixed Nextcloud **Public Reference Corpus**.

## Runtime behavior

1. The document library still starts empty.
2. The user clicks **Import from Nextcloud** and selects one or more documents.
3. The backend checks whether each selected document already exists in the hidden preindex store.
4. If it exists, the backend activates the stored chunks/embeddings into the active RAG store and emits normal ingestion progress events: extraction, chunking, embeddings, and index sync.
5. If it does not exist, the backend falls back to the real ingestion pipeline and takes as long as the actual extraction/embedding flow needs.

The frontend does not need a separate code path. It continues polling the same upload job endpoint and renders the same ingestion stage cards.

## Environment variables

```bash
EVIDENCEOPS_PREINDEX_FAST_IMPORT_ENABLED=true
EVIDENCEOPS_PREINDEX_STORE_PATH=
EVIDENCEOPS_PREINDEX_SIM_TARGET_SECONDS=5
EVIDENCEOPS_PREINDEX_SIM_MIN_SECONDS=2
EVIDENCEOPS_PREINDEX_SIM_MAX_SECONDS=8
EVIDENCEOPS_PREINDEX_SYNC_CHROMA_ON_IMPORT=true
```

`EVIDENCEOPS_PREINDEX_STORE_PATH` can be left blank. The default is:

```text
.runtime/state/rag/preindexed_public_corpus.json
```

## One-time PDF VLM enrichment

When `--force-vlm` is enabled, PDFs are now enriched explicitly through Ollama's `/api/chat` image path before chunking and embeddings. This avoids Docling's default local `SmolVLM` path and lets you use an Ollama Cloud VLM for the one-time corpus build.

Recommended settings for the high-quality one-time build:

```bash
EVIDENCE_VL_MODEL=qwen3-vl:235b-cloud
EVIDENCEOPS_PREINDEX_PDF_VLM_ENABLED=true
EVIDENCEOPS_PREINDEX_PDF_VLM_MODEL=qwen3-vl:235b-cloud
EVIDENCEOPS_PREINDEX_PDF_VLM_MAX_PAGES=20
EVIDENCEOPS_PREINDEX_PDF_VLM_DPI=180
EVIDENCEOPS_PREINDEX_ALLOW_DOCLING_LOCAL_VLM=false
```

By default the script uses a hardcoded page-route manifest at `scripts/preindex_public_reference_corpus_page_routes.json`. For the provided `EvidenceOpsDemo/Public Reference Corpus`, only the selected visual/complex pages are sent to Ollama Cloud VLM; all other PDF pages stay on Docling/text extraction. This saves credits compared with sending the first N pages of every PDF.

`EVIDENCEOPS_PREINDEX_PDF_VLM_MAX_PAGES` is now only the fallback for PDFs that are not in the route manifest. Use `--pdf-vlm-route-policy first-n` to restore the old first-N behavior, or `--pdf-vlm-route-policy all --pdf-vlm-max-pages 0` for all pages. The script logs lines like:

```text
[pdf_vlm] enabled: model=qwen3-vl:235b-cloud, base_url=http://localhost:11434, max_pages=20, dpi=180
[pdf_vlm] Some File.pdf: page 1/5 -> qwen3-vl:235b-cloud
```

If you see `HuggingFaceTB/SmolVLM-256M-Instruct` in the logs, that is Docling's local VLM path, not the Ollama Cloud path. Keep `EVIDENCEOPS_PREINDEX_ALLOW_DOCLING_LOCAL_VLM=false` for the final preindex run.

## Build the hidden store once

From the repo root, after your Ollama and Nextcloud settings are ready:

```bash
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH="/EvidenceOpsDemo/Public Reference Corpus" \
EVIDENCE_VL_MODEL="qwen3-vl:235b-cloud" \
EVIDENCEOPS_PREINDEX_PDF_VLM_MODEL="qwen3-vl:235b-cloud" \
python scripts/preindex_public_reference_corpus.py \
  --from-nextcloud \
  --reset \
  --force-vlm
```

For a smoke test:

```bash
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH="/EvidenceOpsDemo/Public Reference Corpus" \
EVIDENCE_VL_MODEL="qwen3-vl:235b-cloud" \
EVIDENCEOPS_PREINDEX_PDF_VLM_MODEL="qwen3-vl:235b-cloud" \
python scripts/preindex_public_reference_corpus.py \
  --from-nextcloud \
  --reset \
  --force-vlm \
  --limit 2 \
  --pdf-vlm-max-pages 2
```

To build from a local mirror of the corpus instead:

```bash
python scripts/preindex_public_reference_corpus.py \
  --source-root "/path/to/EvidenceOpsDemo/Public Reference Corpus" \
  --reset \
  --force-vlm \
  --pdf-vlm-model qwen3-vl:235b-cloud
```

The script writes a separate hidden JSON store, so the active document library remains empty until a user imports documents in the UI.

## Recommended embedding settings

Keep the embedding path aligned with the app default:

```bash
RAG_EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=embeddinggemma:300m
RAG_EMBEDDING_MODEL=embeddinggemma:300m
RAG_PDF_EVIDENCE_PIPELINE_ENABLED=true
RAG_PDF_DOCLING_PICTURE_DESCRIPTION=false
```

If `RAG_EMBEDDING_MODEL` is intentionally blank in your runtime profile, the app can still resolve the Ollama default from `OLLAMA_EMBEDDING_MODEL`; setting both makes the preindex run easier to audit.

## Deployment note

For the public CPU-only deployment, keep the hidden preindex store and start with an empty visible active RAG store:

```bash
rm -f .runtime/state/rag/rag_store.json
rm -f .runtime/state/rag/rag_store_documents.json
```

Do not delete:

```text
.runtime/state/rag/preindexed_public_corpus.json
```

## Resuming after credits, interruption, or a partial staged run

The preindex script now has resume mode enabled by default. Resume mode reads the existing hidden store, finds documents that already have chunks, and skips them before VLM extraction or embedding.

Important: do **not** use `--reset` when resuming. `--reset` intentionally deletes the hidden store first, so there is nothing to skip.

Resume the next batch with:

```bash
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH="/EvidenceOpsDemo/Public Reference Corpus" \
EVIDENCE_VL_MODEL="qwen3-vl:235b-cloud" \
EVIDENCEOPS_PREINDEX_PDF_VLM_MODEL="qwen3-vl:235b-cloud" \
python scripts/preindex_public_reference_corpus.py \
  --from-nextcloud \
  --force-vlm \
  --limit 10 \
  --pdf-vlm-max-pages 8
```

You should see logs like:

```text
[resume] enabled: 10 completed document hash(es) found in .../preindexed_public_corpus.json
[skip] 1: README_generated.md already fully indexed.
[skip] 2: cms_internal_monitoring_auditing_checklists.pdf already fully indexed.
```

Use `--no-resume` if you deliberately want to reprocess matching documents without deleting the full store. Use `--reset` only when you want to rebuild everything from zero.

## Checkpoints for expensive VLM work

The script also writes checkpoints while it runs:

```text
.runtime/state/rag/preindexed_public_corpus_checkpoints/documents/
.runtime/state/rag/preindexed_public_corpus_checkpoints/pdf_vlm_pages/
```

This means interruption is now safer at two levels:

1. After each VLM page is described, that page result is saved. If the script stops halfway through a large PDF, the next run reuses the cached page summaries and continues with the missing pages.
2. After each document finishes extraction/VLM enrichment, the enriched `LoadedDocument` is saved. If the script stops during embeddings or Chroma sync, the next run skips extraction and VLM for that document and only retries indexing.

You should see logs like:

```text
[pdf_vlm] Some File.pdf: page 1/8 -> cached
[checkpoint] 1: Some File.pdf extracted/VLM text already saved; skipping extraction and PDF VLM.
```

You can override the checkpoint directory with:

```bash
EVIDENCEOPS_PREINDEX_CHECKPOINT_DIR="/path/to/preindex_checkpoints"
```

Keep this checkpoint folder until the full corpus has been successfully indexed. After the final `preindexed_public_corpus.json` and `preindexed_public_corpus_chroma/` are validated, the checkpoints are optional and can be archived or deleted.

### Demo Synthetic Corpus routing

The bundled page-route manifest also covers `Demo Synthetic Corpus`. Most synthetic PDFs are ReportLab-style, text-first documents and are routed to Docling/text extraction only. The only synthetic PDF currently routed to cloud VLM is:

- `technical/Technical Architecture Brief.pdf`: pages 12-15

Those pages are embedded image-only appendix captures. They are a small, controlled cloud-VLM spend and preserve visual/diagram/checklist meaning that plain text extraction may miss. To protect credits for this closed corpus, prefer `--pdf-vlm-route-policy manifest-only`.


## Realistic fast-import simulation timing

The fast path now scales the visible ingestion delay by each preindexed document's real size.

- `EVIDENCEOPS_PREINDEX_SIM_MAX_SECONDS=15` caps the simulated document ingestion time.
- The largest document in the hidden preindexed corpus lands near the cap.
- Smaller documents are reduced proportionally using `char_count` first and `chunk_count` as a secondary signal.
- `EVIDENCEOPS_PREINDEX_SIM_MIN_SECONDS=1.75` keeps tiny files visible without making them feel stuck.
- `EVIDENCEOPS_PREINDEX_SIM_CURVE=0.62` controls the size curve. Lower values make mid-sized documents feel slower; higher values make only the largest documents approach the cap.

Recommended demo defaults:

```env
EVIDENCEOPS_PREINDEX_SIM_MIN_SECONDS=1.75
EVIDENCEOPS_PREINDEX_SIM_MAX_SECONDS=15
EVIDENCEOPS_PREINDEX_SIM_CURVE=0.62
```

The UI still receives the normal stage sequence (`extraction`, `chunking`, `embeddings`, `index_sync`), but the total wait is now based on real corpus metadata instead of a fixed duration per document.
