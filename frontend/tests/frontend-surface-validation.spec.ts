import fs from 'node:fs/promises';
import path from 'node:path';
import { expect, type Locator, type Page } from '@playwright/test';
import { test } from '@playwright/test';

const outputDir = process.env.FRONTEND_SURFACE_OUTPUT_DIR || path.resolve(process.cwd(), '.tmp_frontend_surface_e2e');
const screenshotDir = path.join(outputDir, 'screenshots');
const apiDir = path.join(outputDir, 'api');
const browserDir = path.join(outputDir, 'browser');
const domDir = path.join(outputDir, 'dom');
const statusDir = path.join(outputDir, 'status');
const traceDir = path.join(outputDir, 'traces');
const allowMutations = process.env.FRONTEND_SURFACE_ALLOW_MUTATIONS === '1';
const allowRerun = process.env.FRONTEND_SURFACE_ALLOW_RERUN !== '0';

const pages = [
  { slug: 'run', route: '/app/run', headingCandidates: ['Decision Workflows', 'Workflows'] },
  { slug: 'deck-center', route: '/app/deck-center', headingCandidates: ['Deck Center'] },
  { slug: 'history', route: '/app/history', headingCandidates: ['Run History'] },
  { slug: 'runtime-controls', route: '/app/settings/runtime', headingCandidates: ['Runtime Controls'] },
  { slug: 'preferences', route: '/app/settings/preferences', headingCandidates: ['Preferences'] },
] as const;

type StepRecord = {
  label: string;
  status: 'ok' | 'skipped' | 'error';
  note?: string;
  screenshot?: string;
};

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

async function writeJson(filePath: string, payload: unknown) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(payload, null, 2), 'utf-8');
}

function sanitizeFilePart(value: string, maxLength = 96): string {
  const sanitized = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'item';
  return sanitized.slice(0, maxLength).replace(/-+$/g, '') || 'item';
}

function compactLabel(value: string, fallback: string, maxLength = 72): string {
  const collapsed = value.replace(/\s+/g, ' ').trim();
  if (!collapsed) return fallback;
  return collapsed.length <= maxLength ? collapsed : collapsed.slice(0, maxLength).trimEnd();
}

function isIgnorableRequestFailure(url: string, failureText: string): boolean {
  return /ERR_ABORTED|NS_BINDING_ABORTED/i.test(failureText) || url.includes('/api/preferences');
}

async function locatorVisible(locator: Locator) {
  return locator.isVisible().catch(() => false);
}

async function collectTexts(locator: Locator, limit = 16): Promise<string[]> {
  const values = await locator.evaluateAll((nodes, max) => {
    return nodes
      .map((node) => (node.textContent || '').trim())
      .filter(Boolean)
      .slice(0, Number(max));
  }, limit).catch(() => [] as string[]);
  return Array.from(new Set(values));
}

async function captureStepScreenshot(page: Page, slug: string, label: string) {
  const fileName = `${slug}-${sanitizeFilePart(label)}.png`;
  const filePath = path.join(screenshotDir, fileName);
  await page.screenshot({ path: filePath, fullPage: true });
  return fileName;
}

async function recordStep(page: Page, slug: string, steps: StepRecord[], label: string, action: () => Promise<void>) {
  try {
    await action();
    const screenshot = await captureStepScreenshot(page, slug, label);
    steps.push({ label, status: 'ok', screenshot });
  } catch (error) {
    const screenshot = await captureStepScreenshot(page, slug, `${label}-error`).catch(() => undefined);
    steps.push({ label, status: 'error', note: String(error), screenshot });
  }
}

async function clickThroughVisibleTabs(page: Page, slug: string, steps: StepRecord[]) {
  const tabLabels = await collectTexts(page.locator('[role="tab"]'), 20);
  const visited: string[] = [];

  for (const label of tabLabels) {
    const tab = page.getByRole('tab', { name: label }).first();
    if (!(await locatorVisible(tab))) continue;
    await recordStep(page, slug, steps, `tab-${label}`, async () => {
      await tab.click();
      await page.waitForTimeout(250);
    });
    visited.push(label);
  }

  return visited;
}

