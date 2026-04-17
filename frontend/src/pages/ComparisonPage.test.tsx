import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ComparisonPage from "@/pages/ComparisonPage";
import {
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
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
      <ComparisonPage />
    </QueryClientProvider>,
  );
}

function buildWorkflowResponse(): ProductRunWorkflowResponse {
  return {
    ok: true,
    result: {
      workflow_id: "policy_contract_comparison",
      workflow_label: "Policy / Contract Comparison",
      status: "warning",
      summary: "The comparison highlights material legal and operational deltas that still require final policy review.",
      highlights: ["Formal approval became mandatory in the revised policy."],
      recommendation: "Use the revised policy as the baseline and validate the remaining legal deltas before sign-off.",
      structured_result: {
        success: true,
        validated_output: {},
        overall_confidence: 0.82,
        quality_score: 0.82,
      },
      grounding_preview: {
        strategy: "retrieval",
        document_ids: ["doc-a", "doc-b"],
        context_chars: 840,
        source_block_count: 4,
        preview_text: "[Source: Policy A] formal approval is optional. [Source: Policy B] formal approval is required.",
        warnings: [],
      },
      artifacts: [],
      deck_export_kind: "policy_contract_comparison_deck",
      deck_available: true,
      warnings: ["A final legal review is still required before approval."],
      debug_metadata: {},
    },
    comparison_view: {
      compared_documents: ["Policy A.pdf", "Policy B.pdf"],
      executive_summary: {
        narrative: "Policy B introduces stricter approval, liability and governance controls than Policy A.",
        counts: {
          breaking: 1,
          significant: 2,
          minor: 0,
        },
        status: "Requires Review",
        documents: ["Policy A.pdf", "Policy B.pdf"],
      },
      must_fix_items: [
        {
          title: "Formal approval became mandatory",
          detail: "Document B requires formal approval before onboarding while Document A does not.",
          impact: "breaking",
          recommendation: "Adopt the new approval control only after legal validation of scope and exceptions.",
        },
      ],
      negotiation_priorities: [
        "Adopt the new approval control only after legal validation of scope and exceptions.",
        "Validate the liability and indemnification deltas before signature.",
      ],
      differences: [
        {
          id: "comparison-diff-1",
          clause: "Formal approval became mandatory",
          impact: "breaking",
          category: "Obligation change",
          doc_a_label: "Policy A.pdf",
          doc_a_text: "Policy A allows onboarding to proceed with manager acknowledgment only.",
          doc_b_label: "Policy B.pdf",
          doc_b_text: "Policy B requires formal approval before onboarding may proceed.",
          business_impact: "The new approval gate materially changes operational readiness and legal accountability.",
          recommendation: "Adopt the new approval control only after legal validation of scope and exceptions.",
          evidence: ["Policy A: manager acknowledgment is sufficient.", "Policy B: formal approval is required before onboarding."],
        },
      ],
      recommendation: {
        summary: "Use Policy B as the baseline and validate the remaining legal deltas before sign-off.",
        handoff: "Legal / policy review",
        artifact_label: "Policy / Contract Comparison deck available for generation",
      },
      artifacts: [],
      watchouts: ["A final legal review is still required before approval."],
      next_steps: ["Validate the liability and indemnification deltas before signature."],
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

describe("ComparisonPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("open", vi.fn());

    vi.mocked(getProductDocumentLibrary).mockResolvedValue({
      ok: true,
      summary: {
        total_documents: 2,
        indexed_documents: 2,
        warning_documents: 0,
        error_documents: 0,
        pending_documents: 0,
        indexing_documents: 0,
        total_chunks: 12,
        total_chars: 5400,
      },
      documents: [
        {
          document_id: "doc-a",
          name: "Policy A.pdf",
          file_type: "pdf",
          char_count: 2600,
          chunk_count: 6,
          indexed_at: "2026-04-16T09:00:00",
          loader_strategy_label: "Manual",
          status: "indexed",
          warnings: [],
        },
        {
          document_id: "doc-b",
          name: "Policy B.pdf",
          file_type: "pdf",
          char_count: 2800,
          chunk_count: 6,
          indexed_at: "2026-04-16T09:01:00",
          loader_strategy_label: "Manual",
          status: "indexed",
          warnings: [],
        },
      ],
    });

    vi.mocked(runProductWorkflow).mockResolvedValue(buildWorkflowResponse());

    vi.mocked(generateProductWorkflowDeck).mockResolvedValue({
      ok: true,
      export_result: {
        status: "completed",
        export_kind: "policy_contract_comparison_deck",
      },
      artifacts: [
        {
          artifact_type: "pptx",
          label: "Presentation deck (.pptx)",
          path: "/tmp/policy-comparison-deck.pptx",
          download_name: "policy-comparison-deck.pptx",
          available: true,
        },
      ],
    });
  });

  it("runs the comparison, renders grounded deltas and generates deck artifacts", async () => {
    renderPage();

    expect(await screen.findByText("Policy A.pdf")).toBeInTheDocument();
    expect(await screen.findByText("Policy B.pdf")).toBeInTheDocument();

    const runButton = screen.getByRole("button", { name: /Run Comparison/i });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);
    await waitFor(() => expect(runProductWorkflow).toHaveBeenCalledTimes(1));

    expect(await screen.findByText(/Policy B introduces stricter approval/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Formal approval became mandatory/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Validate the liability and indemnification deltas before signature/i)).toBeInTheDocument();
    expect(screen.getByText(/The new approval gate materially changes operational readiness/i)).toBeInTheDocument();

    const generateButton = screen.getByRole("button", { name: /Generate Deck/i });
    await waitFor(() => expect(generateButton).toBeEnabled());
    fireEvent.click(generateButton);
    await waitFor(() => expect(generateProductWorkflowDeck).toHaveBeenCalledTimes(1));

    expect((await screen.findAllByText(/policy-comparison-deck\.pptx/i)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: /Open/i }));
    expect(window.open).toHaveBeenCalledWith(`${PRODUCT_API_BASE_URL}/api/product/artifact?path=%2Ftmp%2Fpolicy-comparison-deck.pptx`, "_blank", "noopener,noreferrer");
  });

  it("surfaces a warning status when deck generation returns no downloadable artifact", async () => {
    vi.mocked(generateProductWorkflowDeck).mockResolvedValueOnce({
      ok: true,
      export_result: {
        status: "disabled",
      },
      artifacts: [],
    });

    renderPage();

    expect(await screen.findByText("Policy A.pdf")).toBeInTheDocument();
    expect(await screen.findByText("Policy B.pdf")).toBeInTheDocument();

    const runButton = await screen.findByRole("button", { name: /Run Comparison/i });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);
    await waitFor(() => expect(runProductWorkflow).toHaveBeenCalledTimes(1));

    const generateButton = screen.getByRole("button", { name: /Generate Deck/i });
    await waitFor(() => expect(generateButton).toBeEnabled());
    fireEvent.click(generateButton);
    await waitFor(() => expect(generateProductWorkflowDeck).toHaveBeenCalledTimes(1));

    expect(await screen.findByText(/Deck export status/i)).toBeInTheDocument();
    expect(screen.getByText(/currently disabled in the Product API configuration/i)).toBeInTheDocument();
  });
});