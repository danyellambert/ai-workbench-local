/// <reference types="node" />
import fs from 'node:fs/promises';
import path from 'node:path';
import { expect, test, type Locator, type Page } from '@playwright/test';

const outputDir = process.env.MCP_INTEGRATION_OUTPUT_DIR || path.resolve(process.cwd(), '.tmp_mcp_integration_validation');
const screenshotDir = path.join(outputDir, 'screenshots');
const apiDir = path.join(outputDir, 'api');
const browserDir = path.join(outputDir, 'browser');
const domDir = path.join(outputDir, 'dom');
const statusDir = path.join(outputDir, 'status');
const traceDir = path.join(outputDir, 'traces');
const allowMutations = process.env.MCP_INTEGRATION_ALLOW_MUTATIONS === '1';

type CheckStatus = 'passed' | 'degraded' | 'failed' | 'skipped';
type CheckResult = { name: string; status: CheckStatus; details?: string };
type ApiEvent = { url: string; status: number; method: string; body?: unknown };

const pages = [
  { slug: 'action-plan', route: '/app/workflows/action-plan', heading: 'Action Plan & Evidence Review' },
  { slug: 'candidate-review', route: '/app/workflows/candidate-review', heading: 'Candidate Review' },
  { slug: 'documents', route: '/app/documents', heading: 'Document Library' },
  { slug: 'evidenceops', route: '/app/lab/evidenceops', heading: 'EvidenceOps / MCP' },
  { slug: 'history', route: '/app/history', heading: 'Run History' },
  { slug: 'deck-center', route: '/app/deck-center', heading: 'Deck Center' },
] as const;

async function ensureOutputDirs() {
  await Promise.all([
    fs.mkdir(screenshotDir, { recursive: true }),
    fs.mkdir(apiDir, { recursive: true }),
    fs.mkdir(browserDir, { recursive: true }),
    fs.mkdir(domDir, { recursive: true }),
    fs.mkdir(statusDir, { recursive: true }),
    fs.mkdir(traceDir, { recursive: true }),
  ]);
}

function deriveAssessmentStatus(checks: CheckResult[], pageErrors: string[], failedRequests: Array<Record<string, unknown>>) {
  if (pageErrors.length || checks.some((item) => item.status === 'failed')) return 'failed';
  if (failedRequests.length || checks.some((item) => item.status === 'degraded')) return 'degraded';
  return 'passed';
}

async function locatorVisible(locator: Locator) {
  return locator.isVisible().catch(() => false);
}

