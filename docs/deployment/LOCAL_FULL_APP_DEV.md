# Local full app development

This runbook explains how to run the complete AI Decision Studio app locally.

Use this mode when you want to test the real product experience on your machine:

- frontend shell;
- Product API;
- persisted corpus and run-history reads;
- public session overlays;
- admin login/session cookies;
- Preferences provider registry;
- Runtime Controls;
- Trello/Notion publish permission checks;
- Hugging Face Inference connection tests.

---

## Required command

From the repository root:

~~~bash
ENV_FILE=.env.local scripts/run_local_dev.sh
~~~

Open:

~~~text
http://127.0.0.1:5173
~~~

Expected runner output includes:

~~~text
env_file=.env.local
users_root=.../runtime/local_dev/users
python_bin=.venv/bin/python
API health OK
Local dev is running:
  API:      http://127.0.0.1:8011/health
  Frontend: http://127.0.0.1:5173
~~~

---

## Why this is not the same as frontend-only Vite

This command:

~~~bash
npm --prefix frontend run dev:frontend
~~~

starts only the Vite/React frontend.

It does **not** start the Product API.

The full local runner does more:

1. Loads `.env.local`.
2. Prefers `.venv/bin/python` when available.
3. Starts `main_product_api.py` on the Product API port.
4. Waits for `/health`.
5. Starts the Vite frontend.
6. Keeps public/admin overlays in a writable local runtime path.
7. Aligns frontend and backend for same-origin `/api` behavior.
8. Avoids accidentally running the backend with global Python.

Use `npm --prefix frontend run dev:frontend` only for frontend-only visual work. For product-level validation, use:

~~~bash
ENV_FILE=.env.local scripts/run_local_dev.sh
~~~

---

## Local env file

The real local env file is:

~~~text
.env.local
~~~

It is ignored by Git and should not be committed.

Important local settings:

~~~text
APP_USERS_ROOT=runtime/local_dev/users or an absolute local runtime path
AI_DECISION_STUDIO_USERS_ROOT=runtime/local_dev/users or an absolute local runtime path
VITE_PRODUCT_API_BASE_URL=http://127.0.0.1:5173
VITE_PRODUCT_API_PROXY_ENABLED=1
VITE_PRODUCT_API_PROXY_TARGET=http://127.0.0.1:8011
~~~

The local users root is intentionally writable and separate from `/app`.

---

## Local admin auth

If local should use the same admin password as AWS, copy only the admin username/hash from the real `.env.aws` into the real `.env.local`.

Do not commit either real file.

Validate that real env files are ignored:

~~~bash
git check-ignore -v .env.local
git check-ignore -v .env.aws
~~~

---

## Local validation

Static checks:

~~~bash
bash -n scripts/run_local_dev.sh
bash -n scripts/readiness_multi_environment_contract_check.sh

ENV_FILE=.env.local.example scripts/run_local_dev.sh --check
scripts/readiness_multi_environment_contract_check.sh
~~~

Start the full app:

~~~bash
ENV_FILE=.env.local scripts/run_local_dev.sh
~~~

In another terminal, validate Product API reads:

~~~bash
curl -fsS http://127.0.0.1:8011/api/product/document-library \
  -o /tmp/ads_local_doclib.json

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/ads_local_doclib.json").read_text())
docs = data.get("documents") or []
print("documents_len:", len(docs))
print("read_scope:", data.get("read_scope"))
assert len(docs) > 0
assert data.get("read_scope") == "global_plus_session_overlay"
print("OK: document-library local")
PY

curl -fsS "http://127.0.0.1:8011/api/product/run-history?compact=1&limit=100" \
  -o /tmp/ads_local_run_history.json

python3 - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/ads_local_run_history.json").read_text())
runs = data.get("runs") or []
print("runs_len:", len(runs))
print("summary:", data.get("summary"))
assert len(runs) > 0
print("OK: run-history local")
PY

curl -fsS http://127.0.0.1:5173 >/tmp/ads_frontend_check.html && echo "frontend OK"
~~~

Validate that the local Python runtime can load Hugging Face Inference:

~~~bash
.venv/bin/python - <<'PY'
from src.providers.huggingface_inference_provider import HuggingFaceInferenceProvider
print("OK: HuggingFaceInferenceProvider imports from .venv")
PY
~~~

---

## Troubleshooting

### Product API unavailable in the UI

Check:

~~~bash
curl -fsS http://127.0.0.1:8011/health | python3 -m json.tool
~~~

Restart cleanly:

~~~bash
pkill -f "main_product_api.py" >/dev/null 2>&1 || true
pkill -f "vite" >/dev/null 2>&1 || true
sleep 2

ENV_FILE=.env.local scripts/run_local_dev.sh
~~~

### Admin login works visually, but actions say admin access is required

Use the full runner and access the app through Vite:

~~~bash
ENV_FILE=.env.local scripts/run_local_dev.sh
~~~

Then open:

~~~text
http://127.0.0.1:5173
~~~

Do not mix a manually started frontend with a backend started from a different env unless you are intentionally debugging auth/proxy behavior.

### Hugging Face Inference is unavailable in the registry

Confirm the runner uses the virtual environment:

~~~bash
ENV_FILE=.env.local scripts/run_local_dev.sh --check
~~~

Expected:

~~~text
python_bin=.venv/bin/python
~~~

If needed:

~~~bash
PYTHON_BIN=.venv/bin/python ENV_FILE=.env.local scripts/run_local_dev.sh
~~~

### zsh command not found after a shell loop

Avoid using `path` as a loop variable in zsh. It is tied to the shell `PATH`.

Use `endpoint` instead.
