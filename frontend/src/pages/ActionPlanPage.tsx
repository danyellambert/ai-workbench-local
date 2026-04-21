import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  Info,
  Loader2,
  Play,
  Sparkles,
  User,
} from 'lucide-react';

import { WorkflowPublishActions } from '@/components/product/WorkflowPublishActions';
import { PageHeader, StatusPill, SeverityBadge, GlassCard, WorkflowProgressHeader } from '@/components/shared/ui-components';
import {
  buildProductArtifactUrl,
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  runProductWorkflow,
  type ProductActionPlanEvidenceGap,
  type ProductActionPlanItem,
  type ProductActionPlanView,
  type ProductDocumentLibraryEntry,
  type ProductRunWorkflowResponse,
  type ProductPublishNotionResponse,
  type ProductPublishTrelloResponse,
  type ProductWorkflowArtifact,
} from '@/lib/product-api';
import { toast } from '@/components/ui/sonner';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

const statusCols: Array<ProductActionPlanItem['status']> = ['open', 'in_progress', 'blocked', 'done'];
const workflowSteps = [
  { key: 'select', label: 'Select' },
  { key: 'ground', label: 'Ground' },
  { key: 'analyze', label: 'Analyze' },
  { key: 'review', label: 'Review' },
  { key: 'export', label: 'Export' },
] as const;

type ActionPlanTab = 'board' | 'table' | 'timeline' | 'evidence';

