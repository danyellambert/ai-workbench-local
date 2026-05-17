import type { ComponentType } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import AdvancedExperimentsPage from '@/pages/AdvancedExperimentsPage';
import BenchmarksPage from '@/pages/BenchmarksPage';
import ChatPage from '@/pages/ChatPage';
import EvidenceOpsPage from '@/pages/EvidenceOpsPage';
import EvalsDiagnosisPage from '@/pages/EvalsDiagnosisPage';
import LabOverviewPage from '@/pages/LabOverviewPage';
import RuntimeObservabilityPage from '@/pages/RuntimeObservabilityPage';
import WorkflowInspectorPage from '@/pages/WorkflowInspectorPage';

const pages = [
  { Component: LabOverviewPage, heading: 'AI Engineering Operating Console' },
  { Component: RuntimeObservabilityPage, heading: 'Runtime & Observability' },
  { Component: ChatPage, heading: 'Document / Chat Experiments' },
  { Component: WorkflowInspectorPage, heading: 'Workflow Inspector' },
  { Component: BenchmarksPage, heading: 'Benchmarks' },
  { Component: EvalsDiagnosisPage, heading: 'Evals & Diagnosis' },
  { Component: AdvancedExperimentsPage, heading: 'Experiments & Artifacts' },
  { Component: EvidenceOpsPage, heading: 'MCP Operations' },
];

