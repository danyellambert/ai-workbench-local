# Full Local Product Setup

This guide explains how to run Axiovance locally with user-owned runtime resources.

The public repository includes the product code, Docker topology, safe example env files and documentation. It does not include private credentials, external account identifiers, Nextcloud runtime volumes, hosted provider API keys, Trello board IDs, Notion database IDs or private baseline archives.

Use this guide when you want to run the product beyond the basic Quickstart and enable the full local integration surface: admin mode, Nextcloud/WebDAV import, model providers, deck generation, Trello publishing and Notion publishing.

---

## Setup levels

| Level | What works | What you need |
| --- | --- | --- |
| Core local stack | Frontend, Product API, Docker sidecars, product shell, health checks and local runtime surfaces. | Docker and `.env.docker`. |
| Full local product | Nextcloud import, workflow execution with configured providers, admin mode, deck generation, Trello and Notion publishing. | User-owned secrets and integration targets. |
| Maintainer baseline restore | Restores the private Nextcloud golden baseline and product runtime baseline. | Private baseline archives not committed to Git. |

For most external users, start with the Docker path. It is the closest path to the full product because it starts the Product API, frontend, Nextcloud, Ollama and presentation export sidecar together.

Host local development is useful for frontend/backend iteration, but it does not automatically start external sidecars such as Nextcloud, Ollama or `ppt-creator`.

---

## 1. Copy the environment file

For Docker:

```bash
cp .env.docker.example .env.docker
```

For host local development:

```bash
cp .env.local.example .env.local
```

Never commit real environment files.

Do not commit:

```text

.env.local
.env.docker
.env.aws
```

Only `.example` files should be versioned.

---

## 2. Important note for public clones

The local Docker helper can restore a private Nextcloud golden baseline when the private archive exists.

That archive is runtime state and is not committed to Git.

For a fresh public clone, run Docker with:

```bash
SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE=1 ENV_FILE=.env.docker scripts/run_local_docker.sh
```

Without this flag, the helper may fail if the Nextcloud Docker volume is empty and the private golden-baseline archive is not present.

The public path is:

1. start a fresh Nextcloud sidecar;
2. create your own user/password;
3. create your own document folder;
4. upload your own documents;
5. point `.env.docker` to that user and folder.

---

## 3. Generate admin and session secrets

Admin mode requires a username, password hash and session secret.

Generate the admin password hash:

```bash
python3 scripts/generate_admin_password_hash.py
```

You can also pass the password directly:

```bash
python3 scripts/generate_admin_password_hash.py --password "your-strong-password"
```

Generate a session secret:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
```

Fill these values in `.env.docker`:

```env
AI_DECISION_STUDIO_ADMIN_USERNAME=admin
AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH=<generated_password_hash>
AI_DECISION_STUDIO_SESSION_SECRET=<generated_session_secret>
```

Admin mode is required for protected global controls and publishing actions.

Public sessions run in isolated overlays so visitors can interact with the product without mutating the shared baseline.

---

## 4. Configure the private credential store

The product can store provider credentials saved through the Admin UI in a private file-backed secret store.

Recommended local Docker values:

```env
AI_DECISION_STUDIO_SECRET_STORE_BACKEND=file
AI_DECISION_STUDIO_SECRET_STORE_PATH=/app/secrets/credential_store.json
AI_DECISION_STUDIO_SECRET_ROOT=../ai_decision_studio_private_secrets
```

Create the private directory outside the repository:

```bash
mkdir -p ../ai_decision_studio_private_secrets
```

Do not commit this directory.

---

## 5. Configure a fresh Nextcloud workspace

The Docker stack includes a Nextcloud sidecar, but the public repository does not include the private Nextcloud golden baseline.

Use your own Nextcloud user, password and root folder.

Recommended local Docker values:

```env
NEXTCLOUD_ADMIN_USER=ads_admin
NEXTCLOUD_ADMIN_PASSWORD=<strong_local_password>
NEXTCLOUD_TRUSTED_DOMAINS=localhost 127.0.0.1 nextcloud

