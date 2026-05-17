import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, ChevronDown, Clock, FileText, Info, Loader2, Play, Sparkles, User } from 'lucide-react';
import { PublicExecutionQuotaError, formatPublicExecutionQuotaMessage } from '@/lib/public-demo-limits';

import { PageHeader, StatusPill, SeverityBadge, GlassCard, WorkflowProgressHeader } from '@/components/shared/ui-components';
import { WorkflowPublishActions } from '@/components/product/WorkflowPublishActions';
import {
  buildProductArtifactUrl,
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  getProductRunHistoryEntry,
  runProductWorkflow,
  ProductWorkflowTimeoutRecoveryError,
  type ProductDocumentLibraryEntry,
  type ProductDocumentReviewFinding,
  type ProductDocumentReviewView,
  type ProductPublishNotionResponse,
  type ProductPublishTrelloResponse,
  type ProductRunWorkflowResponse,
  type ProductWorkflowArtifact,
} from '@/lib/product-api';
import { toast } from '@/components/ui/sonner';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { useAppStore } from '@/lib/store';
import { findRecommendedDocuments, WORKFLOW_RECOMMENDED_DOCUMENTS } from '@/lib/workflow-demo-documents';

import { formatUserDate } from '@/lib/user-time';
import { aiLabQueryKeys } from '@/lib/ai-lab-data';
import { refreshWorkflowTimeoutRecoveryQueries } from '@/lib/workflow-timeout-recovery';
const workflowSteps = [
  { key: 'select', label: 'Select' },
  { key: 'ground', label: 'Ground' },
  { key: 'analyze', label: 'Analyze' },
  { key: 'review', label: 'Review' },
  { key: 'export', label: 'Export' },
];

function formatDate(value?: string | number | null): string {
  return formatUserDate(value);
}

function buildSeverityNarrative(counts: Record<'critical' | 'high' | 'medium' | 'low', number>, fallback: string): string {
  const critical = counts.critical || 0;
  const high = counts.high || 0;
  if (critical > 0 || high > 0) {
    return `${critical} critical and ${high} high-severity findings require attention before approval.`;
  }
  return fallback;
}

function getDecisionBadgeClass(status: string | undefined): string {
  const normalized = String(status || '').toLowerCase();
  if (normalized.includes('legal') || normalized.includes('review')) {
    return 'bg-glow-warning/10 text-glow-warning border-glow-warning/20';
  }
  if (normalized.includes('ready') || normalized.includes('approved') || normalized.includes('no material blockers')) {
    return 'bg-glow-success/10 text-glow-success border-glow-success/20';
  }
  return 'bg-primary/10 text-primary border-primary/20';
}

function dedupeArtifacts(artifacts: ProductWorkflowArtifact[]): ProductWorkflowArtifact[] {
  const seen = new Set<string>();
  const normalized: ProductWorkflowArtifact[] = [];
  for (const artifact of artifacts) {
    const key = `${artifact.artifact_type}:${artifact.path || artifact.download_name || artifact.label}`;
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push(artifact);
  }
  return normalized;
}

function normalizeSeverity(value: string | undefined): ProductDocumentReviewFinding['severity'] {
  if (value === 'critical' || value === 'high' || value === 'medium' || value === 'low') {
    return value;
  }
  return 'medium';
}

function getDefaultDecisionSummary(view?: ProductDocumentReviewView | null) {
  return view?.decision_summary ?? {
    label: 'Run Review',
    status: 'Awaiting analysis',
    summary: 'Select a grounded document and run the workflow to generate the decision summary, blockers and evidence trail.',
    severity_counts: { critical: 0, high: 0, medium: 0, low: 0 },
    next_owner: null,
    due_date: null,
  };
}

