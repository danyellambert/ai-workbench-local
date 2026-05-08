import { PRODUCT_API_BASE_URL } from '@/lib/product-api';
import type { DataSource } from '@/types/ai-lab';
import { PublicExecutionQuotaError, isPublicExecutionQuotaPayload } from '@/lib/public-demo-limits';

export type LabEvalVerdict = 'PASS' | 'WARN' | 'FAIL';

export interface LabMeta {
  source: DataSource;
  updated_at?: string | null;
  notes?: string[];
}

export interface LabKeyValueRow {
  label: string;
  value: string | number;
  status?: 'healthy' | 'warning' | 'error' | 'neutral';
  detail?: string | null;
}

export interface LabOverviewKpi {
  label: string;
  value: string | number;
  status: 'healthy' | 'warning' | 'error' | 'neutral';
  trend?: string | null;
}

export interface LabOverviewAlert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  detail: string;
  source: string;
  timestamp: string;
}

export interface LabOverviewPageData {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  runtime: Record<string, unknown> & {
    generationProvider?: string;
    generationModel?: string;
    vectorBackendStatus?: string;
    indexedDocumentCount?: number;
    totalChunks?: number;
    contextPressure?: number;
    ingestionHealth?: string;
  };
  kpis: LabOverviewKpi[];
  alerts: LabOverviewAlert[];
  workflow_mix: Array<{ name: string; value: number }>;
  review_rate: number;
  cross_surface_notes?: string[];
}

export interface LabRuntimePayload {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  runtime: Record<string, unknown> & {
    generationProvider?: string;
    generationModel?: string;
    promptProfile?: string;
    contextWindowMode?: string;
    resolvedContext?: number;
    embeddingProvider?: string;
    embeddingModel?: string;
    retrievalStrategy?: string;
    chunkSize?: number;
    chunkOverlap?: number;
    topK?: number;
    rerankPoolSize?: number;
    rerankLexicalWeight?: number;
    vectorBackend?: string;
    vectorBackendStatus?: string;
    indexedDocumentCount?: number;
    totalChunks?: number;
    ingestionHealth?: string;
    contextPressure?: number;
    contextBudgetUsed?: number;
    contextBudgetTotal?: number;
    contextPressurePct?: number;
    contextUtilizationPct?: number;
    latestContextPressurePct?: number;
    avgContextPressurePct?: number;
    maxContextPressurePct?: number;
    latestContextUtilizationPct?: number;
    avgContextUtilizationPct?: number;
    contextHeadroomPct?: number;
    avgSourceCoveragePct?: number;
    medianSourceCoveragePct?: number;
    p90SourceCoveragePct?: number;
    latestSourceCoveragePct?: number;
    minSourceCoveragePct?: number;
    maxSourceCoveragePct?: number;
    sourceCoverageRunCount?: number;
    sourceCoverageHighRunCount?: number;
    sourceCoverageFocusedRunCount?: number;
    sourceCoverageBalancedRunCount?: number;
    sourceCoverageBroadRunCount?: number;
    pdfExtractionMode?: string;
    ocrBackend?: string;
    vlmEnhancement?: boolean;
    executionPolicy?: string;
  };
  generation_rows: LabKeyValueRow[];
  retrieval_rows: LabKeyValueRow[];
  vector_rows: LabKeyValueRow[];
  diagnostics_rows: LabKeyValueRow[];
  ops_summary?: {
    totalRuns?: number;
    successfulRuns?: number;
    errorRate?: number;
    successRate?: number;
    needsReviewRate?: number;
    avgLatencyS?: number;
    p95LatencyS?: number;
    avgTotalTokens?: number;
    throughput24h?: number;
    providerSwitchRate?: number;
    recentWindowLabel?: string;
    lastTraceAt?: string | null;
  };
  retrieval_health?: {
    avgRetrievedChunks?: number;
    emptyRetrievalRate?: number;
    truncatedPromptRate?: number;
    avgContextPressurePct?: number;
    maxContextPressurePct?: number;
    avgContextUtilizationPct?: number;
  };
  cost_summary?: {
    totalTokens?: number;
    avgTotalTokens?: number;
    totalCostUsd?: number;
    avgCostUsd?: number;
    pricedRunRate?: number;
    totalPromptTokens?: number;
    avgPromptTokens?: number;
    totalCompletionTokens?: number;
    avgCompletionTokens?: number;
  };
  surface_window?: {
    scope?: 'product' | 'runtime';
    size?: number;
    maxSize?: number;
    label?: string;
  };
  latency_breakdown?: Array<{ stage: string; seconds: number }>;
  latency_breakdown_meta?: {
    instrumentedRuns?: number;
    totalRuns?: number;
    label?: string;
  };
  provider_breakdown?: Array<{
    key: string;
    provider: string;
    model: string;
    runs: number;
    errorRate: number;
    needsReviewRate: number;
    avgLatencyS: number;
    avgTotalTokens: number;
  }>;
  failure_modes?: Array<{
    id: string;
    label: string;
    count: number;
    severity: 'warning' | 'error';
    detail?: string | null;
  }>;
  recent_traces?: Array<{
    id: string;
    timestamp: string;
    flow: string;
    task: string;
    taskDetail?: string | null;
    provider: string;
    model: string;
    latencyS: number;
    success: boolean;
    needsReview: boolean;
    totalTokens: number;
    tokensEstimated?: boolean;
    sourceCount: number;
    retrievedChunkCount?: number;
    documentCount?: number;
    sourceDocuments?: string[];
    contextPressurePct: number;
    errorMessage?: string | null;
  }>;
  timeline?: Array<{
    label: string;
    latencyS: number;
    contextPressurePct: number;
    error: number;
  }>;
  watchouts?: string[];
  cross_surface_notes?: string[];
}