async function chooseFirstMeaningfulOption(page: Page, trigger: Locator) {
  await trigger.click();
  await page.waitForTimeout(150);
  const options = page.locator('[role="option"]');
  const optionCount = await options.count();
  if (!optionCount) {
    await page.keyboard.press('Escape').catch(() => undefined);
    return null;
  }

  for (let index = 0; index < optionCount; index += 1) {
    const option = options.nth(index);
    const label = ((await option.textContent()) || '').trim();
    if (!label) continue;
    if (/^all\b/i.test(label) || /^status$/i.test(label) || /^workflow$/i.test(label)) continue;
    await option.click();
    await page.waitForTimeout(250);
    return label;
  }

  await page.keyboard.press('Escape').catch(() => undefined);
  return null;
}

async function inspectPopup(button: Locator, page: Page, slug: string, steps: StepRecord[], label: string) {
  await recordStep(page, slug, steps, label, async () => {
    const popupPromise = page.waitForEvent('popup', { timeout: 2000 }).catch(() => null);
    await button.click();
    const popup = await popupPromise;
    if (popup) {
      await popup.waitForLoadState('domcontentloaded').catch(() => undefined);
      await popup.close().catch(() => undefined);
    }
    await page.waitForTimeout(300);
  });
}

async function collectUiInventory(page: Page) {
  return {
    headings: await collectTexts(page.locator('main :is(h1,h2,h3)'), 18),
    tabs: await collectTexts(page.locator('[role="tab"]'), 24),
    buttons: await collectTexts(page.locator('button'), 32),
    links: await collectTexts(page.locator('a'), 20),
    inputs: await page.locator('input').evaluateAll((nodes) => nodes.map((node) => node.getAttribute('placeholder') || node.getAttribute('name') || node.getAttribute('type') || 'input')).catch(() => [] as string[]),
    comboboxCount: await page.locator('[role="combobox"]').count().catch(() => 0),
    switchCount: await page.locator('[role="switch"]').count().catch(() => 0),
    cardCount: await page.locator('.glass').count().catch(() => 0),
  };
}