EVIDENCEOPS_REPOSITORY_BACKEND=nextcloud_webdav
EVIDENCEOPS_NEXTCLOUD_BASE_URL=http://nextcloud/remote.php/dav/files/ads_admin
EVIDENCEOPS_NEXTCLOUD_USERNAME=ads_admin
EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD=<nextcloud_password_or_app_password>
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo
```

For local Docker, the Product API talks to Nextcloud through the internal Docker hostname:

```text
http://nextcloud/remote.php/dav/files/<username>
```

For host local development, point the app to a host-reachable URL instead, for example:

```env
EVIDENCEOPS_NEXTCLOUD_BASE_URL=http://127.0.0.1:8085/remote.php/dav/files/<username>
EVIDENCEOPS_NEXTCLOUD_USERNAME=<username>
EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD=<password_or_app_password>
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo
```

Keep `/EvidenceOpsDemo` unless you also update the helper/readiness expectations that assume this root path.

---

## 6. Optional: expose the Nextcloud UI during setup

By default, the local Docker topology keeps Nextcloud private inside the Docker network.

To access the Nextcloud UI from your browser, create a temporary override file:

```bash
cat > docker-compose.nextcloud-ui.override.yml <<'YAML'
services:
  nextcloud:
    ports:
      - "127.0.0.1:8085:80"
YAML
```

Start Nextcloud with the override:

```bash
docker compose \
  --env-file .env.docker \
  -p ai-decision-studio \
  -f docker-compose.local.yml \
  -f docker-compose.nextcloud-ui.override.yml \
  up -d nextcloud
```

Then open:

```text
http://127.0.0.1:8085
```

Create the folder configured in:

```env
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo
```

Upload the documents you want Axiovance to import.

After setup, the Product API can keep using the internal Docker URL:

```text
http://nextcloud/remote.php/dav/files/<username>
```

---

## 7. Start the local Docker product stack

For a fresh public clone:

```bash
ENV_FILE=.env.docker scripts/run_local_docker.sh --down
SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE=1 ENV_FILE=.env.docker scripts/run_local_docker.sh
```

Then open:

```text
http://127.0.0.1:8071
```

Health check:

```bash
BASE_URL="http://127.0.0.1:8071"
curl -fsS "$BASE_URL/health" | python3 -m json.tool
```

The Docker stack includes:

- frontend;
- Product API;
- Nextcloud;
- Ollama;
- `ppt-creator`.

### Presentation export sidecar

Deck generation depends on the PPT Creator HTTP API.

In the Docker path, this is handled automatically by the `ppt-creator` sidecar. The Product API calls it through the internal Docker URL:

```env
PRESENTATION_EXPORT_ENABLED=true
PRESENTATION_EXPORT_BASE_URL=http://ppt-creator:8787
PRESENTATION_EXPORT_TIMEOUT_SECONDS=120
```

The sidecar exposes its API inside the Docker network on port `8787`, and the Product API waits for the sidecar health check before starting.

You normally do not need to expose this port to the host when using the full Docker stack.

---

## 8. Configure model providers

Axiovance can use local and hosted model lanes.

Leave provider keys blank when you do not want that lane enabled.

---

### Ollama local

The Docker stack includes an Ollama sidecar.

The local Docker helper can pre-pull the embedding model configured by:

```env
AI_DECISION_STUDIO_OLLAMA_EMBEDDING_MODEL_PULL=embeddinggemma:300m
```

To skip this pull:

```bash
SKIP_OLLAMA_EMBEDDING_MODEL_PULL=1 SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE=1 ENV_FILE=.env.docker scripts/run_local_docker.sh
```

If you want local generation, pull a generation model into the Ollama sidecar:

```bash
docker compose \
  --env-file .env.docker \
  -p ai-decision-studio \
  -f docker-compose.local.yml \
  exec ollama ollama pull <model_name>
```

Then set:

```env
OLLAMA_MODEL=<model_name>
OLLAMA_BASE_URL=http://ollama:11434/v1
```

---

### Ollama Hosted

For hosted Ollama models, fill:

```env
OLLAMA_HOSTED_BASE_URL=https://ollama.com/api
OLLAMA_HOSTED_API_KEY=<your_ollama_api_key>
OLLAMA_MODEL=<hosted_model_name>
```

If `OLLAMA_MODEL` points to a hosted/cloud model, make sure `OLLAMA_HOSTED_API_KEY` is configured.

---

### Hugging Face Inference

For Hugging Face remote inference, fill:

```env
HUGGINGFACE_INFERENCE_BASE_URL=https://router.huggingface.co/v1
HUGGINGFACE_INFERENCE_API_KEY=<your_huggingface_token>
```

---

### OpenAI-compatible providers

The codebase supports OpenAI/OpenAI-compatible provider lanes.

For host local development, fill the relevant local env values:

```env
OPENAI_API_KEY=<your_api_key>
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