export interface LabChatMessageSource {
  label: string;
  detail?: string | null;
  score?: number | null;
  scoreKind?: string | null;
  scoreLabel?: string | null;
}

export interface LabChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string | null;
  sources?: LabChatMessageSource[];
}

export interface LabChatSessionSummary {
  session_id: string;
  title: string;
  updated_at?: string | null;
  message_count?: number;
  status?: string | null;
  document_count?: number;
  last_error?: string | null;
  last_model?: string | null;
  avg_latency_s?: number | null;
  grounded_messages?: number;
}

export interface LabDocumentOption {
  document_id: string;
  name: string;
  status?: string;
  chunk_count?: number;
  char_count?: number;
  indexed_at?: string | null;
  loader_strategy_label?: string | null;
  size_bytes?: number | null;
  size_label?: string | null;
  source_type?: string | null;
  page_count?: number | null;
  warnings?: string[];
}

export interface LabTimelineEntry {
  id: string;
  title?: string;
  subtitle?: string;
  label?: string;
  detail?: string;
  timestamp?: string | null;
  status: string;
}

export interface LabChatPageData {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  capabilities: { can_send: boolean; reason?: string | null };
  active_session_id?: string | null;
  sessions: LabChatSessionSummary[];
  messages: LabChatMessage[];
  suggested_prompts: string[];
  selected_documents: LabDocumentOption[];
  available_documents?: LabDocumentOption[];
  session_diagnostics?: Array<{ label: string; value: string | number }> | Record<string, unknown>;
  retrieval_quality?: Array<{ label: string; value: string | number }> | Record<string, unknown>;
  grounding_overview?: Array<{ label: string; value: string | number }> | Record<string, unknown>;
  session_timeline?: LabTimelineEntry[];
  summary?: {
    sessionCount?: number;
    selectedDocumentIds?: string[];
    activeSessionStatus?: string;
    groundedMessageRate?: number;
    artifactCount?: number;
    warningCount?: number;
    avgSourcesPerAssistant?: number;
    lastLatencyS?: number;
    [key: string]: unknown;
  };
}

export interface CreateLabChatSessionResponse {
  ok: boolean;
  session: { session_id: string; [key: string]: unknown };
  page: LabChatPageData;
}

export interface SendLabChatMessageResponse {
  ok: boolean;
  session_id: string;
  assistant_message?: LabChatMessage;
  artifact_path?: string | null;
  page: LabChatPageData;
}