async function exerciseRunPage(page: Page, slug: string, steps: StepRecord[]) {
  const targets = await page.locator('a[href*="/app/workflows/"]').evaluateAll((nodes) => {
    return nodes
      .map((node, index) => {
        const element = node as HTMLAnchorElement;
        const rawText = (element.textContent || '').replace(/\s+/g, ' ').trim();
        const heading = element.querySelector('h1, h2, h3, [data-testid="workflow-title"], strong')?.textContent?.replace(/\s+/g, ' ').trim();
        return {
          href: element.href || element.getAttribute('href') || '',
          label: heading || rawText || `workflow-${index + 1}`,
        };
      })
      .filter((item) => item.href);
  }).catch(() => [] as Array<{ href: string; label: string }>);

  for (const [index, target] of targets.slice(0, 2).entries()) {
    const label = compactLabel(target.label, `workflow-${index + 1}`);
    await recordStep(page, slug, steps, `open-${label}`, async () => {
      const destination = target.href.startsWith('http') ? target.href : new URL(target.href, page.url()).toString();
      await page.goto(destination, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(500);
      await page.goto('/app/run', { waitUntil: 'domcontentloaded', timeout: 15000 });
      await expect(page.locator('main').first()).toBeVisible();
      await page.waitForTimeout(350);
    });
  }
}

async function exerciseDeckCenterPage(page: Page, slug: string, steps: StepRecord[]) {
  const searchInput = page.getByPlaceholder(/search decks/i).first();
  if (await locatorVisible(searchInput)) {
    await recordStep(page, slug, steps, 'search-decks', async () => {
      await searchInput.fill('deck');
      await page.waitForTimeout(250);
    });
  }

  const comboboxes = page.locator('[role="combobox"]');
  const comboCount = await comboboxes.count();
  for (let index = 0; index < Math.min(comboCount, 2); index += 1) {
    const trigger = comboboxes.nth(index);
    if (!(await locatorVisible(trigger))) continue;
    await recordStep(page, slug, steps, `filter-${index + 1}`, async () => {
      await chooseFirstMeaningfulOption(page, trigger);
    });
  }

  const artifactCards = page.locator('button.glass');
  const artifactCount = await artifactCards.count();
  for (let index = 0; index < Math.min(artifactCount, 2); index += 1) {
    await recordStep(page, slug, steps, `select-artifact-${index + 1}`, async () => {
      await artifactCards.nth(index).click();
      await page.waitForTimeout(300);
    });
  }

  const openAssetButton = page.getByRole('button', { name: /open|preview|download/i }).first();
  if (await locatorVisible(openAssetButton)) {
    await inspectPopup(openAssetButton, page, slug, steps, 'inspect-artifact-asset');
  }
}

async function exerciseHistoryPage(page: Page, slug: string, steps: StepRecord[]) {
  const searchInput = page.getByPlaceholder(/search by run id/i).first();
  if (await locatorVisible(searchInput)) {
    await recordStep(page, slug, steps, 'search-history', async () => {
      await searchInput.fill('review');
      await page.waitForTimeout(250);
    });
  }

  const comboboxes = page.locator('[role="combobox"]');
  const comboCount = await comboboxes.count();
  for (let index = 0; index < Math.min(comboCount, 2); index += 1) {
    const trigger = comboboxes.nth(index);
    if (!(await locatorVisible(trigger))) continue;
    await recordStep(page, slug, steps, `history-filter-${index + 1}`, async () => {
      await chooseFirstMeaningfulOption(page, trigger);
    });
  }

  const runCards = page.locator('button.glass');
  const runCount = await runCards.count();
  for (let index = 0; index < Math.min(runCount, 2); index += 1) {
    await recordStep(page, slug, steps, `select-run-${index + 1}`, async () => {
      await runCards.nth(index).click();
      await page.waitForTimeout(400);
    });
  }

  const rerunButton = page.getByRole('button', { name: /^rerun$/i }).first();
  if (allowRerun && await locatorVisible(rerunButton) && await rerunButton.isEnabled().catch(() => false)) {
    await recordStep(page, slug, steps, 'rerun-selected-run', async () => {
      await rerunButton.click();
      await page.waitForTimeout(1200);
    });
  }

  const openArtifactButton = page.getByRole('button', { name: /^open$/i }).first();
  if (await locatorVisible(openArtifactButton)) {
    await inspectPopup(openArtifactButton, page, slug, steps, 'open-run-artifact');
  }
}

async function exerciseRuntimeControlsPage(page: Page, slug: string, steps: StepRecord[]) {
  const selects = page.locator('[role="combobox"]');
  const selectCount = await selects.count();
  for (let index = 0; index < Math.min(selectCount, 4); index += 1) {
    const trigger = selects.nth(index);
    if (!(await locatorVisible(trigger))) continue;
    await recordStep(page, slug, steps, `inspect-runtime-select-${index + 1}`, async () => {
      if (allowMutations) {
        await chooseFirstMeaningfulOption(page, trigger);
      } else {
        await trigger.click();
        await page.waitForTimeout(120);
        await page.keyboard.press('Escape');
      }
    });
  }

  const switches = page.locator('[role="switch"]');
  const switchCount = await switches.count();
  if (allowMutations && switchCount) {
    await recordStep(page, slug, steps, 'toggle-runtime-switch', async () => {
      await switches.first().click();
      await page.waitForTimeout(150);
    });
  }

  const saveButton = page.getByRole('button', { name: /save changes/i }).first();
  if (allowMutations && await locatorVisible(saveButton) && await saveButton.isEnabled().catch(() => false)) {
    await recordStep(page, slug, steps, 'save-runtime-controls', async () => {
      await saveButton.click();
      await page.waitForTimeout(700);
    });
  }

  const resetButton = page.getByRole('button', { name: /^reset$/i }).first();
  if (await locatorVisible(resetButton) && await resetButton.isEnabled().catch(() => false)) {
    await recordStep(page, slug, steps, 'reset-runtime-controls', async () => {
      await resetButton.click();
      await page.waitForTimeout(350);
    });
  }
}

async function exercisePreferencesPage(page: Page, slug: string, steps: StepRecord[]) {
  const testConnectionButtons = page.getByRole('button', { name: /test connection/i });
  const testButtonCount = await testConnectionButtons.count();
  if (testButtonCount) {
    await recordStep(page, slug, steps, 'test-first-connection', async () => {
      await testConnectionButtons.first().click();
      await page.waitForTimeout(1000);
    });
  }

  const selects = page.locator('[role="combobox"]');
  const selectCount = await selects.count();
  for (let index = 0; index < Math.min(selectCount, 3); index += 1) {
    const trigger = selects.nth(index);
    if (!(await locatorVisible(trigger))) continue;
    await recordStep(page, slug, steps, `inspect-preferences-select-${index + 1}`, async () => {
      if (allowMutations) {
        await chooseFirstMeaningfulOption(page, trigger);
      } else {
        await trigger.click();
        await page.waitForTimeout(120);
        await page.keyboard.press('Escape');
      }
    });
  }

  const switches = page.locator('[role="switch"]');
  const switchCount = await switches.count();
  if (allowMutations && switchCount) {
    await recordStep(page, slug, steps, 'toggle-preferences-rule', async () => {
      await switches.first().click();
      await page.waitForTimeout(300);
    });
  }
}

async function exercisePage(page: Page, slug: string, steps: StepRecord[]) {
  if (slug === 'run') return exerciseRunPage(page, slug, steps);
  if (slug === 'deck-center') return exerciseDeckCenterPage(page, slug, steps);
  if (slug === 'history') return exerciseHistoryPage(page, slug, steps);
  if (slug === 'runtime-controls') return exerciseRuntimeControlsPage(page, slug, steps);
  if (slug === 'preferences') return exercisePreferencesPage(page, slug, steps);
}

test.beforeAll(async () => {
  await ensureOutputDirs();
});

for (const pageDefinition of pages) {
  test(`frontend surface: ${pageDefinition.slug}`, async ({ page, context }) => {
    const apiEvents: Array<Record<string, unknown>> = [];
    const consoleEvents: Array<Record<string, unknown>> = [];
    const pageErrors: string[] = [];
    const failedRequests: Array<Record<string, unknown>> = [];
    const steps: StepRecord[] = [];

    await context.tracing.start({ screenshots: true, snapshots: true });

    page.on('response', async (response) => {
      const url = response.url();
      if (!url.includes('/api/')) return;
      const event: Record<string, unknown> = {
        url,
        status: response.status(),
        method: response.request().method(),
      };
      try {
        if ((response.headers()['content-type'] || '').includes('application/json')) {
          event.body = await response.json();
        }
      } catch {
        event.body = null;
      }
      apiEvents.push(event);
    });

    page.on('console', (msg) => {
      consoleEvents.push({ type: msg.type(), text: msg.text() });
    });

    page.on('pageerror', (error) => {
      pageErrors.push(String(error));
    });

    page.on('requestfailed', (request) => {
      const failure = request.failure()?.errorText || 'unknown';
      if (isIgnorableRequestFailure(request.url(), failure)) return;
      failedRequests.push({
        url: request.url(),
        method: request.method(),
        failure,
      });
    });

    await page.goto(pageDefinition.route, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('main').first()).toBeVisible();
    await page.waitForTimeout(1200);

    const initialScreenshot = await captureStepScreenshot(page, pageDefinition.slug, 'initial');
    steps.push({ label: 'initial-load', status: 'ok', screenshot: initialScreenshot });

    let matchedHeading: string | null = null;
    for (const candidate of pageDefinition.headingCandidates) {
      const headingLocator = page.locator('main :is(h1,h2)').filter({ hasText: candidate }).first();
      if (await headingLocator.count()) {
        matchedHeading = candidate;
        await expect(headingLocator).toBeVisible();
        break;
      }
    }

    const tabLabels = await clickThroughVisibleTabs(page, pageDefinition.slug, steps);
    await exercisePage(page, pageDefinition.slug, steps);

    const uiInventory = await collectUiInventory(page);
    const apiErrors = apiEvents.filter((event) => Number(event.status || 0) >= 500);
    const degradedResponses = apiEvents.filter((event) => {
      const status = Number(event.status || 0);
      return status >= 400 && status < 500;
    });

    const status = !matchedHeading
      ? 'failed'
      : pageErrors.length || apiErrors.length || failedRequests.length || steps.some((step) => step.status === 'error')
        ? 'failed'
        : degradedResponses.length
          ? 'degraded'
          : 'passed';

    const summary = {
      slug: pageDefinition.slug,
      route: pageDefinition.route,
      status,
      matchedHeading,
      headingCandidates: pageDefinition.headingCandidates,
      steps,
      tabLabels,
      uiInventory,
      apiEventCount: apiEvents.length,
      apiErrors,
      degradedResponses,
      failedRequests,
      pageErrors,
      consoleErrorCount: consoleEvents.filter((event) => ['error', 'warning'].includes(String(event.type))).length,
    };

    await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}.png`), fullPage: true });
    await fs.writeFile(path.join(domDir, `${pageDefinition.slug}.html`), await page.content(), 'utf-8');
    await writeJson(path.join(apiDir, `${pageDefinition.slug}.json`), { apiEvents, failedRequests });
    await writeJson(path.join(browserDir, `${pageDefinition.slug}.json`), { consoleEvents, pageErrors, steps, tabLabels, uiInventory, matchedHeading });
    await writeJson(path.join(statusDir, `${pageDefinition.slug}.json`), summary);
    await context.tracing.stop({ path: path.join(traceDir, `${pageDefinition.slug}.zip`) });
  });
}
