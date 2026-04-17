import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DocumentReviewPage from "@/pages/DocumentReviewPage";
import {
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  runProductWorkflow,
  type ProductRunWorkflowResponse,
} from "@/lib/product-api";

vi.mock("@/components/ui/sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/lib/product-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/product-api")>("@/lib/product-api");
  return {
    ...actual,
    getProductDocumentLibrary: vi.fn(),
    getProductGroundingPreview: vi.fn(),
    runProductWorkflow: vi.fn(),
    generateProductWorkflowDeck: vi.fn(),
  };
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <DocumentReviewPage />
    </QueryClientProvider>,
  );
}

function buildWorkflowResponse(): ProductRunWorkflowResponse {
  return {
    ok: true,
    result: {
      workflow_id: "document_review",
      workflow_label: "Document Review",
      status: "warning",
      summary: "The document review highlights grounded risks around Artemis III readiness and ISS transition planning.",
      highlights: ["Artemis III risk posture remains elevated"],
      recommendation: "Reassess readiness gates before approval.",
      structured_result: {
        success: true,
        validated_output: {},
        overall_confidence: 0.84,
        quality_score: 0.84,
      },
      grounding_preview: {
        strategy: "retrieval",
        document_ids: ["doc-1"],
        context_chars: 512,
        source_block_count: 3,
        preview_text: "[Source: ASAP report] Artemis III remains a major safety concern.",
        warnings: [],
      },
      artifacts: [],
      deck_export_kind: "document_review_deck",
      deck_available: true,
      warnings: ["The mitigation roadmap is incomplete."],
      debug_metadata: {},
    },
    result_view: {
      decision_summary: {
        label: "Renegotiate",
        status: "Requires Legal Review",
        summary: "Multiple high-signal findings remain open before approval.",
        severity_counts: {
          critical: 1,
          high: 2,
          medium: 0,
          low: 0,
        },
        next_owner: "NASA leadership",
        due_date: "2030-01-01",
      },
      document_metrics: {
        strategy: "retrieval",
        document_ids: ["doc-1"],
        context_chars: 512,
        source_block_count: 3,
      },
      watchouts: ["ISS transition still requires explicit milestone governance."],
      next_steps: ["Reassess Artemis III readiness gates before downstream commitments."],
      top_blockers: [
        {
          title: "Artemis III readiness still carries elevated safety risk",
          severity: "critical",
          recommendation: "Reassess Artemis III readiness gates before committing to downstream milestones.",
        },
      ],
      business_impact: [
        {
          label: "Mission risk",
          detail: "Mission readiness decisions still have material safety and governance exposure.",
        },
      ],
      findings: [
        {
          id: "finding-1",
          severity: "critical",
          category: "Program Risk",
          title: "Artemis III readiness still carries elevated safety risk",
          description: "The report states that Artemis III and follow-on missions still present a major safety concern.",
          source: "ASAP report",
          chunkId: "chunk_1",
          confidence: 0.87,
          recommendation: "Reassess Artemis III readiness gates before committing to downstream milestones.",
          snippet: "has repeatedly raised concern regarding Artemis III and subsequent Artemis mission risk postures",
        },
      ],
      evidence_trail: [
        {
          id: "finding-1",
          severity: "critical",
          title: "Artemis III readiness still carries elevated safety risk",
          chunkId: "chunk_1",
          source: "ASAP report",
          snippet: "has repeatedly raised concern regarding Artemis III and subsequent Artemis mission risk postures",
        },
      ],
      artifacts: [],
      sources: [["ASAP report", "1", "0.91", "Artemis III remains a major safety concern."]],
      run_state: {
        current_step: "review",
        steps: [
          { key: "select", label: "Select", status: "completed" },
          { key: "ground", label: "Ground", status: "completed" },
          { key: "analyze", label: "Analyze", status: "completed" },
          { key: "review", label: "Review", status: "completed" },
          { key: "export", label: "Export", status: "pending" },
        ],
      },
    },
  };
}

describe("DocumentReviewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("open", vi.fn());

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
        total_chars: 1200,
      },
      documents: [
        {
          document_id: "doc-1",
          name: "ASAP Annual Report 2025",
          file_type: "pdf",
          char_count: 1200,
          chunk_count: 4,
          indexed_at: "2026-04-15T20:00:00",
          loader_strategy_label: "Manual",
          status: "indexed",
          warnings: [],
        },
      ],
    });

    vi.mocked(getProductGroundingPreview).mockResolvedValue({
      ok: true,
      preview: {
        strategy: "retrieval",
        document_ids: ["doc-1"],
        context_chars: 512,
        source_block_count: 3,
        preview_text: "[Source: ASAP report] Artemis III remains a major safety concern.",
        warnings: [],
      },
    });

    vi.mocked(runProductWorkflow).mockResolvedValue(buildWorkflowResponse());

    vi.mocked(generateProductWorkflowDeck).mockResolvedValue({
      ok: true,
      export_result: {
        status: "completed",
        export_kind: "document_review_deck",
      },
      artifacts: [
        {
          artifact_type: "pptx",
          label: "Presentation deck (.pptx)",
          path: "/tmp/document-review-deck.pptx",
          download_name: "document-review-deck.pptx",
          available: true,
        },
      ],
    });
  });

  it("runs the review, renders grounded findings/evidence and generates deck artifacts", async () => {
    renderPage();

    expect(await screen.findByText("ASAP Annual Report 2025")).toBeInTheDocument();
    expect(await screen.findByText(/Artemis III remains a major safety concern/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Run Review/i }));

    await waitFor(() => expect(runProductWorkflow).toHaveBeenCalledTimes(1));

    expect(await screen.findByText(/Decision: Renegotiate/i)).toBeInTheDocument();
    expect(screen.getByText(/Requires Legal Review/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Artemis III readiness still carries elevated safety risk/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Mission risk:/i)).toBeInTheDocument();

    const evidenceTab = screen.getByRole("tab", { name: /Evidence/i });
    expect(evidenceTab).toBeInTheDocument();
    fireEvent.click(evidenceTab);
    expect(await screen.findByText(/has repeatedly raised concern regarding Artemis III/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Generate Deck/i }));
    await waitFor(() => expect(generateProductWorkflowDeck).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("tab", { name: /Artifacts/i }));
    expect(await screen.findByText(/document-review-deck\.pptx/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Open/i }));
    expect(window.open).toHaveBeenCalledWith(`${PRODUCT_API_BASE_URL}/api/product/artifact?path=%2Ftmp%2Fdocument-review-deck.pptx`, "_blank", "noopener,noreferrer");
  });
});