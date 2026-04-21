import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  UserCheck,
  Sparkles,
  AlertTriangle,
  Briefcase,
  GraduationCap,
  CheckCircle2,
  Target,
  Search,
  ShieldAlert,
  Loader2,
  FileText,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';

import { WorkflowPublishActions } from '@/components/product/WorkflowPublishActions';
import { PageHeader, GlassCard, StatusPill, WorkflowProgressHeader } from '@/components/shared/ui-components';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from '@/components/ui/sonner';
import {
  buildProductArtifactUrl,
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  runProductWorkflow,
  type ProductDocumentLibraryEntry,
  type ProductResultSections,
  type ProductPublishNotionResponse,
  type ProductPublishTrelloResponse,
  type ProductRunWorkflowResponse,
  type ProductWorkflowArtifact,
} from '@/lib/product-api';

const workflowSteps = [
  { key: 'select', label: 'Select' },
  { key: 'ground', label: 'Ground' },
  { key: 'analyze', label: 'Analyze' },
  { key: 'review', label: 'Review' },
  { key: 'export', label: 'Export' },
] as const;

function isCandidateLikeDocument(document: ProductDocumentLibraryEntry): boolean {
  const haystack = `${document.name} ${document.file_type || ''} ${document.loader_strategy_label || ''}`.toLowerCase();
  return /(cv|resume|candidate|curriculum|hiring)/.test(haystack);
}

function formatDate(value?: string | null): string {
  if (!value) return 'n/a';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function buildInitials(name?: string | null): string {
  const tokens = String(name || '')
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean)
    .slice(0, 2);
  if (!tokens.length) return 'CV';
  return tokens.map((token) => token[0]?.toUpperCase() || '').join('');
}