export default function DocumentReviewPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const historyRunId = searchParams.get('historyRunId') || searchParams.get('runId') || '';
  const operatorPreferences = useAppStore((state) => state.operatorPreferences);
  const defaultTab = operatorPreferences.defaultEvidencePanelOpen ? 'evidence' : 'findings';
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [activeTab, setActiveTab] = useState<'findings' | 'evidence' | 'artifacts'>(defaultTab);
  const [workflowResponse, setWorkflowResponse] = useState<ProductRunWorkflowResponse | null>(null);
  const [generatedArtifacts, setGeneratedArtifacts] = useState<ProductWorkflowArtifact[]>([]);
  const [showGroundingPanel, setShowGroundingPanel] = useState(false);
  const [trelloPublishResult, setTrelloPublishResult] = useState<ProductPublishTrelloResponse | null>(null);
  const [notionPublishResult, setNotionPublishResult] = useState<ProductPublishNotionResponse | null>(null);

  const { data: documentLibrary, isLoading: documentsLoading, isError: documentsError } = useQuery({
    queryKey: ['product-document-library'],
    queryFn: getProductDocumentLibrary,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const historyDetailQuery = useQuery({
    queryKey: ['product-run-history-entry', historyRunId, 'workflow-hydration'],
    queryFn: () => getProductRunHistoryEntry(historyRunId),
    enabled: Boolean(historyRunId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const availableDocuments = useMemo(
    () => (documentLibrary?.documents ?? []).filter((document) => document.status === 'indexed' || document.status === 'warning'),
    [documentLibrary],
  );

  const recommendedDocument = useMemo(
    () => findRecommendedDocuments(availableDocuments, WORKFLOW_RECOMMENDED_DOCUMENTS.documentReview)[0],
    [availableDocuments],
  );

  useEffect(() => {
    if (!availableDocuments.length) {
      if (!historyRunId) setSelectedDocumentId('');
      return;
    }
    if (!selectedDocumentId || !availableDocuments.some((document) => document.document_id === selectedDocumentId)) {
      setSelectedDocumentId(recommendedDocument?.document_id ?? availableDocuments[0]?.document_id ?? '');
    }
  }, [availableDocuments, historyRunId, recommendedDocument, selectedDocumentId]);

  const selectedDocument = useMemo<ProductDocumentLibraryEntry | undefined>(
    () => availableDocuments.find((document) => document.document_id === selectedDocumentId),
    [availableDocuments, selectedDocumentId],
  );

  const previewQuery = useQuery({
    queryKey: ['product-document-review-preview', selectedDocumentId],
    enabled: Boolean(selectedDocumentId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryFn: () =>
      getProductGroundingPreview({
        workflowId: 'document_review',
        strategy: 'retrieval',
        documentIds: selectedDocumentId ? [selectedDocumentId] : [],
      }),
  });

  useEffect(() => {
    const run = historyDetailQuery.data?.run;
    if (!historyRunId || !run) return;

    const fallbackWorkflowResponse: ProductRunWorkflowResponse | null = run.response_payload && typeof run.response_payload === 'object'
      ? {
          ok: true,
          run_id: run.id,
          result: run.response_payload as ProductRunWorkflowResponse['result'],
          result_sections: run.result_sections as ProductRunWorkflowResponse['result_sections'],
          source_run: run,
        }
      : null;
    const hydratedWorkflowResponse = historyDetailQuery.data?.workflow_response ?? fallbackWorkflowResponse;

    if (!hydratedWorkflowResponse?.result || hydratedWorkflowResponse.result.workflow_id !== 'document_review') return;

    const requestPayload = run.request_payload && typeof run.request_payload === 'object' ? run.request_payload : null;
    const requestDocumentIds = Array.isArray(requestPayload?.document_ids)
      ? requestPayload.document_ids.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const historyDocumentId = (run.document_ids ?? [])[0] || requestDocumentIds[0] || hydratedWorkflowResponse.result.grounding_preview?.document_ids?.[0] || '';

    if (historyDocumentId) setSelectedDocumentId(historyDocumentId);
    setWorkflowResponse({ ...hydratedWorkflowResponse, source_run: hydratedWorkflowResponse.source_run ?? run });
    setGeneratedArtifacts(run.artifact_items ?? hydratedWorkflowResponse.result.artifacts ?? []);
    setTrelloPublishResult(null);
    setNotionPublishResult(null);
    setActiveTab('findings');
  }, [historyDetailQuery.data, historyRunId]);

  const runReviewMutation = useMutation({
    mutationFn: () =>
      runProductWorkflow({
        workflow_id: 'document_review',
        document_ids: selectedDocumentId ? [selectedDocumentId] : [],
        context_strategy: 'retrieval',
        use_document_context: true,
      }),
    onSuccess: async (payload) => {
      setWorkflowResponse(payload);
      setGeneratedArtifacts([]);
      setTrelloPublishResult(null);
      setNotionPublishResult(null);
      setActiveTab('findings');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.evals }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.overview }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.runtime }),
      ]);
      toast.success('Document review completed with grounded output.');
    },
    onError: async (error) => {
      if (error instanceof ProductWorkflowTimeoutRecoveryError) {
        await refreshWorkflowTimeoutRecoveryQueries(queryClient);
        toast.error('Document review is still taking longer than expected. Check Run History in a moment; the backend may still finish the run.');
        return;
      }
      toast.error(error instanceof PublicExecutionQuotaError ? formatPublicExecutionQuotaMessage(error) : error instanceof Error ? error.message : 'Document review failed.');
    },
  });

  const generateDeckMutation = useMutation({
    mutationFn: () => {
      if (!workflowResponse?.result) {
        throw new Error('Run a grounded review before generating the executive deck.');
      }
      return generateProductWorkflowDeck(workflowResponse.result, { runId: workflowResponse.run_id });
    },
    onSuccess: async (payload) => {
      setGeneratedArtifacts(payload.artifacts);
      setActiveTab('artifacts');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-artifacts'] }),
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.evals }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.overview }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.runtime }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      toast.success('Executive deck artifacts generated successfully.');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Deck generation failed.');
    },
  });

  const reviewView = workflowResponse?.result_view ?? null;
  const decisionSummary = getDefaultDecisionSummary(reviewView);
  const counts = decisionSummary.severity_counts;
  const findings: ProductDocumentReviewFinding[] = reviewView?.findings ?? [];
  const evidenceTrail = reviewView?.evidence_trail ?? [];
  const topBlockers = reviewView?.top_blockers ?? [];
  const businessImpact = reviewView?.business_impact ?? [];
  const allArtifacts = useMemo(
    () => dedupeArtifacts([...(reviewView?.artifacts ?? []), ...generatedArtifacts]),
    [generatedArtifacts, reviewView],
  );
  const groundingPreview = workflowResponse?.result?.grounding_preview ?? previewQuery.data?.preview ?? null;

  const stepStatuses = useMemo(() => {
    const runStateMap = new Map((reviewView?.run_state.steps ?? []).map((step) => [step.key, step.status]));
    return workflowSteps.map((step) => {
      let status = runStateMap.get(step.key) || 'pending';
      if (!runStateMap.size) {
        if (step.key === 'select' && selectedDocumentId) status = 'completed';
        if (step.key === 'ground' && groundingPreview) status = 'completed';
        if (step.key === 'analyze' && runReviewMutation.isPending) status = 'running';
        if (step.key === 'analyze' && workflowResponse?.result) status = workflowResponse.result.status === 'error' ? 'error' : 'completed';
        if (step.key === 'review' && findings.length > 0) status = 'completed';
        if (step.key === 'export' && allArtifacts.length > 0) status = 'completed';
      }
      if (step.key === 'export' && generateDeckMutation.isPending) status = 'running';
      if (step.key === 'export' && allArtifacts.length > 0) status = 'completed';
      return { ...step, status };
    });
  }, [allArtifacts.length, findings.length, generateDeckMutation.isPending, groundingPreview, reviewView, runReviewMutation.isPending, selectedDocumentId, workflowResponse]);

  const currentStrategy = reviewView?.document_metrics.strategy || groundingPreview?.strategy || 'document_scan';
  const severityNarrative = buildSeverityNarrative(counts, decisionSummary.summary);

  const handleDocumentChange = (documentId: string) => {
    setSelectedDocumentId(documentId);
    setWorkflowResponse(null);
    setGeneratedArtifacts([]);
    setTrelloPublishResult(null);
    setNotionPublishResult(null);
    setActiveTab(defaultTab);
  };

  const handleOpenArtifact = (artifact: ProductWorkflowArtifact) => {
    if (!artifact.path) {
      toast.error(`${artifact.label} is registered, but no local path is available yet.`);
      return;
    }
    window.open(buildProductArtifactUrl(artifact.path), '_blank', 'noopener,noreferrer');
  };

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="document-review-header">
        <PageHeader title="Document Review" description="Review a document for risks, gaps and grounded findings.">
          <Button
            className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"
            disabled={!selectedDocumentId || runReviewMutation.isPending}
            onClick={() => runReviewMutation.mutate()}
          >
            {runReviewMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-2" />}
            {runReviewMutation.isPending ? 'Running Review' : 'Run Review'}
          </Button>
          <Button
            variant="outline"
            className="h-9 px-4 text-xs border-border/50"
            disabled={!workflowResponse?.result?.deck_available || generateDeckMutation.isPending}
            onClick={() => generateDeckMutation.mutate()}
          >
            {generateDeckMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />}
            {generateDeckMutation.isPending ? 'Generating Deck' : 'Generate Deck'}
          </Button>
        </PageHeader>
      </div>
      <div data-tour="document-review-progress">
        <WorkflowProgressHeader
          steps={stepStatuses}
          title="Workflow progress"
          description="Track how the live run moves from document selection to export-ready review outputs."
        />
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} data-tour="document-review-decision" className="glass rounded-xl p-4 mb-6 border-glow-warning/30">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-glow-warning/10 flex items-center justify-center">
              <AlertTriangle className="w-4.5 h-4.5 text-glow-warning" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-foreground">Decision: {decisionSummary.label}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${getDecisionBadgeClass(decisionSummary.status)}`}>
                  {decisionSummary.status}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5">{severityNarrative}</p>
              {workflowResponse?.result?.summary && <p className="text-[11px] text-muted-foreground mt-1">{workflowResponse.result.summary}</p>}
            </div>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground flex-wrap">
            <User className="w-3 h-3" /> Next: {decisionSummary.next_owner || 'n/a'}
            <span className="mx-1">·</span>
            <Clock className="w-3 h-3" /> Due: {formatDate(decisionSummary.due_date)}
          </div>
        </div>
      </motion.div>


      {documentsError && (
        <div className="glass rounded-xl p-4 mb-6 border border-glow-warning/20 text-xs text-glow-warning flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Product API unavailable. The document library cannot be loaded right now.
        </div>
      )}

      <div className="grid lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 space-y-4">
          <GlassCard delay={0.15} data-tour="document-review-selection">
            <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Document Selection</h3>
            <Select value={selectedDocumentId} onValueChange={handleDocumentChange}>
              <SelectTrigger className="h-8 text-xs bg-secondary/30"><SelectValue placeholder={documentsLoading ? 'Loading documents...' : 'Select a document'} /></SelectTrigger>
              <SelectContent>
                {availableDocuments.map((document) => (
                  <SelectItem key={document.document_id} value={document.document_id} className="text-xs">
                    {document.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Collapsible open={showGroundingPanel} onOpenChange={setShowGroundingPanel} className="mt-3">
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex w-full items-center justify-between rounded-xl border border-border/40 bg-secondary/20 px-3 py-3 text-left transition-colors hover:border-primary/30 hover:bg-secondary/30"
                  aria-label={showGroundingPanel ? 'Hide grounding panel' : 'Show grounding panel'}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Grounding</span>
                      <span className={`rounded-full border px-1.5 py-0.5 text-[9px] font-medium ${(groundingPreview?.warnings?.length ?? 0) > 0 ? 'border-glow-warning/30 text-glow-warning' : 'border-glow-success/30 text-glow-success'}`}>
                        {previewQuery.isLoading ? 'Loading' : (groundingPreview?.warnings?.length ?? 0) > 0 ? 'Caveats' : 'Ready'}
                      </span>
                    </div>
                    <div className="mt-1 text-[11px] text-foreground">Context metadata and preview for the selected document</div>
                  </div>
                  <ChevronDown className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${showGroundingPanel ? 'rotate-180' : ''}`} />
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down">
                <div className="mt-2 space-y-3 rounded-xl border border-border/30 bg-secondary/15 p-3">
                  <div>
                    <h3 className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">Grounding Details</h3>
                    <div className="rounded-lg border border-border/30 bg-secondary/20 p-3">
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-[10px] text-muted-foreground"><span>Chunks</span><span>{selectedDocument?.chunk_count?.toLocaleString() ?? '—'}</span></div>
                        <div className="flex justify-between text-[10px] text-muted-foreground"><span>Characters</span><span>{selectedDocument?.char_count ? selectedDocument.char_count.toLocaleString() : '—'}</span></div>
                        <div className="flex justify-between text-[10px] text-muted-foreground"><span>Strategy</span><span className="font-mono">{currentStrategy}</span></div>
                      </div>
                    </div>
                  </div>
                  <div>
                    <h3 className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2">Grounding Preview</h3>
                    <div className="rounded-lg border border-border/30 bg-secondary/20 p-3">
                      <div className="flex items-center gap-2 mb-2">
                        {previewQuery.isLoading ? <Loader2 className="w-3.5 h-3.5 text-primary animate-spin" /> : <div className={`w-1.5 h-1.5 rounded-full ${(groundingPreview?.warnings?.length ?? 0) > 0 ? 'bg-glow-warning' : 'bg-glow-success'}`} />}
                        <span className={`text-[10px] font-medium ${(groundingPreview?.warnings?.length ?? 0) > 0 ? 'text-glow-warning' : 'text-glow-success'}`}>
                          {previewQuery.isLoading ? 'Loading context...' : (groundingPreview?.warnings?.length ?? 0) > 0 ? 'Context loaded with caveats' : 'Context loaded'}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {groundingPreview?.preview_text || 'Select an indexed document to preview the grounded context before running the workflow.'}
                      </p>
                    </div>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </GlassCard>


          <div data-tour="document-review-supporting-cards" className="space-y-4">
            <GlassCard delay={0.25}>
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Top Blockers Before Signature</h3>
            <div className="space-y-2">
              {topBlockers.length > 0 ? topBlockers.map((blocker, index) => (
                <div key={`${blocker.title}-${index}`} className="flex items-start gap-2 text-xs">
                  <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${blocker.severity === 'critical' ? 'bg-glow-error' : 'bg-glow-warning'}`} />
                  <div className="min-w-0">
                    <p className="text-foreground font-medium leading-relaxed">{blocker.title}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{blocker.recommendation}</p>
                  </div>
                </div>
              )) : <p className="text-xs text-muted-foreground leading-relaxed">Run the review to identify grounded blockers before signature.</p>}
            </div>
            </GlassCard>

            <GlassCard delay={0.3}>
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Business Impact Summary</h3>
            <div className="space-y-2 text-xs text-muted-foreground leading-relaxed">
              {businessImpact.length > 0 ? businessImpact.map((item) => (
                <p key={item.label}><span className="text-foreground font-medium">{item.label}:</span> {item.detail}</p>
              )) : <p>Run the review to derive grounded business impact statements from the selected document.</p>}
            </div>
            </GlassCard>
          </div>
        </div>

        <div className="lg:col-span-8" data-tour="document-review-output-panel">
          <div data-tour="document-review-output-tabs" role="tablist" aria-label="Document review panels" className="inline-flex h-10 items-center justify-center rounded-md bg-secondary/30 border border-border/50 p-1 text-muted-foreground mb-4">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'findings'}
              aria-controls="document-review-panel-findings"
              className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-xs font-medium transition-all ${activeTab === 'findings' ? 'bg-secondary text-foreground shadow-sm' : ''}`}
              onClick={() => setActiveTab('findings')}
            >
              Findings ({findings.length})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'evidence'}
              aria-controls="document-review-panel-evidence"
              className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-xs font-medium transition-all ${activeTab === 'evidence' ? 'bg-secondary text-foreground shadow-sm' : ''}`}
              onClick={() => setActiveTab('evidence')}
            >
              Evidence
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'artifacts'}
              aria-controls="document-review-panel-artifacts"
              className={`inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-xs font-medium transition-all ${activeTab === 'artifacts' ? 'bg-secondary text-foreground shadow-sm' : ''}`}
              onClick={() => setActiveTab('artifacts')}
            >
              Artifacts
            </button>
          </div>

          {activeTab === 'findings' && (
            <div id="document-review-panel-findings" role="tabpanel" className="space-y-3 mt-0">
              {findings.length > 0 ? findings.map((finding, index) => (
                <motion.div
                  key={finding.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + index * 0.05 }}
                  className="glass rounded-xl p-4 hover:border-primary/20 transition-all duration-300"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={finding.severity} />
                      <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground">{finding.category}</span>
                    </div>
                  </div>
                  <h4 className="text-sm font-medium text-foreground mb-1">{finding.title}</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed mb-3">{finding.description}</p>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      {operatorPreferences.showSourceBadges ? (
                        <>
                          <div className="flex items-center gap-1 text-[10px] text-muted-foreground bg-secondary/40 px-2 py-1 rounded min-w-0">
                            <FileText className="w-3 h-3 shrink-0" />
                            <span className="truncate max-w-[150px]">{finding.source}</span>
                          </div>
                          <span className="text-[10px] font-mono text-muted-foreground/60">{finding.chunkId}</span>
                        </>
                      ) : null}
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-border/30">
                    <div className="flex items-start gap-2">
                      <Info className="w-3 h-3 text-primary mt-0.5 shrink-0" />
                      <p className="text-[11px] text-primary/80">{finding.recommendation}</p>
                    </div>
                  </div>
                </motion.div>
              )) : (
                <GlassCard>
                  <div className="text-xs text-muted-foreground">Run the grounded review to populate real findings from the selected document.</div>
                </GlassCard>
              )}
            </div>
          )}

          {activeTab === 'evidence' && (
            <div id="document-review-panel-evidence" role="tabpanel" className="mt-0">
              <GlassCard>
                <h3 className="text-sm font-medium text-foreground mb-3">Evidence Trail</h3>
                {evidenceTrail.length > 0 ? evidenceTrail.map((item) => (
                  <div key={String(item.id || item.title)} className="py-3 border-b border-border/30 last:border-0">
                    <div className="flex items-center gap-2 mb-2">
                      <SeverityBadge severity={normalizeSeverity(item.severity)} />
                      <span className="text-xs text-foreground">{item.title}</span>
                    </div>
                    <div className="bg-secondary/30 rounded-lg p-3 text-xs text-muted-foreground font-mono leading-relaxed">
                      <span className="text-primary">[{item.chunkId || 'chunk_n/a'}]</span> {item.snippet || 'No grounded snippet available.'}
                    </div>
                  </div>
                )) : (
                  <div className="text-xs text-muted-foreground">Evidence snippets will appear here after the grounded review runs.</div>
                )}
              </GlassCard>
            </div>
          )}

          {activeTab === 'artifacts' && (
            <div id="document-review-panel-artifacts" role="tabpanel" className="mt-0">
              <GlassCard>
                <h3 className="text-sm font-medium text-foreground mb-3">Generated Artifacts</h3>
                {(trelloPublishResult || notionPublishResult) ? (
                  <div className="mb-4 grid gap-3 md:grid-cols-2">
                    {trelloPublishResult ? (
                      <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-xs font-medium text-foreground">Trello publish</p>
                            <p className="mt-1 text-[10px] text-muted-foreground">{trelloPublishResult.message || 'The current review was sent to Trello.'}</p>
                          </div>
                          <StatusPill status={trelloPublishResult.status || 'completed'} />
                        </div>
                      </div>
                    ) : null}
                    {notionPublishResult ? (
                      <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-xs font-medium text-foreground">Notion handoff</p>
                            <p className="mt-1 text-[10px] text-muted-foreground">{notionPublishResult.message || notionPublishResult.page_title || 'The current review was published to Notion.'}</p>
                          </div>
                          <StatusPill status={notionPublishResult.status || 'completed'} />
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <div className="space-y-2">
                  {allArtifacts.length > 0 ? allArtifacts.map((artifact) => (
                    <div key={`${artifact.artifact_type}-${artifact.path || artifact.label}`} className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors">
                      <div className="flex items-center gap-2 min-w-0">
                        <StatusPill status={artifact.available ? 'ready' : 'pending'} />
                        <span className="text-xs text-foreground">{artifact.download_name || artifact.label}</span>
                      </div>
                      <Button variant="ghost" size="sm" className="h-7 text-[10px] text-muted-foreground hover:text-foreground" onClick={() => handleOpenArtifact(artifact)}>
                        Open
                      </Button>
                    </div>
                  )) : <div className="text-xs text-muted-foreground">Run the workflow and generate the deck to populate real artifacts here.</div>}
                </div>
              </GlassCard>
            </div>
          )}
        </div>
      </div>

      <div className="mt-6" data-tour="document-review-publish" data-testid="workflow-publish-actions-surface" data-workflow="document-review">
        <WorkflowPublishActions
          workflowId="document_review"
          result={workflowResponse?.result ?? null}
          runId={workflowResponse?.run_id ?? null}
          title="Publish outputs"
          description="After reviewing findings, evidence and artifacts, preview the Trello cards or the Notion handoff before publishing."
          notionPreviewPayload={{
            product_api_base_url: PRODUCT_API_BASE_URL,
            title: selectedDocument?.name,
            summary: workflowResponse?.result.summary,
            recommendation: workflowResponse?.result.recommendation || decisionSummary.label,
            next_owner: decisionSummary.next_owner || null,
            findings: findings.map((finding) => ({
              title: finding.title,
              severity: finding.severity,
              category: finding.category,
              recommendation: finding.recommendation,
            })),
            next_steps: reviewView?.next_steps || topBlockers.map((item) => item.title || item.recommendation || 'Review blocker'),
            documents: selectedDocument ? [selectedDocument.name] : [],
            primary_documents: selectedDocument ? [selectedDocument.name] : [],
            source_document_name: selectedDocument?.name || null,
            source_document_title: selectedDocument?.name || null,
            source_document_filename: selectedDocument?.name || null,
            source_document_category: 'review',
          }}
          onTrelloPublished={setTrelloPublishResult}
          onNotionPublished={setNotionPublishResult}
        />
      </div>

    </motion.div>
  );
}
