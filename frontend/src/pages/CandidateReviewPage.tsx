import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  UserCheck,
  Sparkles,
  Play,
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
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

import { WorkflowPublishActions } from '@/components/product/WorkflowPublishActions';
import { PageHeader, GlassCard, StatusPill, WorkflowProgressHeader } from '@/components/shared/ui-components';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from '@/components/ui/sonner';
import {
  buildProductArtifactUrl,
  buildWorkflowResponseFromRunHistory,
  PRODUCT_API_BASE_URL,
  generateProductWorkflowDeck,
  getProductDocumentLibrary,
  getProductGroundingPreview,
  getProductRunHistoryEntry,
  runProductWorkflow,
  type ProductDocumentLibraryEntry,
  type ProductResultSections,
  type ProductPublishNotionResponse,
  type ProductPublishTrelloResponse,
  type ProductRunWorkflowResponse,
  type ProductWorkflowArtifact,
} from '@/lib/product-api';
import { findRecommendedDocument, WORKFLOW_RECOMMENDED_DOCUMENTS } from '@/lib/workflow-demo-documents';

const workflowSteps = [
  { key: 'select', label: 'Select' },
  { key: 'ground', label: 'Ground' },
  { key: 'analyze', label: 'Analyze' },
  { key: 'review', label: 'Review' },
  { key: 'export', label: 'Export' },
] as const;

