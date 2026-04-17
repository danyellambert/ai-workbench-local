import type {
  RuntimeConfig, EvalCase, EvalSuite, WorkflowCase, WorkflowAttempt,
  LabArtifact, LabAlert, LabKPI, BenchmarkPreset, StrategyBenchmark,
  OpenAction, AutoOperation, DataSource, DataSourceMeta,
} from '@/types/ai-lab';
import { models, documents, workflowRuns, mcpTools } from '@/lib/mock-data';

// ─── Source helpers ────────────────────────────────────────
export function makeSource(source: DataSource, updatedAt?: string): DataSourceMeta {
  const labels: Record<DataSource, string> = {
    live: 'Live product API', derived: 'Derived live', snapshot: 'Snapshot', mock: 'Mock',
  };
  return { source, label: labels[source], updatedAt };
}

// ─── Runtime Snapshot ──────────────────────────────────────
export function getRuntimeSnapshot(): { data: RuntimeConfig; meta: DataSourceMeta } {
  const indexedCount = documents.filter(d => d.status === 'indexed').length;
  return {
    data: {
      generationProvider: 'ollama',
      generationModel: 'qwen2.5:32b-instruct-q5_K_M',
      promptProfile: 'structured_extraction_v2',
      contextWindowMode: 'auto',
      resolvedContext: 32768,
      embeddingProvider: 'ollama',
      embeddingModel: 'nomic-embed-text',
      retrievalStrategy: 'hybrid_rerank',
      chunkSize: 1200,
      chunkOverlap: 200,
      topK: 15,
      rerankPoolSize: 50,
      rerankLexicalWeight: 0.3,
      vectorBackend: 'ChromaDB',
      vectorBackendStatus: 'healthy',
      indexedDocumentCount: indexedCount,
      ingestionHealth: documents.some(d => d.status === 'error') ? 'warning' : 'healthy',
      contextPressure: 0.62,
      contextBudgetUsed: 20316,
      contextBudgetTotal: 32768,
    },
    meta: makeSource('derived', new Date().toISOString()),
  };
}

// ─── Lab Overview KPIs ─────────────────────────────────────
export function getLabKPIs(): { data: LabKPI[]; meta: DataSourceMeta } {
  const indexedDocs = documents.filter(d => d.status === 'indexed').length;
  const totalChunks = documents.reduce((s, d) => s + d.chunks, 0);
  const completedRuns = workflowRuns.filter(r => r.status === 'completed').length;
  const activeTools = mcpTools.filter(t => t.status === 'active').length;
  return {
    data: [
      { label: 'Indexed Documents', value: indexedDocs, status: 'healthy' },
      { label: 'Total Chunks', value: totalChunks.toLocaleString(), status: 'healthy' },
      { label: 'Completed Runs', value: completedRuns, status: 'healthy' },
      { label: 'Active MCP Tools', value: activeTools, status: activeTools < mcpTools.length ? 'warning' : 'healthy' },
      { label: 'Eval Pass Rate', value: '82%', status: 'warning' },
      { label: 'Avg Latency', value: '6.2s', trend: '−0.4s', status: 'healthy' },
    ],
    meta: makeSource('derived'),
  };
}

// ─── Lab Alerts ────────────────────────────────────────────
export function getLabAlerts(): { data: LabAlert[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'a1', severity: 'warning', title: 'OCR fallback failure on Technical Architecture Brief', detail: 'Pages 12-15 failed OCR extraction. Document remains unindexed.', source: 'Ingestion', timestamp: '2024-03-14T15:00:00Z' },
      { id: 'a2', severity: 'info', title: 'GDPR Compliance Checklist still indexing', detail: 'Document has been indexing for 12 minutes.', source: 'Indexer', timestamp: '2024-03-15T10:30:00Z' },
      { id: 'a3', severity: 'warning', title: 'Eval regression: extraction_entities dropped to 62%', detail: 'extraction_entities task on Master Service Agreement v4.2 dropped from 94% to 62%. Missed 3 of 8 expected entities in Section 7.', source: 'Evals', timestamp: '2024-03-15T09:00:00Z' },
      { id: 'a4', severity: 'critical', title: 'MCP repository drift detected', detail: 'Technical Architecture Brief removed from source but still referenced in index. Drift since last sync.', source: 'EvidenceOps', timestamp: '2024-03-14T12:00:00Z' },
    ],
    meta: makeSource('mock'),
  };
}

