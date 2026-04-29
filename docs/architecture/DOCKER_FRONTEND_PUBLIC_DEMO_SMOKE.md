# Docker Frontend Public Demo Smoke

This document records the first successful Docker smoke for AI Decision Studio using the sanitized functional baseline.

## Purpose

Validate that Docker can run:

- Product API backend
- React/Vite frontend served by Nginx
- Nginx proxy to Product API
- sanitized functional baseline mounted as a writable overlay

This test uses real baseline state, not Golden Surface JSON as a fake seed.

## Baseline mount

The compose stack expects:

- `AI_DECISION_STUDIO_BASELINE_OVERLAY_ROOT`

During the smoke, this pointed to:

- `../ai_decision_studio_functional_baseline/current_backend_smoke_overlay`

Inside the backend container, it is mounted at:

- `/app/baseline`

The backend uses:

- `APP_WORKSPACE_ROOT=/app/baseline`
- `APP_RUNTIME_ROOT=/app/baseline/.runtime`
- `APP_ARTIFACT_ROOT=/app/baseline/artifacts`
- `PRESENTATION_EXPORT_LOCAL_ARTIFACT_DIR=/app/baseline/artifacts/presentation_exports`

## Public demo images

The smoke introduced:

- `Dockerfile.public-demo`
- `Dockerfile.frontend-public-demo`
- `docker-compose.frontend-public-demo.yml`
- `frontend/nginx.public-demo.conf`
- `requirements-public-demo.txt`

## Dependency strategy

The public demo backend image uses `requirements-public-demo.txt`.

This intentionally excludes heavy AI packages that are not required for serving the already-materialized functional baseline during the public demo smoke.

The excluded heavy packages include:

- `sentence-transformers`
- `transformers`
- `torch`

## Docker context

The `.dockerignore` was tightened to avoid sending local runtime, benchmark, cache, virtualenv, frontend build and artifact directories into the Docker build context.

The Product API build context dropped from gigabytes to kilobytes during the smoke.

## Backend Docker result

The Product API container became healthy.

The direct backend health endpoint returned:

- `ok: true`
- `service: product_api`
- `workflow_count: 4`

Golden Surface capture against the backend Docker port captured 15 endpoints with no errors.

Smoke counts:

| Surface | Count |
|---|---:|
| Product workflows | 4 |
| Product documents | 17 |
| Product run history | 100 |
| Product artifacts | 100 |
| Lab artifacts | 80 |
| EvidenceOps actions | 72 |

## Frontend Docker result

The frontend container became healthy and exposed port `8059`.

Validated routes:

| Route | Result |
|---|---|
| `/` | 200 OK |
| `/health` | proxied to Product API and returned ok |
| `/api/product/workflows` | proxied to Product API and returned 4 workflows |

## Security note

The backend service keeps `cap_drop: ALL`.

The frontend service does not use `cap_drop: ALL` because the stock Nginx entrypoint attempts to adjust ownership of cache directories on startup. With all capabilities dropped, Nginx fails with `chown("/var/cache/nginx/client_temp", 101) failed`.

The frontend still uses:

- read-only root filesystem
- tmpfs for Nginx runtime/cache directories
- `no-new-privileges:true`

## Conclusion

The Docker public demo stack can serve AI Decision Studio from a real sanitized baseline overlay.

The next phase is to formalize repeatable smoke scripts and then validate selected live workflow runs inside Docker.
