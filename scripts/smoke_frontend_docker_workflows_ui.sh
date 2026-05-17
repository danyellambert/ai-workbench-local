#!/usr/bin/env bash
set -euo pipefail

FRONTEND_BASE_URL="${AI_DECISION_STUDIO_FRONTEND_BASE_URL:-http://127.0.0.1:8059}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_DIR="$ROOT_DIR/.tmp_playwright"
SPEC_FILE="$SPEC_DIR/frontend_workflows_ui.spec.js"
mkdir -p "$SPEC_DIR"

cat > "$SPEC_DIR/package.json" <<'JSON'
{
  "private": true,
  "devDependencies": {
    "@playwright/test": "^1.56.0"
  }
}
JSON

if [ ! -d "$SPEC_DIR/node_modules/@playwright/test" ]; then
  echo
  echo "== Install local Playwright test dependency =="
  npm --prefix "$SPEC_DIR" install --no-audit --no-fund
fi

echo "== Frontend Docker workflow UI smoke =="
echo "frontend=$FRONTEND_BASE_URL"

echo
echo "== Check frontend health =="
curl -fsS "$FRONTEND_BASE_URL/health" | python3 -m json.tool

cat > "$SPEC_FILE" <<'JS'
const { test, expect } = require('@playwright/test');

const baseURL = process.env.FRONTEND_BASE_URL || 'http://127.0.0.1:8059';

const cases = [
  {
    name: 'document-review',
    path: '/app/workflows/document-review',
    button: /run review/i,
  },
  {
    name: 'policy-comparison',
    path: '/app/workflows/comparison',
    button: /run comparison/i,
  },
];

test.describe.configure({ mode: 'serial' });

for (const item of cases) {
  test(`${item.name} run does not blank the page`, async ({ page }) => {
    test.setTimeout(180000);

    const consoleErrors = [];
    const pageErrors = [];
    const failedRequests = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (error) => {
      pageErrors.push(error.stack || error.message);
    });

    page.on('requestfailed', (request) => {
      const url = request.url();
      if (url.includes('/api/') || url.includes(baseURL)) {
        failedRequests.push(`${request.method()} ${url} -> ${request.failure()?.errorText}`);
      }
    });

    await page.goto(`${baseURL}${item.path}`, { waitUntil: 'networkidle', timeout: 60000 });

    const beforeText = await page.locator('body').innerText({ timeout: 15000 });
    expect(beforeText.trim().length, `${item.name} initial body should not be blank`).toBeGreaterThan(200);

    const button = page.getByRole('button', { name: item.button }).first();
    await expect(button).toBeVisible({ timeout: 30000 });

    const runResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes('/api/product/run-workflow') &&
        response.request().method() === 'POST',
      { timeout: 150000 }
    ).catch((error) => error);

    await button.click({ timeout: 30000 });

    const runResponse = await runResponsePromise;

    if (runResponse instanceof Error) {
      throw new Error(`${item.name} did not observe run-workflow response: ${runResponse.message}`);
    }

    expect(runResponse.status(), `${item.name} run-workflow HTTP status`).toBeLessThan(500);

    await page.waitForTimeout(5000);

    const afterText = await page.locator('body').innerText({ timeout: 15000 });
    const normalized = afterText.trim();

    await page.screenshot({
      path: `/tmp/ai_decision_studio_${item.name}_after_run.png`,
      fullPage: true,
    });

    expect(normalized.length, `${item.name} body after run should not be blank`).toBeGreaterThan(300);
    expect(normalized).not.toMatch(/Application error|Something went wrong|Cannot read properties|Minified React error/i);

    expect(pageErrors, `${item.name} page errors`).toEqual([]);
    expect(failedRequests, `${item.name} failed API requests`).toEqual([]);

    const severeConsoleErrors = consoleErrors.filter((entry) =>
      /TypeError|ReferenceError|Cannot read properties|Minified React error|Uncaught/i.test(entry)
    );

    expect(severeConsoleErrors, `${item.name} severe console errors`).toEqual([]);
  });
}
JS

echo
echo "== Ensure Playwright Chromium =="
if [ "${SKIP_PLAYWRIGHT_INSTALL:-0}" != "1" ]; then
  (cd "$SPEC_DIR" && npx playwright install chromium)
fi

echo
echo "== Run Playwright UI smoke =="
(
  cd "$SPEC_DIR"
  FRONTEND_BASE_URL="$FRONTEND_BASE_URL" npx playwright test "$SPEC_FILE" \
    --browser=chromium \
    --workers=1 \
    --reporter=line
)

echo
echo "== Frontend Docker workflow UI smoke completed =="
