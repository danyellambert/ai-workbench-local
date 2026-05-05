#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"


FRONTEND_DIR="$REPO_ROOT/frontend"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/.tmp_action_plan_isolated_selected_e2e}"
FRONTEND_TMP_DIR="$FRONTEND_DIR/.tmp_action_plan_isolated_selected_e2e"
mkdir -p "$OUT_DIR" "$FRONTEND_TMP_DIR"

export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434/v1}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-nemotron-3-nano:30b-cloud}"
export OLLAMA_AVAILABLE_MODELS="${OLLAMA_AVAILABLE_MODELS:-nemotron-3-nano:30b-cloud}"
export PRODUCT_API_SERVER_NAME="${PRODUCT_API_SERVER_NAME:-127.0.0.1}"
export PRODUCT_API_SERVER_PORT="${PRODUCT_API_SERVER_PORT:-8011}"
export FRONTEND_DEV_PORT="${FRONTEND_DEV_PORT:-8080}"
export PRODUCT_API_REUSE_EXISTING="0"
export VITE_PRODUCT_API_BASE_URL="${VITE_PRODUCT_API_BASE_URL:-http://127.0.0.1:${PRODUCT_API_SERVER_PORT}}"
export OUT_DIR

cleanup() {
  if [[ -n "${DEV_PID:-}" ]] && kill -0 "$DEV_PID" 2>/dev/null; then
    kill "$DEV_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

kill_port_if_busy() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
    if [[ -n "${pids:-}" ]]; then
      echo "==> Killing existing process(es) on port $port: $pids"
      kill -9 $pids 2>/dev/null || true
      sleep 1
    fi
  fi
}

echo "==> Repo root: $REPO_ROOT"
echo "==> Output dir: $OUT_DIR"
echo "==> Ollama model: $OLLAMA_MODEL"
echo "==> Product API port: $PRODUCT_API_SERVER_PORT"
echo "==> Frontend port: $FRONTEND_DEV_PORT"

kill_port_if_busy "$PRODUCT_API_SERVER_PORT"
kill_port_if_busy "$FRONTEND_DEV_PORT"

echo "==> Ensuring Playwright Chromium is installed..."
npm --prefix "$FRONTEND_DIR" exec playwright install chromium >/dev/null

echo "==> Starting frontend + product-api..."
npm --prefix "$FRONTEND_DIR" run dev >"$OUT_DIR/dev.log" 2>&1 &
DEV_PID=$!

echo "==> Waiting for frontend on exact port..."
frontend_ready=0
for _ in $(seq 1 180); do
  if curl -fsS "http://127.0.0.1:${FRONTEND_DEV_PORT}" >/dev/null 2>&1; then
    frontend_ready=1
    break
  fi
  sleep 1
done
if [[ "$frontend_ready" != "1" ]]; then
  echo "FALHA: frontend nao subiu na porta esperada ${FRONTEND_DEV_PORT}"
  tail -n 80 "$OUT_DIR/dev.log" || true
  exit 1
fi

echo "==> Waiting for product-api on exact port..."
api_ready=0
for _ in $(seq 1 180); do
  if curl -fsS "http://127.0.0.1:${PRODUCT_API_SERVER_PORT}/health" >/dev/null 2>&1; then
    api_ready=1
    break
  fi
  sleep 1
done
if [[ "$api_ready" != "1" ]]; then
  echo "FALHA: product-api nao subiu na porta esperada ${PRODUCT_API_SERVER_PORT}"
  tail -n 80 "$OUT_DIR/dev.log" || true
  exit 1
fi

curl -fsS "http://127.0.0.1:${PRODUCT_API_SERVER_PORT}/health" >"$OUT_DIR/health.json"

echo "==> Reading current library..."
curl -fsS "http://127.0.0.1:${PRODUCT_API_SERVER_PORT}/api/product/document-library" >"$OUT_DIR/document-library-before-reset.json"

echo "==> Deleting all currently indexed documents to isolate the test..."
python - <<'PY'
import json
import os
import urllib.request

port = os.environ.get("PRODUCT_API_SERVER_PORT", "8011")
base = f"http://127.0.0.1:{port}"
with urllib.request.urlopen(f"{base}/api/product/document-library", timeout=30) as resp:
    payload = json.loads(resp.read().decode("utf-8"))

doc_ids = [d["document_id"] for d in payload.get("documents", [])]
print(f"found {len(doc_ids)} documents before reset")

