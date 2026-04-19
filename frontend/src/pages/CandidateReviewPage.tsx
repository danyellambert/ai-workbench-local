import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  UserCheck,
  Sparkles,
  AlertTriangle,
  Briefcase,
  GraduationCap,
  CheckCircle2,
  Upload,
  Target,
  Search,
  ShieldAlert,
  Loader2,
  FileText,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';

import { PageHeader, GlassCard, StatusPill } from '@/components/shared/ui-components';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from '@/components/ui/sonner';
import {
  buildProductArtifactUrl,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  getProductUploadJob,
  runProductWorkflow,
  uploadProductDocuments,
  type ProductDocumentLibraryEntry,
  type ProductResultSections,
  type ProductRunWorkflowResponse,
  type ProductUploadDocumentsResponse,
  type ProductWorkflowArtifact,
} from '@/lib/product-api';

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
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [inputText, setInputText] = useState('Evaluate this CV for a senior AI engineer role and highlight strengths, watchouts, seniority signals and interview focus areas.');
  const [workflowResponse, setWorkflowResponse] = useState<ProductRunWorkflowResponse | null>(null);
  const [generatedArtifacts, setGeneratedArtifacts] = useState<ProductWorkflowArtifact[]>([]);
  const [activeUploadJobId, setActiveUploadJobId] = useState<string | null>(null);
  const [uploadJobSeed, setUploadJobSeed] = useState<ProductUploadDocumentsResponse | null>(null);

  const documentLibraryQuery = useQuery({
    queryKey: ['product-document-library'],
    queryFn: getProductDocumentLibrary,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const uploadJobQuery = useQuery({
    queryKey: ['product-upload-job', activeUploadJobId],
    queryFn: () => getProductUploadJob(activeUploadJobId || ''),
    enabled: Boolean(activeUploadJobId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchInterval: (query) => {
      const payload = query.state.data as ProductUploadDocumentsResponse | undefined;
      if (!payload) return 1000;
      return payload.status === 'completed' || payload.status === 'error' ? false : 1000;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: uploadProductDocuments,
    onSuccess: (payload) => {
      setActiveUploadJobId(payload.job_id);
      setUploadJobSeed(payload);
      toast.success(payload.message || 'Candidate document upload accepted. Indexing started.');
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Candidate document upload failed.');
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
  });

  useEffect(() => {
    const uploadJob = uploadJobQuery.data;
    if (!uploadJob) return;
    if (uploadJob.status === 'completed') {
      setActiveUploadJobId(null);
      setUploadJobSeed(uploadJob);
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-document-library'] }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      toast.success(uploadJob.message || 'Candidate document indexed successfully.');
      return;
    }
    if (uploadJob.status === 'error') {
      setActiveUploadJobId(null);
      setUploadJobSeed(uploadJob);
      toast.error(uploadJob.error || uploadJob.message || 'Candidate document upload failed.');
    }
  }, [queryClient, uploadJobQuery.data]);

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
        input_text: inputText,
        context_strategy: 'document_scan',
        context_window_mode: 'auto',
        use_document_context: true,
      }),
    onSuccess: async (payload) => {
      setWorkflowResponse(payload);
      setGeneratedArtifacts([]);
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
  const uploadJob = uploadJobQuery.data ?? uploadJobSeed;
  const uploadInProgress = uploadMutation.isPending || ['queued', 'running'].includes(uploadJob?.status || '');
  const selectedDocumentDate = formatDate(selectedDocument?.indexed_at || null);
  const preview = workflowResponse?.result?.grounding_preview ?? previewQuery.data?.preview ?? null;

  const handleFilesSelected = (fileList: FileList | File[] | null) => {
    const files = Array.from(fileList ?? []);
    if (!files.length) return;
    uploadMutation.mutate(files.slice(0, 1));
  };

  const handleOpenArtifact = (artifact: ProductWorkflowArtifact) => {
    if (!artifact.path) {
      toast.error(`${artifact.label} is registered, but no local path is available yet.`);
      return;
    }
    window.open(buildProductArtifactUrl(artifact.path), '_blank', 'noopener,noreferrer');
  };

  return (
    <motion.div data-testid="candidate-review-page" className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Candidate Review" description="Live hiring intelligence backed by the Product API, the indexed document corpus and structured candidate-analysis output.">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          className="hidden"
          onChange={(event) => handleFilesSelected(event.target.files)}
        />
        <Button data-testid="candidate-review-upload-button" variant="outline" className="h-9 px-4 text-xs border-border/50" disabled={uploadInProgress} onClick={() => fileInputRef.current?.click()}>
          {uploadInProgress ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Upload className="w-3.5 h-3.5 mr-2" />} Upload CV
        </Button>
        <Button data-testid="candidate-review-run-button" className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs" disabled={!selectedDocumentId || runReviewMutation.isPending} onClick={() => runReviewMutation.mutate()}>
          {runReviewMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />} Run Candidate Review
        </Button>
        <Button data-testid="candidate-review-generate-deck-button" variant="outline" className="h-9 px-4 text-xs border-border/50" disabled={!workflowResponse?.result?.deck_available || generateDeckMutation.isPending} onClick={() => generateDeckMutation.mutate()}>
          {generateDeckMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />} Generate Deck
        </Button>
      </PageHeader>

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
            No indexed documents are available yet. Upload a resume/CV or use the Document Library to index one before running Candidate Review.
          </div>
        </GlassCard>
      )}

      {!documentLibraryQuery.isLoading && selectableDocuments.length > 0 && !hasDedicatedCandidateCorpus && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            The current corpus is live, but no CV-like filename was detected. Candidate Review can still run on the selected document, though the output may be derived from a non-resume source.
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
            <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Evaluation brief</label>
            <textarea
              data-testid="candidate-review-brief-input"
              value={inputText}
              onChange={(event) => setInputText(event.target.value)}
              className="w-full min-h-[92px] rounded-lg border border-border/50 bg-secondary/20 px-3 py-2 text-xs text-foreground outline-none focus:border-primary/50"
              placeholder="Describe the hiring context, role, seniority or signals to validate."
            />
            <p className="mt-2 text-[11px] text-muted-foreground leading-relaxed">
              {preview?.preview_text
                ? preview.preview_text.slice(0, 260)
                : 'Grounding preview will appear here as soon as a candidate document is selected.'}
            </p>
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

          <GlassCard delay={0.3}>
            <div className="flex items-center justify-between gap-3 mb-3">
              <div>
                <h4 className="text-sm font-medium text-foreground">Artifacts</h4>
                <p className="text-xs text-muted-foreground">Generated deck artifacts and any structured exports registered by the live candidate-review flow.</p>
              </div>
              <StatusPill status={allArtifacts.length ? 'ready' : workflowResponse?.result ? workflowResponse.result.status : 'pending'} />
            </div>
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
