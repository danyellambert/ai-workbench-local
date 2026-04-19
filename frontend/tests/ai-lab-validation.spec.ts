import fs from "node:fs/promises";
import path from "node:path";
import { expect, test } from "@playwright/test";

const outputDir = process.env.AI_LAB_OUTPUT_DIR || path.resolve(process.cwd(), ".tmp_ai_lab_e2e");
const screenshotDir = path.join(outputDir, "screenshots");
const apiDir = path.join(outputDir, "api");
const browserDir = path.join(outputDir, "browser");
const domDir = path.join(outputDir, "dom");
const assessmentDir = path.join(outputDir, "assessments");

const pages = [
  { slug: "overview", route: "/app/lab/overview", title: "AI Engineering Operating Console", endpoint: "/api/lab/overview" },
  { slug: "runtime", route: "/app/lab/runtime", title: "Runtime & Observability", endpoint: "/api/lab/runtime" },
  { slug: "chat", route: "/app/lab/chat", title: "Document / Chat Experiments", endpoint: "/api/lab/chat" },
  { slug: "workflow-inspector", route: "/app/lab/workflow-inspector", title: "Workflow Inspector", endpoint: "/api/lab/workflow-inspector" },
  { slug: "benchmarks", route: "/app/lab/benchmarks", title: "Benchmarks", endpoint: "/api/lab/benchmarks" },
  { slug: "evals", route: "/app/lab/evals", title: "Evals & Diagnosis", endpoint: "/api/lab/evals" },
  { slug: "artifacts", route: "/app/lab/artifacts", title: "Experiments & Artifacts", endpoint: "/api/lab/artifacts" },
  { slug: "evidenceops", route: "/app/lab/evidenceops", title: "EvidenceOps / MCP", endpoint: "/api/lab/evidenceops" },
] as const;

type CheckStatus = "passed" | "degraded" | "failed" | "skipped";

type CheckResult = {
  name: string;
  status: CheckStatus;
  details?: string;
};

type ApiEvent = {
  url: string;
  status: number;
  method: string;
  body?: unknown;
};

async function ensureOutputDirs() {
  await Promise.all([
    fs.mkdir(screenshotDir, { recursive: true }),
    fs.mkdir(apiDir, { recursive: true }),
    fs.mkdir(browserDir, { recursive: true }),
    fs.mkdir(domDir, { recursive: true }),
    fs.mkdir(assessmentDir, { recursive: true }),
  ]);
}

function getCountsForPayload(slug: string, payload: Record<string, unknown>) {
  const readListLength = (key: string) => Array.isArray(payload[key]) ? payload[key].length : 0;

  switch (slug) {
    case "overview":
      return {
        kpis: readListLength("kpis"),
        alerts: readListLength("alerts"),
        workflowMix: Array.isArray(payload.workflow_mix) ? payload.workflow_mix.length : 0,
      };
    case "runtime":
      return {
        generationRows: readListLength("generation_rows") || readListLength("generationRows"),
        diagnosticsRows: readListLength("diagnostics_rows") || readListLength("diagnosticsRows"),
        vectorRows: readListLength("vector_rows") || readListLength("vectorRows"),
      };
    case "chat":
      return {
        messages: readListLength("messages"),
        sessions: readListLength("sessions"),
        selectedDocuments: readListLength("selected_documents") || readListLength("selectedDocuments"),
      };
    case "workflow-inspector":
      return {
        taskOptions: readListLength("task_options") || readListLength("taskOptions"),
        recentCases: readListLength("recent_cases") || readListLength("recentCases"),
      };
    case "benchmarks":
      return {
        models: readListLength("models"),
        presets: readListLength("presets"),
        retrievalObservations: readListLength("retrievalObservations") || readListLength("retrieval_observations"),
      };
    case "evals":
      return {
        suites: readListLength("suites"),
        cases: readListLength("cases"),
        watchlist: readListLength("watchlist"),
      };
    case "artifacts":
      return {
        artifacts: readListLength("artifacts"),
        diagnostics: readListLength("diagnostics"),
        recentCaptures: readListLength("recentCaptures") || readListLength("recent_captures"),
      };
    case "evidenceops":
      return {
        tools: readListLength("tools"),
        actions: readListLength("actions"),
        operations: readListLength("operations"),
      };
    default:
      return {};
  }
}