For Docker, make sure the Product API container receives the OpenAI-compatible variables before relying on this lane. If the current Docker compose file does not pass these variables through, add them to the `product-api.environment` block or use the Admin/runtime credential surface when available.

---

## 9. Configure Trello publishing

Trello publishing requires your own Trello API credentials and board/list IDs.

Fill these values in `.env.docker`:

```env
EVIDENCEOPS_TRELLO_API_KEY=<your_trello_api_key>
EVIDENCEOPS_TRELLO_TOKEN=<your_trello_token>
EVIDENCEOPS_TRELLO_BOARD_ID=<your_board_id>
EVIDENCEOPS_TRELLO_LIST_OPEN_ID=<open_list_id>
EVIDENCEOPS_TRELLO_LIST_REVIEW_ID=<review_list_id>
EVIDENCEOPS_TRELLO_LIST_APPROVED_ID=<approved_list_id>
EVIDENCEOPS_TRELLO_LIST_DONE_ID=<done_list_id>
```

Leave them blank to keep Trello publishing disabled.

Do not commit your Trello IDs or tokens.

---

## 10. Configure Notion publishing

Notion publishing requires your own Notion integration and target database.

Fill these values in `.env.docker`:

```env
EVIDENCEOPS_NOTION_API_KEY=<your_notion_integration_secret>
EVIDENCEOPS_NOTION_DATABASE_ID=<your_database_id>
EVIDENCEOPS_NOTION_PARENT_PAGE_ID=<optional_parent_page_id>
EVIDENCEOPS_NOTION_API_VERSION=2022-06-28
```

Make sure your Notion integration has access to the target database.

Leave these values blank to keep Notion publishing disabled.

Do not commit your Notion integration secret or database IDs.

---

## 11. Private baseline restore variables

These variables are for maintainer/private restore flows only.

They are not required for a fresh public clone.

Local Docker Nextcloud baseline variables:

```env
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_ARCHIVE=
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_SHA256=
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_VOLUME=
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_USER=
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_ROOT=/EvidenceOpsDemo
```

AWS/private product data baseline variables:

```env
AI_DECISION_STUDIO_RESTORE_PRODUCT_DATA_BASELINE=
AI_DECISION_STUDIO_FORCE_RESTORE_PRODUCT_DATA_BASELINE=
AI_DECISION_STUDIO_PRODUCT_DATA_BASELINE_ARCHIVE=
AI_DECISION_STUDIO_PRODUCT_DATA_BASELINE_SHA256=
AI_DECISION_STUDIO_PRODUCT_DATA_BASELINE_OWNER=
```

For public local Docker usage, skip private baseline restore:

```bash
SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE=1 ENV_FILE=.env.docker scripts/run_local_docker.sh
```

---

## 12. Validate integrations

Check the public frontend and health route:

```bash
BASE_URL="http://127.0.0.1:8071"
curl -fsS "$BASE_URL/health" | python3 -m json.tool
```

Check integration status:

```bash
BASE_URL="http://127.0.0.1:8071"
curl -fsS "$BASE_URL/api/product/integrations" | python3 -m json.tool
```

Expected result:

- Nextcloud is configured when WebDAV credentials and root path are valid.
- Trello is ready only when API key, token, board ID and list IDs are filled.
- Notion is ready only when the integration key and database ID are valid.
- Provider lanes are available only when their API keys or local models are configured.

---

## 13. Host local development note

`scripts/run_local_dev.sh` starts the Product API and Vite frontend on the host.

It does not start Docker sidecars such as:

- Nextcloud;
- Ollama;
- `ppt-creator`.

For full local product behavior, prefer the Docker path.

For host development, run or expose each external dependency yourself and point `.env.local` to those services:

```env
EVIDENCEOPS_NEXTCLOUD_BASE_URL=http://127.0.0.1:8085/remote.php/dav/files/<username>
OLLAMA_BASE_URL=http://localhost:11434/v1
PRESENTATION_EXPORT_BASE_URL=http://127.0.0.1:8787
```

