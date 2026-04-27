import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import DeckCenterPage from '@/pages/DeckCenterPage';
import { getProductArtifactEntry, getProductArtifacts } from '@/lib/product-api';

vi.mock('@/lib/product-api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/product-api')>('@/lib/product-api');
  return {
    ...actual,
    getProductArtifacts: vi.fn(),
    getProductArtifactEntry: vi.fn(),
  };
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <DeckCenterPage />
    </QueryClientProvider>,
  );
}

describe('DeckCenterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('open', vi.fn());

    vi.mocked(getProductArtifacts).mockResolvedValue({
      ok: true,
      artifact_root: 'artifacts/presentation_exports',
      summary: {
        total_artifacts: 1,
        completed_artifacts: 1,
        error_artifacts: 0,
      },
      artifacts: [
        {
          id: 'artifact-1',
          name: 'candidate-review-deck.pptx',
          title: 'Candidate Review Deck',
          type: 'pptx',
          workflow_label: 'Candidate Review',
          created_at: '2026-04-18T18:00:00',
          size: '128 KB',
          status: 'ready',
          export_kind: 'candidate_review_deck',
          local_pptx_path: 'artifacts/presentation_exports/candidate-review-deck.pptx',
          local_payload_path: 'artifacts/presentation_exports/candidate-review-payload.json',
          slide_count: 8,
          preview_count: 8,
          asset_count: 3,
          average_score: 8.9,
          issue_count: 0,
          warning_count: 1,
          has_preview: true,
          has_review: true,
          available_assets: [
            {
              artifact_type: 'pptx',
              label: 'Presentation deck',
              path: 'artifacts/presentation_exports/candidate-review-deck.pptx',
              available: true,
            },
          ],
        },
      ],
    });

    vi.mocked(getProductArtifactEntry).mockResolvedValue({
      ok: true,
      artifact_root: 'artifacts/presentation_exports',
      artifact: {
        id: 'artifact-1',
        name: 'candidate-review-deck.pptx',
        title: 'Candidate Review Deck',
        type: 'pptx',
        workflow_label: 'Candidate Review',
        created_at: '2026-04-18T18:00:00',
        size: '128 KB',
        status: 'ready',
        export_kind: 'candidate_review_deck',
        local_pptx_path: 'artifacts/presentation_exports/candidate-review-deck.pptx',
        local_payload_path: 'artifacts/presentation_exports/candidate-review-payload.json',
        slide_count: 8,
        preview_count: 8,
        asset_count: 3,
        average_score: 8.9,
        issue_count: 0,
        warning_count: 1,
        has_preview: true,
        has_review: true,
      },
      detail: {
        notes: ['Review sidecar present'],
        assets: [
          {
            artifact_type: 'pptx',
            label: 'Presentation deck',
            path: 'artifacts/presentation_exports/candidate-review-deck.pptx',
            available: true,
          },
          {
            artifact_type: 'payload',
            label: 'Source payload',
            path: 'artifacts/presentation_exports/candidate-review-payload.json',
            available: true,
          },
        ],
        preview_slides: [
          {
            slide_number: 1,
            filename: 'slide-1.png',
            path: 'artifacts/presentation_exports/preview/slide-1.png',
            available: true,
          },
        ],
      },
    });
  });

  it('renders live artifact detail and opens registered assets', async () => {
    renderPage();

    expect((await screen.findAllByText('Candidate Review Deck')).length).toBeGreaterThan(0);
    expect(await screen.findByText('Review sidecar present')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: /presentation deck/i })[0]);

    expect(window.open).toHaveBeenCalled();
    expect(getProductArtifactEntry).toHaveBeenCalledWith('artifact-1');
  });
});