function summarizeRelevantPayload(slug: string, payload: unknown) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return {
      available: false,
      metaSource: null,
      status: null,
      degradedReason: null,
      lastUpdatedAt: null,
      counts: {},
    };
  }

  const record = payload as Record<string, unknown>;
  const meta = record.meta && typeof record.meta === "object" && !Array.isArray(record.meta)
    ? (record.meta as Record<string, unknown>)
    : null;

  return {
    available: true,
    metaSource: typeof meta?.source === "string" ? meta.source : null,
    status: typeof record.status === "string" ? record.status : null,
    degradedReason: typeof record.degraded_reason === "string" ? record.degraded_reason : null,
    lastUpdatedAt: typeof record.last_updated_at === "string" ? record.last_updated_at : null,
    counts: getCountsForPayload(slug, record),
  };
}

function deriveAssessmentStatus(checks: CheckResult[], pageErrors: string[], failedRequests: Array<Record<string, unknown>>) {
  if (pageErrors.length || checks.some((item) => item.status === "failed")) {
    return "failed";
  }
  if (failedRequests.length || checks.some((item) => item.status === "degraded")) {
    return "degraded";
  }
  return "passed";
}

async function persistPageArtifacts(pageDefinition: (typeof pages)[number], page: any, payload: unknown, apiEvents: ApiEvent[], failedRequests: Array<Record<string, unknown>>, consoleEvents: Array<Record<string, unknown>>, pageErrors: string[], checks: CheckResult[], interactions: Array<Record<string, unknown>>, tabLabels: string[]) {
  const payloadSummary = summarizeRelevantPayload(pageDefinition.slug, payload);
  const assessmentStatus = deriveAssessmentStatus(checks, pageErrors, failedRequests);
  const relevantApiEvents = apiEvents.filter((event) => event.url.includes(pageDefinition.endpoint));
  const assessment = {
    slug: pageDefinition.slug,
    title: pageDefinition.title,
    route: pageDefinition.route,
    expectedEndpoint: pageDefinition.endpoint,
    status: assessmentStatus,
    checks,
    interactions,
    tabLabels,
    apiSummary: {
      totalApiEvents: apiEvents.length,
      relevantApiEvents: relevantApiEvents.length,
      failedRequests,
    },
    payloadSummary,
    consoleEvents,
    pageErrors,
  };

  await page.screenshot({ path: path.join(screenshotDir, `${pageDefinition.slug}.png`), fullPage: true }).catch(() => undefined);
  const content = await page.content().catch(() => "");
  await Promise.all([
    fs.writeFile(path.join(domDir, `${pageDefinition.slug}.html`), content, "utf-8"),
    fs.writeFile(path.join(apiDir, `${pageDefinition.slug}.json`), JSON.stringify({ apiEvents, failedRequests, payload }, null, 2), "utf-8"),
    fs.writeFile(path.join(browserDir, `${pageDefinition.slug}.json`), JSON.stringify({ consoleEvents, pageErrors, tabLabels }, null, 2), "utf-8"),
    fs.writeFile(path.join(assessmentDir, `${pageDefinition.slug}.json`), JSON.stringify(assessment, null, 2), "utf-8"),
  ]);

  return assessment;
}

test.beforeAll(async () => {
  await ensureOutputDirs();
});

