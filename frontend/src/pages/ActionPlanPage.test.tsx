import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import ActionPlanPage from '@/pages/ActionPlanPage';
import {
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  publishProductWorkflowToTrello,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  runProductWorkflow,
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
    publishProductWorkflowToTrello: vi.fn(),
  };
});


vi.mock('@/lib/auth-session', () => ({
  useAuthSession: () => ({
    data: {
      mode: 'admin',
      is_admin: true,
      identity: {
        role: 'admin',
        can_write_global: true,
        can_publish_external: true,
        session_id: 'test-admin-session',
        id: 'test-admin-session',
        type: 'admin',
      },
      auth: {
        admin_configured: true,
      },
    },
  }),
  isAdminSession: () => true,
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <ActionPlanPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function buildWorkflowResponse(): ProductRunWorkflowResponse {
  return {
    ok: true,
    result: {
      workflow_id: 'action_plan_evidence_review',
      workflow_label: 'Action Plan / Evidence Review',
      status: 'warning',
      summary: 'Vendor access remediation: 3 actionable task(s) and 2 evidence gaps identified.',
      highlights: [
        'Collect missing privileged-access approvals.',
        'Close temporary access exception before the next committee review.',
      ],
      recommendation: 'Close the access-control evidence gaps before the next committee checkpoint.',
      structured_result: {
        success: true,
        validated_output: {},
        overall_confidence: 0.85,
        quality_score: 0.85,
      },
      grounding_preview: {
        strategy: 'document_scan',
        document_ids: ['doc-1', 'doc-2'],
        context_chars: 1024,
        source_block_count: 4,
        preview_text:
          '[Source: Access Review Evidence Log] Contractor offboarding evidence is still missing from the remediation packet.',
        warnings: [],
      },
      artifacts: [],
      deck_export_kind: 'action_plan_deck',
      deck_available: true,
      warnings: ['Awaiting governance committee confirmation.'],
      debug_metadata: {},
    },
    action_plan_view: {
      objective: 'Drive grounded follow-up actions for Vendor access remediation.',
      summary: {
        total: 3,
        open: 0,
        in_progress: 1,
        blocked: 1,
        done: 1,
        completed: 1,
        critical_path: 2,
        evidence_gaps: 2,
        documents: 2,
        artifacts: 0,
      },
      items: [
        {
          id: 'action-item-1',
          title: 'Collect missing privileged-access approvals.',
          owner: 'Identity Ops',
          due_date: '2024-03-21',
          priority: 'high',
          status: 'in_progress',
          source: 'Privileged Account Approval Email.pdf',
          evidence: 'Approval email is missing for two privileged administrators.',
          rationale: 'Approval email is missing for two privileged administrators.',
          notes: null,
          document_id: 'doc-1',
        },
        {
          id: 'action-item-2',
          title: 'Close temporary access exception before the next committee review.',
          owner: 'Security Governance',
          due_date: '2024-03-20',
          priority: 'critical',
          status: 'blocked',
          source: 'Access Review Evidence Log.pdf',
          evidence: 'Temporary exception remains open pending governance committee approval.',
          rationale: 'Temporary exception remains open pending governance committee approval.',
          notes: null,
          document_id: 'doc-2',
        },
        {
          id: 'action-item-3',
          title: 'Document completed remediation closure note in the access review record.',
          owner: 'Audit PMO',
          due_date: '2024-03-25',
          priority: 'medium',
          status: 'done',
          source: 'Remediation Closure Note - Vendor Access Review.pdf',
          evidence: 'Closure note draft is prepared and ready for filing.',
          rationale: 'Closure note draft is prepared and ready for filing.',
          notes: null,
          document_id: 'doc-2',
        },
      ],
      critical_path: [
        {
          id: 'action-item-2',
          title: 'Close temporary access exception before the next committee review.',
          owner: 'Security Governance',
          due_date: '2024-03-20',
          priority: 'critical',
          status: 'blocked',
          source: 'Access Review Evidence Log.pdf',
          evidence: 'Temporary exception remains open pending governance committee approval.',
          rationale: 'Temporary exception remains open pending governance committee approval.',
          notes: null,
          document_id: 'doc-2',
        },
        {
          id: 'action-item-1',
          title: 'Collect missing privileged-access approvals.',
          owner: 'Identity Ops',
          due_date: '2024-03-21',
          priority: 'high',
          status: 'in_progress',
          source: 'Privileged Account Approval Email.pdf',
          evidence: 'Approval email is missing for two privileged administrators.',
          rationale: 'Approval email is missing for two privileged administrators.',
          notes: null,
          document_id: 'doc-1',
        },
      ],
      evidence_gaps: [
        {
          id: 'gap-1',
          item_id: 'action-item-1',
          title: 'Collect missing privileged-access approvals.',
          detail:
            'Approval email is missing for two privileged administrators. Missing explicit owner sign-off artifact for the remaining administrators.',
          status: 'partial',
          source: 'Privileged Account Approval Email.pdf',
          notes: null,
        },
        {
          id: 'gap-2',
          item_id: null,
          title: 'Contractor offboarding evidence is missing from the remediation packet.',
          detail: 'Contractor offboarding evidence is missing from the remediation packet.',
          status: 'missing',
          source: null,
          notes: 'Workflow limitation',
        },
      ],
      artifacts: [],
      document_ids: ['doc-1', 'doc-2'],
      run_metadata: {
        workflow_id: 'action_plan_evidence_review',
        workflow_label: 'Action Plan / Evidence Review',
        status: 'warning',
        provider: 'ollama',
        model: 'qwen2.5:7b',
        context_strategy: 'document_scan',
        deck_available: true,
        deck_export_kind: 'action_plan_deck',
        warning_count: 1,
        warnings: ['Awaiting governance committee confirmation.'],
        source_block_count: 4,
        highlights: [
          'Collect missing privileged-access approvals.',
          'Close temporary access exception before the next committee review.',
        ],
        summary: 'Vendor access remediation: 3 actionable task(s) and 2 evidence gaps identified.',
        recommendation: 'Close the access-control evidence gaps before the next committee checkpoint.',
        run_state: {
          current_step: 'review',
          steps: [
            { key: 'select', label: 'Select', status: 'completed' },
            { key: 'ground', label: 'Ground', status: 'completed' },
            { key: 'analyze', label: 'Analyze', status: 'completed' },
            { key: 'review', label: 'Review', status: 'completed' },
            { key: 'export', label: 'Export', status: 'pending' },
          ],
        },
      },
    },
  };
}

describe('ActionPlanPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('open', vi.fn());

    vi.mocked(getProductDocumentLibrary).mockResolvedValue({
      ok: true,
      summary: {
        total_documents: 2,
        indexed_documents: 2,
        warning_documents: 0,
        error_documents: 0,
        pending_documents: 0,
        indexing_documents: 0,
        total_chunks: 10,
        total_chars: 5400,
      },
      documents: [
        {
          document_id: 'doc-1',
          name: 'Privileged Account Approval Email.pdf',
          file_type: 'pdf',
          char_count: 2200,
          chunk_count: 4,
          indexed_at: '2026-04-16T18:00:00',
          loader_strategy_label: 'Manual',
          status: 'indexed',
          warnings: [],
        },
        {
          document_id: 'doc-2',
          name: 'Access Review Evidence Log.pdf',
          file_type: 'pdf',
          char_count: 3200,
          chunk_count: 6,
          indexed_at: '2026-04-16T18:05:00',
          loader_strategy_label: 'Manual',
          status: 'indexed',
          warnings: [],
        },
      ],
    });

    vi.mocked(getProductGroundingPreview).mockResolvedValue({
      ok: true,
      preview: {
        strategy: 'document_scan',
        document_ids: ['doc-1', 'doc-2'],
        context_chars: 512,
        source_block_count: 2,
        preview_text: '[Source: Approval Email] Missing privileged-access approval evidence remains open.',
        warnings: [],
      },
    });

    vi.mocked(runProductWorkflow).mockResolvedValue(buildWorkflowResponse());

    vi.mocked(generateProductWorkflowDeck).mockResolvedValue({
      ok: true,
      export_result: {
        status: 'completed',
        export_kind: 'action_plan_deck',
      },
      artifacts: [
        {
          artifact_type: 'pptx',
          label: 'Presentation deck (.pptx)',
          path: '/tmp/action-plan-deck.pptx',
          download_name: 'action-plan-deck.pptx',
          available: true,
        },
      ],
    });

    vi.mocked(publishProductWorkflowToTrello).mockResolvedValue({
      ok: true,
      status: 'success',
      dry_run: false,
      workflow_id: 'action_plan_evidence_review',
      workflow_label: 'Action Plan / Evidence Review',
      message: 'Published 5 card(s) to Trello — Open: 2, Approved: 2, Done: 1',
      target_board_id: 'board-1',
      created_card_count: 5,
      list_breakdown: [
        { list_id: 'open-list', list_label: 'Open', count: 2 },
        { list_id: 'approved-list', list_label: 'Approved', count: 2 },
        { list_id: 'done-list', list_label: 'Done', count: 1 },
      ],
      created_cards: [],
      created_card_urls: [],
    });
  });

  it('shows the no-documents state when the library is empty', async () => {
    vi.mocked(getProductDocumentLibrary).mockResolvedValueOnce({
      ok: true,
      summary: {
        total_documents: 0,
        indexed_documents: 0,
        warning_documents: 0,
        error_documents: 0,
        pending_documents: 0,
        indexing_documents: 0,
        total_chunks: 0,
        total_chars: 0,
      },
      documents: [],
    });

    renderPage();

    expect(await screen.findByText(/No indexed documents available/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Action Plan/i })).toBeDisabled();
  });

  it('runs the workflow, renders live tabs, generates deck artifacts and opens an artifact', async () => {
    renderPage();

    expect(await screen.findByText('Privileged Account Approval Email.pdf')).toBeInTheDocument();
    expect(await screen.findByText('Access Review Evidence Log.pdf')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Show grounding preview/i }));
    await waitFor(() => {
      expect(
        screen.getAllByText(/Missing privileged-access approval evidence remains open/i).length,
      ).toBeGreaterThan(0);
    });
    expect(screen.queryByText(/Advanced preview and raw context/i)).not.toBeInTheDocument();

    expect(screen.getByText(/2 documents selected - Privileged Account Approval Email\.pdf \+ Access Review Evidence Log\.pdf/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Run Action Plan/i }));

    await waitFor(() => expect(runProductWorkflow).toHaveBeenCalledTimes(1));
    expect(runProductWorkflow).toHaveBeenCalledWith(
      expect.objectContaining({
        workflow_id: 'action_plan_evidence_review',
        context_strategy: 'document_scan',
        context_window_mode: 'auto',
        use_document_context: true,
        document_ids: expect.any(Array),
      }),
    );

    expect(
      await screen.findByText(/Vendor access remediation: 3 actionable task\(s\) and 2 evidence gaps identified/i),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(/Close temporary access exception before the next committee review/i)
        .length,
    ).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('tab', { name: /Table/i }));
    expect(screen.getAllByText(/Collect missing privileged-access approvals/i).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('tab', { name: /Timeline/i }));
    expect(screen.getAllByText(/Due:/i).length).toBeGreaterThan(0);

    expect(screen.getAllByRole('tab', { name: /Evidence Gaps/i }).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: /Generate Deck/i }));
    await waitFor(() => expect(generateProductWorkflowDeck).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/action-plan-deck\.pptx/i)).toBeInTheDocument();

    const expectedUrl = `${PRODUCT_API_BASE_URL}/api/product/artifact?${new URLSearchParams({
      path: '/tmp/action-plan-deck.pptx',
    }).toString()}`;
    fireEvent.click(screen.getByRole('button', { name: /^Open$/i }));
    expect(window.open).toHaveBeenCalledWith(expectedUrl, '_blank', 'noopener,noreferrer');
    vi.mocked(window.open).mockClear();

    fireEvent.click(screen.getByRole('button', { name: /Preview Trello/i }));
    await waitFor(() => expect(publishProductWorkflowToTrello).toHaveBeenCalledTimes(1));
    expect(publishProductWorkflowToTrello).toHaveBeenLastCalledWith(
      expect.any(Object),
      expect.objectContaining({ dryRun: true }),
    );

    fireEvent.click(await screen.findByRole('button', { name: /Publish to Trello|Publish selected card/i }));
    await waitFor(() => expect(publishProductWorkflowToTrello).toHaveBeenCalledTimes(2));
    expect(publishProductWorkflowToTrello).toHaveBeenLastCalledWith(
      expect.any(Object),
      expect.objectContaining({ dryRun: false }),
    );
    expect(await screen.findByText(/Published by list/i)).toBeInTheDocument();
    expect(screen.getAllByText(/^Open$/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/^Approved$/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/^Done$/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Open → Open, In Progress → Approved, Blocked\/Needs review → Review, Done → Done/i)).toBeInTheDocument();

  });
});
