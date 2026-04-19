import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Shield, GitCompare, ClipboardList, UserCheck, ArrowRight, FileOutput, Sparkles, AlertTriangle, Loader2 } from 'lucide-react';

import { PageHeader, StatusPill, GlassCard } from '@/components/shared/ui-components';
import { getProductDocumentLibrary, getProductRunHistory, getProductWorkflows, type ProductDocumentLibraryEntry, type ProductRunEntry, type ProductWorkflowDefinition } from '@/lib/product-api';

const WORKFLOW_ICON_MAP: Record<string, typeof Shield> = {
  document_review: Shield,
  policy_contract_comparison: GitCompare,
  action_plan_evidence_review: ClipboardList,
  candidate_review: UserCheck,
};

const WORKFLOW_ROUTE_MAP: Record<string, string> = {
  document_review: '/app/workflows/document-review',
  policy_contract_comparison: '/app/workflows/comparison',
  action_plan_evidence_review: '/app/workflows/action-plan',
  candidate_review: '/app/workflows/candidate-review',
};

const WORKFLOW_COLOR_MAP: Record<string, { gradient: string; icon: string }> = {
  document_review: { gradient: 'from-primary/20 to-primary/5', icon: 'bg-primary/15 text-primary' },
  policy_contract_comparison: { gradient: 'from-accent/20 to-accent/5', icon: 'bg-accent/15 text-accent' },
  action_plan_evidence_review: { gradient: 'from-glow-success/20 to-glow-success/5', icon: 'bg-glow-success/15 text-glow-success' },
  candidate_review: { gradient: 'from-glow-warning/20 to-glow-warning/5', icon: 'bg-glow-warning/15 text-glow-warning' },
};

