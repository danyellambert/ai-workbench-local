import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import CandidateReviewPage from '@/pages/CandidateReviewPage';
import {
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  getProductUploadJob,
  runProductWorkflow,
  uploadProductDocuments,
  type ProductRunWorkflowResponse,
} from '@/lib/product-api';

vi.mock('@/components/ui/sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('@/lib/product-api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/product-api')>('@/lib/product-api');
  return {
    ...actual,
    getProductDocumentLibrary: vi.fn(),
    getProductGroundingPreview: vi.fn(),
    runProductWorkflow: vi.fn(),
    generateProductWorkflowDeck: vi.fn(),
    uploadProductDocuments: vi.fn(),
    getProductUploadJob: vi.fn(),
  };
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <CandidateReviewPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function buildWorkflowResponse(): ProductRunWorkflowResponse {
  return {
    ok: true,
    run_id: 'run-candidate-1',
    result: {
      workflow_id: 'candidate_review',
      workflow_label: 'Candidate Review',
      status: 'completed',
      summary: 'Sarah Chen shows strong senior ML systems and retrieval grounding experience.',
      highlights: ['Strong retrieval systems background'],
      recommendation: 'Advance to panel interview.',
      structured_result: {
        success: true,
        validated_output: {},
        overall_confidence: 0.9,
        quality_score: 0.88,
      },
      grounding_preview: {
        strategy: 'document_scan',
        document_ids: ['doc-cv'],
        context_chars: 640,
        source_block_count: 4,
        preview_text: 'Sarah Chen led ML platform and retrieval initiatives across hiring packet evidence.',
        warnings: [],
      },
      artifacts: [
        {
          artifact_type: 'json',
          label: 'Structured review JSON',
          path: '/tmp/candidate-review.json',
          download_name: 'candidate-review.json',
          available: true,
        },
      ],
      deck_export_kind: 'candidate_review_deck',
      deck_available: true,
      warnings: [],
      debug_metadata: {},
    },
    result_sections: {
      summary: 'Sarah Chen shows strong senior ML systems and retrieval grounding experience.',
      highlights: ['Strong retrieval systems background'],
      recommendation: 'Advance to panel interview.',
      warnings: [],
      tables: [
        {
          title: 'Experience highlights',
          headers: ['Role', 'Company', 'Period', 'Evidence'],
          rows: [['Senior ML Engineer', 'Acme AI', '2022-2026', 'Led retrieval and ranking systems.']],
        },
        {
          title: 'Evidence highlights',
          headers: ['Signal', 'Confidence', 'Source', 'Evidence'],
          rows: [['Retrieval systems', '0.92', 'CV', 'Led ranking and search quality improvements.']],
        },
      ],
      sources: [['CV', '1', '0.92', 'Led ranking and search quality improvements.']],
      artifacts: [
        {
          artifact_type: 'json',
          label: 'Structured review JSON',
          path: '/tmp/candidate-review.json',
          download_name: 'candidate-review.json',
          available: true,
        },
      ],
      candidate_profile: {
        name: 'Sarah Chen',
        headline: 'Senior ML Engineer · Retrieval & Platforms',
        location: 'Remote',
      },
      strengths: ['Strong retrieval systems background', 'Clear seniority signals in platform ownership'],
      watchouts: ['Validate org-scale stakeholder management depth'],
      next_steps: ['Probe system ownership depth', 'Validate hiring scorecard against stakeholder feedback'],
      evidence_highlights: [['Retrieval systems', '0.92', 'CV', 'Led ranking and search quality improvements.']],
    },
  };
}

describe('CandidateReviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('open', vi.fn());

    vi.mocked(getProductDocumentLibrary).mockResolvedValue({
      ok: true,
      summary: {
        total_documents: 1,
        indexed_documents: 1,
        warning_documents: 0,
        error_documents: 0,
        pending_documents: 0,
        indexing_documents: 0,
        total_chunks: 4,
        total_chars: 1600,
      },
      documents: [
        {
          document_id: 'doc-cv',
          name: 'Sarah Chen - Senior ML Engineer CV.pdf',
          file_type: 'pdf',
          char_count: 1600,
          chunk_count: 4,
          indexed_at: '2026-04-18T12:00:00',
          loader_strategy_label: 'Manual Upload',
          status: 'indexed',
          warnings: [],
        },
      ],
    });

    vi.mocked(getProductGroundingPreview).mockResolvedValue({
      ok: true,
      preview: {
        strategy: 'document_scan',
        document_ids: ['doc-cv'],
        context_chars: 640,
        source_block_count: 4,
        preview_text: 'Sarah Chen led ML platform and retrieval initiatives across hiring packet evidence.',
        warnings: [],
      },
    });

    vi.mocked(runProductWorkflow).mockResolvedValue(buildWorkflowResponse());
    vi.mocked(generateProductWorkflowDeck).mockResolvedValue({
      ok: true,
      export_result: { status: 'completed', export_kind: 'candidate_review_deck' },
      artifacts: [
        {
          artifact_type: 'pptx',
          label: 'Candidate Review Deck',
          path: '/tmp/candidate-review-deck.pptx',
          download_name: 'candidate-review-deck.pptx',
          available: true,
        },
      ],
    });
    vi.mocked(uploadProductDocuments).mockResolvedValue({
      ok: true,
      job_id: 'job-1',
      status: 'queued',
      uploaded_count: 1,
      ignored_count: 0,
      message: 'Queued',
      steps: [],
    });
    vi.mocked(getProductUploadJob).mockResolvedValue({
      ok: true,
      job_id: 'job-1',
      status: 'completed',
      uploaded_count: 1,
      ignored_count: 0,
      message: 'Indexed',
      steps: [],
    });
  });

  it('filters duplicate and placeholder experience rows before rendering them', async () => {
    vi.mocked(runProductWorkflow).mockResolvedValueOnce({
      ...buildWorkflowResponse(),
      result_sections: {
        ...buildWorkflowResponse().result_sections,
        tables: [
          {
            title: 'Experience highlights',
            headers: ['Role', 'Company', 'Period', 'Evidence'],
            rows: [
              ['Senior ML Engineer', 'Acme AI', '2022-2026', 'Led retrieval and ranking systems.'],
              ['Senior ML Engineer', 'Acme AI', '2022-2026', 'Led retrieval and ranking systems.'],
              ['-', '-', '2022-2026', '-'],
              ['', '', '', ''],
            ],
          },
        ],
        evidence_highlights: [['Retrieval systems', '0.92', 'CV', 'Led ranking and search quality improvements.']],
      },
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('candidate-review-candidate-name')).toHaveTextContent('Sarah Chen - Senior ML Engineer CV.pdf');
    });

    fireEvent.click(screen.getByRole('button', { name: /run candidate review/i }));

    await waitFor(() => {
      expect(screen.getAllByTestId('candidate-review-experience-row')).toHaveLength(1);
    });
    expect(screen.getByText('1 structured experience row(s)')).toBeInTheDocument();
    expect(screen.queryByText('-', { selector: 'h5' })).not.toBeInTheDocument();
  });

  it('keeps analysis internals collapsed by default and reveals them on demand', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('candidate-review-candidate-name')).toHaveTextContent('Sarah Chen - Senior ML Engineer CV.pdf');
    });
    expect(screen.queryByText('Candidate grounding preview')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('candidate-review-analysis-internals-toggle'));

    expect(screen.getByText('Candidate grounding preview')).toBeInTheDocument();
    expect(screen.getByText('Generated review input')).toBeInTheDocument();
  });


  it('runs the live candidate workflow and renders grounded sections plus deck artifacts', async () => {
    renderPage();

    expect(screen.getByTestId('candidate-review-page')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('candidate-review-candidate-name')).toHaveTextContent('Sarah Chen - Senior ML Engineer CV.pdf');
    });

    fireEvent.click(screen.getByRole('button', { name: /run candidate review/i }));

    expect(await screen.findByText('Sarah Chen')).toBeInTheDocument();
    expect(screen.getByText('Advance to panel interview.')).toBeInTheDocument();
    expect(screen.getAllByText('Strong retrieval systems background').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: /generate deck/i }));

    await waitFor(() => {
      expect(generateProductWorkflowDeck).toHaveBeenCalledWith(expect.anything(), { runId: 'run-candidate-1' });
    });
    expect(await screen.findByText('Candidate Review Deck')).toBeInTheDocument();
  });
});