For deck export in host local development, start the PPT Creator API separately:

```bash
cd services/ppt_creator_app
python -m pip install -e .
python -m ppt_creator.api --host 127.0.0.1 --port 8787 --asset-root examples
```

Then validate:

```bash
curl -fsS http://127.0.0.1:8787/health | python3 -m json.tool
```

If this service is not running, the main product can still load and run non-export workflows, but deck generation/export actions will fail or appear unavailable.

---

## 14. Safe `.env.docker.example` cleanup before publishing

Before publishing the repository, make sure `.env.docker.example` does not contain personal user names, private board IDs or private baseline assumptions.

Recommended public-safe shape:

```env
EVIDENCEOPS_NEXTCLOUD_BASE_URL=http://nextcloud/remote.php/dav/files/ads_admin
EVIDENCEOPS_NEXTCLOUD_USERNAME=ads_admin
EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD=
EVIDENCEOPS_NEXTCLOUD_ROOT_PATH=/EvidenceOpsDemo

NEXTCLOUD_ADMIN_USER=ads_admin
NEXTCLOUD_ADMIN_PASSWORD=
NEXTCLOUD_TRUSTED_DOMAINS=localhost 127.0.0.1 nextcloud

EVIDENCEOPS_TRELLO_API_KEY=
EVIDENCEOPS_TRELLO_TOKEN=
EVIDENCEOPS_TRELLO_BOARD_ID=
EVIDENCEOPS_TRELLO_LIST_OPEN_ID=
EVIDENCEOPS_TRELLO_LIST_REVIEW_ID=
EVIDENCEOPS_TRELLO_LIST_APPROVED_ID=
EVIDENCEOPS_TRELLO_LIST_DONE_ID=

EVIDENCEOPS_NOTION_API_KEY=
EVIDENCEOPS_NOTION_DATABASE_ID=
EVIDENCEOPS_NOTION_PARENT_PAGE_ID=
EVIDENCEOPS_NOTION_API_VERSION=2022-06-28

AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_ARCHIVE=
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_SHA256=
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_VOLUME=
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_USER=ads_admin
AI_DECISION_STUDIO_NEXTCLOUD_GOLDEN_BASELINE_ROOT=/EvidenceOpsDemo
```

Also remove duplicated env keys from example files.

For example, avoid defining these twice:

```env
EVIDENCEOPS_NOTION_API_KEY=
EVIDENCEOPS_NOTION_DATABASE_ID=
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `run_local_docker.sh` fails because the Nextcloud golden baseline archive is missing | You are using a public clone without private runtime state | Run with `SKIP_NEXTCLOUD_GOLDEN_BASELINE_RESTORE=1` and configure your own Nextcloud workspace |
| Nextcloud import cannot find documents | Wrong username, WebDAV password or root path | Check `EVIDENCEOPS_NEXTCLOUD_BASE_URL`, `EVIDENCEOPS_NEXTCLOUD_USERNAME`, `EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD` and `EVIDENCEOPS_NEXTCLOUD_ROOT_PATH` |
| Changing `NEXTCLOUD_ADMIN_USER` or `NEXTCLOUD_ADMIN_PASSWORD` has no effect | The Nextcloud Docker volume was already initialized | Remove/recreate the Nextcloud volume or create the user manually in Nextcloud |
| Workflow execution fails at model call | No hosted key configured or local model not pulled | Configure `OLLAMA_HOSTED_API_KEY`, `HUGGINGFACE_INFERENCE_API_KEY`, `OPENAI_API_KEY`, or pull a local Ollama model |
| Trello appears unavailable | Missing API key, token, board ID or list IDs | Fill all Trello env values in a private `.env.docker` |
| Notion appears unavailable | Integration token missing or database not shared with the integration | Fill Notion env values and grant the integration access to the database |
| Admin login fails | Missing password hash or session secret | Generate `AI_DECISION_STUDIO_ADMIN_PASSWORD_HASH` and `AI_DECISION_STUDIO_SESSION_SECRET` |
| Deck export fails | `ppt-creator` is not reachable or not healthy | Use the Docker path or point `PRESENTATION_EXPORT_BASE_URL` to a running presentation sidecar |
| Host local dev cannot import from Nextcloud | No host-accessible Nextcloud instance is running | Expose Nextcloud on a local port or use the Docker path |