// ─── Eval Data ─────────────────────────────────────────────
export function getEvalSuites(): { data: EvalSuite[]; meta: DataSourceMeta } {
  return {
    data: [
      { name: 'extraction', total: 24, pass: 20, warn: 2, fail: 2, needsReview: 3, lastRun: '2024-03-15T09:00:00Z' },
      { name: 'summarization', total: 18, pass: 16, warn: 1, fail: 1, needsReview: 1, lastRun: '2024-03-15T09:00:00Z' },
      { name: 'comparison', total: 12, pass: 10, warn: 1, fail: 1, needsReview: 2, lastRun: '2024-03-14T16:00:00Z' },
      { name: 'action_plan', total: 8, pass: 7, warn: 1, fail: 0, needsReview: 0, lastRun: '2024-03-14T16:00:00Z' },
      { name: 'candidate_review', total: 6, pass: 5, warn: 0, fail: 1, needsReview: 1, lastRun: '2024-03-15T08:00:00Z' },
    ],
    meta: makeSource('mock'),
  };
}

export function getEvalCases(): { data: EvalCase[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'e1', task: 'extraction_entities', suite: 'extraction', verdict: 'FAIL', score: 0.62, needsReview: true, model: 'qwen2.5:32b', latency: 8.4, timestamp: '2024-03-15T09:01:00Z', errorDetail: 'Missed 3 of 8 expected entities in Master Service Agreement v4.2 Section 7 (liability cap, indemnification scope, limitation period)' },
      { id: 'e2', task: 'extraction_dates', suite: 'extraction', verdict: 'PASS', score: 0.97, needsReview: false, model: 'qwen2.5:32b', latency: 5.2, timestamp: '2024-03-15T09:02:00Z' },
      { id: 'e3', task: 'summarization_risk', suite: 'summarization', verdict: 'WARN', score: 0.78, needsReview: true, model: 'qwen2.5:32b', latency: 12.1, timestamp: '2024-03-15T09:03:00Z', errorDetail: 'Summary of Information Security Policy v3.1 omitted secondary risk factors (incident response SLOs)' },
      { id: 'e4', task: 'comparison_clauses', suite: 'comparison', verdict: 'PASS', score: 0.91, needsReview: false, model: 'qwen2.5:32b', latency: 14.7, timestamp: '2024-03-14T16:05:00Z' },
      { id: 'e5', task: 'extraction_amounts', suite: 'extraction', verdict: 'PASS', score: 0.95, needsReview: false, model: 'qwen2.5:32b', latency: 4.8, timestamp: '2024-03-15T09:04:00Z' },
      { id: 'e6', task: 'candidate_scoring', suite: 'candidate_review', verdict: 'FAIL', score: 0.54, needsReview: true, model: 'llama3.1:70b', latency: 18.2, timestamp: '2024-03-15T08:10:00Z', errorDetail: 'Scoring rubric not followed for Sarah Chen - Senior ML Engineer CV soft skills assessment' },
      { id: 'e7', task: 'summarization_compliance', suite: 'summarization', verdict: 'PASS', score: 0.93, needsReview: false, model: 'qwen2.5:32b', latency: 9.8, timestamp: '2024-03-15T09:05:00Z' },
      { id: 'e8', task: 'action_plan_generation', suite: 'action_plan', verdict: 'WARN', score: 0.81, needsReview: false, model: 'qwen2.5:32b', latency: 11.3, timestamp: '2024-03-14T16:10:00Z', errorDetail: 'Priority ordering for Vendor Risk Assessment Template actions inconsistent with severity ranking' },
    ],
    meta: makeSource('mock'),
  };
}

