import fs from "node:fs/promises";
import path from "node:path";
import { expect, test } from "@playwright/test";

const outputDir = process.env.AI_LAB_OUTPUT_DIR || path.resolve(process.cwd(), ".tmp_ai_lab_e2e");
const screenshotDir = path.join(outputDir, "screenshots");
const apiDir = path.join(outputDir, "api");
const browserDir = path.join(outputDir, "browser");
const domDir = path.join(outputDir, "dom");

const pages = [
  { slug: "overview", route: "/app/lab/overview", title: "AI Engineering Operating Console" },
  { slug: "runtime", route: "/app/lab/runtime", title: "Runtime & Observability" },
  { slug: "chat", route: "/app/lab/chat", title: "Document / Chat Experiments" },
  { slug: "workflow-inspector", route: "/app/lab/workflow-inspector", title: "Workflow Inspector" },
  { slug: "benchmarks", route: "/app/lab/benchmarks", title: "Benchmarks" },
  { slug: "evals", route: "/app/lab/evals", title: "Evals & Diagnosis" },
  { slug: "artifacts", route: "/app/lab/artifacts", title: "Experiments & Artifacts" },
  { slug: "evidenceops", route: "/app/lab/evidenceops", title: "EvidenceOps / MCP" },
] as const;

async function ensureOutputDirs() {
  await Promise.all([
    fs.mkdir(screenshotDir, { recursive: true }),
    fs.mkdir(apiDir, { recursive: true }),
    fs.mkdir(browserDir, { recursive: true }),
    fs.mkdir(domDir, { recursive: true }),
  ]);
}

test.beforeAll(async () => {
  await ensureOutputDirs();
});

for (const pageDefinition of pages) {
  test(`AI Lab page: ${pageDefinition.slug}`, async ({ page }) => {
    const apiEvents: Array<Record<string, unknown>> = [];
    const consoleEvents: Array<Record<string, unknown>> = [];
    const pageErrors: string[] = [];
    const failedRequests: Array<Record<string, unknown>> = [];

    page.on("response", async (response) => {
      const url = response.url();
      if (!url.includes("/api/")) return;
      const event: Record<string, unknown> = {
        url,
        status: response.status(),
        method: response.request().method(),
      };
      try {
        if ((response.headers()["content-type"] || "").includes("application/json")) {
          event.body = await response.json();
        }
      } catch {
        event.body = null;
      }
      apiEvents.push(event);
    });

    page.on("console", (msg) => {
      consoleEvents.push({ type: msg.type(), text: msg.text() });
    });

    page.on("pageerror", (error) => {
      pageErrors.push(String(error));
    });

    page.on("requestfailed", (request) => {
      failedRequests.push({
        url: request.url(),
        method: request.method(),
        failure: request.failure()?.errorText || "unknown",
      });
    });

    await page.goto(pageDefinition.route, { waitUntil: "domcontentloaded" });

    const mainHeading = page.locator("main").getByRole("heading", { name: pageDefinition.title, exact: true }).first();
    await expect(mainHeading).toBeVisible();
    await page.waitForTimeout(1200);

    if (pageDefinition.slug === "chat") {
      const input = page.getByPlaceholder(/Ask about your documents|AI LAB chat is unavailable/i);
      const sendButton = page.getByRole("button", { name: /send chat message/i });
      if (await input.isEnabled()) {
        await input.fill("What should I validate in this AI Lab page?");
      }
      if (await sendButton.isEnabled()) {
        await sendButton.click();
        await page.waitForTimeout(300);
      }
    }

    if (pageDefinition.slug === "workflow-inspector") {
      const execute = page.getByRole("button", { name: /execute task/i });
      if (await execute.isEnabled()) {
        await execute.click();
        await page.waitForTimeout(300);
      }
    }

    if (pageDefinition.slug === "evidenceops") {
      const searchTab = page.getByRole("tab", { name: /search/i });
      if (await searchTab.isVisible()) {
        await searchTab.click();
        const searchInput = page.getByPlaceholder(/semantic search query/i);
        if (await searchInput.isVisible()) {
          await searchInput.fill("vendor access review");
          const searchButton = page.getByRole("button", { name: /^search$/i });
          if (await searchButton.isEnabled()) {
            await searchButton.click();
            await page.waitForTimeout(300);
          }
        }
      }
    }

    const tabLabels = (await page.locator('[role="tab"]').allTextContents()).map((item) => item.trim()).filter(Boolean);
    for (const label of tabLabels) {
      const safeTab = label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      const tab = page.getByRole("tab", { name: label }).first();
      await tab.click();
      await page.waitForTimeout(250);
      await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}-${safeTab}.png`), fullPage: true });
    }

    await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}.png`), fullPage: true });
    await fs.writeFile(path.join(domDir, `${pageDefinition.slug}.html`), await page.content(), "utf-8");
    await fs.writeFile(path.join(apiDir, `${pageDefinition.slug}.json`), JSON.stringify({ apiEvents, failedRequests }, null, 2), "utf-8");
    await fs.writeFile(path.join(browserDir, `${pageDefinition.slug}.json`), JSON.stringify({ consoleEvents, pageErrors, tabLabels }, null, 2), "utf-8");

    expect(pageErrors).toEqual([]);
  });
}