function mockFetch(url: string) {
  if (url.includes('/api/lab/overview')) {
    return {
      ok: true,
      meta: { source: 'derived', updated_at: '2026-04-18T00:00:00Z' },
      runtime: {
        generationProvider: 'ollama',
        generationModel: 'nemotron-3-nano:30b-cloud',
        vectorBackendStatus: 'healthy',
        indexedDocumentCount: 4,
        contextPressure: 0.35,
        ingestionHealth: 'healthy',
      },
      kpis: [
        { label: 'Indexed Documents', value: 4, status: 'healthy' },
        { label: 'Total Chunks', value: '9', status: 'healthy' },
      ],
      alerts: [],
      workflow_mix: [{ name: 'Document Review', value: 3 }],
      review_rate: 10,
    };
  }
  if (url.includes('/api/lab/runtime')) {
    return {
      ok: true,
      meta: { source: 'derived' },
      runtime: { provider: 'ollama', model: 'nemotron-3-nano:30b-cloud' },
      generation_rows: [{ label: 'Context Window', value: '32k', status: 'healthy' }],
      retrieval_rows: [{ label: 'Top-K', value: '12', status: 'healthy' }],
      vector_rows: [{ label: 'Backend', value: 'local', status: 'healthy' }],
      diagnostics_rows: [{ label: 'Latency', value: '2.1s', status: 'healthy' }],
    };
  }
  if (url.includes('/api/lab/chat')) {
    return {
      ok: true,
      meta: { source: 'live', updated_at: '2026-04-18T00:00:00Z' },
      capabilities: { can_send: true, reason: null },
      active_session_id: 'session-test',
      sessions: [{ id: 'session-test', title: 'Validation session', updated_at: '2026-04-18T00:00:00Z' }],
      messages: [
        {
          id: 'assistant-seed',
          role: 'assistant',
          status: 'success',
          content: 'Grounded AI LAB chat is available for this workspace.',
          sources: [{ doc: 'doc-1', chunk: 'source-1', score: 0.92 }],
        },
      ],
      suggested_prompts: [
        'Summarize the main control gaps in the selected evidence.',
        'Turn the findings into next actions with owners and due dates.',
      ],
      selected_documents: [
        { document_id: 'doc-1', name: 'Access Review Evidence Log.pdf', status: 'indexed', chunk_count: 2, char_count: 200, size_label: '4.1 KB', warnings: [] },
        { document_id: 'doc-2', name: 'Privileged Account Approval Email.pdf', status: 'indexed', chunk_count: 2, char_count: 180, size_label: '4.0 KB', warnings: [] },
      ],
      session_diagnostics: [
        { icon: 'messages', label: 'Messages', value: '1' },
        { icon: 'tokens', label: 'Tokens used', value: '321' },
      ],
      retrieval_quality: {
        strategy: 'hybrid',
        rerankPoolSize: 40,
        avgRelevance: 87,
        chunksRetrieved: 2,
      },
    };
  }
  if (url.includes('/api/lab/workflow-inspector')) {
    return {
      ok: true,
      meta: { source: 'live', updated_at: '2026-04-18T00:00:00Z' },
      capabilities: { can_execute: true, reason: null },
      summary: { total_cases: 4, needs_review: 1, avg_confidence: 82, review_blockers: 1, failed: 0 },
      document_options: [
        { id: 'doc-1', name: 'Access Review Evidence Log.pdf', status: 'indexed' },
        { id: 'doc-2', name: 'Privileged Account Approval Email.pdf', status: 'indexed' },
      ],
      task_options: [
        { id: 'extract_operational_tasks', label: 'Action Plan Extraction', description: 'Operational action-plan extraction.', recent_count: 4 },
      ],
      selected_task_id: 'extract_operational_tasks',
      task_details: {
        extract_operational_tasks: {
          id: 'extract_operational_tasks',
          label: 'Action Plan Extraction',
          description: 'Operational action-plan extraction.',
          result_title: 'Latest persisted trace',
          result_items: [{ label: 'Query', value: 'Build a grounded action plan', confidence: null }],
          trace_fields: [{ label: 'Tool', value: 'extract_operational_tasks' }],
        },
      },
      recent_cases: [{ id: 'case-1', title: 'Validation run', status: 'completed', timestamp: '2026-04-18T00:00:00Z' }],
    };
  }
  if (url.includes('/api/lab/benchmarks')) {
    return {
      ok: true,
      meta: { source: 'derived', updated_at: '2026-04-18T00:00:00Z' },
      status: 'derived-live',
      summary: {
        modelCount: 2,
        scoredModelCount: 1,
        partialModelCount: 1,
        promptProfileCount: 1,
        useCaseCount: 1,
        scoredCandidateCount: 2,
        bestGroundedness: 0.34,
        fastestLatency: 0.82,
        bestModel: 'nemotron-3-nano:30b-cloud',
        totalRuns: 4,
        lastRecordedAt: '2026-04-18T00:00:00Z',
      },
      models: [
        {
          id: 'ollama:nemotron-3-nano:30b-cloud',
          family: 'nemotron-3-nano:30b-cloud',
          provider: 'ollama',
          model: 'nemotron-3-nano:30b-cloud',
          profileTag: 'Recommended production',
          useCaseFit: 0.82,
          groundedness: 0.34,
          adherence: 0.96,
          latency: 2.1,
          outputChars: 980,
          runtimeBucket: 'cloud',
          quantization: 'cloud_managed',
          runs: 3,
          scoreStatus: 'scored',
          metricCoverage: { useCaseFit: 2, groundedness: 2, adherence: 3, latency: 3, outputChars: 3 },
        },
        {
          id: 'huggingface_inference:meta-llama/Llama-3.1-8B-Instruct',
          family: 'meta-llama/Llama-3.1-8B-Instruct',
          provider: 'huggingface_inference',
          model: 'meta-llama/Llama-3.1-8B-Instruct',
          profileTag: 'Fastest observed',
          useCaseFit: null,
          groundedness: null,
          adherence: 0.91,
          latency: 0.82,
          outputChars: 1100,
          runtimeBucket: 'cloud',
          quantization: 'cloud_managed',
          runs: 1,
          scoreStatus: 'partial',
          metricCoverage: { useCaseFit: 0, groundedness: 0, adherence: 1, latency: 1, outputChars: 1 },
        },
      ],
      presets: [{ id: 'default', name: 'default', description: 'Default prompt profile.', metrics: ['use case fit', 'groundedness'], models: ['nemotron-3-nano:30b-cloud'] }],
      providerSummary: [
        { provider: 'ollama', models: 1, scoredModels: 1, bestFit: 82, avgLatency: 2.1, bestModel: 'nemotron-3-nano:30b-cloud' },
        { provider: 'huggingface_inference', models: 1, scoredModels: 0, bestFit: null, avgLatency: 0.82, bestModel: null },
      ],
      leaderboardHighlights: [
        { label: 'Best scored fit', model: 'nemotron-3-nano:30b-cloud', detail: '82% use-case fit across 2 scored runs' },
      ],
      retrievalObservations: [
        {
          strategy: 'manual_hybrid',
          outputDiscipline: 0.94,
          contextRetention: 0.88,
          composite: 0.76,
          latency: 1.8,
          candidateCount: 4,
          scoredCandidateCount: 2,
          avgContextChars: 3200,
          description: 'Stable across recent runs.',
        },
      ],
    };
  }
  if (url.includes('/api/lab/evals')) {
    return {
      ok: true,
      meta: { source: 'derived' },
      passRate: 82,
      totals: { pass: 8, warn: 1, fail: 1, review: 2, total: 10 },
      suites: [{ name: 'document_review', total: 10, pass: 8, warn: 1, fail: 1, needsReview: 2, lastRun: '2026-04-18T00:00:00Z' }],
      cases: [{ id: 'case-1', task: 'document_review', suite: 'document_review', verdict: 'FAIL', score: 0.61, needsReview: true, model: 'nemotron-3-nano:30b-cloud', latency: 4.2, timestamp: '2026-04-18T00:00:00Z', errorDetail: 'Synthetic test failure' }],
      diagnosis: {},
    };
  }
  if (url.includes('/api/lab/artifacts')) {
    return {
      ok: true,
      meta: { source: 'derived' },
      artifacts: [{
        id: 'deckexp_1',
        name: 'Validation deck',
        type: 'deck_bundle',
        category: 'Document Review',
        version: 'deckexp_1',
        createdAt: '2026-04-18T00:00:00Z',
        size: '48 KB',
        status: 'ready',
        description: 'document review deck · 6 slide(s) · 6 preview(s)',
        workflowLabel: 'Document Review',
        exportKind: 'document_review_deck',
        slideCount: 6,
        previewCount: 6,
        issueCount: 0,
        warningCount: 0,
        assetCount: 5,
      }],
      summary: { totalArtifacts: 1, readyArtifacts: 1, warningArtifacts: 0, errorArtifacts: 0, chatSessions: 1, workflowRuns: 1, linkedWorkflowRuns: 1, unlinkedWorkflowRuns: 0, previewAssets: 6, issueCount: 0, workflowCount: 1, benchmarkArtifacts: 0 },
      diagnostics: [{ label: 'Bundle registry', detail: '1 product-visible export bundle.', status: 'ready', health: 'healthy' }],
      runRegistry: { latestChatSession: 'session-1', latestWorkflowRun: 'run-1', latestWorkflowArtifact: { label: 'Validation deck', runId: 'run-1', updatedAt: '2026-04-18T00:00:00Z' } },
      recentCaptures: [{ id: 'deckexp_1', label: 'Validation deck', workflowLabel: 'Document Review', exportKind: 'document_review_deck', status: 'ready', createdAt: '2026-04-18T00:00:00Z', slideCount: 6, previewCount: 6, issueCount: 0, warningCount: 0, assetCount: 5 }],
    };
  }
  if (url.includes('/api/lab/evidenceops/search')) {
    return {
      ok: true,
      meta: { source: 'derived' },
      query: 'vendor',
      repositoryRoot: '/tmp/repository',
      results: [{ path: 'vendor/access-review.md', title: 'Vendor access review' }],
    };
  }
  if (url.includes('/api/lab/evidenceops')) {
    return {
      ok: true,
      meta: { source: 'derived' },
      summary: { toolsTotal: 4, activeTools: 3, openActions: 1, operationsCount: 2, repositoryDocumentCount: 4 },
      tools: [{ name: 'local_repository_scan', description: 'Scans corpus', status: 'active', lastCall: '2026-04-18T00:00:00Z' }],
      actions: [{ id: 'action-1', title: 'Review evidence gap', status: 'open', owner: 'Unassigned', dueDate: '—', target: 'Document Risk Review', priority: 'high', rawStatus: 'recommended', evidence: null, sourceCount: 2 }],
      operations: [{ id: 'repository-scan', operation: 'repository_scan', tool: 'local_repository_scan', status: 'success', timestamp: '2026-04-18T00:00:00Z', durationMs: 12, detail: '4 documents visible.' }],
      telemetry: [{ event: 'repository_scan', tool: 'local_repository_scan', status: 'ok', latency: '12ms', ts: '2026-04-18T00:00:00Z' }],
      readiness: [{ label: 'Repository', status: 'ready', detail: 'Connected' }],
    };
  }
  if (url.includes('/api/product/document-library')) {
    return {
      ok: true,
      summary: { total_documents: 2, indexed_documents: 2, warning_documents: 0, error_documents: 0, pending_documents: 0, indexing_documents: 0, total_chunks: 6, total_chars: 1200 },
      documents: [
        { document_id: 'doc-1', name: 'Access Review Evidence Log.pdf', status: 'indexed', chunk_count: 2, char_count: 200, size_label: '4.1 KB', warnings: [] },
        { document_id: 'doc-2', name: 'Privileged Account Approval Email.pdf', status: 'indexed', chunk_count: 2, char_count: 180, size_label: '4.0 KB', warnings: [] },
      ],
    };
  }
  if (url.includes('/api/runtime/controls')) {
    return {
      ok: true,
      active_profile: {
        primaryModel: 'nemotron-3-nano:30b-cloud',
        primaryConnectionId: 'ollama',
        retrievalStrategy: 'hybrid',
        generation: { contextWindow: '32k' },
        retrieval: { topK: 12, rerankPoolSize: 40 },
      },
    };
  }
  if (url.includes('/api/product/run-workflow')) {
    return {
      ok: true,
      result: {
        status: 'completed',
        summary: 'Grounded workflow response.',
        highlights: ['One', 'Two'],
        warnings: [],
        debug_metadata: { model: 'nemotron-3-nano:30b-cloud' },
        grounding_preview: { document_ids: ['doc-1'], source_block_count: 2, context_chars: 500 },
        structured_result: { execution_metadata: { usage_metrics: { total_tokens: 321 } } },
      },
    };
  }
  return { ok: true };
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    return new Response(JSON.stringify(mockFetch(url)), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderWithProviders(Component: ComponentType) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Component />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AI Lab pages', () => {
  it.each(pages)('renders $heading', ({ Component, heading }) => {
    renderWithProviders(Component);
    expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument();
  });

  it('exposes a real send action on chat experiments page', async () => {
    renderWithProviders(ChatPage);
    expect(await screen.findByRole('button', { name: /send chat message/i })).toBeInTheDocument();
  });

  it('shows the workflow inspector primary action', async () => {
    renderWithProviders(WorkflowInspectorPage);
    expect(await screen.findByRole('button', { name: /execute task|execution unavailable/i })).toBeInTheDocument();
  });
});
