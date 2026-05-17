# Golden Surface Snapshot

Golden Surface is a parity ruler for Axiovance.

It captures read-only API payloads from the current local backend so future Docker/baseline work can prove that the frontend-visible surface still has the same shape and real backing objects.

## Important rule

Golden Surface is not the Docker seed source.

The Docker source will be the Functional Baseline State: copied and sanitized real runtime state, documents, chunks, artifacts, run history, EvidenceOps state, benchmarks/evals and provider metadata.

## Capture command

Save raw snapshots outside the repo first:

```bash
python3 scripts/capture_golden_surface_snapshot.py \
  --base-url http://127.0.0.1:8011 \
  --out ../ai_decision_studio_golden_snapshots/current_local_snapshot
```

## Read-only endpoints

The script captures only read-only endpoints. It does not run workflows, import documents, upload files, generate decks, edit preferences, test credentials or mutate runtime controls.

## Commit policy

Do not commit raw snapshots until reviewed for secrets, absolute paths, excessive size and private data.
