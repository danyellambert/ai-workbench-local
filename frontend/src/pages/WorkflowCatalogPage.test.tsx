import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import WorkflowCatalogPage from '@/pages/WorkflowCatalogPage';
import { getProductDocumentLibrary, getProductRunHistory, getProductWorkflows } from '@/lib/product-api';

vi.mock('@/lib/product-api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/product-api')>('@/lib/product-api');
  return {
    ...actual,
    getProductWorkflows: vi.fn(),
    getProductDocumentLibrary: vi.fn(),
    getProductRunHistory: vi.fn(),
  };
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <WorkflowCatalogPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('WorkflowCatalogPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getProductWorkflows).mockResolvedValue({
      contract_version: 'product_workflows.v1',
      product_headline: 'Decision workflows',
      workflow_count: 2,
      executive_deck_catalog: [{ export_kind: 'candidate_review_deck', label: 'Candidate Review Deck' }],
      workflows: [
        {
          workflow_id: 'candidate_review',
          label: 'Candidate Review',
          headline: 'Evaluate candidate evidence live.',
          description: 'Grounded candidate review using indexed resume and hiring packet documents.',
          required_document_count_min: 1,
          required_document_count_max: 1,
          supports_optional_prompt: true,
          default_export_kind: 'candidate_review_deck',
          default_export_label: 'Candidate Review Deck',
          backend_task_types: ['candidate_review'],
          badge_items: ['live', 'deck-ready'],
          preferred_context_strategy: 'document_scan',
          input_placeholder: 'Evaluate this CV',
          example_prompts: ['Evaluate this CV for a senior role'],
          expected_outputs: ['strengths', 'watchouts'],
          workflow_contract: 'candidate_review.v1',
        },
        {
          workflow_id: 'document_review',
          label: 'Document Review',
          headline: 'Review document evidence.',
          description: 'Grounded document review using live retrieval.',
          required_document_count_min: 1,
          required_document_count_max: 1,
          supports_optional_prompt: true,
          default_export_kind: 'document_review_deck',
          default_export_label: 'Document Review Deck',
          backend_task_types: ['document_review'],
          badge_items: ['live'],
          preferred_context_strategy: 'retrieval',
          input_placeholder: 'Review this document',
          example_prompts: ['Review this document'],
          expected_outputs: ['summary'],
          workflow_contract: 'document_review.v1',
        },
      ],
    });

    vi.mocked(getProductDocumentLibrary).mockResolvedValue({
      ok: true,
      summary: {
        total_documents: 2,
        indexed_documents: 2,
        warning_documents: 0,
        error_documents: 0,
        pending_documents: 0,
        indexing_documents: 0,
        total_chunks: 6,
        total_chars: 2400,
      },
      documents: [
        {
          document_id: 'doc-cv',
          name: 'Sarah Chen - Senior ML Engineer CV.pdf',
          file_type: 'pdf',
          char_count: 1400,
          chunk_count: 3,
          indexed_at: '2026-04-18T12:00:00',
          loader_strategy_label: 'Manual Upload',
          status: 'indexed',
          warnings: [],
        },
        {
          document_id: 'doc-policy',
          name: 'Policy.pdf',
          file_type: 'pdf',
          char_count: 1000,
          chunk_count: 3,
          indexed_at: '2026-04-18T12:00:00',
          loader_strategy_label: 'Manual Upload',
          status: 'indexed',
          warnings: [],
        },
      ],
    });

    vi.mocked(getProductRunHistory).mockResolvedValue({
      ok: true,
      summary: {
        total_runs: 3,
        completed_runs: 2,
        warning_runs: 1,
        error_runs: 0,
        workflow_counts: { candidate_review: 1, document_review: 2 },
        latest_timestamp: '2026-04-18T15:00:00',
      },
      runs: [
        {
          id: 'run-1',
          workflow_id: 'candidate_review',
          workflow_label: 'Candidate Review',
          status: 'completed',
          documents: ['Sarah Chen - Senior ML Engineer CV.pdf'],
          timestamp: '2026-04-18T15:00:00',
        },
      ],
    });
  });

  it('renders live workflow readiness signals from backend contracts', async () => {
    renderPage();

    expect(await screen.findByText('Run surface is live')).toBeInTheDocument();
    expect(screen.getByText('Candidate Review')).toBeInTheDocument();
    expect(screen.getByText(/1 eligible document/)).toBeInTheDocument();
    expect(screen.getByText(/1 persisted run/)).toBeInTheDocument();
    expect(screen.getByText('retrieval-grounded')).toBeInTheDocument();
  });
});