export interface DeleteLabChatSessionResponse {
  ok: boolean;
  session_id: string;
  deleted?: boolean;
  warning?: string;
  page: LabChatPageData;
}

export interface LabWorkflowInspectorPageData {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  capabilities: { can_execute: boolean; reason?: string | null };
  summary: {
    total_cases: number;
    recent_window_count?: number;
    recent_window_limit?: number;
    needs_review: number;
    avg_confidence: number;
    review_blockers: number;
    failed: number;
    task_count?: number;
    document_count?: number;
    live_runs?: number;
    last_run_at?: string | null;
  };
  task_options: Array<{ id: string; label: string; description: string; recent_count: number }>;
  document_options: Array<{ id: string; name: string; status?: string }>;
  selected_task_id?: string;
  task_details: Record<string, {
    id: string;
    label: string;
    description: string;
    document_names?: string[];
    result_title?: string;
    result_items: Array<{ label: string; value: string; confidence?: number | null }>;
    raw_json?: Record<string, unknown>;
    executions?: Array<{
      id: string;
      mode: string;
      status: string;
      needs_review: boolean;
      review_reason?: string | null;
      latency_s?: number | null;
      confidence?: number | null;
      provider?: string | null;
      model?: string | null;
      source_count?: number;
      surface?: string | null;
      answer_mode?: string | null;
      tool_used?: string | null;
      intent?: string | null;
    }>;
    trace_fields?: Array<{ label: string; value: string | number }>;
    stage_timeline?: Array<{ label: string; status: string; detail?: string | null; duration_ms?: number | null }>;
    guardrails?: Array<{ label: string; severity: string; detail?: string | null }>;
    artifacts?: Array<{ label: string; path?: string | null }>;
    run_summary?: { runs?: number; needsReviewRate?: number; avgLatencyS?: number; lastRunAt?: string | null };
  }>;
  recent_cases: Array<{
    id: string;
    task: string;
    document: string;
    mode: string;
    status: string;
    confidence: number;
    sourceCount: number;
    documentCount?: number;
    needsReview: boolean;
  }>;
  mode_breakdown?: Array<{ label: string; value: number }>;
  review_reasons?: Array<{ label: string; value: number }>;
  task_health?: Array<{ id: string; label: string; runs: number; last_status: string; needs_review_rate: number; avg_latency_s: number; last_run_at?: string | null }>;
  latest_runs?: Array<{
    id: string;
    task_id: string;
    task_label: string;
    status: string;
    timestamp?: string | null;
    provider?: string | null;
    model?: string | null;
    latency_s?: number | null;
    source_count?: number;
    needs_review?: boolean;
    review_reason?: string | null;
    artifact_label?: string | null;
    artifact_path?: string | null;
    document_names?: string[];
  }>;
}

export interface RunLabWorkflowInspectorResponse {
  ok: boolean;
  run?: Record<string, unknown>;
  result?: Record<string, unknown>;
  page: LabWorkflowInspectorPageData;
}