function formatDateTime(value?: string | null): string {
  if (!value) return 'No live runs yet';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function isCandidateLikeDocument(document: ProductDocumentLibraryEntry): boolean {
  const haystack = `${document.name} ${document.file_type || ''} ${document.loader_strategy_label || ''}`.toLowerCase();
  return /(cv|resume|candidate|curriculum|hiring)/.test(haystack);
}

function countEligibleDocuments(workflow: ProductWorkflowDefinition, documents: ProductDocumentLibraryEntry[]): number {
  if (workflow.workflow_id === 'candidate_review') {
    return documents.filter(isCandidateLikeDocument).length;
  }
  return documents.length;
}

function workflowSurfaceStatus(workflow: ProductWorkflowDefinition, documents: ProductDocumentLibraryEntry[]): 'ready' | 'degraded' | 'pending' {
  const eligibleCount = countEligibleDocuments(workflow, documents);
  if (eligibleCount >= workflow.required_document_count_min) return 'ready';
  if (documents.length > 0) return 'degraded';
  return 'pending';
}

function summarizeRequirement(workflow: ProductWorkflowDefinition): string {
  if (workflow.required_document_count_max && workflow.required_document_count_max === workflow.required_document_count_min) {
    return `${workflow.required_document_count_min} document${workflow.required_document_count_min > 1 ? 's' : ''}`;
  }
  if (workflow.required_document_count_max) {
    return `${workflow.required_document_count_min}-${workflow.required_document_count_max} documents`;
  }
  return `${workflow.required_document_count_min}+ documents`;
}

function buildRecentRunLookup(runs: ProductRunEntry[]): Record<string, { count: number; latest?: ProductRunEntry }> {
  return runs.reduce<Record<string, { count: number; latest?: ProductRunEntry }>>((accumulator, run) => {
    const workflowId = String(run.workflow_id || '').trim();
    if (!workflowId) return accumulator;
    const current = accumulator[workflowId] || { count: 0, latest: undefined };
    accumulator[workflowId] = {
      count: current.count + 1,
      latest: current.latest || run,
    };
    return accumulator;
  }, {});
}

export default function WorkflowCatalogPage() {
  const workflowsQuery = useQuery({
    queryKey: ['product-workflows'],
    queryFn: getProductWorkflows,
    refetchOnWindowFocus: false,
  });

  const documentLibraryQuery = useQuery({
    queryKey: ['product-document-library'],
    queryFn: getProductDocumentLibrary,
    refetchOnWindowFocus: false,
  });

  const runHistoryQuery = useQuery({
    queryKey: ['product-run-history'],
    queryFn: getProductRunHistory,
    refetchOnWindowFocus: false,
  });

  const workflows = workflowsQuery.data?.workflows ?? [];
  const availableDocuments = (documentLibraryQuery.data?.documents ?? []).filter((document) => document.status === 'indexed' || document.status === 'warning');
  const recentRunLookup = buildRecentRunLookup(runHistoryQuery.data?.runs ?? []);
  const candidateDocCount = availableDocuments.filter(isCandidateLikeDocument).length;

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Decision Workflows" description="Run the live workflow catalog backed by the Product API contract, document index and persisted run history." />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="glass rounded-xl p-4 mb-8 flex items-center gap-4"
      >
        <div className="w-10 h-10 rounded-xl bg-glow-warning/10 flex items-center justify-center shrink-0">
          <FileOutput className="w-5 h-5 text-glow-warning" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="text-sm font-medium text-foreground">Run surface is live</h3>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-medium">{workflowsQuery.data?.contract_version || 'product_workflows.v1'}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            {workflows.length
              ? `Loaded ${workflows.length} workflow definitions, ${availableDocuments.length} grounded document(s) and ${(runHistoryQuery.data?.summary.total_runs ?? 0)} persisted run(s).`
              : 'Loading the workflow contract, corpus coverage and live run history.'}
          </p>
          {candidateDocCount === 0 && availableDocuments.length > 0 && (
            <p className="text-[11px] text-glow-warning mt-1">Candidate Review is available, but no CV-like document is currently indexed. Upload a resume or CV to run it end to end.</p>
          )}
        </div>
        <Link to="/app/deck-center" className="text-xs text-primary hover:text-primary/80 flex items-center gap-1 shrink-0">
          Deck Center <ArrowRight className="w-3 h-3" />
        </Link>
      </motion.div>

      {(workflowsQuery.isError || documentLibraryQuery.isError || runHistoryQuery.isError) && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            One or more live contracts could not be loaded. The catalog is still rendered, but some readiness signals may be degraded.
          </div>
        </GlassCard>
      )}

      {workflowsQuery.isLoading && !workflows.length ? (
        <GlassCard>
          <div className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> Loading workflow catalog...</div>
        </GlassCard>
      ) : (
        <div className="space-y-4">
          {workflows.map((workflow, index) => {
            const Icon = WORKFLOW_ICON_MAP[workflow.workflow_id] || Shield;
            const colors = WORKFLOW_COLOR_MAP[workflow.workflow_id] || WORKFLOW_COLOR_MAP.document_review;
            const route = WORKFLOW_ROUTE_MAP[workflow.workflow_id] || '/app/workflows';
            const readiness = workflowSurfaceStatus(workflow, availableDocuments);
            const eligibleDocumentCount = countEligibleDocuments(workflow, availableDocuments);
            const runStats = recentRunLookup[workflow.workflow_id];
            const latestRun = runStats?.latest;
            const requirementLabel = summarizeRequirement(workflow);
            const executionModeLabel = workflow.preferred_context_strategy === 'retrieval' ? 'retrieval-grounded' : 'document-scan';
            const readinessCopy =
              readiness === 'ready'
                ? `${eligibleDocumentCount} eligible document(s) currently support this workflow.`
                : readiness === 'degraded'
                  ? `Documents are indexed, but ${workflow.label} still needs ${workflow.workflow_id === 'candidate_review' ? 'a CV-like document' : requirementLabel}.`
                  : `No indexed documents are available yet for ${workflow.label}.`;

            return (
              <motion.div
                key={workflow.workflow_id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + index * 0.08, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              >
                <Link to={route} className="block">
                  <div className={`glass rounded-xl p-6 group hover:border-primary/30 transition-all duration-300 cursor-pointer bg-gradient-to-r ${colors.gradient}`}>
                    <div className="flex items-start gap-5">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${colors.icon}`}>
                        <Icon className="w-6 h-6" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-3 mb-1.5">
                          <h3 className="text-lg font-semibold text-foreground">{workflow.label}</h3>
                          <StatusPill status={readiness} />
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-warning/10 text-glow-warning border border-glow-warning/20 font-medium flex items-center gap-1">
                            <Sparkles className="w-2.5 h-2.5" /> Deck Ready
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-1">{workflow.headline}</p>
                        <p className="text-xs text-muted-foreground/70 leading-relaxed max-w-3xl">{workflow.description}</p>

                        <div className="grid md:grid-cols-3 gap-4 mt-4">
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-medium">Inputs</span>
                            <div className="flex flex-wrap items-center gap-1 mt-1">
                              <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground">{requirementLabel}</span>
                              <span className="text-[10px] px-2 py-0.5 rounded-md bg-secondary/50 text-muted-foreground">{executionModeLabel}</span>
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-medium">Outputs</span>
                            <div className="flex flex-wrap items-center gap-1 mt-1">
                              {workflow.expected_outputs.map((output) => (
                                <span key={output} className="text-[10px] px-2 py-0.5 rounded-md bg-primary/5 text-primary/80">{output}</span>
                              ))}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground/50 font-medium">Live signals</span>
                            <div className="mt-1 space-y-1.5 text-[11px] text-muted-foreground">
                              <div>{readinessCopy}</div>
                              <div>{runStats?.count ? `${runStats.count} persisted run(s). Last run: ${formatDateTime(latestRun?.timestamp)}` : 'No persisted runs captured yet.'}</div>
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-1 mt-4">
                          {workflow.badge_items.map((badge) => (
                            <span key={badge} className="text-[10px] px-2 py-0.5 rounded-md border border-border/50 bg-background/30 text-muted-foreground">{badge}</span>
                          ))}
                        </div>
                      </div>
                      <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors shrink-0 mt-3 group-hover:translate-x-1 duration-200" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