// ─── Workflow Inspector ────────────────────────────────────
export function getWorkflowCases(): { data: WorkflowCase[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'wc1', task: 'document_review', document: 'Master Service Agreement v4.2', route: 'direct', status: 'completed', needsReview: false, confidence: 0.94, qualityScore: 0.91, timestamp: '2024-03-15T10:30:00Z' },
      { id: 'wc2', task: 'extraction', document: 'Data Processing Addendum 2024', route: 'langgraph', status: 'completed', needsReview: true, confidence: 0.72, qualityScore: 0.78, timestamp: '2024-03-15T09:15:00Z' },
      { id: 'wc3', task: 'comparison', document: 'Information Security Policy v3.1', route: 'direct', status: 'completed', needsReview: false, confidence: 0.88, qualityScore: 0.86, timestamp: '2024-03-14T16:20:00Z' },
      { id: 'wc4', task: 'candidate_review', document: 'Sarah Chen - Senior ML Engineer CV', route: 'langgraph', status: 'completed', needsReview: true, confidence: 0.65, qualityScore: 0.71, timestamp: '2024-03-15T08:45:00Z' },
      { id: 'wc5', task: 'contract_risk_extraction', document: 'Vendor Risk Assessment Template', route: 'fallback', status: 'completed', needsReview: true, confidence: 0.58, qualityScore: 0.64, timestamp: '2024-03-14T16:20:00Z' },
      { id: 'wc6', task: 'extraction', document: 'Technical Architecture Brief', route: 'direct', status: 'failed', needsReview: true, confidence: 0, qualityScore: 0, timestamp: '2024-03-14T15:00:00Z' },
    ],
    meta: makeSource('mock'),
  };
}

export function getWorkflowAttempts(): { data: WorkflowAttempt[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'wa1', route: 'direct', status: 'completed', confidence: 0.94, qualityScore: 0.91, needsReview: false, guardrailTriggered: false, durationMs: 8400, tokenCount: 3420, timestamp: '2024-03-15T10:30:00Z' },
      { id: 'wa2', route: 'langgraph', status: 'completed', confidence: 0.72, qualityScore: 0.78, needsReview: true, guardrailTriggered: true, guardrailReason: 'Confidence below threshold (0.72 < 0.80) on Data Processing Addendum 2024 extraction. Routed to multi-step agent for deeper entity resolution.', durationMs: 14200, tokenCount: 6180, timestamp: '2024-03-15T09:15:00Z' },
      { id: 'wa3', route: 'fallback', status: 'completed', confidence: 0.58, qualityScore: 0.64, needsReview: true, guardrailTriggered: true, guardrailReason: 'LangGraph agent timed out after 30s on Vendor Risk Assessment Template. Fallback to simplified contract risk extraction.', durationMs: 32000, tokenCount: 8900, timestamp: '2024-03-14T16:20:00Z' },
    ],
    meta: makeSource('mock'),
  };
}

// ─── Benchmarks ────────────────────────────────────────────
export function getBenchmarkPresets(): { data: BenchmarkPreset[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'bp1', name: 'Contract Review (Production)', description: 'Extraction + risk identification from legal documents — recommended production profile', metrics: ['adherence', 'groundedness', 'latency'], models: ['m2', 'm3'] },
      { id: 'bp2', name: 'Fast Triage (Local)', description: 'Low-latency classification and routing for high-volume document intake', metrics: ['latency', 'adherence'], models: ['m4', 'm2'] },
      { id: 'bp3', name: 'Deep Analysis (Reference)', description: 'Complex multi-step reasoning with full evidence chain — external quality ceiling', metrics: ['groundedness', 'useCaseFit', 'adherence'], models: ['m1', 'm3', 'm5'] },
    ],
    meta: makeSource('mock'),
  };
}

export function getStrategyBenchmarks(): { data: StrategyBenchmark[]; meta: DataSourceMeta } {
  return {
    data: [
      { strategy: 'hybrid_rerank', precision: 0.89, recall: 0.91, f1: 0.90, latency: 1.8, description: 'BM25 + semantic with cross-encoder reranking — recommended production strategy' },
      { strategy: 'semantic_only', precision: 0.84, recall: 0.88, f1: 0.86, latency: 1.2, description: 'Pure vector similarity search' },
      { strategy: 'bm25_only', precision: 0.78, recall: 0.82, f1: 0.80, latency: 0.3, description: 'Lexical keyword matching — fastest, suitable for triage' },
      { strategy: 'ensemble_weighted', precision: 0.91, recall: 0.89, f1: 0.90, latency: 2.4, description: 'Weighted ensemble with learned fusion — highest precision' },
    ],
    meta: makeSource('mock'),
  };
}