export interface LabBenchmarksPageData {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  summary: {
    modelCount: number;
    scoredModelCount?: number;
    partialModelCount?: number;
    promptProfileCount?: number;
    useCaseCount?: number;
    scoredCandidateCount?: number;
    bestGroundedness?: number | null;
    fastestLatency?: number | null;
    bestModel?: string | null;
    totalRuns?: number;
    lastRecordedAt?: string | null;
    sourceBundleCount?: number;
    phase85CaseCount?: number;
    phase85WinnerCount?: number;
  };
  models: Array<{
    id: string;
    family: string;
    provider: string;
    model: string;
    profileTag?: string | null;
    useCaseFit?: number | null;
    groundedness?: number | null;
    adherence?: number | null;
    latency?: number | null;
    outputChars?: number | null;
    runtimeBucket?: string;
    quantization?: string;
    runs: number;
    caseCount?: number;
    scoreStatus?: 'scored' | 'partial';
    sourceFamilies?: string[];
    metricCoverage?: {
      useCaseFit?: number;
      groundedness?: number;
      adherence?: number;
      latency?: number;
      outputChars?: number;
    };
  }>;
  presets: Array<{
    id: string;
    name: string;
    description: string;
    metrics: string[];
    models: string[];
    runCount?: number;
    metricSummary?: {
      useCaseFit?: number | null;
      groundedness?: number | null;
      adherence?: number | null;
      decisionScore?: number | null;
      groundingRatio?: number | null;
      structuredSuccess?: number | null;
      latency?: number | null;
    };
  }>;
  providerSummary?: Array<{ provider: string; models: number; scoredModels?: number; bestFit?: number | null; avgLatency?: number | null; bestModel?: string | null }>;
  leaderboardHighlights?: Array<{ label: string; model?: string | null; detail?: string | null }>;
  retrievalObservations: Array<{
    strategy: string;
    category?: string | null;
    outputDiscipline?: number | null;
    contextRetention?: number | null;
    composite?: number | null;
    latency?: number | null;
    candidateCount?: number;
    scoredCandidateCount?: number;
    avgContextChars?: number | null;
    description: string;
  }>;
  sourceBreakdown?: Array<{
    id: string;
    label: string;
    bundles: number;
    runs?: number;
    detail?: string | null;
  }>;
}

export interface LabEvalsCase {
  id: string;
  task: string;
  taskType?: string | null;
  workflowId?: string | null;
  suite: string;
  verdict: LabEvalVerdict;
  score: number;
  needsReview: boolean;
  model: string;
  provider?: string;
  latency: number;
  timestamp: string;
  sourceKind?: 'live' | 'historical';
  reason?: string | null;
  errorDetail?: string | null;
  traceId?: string | null;
  runId?: string | null;
}

export interface LabEvalsPageData {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  scope?: {
    observedWorkflowIds?: string[];
    observedWorkflowLabels?: string[];
    observedTaskTypes?: string[];
    capableTaskTypes?: string[];
    uncoveredTaskTypes?: string[];
    historicalWindow?: { start?: string | null; end?: string | null; label?: string | null };
    liveWindow?: { start?: string | null; end?: string | null; label?: string | null };
    workflowCoverage?: {
      observed: number;
      historical: number;
      live: number;
      historicalCoveredWorkflowIds?: string[];
      liveCoveredWorkflowIds?: string[];
    };
  };
  passRate: number;
  livePassRate?: number;
  recentLivePassRate?: number;
  recentLiveTotals?: { pass: number; warn: number; fail: number; review: number; total: number };
  recentLiveWindow?: { label?: string; size?: number; maxSize?: number; source?: string };
  totals: { pass: number; warn: number; fail: number; review: number; total: number };
  liveTotals?: { pass: number; warn: number; fail: number; review: number; total: number };
  suites: Array<{ name: string; total: number; pass: number; warn: number; fail: number; needsReview: number; lastRun: string }>;
  cases: LabEvalsCase[];
  historicalCases?: LabEvalsCase[];
  liveCases?: LabEvalsCase[];
  providerBreakdown?: Array<{ provider: string; total: number; failures: number; warnings?: number; passRate: number }>;
  taskBreakdown?: Array<{ task: string; total: number; passRate: number; avgScore: number; warnings?: number; failures?: number }>;
  liveProviderBreakdown?: Array<{ provider: string; total: number; failures: number; warnings?: number; passRate: number }>;
  liveTaskBreakdown?: Array<{ task: string; total: number; passRate: number; avgScore: number; warnings?: number; failures?: number }>;
  liveWorkflowBreakdown?: Array<{ workflowId: string; label: string; shortLabel?: string; pass: number; warn: number; fail: number; total: number }>;
  watchlist?: Array<{ id: string; task: string; suite: string; verdict: 'WARN' | 'FAIL'; score: number; model: string; latency: number; reason?: string | null; timestamp?: string | null; errorDetail?: string | null; sourceKind?: 'live' | 'historical' }>;
  liveWatchlist?: Array<{ id: string; task: string; suite: string; verdict: 'WARN' | 'FAIL'; score: number; model: string; latency: number; reason?: string | null; timestamp?: string | null; errorDetail?: string | null; sourceKind?: 'live' | 'historical' }>;
  historicalWatchlist?: Array<{ id: string; task: string; suite: string; verdict: 'WARN' | 'FAIL'; score: number; model: string; latency: number; reason?: string | null; timestamp?: string | null; errorDetail?: string | null; sourceKind?: 'live' | 'historical' }>;
  investigateFirst?: LabEvalsCase[];
  diagnosis: any;
}

