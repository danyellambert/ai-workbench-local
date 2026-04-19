import fs from 'node:fs/promises';
import path from 'node:path';
import { expect, test } from '@playwright/test';
const outputDir = process.env.CANDIDATE_REVIEW_OUTPUT_DIR || path.resolve(process.cwd(), '.tmp_candidate_review_validation');
const screenshotDir = path.join(outputDir, 'screenshots');
const apiDir = path.join(outputDir, 'api');
const browserDir = path.join(outputDir, 'browser');
const domDir = path.join(outputDir, 'dom');
const statusDir = path.join(outputDir, 'status');
const traceDir = path.join(outputDir, 'traces');
const candidateDocumentName = process.env.WORKFLOW_SURFACE_CANDIDATE_DOC_NAME || 'Sarah Chen - Senior ML Engineer CV.pdf';
type CheckStatus = 'passed' | 'degraded' | 'failed' | 'skipped';
type CheckResult = { name: string; status: CheckStatus; details?: string };
type ApiEvent = { url: string; status: number; method: string; body?: unknown };
const pages = [{ slug: 'candidate-review', route: '/app/workflows/candidate-review', title: 'Candidate Review' }] as const;
async function ensureOutputDirs() { await Promise.all([fs.mkdir(screenshotDir, { recursive: true }), fs.mkdir(apiDir, { recursive: true }), fs.mkdir(browserDir, { recursive: true }), fs.mkdir(domDir, { recursive: true }), fs.mkdir(statusDir, { recursive: true }), fs.mkdir(traceDir, { recursive: true })]); }
function deriveAssessmentStatus(checks: CheckResult[], pageErrors: string[], failedRequests: Array<Record<string, unknown>>) { if (pageErrors.length || checks.some((item) => item.status === 'failed')) return 'failed'; if (failedRequests.length || checks.some((item) => item.status === 'degraded')) return 'degraded'; return 'passed'; }
test.beforeAll(async () => { await ensureOutputDirs(); });
for (const pageDefinition of pages) {
  test(`candidate review surface: ${pageDefinition.slug}`, async ({ page, context }) => {
    await context.tracing.start({ screenshots: true, snapshots: true });
    const apiEvents: ApiEvent[] = []; const consoleEvents: Array<Record<string, unknown>> = []; const pageErrors: string[] = []; const failedRequests: Array<Record<string, unknown>> = []; const checks: CheckResult[] = []; const interactions: Array<Record<string, unknown>> = []; const addCheck = (name: string, status: CheckStatus, details?: string) => checks.push({ name, status, details });
    page.on('response', async (response) => { const url = response.url(); if (!url.includes('/api/')) return; const event: ApiEvent = { url, status: response.status(), method: response.request().method() }; try { const contentType = response.headers()['content-type'] || ''; if (contentType.includes('application/json')) event.body = await response.json(); } catch { event.body = null; } apiEvents.push(event); });
    page.on('console', (msg) => consoleEvents.push({ type: msg.type(), text: msg.text() }));
    page.on('pageerror', (error) => pageErrors.push(String(error)));
    page.on('requestfailed', (request) => failedRequests.push({ url: request.url(), method: request.method(), failure: request.failure()?.errorText || 'unknown' }));
    try {
      await page.goto(pageDefinition.route, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('main').getByRole('heading', { name: pageDefinition.title, exact: true }).first()).toBeVisible();
      addCheck('heading-visible', 'passed', pageDefinition.title);
      await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}-initial.png`), fullPage: true });
      if (pageDefinition.slug === 'candidate-review') {
        await expect(page.getByTestId('candidate-review-page')).toBeVisible();
        await page.getByTestId('candidate-review-document-trigger').click();
        await page.getByRole('option', { name: candidateDocumentName, exact: true }).click();
        interactions.push({ type: 'select-document', name: candidateDocumentName });
        await page.getByTestId('candidate-review-brief-input').fill('Evaluate this CV for a senior AI engineer role and highlight strengths, watchouts, seniority signals and interview focus areas.');
        const runResponsePromise = page.waitForResponse((response) => response.url().includes('/api/product/run-workflow') && response.request().method() === 'POST', { timeout: 180000 });
        await page.getByTestId('candidate-review-run-button').click();
        const runResponse = await runResponsePromise; addCheck('run-workflow-response', runResponse.ok() ? 'passed' : 'failed', String(runResponse.status()));
        await fs.writeFile(path.join(apiDir, 'candidate-review-run-response.json'), JSON.stringify(await runResponse.json().catch(() => null), null, 2), 'utf-8');
        await expect(page.getByTestId('candidate-review-status-panel')).toBeVisible(); await expect(page.getByTestId('candidate-review-candidate-name')).toBeVisible();
        await expect(page.getByTestId('candidate-review-generate-deck-button')).toBeEnabled({ timeout: 30000 });
        const deckResponsePromise = page.waitForResponse((response) => response.url().includes('/api/product/generate-deck') && response.request().method() === 'POST', { timeout: 180000 });
        await page.getByTestId('candidate-review-generate-deck-button').click();
        const deckResponse = await deckResponsePromise; addCheck('generate-deck-response', deckResponse.ok() ? 'passed' : 'failed', String(deckResponse.status()));
        await fs.writeFile(path.join(apiDir, 'candidate-review-generate-deck.json'), JSON.stringify(await deckResponse.json().catch(() => null), null, 2), 'utf-8');
      }
      await page.waitForTimeout(800); await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}-after-run.png`), fullPage: true });
    } catch (error) { addCheck('page-execution', 'failed', String(error)); throw error; }
    finally {
      await context.tracing.stop({ path: path.join(traceDir, `${pageDefinition.slug}.zip`) }).catch(() => undefined);
      const statusPayload = { slug: pageDefinition.slug, title: pageDefinition.title, route: pageDefinition.route, status: deriveAssessmentStatus(checks, pageErrors, failedRequests), checks, interactions, consoleEvents, failedRequests, pageErrors, apiEvents };
      await Promise.all([fs.writeFile(path.join(statusDir, `${pageDefinition.slug}.json`), JSON.stringify(statusPayload, null, 2), 'utf-8'), fs.writeFile(path.join(apiDir, `${pageDefinition.slug}.json`), JSON.stringify({ apiEvents, failedRequests }, null, 2), 'utf-8'), fs.writeFile(path.join(browserDir, `${pageDefinition.slug}.json`), JSON.stringify({ consoleEvents, pageErrors }, null, 2), 'utf-8'), fs.writeFile(path.join(domDir, `${pageDefinition.slug}.html`), await page.content().catch(() => ''), 'utf-8')]);
    }
  });
}
