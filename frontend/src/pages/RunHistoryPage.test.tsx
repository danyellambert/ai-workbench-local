import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import RunHistoryPage from '@/pages/RunHistoryPage';
import { getProductRunHistory, getProductRunHistoryEntry, rerunProductRunHistoryEntry } from '@/lib/product-api';

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
    getProductRunHistory: vi.fn(),
    getProductRunHistoryEntry: vi.fn(),
    rerunProductRunHistoryEntry: vi.fn(),
  };
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <RunHistoryPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('RunHistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(getProductRunHistory).mockResolvedValue({
      ok: true,
      summary: {
        total_runs: 2,
        completed_runs: 1,
        warning_runs: 1,
        error_runs: 0,
        workflow_counts: { candidate_review: 1 },
        latest_timestamp: '2026-04-18T18:00:00',
      },
      runs: [
        {
          id: 'run-1',
          workflow_id: 'candidate_review',
          workflow_label: 'Candidate Review',
          status: 'completed',
          provider: 'ollama',
          model: 'qwen2.5:14b',
          duration_label: '12s',
          documents: ['Sarah Chen - Senior ML Engineer CV.pdf'],
          document_count: 1,
          findings_count: 2,
          recommendation: 'Advance to panel interview.',
          can_rerun: true,
          artifact_items: [
            {
              artifact_type: 'pptx',
              label: 'Candidate Review Deck',
              path: 'artifacts/candidate-review-deck.pptx',
              available: true,
            },
          ],
        },
      ],
    });

    vi.mocked(getProductRunHistoryEntry).mockResolvedValue({
      ok: true,
      run: {
        id: 'run-1',
        workflow_id: 'candidate_review',
        workflow_label: 'Candidate Review',
        status: 'completed',
        provider: 'ollama',
        model: 'qwen2.5:14b',
        duration_label: '12s',
        documents: ['Sarah Chen - Senior ML Engineer CV.pdf'],
        document_count: 1,
        findings_count: 2,
        recommendation: 'Advance to panel interview.',
        can_rerun: true,
        request_payload: {
          workflow_id: 'candidate_review',
          document_ids: ['doc-cv'],
        },
        response_payload: {
          workflow_id: 'candidate_review',
          status: 'completed',
        },
        result_sections: {
          summary: 'Grounded summary from persisted run.',
          highlights: ['Strong retrieval background'],
          warnings: [],
          tables: [],
          sources: [],
          artifacts: [],
          strengths: ['Strong retrieval background'],
          watchouts: [],
          next_steps: ['Advance to panel interview'],
          evidence_highlights: [],
        },
        artifact_items: [
          {
            artifact_type: 'pptx',
            label: 'Candidate Review Deck',
            path: 'artifacts/candidate-review-deck.pptx',
            available: true,
          },
        ],
      },
    });

    vi.mocked(rerunProductRunHistoryEntry).mockResolvedValue({
      ok: true,
      run_id: 'run-2',
      reran_from_run_id: 'run-1',
      source_run: {
        id: 'run-1',
        workflow_label: 'Candidate Review',
        status: 'completed',
        documents: ['Sarah Chen - Senior ML Engineer CV.pdf'],
      },
      result: {
        workflow_id: 'candidate_review',
        workflow_label: 'Candidate Review',
        status: 'completed',
        summary: 'Rerun completed',
        highlights: [],
        artifacts: [],
        deck_available: true,
        warnings: [],
      },
    });
  });

  it('loads run detail and triggers rerun from the live history surface', async () => {
    renderPage();

    expect(await screen.findByText('Candidate Review')).toBeInTheDocument();
    expect(await screen.findByText('Grounded summary from persisted run.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Rerun from history/i }));

    await waitFor(() => {
      expect(rerunProductRunHistoryEntry).toHaveBeenCalledWith('run-1');
    });
  });
});