function formatDate(value?: string | null): string {
  if (!value) return 'n/a';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function dueSortKey(value?: string | null): [number, string] {
  if (!value) return [2, ''];
  const normalized = value.trim();
  const parsed = Date.parse(normalized.includes('T') ? normalized : `${normalized}T00:00:00`);
  if (!Number.isNaN(parsed)) {
    return [0, new Date(parsed).toISOString()];
  }
  return [1, normalized];
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

function selectedDocumentSummary(documents: ProductDocumentLibraryEntry[]): string {
  if (!documents.length) return 'Select grounded documents to build a live action plan.';
  if (documents.length === 1) return `1 document selected - ${documents[0].name}`;
  if (documents.length === 2) return `2 documents selected - ${documents[0].name} + ${documents[1].name}`;
  return `${documents.length} documents selected - ${documents[0].name} + ${documents.length - 1} more`;
}

function getGapBadgeClass(status: ProductActionPlanEvidenceGap['status']): string {
  if (status === 'sufficient') return 'bg-glow-success/10 text-glow-success border-glow-success/20';
  if (status === 'partial') return 'bg-glow-warning/10 text-glow-warning border-glow-warning/20';
  return 'bg-glow-error/10 text-glow-error border-glow-error/20';
}

function getGapLabel(status: ProductActionPlanEvidenceGap['status']): string {
  if (status === 'sufficient') return 'Sufficient';
  if (status === 'partial') return 'Partial';
  return 'Missing';
}


function emptyActionPlanSummary(documentCount = 0, artifactCount = 0): ProductActionPlanView['summary'] {
  return {
    total: 0,
    open: 0,
    in_progress: 0,
    blocked: 0,
    done: 0,
    completed: 0,
    critical_path: 0,
    evidence_gaps: 0,
    documents: documentCount,
    artifacts: artifactCount,
  };
}

function normalizeTab(defaultEvidencePanelOpen: boolean): ActionPlanTab {
  return defaultEvidencePanelOpen ? 'evidence' : 'board';
}

type GroundingPreviewBlock = {
  source: string;
  excerpt: string;
};

function parseGroundingPreviewBlocks(previewText?: string | null): GroundingPreviewBlock[] {
  if (!previewText) return [];
  const pattern = /\[Source:\s*([^\]]+)\]\s*([\s\S]*?)(?=(?:\[Source:)|$)/g;
  const blocks: GroundingPreviewBlock[] = [];
  let match: RegExpExecArray | null = null;
  while ((match = pattern.exec(previewText)) !== null) {
    const source = match[1]?.trim();
    const excerpt = match[2]?.replace(/\s+/g, ' ').trim();
    if (!source || !excerpt) continue;
    blocks.push({ source, excerpt });
    if (blocks.length >= 3) break;
  }
  if (blocks.length) return blocks;
  return [{ source: 'Grounded context', excerpt: previewText.replace(/\s+/g, ' ').trim() }];
}

function truncatePreviewText(value: string, maxChars = 220): string {
  if (value.length <= maxChars) return value;
  return `${value.slice(0, maxChars - 1).trimEnd()}…`;
}

export default function ActionPlanPage() {
  const queryClient = useQueryClient();
  const operatorPreferences = useAppStore((state) => state.operatorPreferences);
  const defaultTab = normalizeTab(operatorPreferences.defaultEvidencePanelOpen);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const previousAvailableDocumentIdsRef = useRef<string[]>([]);
  const [activeTab, setActiveTab] = useState<ActionPlanTab>(defaultTab);
  const [workflowResponse, setWorkflowResponse] = useState<ProductRunWorkflowResponse | null>(null);
  const [generatedArtifacts, setGeneratedArtifacts] = useState<ProductWorkflowArtifact[]>([]);
  const [trelloPublishResult, setTrelloPublishResult] = useState<ProductPublishTrelloResponse | null>(null);
  const [notionPublishResult, setNotionPublishResult] = useState<ProductPublishNotionResponse | null>(null);

  const { data: documentLibrary, isLoading: documentsLoading, isError: documentsError } = useQuery({
    queryKey: ['product-document-library'],
    queryFn: getProductDocumentLibrary,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const availableDocuments = useMemo(
    () => (documentLibrary?.documents ?? []).filter((document) => document.status === 'indexed' || document.status === 'warning'),
    [documentLibrary],
  );

  useEffect(() => {
    const availableIds = availableDocuments.map((document) => document.document_id);
    const previousAvailableIds = previousAvailableDocumentIdsRef.current;
    previousAvailableDocumentIdsRef.current = availableIds;

    if (!availableIds.length) {
      if (selectedDocumentIds.length) setSelectedDocumentIds([]);
      return;
    }

    const validSelected = selectedDocumentIds.filter((documentId) => availableIds.includes(documentId));
    const hadNoPreviousDocuments = previousAvailableIds.length === 0;
    const previouslySelectedAllDocuments =
      previousAvailableIds.length > 0 && previousAvailableIds.every((documentId) => selectedDocumentIds.includes(documentId));
    const newDocumentWasAdded = availableIds.some((documentId) => !previousAvailableIds.includes(documentId));

    if (!validSelected.length && (hadNoPreviousDocuments || !selectedDocumentIds.length)) {
      setSelectedDocumentIds(availableIds);
      return;
    }

    if (validSelected.length !== selectedDocumentIds.length) {
      setSelectedDocumentIds(validSelected);
      return;
    }

    if (previouslySelectedAllDocuments && newDocumentWasAdded) {
      setSelectedDocumentIds(availableIds);
    }
  }, [availableDocuments, selectedDocumentIds]);

  const selectedDocuments = useMemo(
    () => availableDocuments.filter((document) => selectedDocumentIds.includes(document.document_id)),
    [availableDocuments, selectedDocumentIds],
  );

  const previewQuery = useQuery({
    queryKey: ['product-action-plan-preview', ...selectedDocumentIds],
    enabled: selectedDocumentIds.length > 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryFn: () =>
      getProductGroundingPreview({
        workflowId: 'action_plan_evidence_review',
        strategy: 'document_scan',
        documentIds: selectedDocumentIds,
      }),
  });

  const runActionPlanMutation = useMutation({
    mutationFn: () =>
      runProductWorkflow({
        workflow_id: 'action_plan_evidence_review',
        document_ids: selectedDocumentIds,
        context_strategy: 'document_scan',
        context_window_mode: 'auto',
        use_document_context: true,
      }),
    onSuccess: async (payload) => {
      setWorkflowResponse(payload);
      setGeneratedArtifacts([]);
      setTrelloPublishResult(null);
      setNotionPublishResult(null);
      setActiveTab('board');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
      ]);
      toast.success('Action plan generated from grounded backend output.');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Action plan workflow failed.');
    },
  });

  const generateDeckMutation = useMutation({
    mutationFn: () => {
      if (!workflowResponse?.result) {
        throw new Error('Run the action plan workflow before generating the deck.');
      }
      return generateProductWorkflowDeck(workflowResponse.result, { runId: workflowResponse.run_id });
    },
    onSuccess: async (payload) => {
      setGeneratedArtifacts(payload.artifacts);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-artifacts'] }),
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      toast.success('Action plan deck artifacts generated successfully.');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Deck generation failed.');
    },
  });


  const actionPlanView = workflowResponse?.action_plan_view ?? null;
  const summary = actionPlanView?.summary ?? emptyActionPlanSummary(selectedDocumentIds.length, generatedArtifacts.length);
  const items = actionPlanView?.items ?? [];
  const criticalPath = actionPlanView?.critical_path ?? [];
  const evidenceGaps = actionPlanView?.evidence_gaps ?? [];
  const allArtifacts = useMemo(
    () => dedupeArtifacts([...(actionPlanView?.artifacts ?? []), ...(workflowResponse?.result.artifacts ?? []), ...generatedArtifacts]),
    [actionPlanView, generatedArtifacts, workflowResponse],
  );
  const groundingPreview = workflowResponse?.result.grounding_preview ?? previewQuery.data?.preview ?? null;
  const groundingPreviewBlocks = useMemo(
    () => parseGroundingPreviewBlocks(groundingPreview?.preview_text),
    [groundingPreview?.preview_text],
  );
  const runMetadata = actionPlanView?.run_metadata ?? null;
  const warnings = runMetadata?.warnings ?? workflowResponse?.result.warnings ?? [];
  const highlights = runMetadata?.highlights ?? workflowResponse?.result.highlights ?? [];

  const sortedTimelineItems = useMemo(
    () => [...items].sort((left, right) => {
      const [leftRank, leftValue] = dueSortKey(left.due_date);
      const [rightRank, rightValue] = dueSortKey(right.due_date);
      if (leftRank !== rightRank) return leftRank - rightRank;
      return leftValue.localeCompare(rightValue);
    }),
    [items],
  );

  const stepStatuses = useMemo(() => {
    const runStateMap = new Map((runMetadata?.run_state.steps ?? []).map((step) => [step.key, step.status]));
    return workflowSteps.map((step) => {
      let status = runStateMap.get(step.key) || 'pending';
      if (!runStateMap.size) {
        if (step.key === 'select' && selectedDocumentIds.length > 0) status = 'completed';
        if (step.key === 'ground' && groundingPreview) status = 'completed';
        if (step.key === 'analyze' && runActionPlanMutation.isPending) status = 'running';
        if (step.key === 'analyze' && workflowResponse?.result) status = workflowResponse.result.status === 'error' ? 'error' : 'completed';
        if (step.key === 'review' && actionPlanView) status = 'completed';
        if (step.key === 'export' && allArtifacts.length > 0) status = 'completed';
      }
      if (step.key === 'export' && generateDeckMutation.isPending) status = 'running';
      if (step.key === 'export' && allArtifacts.length > 0) status = 'completed';
      return { ...step, status };
    });
  }, [actionPlanView, allArtifacts.length, generateDeckMutation.isPending, groundingPreview, runActionPlanMutation.isPending, runMetadata, selectedDocumentIds.length, workflowResponse]);

  const handleToggleDocument = (documentId: string) => {
    setSelectedDocumentIds((current) => {
      if (current.includes(documentId)) {
        if (current.length === 1) return current;
        return current.filter((value) => value !== documentId);
      }
      return [...current, documentId];
    });
    setWorkflowResponse(null);
    setGeneratedArtifacts([]);
    setTrelloPublishResult(null);
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
    <motion.div className="p-6 lg:p-8 max-w-[1440px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Action Plan & Evidence Review" description="Turn grounded findings into action items with owners, timelines and evidence tracking.">
        <Button
          variant="outline"
          className="h-9 px-4 text-xs"
          disabled={!workflowResponse?.result || generateDeckMutation.isPending}
          onClick={() => generateDeckMutation.mutate()}
        >
          {generateDeckMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />}
          Generate Deck
        </Button>
        <Button
          className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"
          disabled={!selectedDocumentIds.length || runActionPlanMutation.isPending || documentsLoading}
          onClick={() => runActionPlanMutation.mutate()}
        >
          {runActionPlanMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-2" />}
          Run Action Plan
        </Button>
      </PageHeader>

      <WorkflowProgressHeader
        steps={stepStatuses}
        title="Workflow progress"
        description="Track how the live run moves from document selection to export-ready action items."
      />

      {documentsError && (
        <GlassCard className="mb-6 border border-glow-error/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-4 h-4 text-glow-error mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-foreground">Product API unavailable</p>
              <p className="text-xs text-muted-foreground mt-1">
                The document library could not be loaded. Start the backend Product API and retry.
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {documentsLoading && (
        <GlassCard className="mb-6">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading grounded document library...
          </div>
        </GlassCard>
      )}

      {!documentsLoading && !availableDocuments.length && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-glow-warning mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-foreground">No indexed documents available</p>
              <p className="text-xs text-muted-foreground mt-1">
                Upload and index the curated audit, evidence and risk documents before running the Action Plan workflow.
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {!!availableDocuments.length && (
        <GlassCard className="mb-6" delay={0.04}>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
            <div className="min-w-0">
              <div className="flex items-start justify-between gap-4 mb-3">
                <div>
                  <h2 className="text-sm font-medium text-foreground">Grounded document selection</h2>
                  <p className="text-xs text-muted-foreground mt-1">{selectedDocumentSummary(selectedDocuments)}</p>
                </div>
                <div className="text-right text-[10px] text-muted-foreground">
                  <div>{availableDocuments.length} available</div>
                  <div>{documentLibrary?.summary.total_chunks || 0} total chunks</div>
                </div>
              </div>

              <ScrollArea className="h-[340px] pr-3">
                <div className="space-y-2">
                  {availableDocuments.map((document) => {
                    const selected = selectedDocumentIds.includes(document.document_id);
                    return (
                      <button
                        key={document.document_id}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => handleToggleDocument(document.document_id)}
                        className={cn(
                          'w-full rounded-xl border px-3 py-3 text-left transition-all duration-200',
                          selected
                            ? 'border-primary/50 bg-primary/10 shadow-[0_0_0_1px_rgba(80,120,255,0.15)]'
                            : 'border-border/60 bg-secondary/20 hover:border-primary/20 hover:bg-secondary/30',
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span
                                className={cn(
                                  'inline-flex h-5 min-w-5 items-center justify-center rounded-full border px-1.5 text-[10px] font-semibold',
                                  selected ? 'border-primary/40 bg-primary/15 text-primary' : 'border-border bg-background/70 text-muted-foreground',
                                )}
                              >
                                {selected ? '✓' : '○'}
                              </span>
                              <p className="text-xs font-medium text-foreground line-clamp-2">{document.name}</p>
                            </div>
                            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
                              <span>{document.chunk_count} chunks</span>
                              <span>{document.char_count.toLocaleString()} chars</span>
                              <span>{document.loader_strategy_label || 'Grounded ingest'}</span>
                              {document.size_label ? <span>{document.size_label}</span> : null}
                            </div>
                            {document.warnings?.length ? (
                              <p className="mt-2 text-[10px] text-glow-warning leading-relaxed">{document.warnings[0]}</p>
                            ) : null}
                          </div>
                          <StatusPill status={document.status} />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </ScrollArea>
            </div>

            <div className="min-w-0 rounded-xl border border-border/50 bg-secondary/20 px-4 py-4">
              <div className="flex items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-2">
                  <Info className="w-4 h-4 text-primary" />
                  <h3 className="text-xs font-medium text-foreground">Grounding preview</h3>
                </div>
                <StatusPill
                  status={
                    previewQuery.isLoading
                      ? 'running'
                      : groundingPreview?.warnings?.length
                        ? 'warning'
                        : groundingPreview
                          ? 'ready'
                          : 'pending'
                  }
                />
              </div>
              {previewQuery.isLoading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Building preview from selected evidence...
                </div>
              ) : groundingPreview ? (
                <div className="space-y-3">
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Quick signal check before execution: confirm the workflow is using the intended documents, enough source blocks and the expected evidence themes.
                  </p>
                  <div className="grid gap-2 sm:grid-cols-3">
                    <div className="rounded-lg border border-border/40 bg-background/60 px-3 py-2">
                      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Selected docs</div>
                      <div className="text-sm font-medium text-foreground">{groundingPreview.document_ids.length}</div>
                    </div>
                    <div className="rounded-lg border border-border/40 bg-background/60 px-3 py-2">
                      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Source blocks</div>
                      <div className="text-sm font-medium text-foreground">{groundingPreview.source_block_count}</div>
                    </div>
                    <div className="rounded-lg border border-border/40 bg-background/60 px-3 py-2">
                      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Context size</div>
                      <div className="text-sm font-medium text-foreground">{groundingPreview.context_chars.toLocaleString()} chars</div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                      <FileText className="w-3.5 h-3.5" />
                      Context highlights
                    </div>
                    <div className="space-y-2">
                      {groundingPreviewBlocks.slice(0, 2).map((block) => (
                        <div key={`${block.source}-${block.excerpt.slice(0, 24)}`} className="rounded-lg border border-border/40 bg-background/60 px-3 py-2">
                          <div className="text-[10px] font-medium uppercase tracking-wide text-primary">{block.source}</div>
                          <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{truncatePreviewText(block.excerpt)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  {groundingPreview.warnings?.length ? (
                    <div className="rounded-lg border border-glow-warning/30 bg-glow-warning/10 px-3 py-2">
                      <div className="text-[10px] uppercase tracking-wide text-glow-warning font-medium">Context caveats</div>
                      <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                        {groundingPreview.warnings.map((warning) => (
                          <li key={warning}>• {warning}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Select at least one indexed document to preview the grounded context.</p>
              )}
            </div>
          </div>
        </GlassCard>
      )}

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Open', value: summary.open, color: 'text-primary' },
          { label: 'In Progress', value: summary.in_progress, color: 'text-glow-warning' },
          { label: 'Blocked', value: summary.blocked, color: 'text-glow-error' },
          { label: 'Done', value: summary.done, color: 'text-glow-success' },
        ].map((metric) => (
          <div key={metric.label} className="glass rounded-xl p-4 text-center">
            <p className={`text-2xl font-semibold ${metric.color}`}>{metric.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{metric.label}</p>
          </div>
        ))}
      </motion.div>

      {!!criticalPath.length && (
        <GlassCard className="mb-6" delay={0.12}>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Critical Path - Top Unblockers</h3>
          </div>
          <div className="space-y-2">
            {criticalPath.slice(0, 3).map((item, index) => (
              <div key={item.id} className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg bg-secondary/20">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-[10px] font-bold text-muted-foreground w-4">{index + 1}</span>
                  <SeverityBadge severity={item.priority} />
                  <span className="text-xs text-foreground truncate">{item.title}</span>
                </div>
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground shrink-0">
                  {item.owner ? <span>{item.owner}</span> : null}
                  <span>Due: {formatDate(item.due_date)}</span>
                  <StatusPill status={item.status} />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as ActionPlanTab)}>
        <TabsList className="bg-secondary/30 border border-border/50 mb-4">
          <TabsTrigger value="board" className="text-xs data-[state=active]:bg-secondary">Board</TabsTrigger>
          <TabsTrigger value="table" className="text-xs data-[state=active]:bg-secondary">Table</TabsTrigger>
          <TabsTrigger value="timeline" className="text-xs data-[state=active]:bg-secondary">Timeline</TabsTrigger>
          <TabsTrigger value="evidence" className="text-xs data-[state=active]:bg-secondary">Evidence Gaps</TabsTrigger>
        </TabsList>

        <TabsContent value="board" className="mt-0">
          {!actionPlanView ? (
            <GlassCard>
              <div className="flex items-start gap-3">
                <AlertCircle className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-foreground">Run not triggered yet</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Select the grounded audit, evidence and risk documents, then run the live workflow to populate the board, table, timeline and evidence tabs.
                  </p>
                </div>
              </div>
            </GlassCard>
          ) : !items.length ? (
            <GlassCard>
              <p className="text-xs text-muted-foreground">The workflow completed, but no action items were returned by the normalized presenter.</p>
            </GlassCard>
          ) : (
            <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
              {statusCols.map((status) => {
                const columnItems = items.filter((item) => item.status === status);
                return (
                  <div key={status} className="space-y-2">
                    <div className="flex items-center gap-2 mb-2">
                      <StatusPill status={status} />
                      <span className="text-[10px] text-muted-foreground">({columnItems.length})</span>
                    </div>
                    {columnItems.map((item, index) => (
                      <motion.div
                        key={item.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.08 + index * 0.03 }}
                        className="glass rounded-lg p-3 hover:border-primary/20 transition-all"
                      >
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <SeverityBadge severity={item.priority} />
                          {item.source ? <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[110px]">{item.source}</span> : null}
                        </div>
                        <h4 className="text-xs font-medium text-foreground mb-2 leading-relaxed">{item.title}</h4>
                        <p className="text-[10px] text-muted-foreground leading-relaxed min-h-8">{item.rationale || item.evidence || item.notes || 'Grounded execution item.'}</p>
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-3">
                          <User className="w-3 h-3" />
                          <span>{item.owner || 'Owner TBD'}</span>
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-1">
                          <Clock className="w-3 h-3" />
                          <span>{formatDate(item.due_date)}</span>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </TabsContent>

        <TabsContent value="table" className="mt-0">
          {!items.length ? (
            <GlassCard>
              <p className="text-xs text-muted-foreground">Run the workflow to populate the normalized action table.</p>
            </GlassCard>
          ) : (
            <div className="glass rounded-xl overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border/50">
                    {['Task', 'Owner', 'Priority', 'Status', 'Due Date', 'Source'].map((heading) => (
                      <th key={heading} className="text-left px-4 py-3 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} className="border-b border-border/30 hover:bg-secondary/20 transition-colors align-top">
                      <td className="px-4 py-3 text-xs text-foreground max-w-[320px]">
                        <div className="font-medium leading-relaxed">{item.title}</div>
                        {item.rationale ? <div className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{item.rationale}</div> : null}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{item.owner || 'Owner TBD'}</td>
                      <td className="px-4 py-3"><SeverityBadge severity={item.priority} /></td>
                      <td className="px-4 py-3"><StatusPill status={item.status} /></td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{formatDate(item.due_date)}</td>
                      <td className="px-4 py-3 text-[10px] text-muted-foreground font-mono">{item.source || 'n/a'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        <TabsContent value="timeline" className="mt-0">
          {!sortedTimelineItems.length ? (
            <GlassCard>
              <p className="text-xs text-muted-foreground">Run the workflow to populate the timeline view.</p>
            </GlassCard>
          ) : (
            <GlassCard>
              <div className="space-y-4">
                {sortedTimelineItems.map((item, index) => (
                  <div key={item.id} className="flex items-start gap-4">
                    <div className="flex flex-col items-center">
                      <div
                        className={cn(
                          'w-3 h-3 rounded-full',
                          item.status === 'done' && 'bg-glow-success',
                          item.status === 'blocked' && 'bg-glow-error',
                          item.status === 'in_progress' && 'bg-glow-warning',
                          item.status === 'open' && 'bg-primary',
                        )}
                      />
                      {index < sortedTimelineItems.length - 1 && <div className="w-px h-8 bg-border mt-1" />}
                    </div>
                    <div className="pb-4 flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-xs font-medium text-foreground">{item.title}</span>
                        <SeverityBadge severity={item.priority} />
                      </div>
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground flex-wrap">
                        <span>{item.owner || 'Owner TBD'}</span>
                        <span>Due: {formatDate(item.due_date)}</span>
                        <StatusPill status={item.status} />
                      </div>
                      {item.source ? <div className="text-[10px] text-muted-foreground mt-2">Source: {item.source}</div> : null}
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </TabsContent>

        <TabsContent value="evidence" className="mt-0">
          <GlassCard>
            <h3 className="text-sm font-medium text-foreground mb-4">Evidence Gaps Assessment</h3>
            {!evidenceGaps.length ? (
              <p className="text-xs text-muted-foreground">Run the workflow to assess evidence sufficiency for each action item.</p>
            ) : (
              <div className="space-y-3">
                {evidenceGaps.map((gap) => (
                  <div key={gap.id} className="flex items-center justify-between gap-4 py-2 px-3 rounded-lg bg-secondary/20">
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-foreground truncate">{gap.title}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{gap.detail}</p>
                      {gap.source ? <p className="text-[10px] text-muted-foreground mt-1 font-mono">{gap.source}</p> : null}
                    </div>
                    <div className="flex items-center gap-2 ml-3 shrink-0">
                      <span className={cn('text-[10px] px-2 py-0.5 rounded border', getGapBadgeClass(gap.status))}>
                        {getGapLabel(gap.status)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {!!warnings.length && (
              <div className="mt-5 pt-4 border-t border-border/40">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-glow-warning" />
                  <h4 className="text-xs font-medium text-foreground">Workflow watchouts</h4>
                </div>
                <ul className="space-y-1.5 text-xs text-muted-foreground">
                  {warnings.map((warning) => (
                    <li key={warning} className="leading-relaxed">- {warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </GlassCard>
        </TabsContent>
      </Tabs>


      <div className="grid xl:grid-cols-[1.2fr_0.8fr] gap-4 mt-6">
        <GlassCard>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Run summary</h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-border/40 bg-secondary/20 px-4 py-4">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Summary</p>
              <p className="text-sm text-foreground leading-relaxed">{runMetadata?.summary || workflowResponse?.result.summary || 'Run the workflow to generate a grounded summary of the current action plan, blockers and evidence coverage.'}</p>
              {runMetadata?.recommendation || workflowResponse?.result.recommendation ? (
                <p className="mt-3 text-xs text-muted-foreground leading-relaxed">Recommendation: <span className="text-foreground">{runMetadata?.recommendation || workflowResponse?.result.recommendation}</span></p>
              ) : null}
            </div>
            <div className="rounded-xl border border-border/40 bg-secondary/20 px-4 py-4">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Highlights</p>
              {highlights.length ? (
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {highlights.slice(0, 5).map((highlight) => (
                    <li key={highlight} className="leading-relaxed">• {highlight}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">Run the workflow to capture grounded highlights and execution watchouts.</p>
              )}
            </div>
          </div>
          {warnings.length ? (
            <div className="mt-4 rounded-xl border border-glow-warning/30 bg-glow-warning/10 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-glow-warning font-medium mb-2">Watchouts</p>
              <ul className="space-y-1.5 text-xs text-muted-foreground">
                {warnings.slice(0, 4).map((warning) => (
                  <li key={warning}>• {warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </GlassCard>

        <GlassCard>
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Generated artifacts</h3>
          </div>
          {(trelloPublishResult || notionPublishResult) ? (
            <div className="mb-4 grid gap-3 md:grid-cols-2">
              {trelloPublishResult ? (
                <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-foreground">Trello publish</p>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    {trelloPublishResult.message || 'The current run was published to Trello.'}
                  </p>
                </div>
                <StatusPill status={trelloPublishResult.status || 'completed'} />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
                <div className="rounded-md bg-background/70 px-2 py-2">
                  <div className="uppercase tracking-wide text-muted-foreground">Cards</div>
                  <div className="text-sm font-medium text-foreground mt-1">
                    {trelloPublishResult.created_card_count ?? trelloPublishResult.planned_card_count ?? 0}
                  </div>
                </div>
                <div className="rounded-md bg-background/70 px-2 py-2">
                  <div className="uppercase tracking-wide text-muted-foreground">Workspace</div>
                  <div className="text-xs font-medium text-foreground mt-1">{trelloPublishResult.board_name || 'Configured Trello workspace'}</div>
                </div>
              </div>
              {trelloPublishResult.list_breakdown?.length ? (
                <div className="mt-3">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Published by list</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px]">
                    {trelloPublishResult.list_breakdown.map((entry) => (
                      <div key={`${entry.list_id || entry.list_label}`} className="rounded-md bg-background/70 px-2 py-2">
                        <div className="text-muted-foreground uppercase tracking-wide">{entry.list_label}</div>
                        <div className="text-sm font-medium text-foreground mt-1">{entry.count}</div>
                      </div>
                    ))}
                  </div>
                  <p className="mt-2 text-[10px] text-muted-foreground">
                    Action status is mapped to Trello lists as Open → Open, In Progress → Approved, Blocked/Needs review → Review, Done → Done.
                  </p>
                  {trelloPublishResult.board_url ? (
                    <Button variant="outline" size="sm" className="mt-3 h-7 px-2 text-[10px]" onClick={() => window.open(trelloPublishResult.board_url || '', '_blank', 'noopener,noreferrer')}>
                      Open board <ExternalLink className="ml-1 h-3 w-3" />
                    </Button>
                  ) : null}
                </div>
              ) : null}
                </div>
              ) : null}
              {notionPublishResult ? (
                <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-medium text-foreground">Notion handoff</p>
                      <p className="text-[10px] text-muted-foreground mt-1">{notionPublishResult.message || notionPublishResult.page_title || 'The current action plan was published to Notion.'}</p>
                    </div>
                    <StatusPill status={notionPublishResult.status || 'completed'} />
                  </div>
                  {notionPublishResult.page_url ? (
                    <Button variant="outline" size="sm" className="mt-3 h-7 px-2 text-[10px]" onClick={() => window.open(notionPublishResult.page_url || '', '_blank', 'noopener,noreferrer')}>
                      Open page <ExternalLink className="ml-1 h-3 w-3" />
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}
          {!allArtifacts.length ? (
            <p className="text-xs text-muted-foreground">Run the workflow and generate the deck to populate export artifacts here.</p>
          ) : (
            <div className="space-y-3">
              {allArtifacts.map((artifact) => (
                <div key={`${artifact.artifact_type}:${artifact.path || artifact.download_name || artifact.label}`} className="rounded-lg bg-secondary/20 px-3 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-foreground truncate">{artifact.download_name || artifact.label}</p>
                      <p className="text-[10px] text-muted-foreground mt-1">{artifact.label}</p>
                    </div>
                    <StatusPill status={artifact.available ? 'ready' : 'pending'} />
                  </div>
                  <div className="flex items-center justify-between gap-3 mt-3">
                    <span className="text-[10px] text-muted-foreground font-mono">{artifact.artifact_type}</span>
                    <Button size="sm" variant="outline" className="h-7 px-2 text-[10px]" disabled={!artifact.path} onClick={() => handleOpenArtifact(artifact)}>
                      <ExternalLink className="w-3 h-3 mr-1" />
                      Open
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      <div className="mt-6" data-testid="workflow-publish-actions-surface" data-workflow="action-plan">
        <WorkflowPublishActions
          workflowId="action_plan_evidence_review"
          result={workflowResponse?.result ?? null}
          runId={workflowResponse?.run_id ?? null}
          title="Publish outputs"
          description="After reviewing the board, evidence gaps and generated artifacts, preview the selected Trello card or the Notion handoff before publishing."
          notionPreviewPayload={{
            title: actionPlanView?.objective || workflowResponse?.result.summary || 'Action Plan handoff',
            product_api_base_url: PRODUCT_API_BASE_URL,
            summary: workflowResponse?.result.summary,
            recommendation: workflowResponse?.result.recommendation,
            next_owner: criticalPath[0]?.owner || items.find((item) => item.owner)?.owner || null,
            actions: items.map((item) => ({ title: item.title, owner: item.owner, due_date: item.due_date, priority: item.priority, status: item.status })),
            evidence_gaps: evidenceGaps.map((gap) => ({ title: gap.title, status: gap.status, detail: gap.detail })),
            next_steps: items.slice(0, 6).map((item) => item.title),
            highlights,
            documents: selectedDocuments.map((document) => document.name),
            primary_documents: selectedDocuments.map((document) => document.name),
            source_document_name: selectedDocuments[0]?.name || null,
            source_document_title: selectedDocuments[0]?.name || null,
            source_document_filename: selectedDocuments[0]?.name || null,
            source_document_category: 'action-plan',
          }}
          onTrelloPublished={setTrelloPublishResult}
          onNotionPublished={setNotionPublishResult}
        />
      </div>

    </motion.div>
  );
}