export interface LabArtifactsPageData {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  artifacts: Array<{
    id: string;
    name: string;
    type: 'deck_bundle' | 'benchmark_bundle' | 'evidence_bundle';
    category: string;
    version: string;
    createdAt: string;
    size: string;
    status: 'ready' | 'warning' | 'pending' | 'error';
    description: string;
    workflowLabel?: string;
    exportKind?: string;
    slideCount?: number;
    previewCount?: number;
    issueCount?: number;
    warningCount?: number;
    assetCount?: number;
  }>;
  summary: {
    totalArtifacts: number;
    readyArtifacts: number;
    warningArtifacts?: number;
    errorArtifacts: number;
    chatSessions?: number;
    workflowRuns?: number;
    linkedWorkflowRuns?: number;
    unlinkedWorkflowRuns?: number;
    previewAssets?: number;
    issueCount?: number;
    workflowCount?: number;
    benchmarkArtifacts?: number;
    inspectorRuns?: number;
  };
  diagnostics: Array<{ label: string; detail: string; status: string; health: 'healthy' | 'warning' | 'neutral' }>;
  runRegistry?: {
    chatSessions?: number;
    workflowRuns?: number;
    inspectorRuns?: number;
    latestChatSession?: string | null;
    latestWorkflowRun?: string | null;
    latestWorkflowArtifact?: {
      label?: string | null;
      runId?: string | null;
      updatedAt?: string | null;
    } | null;
  };
  recentCaptures?: Array<{
    id: string;
    label: string;
    workflowLabel?: string | null;
    exportKind?: string | null;
    status?: string | null;
    createdAt?: string | null;
    slideCount?: number | null;
    previewCount?: number | null;
    issueCount?: number | null;
    warningCount?: number | null;
    assetCount?: number | null;
  }>;
}

export interface LabEvidenceOpsPageData {
  meta: LabMeta;
  status?: string;
  degraded_reason?: string | null;
  summary: {
    toolsTotal: number;
    activeTools: number;
    externalToolsTotal?: number;
    activeExternalTools?: number;
    openActions: number;
    latestOpenActions?: number;
    latestActionWindow?: number;
    operationsCount: number;
    repositoryDocumentCount: number;
    repositoryRoot?: string | null;
    lastSyncAt?: string | null;
    overdueActions?: number;
    unassignedActions?: number;
    inProgressActions?: number;
    needsReviewActions?: number;
  };
  repositoryStats?: { changedDocuments: number; newDocuments: number; categories?: number; totalSizeLabel?: string };
  searchHints?: string[];
  tools: Array<{ name: string; description: string; status: string; lastCall?: string | null }>;
  externalTools?: Array<{ name: string; description: string; status: string; lastCall?: string | null; missing?: string[]; connected?: boolean; surface?: string | null }>;
  actions: Array<{ id: string; title: string; status: string; owner: string; target: string; priority: string; dueDate: string; [key: string]: unknown }>;
  operations: Array<{ id: string; operation: string; tool: string; status: string; timestamp: string; durationMs: number; detail: string }>;
  timeline?: LabTimelineEntry[];
  telemetry?: Array<{ event: string; tool: string; status: string; latency: string; ts?: string | null }>;
  readiness?: Array<{ target: string; status: string; detail: string }>;
  ownershipSummary?: Array<{ owner: string; count: number }>;
  operationBreakdown?: Array<{ label: string; value: number }>;
  categoryBreakdown?: Array<{ label: string; value: number }>;
  statusBreakdown?: Array<{ label: string; value: number }>;
  recentSearches?: Array<{ query: string; timestamp?: string | null; hits: number }>;
}

export interface LabEvidenceOpsSearchResult {
  title: string;
  relativePath: string;
  category?: string | null;
  suffix?: string | null;
  sizeKb?: number | null;
  modifiedAt?: string | null;
  matchScore: number;
}

