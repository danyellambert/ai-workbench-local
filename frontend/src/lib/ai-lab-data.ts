import { PRODUCT_API_BASE_URL } from '@/lib/product-api';
import type { DataSource } from '@/types/ai-lab';

export interface LabApiMeta {
  source: DataSource;
  updated_at?: string | null;
  notes: string[];
}

export interface LabRuntimeSnapshot {
  generationProvider: string;
  generationModel: string;
  promptProfile: string;
  contextWindowMode: string;
  resolvedContext: number;
  embeddingProvider: string;
  embeddingModel: string;
  retrievalStrategy: string;
  chunkSize: number;
  chunkOverlap: number;
  topK: number;
  rerankPoolSize: number;
  rerankLexicalWeight: number;
  vectorBackend: string;
  vectorBackendStatus: 'healthy' | 'degraded' | 'offline';
  indexedDocumentCount: number;
  ingestionHealth: 'healthy' | 'warning' | 'error';
  contextPressure: number;
  contextBudgetUsed: number;
  contextBudgetTotal: number;
}

export interface LabMetricEntry {
  label: string;
  value: string | number;
  status: string;
  trend?: string;
}

export interface LabAlertEntry {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  detail: string;
  source: string;
  timestamp?: string | null;
}

export interface LabPieEntry {
  name: string;
  value: number;
}

export interface LabKeyValueRow {
  label: string;
  value: string;
}

export interface LabOverviewResponse {
  ok: boolean;
  meta: LabApiMeta;
  runtime: LabRuntimeSnapshot;
  kpis: LabMetricEntry[];
  alerts: LabAlertEntry[];
  workflow_mix_label: string;
  workflow_mix: LabPieEntry[];
  review_rate: number;
}

export interface LabRuntimeResponse {
  ok: boolean;
  meta: LabApiMeta;
  runtime: LabRuntimeSnapshot;
  generation_rows: LabKeyValueRow[];
  retrieval_rows: LabKeyValueRow[];
  vector_rows: LabKeyValueRow[];
  diagnostics_rows: LabKeyValueRow[];
}

export interface LabChatMessageSource {
  label: string;
  detail?: string | null;
  score?: number | null;
}

export interface LabChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string | null;
  sources?: LabChatMessageSource[];
}

