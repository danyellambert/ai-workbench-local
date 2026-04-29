#!/usr/bin/env bash
set -euo pipefail

LOCAL_FRONTEND_URL="${AI_DECISION_STUDIO_LOCAL_FRONTEND_URL:-http://127.0.0.1:8080}"
DOCKER_FRONTEND_URL="${AI_DECISION_STUDIO_DOCKER_FRONTEND_URL:-http://127.0.0.1:8059}"
REPORT_OUT="${AI_DECISION_STUDIO_UI_PARITY_REPORT:-../ai_decision_studio_functional_baseline/parity_reports/ui_route_parity_report.json}"
SCREENSHOT_DIR="${AI_DECISION_STUDIO_UI_PARITY_SCREENSHOTS:-../ai_decision_studio_functional_baseline/parity_reports/ui_route_screenshots}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_DIR="$ROOT_DIR/.tmp_playwright"
SPEC_FILE="$SPEC_DIR/ui_parity_local_vs_docker.cjs"

mkdir -p "$SPEC_DIR"
mkdir -p "$(dirname "$REPORT_OUT")"
mkdir -p "$SCREENSHOT_DIR"

cat > "$SPEC_DIR/package.json" <<'JSON'
{
  "private": true,
  "devDependencies": {
    "@playwright/test": "^1.56.0"
  }
}
JSON

if [ ! -d "$SPEC_DIR/node_modules/@playwright/test" ]; then
  npm --prefix "$SPEC_DIR" install --no-audit --no-fund
fi

cat > "$SPEC_FILE" <<'JS'
const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const localBase = process.env.LOCAL_FRONTEND_URL;
const dockerBase = process.env.DOCKER_FRONTEND_URL;
const reportOut = process.env.REPORT_OUT;
const screenshotDir = process.env.SCREENSHOT_DIR;

