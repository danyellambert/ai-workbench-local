import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Sparkles, AlertTriangle, Play, ArrowLeftRight, CheckCircle2, Shield, Loader2, AlertCircle, ExternalLink } from 'lucide-react';
import { PageHeader, GlassCard, StatusPill, WorkflowProgressHeader } from '@/components/shared/ui-components';
import { WorkflowPublishActions } from '@/components/product/WorkflowPublishActions';
import {
  buildProductArtifactUrl,
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  runProductWorkflow,
  type ProductDocumentLibraryEntry,
  type ProductPolicyComparisonDiff,
  type ProductPublishNotionResponse,
  type ProductPublishTrelloResponse,
  type ProductRunWorkflowResponse,
  type ProductWorkflowArtifact,
} from '@/lib/product-api';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from '@/components/ui/sonner';
import { useAppStore } from '@/lib/store';

const impactColors = {
  breaking: 'bg-glow-error/10 text-glow-error border-glow-error/20',
  significant: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
  minor: 'bg-muted text-muted-foreground border-border',
};

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

function getDefaultSecondaryDocument(
  documents: ProductDocumentLibraryEntry[],
  primaryId: string,
): string {
  return documents.find((document) => document.document_id !== primaryId)?.document_id || '';
}

export default function ComparisonPage() {
  const queryClient = useQueryClient();
  const showSourceBadges = useAppStore((state) => state.operatorPreferences.showSourceBadges);
  const [selectedDocumentAId, setSelectedDocumentAId] = useState('');
  const [selectedDocumentBId, setSelectedDocumentBId] = useState('');
  const [workflowResponse, setWorkflowResponse] = useState<ProductRunWorkflowResponse | null>(null);
  const [generatedArtifacts, setGeneratedArtifacts] = useState<ProductWorkflowArtifact[]>([]);
  const [deckExportState, setDeckExportState] = useState<{ status: string; message: string } | null>(null);
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
    if (!availableDocuments.length) {
      setSelectedDocumentAId('');
      setSelectedDocumentBId('');
      return;
    }

    const fallbackPrimaryId = availableDocuments[0].document_id;
    const nextPrimaryId = availableDocuments.some((document) => document.document_id === selectedDocumentAId)
      ? selectedDocumentAId
      : fallbackPrimaryId;
    const fallbackSecondaryId = getDefaultSecondaryDocument(availableDocuments, nextPrimaryId);
    const nextSecondaryId =
      selectedDocumentBId &&
      selectedDocumentBId !== nextPrimaryId &&
      availableDocuments.some((document) => document.document_id === selectedDocumentBId)
        ? selectedDocumentBId
        : fallbackSecondaryId;

    if (nextPrimaryId !== selectedDocumentAId) setSelectedDocumentAId(nextPrimaryId);
    if (nextSecondaryId !== selectedDocumentBId) setSelectedDocumentBId(nextSecondaryId);
  }, [availableDocuments, selectedDocumentAId, selectedDocumentBId]);

  const selectedDocumentA = useMemo(
    () => availableDocuments.find((document) => document.document_id === selectedDocumentAId),
    [availableDocuments, selectedDocumentAId],
  );
  const selectedDocumentB = useMemo(
    () => availableDocuments.find((document) => document.document_id === selectedDocumentBId),
    [availableDocuments, selectedDocumentBId],
  );


  const previewQuery = useQuery({
    queryKey: ['product-policy-comparison-preview', selectedDocumentAId, selectedDocumentBId],
    enabled: Boolean(selectedDocumentAId && selectedDocumentBId && selectedDocumentAId !== selectedDocumentBId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryFn: () =>
      getProductGroundingPreview({
        workflowId: 'policy_contract_comparison',
        strategy: 'retrieval',
        documentIds: [selectedDocumentAId, selectedDocumentBId].filter(Boolean),
      }),
  });

  const runComparisonMutation = useMutation({
    mutationFn: () =>
      runProductWorkflow({
        workflow_id: 'policy_contract_comparison',
        document_ids: [selectedDocumentAId, selectedDocumentBId].filter(Boolean),
        context_strategy: 'retrieval',
        context_window_mode: 'auto',
        use_document_context: true,
      }),
    onSuccess: async (payload) => {
      setWorkflowResponse(payload);
      setGeneratedArtifacts([]);
      setDeckExportState(null);
      setTrelloPublishResult(null);
      setNotionPublishResult(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
      ]);
      toast.success('Policy comparison completed with grounded output.');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Policy comparison failed.');
    },
  });

  const generateDeckMutation = useMutation({
    mutationFn: () => {
      if (!workflowResponse?.result) {
        throw new Error('Run the policy comparison before generating the executive deck.');
      }
      return generateProductWorkflowDeck(workflowResponse.result, { runId: workflowResponse.run_id });
    },
    onSuccess: async (payload) => {
      setGeneratedArtifacts(payload.artifacts);
      const rawStatus = String(payload.export_result?.status || '').trim().toLowerCase();
      const hasArtifacts = payload.artifacts.length > 0;
      const normalizedStatus = hasArtifacts
        ? 'completed'
        : rawStatus.includes('fail')
          ? 'error'
          : rawStatus.includes('disabled') || rawStatus.includes('unavailable')
            ? 'warning'
            : 'warning';
      const statusMessage = hasArtifacts
        ? 'Comparison artifacts were generated and are ready for review.'
        : rawStatus.includes('disabled')
          ? 'Deck export is currently disabled in the Product API configuration. The workflow ran correctly, but no downloadable artifact was produced.'
          : rawStatus.includes('unavailable')
            ? 'The comparison deck renderer is unavailable right now. Check the presentation export service before retrying.'
            : 'The deck generation request completed, but no downloadable artifact was returned.';
      setDeckExportState({ status: normalizedStatus, message: statusMessage });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-artifacts'] }),
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      if (hasArtifacts) {
        toast.success('Policy comparison deck artifacts generated successfully.');
      } else {
        toast.error(statusMessage);
      }
    },
    onError: (error) => {
      setDeckExportState({ status: 'error', message: error instanceof Error ? error.message : 'Deck generation failed.' });
      toast.error(error instanceof Error ? error.message : 'Deck generation failed.');
    },
  });

  const comparisonView = workflowResponse?.comparison_view ?? null;
  const impactCounts = comparisonView?.executive_summary.counts ?? { breaking: 0, significant: 0, minor: 0 };
  const differences: ProductPolicyComparisonDiff[] = comparisonView?.differences ?? [];
  const mustFixItems = comparisonView?.must_fix_items ?? [];
  const negotiationPriorities = comparisonView?.negotiation_priorities ?? [];
  const allArtifacts = useMemo(
    () => dedupeArtifacts([...(comparisonView?.artifacts ?? []), ...generatedArtifacts]),
    [comparisonView?.artifacts, generatedArtifacts],
  );
  const groundingPreview = workflowResponse?.result?.grounding_preview ?? previewQuery.data?.preview ?? null;

  const runDisabled =
    !selectedDocumentAId ||
    !selectedDocumentBId ||
    selectedDocumentAId === selectedDocumentBId ||
    availableDocuments.length < 2 ||
    runComparisonMutation.isPending;

  const comparisonSteps = comparisonView?.run_state.steps ?? [
    { key: 'select', label: 'Select', status: selectedDocumentAId && selectedDocumentBId ? 'completed' : 'pending' },
    { key: 'ground', label: 'Ground', status: workflowResponse?.result?.grounding_preview ? 'completed' : 'pending' },
    { key: 'analyze', label: 'Analyze', status: runComparisonMutation.isPending ? 'running' : workflowResponse?.result ? (workflowResponse.result.status === 'error' ? 'error' : 'completed') : 'pending' },
    { key: 'review', label: 'Review', status: differences.length > 0 ? 'completed' : 'pending' },
    { key: 'export', label: 'Export', status: generateDeckMutation.isPending ? 'running' : allArtifacts.length > 0 ? 'completed' : 'pending' },
  ];

  const handleDocumentAChange = (documentId: string) => {
    setSelectedDocumentAId(documentId);
    if (documentId === selectedDocumentBId) {
      setSelectedDocumentBId(getDefaultSecondaryDocument(availableDocuments, documentId));
    }
    setWorkflowResponse(null);
    setGeneratedArtifacts([]);
    setDeckExportState(null);
    setTrelloPublishResult(null);
    setNotionPublishResult(null);
  };

  const handleDocumentBChange = (documentId: string) => {
    setSelectedDocumentBId(documentId);
    setWorkflowResponse(null);
    setGeneratedArtifacts([]);
    setDeckExportState(null);
    setTrelloPublishResult(null);
    setNotionPublishResult(null);
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
      <PageHeader title="Policy & Contract Comparison" description="Compare two documents side by side and surface grounded deltas.">
        <Button
          className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs"
          disabled={runDisabled}
          onClick={() => runComparisonMutation.mutate()}
        >
          {runComparisonMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-2" />}
          {runComparisonMutation.isPending ? 'Running Comparison' : 'Run Comparison'}
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

      {documentsError && (
        <div className="glass rounded-xl p-4 mb-6 border border-glow-warning/20 text-xs text-glow-warning flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          Product API unavailable. The comparison surface cannot load the document library right now.
        </div>
      )}

      {!documentsLoading && availableDocuments.length < 2 && (
        <div className="glass rounded-xl p-4 mb-6 border border-glow-warning/20 text-xs text-glow-warning flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          At least two indexed documents are required to run a grounded policy comparison.
        </div>
      )}
      <WorkflowProgressHeader
        steps={comparisonSteps}
        title="Workflow progress"
        description="Track how the grounded comparison moves from document selection to export-ready outputs."
      />


      {/* Document Selection */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="glass rounded-xl p-5 mb-6">
        <div className="grid md:grid-cols-2 gap-4 items-end">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Document A</label>
            <Select value={selectedDocumentAId} onValueChange={handleDocumentAChange}>
              <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
              <SelectContent>
                {availableDocuments.map(document => (
                  <SelectItem key={document.document_id} value={document.document_id} className="text-xs">{document.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Document B</label>
            <Select value={selectedDocumentBId} onValueChange={handleDocumentBChange}>
              <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue /></SelectTrigger>
              <SelectContent>
                {availableDocuments.map(document => (
                  <SelectItem key={document.document_id} value={document.document_id} className="text-xs">{document.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
          <div className="mt-4 border-t border-border/40 pt-4">
            <div className="flex items-center gap-2 mb-2">
              <ArrowLeftRight className="w-4 h-4 text-primary" />
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Grounding Preview</h3>
            </div>
            <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Selected docs</div>
                  <div className="mt-1 text-sm font-medium text-foreground">{[selectedDocumentAId, selectedDocumentBId].filter(Boolean).length}</div>
                </div>
                <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Source blocks</div>
                  <div className="mt-1 text-sm font-medium text-foreground">{groundingPreview?.source_block_count ?? 0}</div>
                </div>
                <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Context size</div>
                  <div className="mt-1 text-sm font-medium text-foreground">{(groundingPreview?.context_chars ?? 0).toLocaleString()} chars</div>
                </div>
              </div>
              <div className="rounded-lg bg-secondary/20 px-3 py-3">
                <p className="text-xs text-muted-foreground leading-relaxed line-clamp-4">
                  {previewQuery.isLoading
                    ? 'Loading comparison grounding preview...'
                    : groundingPreview?.preview_text || 'Select two different indexed documents to preview the grounded comparison context before running the workflow.'}
                </p>
              </div>
            </div>
          </div>
      </motion.div>

      {/* Executive Summary */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <GlassCard className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Executive Summary</h3>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed mb-4">
            {comparisonView ? (
              <>
                Analysis between <span className="text-foreground">{comparisonView.executive_summary.documents[0] || selectedDocumentA?.name || 'Document A'}</span> and <span className="text-foreground">{comparisonView.executive_summary.documents[1] || selectedDocumentB?.name || 'Document B'}</span> reveals
                <span className="text-glow-error font-medium"> {impactCounts.breaking} breaking</span> and
                <span className="text-glow-warning font-medium"> {impactCounts.significant} significant</span> differences requiring attention. {comparisonView.executive_summary.narrative}
              </>
            ) : (
              'Select two indexed documents and run the comparison to populate grounded deltas, must-fix items and negotiation priorities.'
            )}
          </p>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-glow-error/20 border border-glow-error/30" />
              <span className="text-muted-foreground">{impactCounts.breaking} Breaking</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-glow-warning/20 border border-glow-warning/30" />
              <span className="text-muted-foreground">{impactCounts.significant} Significant</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded bg-muted border border-border" />
              <span className="text-muted-foreground">{impactCounts.minor} Minor</span>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {/* Must-Fix & Negotiation Priorities */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.17 }}
        className="grid md:grid-cols-2 gap-4 mb-6">
        <GlassCard>
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-glow-error" />
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Must-Fix Before Approval</h4>
          </div>
          <div className="space-y-2">
            {mustFixItems.length > 0 ? mustFixItems.map((item, index) => (
              <div key={`${item.title}-${index}`} className="flex items-start gap-2 text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-glow-error mt-1.5 shrink-0" />
                <div>
                  <p className="text-foreground font-medium">{item.title}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{item.detail}</p>
                </div>
              </div>
            )) : <p className="text-xs text-muted-foreground">Run the grounded comparison to identify the highest-priority blockers before approval.</p>}
          </div>
        </GlassCard>
        <GlassCard>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Negotiation Priorities</h4>
          </div>
          <div className="space-y-2 text-xs text-muted-foreground leading-relaxed">
            {negotiationPriorities.length > 0 ? negotiationPriorities.map((priority, index) => (
              <p key={priority}><span className="text-foreground font-medium">{index + 1}.</span> {priority}</p>
            )) : <p>Negotiation priorities will appear here after the grounded comparison runs.</p>}
          </div>
        </GlassCard>
      </motion.div>

      {/* Comparison Diffs */}
      <div className="space-y-3">
        {differences.length > 0 ? differences.map((diff, i) => (
          <motion.div key={diff.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.06 }}
            className="glass rounded-xl p-5 hover:border-primary/20 transition-all duration-300">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-medium text-foreground">{diff.clause}</h4>
                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium capitalize ${impactColors[diff.impact]}`}>{diff.impact}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground">{diff.category}</span>
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4 mb-3">
              <div className="bg-glow-error/5 border border-glow-error/10 rounded-lg p-3">
                <span className="text-[10px] uppercase tracking-wider text-glow-error/60 font-medium block mb-1">{diff.doc_a_label}</span>
                <p className="text-xs text-foreground/80 leading-relaxed">{diff.doc_a_text}</p>
              </div>
              <div className="bg-glow-success/5 border border-glow-success/10 rounded-lg p-3">
                <span className="text-[10px] uppercase tracking-wider text-glow-success/60 font-medium block mb-1">{diff.doc_b_label}</span>
                <p className="text-xs text-foreground/80 leading-relaxed">{diff.doc_b_text}</p>
              </div>
            </div>
            <div className="flex items-start gap-2 bg-secondary/20 rounded-lg p-3">
              <ArrowLeftRight className="w-3.5 h-3.5 text-primary mt-0.5 shrink-0" />
              <p className="text-xs text-muted-foreground leading-relaxed">{diff.business_impact}</p>
            </div>
            {showSourceBadges && diff.evidence.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/30 space-y-1">
                {diff.evidence.map((item) => (
                  <p key={item} className="text-[10px] text-muted-foreground">• {item}</p>
                ))}
              </div>
            )}
          </motion.div>
        )) : (
          <GlassCard>
            <div className="text-xs text-muted-foreground">Run the comparison to populate grounded differences, category tags and bilateral document evidence.</div>
          </GlassCard>
        )}
      </div>

      {/* Recommendation */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
        className="mt-6">
        <GlassCard>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Recommendation</h3>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed mb-3">
            {comparisonView ? (
              comparisonView.recommendation.summary
            ) : (
              'Run the grounded comparison to generate a decision-ready recommendation and executive handoff note.'
            )}
          </p>
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground pt-2 border-t border-border/30">
            <span><span className="text-foreground font-medium">Handoff:</span> {comparisonView?.recommendation.handoff || 'Human review pending'}</span>
            <span>·</span>
            <span><span className="text-foreground font-medium">Artifact:</span> {comparisonView?.recommendation.artifact_label || 'Generate the comparison deck to create a local artifact.'}</span>
          </div>
        </GlassCard>
      </motion.div>

      <div className="grid lg:grid-cols-2 gap-4 mt-6">
        <GlassCard>
          <h3 className="text-sm font-medium text-foreground mb-3">Watchouts</h3>
          <div className="space-y-2 text-xs text-muted-foreground">
            {(comparisonView?.watchouts ?? []).length > 0 ? (comparisonView?.watchouts ?? []).map((item) => (
              <p key={item}>• {item}</p>
            )) : <p>Watchouts will appear here after the workflow runs.</p>}
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="text-sm font-medium text-foreground mb-3">Generated Artifacts</h3>
          {(trelloPublishResult || notionPublishResult) ? (
            <div className="mb-4 grid gap-3 md:grid-cols-2">
              {trelloPublishResult ? (
                <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-medium text-foreground">Trello publish</p>
                      <p className="mt-1 text-[10px] text-muted-foreground">{trelloPublishResult.message || 'The current comparison was sent to Trello.'}</p>
                    </div>
                    <StatusPill status={trelloPublishResult.status || 'completed'} />
                  </div>
                </div>
              ) : null}
              {notionPublishResult ? (
                <div className="rounded-lg border border-border/40 bg-secondary/20 px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-medium text-foreground">Notion memo</p>
                      <p className="mt-1 text-[10px] text-muted-foreground">{notionPublishResult.message || notionPublishResult.page_title || 'The current comparison was published to Notion.'}</p>
                    </div>
                    <StatusPill status={notionPublishResult.status || 'completed'} />
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
          {deckExportState && (
            <div className="mb-3 rounded-lg bg-secondary/20 border border-border/40 px-3 py-2">
              <div className="flex items-center gap-2 mb-1">
                <StatusPill status={deckExportState.status} />
                <span className="text-xs font-medium text-foreground">Deck export status</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">{deckExportState.message}</p>
            </div>
          )}
          <div className="space-y-2">
            {allArtifacts.length > 0 ? allArtifacts.map((artifact) => (
              <div key={`${artifact.artifact_type}-${artifact.path || artifact.label}`} className="flex items-center justify-between py-2 px-3 rounded-lg bg-secondary/20 hover:bg-secondary/30 transition-colors">
                <div className="flex items-center gap-2 min-w-0">
                  <StatusPill status={artifact.available ? 'ready' : 'pending'} />
                  <div className="min-w-0">
                    <span className="block text-xs text-foreground truncate">{artifact.download_name || artifact.label}</span>
                    <span className="block text-[10px] text-muted-foreground truncate">{artifact.artifact_type}{artifact.path ? ` • ${artifact.path}` : ''}</span>
                  </div>
                </div>
                <Button variant="ghost" size="sm" className="h-7 text-[10px] text-muted-foreground hover:text-foreground" disabled={!artifact.available || !artifact.path} onClick={() => handleOpenArtifact(artifact)}>
                  Open <ExternalLink className="w-3 h-3 ml-1" />
                </Button>
              </div>
            )) : <div className="text-xs text-muted-foreground">Run the workflow and generate the deck to populate comparison artifacts.</div>}
          </div>
        </GlassCard>
      </div>

      <div className="mt-6" data-testid="workflow-publish-actions-surface" data-workflow="policy-comparison">
        <WorkflowPublishActions
          workflowId="policy_contract_comparison"
          result={workflowResponse?.result ?? null}
          runId={workflowResponse?.run_id ?? null}
          title="Publish outputs"
          description="After reviewing the comparison summary, deltas and artifacts, preview the remediation cards or Notion memo before publishing."
          notionPreviewPayload={{
            product_api_base_url: PRODUCT_API_BASE_URL,
            title: comparisonView?.executive_summary.documents?.join(' vs ') || 'Policy comparison',
            summary: comparisonView?.executive_summary.narrative || workflowResponse?.result.summary,
            recommendation: comparisonView?.recommendation.summary || workflowResponse?.result.recommendation,
            must_fix_items: mustFixItems,
            negotiation_priorities: negotiationPriorities,
            differences: differences.map((item) => ({
              clause: item.clause,
              impact: item.impact,
              business_impact: item.business_impact,
            })),
            documents: comparisonView?.compared_documents || [selectedDocumentA?.name, selectedDocumentB?.name].filter(Boolean),
            primary_documents: [selectedDocumentA?.name, selectedDocumentB?.name].filter(Boolean),
            source_document_name: selectedDocumentA?.name || null,
            source_document_title: selectedDocumentA?.name || null,
            source_document_filename: selectedDocumentA?.name || null,
            source_document_category: 'comparison',
          }}
          onTrelloPublished={setTrelloPublishResult}
          onNotionPublished={setNotionPublishResult}
        />
      </div>

    </motion.div>
  );
}