function deriveScore(response: ProductRunWorkflowResponse | null, sections: ProductResultSections | null): number {
  const structured = response?.result?.structured_result;
  const confidenceSeed =
    (typeof structured?.overall_confidence === 'number' ? structured.overall_confidence : null) ??
    (typeof structured?.quality_score === 'number' ? structured.quality_score : null);
  if (typeof confidenceSeed === 'number') {
    return Math.max(1, Math.min(99, Math.round(confidenceSeed * 100)));
  }
  const strengthCount = sections?.strengths.length || 0;
  const watchoutCount = sections?.watchouts.length || 0;
  return Math.max(15, Math.min(95, 55 + strengthCount * 8 - watchoutCount * 4));
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

function getTable(sections: ProductResultSections | null, title: string) {
  return sections?.tables.find((table) => table.title === title) || null;
}

function isMeaningfulCell(value: unknown): boolean {
  const normalized = String(value ?? '').trim().toLowerCase();
  return Boolean(normalized && normalized !== '-' && normalized !== 'n/a' && normalized !== 'na' && normalized !== 'null' && normalized !== 'undefined');
}

function dedupeRows(rows: Array<Array<unknown>>): Array<Array<unknown>> {
  const seen = new Set<string>();
  return rows.filter((row) => {
    const key = row.map((cell) => String(cell ?? '').trim().toLowerCase()).join('|');
    if (!key) return false;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeExperienceRows(rows: Array<Array<unknown>>): Array<Array<unknown>> {
  return dedupeRows(rows).filter((row) => isMeaningfulCell(row[0]) || isMeaningfulCell(row[1]) || isMeaningfulCell(row[3]));
}

function normalizeEvidenceRows(rows: Array<Array<unknown>>): Array<Array<unknown>> {
  return dedupeRows(rows).filter((row) => row.some((cell) => isMeaningfulCell(cell)));
}

function getStatusCopy(response: ProductRunWorkflowResponse | null): { label: string; detail: string } {
  const status = String(response?.result?.status || '').toLowerCase();
  if (status === 'completed') {
    return {
      label: response?.result?.recommendation || 'Grounded review ready',
      detail: 'The candidate review ran live against the selected document and the structured sections below come from the backend response.',
    };
  }
  if (status === 'warning') {
    return {
      label: response?.result?.recommendation || 'Needs interview validation',
      detail: 'The candidate review completed, but the backend surfaced watchouts that should be validated in interview before making a hiring call.',
    };
  }
  if (status === 'error') {
    return {
      label: 'Run failed',
      detail: 'The backend could not complete the candidate review. Check the error banner and document index before retrying.',
    };
  }
  return {
    label: 'Awaiting live run',
    detail: 'Select a CV-like document and run the backend workflow to replace placeholders with grounded hiring signals.',
  };
}

export default function CandidateReviewPage() {
  const queryClient = useQueryClient();
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const candidateReviewBrief = 'Evaluate this CV for a senior AI engineer role and highlight strengths, watchouts, seniority signals and interview focus areas.';
  const [workflowResponse, setWorkflowResponse] = useState<ProductRunWorkflowResponse | null>(null);
  const [generatedArtifacts, setGeneratedArtifacts] = useState<ProductWorkflowArtifact[]>([]);
  const [trelloPublishResult, setTrelloPublishResult] = useState<ProductPublishTrelloResponse | null>(null);
  const [notionPublishResult, setNotionPublishResult] = useState<ProductPublishNotionResponse | null>(null);

  const documentLibraryQuery = useQuery({
    queryKey: ['product-document-library'],
    queryFn: getProductDocumentLibrary,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const availableDocuments = useMemo(
    () => (documentLibraryQuery.data?.documents ?? []).filter((document) => document.status === 'indexed' || document.status === 'warning'),
    [documentLibraryQuery.data?.documents],
  );


  const preferredCandidateDocuments = useMemo(
    () => availableDocuments.filter(isCandidateLikeDocument),
    [availableDocuments],
  );

  const selectableDocuments = preferredCandidateDocuments.length ? preferredCandidateDocuments : availableDocuments;
  const hasDedicatedCandidateCorpus = preferredCandidateDocuments.length > 0;

  useEffect(() => {
    if (!selectableDocuments.length) {
      setSelectedDocumentId('');
      return;
    }
    if (!selectedDocumentId || !selectableDocuments.some((document) => document.document_id === selectedDocumentId)) {
      setSelectedDocumentId(selectableDocuments[0].document_id);
    }
  }, [selectedDocumentId, selectableDocuments]);

  const selectedDocument = selectableDocuments.find((document) => document.document_id === selectedDocumentId);

  const previewQuery = useQuery({
    queryKey: ['candidate-review-preview', selectedDocumentId],
    enabled: Boolean(selectedDocumentId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryFn: () =>
      getProductGroundingPreview({
        workflowId: 'candidate_review',
        strategy: 'document_scan',
        documentIds: selectedDocumentId ? [selectedDocumentId] : [],
      }),
  });

  const runReviewMutation = useMutation({
    mutationFn: () =>
      runProductWorkflow({
        workflow_id: 'candidate_review',
        document_ids: selectedDocumentId ? [selectedDocumentId] : [],
        input_text: candidateReviewBrief,
        context_strategy: 'document_scan',
        context_window_mode: 'auto',
        use_document_context: true,
      }),
    onSuccess: async (payload) => {
      setWorkflowResponse(payload);
      setGeneratedArtifacts([]);
      setTrelloPublishResult(null);
      setNotionPublishResult(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      toast.success('Candidate review completed with grounded backend output.');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Candidate review failed.');
    },
  });

  const generateDeckMutation = useMutation({
    mutationFn: () => {
      if (!workflowResponse?.result) {
        throw new Error('Run the candidate review before generating the executive deck.');
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
      toast.success('Candidate review deck artifacts generated successfully.');
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Candidate review deck generation failed.');
    },
  });

  const sections = workflowResponse?.result_sections ?? null;
  const statusCopy = getStatusCopy(workflowResponse);
  const candidateProfile = sections?.candidate_profile ?? null;
  const score = deriveScore(workflowResponse, sections);
  const evidenceRows = useMemo(() => normalizeEvidenceRows(sections?.evidence_highlights ?? []), [sections?.evidence_highlights]);
  const experienceTable = getTable(sections, 'Experience highlights');
  const experienceRows = useMemo(() => normalizeExperienceRows(experienceTable?.rows ?? []), [experienceTable?.rows]);
  const evidenceTable = getTable(sections, 'Evidence highlights');
  const evidenceTableRows = useMemo(() => normalizeEvidenceRows(evidenceTable?.rows ?? []), [evidenceTable?.rows]);
  const allArtifacts = useMemo(
    () => dedupeArtifacts([...(sections?.artifacts ?? []), ...generatedArtifacts]),
    [generatedArtifacts, sections?.artifacts],
  );
  const selectedDocumentDate = formatDate(selectedDocument?.indexed_at || null);
  const preview = workflowResponse?.result?.grounding_preview ?? previewQuery.data?.preview ?? null;

  const stepStatuses = useMemo(() => workflowSteps.map((step) => {
    let status = 'pending';
    if (step.key === 'select' && selectedDocumentId) status = 'completed';
    if (step.key === 'ground' && preview) status = 'completed';
    if (step.key === 'analyze' && runReviewMutation.isPending) status = 'running';
    if (step.key === 'analyze' && workflowResponse?.result) status = workflowResponse.result.status === 'error' ? 'error' : 'completed';
    if (step.key === 'review' && sections) status = 'completed';
    if (step.key === 'export' && generateDeckMutation.isPending) status = 'running';
    if (step.key === 'export' && allArtifacts.length > 0) status = 'completed';
    return { ...step, status };
  }), [allArtifacts.length, generateDeckMutation.isPending, preview, runReviewMutation.isPending, sections, selectedDocumentId, workflowResponse?.result]);


  const handleOpenArtifact = (artifact: ProductWorkflowArtifact) => {
    if (!artifact.path) {
      toast.error(`${artifact.label} is registered, but no local path is available yet.`);
      return;
    }
    window.open(buildProductArtifactUrl(artifact.path), '_blank', 'noopener,noreferrer');
  };

  return (
    <motion.div data-testid="candidate-review-page" className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Candidate Review" description="Review a candidate profile with grounded strengths, watchouts and interview focus.">
        <Button data-testid="candidate-review-run-button" className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs" disabled={!selectedDocumentId || runReviewMutation.isPending} onClick={() => runReviewMutation.mutate()}>
          {runReviewMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />} Run Candidate Review
        </Button>
        <Button data-testid="candidate-review-generate-deck-button" variant="outline" className="h-9 px-4 text-xs border-border/50" disabled={!workflowResponse?.result?.deck_available || generateDeckMutation.isPending} onClick={() => generateDeckMutation.mutate()}>
          {generateDeckMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />} Generate Deck
        </Button>
      </PageHeader>

      <WorkflowProgressHeader
        steps={stepStatuses}
        title="Workflow progress"
        description="Track how the candidate review moves from document selection to publish-ready outputs."
      />

      {(documentLibraryQuery.isError || previewQuery.isError) && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            Live candidate-review dependencies are partially unavailable. The page remains interactive, but some readiness signals may be degraded.
          </div>
        </GlassCard>
      )}

      {!documentLibraryQuery.isLoading && !selectableDocuments.length && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            No indexed documents are available yet. Use the Document Library to import or index a CV before running Candidate Review.
          </div>
        </GlassCard>
      )}

      {!documentLibraryQuery.isLoading && selectableDocuments.length > 0 && !hasDedicatedCandidateCorpus && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            The current corpus is live, but no CV-like filename was detected. Candidate Review can still run on the selected document, though a CV imported through the Document Library is preferred.
          </div>
        </GlassCard>
      )}

      <GlassCard className="mb-6">
        <div className="grid lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)] gap-4">
          <div>
            <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Candidate document</label>
            <Select value={selectedDocumentId} onValueChange={setSelectedDocumentId}>
              <SelectTrigger data-testid="candidate-review-document-trigger" className="h-9 text-xs bg-secondary/30"><SelectValue placeholder="Select a candidate document" /></SelectTrigger>
              <SelectContent>
                {selectableDocuments.map((document) => (
                  <SelectItem data-testid="candidate-review-document-option" data-document-name={document.name} key={document.document_id} value={document.document_id} className="text-xs">{document.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="mt-2 space-y-1 text-[11px] text-muted-foreground">
              <div data-testid="candidate-review-selected-document-date">Indexed: {selectedDocumentDate}</div>
              <div data-testid="candidate-review-selected-document-stats">Chunks: {selectedDocument?.chunk_count ?? 0} | Characters: {(selectedDocument?.char_count ?? 0).toLocaleString()}</div>
              <div data-testid="candidate-review-source-coverage">Source coverage: {preview?.source_block_count ?? 0} source block(s), {preview?.context_chars ?? 0} context chars</div>
            </div>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Grounding preview</label>
            <div className="rounded-lg border border-border/50 bg-secondary/20 px-3 py-3 min-h-[92px]">
              <div className="grid gap-2 sm:grid-cols-3">
                <div className="rounded-md bg-background/60 px-2 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Selected docs</div>
                  <div className="mt-1 text-sm font-medium text-foreground">{selectedDocumentId ? 1 : 0}</div>
                </div>
                <div className="rounded-md bg-background/60 px-2 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Source blocks</div>
                  <div className="mt-1 text-sm font-medium text-foreground">{preview?.source_block_count ?? 0}</div>
                </div>
                <div className="rounded-md bg-background/60 px-2 py-2">
                  <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Context size</div>
                  <div className="mt-1 text-sm font-medium text-foreground">{(preview?.context_chars ?? 0).toLocaleString()} chars</div>
                </div>
              </div>
              <p className="mt-3 text-[11px] text-muted-foreground leading-relaxed line-clamp-5">
                {preview?.preview_text
                  ? preview.preview_text
                  : 'Select a candidate document to preview the grounded CV context before running the workflow.'}
              </p>
            </div>
          </div>
        </div>
      </GlassCard>

      <div className="grid lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 space-y-4">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="glass rounded-xl p-6 text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl font-bold text-gradient-primary">{buildInitials(candidateProfile?.name)}</span>
            </div>
            <h3 data-testid="candidate-review-candidate-name" className="text-lg font-semibold text-foreground">{candidateProfile?.name || selectedDocument?.name || 'Awaiting candidate run'}</h3>
            <p className="text-sm text-muted-foreground">{candidateProfile?.headline || 'Run the backend workflow to populate the live candidate profile.'}</p>
            <p className="text-xs text-muted-foreground mt-1">{candidateProfile?.location || 'Location will be derived from the structured CV output.'}</p>

            <div className="mt-5 pt-5 border-t border-border/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-muted-foreground">Overall confidence score</span>
                <span className="text-sm font-semibold text-primary">{score}/100</span>
              </div>
              <Progress value={score} className="h-2 bg-secondary" />
            </div>

            <div data-testid="candidate-review-status-panel" className="mt-4 bg-glow-success/5 border border-glow-success/20 rounded-lg p-3">
              <div className="flex items-center justify-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-glow-success" />
                <span className="text-sm font-semibold text-glow-success">{statusCopy.label}</span>
              </div>
              <p className="text-[10px] text-muted-foreground mt-1.5">{statusCopy.detail}</p>
            </div>

            <div data-testid="candidate-review-run-metadata" className="mt-4 space-y-2 text-left">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Briefcase className="w-3.5 h-3.5" />
                {experienceRows.length ? `${experienceRows.length} structured experience row(s)` : 'Experience rows will populate after the live run.'}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <GraduationCap className="w-3.5 h-3.5" />
                {sections?.tables.some((table) => table.title === 'Education snapshot') ? 'Education snapshot available' : 'Education snapshot will appear when available'}
              </div>
            </div>
          </motion.div>

          <GlassCard delay={0.16}>
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="w-4 h-4 text-glow-warning" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Decision Risks</h4>
            </div>
            <div className="space-y-2">
              {(sections?.watchouts.length ? sections.watchouts : ['Run the candidate workflow to surface live watchouts and interview risks.']).map((watchout) => (
                <div key={watchout} className="text-xs">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-glow-warning shrink-0" />
                    <span className="text-foreground font-medium">{watchout}</span>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard delay={0.2}>
            <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-3">Grounded Signals</h4>
            <div className="space-y-2">
              {evidenceRows.length ? (
                evidenceRows.map((row) => (
                  <div key={`${row[0]}-${row[1]}`} className="rounded-lg bg-secondary/20 px-3 py-2">
                    <p className="text-xs text-foreground font-medium">{String(row[0] || 'Signal')}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{String(row[1] || '-')} · {String(row[2] || '-')}</p>
                    <p className="text-[10px] text-muted-foreground/80 mt-1">{String(row[3] || '')}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">Grounded evidence signals will appear here after the candidate workflow runs.</p>
              )}
            </div>
          </GlassCard>
        </div>

        <div className="lg:col-span-8 space-y-4">
          <GlassCard delay={0.1}>
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-primary" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Interview Focus Areas</h4>
            </div>
            <div className="space-y-2">
              {(sections?.next_steps.length ? sections.next_steps : ['Run the candidate review to generate live interview focus areas.']).map((step, index) => (
                <div key={step} className="flex items-start gap-3 py-2 px-3 rounded-lg bg-secondary/20">
                  <span className="text-[10px] font-bold text-muted-foreground w-4 mt-0.5">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <span className="text-xs font-medium text-foreground">{step}</span>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard delay={0.14}>
            <div className="flex items-center gap-2 mb-4">
              <Search className="w-4 h-4 text-primary" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Experience Highlights</h4>
            </div>
            <div className="space-y-4">
              {experienceRows.length ? (
                experienceRows.map((row, index) => (
                  <motion.div data-testid="candidate-review-experience-row" key={`experience-${index}-${String(row[0] || '-')}-${String(row[1] || '-')}`} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.18 + index * 0.05 }} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                        <Briefcase className="w-4 h-4 text-primary" />
                      </div>
                      {index < experienceRows.length - 1 && <div className="w-px flex-1 bg-border mt-2" />}
                    </div>
                    <div className="pb-4 flex-1">
                      <div className="flex items-center justify-between mb-1 gap-3">
                        <h5 className="text-sm font-medium text-foreground">{String(row[0] || '-')}</h5>
                        <span className="text-[10px] text-muted-foreground">{String(row[2] || '-')}</span>
                      </div>
                      <p className="text-xs text-primary/80 mb-2">{String(row[1] || '-')}</p>
                      <p className="text-xs text-muted-foreground leading-relaxed">{String(row[3] || '-')}</p>
                    </div>
                  </motion.div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">Run the candidate review to populate grounded experience rows from the selected CV.</p>
              )}
            </div>
          </GlassCard>

          <div className="grid md:grid-cols-2 gap-4">
            <GlassCard delay={0.18}>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-glow-success" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Strengths</h4>
              </div>
              <div className="space-y-2">
                {(sections?.strengths.length ? sections.strengths : ['Strengths will populate from the structured candidate payload after the live run.']).map((strength) => (
                  <p key={strength} className="text-xs text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-glow-success mt-1.5 shrink-0" />{strength}
                  </p>
                ))}
              </div>
            </GlassCard>

            <GlassCard delay={0.22}>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-glow-warning" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Watchouts</h4>
              </div>
              <div className="space-y-2">
                {(sections?.watchouts.length ? sections.watchouts : ['Watchouts will populate from the backend review status after the live run.']).map((watchout) => (
                  <p key={watchout} className="text-xs text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-glow-warning mt-1.5 shrink-0" />{watchout}
                  </p>
                ))}
              </div>
            </GlassCard>
          </div>

          {evidenceTable && evidenceTableRows.length > 0 && (
            <GlassCard delay={0.26}>
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-4 h-4 text-primary" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Evidence Table</h4>
              </div>
              <div className="overflow-x-auto rounded-lg border border-border/50">
                <table className="min-w-full text-left text-xs">
                  <thead className="bg-secondary/30">
                    <tr>
                      {evidenceTable.headers.map((header) => (
                        <th key={header} className="px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground">{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evidenceTableRows.map((row, rowIndex) => (
                      <tr key={`evidence-${rowIndex}-${String(row[0] || '-')}-${String(row[1] || '-')}`} className="border-t border-border/40">
                        {row.map((cell, index) => (
                          <td key={`evidence-cell-${rowIndex}-${index}`} className="px-3 py-2 text-muted-foreground">{String(cell ?? '-')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          )}

          <div data-testid="workflow-publish-actions-surface" data-workflow="candidate-review">
          <WorkflowPublishActions
            workflowId="candidate_review"
            result={workflowResponse?.result ?? null}
            runId={workflowResponse?.run_id ?? null}
            className="p-4"
            title="Publish outputs"
            description="Keep the hiring workflow focused: preview the interview tasks or the hiring brief before publishing them."
            notionPreviewPayload={{
              product_api_base_url: PRODUCT_API_BASE_URL,
              title: candidateProfile?.headline || candidateProfile?.name || selectedDocument?.name,
              candidate_name: candidateProfile?.name || selectedDocument?.name,
              candidate_headline: candidateProfile?.headline || null,
              candidate_location: candidateProfile?.location || null,
              summary: workflowResponse?.result.summary,
              recommendation: workflowResponse?.result.recommendation,
              strengths: sections?.strengths || [],
              watchouts: sections?.watchouts || [],
              highlights: sections?.strengths || [],
              next_steps: sections?.next_steps || [],
              interview_focus: sections?.watchouts || [],
              interview_questions: sections?.watchouts || [],
              experience_snapshot: experienceRows.map((row) => ({ role: String(row[0] || ''), company: String(row[1] || ''), tenure: String(row[2] || ''), impact: String(row[3] || '') })),
              evidence_rows: evidenceTableRows.map((row) => row.map((cell) => String(cell ?? ''))),
              documents: selectedDocument ? [selectedDocument.name] : [],
              primary_documents: selectedDocument ? [selectedDocument.name] : [],
              source_document_name: selectedDocument?.name || null,
              source_document_title: selectedDocument?.name || null,
              source_document_filename: selectedDocument?.name || null,
              source_document_id: selectedDocument?.document_id || null,
              source_document_relative_path: (selectedDocument as unknown as { relative_path?: string | null })?.relative_path || null,
              source_document_webdav_url: (selectedDocument as unknown as { webdav_url?: string | null })?.webdav_url || null,
              source_document_category: 'candidate',
            }}
            onTrelloPublished={setTrelloPublishResult}
            onNotionPublished={setNotionPublishResult}
          />
          </div>

          <GlassCard delay={0.3}>
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <h4 className="text-sm font-medium text-foreground">Artifacts</h4>
                <p className="text-xs text-muted-foreground">Generated deck artifacts and any structured exports registered by the live candidate-review flow.</p>
              </div>
              <StatusPill status={allArtifacts.length ? 'ready' : workflowResponse?.result ? workflowResponse.result.status : 'pending'} />
            </div>
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
                    <p className="mt-3 text-[10px] text-muted-foreground">Cards: {trelloPublishResult.created_card_count ?? trelloPublishResult.planned_card_count ?? 0}</p>
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
                    {notionPublishResult.page_url ? (
                      <Button variant="outline" size="sm" className="mt-3 h-7 text-[10px]" onClick={() => window.open(notionPublishResult.page_url || '', '_blank', 'noopener,noreferrer')}>
                        Open page <ExternalLink className="ml-1 h-3 w-3" />
                      </Button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}

            {allArtifacts.length ? (
              <div className="space-y-2">
                {allArtifacts.map((artifact) => (
                  <div key={`${artifact.artifact_type}-${artifact.path || artifact.label}`} className="flex items-center justify-between gap-3 rounded-lg border border-border/50 bg-secondary/15 px-3 py-2">
                    <div className="min-w-0">
                      <p className="text-xs text-foreground font-medium truncate">{artifact.label}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{artifact.download_name || artifact.path || artifact.artifact_type}</p>
                    </div>
                    <Button variant="outline" size="sm" className="h-7 text-[10px]" disabled={!artifact.available || !artifact.path} onClick={() => handleOpenArtifact(artifact)}>
                      Open <ExternalLink className="w-3 h-3 ml-1" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Run the workflow and generate the deck to register downloadable candidate-review artifacts here.</p>
            )}
            {workflowResponse?.run_id && (
              <p className="mt-3 text-[10px] text-muted-foreground">Linked run id: {workflowResponse.run_id}</p>
            )}
            {workflowResponse?.source_run?.id && (
              <p className="mt-1 text-[10px] text-muted-foreground">Rerun source: {workflowResponse.source_run.id}</p>
            )}
          </GlassCard>
        </div>
      </div>
    </motion.div>
  );
}