const skippedRoutes = new Set(
  (process.env.AI_DECISION_STUDIO_ROUTE_PARITY_SKIP || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
);

const routes = [
  '/',
  '/app',
  '/app/documents',
  '/app/workflows',
  '/app/workflows/document-review',
  '/app/workflows/comparison',
  '/app/workflows/action-plan',
  '/app/workflows/candidate-review',
  '/app/deck-center',
  '/app/history',
  '/app/run',
  '/app/lab/overview',
  '/app/lab/runtime',
  '/app/lab/chat',
  '/app/lab/workflow-inspector',
  '/app/lab/benchmarks',
  '/app/lab/evals',
  '/app/lab/artifacts',
  '/app/lab/evidenceops',
  '/app/lab/structured',
  '/app/lab/models',
  '/app/settings/runtime',
  '/app/settings/preferences',
];

function severe(text) {
  return /TypeError|ReferenceError|Cannot read properties|Minified React error|Uncaught|Application error|Something went wrong/i.test(text || '');
}

function safeName(base, route) {
  const label = base.includes('8059') ? 'docker' : 'local';
  const routeName = route === '/' ? 'root' : route.replaceAll('/', '_').replace(/^_/, '');
  return `${label}_${routeName}.png`;
}

async function inspectRoute(context, baseURL, route) {
  const page = await context.newPage();

  const consoleErrors = [];
  const pageErrors = [];
  const failedApiRequests = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  page.on('pageerror', (error) => {
    pageErrors.push(error.stack || error.message);
  });

  page.on('requestfailed', (request) => {
    const url = request.url();
    if (url.includes('/api/') || url.startsWith(baseURL)) {
      failedApiRequests.push(`${request.method()} ${url} -> ${request.failure()?.errorText}`);
    }
  });

  let status = null;
  let finalUrl = null;
  let body = '';
  let title = '';
  let error = null;

  try {
    const response = await page.goto(`${baseURL}${route}`, {
      waitUntil: 'networkidle',
      timeout: 60000,
    });

    status = response ? response.status() : null;
    finalUrl = page.url().replace(baseURL, '');
    await page.waitForTimeout(1000);
    body = (await page.locator('body').innerText({ timeout: 15000 })).trim();
    title = await page.title().catch(() => '');

    await page.screenshot({
      path: path.join(screenshotDir, safeName(baseURL, route)),
      fullPage: true,
    });
  } catch (exc) {
    error = String(exc && exc.stack ? exc.stack : exc);
  }

  await page.close();

  const severeConsoleErrors = consoleErrors.filter(severe);

  const ok =
    !error &&
    status !== null &&
    status < 500 &&
    body.length > 200 &&
    pageErrors.length === 0 &&
    failedApiRequests.length === 0 &&
    severeConsoleErrors.length === 0 &&
    !severe(body);

  return {
    ok,
    status,
    finalUrl,
    body_length: body.length,
    title,
    sample: body.slice(0, 500),
    error,
    page_errors: pageErrors,
    failed_api_requests: failedApiRequests,
    severe_console_errors: severeConsoleErrors,
  };
}

function compare(local, docker) {
  const minLen = Math.min(local.body_length || 0, docker.body_length || 0);
  const maxLen = Math.max(local.body_length || 0, docker.body_length || 0);
  const ratio = maxLen ? minLen / maxLen : 0;

  const localFinal = (local.finalUrl || '').replace(/\/$/, '');
  const dockerFinal = (docker.finalUrl || '').replace(/\/$/, '');

  return {
    ok:
      local.ok &&
      docker.ok &&
      local.status === docker.status &&
      ratio >= 0.35 &&
      localFinal === dockerFinal,
    same_status: local.status === docker.status,
    same_final_url: localFinal === dockerFinal,
    body_length_ratio: ratio,
  };
}

async function main() {
  fs.mkdirSync(screenshotDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();

  const results = [];

  for (const route of routes) {
    if (skippedRoutes.has(route)) {
      console.log(`SKIP ${route} dynamic route excluded from strict local-vs-Docker size parity`);
      results.push({
        route,
        ok: true,
        skipped: true,
        reason: 'dynamic route excluded from strict local-vs-Docker size parity',
      });
      continue;
    }
    const local = await inspectRoute(context, localBase, route);
    const docker = await inspectRoute(context, dockerBase, route);
    const parity = compare(local, docker);

    const item = { route, ok: parity.ok, parity, local, docker };
    results.push(item);

    console.log(`${item.ok ? 'OK' : 'FAIL'} ${route} local=${local.status}/${local.body_length} docker=${docker.status}/${docker.body_length} ratio=${parity.body_length_ratio.toFixed(2)}`);
  }

  await browser.close();

  const report = {
    ok: results.every((item) => item.ok),
    localBase,
    dockerBase,
    route_count: routes.length,
    failed_routes: results.filter((item) => !item.ok).map((item) => item.route),
    results,
  };

  fs.writeFileSync(reportOut, JSON.stringify(report, null, 2));

  console.log('');
  console.log(JSON.stringify({
    ok: report.ok,
    route_count: report.route_count,
    failed_routes: report.failed_routes,
    report: reportOut,
    screenshots: screenshotDir,
  }, null, 2));

  if (!report.ok) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
JS

echo "== Frontend UI parity local vs Docker =="
echo "local=$LOCAL_FRONTEND_URL"
echo "docker=$DOCKER_FRONTEND_URL"
echo "report=$REPORT_OUT"
echo "screenshots=$SCREENSHOT_DIR"

curl -fsS "$LOCAL_FRONTEND_URL" >/dev/null
curl -fsS "$DOCKER_FRONTEND_URL" >/dev/null

LOCAL_FRONTEND_URL="$LOCAL_FRONTEND_URL" \
DOCKER_FRONTEND_URL="$DOCKER_FRONTEND_URL" \
REPORT_OUT="$REPORT_OUT" \
SCREENSHOT_DIR="$SCREENSHOT_DIR" \
node "$SPEC_FILE"

echo
echo "== Frontend UI parity completed =="
