# AI Decision Studio — Oracle Environment Contract

Este documento define o contrato de ambiente para subir o AI Decision Studio no modo Oracle-like / Oracle VM.

Objetivo: impedir que o deploy volte com problemas já resolvidos localmente:
- admin/session env vazio;
- Nextcloud apontando para 127.0.0.1 dentro do container;
- Ollama inacessível dentro do container;
- PPT Creator sem PRESENTATION_EXPORT_BASE_URL;
- baseline/runtime/artifacts/users montados no lugar errado;
- public session overlay escrevendo no global.

## 1. Arquivos de ambiente

Pode ir para Git:
- legacy/deploy/oracle/.env.oracle.example

Não pode ir para Git:
- .env.oracle
- secrets reais
- tokens reais
- hashes reais de admin
- session secret real

## 2. Data roots esperados na Oracle

Layout recomendado no host Oracle:

    /opt/ai-decision-studio/
      app/
      data/
        baseline/
        runtime/
        artifacts/
        users/
        backups/

Variáveis obrigatórias:

    AI_DECISION_STUDIO_ORACLE_DATA_ROOT=/opt/ai-decision-studio/data
    AI_DECISION_STUDIO_BASELINE_ROOT=/opt/ai-decision-studio/data/baseline
    AI_DECISION_STUDIO_RUNTIME_ROOT=/opt/ai-decision-studio/data/runtime
    AI_DECISION_STUDIO_ARTIFACT_ROOT=/opt/ai-decision-studio/data/artifacts
    AI_DECISION_STUDIO_USERS_ROOT=/opt/ai-decision-studio/data/users

Dentro do container:

    /app/baseline   baseline funcional
    /app/runtime    runtime global
    /app/artifacts  artifacts globais
    /app/users      public/admin session overlays

## 3. Admin/session obrigatórios

Obrigatório:

    AI_DECISION_STUDIO_ADMIN_USERNAME=admin
    AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH=
    AI_DECISION_STUDIO_SESSION_SECRET=

Gerar hash:

    python3 scripts/generate_admin_password_hash.py --password '<admin-password>'

Gerar session secret:

    python3 -c "import secrets; print(secrets.token_urlsafe(48))"

Nunca commitar hash real nem session secret real.

## 4. Ollama

Se Ollama rodar como serviço Compose:

    OLLAMA_HOST=http://ollama:11434
    OLLAMA_BASE_URL=http://ollama:11434/v1

Se Ollama rodar no host Oracle e product-api estiver em Docker:

    OLLAMA_HOST=http://host.docker.internal:11434
    OLLAMA_BASE_URL=http://host.docker.internal:11434

Em Linux Docker, usar no compose:

    extra_hosts:
      - "host.docker.internal:host-gateway"

Nunca usar localhost/127.0.0.1 dentro do product-api para falar com serviço no host.

## 5. EvidenceOps / Nextcloud

Smoke local:

    EVIDENCEOPS_REPOSITORY_BACKEND=local

WebDAV real:

    EVIDENCEOPS_REPOSITORY_BACKEND=nextcloud_webdav
    EVIDENCEOPS_NEXTCLOUD_BASE_URL=https://<nextcloud-host>/remote.php/dav/files/<username>
    EVIDENCEOPS_NEXTCLOUD_USERNAME=
    EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD=
    EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo

Se Nextcloud rodar no host Oracle e product-api estiver em Docker:

    EVIDENCEOPS_NEXTCLOUD_BASE_URL=http://host.docker.internal:8085/remote.php/dav/files/<username>

com:

    extra_hosts:
      - "host.docker.internal:host-gateway"

## 6. PPT Creator / Presentation Export

Obrigatório se deck generation estiver habilitado:

    PRESENTATION_EXPORT_ENABLED=true
    PRESENTATION_EXPORT_BASE_URL=http://ppt-creator:8787
    PRESENTATION_EXPORT_TIMEOUT_SECONDS=120
    PRESENTATION_EXPORT_REMOTE_OUTPUT_DIR=outputs/ai_workbench_exports
    PRESENTATION_EXPORT_REMOTE_PREVIEW_DIR=outputs/ai_workbench_export_previews
    PRESENTATION_EXPORT_INCLUDE_REVIEW=true
    PRESENTATION_EXPORT_PREVIEW_BACKEND=auto
    PRESENTATION_EXPORT_REQUIRE_REAL_PREVIEWS=false
    PRESENTATION_EXPORT_FAIL_ON_REGRESSION=false

Se PPT Creator rodar no host Oracle:

    PRESENTATION_EXPORT_BASE_URL=http://host.docker.internal:8787

Validação esperada:

    GET /health no PPT Creator deve retornar 200.
    POST /api/product/generate-deck deve gerar .pptx em /app/artifacts/presentation_exports.

O endpoint /docs é opcional e pode retornar 404.

## 7. Trello / Notion

Admin-only:

    EVIDENCEOPS_TRELLO_API_KEY=
    EVIDENCEOPS_TRELLO_TOKEN=
    EVIDENCEOPS_TRELLO_BOARD_ID=
    EVIDENCEOPS_TRELLO_LIST_OPEN_ID=
    EVIDENCEOPS_TRELLO_LIST_REVIEW_ID=
    EVIDENCEOPS_TRELLO_LIST_APPROVED_ID=
    EVIDENCEOPS_TRELLO_LIST_DONE_ID=

    EVIDENCEOPS_NOTION_API_KEY=
    EVIDENCEOPS_NOTION_DATABASE_ID=

Public pode preview. Publish externo continua admin-only.

## 8. Public/admin overlay

Public nunca deve mutar runtime global.

Targets públicos esperados:

    /app/users/public_sessions/{session_id}/overlay/runs
    /app/users/public_sessions/{session_id}/overlay/indexes
    /app/users/public_sessions/{session_id}/overlay/documents
    /app/users/public_sessions/{session_id}/overlay/artifacts
    /app/users/public_sessions/{session_id}/overlay/handoffs

Admin autenticado pode escrever global.

## 9. Subida Oracle

Usar:

    docker compose --env-file .env.oracle -p ai-decision-studio -f docker-compose.oracle-like.yml up -d --build

Antes de expor publicamente, rodar:

    legacy/scripts/oracle/validate_oracle_environment_contract.sh .env.oracle

Não expor se:
- admin/session env estiver vazio;
- PRESENTATION_EXPORT_BASE_URL estiver vazio com export habilitado;
- endpoints container-facing usarem localhost/127.0.0.1 indevidamente;
- /app/users não estiver writable;
- public workflow/import estiver mutando global;
- secrets reais estiverem em arquivos versionados.


Required Hugging Face Inference provider:

```env
    HUGGINGFACE_INFERENCE_BASE_URL=https://router.huggingface.co/v1
    HUGGINGFACE_INFERENCE_API_KEY=
```

EvidenceOps UI cache policy:

    EVIDENCEOPS_UI_CACHE_MODE=persistent_until_sync
    EVIDENCEOPS_UI_CACHE_PATH=/app/runtime/cache/lab/evidenceops_payload.json

The EvidenceOps UI cache is persistent and intentionally does not expire automatically.
Normal UI reads use the last known good snapshot immediately.
Nextcloud/WebDAV rescans happen through explicit sync, deploy warmup, or state restore.