export interface LabDocumentOption {
  document_id: string;
  name: string;
  status: string;
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

export interface LabCapabilityState {
  can_send?: boolean;
  can_execute?: boolean;
  reason?: string | null;
}

export interface LabChatSessionSummary {
  session_id: string;
  title: string;
  updated_at?: string | null;
  message_count: number;
  status?: string | null;
  document_count?: number;
  last_error?: string | null;
  last_model?: string | null;
  avg_latency_s?: number | null;
  grounded_messages?: number;
}

export interface LabTimelineEntry {
  id: string;
  kind?: string | null;
  label: string;
  timestamp?: string | null;
  status?: string | null;
  detail?: string | null;
}

export interface LabChatSummary {
  total_sessions?: number;
  assistant_messages?: number;
  grounded_messages?: number;
  grounding_sources?: number;
  active_documents?: number;
  avg_latency_s?: number | null;
  last_model?: string | null;
  failed_sessions?: number;
}

export interface LabChatResponse {
  ok: boolean;
  status?: string | null;
  degraded_reason?: string | null;
  last_updated_at?: string | null;
  meta: LabApiMeta;
  capabilities: LabCapabilityState;
  active_session_id?: string | null;
  sessions?: LabChatSessionSummary[];
  summary?: LabChatSummary;
  grounding_overview?: LabKeyValueRow[];
  session_timeline?: LabTimelineEntry[];
  messages: LabChatMessage[];
  suggested_prompts: string[];
  selected_documents: LabDocumentOption[];
  session_diagnostics: LabKeyValueRow[];
  retrieval_quality: LabKeyValueRow[];
}

export interface LabCreateChatSessionPayload {
  title?: string;
  document_ids?: string[];
}

export interface LabCreateChatSessionResponse {
  ok: boolean;
  session: LabChatSessionSummary & Record<string, unknown>;
  page: LabChatResponse;
}

export interface LabSendChatMessagePayload {
  content: string;
  document_ids?: string[];
}

export interface LabSendChatMessageResponse {
  ok: boolean;
  session_id: string;
  assistant_message?: LabChatMessage;
  artifact_path?: string | null;
  page: LabChatResponse;
}

export interface LabWorkflowTaskOption {
  id: string;
  label: string;
  description: string;
  recent_count: number;
}

export interface LabWorkflowResultItem {
  label: string;
  value: string;
  confidence?: number | null;
}

export interface LabWorkflowExecution {
  id: string;
  mode: string;
  status: string;
  confidence: number;
  source_count: number;
  latency_s?: number | null;
  provider?: string | null;
  model?: string | null;
  needs_review: boolean;
  review_reason?: string | null;
  timestamp?: string | null;
}

export interface LabWorkflowTaskDetail {
  id: string;
  label: string;
  description: string;
  document_names: string[];
  result_title: string;
  result_items: LabWorkflowResultItem[];
  trace_fields: LabKeyValueRow[];
  raw_json: Record<string, unknown>;
  executions: LabWorkflowExecution[];
  artifact_path?: string | null;
  latest_request?: Record<string, unknown>;
  latest_status?: string | null;
  latest_timestamp?: string | null;
  latest_summary?: string | null;
}

export interface LabWorkflowCase {
  id: string;
  task: string;
  document: string;
  mode: string;
  status: string;
  needsReview: boolean;
  confidence: number;
  sourceCount: number;
  timestamp?: string | null;
  reviewReason?: string | null;
  artifactPath?: string | null;
  summary?: string | null;
}

export interface LabWorkflowInspectorResponse {
  ok: boolean;
  status?: string | null;
  degraded_reason?: string | null;
  last_updated_at?: string | null;
  meta: LabApiMeta;
  capabilities: LabCapabilityState;
  summary: {
    total_cases: number;
    needs_review: number;
    avg_confidence: number;
    review_blockers: number;
    failed: number;
    task_count?: number;
    document_count?: number;
    live_runs?: number;
    last_run_at?: string | null;
  };
  mode_breakdown?: LabKeyValueRow[];
  review_reasons?: LabKeyValueRow[];
  task_options: LabWorkflowTaskOption[];
  document_options: Array<{ id: string; name: string; status: string }>;
  selected_task_id?: string | null;
  task_details: Record<string, LabWorkflowTaskDetail>;
  recent_cases: LabWorkflowCase[];
}

export interface LabRunWorkflowInspectorPayload {
  task_id: string;
  document_id?: string | null;
  input_text?: string | null;
  provider?: string | null;
  model?: string | null;
}

export interface LabRunWorkflowInspectorResponse {
  ok: boolean;
  run: Record<string, unknown>;
  result: Record<string, unknown>;
  page: LabWorkflowInspectorResponse;
  result_view?: Record<string, unknown>;
  comparison_view?: Record<string, unknown>;
  action_plan_view?: Record<string, unknown>;
}

export interface LabBenchmarkModel {
  id: string;
  provider: string;
  model: string;
  family: string;
  quantization: string;
  latency: number;
  outputChars: number;
  adherence: number;
  groundedness: number;
  useCaseFit: number;
  runtimeBucket: string;
  runs: number;
  successRate: number;
  source: string;
  profileTag?: string | null;
}

export interface LabBenchmarkPreset {
  id: string;
  name: string;
  description: string;
  metrics: string[];
  models: string[];
}

export interface LabRetrievalObservation {
  strategy: string;
  outputDiscipline: number;
  contextRetention: number;
  composite: number;
  latency: number;
  description: string;
  coverage: number;
}

export interface LabBenchmarksResponse {
  ok: boolean;
  status?: string | null;
  degraded_reason?: string | null;
  last_updated_at?: string | null;
  meta: LabApiMeta;
  summary: {
    modelCount: number;
    recommendedModel?: string | null;
    bestGroundedness: number;
    fastestLatency: number;
  };
  providerSummary?: Array<{ provider: string; models: number; avgLatency: number; bestFit: number; bestModel?: string | null }>;
  leaderboardHighlights?: Array<{ label: string; model?: string | null; detail?: string | null }>;
  models: LabBenchmarkModel[];
  presets: LabBenchmarkPreset[];
  retrievalObservations: LabRetrievalObservation[];
}

export interface LabEvalSuite {
  name: string;
  total: number;
  pass: number;
  warn: number;
  fail: number;
  needsReview: number;
  lastRun?: string | null;
}

export type LabEvalVerdict = 'PASS' | 'WARN' | 'FAIL';

export interface LabEvalCase {
  id: string;
  task: string;
  suite: string;
  verdict: LabEvalVerdict;
  score: number;
  needsReview: boolean;
  model: string;
  latency: number;
  timestamp?: string | null;
  errorDetail?: string | null;
}

export interface LabEvalDiagnosisFailureReason {
  reason: string;
  count: number;
}

export interface LabEvalDiagnosisCandidate {
  task_type: string;
  fail_rate: number;
  recent_fail_rate: number;
  avg_score_ratio: number;
  health_label: string;
  adaptation_priority: string;
  recommended_action: string;
  top_reasons: LabEvalDiagnosisFailureReason[];
}

export interface LabEvalDiagnosisPriority {
  task_type: string;
  fail_rate: number;
  recent_fail_rate: number;
  recommended_action: string;
}

export interface LabEvalsResponse {
  ok: boolean;
  status?: string | null;
  degraded_reason?: string | null;
  last_updated_at?: string | null;
  meta: LabApiMeta;
  passRate: number;
  totals: {
    total: number;
    pass: number;
    warn: number;
    fail: number;
    review: number;
  };
  suites: LabEvalSuite[];
  cases: LabEvalCase[];
  providerBreakdown?: Array<{ provider: string; total: number; passRate: number; failures: number }>;
  taskBreakdown?: Array<{ task: string; total: number; passRate: number; avgScore: number }>;
  watchlist?: Array<{ id: string; task: string; suite: string; reason: string; timestamp?: string | null; verdict: LabEvalVerdict }>;
  diagnosis: {
    topFailureReasons: LabEvalDiagnosisFailureReason[];
    adaptationCandidates: LabEvalDiagnosisCandidate[];
    nextEvalPriorities: LabEvalDiagnosisPriority[];
    globalRecommendation?: string | null;
  };
}

export interface LabArtifact {
  id: string;
  name: string;
  type: 'report' | 'benchmark' | 'eval' | 'extraction' | 'ocr_diagnostic' | 'embedding_experiment';
  category: string;
  version: string;
  createdAt: string;
  size: string;
  status: 'ready' | 'generating' | 'error';
  description: string;
  artifactPath?: string | null;
}

export interface LabDiagnosticEntry {
  label: string;
  detail: string;
  status: string;
  health: 'healthy' | 'warning' | 'neutral';
}

export interface LabArtifactsResponse {
  ok: boolean;
  status?: string | null;
  degraded_reason?: string | null;
  last_updated_at?: string | null;
  meta: LabApiMeta;
  artifacts: LabArtifact[];
  summary: {
    totalArtifacts: number;
    readyArtifacts: number;
    errorArtifacts: number;
    chatSessions?: number;
    workflowRuns?: number;
  };
  runRegistry?: {
    chatSessions: number;
    workflowRuns: number;
    latestChatSession?: string | null;
    latestWorkflowRun?: string | null;
    latestWorkflowArtifact?: string | null;
  };
  recentCaptures?: Array<{ id: string; label: string; category?: string | null; status?: string | null; createdAt?: string | null; artifactPath?: string | null }>;
  diagnostics: LabDiagnosticEntry[];
}

export interface LabEvidenceTool {
  name: string;
  description: string;
  status: string;
  lastCall?: string | null;
}

export interface LabEvidenceAction {
  id: string;
  title: string;
  status: 'open' | 'in_progress' | 'blocked' | 'done';
  owner: string;
  dueDate: string;
  target: string;
  priority: 'high' | 'medium' | 'low';
  rawStatus?: string;
  evidence?: string | null;
  sourceCount?: number;
}

export interface LabEvidenceOperation {
  id: string;
  operation: string;
  tool: string;
  status: 'success' | 'warning' | 'error';
  timestamp?: string | null;
  durationMs: number;
  detail: string;
}

export interface LabEvidenceTelemetry {
  event: string;
  tool: string;
  status: 'ok' | 'warning' | 'skipped';
  latency: string;
  ts?: string | null;
}

export interface LabEvidenceReadiness {
  target: string;
  status: 'ready' | 'degraded';
  detail: string;
}

export interface LabEvidenceOpsResponse {
  ok: boolean;
  status?: string | null;
  degraded_reason?: string | null;
  last_updated_at?: string | null;
  meta: LabApiMeta;
  summary: {
    toolsTotal: number;
    activeTools: number;
    openActions: number;
    operationsCount: number;
    lastSyncAt?: string | null;
    repositoryRoot: string;
    repositoryDocumentCount: number;
    repositoryCategories?: string[];
  };
  tools: LabEvidenceTool[];
  actions: LabEvidenceAction[];
  operations: LabEvidenceOperation[];
  telemetry: LabEvidenceTelemetry[];
  readiness: LabEvidenceReadiness[];
  ownershipSummary?: Array<{ owner: string; count: number }>;
  operationBreakdown?: LabKeyValueRow[];
  timeline?: Array<{ id: string; title: string; subtitle?: string | null; timestamp?: string | null; status?: string | null }>;
  searchHints?: string[];
  repositoryStats?: { totalDocuments: number; newDocuments: number; changedDocuments: number; removedDocuments: number };
}

export interface LabEvidenceSearchResult {
  documentId?: string | null;
  title: string;
  category?: string | null;
  relativePath: string;
  suffix?: string | null;
  sizeKb?: number | null;
  matchScore: number;
  modifiedAt?: string | null;
}

export interface LabEvidenceSearchResponse {
  ok: boolean;
  meta: LabApiMeta;
  query: string;
  repositoryRoot: string;
  results: LabEvidenceSearchResult[];
}

async function requestLabApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${PRODUCT_API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    let detail = '';
    try {
      const payload = await response.json();
      detail = typeof payload?.error === 'string' ? payload.error : JSON.stringify(payload);
    } catch {
      detail = response.statusText;
    }
    throw new Error(detail ? `AI Lab API request failed: ${response.status} ${detail}` : `AI Lab API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function fetchLabApi<T>(path: string): Promise<T> {
  return requestLabApi<T>(path);
}

async function postLabApi<T>(path: string, payload: unknown): Promise<T> {
  return requestLabApi<T>(path, {
    method: 'POST',
    body: JSON.stringify(payload ?? {}),
  });
}

export const aiLabQueryKeys = {
  overview: ['ai-lab', 'overview'] as const,
  runtime: ['ai-lab', 'runtime'] as const,
  chat: (sessionId?: string | null) => ['ai-lab', 'chat', sessionId ?? 'latest'] as const,
  workflowInspector: (taskId?: string | null) => ['ai-lab', 'workflow-inspector', taskId ?? 'default'] as const,
  benchmarks: ['ai-lab', 'benchmarks'] as const,
  evals: ['ai-lab', 'evals'] as const,
  artifacts: ['ai-lab', 'artifacts'] as const,
  evidenceOps: ['ai-lab', 'evidenceops'] as const,
  evidenceSearch: (query: string) => ['ai-lab', 'evidenceops', 'search', query] as const,
};

export function getLabOverviewPage(): Promise<LabOverviewResponse> {
  return fetchLabApi<LabOverviewResponse>('/api/lab/overview');
}

export function getLabRuntimePage(): Promise<LabRuntimeResponse> {
  return fetchLabApi<LabRuntimeResponse>('/api/lab/runtime');
}

export function getLabChatPage(sessionId?: string | null): Promise<LabChatResponse> {
  const suffix = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
  return fetchLabApi<LabChatResponse>(`/api/lab/chat${suffix}`);
}

export function createLabChatSession(payload: LabCreateChatSessionPayload): Promise<LabCreateChatSessionResponse> {
  return postLabApi<LabCreateChatSessionResponse>('/api/lab/chat/sessions', payload);
}

export function sendLabChatMessage(sessionId: string, payload: LabSendChatMessagePayload): Promise<LabSendChatMessageResponse> {
  return postLabApi<LabSendChatMessageResponse>(`/api/lab/chat/sessions/${encodeURIComponent(sessionId)}/messages`, payload);
}

export function getLabWorkflowInspectorPage(taskId?: string | null): Promise<LabWorkflowInspectorResponse> {
  const suffix = taskId ? `?task_id=${encodeURIComponent(taskId)}` : '';
  return fetchLabApi<LabWorkflowInspectorResponse>(`/api/lab/workflow-inspector${suffix}`);
}

export function runLabWorkflowInspector(payload: LabRunWorkflowInspectorPayload): Promise<LabRunWorkflowInspectorResponse> {
  return postLabApi<LabRunWorkflowInspectorResponse>('/api/lab/workflow-inspector/run', payload);
}

export function getLabBenchmarksPage(): Promise<LabBenchmarksResponse> {
  return fetchLabApi<LabBenchmarksResponse>('/api/lab/benchmarks');
}

export function getLabEvalsPage(): Promise<LabEvalsResponse> {
  return fetchLabApi<LabEvalsResponse>('/api/lab/evals');
}

export function getLabArtifactsPage(): Promise<LabArtifactsResponse> {
  return fetchLabApi<LabArtifactsResponse>('/api/lab/artifacts');
}

export function getLabEvidenceOpsPage(): Promise<LabEvidenceOpsResponse> {
  return fetchLabApi<LabEvidenceOpsResponse>('/api/lab/evidenceops');
}

export function searchLabEvidenceOps(query: string): Promise<LabEvidenceSearchResponse> {
  return fetchLabApi<LabEvidenceSearchResponse>(`/api/lab/evidenceops/search?q=${encodeURIComponent(query)}`);
}