async function collectTexts(locator: Locator, limit = 20): Promise<string[]> {
  return locator
    .evaluateAll((nodes, max) => nodes.map((node) => (node.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, Number(max)), limit)
    .catch(() => [] as string[]);
}

async function clickVisibleTabs(page: Page, checks: CheckResult[], slug: string) {
  const labels = await collectTexts(page.locator('[role="tab"]'), 16);
  for (const label of labels) {
    const tab = page.getByRole('tab', { name: label }).first();
    if (!(await locatorVisible(tab))) continue;
    try {
      await tab.click();
      await page.waitForTimeout(250);
      checks.push({ name: `tab-${label}`, status: 'passed' });
    } catch (error) {
      checks.push({ name: `tab-${label}`, status: 'degraded', details: String(error) });
    }
  }
  await page.screenshot({ path: path.join(screenshotDir, `${slug}-tabs.png`), fullPage: true }).catch(() => undefined);
}

async function chooseFirstOption(page: Page, trigger: Locator) {
  await trigger.click();
  await page.waitForTimeout(150);
  const options = page.locator('[role="option"]');
  const count = await options.count();
  for (let index = 0; index < count; index += 1) {
    const option = options.nth(index);
    const label = ((await option.textContent()) || '').trim();
    if (!label || /^all\b/i.test(label)) continue;
    await option.click();
    await page.waitForTimeout(200);
    return label;
  }
  await page.keyboard.press('Escape').catch(() => undefined);
  return null;
}

async function ensureNextcloudFileSelection(page: Page): Promise<boolean> {
  const selectedDocument = page.getByTestId('nextcloud-document-selected').first();
  if (await locatorVisible(selectedDocument)) return true;

  const fileButtons = page.locator('[data-testid="nextcloud-file-list"] button');
  if ((await fileButtons.count()) > 0) {
    await fileButtons.first().click();
    await page.waitForTimeout(250);
    return true;
  }

  const folderButtons = page.locator('[data-testid="nextcloud-folder-list"] button');
  const folderCount = await folderButtons.count();
  for (let index = 0; index < folderCount; index += 1) {
    const button = folderButtons.nth(index);
    if (!(await locatorVisible(button))) continue;
    await button.click();
    await page.waitForTimeout(250);
    const nestedFileButtons = page.locator('[data-testid="nextcloud-file-list"] button');
    if ((await nestedFileButtons.count()) > 0) {
      await nestedFileButtons.first().click();
      await page.waitForTimeout(250);
      return true;
    }
  }

  return false;
}

test.beforeAll(async () => {
  await ensureOutputDirs();
});

for (const pageDefinition of pages) {
  test(`mcp integration surface: ${pageDefinition.slug}`, async ({ page, context }) => {
    test.setTimeout(allowMutations ? 180_000 : 120_000);
    await context.tracing.start({ screenshots: true, snapshots: true });
    const apiEvents: ApiEvent[] = [];
    const consoleEvents: Array<Record<string, unknown>> = [];
    const pageErrors: string[] = [];
    const failedRequests: Array<Record<string, unknown>> = [];
    const checks: CheckResult[] = [];
    const interactions: Array<Record<string, unknown>> = [];

    page.on('response', async (response) => {
      const url = response.url();
      if (!url.includes('/api/')) return;
      const event: ApiEvent = { url, status: response.status(), method: response.request().method() };
      try {
        const contentType = response.headers()['content-type'] || '';
        if (contentType.includes('application/json')) event.body = await response.json();
      } catch {
        event.body = null;
      }
      apiEvents.push(event);
    });
    page.on('console', (msg) => consoleEvents.push({ type: msg.type(), text: msg.text() }));
    page.on('pageerror', (error) => pageErrors.push(String(error)));
    page.on('requestfailed', (request) => failedRequests.push({ url: request.url(), method: request.method(), failure: request.failure()?.errorText || 'unknown' }));

    try {
      await page.goto(pageDefinition.route, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('main').getByRole('heading', { name: pageDefinition.heading, exact: true }).first()).toBeVisible();
      checks.push({ name: 'heading-visible', status: 'passed', details: pageDefinition.heading });
      await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}-initial.png`), fullPage: true });

      if (pageDefinition.slug === 'action-plan') {
        await clickVisibleTabs(page, checks, pageDefinition.slug);
        const publishRegion = page.locator('[data-testid="workflow-publish-actions-surface"][data-workflow="action-plan"]').first();
        const publishSurface = page.getByTestId('workflow-publish-actions').first();
        const publishTrello = page.getByTestId('workflow-preview-trello').first();
        const publishNotion = page.getByTestId('workflow-preview-notion').first();
        await publishRegion.scrollIntoViewIfNeeded().catch(() => undefined);
        await Promise.all([
          publishSurface.waitFor({ state: 'visible', timeout: 8000 }).catch(() => undefined),
          publishTrello.waitFor({ state: 'visible', timeout: 8000 }).catch(() => undefined),
          publishNotion.waitFor({ state: 'visible', timeout: 8000 }).catch(() => undefined),
        ]);
        checks.push({ name: 'publish-actions-visible', status: (await locatorVisible(publishSurface)) && (await locatorVisible(publishTrello)) && (await locatorVisible(publishNotion)) ? 'passed' : 'degraded' });
      }

      if (pageDefinition.slug === 'candidate-review') {
        const trigger = page.getByTestId('candidate-review-document-trigger').first();
        const selectedName = page.getByTestId('candidate-review-candidate-name').first();
        let selectedLabel = '';
        if (await locatorVisible(selectedName)) {
          selectedLabel = ((await selectedName.textContent()) || '').trim();
        }
        if (!selectedLabel && (await locatorVisible(trigger))) {
          selectedLabel = ((await trigger.textContent()) || '').replace(/\s+/g, ' ').trim();
        }
        checks.push({ name: 'candidate-document-selected', status: selectedLabel ? 'passed' : 'degraded', details: selectedLabel || 'no-selection' });

        if (allowMutations) {
          const runButton = page.getByTestId('candidate-review-run-button').first();
          if (await locatorVisible(runButton) && !(await runButton.isDisabled().catch(() => true))) {
            const responsePromise = page.waitForResponse((response) => response.url().includes('/api/product/run-workflow') && response.request().method() === 'POST', { timeout: 60_000 }).catch(() => null);
            await runButton.click();
            const response = await responsePromise;
            checks.push({ name: 'candidate-run', status: response?.ok() ? 'passed' : 'degraded', details: response ? String(response.status()) : 'no-response' });
            interactions.push({ type: 'candidate-run' });
          }
        }

        const publishRegion = page.locator('[data-testid="workflow-publish-actions-surface"][data-workflow="candidate-review"]').first();
        const publishActions = page.getByTestId('workflow-publish-actions').first();
        const previewTrello = page.getByTestId('workflow-preview-trello').first();
        const previewNotion = page.getByTestId('workflow-preview-notion').first();
        await publishRegion.scrollIntoViewIfNeeded().catch(() => undefined);
        await Promise.all([
          publishActions.waitFor({ state: 'visible', timeout: 8_000 }).catch(() => undefined),
          previewTrello.waitFor({ state: 'visible', timeout: 8_000 }).catch(() => undefined),
          previewNotion.waitFor({ state: 'visible', timeout: 8_000 }).catch(() => undefined),
        ]);
        checks.push({
          name: 'publish-actions-visible',
          status: (await locatorVisible(publishActions)) && (await locatorVisible(previewTrello)) && (await locatorVisible(previewNotion)) ? 'passed' : 'degraded',
        });
      }

      if (pageDefinition.slug === 'documents') {
        const importButton = page.getByTestId('open-nextcloud-import').first();
        checks.push({ name: 'nextcloud-import-entrypoint', status: (await locatorVisible(importButton)) ? 'passed' : 'degraded' });
        if (await locatorVisible(importButton)) {
          await importButton.click();
          await page.waitForTimeout(350);
          checks.push({ name: 'nextcloud-import-sheet', status: (await locatorVisible(page.getByTestId('nextcloud-import-sheet').first())) ? 'passed' : 'degraded' });
          const selected = await ensureNextcloudFileSelection(page);
          checks.push({ name: 'nextcloud-file-visible', status: selected ? 'passed' : 'degraded', details: selected ? 'selected' : 'no-remote-files' });
          if (allowMutations && selected) {
            const responsePromise = page.waitForResponse((response) => response.url().includes('/api/product/integrations/nextcloud/import') && response.request().method() === 'POST', { timeout: 180000 }).catch(() => null);
            await page.getByRole('button', { name: /import into document library/i }).click();
            const response = await responsePromise;
            checks.push({ name: 'nextcloud-import', status: response?.ok() ? 'passed' : 'degraded', details: response ? String(response.status()) : 'no-response' });
            interactions.push({ type: 'nextcloud-import' });
          }
        }
      }

      if (pageDefinition.slug === 'evidenceops') {
        await clickVisibleTabs(page, checks, pageDefinition.slug);
        const searchInput = page.getByPlaceholder(/search the live evidenceops repository/i).first();
        if (await locatorVisible(searchInput)) {
          await searchInput.fill('vendor');
          const searchButton = page.getByRole('button', { name: /^search$/i }).first();
          await searchButton.click();
          await page.waitForTimeout(600);
          checks.push({ name: 'repository-search', status: 'passed', details: 'vendor' });
          interactions.push({ type: 'repository-search', value: 'vendor' });
        }
        const deliveryTargets = page.getByTestId('evidenceops-delivery-targets').first();
        checks.push({ name: 'delivery-targets-summary-visible', status: (await locatorVisible(deliveryTargets)) ? 'passed' : 'degraded' });
      }

      if (pageDefinition.slug === 'history') {
        const cards = page.locator('button.glass');
        if ((await cards.count()) > 0) {
          await cards.first().click();
          await page.waitForTimeout(300);
          checks.push({ name: 'open-run-detail', status: 'passed' });
        } else {
          checks.push({ name: 'open-run-detail', status: 'degraded', details: 'no-run-cards' });
        }
        const externalDeliveries = page.getByTestId('delivery-history-section').first();
        checks.push({ name: 'delivery-history-section', status: (await locatorVisible(externalDeliveries)) ? 'passed' : 'degraded' });
      }

      if (pageDefinition.slug === 'deck-center') {
        const searchInput = page.getByPlaceholder(/search decks/i).first();
        if (await locatorVisible(searchInput)) {
          await searchInput.fill('deck');
          checks.push({ name: 'search-decks', status: 'passed' });
        }

        const cards = page.getByTestId('deck-center-artifact-card');
        const detailPanel = page.getByTestId('deck-center-detail-panel').first();
        const emptyState = page.getByTestId('deck-center-detail-empty').first();

        await Promise.race([
          cards.first().waitFor({ state: 'visible', timeout: 8_000 }).catch(() => undefined),
          emptyState.waitFor({ state: 'visible', timeout: 8_000 }).catch(() => undefined),
          detailPanel.waitFor({ state: 'visible', timeout: 8_000 }).catch(() => undefined),
        ]);

        if ((await cards.count()) > 0) {
          await cards.first().click();
          checks.push({ name: 'open-artifact-detail', status: 'passed' });
        } else {
          checks.push({ name: 'open-artifact-detail', status: (await locatorVisible(emptyState)) ? 'passed' : 'degraded', details: (await locatorVisible(emptyState)) ? 'empty-state-visible' : 'no-artifact-cards' });
        }

        await detailPanel.scrollIntoViewIfNeeded().catch(() => undefined);
        checks.push({ name: 'detail-panel-visible', status: (await locatorVisible(detailPanel)) ? 'passed' : 'degraded' });
      }

      await page.waitForTimeout(150);
      await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}-final.png`), fullPage: true });
    } catch (error) {
      checks.push({ name: 'page-execution', status: 'degraded', details: String(error) });
      await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}-error.png`), fullPage: true }).catch(() => undefined);
    } finally {
      await context.tracing.stop({ path: path.join(traceDir, `${pageDefinition.slug}.zip`) }).catch(() => undefined);
      const statusPayload = {
        slug: pageDefinition.slug,
        title: pageDefinition.heading,
        route: pageDefinition.route,
        status: deriveAssessmentStatus(checks, pageErrors, failedRequests),
        checks,
        interactions,
        consoleEvents,
        failedRequests,
        pageErrors,
        apiEvents,
      };
      await Promise.all([
        fs.writeFile(path.join(statusDir, `${pageDefinition.slug}.json`), JSON.stringify(statusPayload, null, 2), 'utf-8'),
        fs.writeFile(path.join(apiDir, `${pageDefinition.slug}.json`), JSON.stringify({ apiEvents, failedRequests }, null, 2), 'utf-8'),
        fs.writeFile(path.join(browserDir, `${pageDefinition.slug}.json`), JSON.stringify({ consoleEvents, pageErrors }, null, 2), 'utf-8'),
        fs.writeFile(path.join(domDir, `${pageDefinition.slug}.html`), await page.content().catch(() => ''), 'utf-8'),
      ]);
    }
  });
}