function isRoleBriefLikeText(value: string): boolean {
  const normalized = value
    .toLowerCase()
    .replace(/[._-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return /(^|\s)(jd|job description|job brief|role brief|hiring brief|position brief|job posting|scorecard|requisition)(\s|$)/.test(normalized);
}

function isCandidateLikeDocument(document: ProductDocumentLibraryEntry): boolean {
  const haystack = `${document.name} ${document.file_type || ''} ${document.loader_strategy_label || ''}`.toLowerCase();
  return /(cv|resume|candidate|curriculum|francis\s+taylor)/.test(haystack);
}

const ROLE_BRIEF_NONE = '__none__';

interface CandidateReviewRoleContext {
  title?: string | null;
  seniority?: string | null;
  must_haves: string[];
  nice_to_haves: string[];
  leadership_expectations: string[];
  interview_focus: string[];
  red_flags: string[];
}

function isRoleBriefDocument(document: ProductDocumentLibraryEntry): boolean {
  const haystack = `${document.name} ${document.file_type || ''} ${document.loader_strategy_label || ''}`;
  return isRoleBriefLikeText(haystack) && !isCandidateLikeDocument(document);
}

function stripSourceDecorators(value: string): string {
  return value
    .replace(/\[source:[^\]]+\]/gi, '')
    .replace(/\bsource\s*:\s*[^\n]+/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function looksLikeDocumentLabel(value: string): boolean {
  const lowered = value.toLowerCase();
  return /\.(pdf|doc|docx|txt|md)$/i.test(value) || (isRoleBriefLikeText(lowered) && /(pdf|doc|docx|txt|md)/.test(lowered));
}

function cleanText(value: unknown): string | null {
  const cleaned = stripSourceDecorators(String(value ?? ''));
  return cleaned || null;
}

function cleanMultilineText(value: unknown): string {
  return String(value ?? '')
    .replace(/\[source:[^\]]+\]/gi, '')
    .replace(/\bsource\s*:\s*[^\n]+/gi, '')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function normalizeBullets(values: Array<unknown>, limit = 8): string[] {
  const normalized: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    // Remove only real bullet/list prefixes:
    // "- item", "* item", "• item", "1. item", "1) item".
    // Do not remove requirement numbers such as "3+ years".
    const cleaned = cleanText(value)
      ?.replace(/^\s*(?:[-*\u2022]\s+|\d+[\.)]\s+)/, '')
      .trim();
    if (!cleaned) continue;
    const key = cleaned.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push(cleaned);
    if (normalized.length >= limit) break;
  }
  return normalized;
}

function canonicalRoleSectionName(rawName: string): keyof CandidateReviewRoleContext | null {
  const lowered = cleanText(rawName)?.toLowerCase().replace(/:$/, '');
  if (!lowered) return null;
  const lookup: Record<string, keyof CandidateReviewRoleContext> = {
    title: 'title',
    'role title': 'title',
    'job title': 'title',
    position: 'title',
    seniority: 'seniority',
    level: 'seniority',
    'seniority level': 'seniority',
    'must have': 'must_haves',
    'must-have': 'must_haves',
    'must-have requirements': 'must_haves',
    'must have requirements': 'must_haves',
    'must-haves': 'must_haves',
    'must haves': 'must_haves',
    required: 'must_haves',
    requirements: 'must_haves',
    'required skills': 'must_haves',
    'core requirements': 'must_haves',
    'role requirements': 'must_haves',
    'minimum requirements': 'must_haves',
    preferred: 'nice_to_haves',
    'preferred qualifications': 'nice_to_haves',
    bonus: 'nice_to_haves',
    'nice to have': 'nice_to_haves',
    'nice-to-have': 'nice_to_haves',
    'nice-to-have signals': 'nice_to_haves',
    'nice to have signals': 'nice_to_haves',
    'nice to haves': 'nice_to_haves',
    leadership: 'leadership_expectations',
    ownership: 'leadership_expectations',
    scope: 'leadership_expectations',
    'leadership expectations': 'leadership_expectations',
    'leadership / scope expectations': 'leadership_expectations',
    'leadership scope expectations': 'leadership_expectations',
    'interview focus': 'interview_focus',
    'interview priorities': 'interview_focus',
    assessment: 'interview_focus',
    'evaluation focus': 'interview_focus',
    'red flags': 'red_flags',
    watchouts: 'red_flags',
    'watch-outs': 'red_flags',
    watchout: 'red_flags',
    'role-specific watchouts': 'red_flags',
    'role specific watchouts': 'red_flags',
    'role watchouts': 'red_flags',
    risks: 'red_flags',
    'screen outs': 'red_flags',
    'screen-outs': 'red_flags',
  };
  return lookup[lowered] || null;
}

function deriveRoleTitleFromDocumentName(rawLabel?: string | null): string | null {
  const value = cleanText(rawLabel);
  if (!value) return null;
  const withoutExtension = value.replace(/\.(pdf|doc|docx|txt|md)$/i, '').trim();
  const normalized = withoutExtension
    .replace(/(^|[\s._-]+)(jd|role brief|job description|job brief|hiring brief|position brief|job posting|scorecard|requisition)(?=$|[\s._-]+)/gi, ' ')
    .replace(/[\-_]+/g, ' ')
    .replace(/\s{2,}/g, ' ')
    .trim();
  if (!normalized || normalized.length < 3 || looksLikeDocumentLabel(normalized)) return null;
  if (/(engineer|manager|designer|analyst|scientist|counsel|lead|specialist|architect|director)/i.test(normalized)) return normalized;
  return null;
}

function normalizeRoleBriefText(rawText?: string | null, fallbackDocumentName?: string | null): CandidateReviewRoleContext {
  const text = String(rawText || '').trim();
  if (!text) {
    return {
      title: deriveRoleTitleFromDocumentName(fallbackDocumentName),
      seniority: null,
      must_haves: [],
      nice_to_haves: [],
      leadership_expectations: [],
      interview_focus: [],
      red_flags: [],
    };
  }

  const sections: Partial<Record<keyof CandidateReviewRoleContext, string[]>> = {};
  let current: keyof CandidateReviewRoleContext | null = null;
  for (const rawLine of text.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const headingMatch = line.match(/^([A-Za-z][A-Za-z\s\-/]+):\s*(.*)$/);
    if (headingMatch) {
      const maybeSection = canonicalRoleSectionName(headingMatch[1]);
      if (maybeSection) {
        current = maybeSection;
        const trailing = cleanText(headingMatch[2]);
        if (trailing) sections[maybeSection] = [...(sections[maybeSection] || []), trailing];
        continue;
      }

      // Unknown headings should not leak into the previous recognized section.
      // This prevents lines like "Final instruction:" or future role headings
      // from being interpreted as bullets under interview_focus/watchouts.
      current = null;
      continue;
    }
    if (current) sections[current] = [...(sections[current] || []), line];
  }

  const inferredTitle = (() => {
    const explicit = cleanText(sections.title?.[0]);
    if (explicit && !looksLikeDocumentLabel(explicit)) return explicit;
    const roleMatch = text.match(/(?:role|job title|position)\s*:\s*(.+)/i);
    const matchedTitle = roleMatch ? cleanText(roleMatch[1]) : null;
    if (matchedTitle && !looksLikeDocumentLabel(matchedTitle)) return matchedTitle;
    for (const line of text.split(/\r?\n/).slice(0, 6)) {
      const cleaned = cleanText(line);
      if (!cleaned || cleaned.length > 100 || looksLikeDocumentLabel(cleaned)) continue;
      if (/(engineer|manager|designer|analyst|scientist|counsel|lead|specialist)/i.test(cleaned)) return cleaned.replace(/:$/, '');
    }
    const fromDocumentName = deriveRoleTitleFromDocumentName(fallbackDocumentName);
    if (fromDocumentName) return fromDocumentName;
    return null;
  })();

  const inferredSeniority = (() => {
    const explicit = cleanText(sections.seniority?.[0]);
    if (explicit) return explicit;
    const match = text.match(/\b(staff|principal|director|lead|senior|mid|junior|entry[ -]?level)\b/i);
    return match ? match[1].replace(/-/g, ' ') : null;
  })();

  const mustHaves = normalizeBullets(sections.must_haves || []);
  const niceToHaves = normalizeBullets(sections.nice_to_haves || []);
  const leadershipExpectations = normalizeBullets(sections.leadership_expectations || []);
  const redFlags = normalizeBullets(sections.red_flags || []);
  const interviewFocus = normalizeBullets(
    (sections.interview_focus || []).length
      ? sections.interview_focus || []
      : [...leadershipExpectations.slice(0, 2), ...redFlags.slice(0, 1), ...mustHaves.slice(0, 2)],
    4,
  );

  return {
    title: inferredTitle,
    seniority: inferredSeniority,
    must_haves: mustHaves,
    nice_to_haves: niceToHaves,
    leadership_expectations: leadershipExpectations,
    interview_focus: interviewFocus,
    red_flags: redFlags,
  };
}

function renderCandidateReviewInputText(roleContext: CandidateReviewRoleContext): string | undefined {
  const hasRoleContext = Boolean(roleContext.title || roleContext.seniority || roleContext.must_haves.length || roleContext.nice_to_haves.length || roleContext.leadership_expectations.length || roleContext.interview_focus.length || roleContext.red_flags.length);
  if (!hasRoleContext) return undefined;

  const lines = [
    'Evaluate the CV against the normalized hiring thesis below.',
    'Keep the same candidate_review output shape: candidate fit summary, strengths, gaps, seniority signals, watchouts and interview next steps.',
    'Do not attribute role requirements to the candidate unless the CV explicitly supports them.',
    'Prefer grounded evidence from the CV over assumptions.',
  ];

  if (roleContext.title) lines.push(`Role title: ${roleContext.title}`);
  if (roleContext.seniority) lines.push(`Target seniority: ${roleContext.seniority}`);
  if (roleContext.must_haves.length) {
    lines.push('Must-have requirements:');
    lines.push(...roleContext.must_haves.map((item) => `- ${item}`));
  }
  if (roleContext.nice_to_haves.length) {
    lines.push('Nice-to-have signals:');
    lines.push(...roleContext.nice_to_haves.map((item) => `- ${item}`));
  }
  if (roleContext.leadership_expectations.length) {
    lines.push('Leadership / scope expectations:');
    lines.push(...roleContext.leadership_expectations.map((item) => `- ${item}`));
  }
  if (roleContext.interview_focus.length) {
    lines.push('Interview focus:');
    lines.push(...roleContext.interview_focus.map((item) => `- ${item}`));
  }
  if (roleContext.red_flags.length) {
    lines.push('Role-specific watchouts:');
    lines.push(...roleContext.red_flags.map((item) => `- ${item}`));
  }

  lines.push('Final instruction: preserve the existing candidate_review output style and evaluate fit specifically for this role context.');
  return lines.join('\n').trim();
}

function roleContextHasContent(roleContext: CandidateReviewRoleContext | null | undefined): boolean {
  return Boolean(roleContext && (roleContext.title || roleContext.seniority || roleContext.must_haves.length || roleContext.nice_to_haves.length || roleContext.leadership_expectations.length || roleContext.interview_focus.length || roleContext.red_flags.length));
}

function roleContextSummary(roleContext: CandidateReviewRoleContext | null | undefined): string {
  if (!roleContextHasContent(roleContext)) return 'No role brief selected. Candidate Review will use the default workflow prompt.';
  const parts = [
    roleContext?.title ? `Role: ${roleContext.title}` : null,
    roleContext?.seniority ? `Seniority: ${roleContext.seniority}` : null,
    roleContext?.must_haves?.length ? `${roleContext.must_haves.length} must-have requirement(s)` : null,
    roleContext?.interview_focus?.length ? `${roleContext.interview_focus.length} interview focus area(s)` : null,
  ].filter(Boolean);
  return parts.join(' · ');
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
  return dedupeRows(rows).filter((row) => {
    const meaningfulCount = [row[0], row[1], row[2], row[3]].filter((cell) => isMeaningfulCell(cell)).length;
    const hasRoleAndCompany = isMeaningfulCell(row[0]) && isMeaningfulCell(row[1]);
    const hasRoleAndSummary = isMeaningfulCell(row[0]) && isMeaningfulCell(row[3]);
    return meaningfulCount >= 2 && (hasRoleAndCompany || hasRoleAndSummary || meaningfulCount >= 3);
  });
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
  const [searchParams] = useSearchParams();
  const historyRunId = searchParams.get('historyRunId') || searchParams.get('runId') || '';
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [selectedRoleBriefDocumentId, setSelectedRoleBriefDocumentId] = useState(ROLE_BRIEF_NONE);
  const [workflowResponse, setWorkflowResponse] = useState<ProductRunWorkflowResponse | null>(null);
  const [generatedArtifacts, setGeneratedArtifacts] = useState<ProductWorkflowArtifact[]>([]);
  const [analysisInternalsOpen, setAnalysisInternalsOpen] = useState(false);
  const [trelloPublishResult, setTrelloPublishResult] = useState<ProductPublishTrelloResponse | null>(null);
  const [notionPublishResult, setNotionPublishResult] = useState<ProductPublishNotionResponse | null>(null);

  useEffect(() => {
    const handleOpenInternals = () => setAnalysisInternalsOpen(true);
    window.addEventListener('workbench-tour:open-candidate-internals', handleOpenInternals);
    return () => window.removeEventListener('workbench-tour:open-candidate-internals', handleOpenInternals);
  }, []);

  const documentLibraryQuery = useQuery({
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
    () => (documentLibraryQuery.data?.documents ?? []).filter((document) => document.status === 'indexed' || document.status === 'warning'),
    [documentLibraryQuery.data?.documents],
  );

  const preferredCandidateDocuments = useMemo(
    () => availableDocuments.filter(isCandidateLikeDocument),
    [availableDocuments],
  );

  const selectableDocuments = preferredCandidateDocuments.length ? preferredCandidateDocuments : availableDocuments;
  const hasDedicatedCandidateCorpus = preferredCandidateDocuments.length > 0;

  const recommendedCandidateDocument = useMemo(
    () => findRecommendedDocument(selectableDocuments, WORKFLOW_RECOMMENDED_DOCUMENTS.candidateReview[0]),
    [selectableDocuments],
  );

  const roleBriefDocuments = useMemo(
    () => availableDocuments.filter((document) => isRoleBriefDocument(document) && document.document_id !== selectedDocumentId),
    [availableDocuments, selectedDocumentId],
  );

  const recommendedRoleBriefDocument = useMemo(
    () => findRecommendedDocument(roleBriefDocuments, WORKFLOW_RECOMMENDED_DOCUMENTS.candidateReview[1]),
    [roleBriefDocuments],
  );

  useEffect(() => {
    if (!selectableDocuments.length) {
      setSelectedDocumentId('');
      return;
    }
    if (!selectedDocumentId || !selectableDocuments.some((document) => document.document_id === selectedDocumentId)) {
      setSelectedDocumentId(recommendedCandidateDocument?.document_id ?? selectableDocuments[0]?.document_id ?? '');
    }
  }, [recommendedCandidateDocument, selectedDocumentId, selectableDocuments]);

  useEffect(() => {
    if (!roleBriefDocuments.length) {
      if (selectedRoleBriefDocumentId !== ROLE_BRIEF_NONE) setSelectedRoleBriefDocumentId(ROLE_BRIEF_NONE);
      return;
    }

    const fallbackRoleBriefDocument = recommendedRoleBriefDocument ?? roleBriefDocuments[0] ?? null;

    if (selectedRoleBriefDocumentId === ROLE_BRIEF_NONE && fallbackRoleBriefDocument) {
      setSelectedRoleBriefDocumentId(fallbackRoleBriefDocument.document_id);
      return;
    }

    if (selectedRoleBriefDocumentId !== ROLE_BRIEF_NONE && !roleBriefDocuments.some((document) => document.document_id === selectedRoleBriefDocumentId)) {
      setSelectedRoleBriefDocumentId(fallbackRoleBriefDocument?.document_id ?? ROLE_BRIEF_NONE);
    }
  }, [recommendedRoleBriefDocument, roleBriefDocuments, selectedRoleBriefDocumentId]);

  const selectedDocument = selectableDocuments.find((document) => document.document_id === selectedDocumentId);
  const selectedRoleBriefDocument = roleBriefDocuments.find((document) => document.document_id === selectedRoleBriefDocumentId);

  const roleBriefPreviewQuery = useQuery({
    queryKey: ['candidate-review-role-brief-preview', selectedRoleBriefDocumentId],
    enabled: selectedRoleBriefDocumentId !== ROLE_BRIEF_NONE,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryFn: () =>
      getProductGroundingPreview({
        workflowId: 'document_review',
        strategy: 'document_scan',
        documentIds: selectedRoleBriefDocumentId !== ROLE_BRIEF_NONE ? [selectedRoleBriefDocumentId] : [],
        inputText: 'Extract the hiring thesis, must-haves, preferred signals, leadership scope, interview focus and red flags from this role brief.',
      }),
  });

  const rawRoleBriefText = useMemo(
    () => cleanMultilineText(roleBriefPreviewQuery.data?.preview.preview_text),
    [roleBriefPreviewQuery.data?.preview.preview_text],
  );
  const normalizedRoleBrief = useMemo(() => normalizeRoleBriefText(rawRoleBriefText, selectedRoleBriefDocument?.name), [rawRoleBriefText, selectedRoleBriefDocument?.name]);
  const generatedCandidateReviewInputText = useMemo(
    () => renderCandidateReviewInputText(normalizedRoleBrief),
    [normalizedRoleBrief],
  );

  const previewQuery = useQuery({
    queryKey: ['candidate-review-preview', selectedDocumentId, generatedCandidateReviewInputText],
    enabled: Boolean(selectedDocumentId),
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryFn: () =>
      getProductGroundingPreview({
        workflowId: 'candidate_review',
        strategy: 'document_scan',
        documentIds: selectedDocumentId ? [selectedDocumentId] : [],
        inputText: generatedCandidateReviewInputText,
      }),
  });

  useEffect(() => {
    const run = historyDetailQuery.data?.run;
    const hydratedWorkflowResponse = buildWorkflowResponseFromRunHistory(historyDetailQuery.data);
    if (!historyRunId || !run || !hydratedWorkflowResponse?.result || hydratedWorkflowResponse.result.workflow_id !== 'candidate_review') return;

    const requestPayload = run.request_payload && typeof run.request_payload === 'object' ? run.request_payload : null;
    const requestDocumentIds = Array.isArray(requestPayload?.document_ids)
      ? requestPayload.document_ids.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const historyDocumentId = (run.document_ids ?? [])[0] || requestDocumentIds[0] || hydratedWorkflowResponse.result.grounding_preview?.document_ids?.[0] || '';

    if (historyDocumentId) setSelectedDocumentId(historyDocumentId);
    setWorkflowResponse(hydratedWorkflowResponse);
    setGeneratedArtifacts(run.artifact_items?.length ? run.artifact_items : hydratedWorkflowResponse.result.artifacts ?? []);
    setTrelloPublishResult(null);
    setNotionPublishResult(null);
  }, [historyDetailQuery.data, historyRunId]);

  const runReviewMutation = useMutation({
    mutationFn: () =>
      runProductWorkflow({
        workflow_id: 'candidate_review',
        document_ids: selectedDocumentId ? [selectedDocumentId] : [],
        role_brief_document_id: selectedRoleBriefDocumentId !== ROLE_BRIEF_NONE ? selectedRoleBriefDocumentId : null,
        input_text: selectedRoleBriefDocumentId !== ROLE_BRIEF_NONE ? undefined : generatedCandidateReviewInputText,
        context_strategy: 'document_scan',
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
      toast.success(generatedCandidateReviewInputText ? 'Candidate review completed against the selected role brief.' : 'Candidate review completed with grounded backend output.');
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
  const candidateReviewView = (workflowResponse as (ProductRunWorkflowResponse & { candidate_review_view?: any }) | null)?.candidate_review_view ?? null;
  const statusCopy = getStatusCopy(workflowResponse);
  const activeRoleContext = roleContextHasContent(candidateReviewView?.role_context) ? candidateReviewView?.role_context : roleContextHasContent(normalizedRoleBrief) ? normalizedRoleBrief : null;
  const roleBriefSignalsSparse = Boolean(selectedRoleBriefDocument && activeRoleContext && !activeRoleContext.must_haves.length && !activeRoleContext.interview_focus.length);
  const candidateProfile = candidateReviewView?.candidate_profile ?? sections?.candidate_profile ?? null;
  const score = deriveScore(workflowResponse, sections);
  const evidenceRows = useMemo(() => normalizeEvidenceRows(sections?.evidence_highlights ?? []), [sections?.evidence_highlights]);
  const experienceTable = getTable(sections, 'Experience highlights');
  const experienceRows = useMemo(() => normalizeExperienceRows(experienceTable?.rows ?? []), [experienceTable?.rows]);
  const evidenceTable = getTable(sections, 'Evidence highlights');
  const evidenceTableRows = useMemo(() => normalizeEvidenceRows(evidenceTable?.rows ?? []), [evidenceTable?.rows]);
  const educationTable = getTable(sections, 'Education snapshot');
  const educationRows = useMemo(() => {
    const fromCandidateView = Array.isArray(candidateReviewView?.education)
      ? candidateReviewView.education
          .map((item: any) => [item.degree, item.institution, item.period || item.year || item.details].filter(Boolean).join(' · '))
          .filter(Boolean)
      : [];
    const fromSections = (educationTable?.rows ?? [])
      .map((row: any) => Array.isArray(row) ? row.filter(Boolean).join(' · ') : String(row || '').trim())
      .filter(Boolean);
    return fromCandidateView.length ? fromCandidateView : fromSections;
  }, [candidateReviewView?.education, educationTable?.rows]);
  const strengths = candidateReviewView?.strengths?.length ? candidateReviewView.strengths : (sections?.strengths ?? []);
  const gaps = candidateReviewView?.gaps?.length ? candidateReviewView.gaps : (sections?.warnings ?? []);
  const senioritySignals = candidateReviewView?.seniority_signals?.length ? candidateReviewView.seniority_signals : (sections?.highlights ?? []);
  const watchouts = candidateReviewView?.watchouts?.length ? candidateReviewView.watchouts : (sections?.watchouts ?? sections?.warnings ?? []);
  const nextSteps = candidateReviewView?.next_steps?.length ? candidateReviewView.next_steps : (sections?.next_steps ?? []);
  const documentMetrics = candidateReviewView?.document_metrics ?? null;
  const showSourceBlockCount = documentMetrics?.show_source_block_count ?? ((workflowResponse?.result?.grounding_preview?.source_block_count ?? previewQuery.data?.preview?.source_block_count ?? 0) > 0);
  const sourceBlockCount = documentMetrics?.source_block_count ?? workflowResponse?.result?.grounding_preview?.source_block_count ?? previewQuery.data?.preview?.source_block_count ?? 0;
  const previewContextChars = documentMetrics?.context_chars ?? workflowResponse?.result?.grounding_preview?.context_chars ?? previewQuery.data?.preview?.context_chars ?? 0;
  const allArtifacts = useMemo(
    () => dedupeArtifacts([...(candidateReviewView?.artifacts ?? []), ...(sections?.artifacts ?? []), ...generatedArtifacts]),
    [candidateReviewView?.artifacts, generatedArtifacts, sections?.artifacts],
  );
  const selectedDocumentDate = formatDate(selectedDocument?.indexed_at || null);
  const preview = workflowResponse?.result?.grounding_preview ?? previewQuery.data?.preview ?? null;

  const stepStatuses = useMemo(() => workflowSteps.map((step) => {
    let status = 'pending';
    if (step.key === 'select' && selectedDocumentId) status = 'completed';
    if (step.key === 'ground' && (preview || selectedRoleBriefDocumentId !== ROLE_BRIEF_NONE)) status = 'completed';
    if (step.key === 'analyze' && runReviewMutation.isPending) status = 'running';
    if (step.key === 'analyze' && workflowResponse?.result) status = workflowResponse.result.status === 'error' ? 'error' : 'completed';
    if (step.key === 'review' && (sections || candidateReviewView)) status = 'completed';
    if (step.key === 'export' && generateDeckMutation.isPending) status = 'running';
    if (step.key === 'export' && allArtifacts.length > 0) status = 'completed';
    return { ...step, status };
  }), [allArtifacts.length, candidateReviewView, generateDeckMutation.isPending, preview, runReviewMutation.isPending, sections, selectedDocumentId, selectedRoleBriefDocumentId, workflowResponse?.result]);


  const handleOpenArtifact = (artifact: ProductWorkflowArtifact) => {
    if (!artifact.path) {
      toast.error(`${artifact.label} is registered, but no local path is available yet.`);
      return;
    }
    window.open(buildProductArtifactUrl(artifact.path), '_blank', 'noopener,noreferrer');
  };

  return (
    <motion.div data-testid="candidate-review-page" className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="candidate-review-header">
        <PageHeader title="Candidate Review" description="Review a candidate profile with grounded strengths, watchouts and interview focus.">
          <Button data-testid="candidate-review-run-button" className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs" disabled={!selectedDocumentId || runReviewMutation.isPending} onClick={() => runReviewMutation.mutate()}>
            {runReviewMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-2" />} Run Candidate Review
          </Button>
          <Button data-testid="candidate-review-generate-deck-button" variant="outline" className="h-9 px-4 text-xs border-border/50" disabled={!workflowResponse?.result?.deck_available || generateDeckMutation.isPending} onClick={() => generateDeckMutation.mutate()}>
            {generateDeckMutation.isPending ? <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 mr-2" />} Generate Deck
          </Button>
        </PageHeader>
      </div>

      <div data-tour="candidate-review-progress">
        <WorkflowProgressHeader
          steps={stepStatuses}
          title="Workflow progress"
          description="Track how the candidate review moves from document selection to publish-ready outputs."
        />
      </div>

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

      <GlassCard className="mb-6" data-tour="candidate-review-selection">
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="rounded-xl border border-border/50 bg-secondary/10 p-4">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Candidate document</p>
                <p className="mt-2 text-sm text-muted-foreground">This is the primary grounded document used by the candidate_review workflow.</p>
              </div>
              <StatusPill status={selectedDocumentId ? 'ready' : 'pending'} />
            </div>
            <Select value={selectedDocumentId} onValueChange={setSelectedDocumentId}>
              <SelectTrigger data-testid="candidate-review-document-trigger" className="h-11 text-sm bg-secondary/30"><SelectValue placeholder="Select a candidate document" /></SelectTrigger>
              <SelectContent>
                {selectableDocuments.map((document) => (
                  <SelectItem data-testid="candidate-review-document-option" data-document-name={document.name} key={document.document_id} value={document.document_id} className="text-xs">{document.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="rounded-xl border border-border/50 bg-secondary/10 p-4">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Role brief document</p>
                <p className="mt-2 text-sm text-muted-foreground">Use an indexed role brief to make the review role-aware without changing the workflow contract.</p>
              </div>
              <StatusPill status={selectedRoleBriefDocument ? 'ready' : 'pending'} />
            </div>
            <Select value={selectedRoleBriefDocumentId} onValueChange={setSelectedRoleBriefDocumentId}>
              <SelectTrigger data-testid="candidate-review-role-brief-trigger" className="h-11 text-sm bg-secondary/30"><SelectValue placeholder="Select an indexed role brief" /></SelectTrigger>
              <SelectContent>
                <SelectItem value={ROLE_BRIEF_NONE} className="text-xs">No indexed role brief</SelectItem>
                {roleBriefDocuments.map((document) => (
                  <SelectItem key={document.document_id} value={document.document_id} className="text-xs">{document.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </GlassCard>

      <GlassCard className="mb-6" data-tour="candidate-review-analysis-internals">
        <button
          type="button"
          onClick={() => setAnalysisInternalsOpen((value) => !value)}
          className="w-full flex items-start justify-between gap-4 text-left"
          data-testid="candidate-review-analysis-internals-toggle"
        >
          <div>
            <h3 className="text-sm font-semibold text-foreground">Analysis internals</h3>
            <p className="mt-1 text-xs text-muted-foreground">Grounding preview and generated role-aware input. Keep collapsed unless you need retrieval/debug context.</p>
          </div>
          <span className="mt-0.5 text-muted-foreground">{analysisInternalsOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}</span>
        </button>

        {analysisInternalsOpen ? (
          <div className="mt-4 grid lg:grid-cols-2 gap-4">
            <div>
              <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Candidate grounding preview</label>
              <div className="rounded-lg border border-border/50 bg-secondary/20 px-3 py-3 min-h-[132px]">
                <div className="grid gap-2 sm:grid-cols-3">
                  <div className="rounded-md bg-background/60 px-2 py-2">
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Selected docs</div>
                    <div className="mt-1 text-sm font-medium text-foreground">{selectedDocumentId ? 1 : 0}</div>
                  </div>
                  {showSourceBlockCount ? (
                    <div className="rounded-md bg-background/60 px-2 py-2">
                      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Source blocks</div>
                      <div className="mt-1 text-sm font-medium text-foreground">{sourceBlockCount}</div>
                    </div>
                  ) : null}
                  <div className="rounded-md bg-background/60 px-2 py-2">
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Context size</div>
                    <div className="mt-1 text-sm font-medium text-foreground">{previewContextChars.toLocaleString()} chars</div>
                  </div>
                </div>
                <p className="mt-3 text-[11px] text-muted-foreground leading-relaxed line-clamp-6">
                  {preview?.preview_text
                    ? preview.preview_text
                    : 'Select a candidate document to preview the grounded CV context before running the workflow.'}
                </p>
              </div>
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-1.5 block">Generated review input</label>
              <div className="rounded-lg border border-border/50 bg-secondary/20 px-3 py-3 min-h-[132px]">
                <div className="grid gap-2 sm:grid-cols-3">
                  <div className="rounded-md bg-background/60 px-2 py-2">
                    <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Role title</div>
                    <div className="mt-1 text-sm font-medium text-foreground">{activeRoleContext?.title || 'Role-aware review'}</div>
                  </div>
                  {activeRoleContext?.must_haves.length ? (
                    <div className="rounded-md bg-background/60 px-2 py-2">
                      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Must-haves</div>
                      <div className="mt-1 text-sm font-medium text-foreground">{activeRoleContext.must_haves.length}</div>
                    </div>
                  ) : null}
                  {activeRoleContext?.interview_focus.length ? (
                    <div className="rounded-md bg-background/60 px-2 py-2">
                      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Interview focus</div>
                      <div className="mt-1 text-sm font-medium text-foreground">{activeRoleContext.interview_focus.length}</div>
                    </div>
                  ) : null}
                </div>
                {roleBriefSignalsSparse ? (
                  <p className="mt-3 text-[11px] text-muted-foreground leading-relaxed">Indexed role brief selected, but structured signals are still sparse. Candidate Review will still use role title and seniority context without surfacing empty counters.</p>
                ) : null}
                <p className="mt-3 text-[11px] text-muted-foreground leading-relaxed line-clamp-6">
                  {generatedCandidateReviewInputText || 'No role brief was supplied. The workflow will use its default backend candidate-review prompt.'}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </GlassCard>

      <div className="grid lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 space-y-4">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} data-tour="candidate-review-profile" className="glass rounded-xl p-6 text-center">
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
                {educationRows.length ? 'Education snapshot available' : 'Education snapshot will appear when available'}
              </div>
              {educationRows.length > 0 && (
                <div className="mt-3 space-y-2">
                  {educationRows.slice(0, 4).map((item, index) => (
                    <p key={`${item}-${index}`} className="text-xs text-muted-foreground leading-relaxed">
                      {item}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </motion.div>

          <GlassCard delay={0.16} data-tour="candidate-review-left-insights">
            <div className="flex items-center gap-2 mb-3">
              <Briefcase className="w-4 h-4 text-primary" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Role Context</h4>
            </div>
            {roleContextHasContent(activeRoleContext) ? (
              <div className="space-y-3 text-xs text-muted-foreground">
                <div>
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Role</p>
                  <p className="mt-1 text-foreground font-medium">{activeRoleContext?.title || 'Selected role brief'}</p>
                  {activeRoleContext?.seniority ? <p className="mt-1 text-[11px] text-muted-foreground">Target seniority: {activeRoleContext.seniority}</p> : null}
                </div>
                {activeRoleContext?.must_haves.length ? (
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Must-haves</p>
                    <div className="space-y-1">
                      {activeRoleContext.must_haves.slice(0, 4).map((item) => <p key={item}>• {item}</p>)}
                    </div>
                  </div>
                ) : null}
                {activeRoleContext?.interview_focus.length ? (
                  <div>
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Interview focus</p>
                    <div className="space-y-1">
                      {activeRoleContext.interview_focus.slice(0, 3).map((item) => <p key={item}>• {item}</p>)}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Select an indexed role brief to make Candidate Review fit-aware instead of using the generic prompt.</p>
            )}
          </GlassCard>

          <GlassCard delay={0.18}>
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="w-4 h-4 text-glow-warning" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Decision Risks</h4>
            </div>
            <div className="space-y-2">
              {(watchouts.length ? watchouts : ['Run the candidate workflow to surface live watchouts and interview risks.']).map((watchout) => (
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
          <GlassCard delay={0.1} data-tour="candidate-review-interview-focus">
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-primary" />
              <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Interview Focus Areas</h4>
            </div>
            <div className="space-y-2">
              {(nextSteps.length ? nextSteps : ['Run the candidate review to generate live interview focus areas.']).map((step, index) => (
                <div key={step} className="flex items-start gap-3 py-2 px-3 rounded-lg bg-secondary/20">
                  <span className="text-[10px] font-bold text-muted-foreground w-4 mt-0.5">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <span className="text-xs font-medium text-foreground">{step}</span>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard delay={0.14} data-tour="candidate-review-experience">
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

          <div className="grid md:grid-cols-2 gap-4" data-tour="candidate-review-evaluation-grid">
            <GlassCard delay={0.18}>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-glow-success" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Strengths</h4>
              </div>
              <div className="space-y-2">
                {(strengths.length ? strengths : ['Strengths will populate from the structured candidate payload after the live run.']).map((strength) => (
                  <p key={strength} className="text-xs text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-glow-success mt-1.5 shrink-0" />{strength}
                  </p>
                ))}
              </div>
            </GlassCard>

            <GlassCard delay={0.2}>
              <div className="flex items-center gap-2 mb-3">
                <Search className="w-4 h-4 text-primary" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Gaps</h4>
              </div>
              <div className="space-y-2">
                {(gaps.length ? gaps : ['Gaps will appear once the role-aware candidate review compares the CV against the selected hiring brief.']).map((gap) => (
                  <p key={gap} className="text-xs text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />{gap}
                  </p>
                ))}
              </div>
            </GlassCard>

            <GlassCard delay={0.22}>
              <div className="flex items-center gap-2 mb-3">
                <UserCheck className="w-4 h-4 text-primary" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Seniority Signals</h4>
              </div>
              <div className="space-y-2">
                {(senioritySignals.length ? senioritySignals : ['Seniority signals will populate after the live run.']).map((signal) => (
                  <p key={signal} className="text-xs text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 shrink-0" />{signal}
                  </p>
                ))}
              </div>
            </GlassCard>

            <GlassCard delay={0.24}>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-glow-warning" />
                <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Watchouts</h4>
              </div>
              <div className="space-y-2">
                {(watchouts.length ? watchouts : ['Watchouts will populate from the backend review status after the live run.']).map((watchout) => (
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

          <div data-testid="workflow-publish-actions-surface" data-workflow="candidate-review" data-tour="candidate-review-handoff">
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
              strengths: strengths || [],
              watchouts: watchouts || [],
              highlights: strengths || [],
              next_steps: nextSteps || [],
              interview_focus: activeRoleContext?.interview_focus || watchouts || [],
              interview_questions: watchouts || [],
              role_title: activeRoleContext?.title || null,
              target_seniority: activeRoleContext?.seniority || null,
              must_haves: activeRoleContext?.must_haves || [],
              role_watchouts: activeRoleContext?.red_flags || [],
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
