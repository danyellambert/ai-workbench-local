import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  ChevronRight,
  FileText,
  Info,
  Loader2,
  Play,
  Sparkles,
  User,
} from 'lucide-react';
import { PublicExecutionQuotaError, formatPublicExecutionQuotaMessage } from '@/lib/public-demo-limits';

import { WorkflowPublishActions } from '@/components/product/WorkflowPublishActions';
import { PageHeader, StatusPill, SeverityBadge, GlassCard, WorkflowProgressHeader } from '@/components/shared/ui-components';
import {
  buildProductArtifactUrl,
  buildWorkflowResponseFromRunHistory,
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  getProductRunHistoryEntry,
  runProductWorkflow,
  ProductWorkflowTimeoutRecoveryError,
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
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import { ACTION_PLAN_DOCUMENT_LIMIT, findRecommendedDocuments, WORKFLOW_RECOMMENDED_DOCUMENTS } from '@/lib/workflow-demo-documents';

import { formatUserDate } from '@/lib/user-time';
import { aiLabQueryKeys } from '@/lib/ai-lab-data';
import { refreshWorkflowTimeoutRecoveryQueries } from '@/lib/workflow-timeout-recovery';
const statusCols: Array<ProductActionPlanItem['status']> = ['open', 'in_progress', 'blocked', 'done'];
const workflowSteps = [
  { key: 'select', label: 'Select' },
  { key: 'ground', label: 'Ground' },
  { key: 'analyze', label: 'Analyze' },
  { key: 'review', label: 'Review' },
  { key: 'export', label: 'Export' },
] as const;

type ActionPlanTab = 'board' | 'table' | 'timeline' | 'evidence';

function formatDate(value?: string | number | null): string {
  return formatUserDate(value);
}



function normalizeActionSummaryKey(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

function actionSummaryFromRecord(record: Record<string, unknown>): string {
  const title = normalizeActionSummaryKey(record.title || record.description || record.name);
  const candidates = [
    record.card_summary,
    record.summary,
    record.short_summary,
    record.action_summary,
    record.narrative,
    record.explanation,
  ]
    .map((value) => String(value || '').trim())
    .filter(Boolean);

  const selected = candidates.find((value) => {
    const normalized = normalizeActionSummaryKey(value);
    if (!normalized || normalized === title) return false;
    if (value.includes(' | ')) return false;
    if (/\bCTR-\d+\b/i.test(value)) return false;
    if (/\b(Open|In progress|Approved|Done|Blocked)\b/i.test(value) && /\b\d{4}-\d{2}-\d{2}\b/.test(value)) return false;
    return true;
  });

  return selected || '';
}

function collectActionSummaryLookup(source: unknown): Map<string, string> {
  const lookup = new Map<string, string>();
  const seen = new WeakSet<object>();

  function visit(value: unknown): void {
    if (!value || typeof value !== 'object') return;
    if (seen.has(value as object)) return;

    seen.add(value as object);

    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }

    const record = value as Record<string, unknown>;
    const summary = actionSummaryFromRecord(record);
    const title = normalizeActionSummaryKey(record.title || record.description || record.name);
    const evidence = normalizeActionSummaryKey(record.evidence);

    if (summary && title) lookup.set(title, summary);
    if (summary && evidence) lookup.set(evidence, summary);

    Object.values(record).forEach(visit);
  }

  visit(source);
  return lookup;
}


function hasTextEllipsis(value: unknown): boolean {
  const text = String(value || '');
  return text.includes('...') || text.includes('…');
}

function normalizeActionTitleKey(value: unknown): string {
  return String(value || '')
    .trim()
    .replace(/[.…]+$/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

function collectFullActionTitles(source: unknown): string[] {
  const titles: string[] = [];
  const seen = new WeakSet<object>();

  function visit(value: unknown): void {
    if (!value || typeof value !== 'object') return;
    if (seen.has(value as object)) return;
    seen.add(value as object);

    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }

    const record = value as Record<string, unknown>;
    [
      record.full_title,
      record.fullTitle,
      record.full_name,
      record.fullName,
      record.card_title,
      record.cardTitle,
      record.action_title,
      record.actionTitle,
      record.title,
      record.description,
      record.name,
    ].forEach((candidate) => {
      const text = String(candidate || '').trim();
      if (text && !hasTextEllipsis(text) && text.length > 8) titles.push(text);
    });

    Object.values(record).forEach(visit);
  }

  visit(source);
  return Array.from(new Set(titles));
}

function actionItemFullTitle(item: ProductActionPlanItem, source?: unknown): string {
  const raw = item as unknown as Record<string, unknown>;
  const current = String(item.title || raw.description || raw.name || '').trim();

  if (!hasTextEllipsis(current)) return current;

  const currentKey = normalizeActionTitleKey(current);
  const candidates = collectFullActionTitles(source);

  const matched = candidates.find((candidate) => {
    const candidateKey = normalizeActionTitleKey(candidate);
    return candidateKey.startsWith(currentKey) || currentKey.startsWith(candidateKey);
  });

  return matched || current;
}

function actionItemNarrative(item: ProductActionPlanItem, source?: unknown): string {
  const raw = item as unknown as Record<string, unknown>;
  const direct = actionSummaryFromRecord(raw);
  if (direct) return direct;

  const lookup = collectActionSummaryLookup(source);
  const keyCandidates = [
    item.title,
    raw.description,
    raw.evidence,
    raw.name,
  ]
    .map(normalizeActionSummaryKey)
    .filter(Boolean);

  return keyCandidates
    .map((key) => lookup.get(key))
    .find(Boolean) || '';
}

function actionItemNotionLine(item: ProductActionPlanItem): string {
  const due = formatDate(item.due_date);
  return due && due !== '—' ? `Due: ${due}` : '';
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
  const [searchParams] = useSearchParams();
  const historyRunId = searchParams.get('historyRunId') || searchParams.get('runId') || '';
  const operatorPreferences = useAppStore((state) => state.operatorPreferences);
  const defaultTab = normalizeTab(operatorPreferences.defaultEvidencePanelOpen);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const previousAvailableDocumentIdsRef = useRef<string[]>([]);
  const hasInitializedDocumentSelectionRef = useRef(false);
  const [activeTab, setActiveTab] = useState<ActionPlanTab>(defaultTab);
  const [workflowResponse, setWorkflowResponse] = useState<ProductRunWorkflowResponse | null>(null);
  const [generatedArtifacts, setGeneratedArtifacts] = useState<ProductWorkflowArtifact[]>([]);
  const [trelloPublishResult, setTrelloPublishResult] = useState<ProductPublishTrelloResponse | null>(null);
  const [notionPublishResult, setNotionPublishResult] = useState<ProductPublishNotionResponse | null>(null);
  const [isGroundingPreviewOpen, setIsGroundingPreviewOpen] = useState(false);

  useEffect(() => {
    const handleOpenBoard = () => setActiveTab('board');
    window.addEventListener('workbench-tour:open-action-plan-board', handleOpenBoard);
    return () => window.removeEventListener('workbench-tour:open-action-plan-board', handleOpenBoard);
  }, []);

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

  const recommendedActionPlanDocuments = useMemo(
    () => findRecommendedDocuments(availableDocuments, WORKFLOW_RECOMMENDED_DOCUMENTS.actionPlan).slice(0, ACTION_PLAN_DOCUMENT_LIMIT),
    [availableDocuments],
  );

  const recommendedActionPlanDocumentIds = useMemo(
    () => recommendedActionPlanDocuments.map((document) => document.document_id),
    [recommendedActionPlanDocuments],
  );

  useEffect(() => {
    const availableIds = availableDocuments.map((document) => document.document_id);
    previousAvailableDocumentIdsRef.current = availableIds;

    if (!availableIds.length) {
      if (selectedDocumentIds.length) setSelectedDocumentIds([]);
      hasInitializedDocumentSelectionRef.current = false;
      return;
    }

    const validSelected = selectedDocumentIds
      .filter((documentId) => availableIds.includes(documentId))
      .slice(0, ACTION_PLAN_DOCUMENT_LIMIT);

    if (!hasInitializedDocumentSelectionRef.current && !selectedDocumentIds.length) {
      hasInitializedDocumentSelectionRef.current = true;
      const initialSelectionIds = recommendedActionPlanDocumentIds.length
        ? recommendedActionPlanDocumentIds
        : availableIds.slice(0, ACTION_PLAN_DOCUMENT_LIMIT);
      setSelectedDocumentIds(initialSelectionIds);
      return;
    }

    hasInitializedDocumentSelectionRef.current = true;

    if (validSelected.length !== selectedDocumentIds.length || validSelected.some((documentId, index) => documentId !== selectedDocumentIds[index])) {
      setSelectedDocumentIds(validSelected);
    }
  }, [availableDocuments, recommendedActionPlanDocumentIds, selectedDocumentIds]);

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

  useEffect(() => {
    const run = historyDetailQuery.data?.run;
    const hydratedWorkflowResponse = buildWorkflowResponseFromRunHistory(historyDetailQuery.data);
    if (!historyRunId || !run || !hydratedWorkflowResponse?.result || hydratedWorkflowResponse.result.workflow_id !== 'action_plan_evidence_review') return;

    const requestPayload = run.request_payload && typeof run.request_payload === 'object' ? run.request_payload : null;
    const requestDocumentIds = Array.isArray(requestPayload?.document_ids)
      ? requestPayload.document_ids.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const groundingDocumentIds = hydratedWorkflowResponse.result.grounding_preview?.document_ids ?? [];
    const historyDocumentIds = [
      ...(run.document_ids?.length ? run.document_ids : requestDocumentIds),
      ...groundingDocumentIds,
    ]
      .map((item) => String(item || '').trim())
      .filter(Boolean);
    const uniqueDocumentIds = Array.from(new Set(historyDocumentIds)).slice(0, ACTION_PLAN_DOCUMENT_LIMIT);

    hasInitializedDocumentSelectionRef.current = true;
    setSelectedDocumentIds(uniqueDocumentIds);
    setWorkflowResponse(hydratedWorkflowResponse);
    setGeneratedArtifacts(run.artifact_items?.length ? run.artifact_items : hydratedWorkflowResponse.result.artifacts ?? []);
    setTrelloPublishResult(null);
    setNotionPublishResult(null);
    setActiveTab('board');
  }, [historyDetailQuery.data, historyRunId]);

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
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.evals }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.overview }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.runtime }),
      ]);
      toast.success('Action plan generated from grounded backend output.');
    },
    onError: async (error) => {
      if (error instanceof ProductWorkflowTimeoutRecoveryError) {
        await refreshWorkflowTimeoutRecoveryQueries(queryClient);
        toast.error('Action plan is still taking longer than expected. Check Run History in a moment; the backend may still finish the run.');
        return;
      }
      toast.error(error instanceof PublicExecutionQuotaError ? formatPublicExecutionQuotaMessage(error) : error instanceof Error ? error.message : 'Action plan workflow failed.');
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
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.evals }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.overview }),
        queryClient.invalidateQueries({ queryKey: aiLabQueryKeys.runtime }),
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
  const groundingPreviewStatus = previewQuery.isLoading
    ? 'running'
    : groundingPreview?.warnings?.length
      ? 'warning'
      : groundingPreview
        ? 'ready'
        : 'pending';
  const groundingPreviewSummary = groundingPreview
    ? `${groundingPreview.document_ids.length} docs · ${groundingPreview.source_block_count} blocks · ${groundingPreview.context_chars.toLocaleString()} chars`
    : selectedDocumentIds.length
      ? 'Preview available for the selected documents'
      : 'Select documents to prepare a preview';
  const maximumSelectionReached = selectedDocumentIds.length >= ACTION_PLAN_DOCUMENT_LIMIT;
  const preferredSelectionIds = recommendedActionPlanDocumentIds.length
    ? recommendedActionPlanDocumentIds
    : availableDocuments.slice(0, ACTION_PLAN_DOCUMENT_LIMIT).map((document) => document.document_id);
  const preferredDocumentsSelected = preferredSelectionIds.length > 0 && preferredSelectionIds.every((documentId) => selectedDocumentIds.includes(documentId));
  const hasSelectedDocuments = selectedDocumentIds.length > 0;
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

  const resetRunOutputs = () => {
    setWorkflowResponse(null);
    setGeneratedArtifacts([]);
    setTrelloPublishResult(null);
    setNotionPublishResult(null);
    setActiveTab(defaultTab);
  };

  const handleToggleDocument = (documentId: string) => {
    hasInitializedDocumentSelectionRef.current = true;
    setSelectedDocumentIds((current) => {
      if (current.includes(documentId)) {
        return current.filter((value) => value !== documentId);
      }
      if (current.length >= ACTION_PLAN_DOCUMENT_LIMIT) {
        toast.warning(`Action Plan uses up to ${ACTION_PLAN_DOCUMENT_LIMIT} documents at once. Deselect one before adding another.`);
        return current;
      }
      return [...current, documentId];
    });
    resetRunOutputs();
  };

  const handleSelectAllDocuments = () => {
    hasInitializedDocumentSelectionRef.current = true;
    setSelectedDocumentIds(preferredSelectionIds);
    resetRunOutputs();
  };

  const handleClearSelectedDocuments = () => {
    hasInitializedDocumentSelectionRef.current = true;
    setSelectedDocumentIds([]);
    resetRunOutputs();
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
      <div data-tour="action-plan-header">
        <PageHeader title="Action Plan & Evidence Review" description="Turn grounded findings into action items with owners, timelines and evidence tracking.">
        <Button
          className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"
          disabled={!selectedDocumentIds.length || runActionPlanMutation.isPending || documentsLoading}
          onClick={() => runActionPlanMutation.mutate()}
        >
          {runActionPlanMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-2" />}
          Run Action Plan
        </Button>
        <Button
          variant="outline"
          className="h-9 px-4 text-xs"
          disabled={!workflowResponse?.result || generateDeckMutation.isPending}
          onClick={() => generateDeckMutation.mutate()}
        >
          {generateDeckMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />}
          Generate Deck
        </Button>
        </PageHeader>
      </div>

      <div data-tour="action-plan-progress">
        <WorkflowProgressHeader
          steps={stepStatuses}
          title="Workflow progress"
          description="Track how the live run moves from document selection to export-ready action items."
        />
      </div>

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
        <>
          <GlassCard className="mb-5" delay={0.04} data-tour="action-plan-selection">
            <div className="space-y-3">
              <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-medium text-foreground">Grounded document selection</h2>
                    <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-[10px] text-primary">
                      Grounding preview below
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{selectedDocumentSummary(selectedDocuments)}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="rounded-full border border-border/50 bg-background/60 px-2.5 py-1 text-[10px] text-muted-foreground">
                      {selectedDocumentIds.length} selected
                    </span>
                    <span className="rounded-full border border-border/50 bg-background/60 px-2.5 py-1 text-[10px] text-muted-foreground">
                      max {ACTION_PLAN_DOCUMENT_LIMIT} docs
                    </span>
                    <span className="rounded-full border border-border/50 bg-background/60 px-2.5 py-1 text-[10px] text-muted-foreground">
                      {availableDocuments.length} available
                    </span>
                    <span className="rounded-full border border-border/50 bg-background/60 px-2.5 py-1 text-[10px] text-muted-foreground">
                      {(documentLibrary?.summary.total_chunks || 0).toLocaleString()} total chunks
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 xl:justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    className="h-8 border-border/60 bg-background/45 px-3 text-[11px] text-muted-foreground hover:bg-background/70 hover:text-foreground"
                    onClick={preferredDocumentsSelected ? handleClearSelectedDocuments : handleSelectAllDocuments}
                    disabled={!availableDocuments.length}
                  >
                    {preferredDocumentsSelected ? 'Deselect all' : recommendedActionPlanDocumentIds.length ? 'Use recommended 4' : 'Select first 4'}
                  </Button>
                  <span className="rounded-full border border-border/50 bg-background/60 px-2.5 py-1 text-[10px] text-muted-foreground">
                    {hasSelectedDocuments ? 'Review selection first' : 'No documents selected'}
                  </span>
                </div>
              </div>

              <div className="rounded-2xl border border-border/40 bg-background/20 p-2">
                <ScrollArea className="h-[170px] pr-2">
                  <div className="space-y-1">
                    {availableDocuments.map((document) => {
                      const selected = selectedDocumentIds.includes(document.document_id);
                      return (
                        <button
                          key={document.document_id}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => handleToggleDocument(document.document_id)}
                          disabled={!selected && maximumSelectionReached}
                          title={!selected && maximumSelectionReached ? `Limit of ${ACTION_PLAN_DOCUMENT_LIMIT} selected documents reached` : undefined}
                          className={cn(
                            'w-full rounded-xl border px-3 py-1.5 text-left transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50',
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
                                <p className="line-clamp-1 text-xs font-medium text-foreground">{document.name}</p>
                              </div>
                              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
                                <span>{document.chunk_count} chunks</span>
                                <span>{document.char_count.toLocaleString()} chars</span>
                                <span>{document.loader_strategy_label || 'Grounded ingest'}</span>
                                {document.size_label ? <span>{document.size_label}</span> : null}
                              </div>
                              {document.warnings?.length ? (
                                <p className="mt-2 text-[10px] leading-relaxed text-glow-warning">{document.warnings[0]}</p>
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
            </div>
          </GlassCard>

          <GlassCard className="mb-6" delay={0.06} data-tour="action-plan-grounding">
            <Collapsible open={isGroundingPreviewOpen} onOpenChange={setIsGroundingPreviewOpen}>
              <div className="space-y-3">
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="group w-full rounded-2xl border border-border/50 bg-background/35 px-4 py-3.5 text-left transition-all duration-200 hover:border-primary/20 hover:bg-background/50 hover:shadow-[0_8px_24px_rgba(6,14,40,0.12)]"
                    aria-label={isGroundingPreviewOpen ? 'Hide grounding preview' : 'Show grounding preview'}
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                      <div className="flex min-w-0 items-start gap-3">
                        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-primary/10 text-primary">
                          <Info className="h-4 w-4" />
                        </span>
                        <span className="min-w-0">
                          <span className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-medium text-foreground">Grounding preview</span>
                            <span
                              className={cn(
                                'inline-flex rounded-full border px-2 py-0.5 text-[10px] font-medium',
                                groundingPreviewStatus === 'warning'
                                  ? 'border-glow-warning/30 bg-glow-warning/10 text-glow-warning'
                                  : groundingPreviewStatus === 'ready'
                                    ? 'border-primary/25 bg-primary/10 text-primary'
                                    : 'border-border/50 bg-background/60 text-muted-foreground',
                              )}
                            >
                              {groundingPreviewStatus === 'running'
                                ? 'Updating'
                                : groundingPreviewStatus === 'warning'
                                  ? 'Needs attention'
                                  : groundingPreviewStatus === 'ready'
                                    ? 'Ready'
                                    : 'Idle'}
                            </span>
                          </span>
                          <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">
                            {isGroundingPreviewOpen
                              ? 'Hide the detailed grounded signals once you are done reviewing the current selection.'
                              : groundingPreviewSummary}
                          </span>
                        </span>
                      </div>

                      <div className="flex items-center justify-between gap-3 lg:justify-end">
                        <span className="flex flex-wrap gap-2">
                          <span className="rounded-full border border-border/40 bg-background/55 px-2.5 py-1 text-[10px] text-muted-foreground">
                            {previewQuery.isLoading ? 'Refreshing preview' : groundingPreview ? 'Preview ready' : 'Preview on demand'}
                          </span>
                          {groundingPreview?.warnings?.length ? (
                            <span className="rounded-full border border-glow-warning/30 bg-glow-warning/10 px-2.5 py-1 text-[10px] text-glow-warning">
                              {groundingPreview.warnings.length} caveat{groundingPreview.warnings.length > 1 ? 's' : ''}
                            </span>
                          ) : null}
                        </span>
                        <ChevronRight
                          className={cn(
                            'h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200',
                            isGroundingPreviewOpen && 'rotate-90 text-primary',
                          )}
                        />
                      </div>
                    </div>
                  </button>
                </CollapsibleTrigger>

                <CollapsibleContent className="space-y-3">
                  <div className="rounded-2xl border border-border/50 bg-background/35 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.02)]">
                    {previewQuery.isLoading ? (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Building preview from selected evidence...
                      </div>
                    ) : groundingPreview ? (
                      <div className="space-y-3">
                        <div className="grid gap-3 xl:grid-cols-12">
                          <div className="rounded-xl border border-border/40 bg-background/60 p-4 xl:col-span-3">
                            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Quick signal check</div>
                            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                              Confirm the workflow is using the intended documents, enough source blocks and the expected evidence themes before execution.
                            </p>
                          </div>
                          <div className="rounded-xl border border-border/40 bg-background/60 p-4 xl:col-span-2">
                            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Selected docs</div>
                            <div className="mt-2 text-lg font-semibold text-foreground">{groundingPreview.document_ids.length}</div>
                          </div>
                          <div className="rounded-xl border border-border/40 bg-background/60 p-4 xl:col-span-2">
                            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Source blocks</div>
                            <div className="mt-2 text-lg font-semibold text-foreground">{groundingPreview.source_block_count}</div>
                          </div>
                          <div className="rounded-xl border border-border/40 bg-background/60 p-4 xl:col-span-2">
                            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Context size</div>
                            <div className="mt-2 text-lg font-semibold text-foreground">{groundingPreview.context_chars.toLocaleString()}</div>
                            <div className="mt-1 text-[10px] text-muted-foreground">characters</div>
                          </div>
                          <div
                            className={cn(
                              'rounded-xl border p-4 xl:col-span-3',
                              groundingPreview.warnings?.length
                                ? 'border-glow-warning/30 bg-glow-warning/10'
                                : 'border-border/40 bg-background/60',
                            )}
                          >
                            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                              <AlertTriangle className={cn('h-3.5 w-3.5', groundingPreview.warnings?.length ? 'text-glow-warning' : 'text-primary')} />
                              {groundingPreview.warnings?.length ? 'Context caveats' : 'Preview status'}
                            </div>
                            {groundingPreview.warnings?.length ? (
                              <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-muted-foreground">
                                {groundingPreview.warnings.slice(0, 2).map((warning) => (
                                  <li key={warning}>• {warning}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                                No immediate caveats detected for the current grounded selection.
                              </p>
                            )}
                          </div>
                        </div>

                        {groundingPreviewBlocks.slice(0, 2).length ? (
                          <div className="grid gap-3 xl:grid-cols-2">
                            {groundingPreviewBlocks.slice(0, 2).map((block) => (
                              <div key={`${block.source}-${block.excerpt.slice(0, 24)}`} className="rounded-xl border border-border/40 bg-background/60 p-4">
                                <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                                  <FileText className="h-3.5 w-3.5 text-primary" />
                                  Context highlight
                                </div>
                                <div className="mt-2 text-[10px] font-medium uppercase tracking-wide text-primary">{block.source}</div>
                                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{truncatePreviewText(block.excerpt, 280)}</p>
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">Select at least one indexed document to preview the grounded context.</p>
                    )}
                  </div>
                </CollapsibleContent>
              </div>
            </Collapsible>
          </GlassCard>
        </>
      )}

      <motion.div data-tour="action-plan-status-strip" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Open', value: summary.open, color: 'text-primary' },
          { label: 'Approved / WIP', value: summary.in_progress, color: 'text-glow-warning' },
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
        <GlassCard className="mb-6" delay={0.12} data-tour="action-plan-critical-path">
          <div className="flex items-start justify-between gap-3 mb-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-glow-warning mt-0.5" />
              <div>
                <h3 className="text-sm font-medium text-foreground">Critical Path · Top Operational Risks</h3>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Highest-impact unblockers selected from the action plan, not the full list of high-priority tasks.
                </p>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            {criticalPath.slice(0, 3).map((item, index) => (
              <div key={item.id} className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg bg-secondary/20">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-[10px] font-bold text-muted-foreground w-4">{index + 1}</span>
                  <SeverityBadge severity={item.priority} />
                  <span className="text-xs text-foreground whitespace-normal break-words" style={{ display: 'block', overflow: 'visible', whiteSpace: 'normal', WebkitLineClamp: 'unset' }}>{actionItemFullTitle(item, workflowResponse)}</span>
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
        <div className="inline-flex w-fit">
          <TabsList className="mb-4 border border-border/50 bg-secondary/30" data-tour="action-plan-work-views">
            <TabsTrigger value="board" className="text-xs data-[state=active]:bg-secondary">Board</TabsTrigger>
            <TabsTrigger value="table" className="text-xs data-[state=active]:bg-secondary">Table</TabsTrigger>
            <TabsTrigger value="timeline" className="text-xs data-[state=active]:bg-secondary">Timeline</TabsTrigger>
            <TabsTrigger value="evidence" className="text-xs data-[state=active]:bg-secondary">Evidence Gaps</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="board" className="mt-0" data-tour="action-plan-board">
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
                        <h4 className="text-xs font-medium text-foreground mb-2 leading-relaxed whitespace-normal break-words" style={{ display: 'block', overflow: 'visible', whiteSpace: 'normal', WebkitLineClamp: 'unset' }}>{actionItemFullTitle(item, workflowResponse)}</h4>
                        {actionItemNarrative(item, workflowResponse) ? (
                          <p className="text-[10px] text-muted-foreground leading-relaxed min-h-8">{actionItemNarrative(item, workflowResponse)}</p>
                        ) : null}
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
                        <div className="font-medium leading-relaxed whitespace-normal break-words" style={{ display: 'block', overflow: 'visible', whiteSpace: 'normal', WebkitLineClamp: 'unset' }}>{actionItemFullTitle(item, workflowResponse)}</div>
                        {actionItemNarrative(item, workflowResponse) ? (
                          <div className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{actionItemNarrative(item, workflowResponse)}</div>
                        ) : null}
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
                        <span className="text-xs font-medium text-foreground whitespace-normal break-words" style={{ display: 'block', overflow: 'visible', whiteSpace: 'normal', WebkitLineClamp: 'unset' }}>{actionItemFullTitle(item, workflowResponse)}</span>
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


      <div className="grid xl:grid-cols-[1.2fr_0.8fr] gap-4 mt-6" data-tour="action-plan-run-summary">
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
                    Action status is mapped to Trello lists as Open → Open, Approved / WIP → Approved, Blocked/Needs review → Review, Done → Done.
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

      <div className="mt-6" data-tour="action-plan-publish" data-testid="workflow-publish-actions-surface" data-workflow="action-plan">
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
            actions: items.map((item) => ({
              title: item.title,
              detail: actionItemNotionLine(item),
              summary: actionItemNarrative(item, workflowResponse),
              owner: item.owner,
              due_date: item.due_date,
              priority: item.priority,
              status: item.status,
            })),
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