export interface LabEvidenceOpsSearchResponse {
  meta: LabMeta;
  query: string;
  repositoryRoot: string;
  results: LabEvidenceOpsSearchResult[];
}

async function parseError(response: Response, fallback: string) {
  try {
    const payload = await response.json() as { error?: string };
    return payload?.error || fallback;
  } catch {
    return fallback;
  }
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(await parseError(response, `Product API request failed: ${response.status}`));
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, payload: object): Promise<T> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseError(response, `Product API post failed: ${response.status}`));
  }
  return response.json() as Promise<T>;
}

export const aiLabQueryKeys = {
  overview: ['ai-lab', 'overview'] as const,
  runtime: ['ai-lab', 'runtime'] as const,
  chat: (sessionId?: string | null) => ['ai-lab', 'chat', sessionId ?? 'latest'] as const,
  workflowInspector: () => ['ai-lab', 'workflow-inspector'] as const,
  benchmarks: ['ai-lab', 'benchmarks'] as const,
  evals: ['ai-lab', 'evals'] as const,
  artifacts: ['ai-lab', 'artifacts'] as const,
  evidenceOps: ['ai-lab', 'evidenceops'] as const,
  evidenceSearch: (query: string) => ['ai-lab', 'evidenceops-search', query] as const,
};

export function getLabOverviewPage() {
  return fetchJson<LabOverviewPageData>('/api/lab/overview');
}

export function getLabRuntimePage() {
  return fetchJson<LabRuntimePayload>('/api/lab/runtime');
}

export function getLabChatPage(sessionId?: string | null) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  return fetchJson<LabChatPageData>(`/api/lab/chat${query}`);
}

export function createLabChatSession(payload: { document_ids?: string[]; title?: string | null }) {
  return postJson<CreateLabChatSessionResponse>('/api/lab/chat/sessions', payload);
}

export function sendLabChatMessage(sessionId: string, payload: { content: string; document_ids?: string[] }) {
  return postJson<SendLabChatMessageResponse>(`/api/lab/chat/sessions/${encodeURIComponent(sessionId)}/messages`, payload);
}

export function deleteLabChatSession(sessionId: string) {
  return postJson<DeleteLabChatSessionResponse>(`/api/lab/chat/sessions/${encodeURIComponent(sessionId)}/delete`, {});
}

export function getLabWorkflowInspectorPage() {
  return fetchJson<LabWorkflowInspectorPageData>('/api/lab/workflow-inspector');
}

export function runLabWorkflowInspector(payload: { task_id: string; document_id?: string | null; document_ids?: string[]; input_text?: string | null; provider?: string | null; model?: string | null }) {
  return postJson<RunLabWorkflowInspectorResponse>('/api/lab/workflow-inspector/run', payload);
}

export function getLabBenchmarksPage() {
  return fetchJson<LabBenchmarksPageData>('/api/lab/benchmarks');
}

export function getLabEvalsPage() {
  return fetchJson<LabEvalsPageData>('/api/lab/evals');
}

export function getLabArtifactsPage() {
  return fetchJson<LabArtifactsPageData>('/api/lab/artifacts');
}

export function getLabEvidenceOpsPage() {
  return fetchJson<LabEvidenceOpsPageData>('/api/lab/evidenceops');
}

export function searchLabEvidenceOps(query: string) {
  return fetchJson<LabEvidenceOpsSearchResponse>(`/api/lab/evidenceops/search?q=${encodeURIComponent(query)}`);
}

export function syncLabEvidenceOps() {
  return postJson<{ ok: boolean; diff?: Record<string, unknown>; page: LabEvidenceOpsPageData }>('/api/lab/evidenceops/sync', {});
}

export function updateLabEvidenceOpsAction(actionId: string | number, payload: { status?: string | null; owner?: string | null }) {
  return postJson<{ ok: boolean; action?: Record<string, unknown>; page: LabEvidenceOpsPageData }>(`/api/lab/evidenceops/actions/${encodeURIComponent(String(actionId))}`, payload);
}
