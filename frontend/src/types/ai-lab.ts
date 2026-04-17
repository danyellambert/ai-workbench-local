export type DataSource = 'live' | 'derived' | 'snapshot' | 'mock';

export interface DataSourceMeta {
  source: DataSource;
  label: string;
  updatedAt?: string;
}

export const DATA_SOURCE_LABELS: Record<DataSource, string> = {
  live: 'Live product API',
  derived: 'Derived live',
  snapshot: 'Snapshot',
  mock: 'Mock',
};

export interface RuntimeConfig {
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

export type EvalVerdict = 'PASS' | 'WARN' | 'FAIL';

export interface EvalCase {
  id: string;
  task: string;
  suite: string;
  verdict: EvalVerdict;
  score: number;
  needsReview: boolean;
  model: string;
  latency: number;
  timestamp: string;
  errorDetail?: string;
}

export interface EvalSuite {
  name: string;
  total: number;
  pass: number;
  warn: number;
  fail: number;
  needsReview: number;
  lastRun: string;
}

export interface BenchmarkPreset {
  id: string;
  name: string;
  description: string;
  metrics: string[];
  models: string[];
}

export interface StrategyBenchmark {
  strategy: string;
  precision: number;
  recall: number;
  f1: number;
  latency: number;
  description: string;
}

export interface WorkflowAttempt {
  id: string;
  route: 'direct' | 'langgraph' | 'fallback';
  status: 'completed' | 'failed' | 'timeout';
  confidence: number;
  qualityScore: number;
  needsReview: boolean;
  guardrailTriggered: boolean;
  guardrailReason?: string;
  durationMs: number;
  tokenCount: number;
  timestamp: string;
}

export interface WorkflowCase {
  id: string;
  task: string;
  document: string;
  route: string;
  status: string;
  needsReview: boolean;
  confidence: number;
  qualityScore: number;
  timestamp: string;
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
}

export interface OpenAction {
  id: string;
  title: string;
  status: 'open' | 'in_progress' | 'blocked' | 'done';
  owner: string;
  dueDate: string;
  target: string;
  priority: 'high' | 'medium' | 'low';
}

export interface AutoOperation {
  id: string;
  operation: string;
  tool: string;
  status: 'success' | 'warning' | 'error';
  timestamp: string;
  durationMs: number;
  detail: string;
}

export interface LabAlert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  detail: string;
  source: string;
  timestamp: string;
}

export interface LabKPI {
  label: string;
  value: string | number;
  trend?: string;
  status: 'healthy' | 'warning' | 'error' | 'neutral';
}