for (const pageDefinition of pages) {
  test(`AI Lab page: ${pageDefinition.slug}`, async ({ page }) => {
    const apiEvents: ApiEvent[] = [];
    const consoleEvents: Array<Record<string, unknown>> = [];
    const pageErrors: string[] = [];
    const failedRequests: Array<Record<string, unknown>> = [];
    const checks: CheckResult[] = [];
    const interactions: Array<Record<string, unknown>> = [];
    let payload: unknown = null;

    const addCheck = (name: string, status: CheckStatus, details?: string) => {
      checks.push({ name, status, details });
    };

    page.on("response", async (response) => {
      const url = response.url();
      if (!url.includes("/api/")) return;
      const event: ApiEvent = {
        url,
        status: response.status(),
        method: response.request().method(),
      };
      try {
        if ((response.headers()["content-type"] || "").includes("application/json")) {
          event.body = await response.json();
          if (url.includes(pageDefinition.endpoint)) {
            payload = event.body;
          } else if (
            pageDefinition.slug === "chat" &&
            response.request().method() === "POST" &&
            url.includes("/api/lab/chat/sessions/") &&
            event.body &&
            typeof event.body === "object" &&
            !Array.isArray(event.body) &&
            "page" in (event.body as Record<string, unknown>)
          ) {
            const pagePayload = (event.body as { page?: unknown }).page;
            if (pagePayload && typeof pagePayload === "object" && !Array.isArray(pagePayload)) {
              payload = pagePayload;
            }
          }
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

    const expectedEndpointResponse = page.waitForResponse(
      (response) => response.url().includes(pageDefinition.endpoint) && response.request().method() === "GET",
      { timeout: 15000 },
    ).catch(() => null);

    try {
      await page.goto(pageDefinition.route, { waitUntil: "domcontentloaded" });

      const mainHeading = page.locator("main").getByRole("heading", { name: pageDefinition.title, exact: true }).first();
      await expect(mainHeading).toBeVisible();
      addCheck("heading-visible", "passed", pageDefinition.title);

      const firstEndpoint = await expectedEndpointResponse;
      if (firstEndpoint && firstEndpoint.status() >= 200 && firstEndpoint.status() < 300) {
        addCheck("expected-endpoint-response", "passed", `${pageDefinition.endpoint} -> ${firstEndpoint.status()}`);
      } else {
        addCheck("expected-endpoint-response", "failed", `Did not observe a successful response for ${pageDefinition.endpoint}`);
      }

      await page.waitForTimeout(1200);

      if (pageDefinition.slug === "chat") {
        const input = page.getByPlaceholder(/Ask about your documents|AI LAB chat is unavailable/i).first();
        const sendButton = page.getByRole("button", { name: /send chat message/i }).first();
        const inputVisible = await input.isVisible().catch(() => false);
        if (inputVisible) {
          await input.fill("Please summarize the main grounded signals shown on this AI LAB chat page.");
          await page.waitForTimeout(150);
        }
        const buttonEnabled = await sendButton.isEnabled().catch(() => false);
        if (inputVisible && buttonEnabled) {
          const postResponse = page.waitForResponse(
            (response) => response.url().includes("/api/lab/chat/sessions/") && response.request().method() === "POST",
            { timeout: 45000 },
          ).catch(() => null);
          await sendButton.click();
          const response = await postResponse;
          if (response && response.status() >= 200 && response.status() < 300) {
            addCheck("chat-send", "passed", `POST ${response.url()} -> ${response.status()}`);
            interactions.push({ action: "chat-send", status: "ok", responseStatus: response.status() });
          } else {
            addCheck("chat-send", "failed", "Send button was enabled after entering a prompt but no successful chat POST was observed.");
            interactions.push({ action: "chat-send", status: "failed" });
          }
          await page.waitForTimeout(700);
        } else {
          addCheck("chat-send", "degraded", "Chat send is unavailable in the current runtime state.");
          interactions.push({ action: "chat-send", status: "degraded" });
        }
      }

      if (pageDefinition.slug === "workflow-inspector") {
        const execute = page.getByRole("button", { name: /execute task/i }).first();
        const requestInput = page.getByPlaceholder(/Describe the run you want to execute/i).first();
        const executeEnabled = await execute.isEnabled().catch(() => false);
        if (executeEnabled) {
          const runResponse = page.waitForResponse(
            (response) => response.url().includes("/api/lab/workflow-inspector/run") && response.request().method() === "POST",
            { timeout: 60000 },
          ).catch(() => null);
          if (await requestInput.isVisible().catch(() => false)) {
            await requestInput.fill("Execute the selected workflow and surface the most material risk or blocker.");
          }
          await execute.click();
          const response = await runResponse;
          if (response && response.status() >= 200 && response.status() < 300) {
            addCheck("workflow-execute", "passed", `POST ${response.url()} -> ${response.status()}`);
            interactions.push({ action: "workflow-execute", status: "ok", responseStatus: response.status() });
          } else {
            addCheck("workflow-execute", "failed", "Execute button was enabled but no successful workflow POST was observed.");
            interactions.push({ action: "workflow-execute", status: "failed" });
          }
          await page.waitForTimeout(700);
        } else {
          addCheck("workflow-execute", "degraded", "Workflow execution is unavailable in the current runtime state.");
          interactions.push({ action: "workflow-execute", status: "degraded" });
        }
      }

      if (pageDefinition.slug === "evidenceops") {
        const searchTab = page.getByRole("tab", { name: /search/i }).first();
        if (await searchTab.isVisible().catch(() => false)) {
          await searchTab.click();
          const searchInput = page.getByPlaceholder(/semantic search query|Search the live EvidenceOps repository/i).first();
          if (await searchInput.isVisible().catch(() => false)) {
            await searchInput.fill("vendor access review");
            const searchButton = page.getByRole("button", { name: /^search$/i }).first();
            if (await searchButton.isEnabled().catch(() => false)) {
              await searchButton.click();
              interactions.push({ action: "evidence-search", status: "ok" });
              await page.waitForTimeout(500);
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

      if (tabLabels.length) {
        addCheck("tab-navigation", "passed", `${tabLabels.length} tabs exercised`);
      } else {
        addCheck("tab-navigation", "skipped", "No tabs were exposed on this page.");
      }

      const payloadSummary = summarizeRelevantPayload(pageDefinition.slug, payload);
      if (payloadSummary.available) {
        if (payloadSummary.status === "degraded") {
          addCheck("payload-structure", "degraded", `source=${payloadSummary.metaSource ?? "unknown"} status=${payloadSummary.status}`);
        } else {
          addCheck("payload-structure", "passed", `source=${payloadSummary.metaSource ?? "unknown"} status=${payloadSummary.status ?? "n/a"}`);
        }
      } else {
        addCheck("payload-structure", "failed", "No JSON payload was captured for the expected AI LAB endpoint.");
      }

      if (pageErrors.length === 0) {
        addCheck("page-errors", "passed", "No uncaught page errors.");
      } else {
        addCheck("page-errors", "failed", pageErrors.join(" | "));
      }

      await persistPageArtifacts(pageDefinition, page, payload, apiEvents, failedRequests, consoleEvents, pageErrors, checks, interactions, tabLabels);

      const failedChecks = checks.filter((item) => item.status === "failed");
      expect.soft(pageErrors, `Page errors on ${pageDefinition.slug}`).toEqual([]);
      expect.soft(failedChecks, `Failed semantic checks on ${pageDefinition.slug}: ${JSON.stringify(failedChecks, null, 2)}`).toEqual([]);
    } catch (error) {
      if (!checks.some((item) => item.name === "heading-visible")) {
        addCheck("heading-visible", "failed", error instanceof Error ? error.message : String(error));
      }

      const endpointObserved = apiEvents.some((event) => event.url.includes(pageDefinition.endpoint) && event.status >= 200 && event.status < 300);
      if (!checks.some((item) => item.name === "expected-endpoint-response")) {
        addCheck("expected-endpoint-response", endpointObserved ? "passed" : "failed", endpointObserved ? `${pageDefinition.endpoint} -> observed` : `Did not observe a successful response for ${pageDefinition.endpoint}`);
      }

      if (!checks.some((item) => item.name === "page-errors")) {
        addCheck("page-errors", pageErrors.length ? "failed" : "passed", pageErrors.length ? pageErrors.join(" | ") : "No uncaught page errors.");
      }

      await persistPageArtifacts(pageDefinition, page, payload, apiEvents, failedRequests, consoleEvents, pageErrors, checks, interactions, []);
      throw error;
    }
  });
}
