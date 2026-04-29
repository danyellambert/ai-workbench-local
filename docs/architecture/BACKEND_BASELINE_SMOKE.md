# Backend Baseline Smoke

This document records the first backend smoke test against the sanitized functional baseline.

## Purpose

Validate that the Product API can boot against a copied writable overlay of the sanitized baseline before Docker wiring.

This is not a Docker test yet.

## Configuration used

The smoke used a temporary overlay copied from:

- Source: `../ai_decision_studio_functional_baseline/current_sanitized_baseline/baseline`
- Overlay: `../ai_decision_studio_functional_baseline/current_backend_smoke_overlay`

The Product API was started with:

- `APP_WORKSPACE_ROOT=../ai_decision_studio_functional_baseline/current_backend_smoke_overlay`
- `APP_RUNTIME_ROOT=../ai_decision_studio_functional_baseline/current_backend_smoke_overlay/.runtime`
- `APP_ARTIFACT_ROOT=../ai_decision_studio_functional_baseline/current_backend_smoke_overlay/artifacts`
- `PRESENTATION_EXPORT_LOCAL_ARTIFACT_DIR=../ai_decision_studio_functional_baseline/current_backend_smoke_overlay/artifacts/presentation_exports`
- `PRODUCT_API_SERVER_PORT=8012`

## Result

The API health endpoint returned ok.

Golden Surface capture against port 8012 captured 15 endpoints with no errors.

## Smoke counts

| Surface | Count |
|---|---:|
| Product workflows | 4 |
| Product documents | 17 |
| Product run history | 100 |
| Product artifacts | 100 |
| Lab artifacts | 80 |
| EvidenceOps actions | 72 |

## Conclusion

The backend can read the sanitized baseline through a copied writable overlay when configured with explicit workspace, runtime and artifact roots.

The next phase is Docker mounting/wiring, still preserving the rule that generated baseline data is not committed.
