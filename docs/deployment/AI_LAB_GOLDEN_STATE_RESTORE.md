# AI Lab Golden State Restore

This document defines the slim AI Lab historical state restore used by AI Decision Studio AWS/Oracle-like deployments.

## Official baseline archive

The official v1 archive is stored outside Git:

runtime/ai_decision_studio_functional_baseline/ai_lab_golden_state/ai-lab-golden-state-v1.tar.gz

Manifest:

runtime/ai_decision_studio_functional_baseline/ai_lab_golden_state/ai-lab-golden-state-v1.manifest.json

SHA256:

c89628335dd1e6a9b9e177d202ab6492361d8b759bb22b41453ed0bc00253a5c

## What it contains

This is a slim AI Lab state pack. It preserves the historical UI state needed by:

- EvidenceOps
- Benchmarks
- Evals / Historical Diagnosis
- Overview
- Runtime Observability

It includes:

- EvidenceOps action store
- EvidenceOps worklog
- EvidenceOps repository snapshot
- Phase 8 eval SQLite database
- runtime execution log
- phase6 / phase7 / phase55 logs
- benchmark_runs summary/result/report files
- phase5_eval and phase8_eval reports

It intentionally excludes:

- Chroma/vector stores
- .chroma_rag directories
- large benchmark binary files
- benchmark PDFs
- old PNG/PPTX artifacts

## Restore method

Do not extract the tar directly into the data root.

Correct restore flow:

1. Validate SHA256.
2. Extract archive into a temporary directory.
3. Stop product-api and frontend.
4. Overlay into /opt/ai-decision-studio/data using sudo rsync.
5. Restart product-api and frontend.
6. Run AI Lab golden readiness check.

The robust overlay is required because direct tar extraction can fail when existing runtime files are owned or locked by the container.

## Expected readiness

After restore:

- EvidenceOps action rows > 0
- EvidenceOps open actions > 0
- Benchmarks total runs > 0
- Benchmarks model count > 0
- Evals historical cases > 0
- Overview Eval Pass Rate must not remain empty because historical evals are present

## Do not

- Do not commit the tar.gz to Git.
- Do not include vector stores or Chroma DBs in the slim pack.
- Do not leave restore archives permanently on small AWS disks after a successful deploy.
