# Phase 13.2 — Oracle Always Free Hardening Handoff

## Status

Phase 13.2 is locally complete.

This phase prepares AI Decision Studio for a professional Oracle Always Free public demo deployment by adding operational guardrails around public sessions, storage growth, backups, restore, HTTPS exposure, firewall posture, and health monitoring.

## Branch

production-readiness-runbook-clean

## Latest relevant commits

86a22d1 feat(readiness): add Phase 13.2 Oracle hardening gate
b44d5f2 feat(ops): add Oracle health ops report
0640ee6 feat(deploy): add Oracle HTTPS exposure checklist
af42c3f feat(ops): add Oracle data backup and restore scripts
554d785 feat(access): enforce public session storage quota
2cefd64 feat(ops): add public session overlay retention cleanup

## What Phase 13.2 added

### 1. Public session retention / cleanup

Files:

    scripts/cleanup_public_session_overlays.py
    scripts/readiness_phase_13_2_public_session_retention_check.sh

Behavior:

    dry-run by default
    delete only with --apply
    delete oversized only with --delete-oversized
    only touches users/public_sessions/sess_*
    never touches baseline/runtime/artifacts global roots

### 2. Public session storage quota

Files:

    src/product/access_control.py
    src/product/api.py
    docker-compose.oracle-like.yml
    .env.oracle.example

Policy:

    AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB=100 recommended for Oracle public demo
    250 MB used for local/dev validation
    admin is not subject to public session quota
    public run/import/rerun/deck generation is blocked with HTTP 429 when quota is exceeded

### 3. Oracle data backup / restore

Files:

    scripts/backup_oracle_data_root.sh
    scripts/restore_oracle_data_root.sh
    scripts/readiness_phase_13_2_backup_restore_check.sh

Backup includes:

    baseline/
    runtime/
    artifacts/
    users/

Backup excludes:

    .env
    .env.*
    *.env
    backups/
    ._*
    .DS_Store

### 4. HTTPS / reverse proxy / firewall posture

Files:

    deploy/oracle/Caddyfile.example
    docs/deployment/ORACLE_ALWAYS_FREE_SECURITY_EXPOSURE_CHECKLIST.md
    scripts/readiness_phase_13_2_oracle_exposure_check.sh

Exposure model:

    frontend binds to 127.0.0.1 only
    product-api has no public ports
    Caddy/Nginx should expose only 80/443
    OCI firewall should not expose 8011, 8787, 11434, 8085 or direct 8080

### 5. Health ops report

Files:

    scripts/oracle_health_ops_report.py
    scripts/readiness_phase_13_2_health_ops_check.sh

Checks:

    data root exists
    required dirs exist
    disk usage below threshold
    latest backup is recent
    public sessions within quota
    HTTP /health is OK
    docker compose services are healthy

### 6. Consolidated Phase 13.2 gate

File:

    scripts/readiness_phase_13_2_oracle_hardening_check.sh

Runs:

    retention/cleanup readiness
    backup/restore readiness
    HTTPS/exposure readiness
    health ops synthetic readiness
    Oracle-like deploy readiness
    real local health ops report

## Final local validation command

Run:

    export COMPOSE_PROJECT_NAME=ai-decision-studio
    export AI_DECISION_STUDIO_ORACLE_DATA_ROOT="$(cd runtime/ai_decision_studio_functional_baseline/oracle_like_data && pwd)"
    export AI_DECISION_STUDIO_READINESS_BASE_URL="http://127.0.0.1:8071"
    export AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB=250
    export AI_DECISION_STUDIO_MAX_BACKUP_AGE_HOURS=48

    bash scripts/readiness_phase_13_2_oracle_hardening_check.sh

Expected final line:

    == Phase 13.2 Oracle hardening readiness completed ==

## Known final local evidence

    frontend: 127.0.0.1:8071->8080/tcp
    product-api: 8011/tcp, no host-published port
    http_health_ok: true
    docker_compose_services_ok: true
    latest_backup_recent: true
    public_sessions_within_quota: true
    warnings: []
    errors: []

## Next step: real Oracle deployment

The next step is no longer local feature work. It is manual/cloud work:

    1. choose domain or subdomain
    2. create Oracle Always Free VM
    3. configure OCI firewall / NSG
    4. install Docker and Caddy
    5. transfer app bundle and data backup
    6. create real .env.oracle on VM
    7. restore data root
    8. run ARM64 smoke on the VM
    9. point DNS
    10. enable HTTPS with Caddy
    11. run final health ops report from VM

## Important manual security rules

    Do not commit .env.oracle.
    Do not expose product-api publicly.
    Do not expose ppt-creator publicly.
    Do not expose Ollama publicly.
    Restrict SSH to your own IP.
    Keep frontend bound to localhost when using Caddy/Nginx.
    Use AI_DECISION_STUDIO_PUBLIC_SESSION_MAX_MB=100 for public demo.
    Schedule cleanup_public_session_overlays.py daily.
    Create and test backups regularly.