if doc_ids:
    body = json.dumps({"document_ids": doc_ids}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/product/delete-documents",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    print("delete result:", result)
else:
    print("library already empty")
PY

echo "==> Waiting for library to become empty..."
python - <<'PY'
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

port = os.environ.get("PRODUCT_API_SERVER_PORT", "8011")
out_dir = os.environ["OUT_DIR"]
url = f"http://127.0.0.1:{port}/api/product/document-library"
deadline = time.time() + 180

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        time.sleep(2)
        continue

    with open(os.path.join(out_dir, "document-library-empty-check.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    if not payload.get("documents"):
        print("library is empty")
        sys.exit(0)
    print(f"still {len(payload.get('documents', []))} docs in library")
    time.sleep(2)

print("FALHA: library did not become empty in time")
sys.exit(1)
PY

echo "==> Uploading only curated Action Plan corpus docs..."
curl -fsS -X POST "http://127.0.0.1:${PRODUCT_API_SERVER_PORT}/api/product/upload-documents"   -F "files=@$REPO_ROOT/data/corpus_revisado/frontend_demo_grounded_v1/audit/Access Review Evidence Log.pdf"   -F "files=@$REPO_ROOT/data/corpus_revisado/frontend_demo_grounded_v1/evidence/Privileged Account Approval Email.pdf"   -F "files=@$REPO_ROOT/data/corpus_revisado/frontend_demo_grounded_v1/audit/Governance Committee Minutes and Action Items.pdf"   -F "files=@$REPO_ROOT/data/corpus_revisado/frontend_demo_grounded_v1/audit/Nonconformance Report - Vendor Access Review.pdf"   >"$OUT_DIR/upload.json"

echo "==> Waiting for only curated docs to be indexed..."
python - <<'PY'
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

port = os.environ.get("PRODUCT_API_SERVER_PORT", "8011")
out_dir = os.environ["OUT_DIR"]
url = f"http://127.0.0.1:{port}/api/product/document-library"

wanted = {
    "Access Review Evidence Log.pdf",
    "Privileged Account Approval Email.pdf",
    "Governance Committee Minutes and Action Items.pdf",
    "Nonconformance Report - Vendor Access Review.pdf",
}
deadline = time.time() + 300

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, socket.timeout, TimeoutError):
        time.sleep(3)
        continue

    docs = payload.get("documents", [])
    indexed = [d for d in docs if d.get("status") == "indexed"]
    names = {d.get("name") for d in indexed}

    with open(os.path.join(out_dir, "document-library-latest.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    print("indexed names:", sorted(names))
    if names == wanted and len(indexed) == 4 and len(docs) == 4:
        with open(os.path.join(out_dir, "document-library.json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print("isolated library ready with exactly 4 curated docs")
        sys.exit(0)

    time.sleep(3)

print("FALHA: isolated library did not converge to exactly the 4 curated docs")
sys.exit(1)
PY

cat >"$FRONTEND_TMP_DIR/action-plan-isolated-selected-e2e.mjs" <<'EOF'
import fs from 'node:fs/promises';
import { chromium } from 'playwright';

const frontendPort = process.env.FRONTEND_DEV_PORT || '8080';
const apiPort = process.env.PRODUCT_API_SERVER_PORT || '8011';
const outDir = process.env.OUT_DIR;
const baseUrl = `http://127.0.0.1:${frontendPort}`;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } });

let runWorkflowResponse = null;
let generateDeckResponse = null;
let groundingPreviewResponse = null;

page.on('response', async (response) => {
  const url = response.url();
  try {
    if (url.includes('/api/product/run-workflow') && response.request().method() === 'POST') {
      runWorkflowResponse = await response.json();
    } else if (url.includes('/api/product/generate-deck') && response.request().method() === 'POST') {
      generateDeckResponse = await response.json();
    } else if (url.includes('/api/product/grounding-preview')) {
      groundingPreviewResponse = await response.json();
    }
  } catch {}
});

page.on('console', (msg) => {
  console.log(`[browser:${msg.type()}] ${msg.text()}`);
});

async function save(name) {
  await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
  await fs.writeFile(`${outDir}/${name}.html`, await page.content(), 'utf-8');
}

async function waitForEnabled(locator, timeoutMs = 300000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (await locator.isEnabled()) return;
    await page.waitForTimeout(1000);
  }
  throw new Error('Timed out waiting for button to become enabled');
}

const wantedDocs = [
  'Access Review Evidence Log.pdf',
  'Privileged Account Approval Email.pdf',
  'Governance Committee Minutes and Action Items.pdf',
  'Nonconformance Report - Vendor Access Review.pdf',
];

async function findSelectableDocButton(name) {
  const all = await page.locator('button[aria-pressed]').all();
  for (const btn of all) {
    const text = (await btn.innerText()).trim();
    if (text.includes(name)) return btn;
  }
  throw new Error(`Could not find selectable button for ${name}`);
}

async function normalizeSelection() {
  const state = [];
  for (const name of wantedDocs) {
    const btn = await findSelectableDocButton(name);
    const pressed = await btn.getAttribute('aria-pressed');
    if (pressed !== 'true') {
      await btn.click();
      await page.waitForTimeout(150);
    }
  }

  for (const name of wantedDocs) {
    const btn = await findSelectableDocButton(name);
    state.push({
      name,
      ariaPressed: await btn.getAttribute('aria-pressed'),
      text: (await btn.innerText()).trim(),
    });
  }

  await fs.writeFile(`${outDir}/selection-state.json`, JSON.stringify(state, null, 2), 'utf-8');
  await fs.writeFile(
    `${outDir}/selection-summary.txt`,
    state.map((x) => `${x.ariaPressed}	${x.name}`).join('\n'),
    'utf-8',
  );

  const selectedCount = state.filter((x) => x.ariaPressed === 'true').length;
  if (selectedCount !== 4) {
    throw new Error(`Selection normalization failed. selectedCount=${selectedCount}`);
  }
}

try {
  await page.goto(`${baseUrl}/app/workflows/action-plan`, { waitUntil: 'networkidle' });
  await save('01-action-plan-initial');

  for (const name of wantedDocs) {
    const btn = await findSelectableDocButton(name);
    await btn.waitFor({ state: 'visible', timeout: 120000 });
  }

  await normalizeSelection();
  await save('02-after-selection-normalization');

  const runButton = page.getByRole('button', { name: /Run Action Plan/i });
  await runButton.click();

  const deckButton = page.getByRole('button', { name: /Generate Deck/i });
  await waitForEnabled(deckButton, 300000);

  await page.getByText(/Action Plan & Evidence Review/i).waitFor({ timeout: 120000 });
  await save('03-after-run');

  await page.getByRole('tab', { name: /Board/i }).click();
  await save('04-board');

  await page.getByRole('tab', { name: /Table/i }).click();
  await save('05-table');

  await page.getByRole('tab', { name: /Timeline/i }).click();
  await save('06-timeline');

  const evidenceTabs = page.getByRole('tab', { name: /Evidence Gaps/i });
  if (await evidenceTabs.count()) {
    await evidenceTabs.first().click();
    await page.waitForTimeout(1000);
    await save('07-evidence-gaps');
  }

  await deckButton.click();
  await page.getByText(/action_plan_deck\.pptx/i).waitFor({ timeout: 180000 });
  await save('08-deck-generated');

  const openButtons = page.getByRole('button', { name: /^Open$/i });
  if (await openButtons.count()) {
    try {
      await Promise.all([
        page.waitForEvent('popup', { timeout: 5000 }).catch(() => null),
        openButtons.first().click(),
      ]);
    } catch {}
  }
  await save('09-after-open-click');

  const runHistory = await fetch(`http://127.0.0.1:${apiPort}/api/product/run-history`).then((r) => r.json());
  const artifacts = await fetch(`http://127.0.0.1:${apiPort}/api/product/artifacts`).then((r) => r.json());
  const library = await fetch(`http://127.0.0.1:${apiPort}/api/product/document-library`).then((r) => r.json());

  await fs.writeFile(`${outDir}/run-history.json`, JSON.stringify(runHistory, null, 2), 'utf-8');
  await fs.writeFile(`${outDir}/artifacts.json`, JSON.stringify(artifacts, null, 2), 'utf-8');
  await fs.writeFile(`${outDir}/document-library-after-e2e.json`, JSON.stringify(library, null, 2), 'utf-8');

  if (groundingPreviewResponse) {
    await fs.writeFile(`${outDir}/grounding-preview.json`, JSON.stringify(groundingPreviewResponse, null, 2), 'utf-8');
  }
  if (runWorkflowResponse) {
    await fs.writeFile(`${outDir}/run-workflow-response.json`, JSON.stringify(runWorkflowResponse, null, 2), 'utf-8');
  }
  if (generateDeckResponse) {
    await fs.writeFile(`${outDir}/generate-deck-response.json`, JSON.stringify(generateDeckResponse, null, 2), 'utf-8');
  }

  const summary = {
    ok: true,
    url: `${baseUrl}/app/workflows/action-plan`,
    screenshots: [
      '01-action-plan-initial.png',
      '02-after-selection-normalization.png',
      '03-after-run.png',
      '04-board.png',
      '05-table.png',
      '06-timeline.png',
      '07-evidence-gaps.png',
      '08-deck-generated.png',
      '09-after-open-click.png',
    ],
    outputs: [
      'selection-state.json',
      'selection-summary.txt',
      'grounding-preview.json',
      'run-workflow-response.json',
      'generate-deck-response.json',
      'run-history.json',
      'artifacts.json',
      'document-library.json',
      'document-library-after-e2e.json',
      'dev.log',
    ],
  };

  await fs.writeFile(`${outDir}/summary.json`, JSON.stringify(summary, null, 2), 'utf-8');
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await browser.close();
}
EOF

echo "==> Running isolated selected Playwright E2E..."
cd "$FRONTEND_DIR"
node "$FRONTEND_TMP_DIR/action-plan-isolated-selected-e2e.mjs"

echo
echo "==> Done."
echo "Send me these files:"
echo "  $OUT_DIR/summary.json"
echo "  $OUT_DIR/selection-state.json"
echo "  $OUT_DIR/selection-summary.txt"
echo "  $OUT_DIR/grounding-preview.json"
echo "  $OUT_DIR/run-workflow-response.json"
echo "  $OUT_DIR/generate-deck-response.json"
echo "  $OUT_DIR/run-history.json"
echo "  $OUT_DIR/artifacts.json"
echo "  $OUT_DIR/document-library.json"
echo "  $OUT_DIR/document-library-after-e2e.json"
echo "  $OUT_DIR/03-after-run.png"
echo "  $OUT_DIR/05-table.png"
echo "  $OUT_DIR/06-timeline.png"
echo "  $OUT_DIR/07-evidence-gaps.png"
echo "  $OUT_DIR/08-deck-generated.png"