// ─── Lab Artifacts ─────────────────────────────────────────
export function getLabArtifacts(): { data: LabArtifact[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'la1', name: 'Extraction Benchmark Report', type: 'benchmark', category: 'Benchmarks', version: 'v3', createdAt: '2024-03-15T09:00:00Z', size: '2.1 MB', status: 'ready', description: 'Qwen 2.5 vs GPT-4o vs Llama 3.1 comparison across contract extraction tasks with latency/quality tradeoff analysis' },
      { id: 'la2', name: 'Eval Regression Analysis — extraction_entities', type: 'eval', category: 'Evals', version: 'v2', createdAt: '2024-03-15T09:30:00Z', size: '890 KB', status: 'ready', description: 'Root cause analysis: extraction_entities dropped from 94% to 62% on Master Service Agreement v4.2 Section 7' },
      { id: 'la3', name: 'OCR Diagnostic — Technical Architecture Brief', type: 'ocr_diagnostic', category: 'Document Processing', version: 'v1', createdAt: '2024-03-14T15:30:00Z', size: '3.4 MB', status: 'ready', description: 'Page-level OCR quality analysis for Technical Architecture Brief pages 12-15 with Tesseract and Surya fallback attempts' },
      { id: 'la4', name: 'Embedding Space Visualization', type: 'embedding_experiment', category: 'Retrieval', version: 'v1', createdAt: '2024-03-13T14:00:00Z', size: '1.2 MB', status: 'ready', description: 'UMAP projection of document chunk embeddings (nomic-embed-text) across Master Service Agreement v4.2, Data Processing Addendum 2024 and Cloud Infrastructure SLA' },
      { id: 'la5', name: 'Reranking Strategy Comparison', type: 'benchmark', category: 'Retrieval', version: 'v2', createdAt: '2024-03-14T10:00:00Z', size: '780 KB', status: 'ready', description: 'Precision/recall tradeoffs across hybrid_rerank, semantic_only, bm25_only and ensemble_weighted strategies' },
      { id: 'la6', name: 'Q1 Workflow Execution Report', type: 'report', category: 'Operations', version: 'v1', createdAt: '2024-03-15T11:00:00Z', size: '1.6 MB', status: 'generating', description: 'Aggregated workflow execution statistics for Q1 2024 across all document review, comparison and extraction runs' },
    ],
    meta: makeSource('mock'),
  };
}

// ─── EvidenceOps ───────────────────────────────────────────
export function getOpenActions(): { data: OpenAction[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'oa1', title: 'Resolve OCR failure on Technical Architecture Brief', status: 'open', owner: 'Engineering', dueDate: '2024-03-18', target: 'Ingestion', priority: 'high' },
      { id: 'oa2', title: 'Investigate extraction_entities regression on Master Service Agreement v4.2', status: 'in_progress', owner: 'ML Team', dueDate: '2024-03-16', target: 'Evals', priority: 'high' },
      { id: 'oa3', title: 'Add GDPR Compliance Checklist eval suite', status: 'open', owner: 'Compliance', dueDate: '2024-03-22', target: 'Evals', priority: 'medium' },
      { id: 'oa4', title: 'Benchmark Phi-3 Medium on contract extraction tasks', status: 'blocked', owner: 'ML Team', dueDate: '2024-03-20', target: 'Benchmarks', priority: 'low' },
    ],
    meta: makeSource('mock'),
  };
}

export function getAutoOperations(): { data: AutoOperation[]; meta: DataSourceMeta } {
  return {
    data: [
      { id: 'ao1', operation: 'auto_register', tool: 'auto_register', status: 'success', timestamp: '2024-03-15T06:00:00Z', durationMs: 560, detail: 'Registered 2 new documents from watch folder' },
      { id: 'ao2', operation: 'drift_check', tool: 'detect_repository_drift', status: 'warning', timestamp: '2024-03-14T12:00:00Z', durationMs: 2400, detail: 'Minor drift: Technical Architecture Brief removed from source but still referenced in index' },
      { id: 'ao3', operation: 'index_health_check', tool: 'check_index_health', status: 'success', timestamp: '2024-03-15T03:00:00Z', durationMs: 890, detail: 'All 7 indexed documents verified, 1360 chunks healthy' },
      { id: 'ao4', operation: 'eval_run', tool: 'run_eval_suite', status: 'success', timestamp: '2024-03-15T09:00:00Z', durationMs: 45200, detail: 'Ran 68 eval cases across 5 suites. 2 failures: extraction_entities, candidate_scoring' },
    ],
    meta: makeSource('mock'),
  };
}