import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  Clock,
  ExternalLink,
  FileText,
  History,
  Loader2,
  Play,
  Search,
  Sparkles,
  Link2,
} from 'lucide-react';

import { PageHeader, StatusPill, GlassCard, MetricCard } from '@/components/shared/ui-components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  buildProductArtifactUrl,
  getProductRunHistory,
  getProductRunHistoryEntry,
  rerunProductRunHistoryEntry,
  type ProductDeliveryOutput,
  type ProductRunEntry,
  type ProductWorkflowArtifact,
} from '@/lib/product-api';
import { toast } from '@/components/ui/sonner';

const STATUS_FILTERS = ['all', 'completed', 'warning', 'error'] as const;
const WINDOW_FILTERS = ['24h', '7d', '30d', 'all'] as const;
const DEFAULT_PAGE_SIZE = 25;
const WORKFLOW_ROUTE_MAP: Record<string, string> = {
  document_review: '/app/workflows/document-review',
  policy_contract_comparison: '/app/workflows/comparison',
  action_plan_evidence_review: '/app/workflows/action-plan',
  candidate_review: '/app/workflows/candidate-review',
};


type DeliveryEvent = {
  runId: string;
  workflowLabel: string;
  runTimestamp: string | null | undefined;
  key: string;
  delivery: ProductDeliveryOutput;
};

function formatDateTime(value?: string | null): string {
  if (!value) return 'n/a';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function stringifyPayload(payload: unknown): string {
  try {
    return JSON.stringify(payload ?? {}, null, 2);
  } catch {
    return String(payload ?? '');
  }
}

function deliveryOutputEntries(run: ProductRunEntry | null | undefined): Array<[string, ProductDeliveryOutput]> {
  const outputs = run?.delivery_outputs;
  if (!outputs || typeof outputs !== 'object') return [];
  return Object.entries(outputs) as Array<[string, ProductDeliveryOutput]>;
}

function dedupeArtifacts(run: ProductRunEntry | null | undefined): ProductWorkflowArtifact[] {
  const artifacts = run?.artifact_items ?? [];
  const seen = new Set<string>();
  return artifacts.filter((artifact) => {
    const key = `${artifact.artifact_type}:${artifact.path || artifact.download_name || artifact.label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}



function buildRecentDeliveryEvents(sourceRuns: ProductRunEntry[], preferredRunId?: string | null, limit = 8): DeliveryEvent[] {
  const events: DeliveryEvent[] = [];
  for (const run of sourceRuns) {
    const outputs = deliveryOutputEntries(run);
    for (const [key, delivery] of outputs) {
      events.push({
        runId: run.id,
        workflowLabel: run.workflow_label,
        runTimestamp: run.timestamp,
        key,
        delivery,
      });
    }
  }

  const score = (event: DeliveryEvent) => {
    const deliveryTime = event.delivery.timestamp ? new Date(event.delivery.timestamp).getTime() : 0;
    const runTime = event.runTimestamp ? new Date(event.runTimestamp).getTime() : 0;
    const preferredBoost = preferredRunId && event.runId === preferredRunId ? 1 : 0;
    return { preferredBoost, time: deliveryTime || runTime || 0 };
  };

  const deduped = new Map<string, DeliveryEvent>();
  for (const event of events) {
    const key = `${event.runId}:${event.key}:${event.delivery.timestamp || event.runTimestamp || ''}`;
    if (!deduped.has(key)) deduped.set(key, event);
  }

  return Array.from(deduped.values())
    .sort((left, right) => {
      const leftScore = score(left);
      const rightScore = score(right);
      if (leftScore.preferredBoost !== rightScore.preferredBoost) {
        return rightScore.preferredBoost - leftScore.preferredBoost;
      }
      return rightScore.time - leftScore.time;
    })
    .slice(0, limit);
}

function inWindow(timestamp: string | null | undefined, filter: (typeof WINDOW_FILTERS)[number]): boolean {
  if (filter === 'all') return true;
  if (!timestamp) return false;
  const value = new Date(timestamp).getTime();
  if (Number.isNaN(value)) return true;
  const now = Date.now();
  const windowMs = filter === '24h' ? 24 * 60 * 60 * 1000 : filter === '7d' ? 7 * 24 * 60 * 60 * 1000 : 30 * 24 * 60 * 60 * 1000;
  return now - value <= windowMs;
}

export default function RunHistoryPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>('all');
  const [windowFilter, setWindowFilter] = useState<(typeof WINDOW_FILTERS)[number]>('7d');
  const [workflowFilter, setWorkflowFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [selectedRunId, setSelectedRunId] = useState('');
  const [lastRerunId, setLastRerunId] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(DEFAULT_PAGE_SIZE);

  const runHistoryQuery = useQuery({
    queryKey: ['product-run-history'],
    queryFn: getProductRunHistory,
    refetchOnWindowFocus: false,
  });

  const runs = useMemo(() => {
    const sourceRuns = runHistoryQuery.data?.runs ?? [];
    return [...sourceRuns].sort((left, right) => {
      const leftTime = left.timestamp ? new Date(left.timestamp).getTime() : 0;
      const rightTime = right.timestamp ? new Date(right.timestamp).getTime() : 0;
      return rightTime - leftTime;
    });
  }, [runHistoryQuery.data?.runs]);

  const workflowOptions = useMemo(
    () => ['all', ...Array.from(new Set(runs.map((run) => run.workflow_label).filter(Boolean)))],
    [runs],
  );

  const filteredRuns = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return runs.filter((run) => {
      const matchesStatus = statusFilter === 'all' || run.status === statusFilter;
      const matchesWorkflow = workflowFilter === 'all' || run.workflow_label === workflowFilter;
      const matchesWindow = inWindow(run.timestamp, windowFilter);
      const matchesSearch =
        !needle ||
        `${run.id} ${run.workflow_label} ${(run.documents || []).join(' ')} ${run.recommendation || ''}`.toLowerCase().includes(needle);
      return matchesStatus && matchesWorkflow && matchesWindow && matchesSearch;
    });
  }, [runs, search, statusFilter, workflowFilter, windowFilter]);

  const visibleRuns = useMemo(() => filteredRuns.slice(0, visibleCount), [filteredRuns, visibleCount]);
  const hiddenRunCount = Math.max(filteredRuns.length - visibleRuns.length, 0);

  useEffect(() => {
    setVisibleCount(DEFAULT_PAGE_SIZE);
  }, [search, statusFilter, workflowFilter, windowFilter]);

  useEffect(() => {
    if (!visibleRuns.length) {
      setSelectedRunId('');
      return;
    }
    if (!selectedRunId || !visibleRuns.some((run) => run.id === selectedRunId)) {
      setSelectedRunId(visibleRuns[0].id);
    }
  }, [visibleRuns, selectedRunId]);

  const selectedRun = visibleRuns.find((run) => run.id === selectedRunId) ?? visibleRuns[0] ?? null;

  const detailQuery = useQuery({
    queryKey: ['product-run-history-entry', selectedRun?.id],
    queryFn: () => getProductRunHistoryEntry(selectedRun?.id || ''),
    enabled: Boolean(selectedRun?.id),
    refetchOnWindowFocus: false,
  });

  const rerunMutation = useMutation({
    mutationFn: (runId: string) => rerunProductRunHistoryEntry(runId),
    onSuccess: async (payload) => {
      setLastRerunId(payload.run_id || null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['product-run-history'] }),
        queryClient.invalidateQueries({ queryKey: ['product-run-history-entry'] }),
        queryClient.invalidateQueries({ queryKey: ['product-artifacts'] }),
        queryClient.invalidateQueries({ queryKey: ['product-command-center'] }),
      ]);
      if (payload.run_id) setSelectedRunId(payload.run_id);
      toast.success(`Rerun completed${payload.run_id ? ` · new run id ${payload.run_id}` : ''}.`);
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Run rerun failed.');
    },
  });

  const detailRun = detailQuery.data?.run ?? selectedRun;
  const artifacts = dedupeArtifacts(detailRun);
  const deliveryOutputs = deliveryOutputEntries(detailRun);
  const recentDeliveryEvents = useMemo(() => buildRecentDeliveryEvents(filteredRuns.length ? filteredRuns : runs, detailRun?.id ?? selectedRun?.id ?? null), [filteredRuns, runs, detailRun?.id, selectedRun?.id]);
  const workflowRoute = detailRun?.workflow_id ? WORKFLOW_ROUTE_MAP[detailRun.workflow_id] : undefined;
  const latestSummary = detailRun?.result_sections && typeof detailRun.result_sections === 'object' && 'summary' in detailRun.result_sections
    ? String((detailRun.result_sections as { summary?: string | null }).summary || '')
    : '';
  const resultSections = detailRun?.result_sections && typeof detailRun.result_sections === 'object' ? detailRun.result_sections as Record<string, unknown> : null;
  const requestPayloadText = detailRun?.request_payload ? stringifyPayload(detailRun.request_payload) : '';
  const responsePayloadText = detailRun?.response_payload ? stringifyPayload(detailRun.response_payload) : '';

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Run History" description="Persisted workflow executions, rerun controls, request/response payloads and artifact links backed by the live Product API registry.">
        {workflowRoute ? (
          <Link to={workflowRoute}>
            <Button className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs">
              <Sparkles className="mr-2 h-3.5 w-3.5" /> Open workflow
            </Button>
          </Link>
        ) : null}
      </PageHeader>

      {runHistoryQuery.isError && (
        <GlassCard className="mb-6 border border-glow-warning/20">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="h-4 w-4" />
            The live run registry could not be loaded completely. Use the filters below after refresh to recover the latest persisted entries.
          </div>
        </GlassCard>
      )}

      <div className="grid gap-3 md:grid-cols-4 mb-6">
        <MetricCard label="Total runs" value={runHistoryQuery.data?.summary.total_runs ?? runs.length} icon={History} delay={0.05} />
        <MetricCard label="Completed" value={runHistoryQuery.data?.summary.completed_runs ?? runs.filter((run) => run.status === 'completed').length} icon={Sparkles} glowColor="success" delay={0.08} />
        <MetricCard label="Warnings" value={runHistoryQuery.data?.summary.warning_runs ?? runs.filter((run) => run.status === 'warning').length} icon={AlertTriangle} glowColor="warning" delay={0.11} />
        <MetricCard label="Errors" value={runHistoryQuery.data?.summary.error_runs ?? runs.filter((run) => run.status === 'error').length} icon={FileText} glowColor="accent" delay={0.14} />
      </div>

      <GlassCard className="mb-4">
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_180px_220px_180px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by run id, workflow, document name or recommendation..." className="h-9 pl-9 text-xs" />
          </div>
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as (typeof STATUS_FILTERS)[number])}>
            <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              {STATUS_FILTERS.map((status) => (
                <SelectItem key={status} value={status} className="text-xs capitalize">{status}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={workflowFilter} onValueChange={setWorkflowFilter}>
            <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue placeholder="Workflow" /></SelectTrigger>
            <SelectContent>
              {workflowOptions.map((workflow) => (
                <SelectItem key={workflow} value={workflow} className="text-xs">{workflow === 'all' ? 'All workflows' : workflow}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={windowFilter} onValueChange={(value) => setWindowFilter(value as (typeof WINDOW_FILTERS)[number])}>
            <SelectTrigger className="h-9 text-xs bg-secondary/30"><SelectValue placeholder="Window" /></SelectTrigger>
            <SelectContent>
              {WINDOW_FILTERS.map((windowValue) => (
                <SelectItem key={windowValue} value={windowValue} className="text-xs">{windowValue === 'all' ? 'All time' : `Last ${windowValue}`}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </GlassCard>

      <div className="mb-6 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <Badge variant="outline" className="border-border/60 text-[10px] text-muted-foreground">
          Showing {visibleRuns.length} of {filteredRuns.length}
        </Badge>
        <span>The list defaults to recent runs so the page stays operational instead of turning into a raw log dump.</span>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(460px,0.95fr)]">
        <div className="space-y-3">
          {!visibleRuns.length && (
            <GlassCard>
              <div className="text-xs text-muted-foreground">
                {runHistoryQuery.isLoading ? 'Loading persisted workflow runs...' : 'No runs matched the current filters. Expand the time window or execute a workflow to populate this registry.'}
              </div>
            </GlassCard>
          )}
          {visibleRuns.map((run, index) => (
            <motion.button
              type="button"
              key={run.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.06 + index * 0.03 }}
              onClick={() => setSelectedRunId(run.id)}
              className={`glass w-full rounded-xl p-4 text-left transition-all duration-200 ${run.id === selectedRun?.id ? 'border-primary/40 bg-primary/5' : 'hover:border-primary/20'}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <StatusPill status={run.status} />
                    <h3 className="text-sm font-medium text-foreground">{run.workflow_label}</h3>
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{(run.documents || []).join(', ') || 'No document labels captured'}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {formatDateTime(run.timestamp)}</span>
                    <span>{run.duration_label || 'duration n/a'}</span>
                    {typeof run.findings_count === 'number' ? <span>{run.findings_count} finding(s)</span> : null}
                    {run.recommendation ? <span className="truncate">{run.recommendation}</span> : null}
                  </div>
                </div>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
              </div>
            </motion.button>
          ))}
          {hiddenRunCount > 0 ? (
            <Button variant="outline" className="w-full h-9 text-xs border-border/50" onClick={() => setVisibleCount((current) => current + DEFAULT_PAGE_SIZE)}>
              Show {Math.min(DEFAULT_PAGE_SIZE, hiddenRunCount)} more runs
            </Button>
          ) : null}
        </div>

        <GlassCard className="min-h-[620px]">
          {!detailRun ? (
            <div className="text-xs text-muted-foreground">Select a run to inspect request payloads, backend result sections and rerun options.</div>
          ) : (
            <div className="space-y-5">
              {detailQuery.isError ? (
                <div className="rounded-lg border border-glow-warning/20 bg-glow-warning/5 px-3 py-2 text-[11px] text-glow-warning">
                  Some older runs only expose summary rows. Rerun and the list itself remain usable; full detail could not be reconstructed for this selection.
                </div>
              ) : null}

              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="text-lg font-semibold text-foreground">{detailRun.workflow_label}</h3>
                    <StatusPill status={detailRun.status} />
                  </div>
                  <p className="text-xs text-muted-foreground">Run id {detailRun.id} · {formatDateTime(detailRun.timestamp)}</p>
                  {lastRerunId && detailRun.id === lastRerunId ? <p className="mt-1 text-[11px] text-glow-success">This is the latest rerun generated from the history surface.</p> : null}
                </div>
                <div className="flex items-center gap-2">
                  {workflowRoute ? (
                    <Link to={workflowRoute}>
                      <Button variant="outline" size="sm" className="h-8 text-[10px] border-border/50">Open flow</Button>
                    </Link>
                  ) : null}
                  <Button
                    size="sm"
                    className="h-8 text-[10px]"
                    disabled={!detailRun.can_rerun || rerunMutation.isPending}
                    onClick={() => rerunMutation.mutate(detailRun.id)}
                  >
                    {rerunMutation.isPending ? <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" /> : <Play className="mr-1 h-3.5 w-3.5" />}
                    {detailRun.can_rerun ? 'Rerun from history' : 'Rerun unavailable'}
                  </Button>
                </div>
              </div>

              {latestSummary ? (
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-4">
                  <p className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">Latest summary</p>
                  <p className="text-sm leading-relaxed text-foreground">{latestSummary}</p>
                </div>
              ) : null}

              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Documents</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{detailRun.documents?.length ?? 0}</p>
                </div>
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Artifacts</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{artifacts.length}</p>
                </div>
                <div className="rounded-lg border border-border/40 bg-secondary/10 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Duration</p>
                  <p className="mt-1 text-sm font-medium text-foreground">{detailRun.duration_label || 'n/a'}</p>
                </div>
              </div>


              {recentDeliveryEvents.length ? (
                <div data-testid="delivery-history-section">
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <div>
                      <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium">External deliveries</h4>
                      <p className="mt-1 text-[11px] text-muted-foreground">Recent Trello, Notion and Nextcloud outputs captured in run history. Selected-run deliveries are pinned first.</p>
                    </div>
                    <Badge variant="outline" className="border-border/60 text-[10px] text-muted-foreground">{recentDeliveryEvents.length} recent item(s)</Badge>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    {recentDeliveryEvents.map((event) => {
                      const delivery = event.delivery;
                      const isSelectedRun = event.runId === detailRun?.id;
                      return (
                        <div key={`${event.runId}:${event.key}:${delivery.timestamp || event.runTimestamp || ''}`} className={`rounded-lg border p-3 ${isSelectedRun ? 'border-primary/30 bg-primary/5' : 'border-border/40 bg-secondary/10'}`}>
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <p className="text-xs font-medium text-foreground capitalize">{delivery.label || delivery.target || event.key}</p>
                                {isSelectedRun ? <Badge className="h-5 rounded-full bg-primary/15 px-2 text-[10px] text-primary hover:bg-primary/15">Selected run</Badge> : null}
                              </div>
                              <p className="mt-1 text-[11px] text-muted-foreground">{event.workflowLabel}</p>
                            </div>
                            <StatusPill status={delivery.status || 'pending'} />
                          </div>
                          <p className="mt-2 text-[11px] text-muted-foreground">{delivery.summary || delivery.message || 'External delivery recorded for this run.'}</p>
                          <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                            <span className="inline-flex items-center gap-1 rounded-full border border-border/50 px-2 py-1">
                              <Clock className="h-3 w-3" /> {formatDateTime(delivery.timestamp || event.runTimestamp)}
                            </span>
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 rounded-full border border-border/50 px-2 py-1 transition hover:border-primary/30 hover:text-primary"
                              onClick={() => setSelectedRunId(event.runId)}
                            >
                              <Link2 className="h-3 w-3" /> Open run
                            </button>
                          </div>
                          {delivery.url ? (
                            <Button variant="outline" size="sm" className="mt-3 h-7 text-[10px] border-border/50" onClick={() => window.open(delivery.url || '', '_blank', 'noopener,noreferrer')}>
                              Open target <ExternalLink className="ml-1 h-3 w-3" />
                            </Button>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {artifacts.length ? (
                <div>
                  <h4 className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">Linked artifacts</h4>
                  <div className="flex flex-wrap gap-2">
                    {artifacts.map((artifact) => (
                      <Button
                        key={`${artifact.artifact_type}:${artifact.path || artifact.label}`}
                        variant="outline"
                        size="sm"
                        className="h-8 text-[10px] border-border/50"
                        disabled={!artifact.path}
                        onClick={() => artifact.path && window.open(buildProductArtifactUrl(artifact.path), '_blank', 'noopener,noreferrer')}
                      >
                        {artifact.label}
                        <ExternalLink className="ml-1 h-3 w-3" />
                      </Button>
                    ))}
                  </div>
                </div>
              ) : null}

              {resultSections ? (
                <details className="rounded-lg border border-border/40 bg-secondary/10 p-0" open>
                  <summary className="cursor-pointer list-none px-3 py-2 text-xs font-medium text-foreground">Result sections</summary>
                  <div className="border-t border-border/40 p-3">
                    <pre className="max-h-[260px] overflow-auto whitespace-pre-wrap text-[11px] text-muted-foreground">{stringifyPayload(resultSections)}</pre>
                  </div>
                </details>
              ) : null}

              {requestPayloadText ? (
                <details className="rounded-lg border border-border/40 bg-secondary/10 p-0">
                  <summary className="cursor-pointer list-none px-3 py-2 text-xs font-medium text-foreground">Request payload</summary>
                  <div className="border-t border-border/40 p-3">
                    <pre className="max-h-[260px] overflow-auto whitespace-pre-wrap text-[11px] text-muted-foreground">{requestPayloadText}</pre>
                  </div>
                </details>
              ) : null}

              {responsePayloadText ? (
                <details className="rounded-lg border border-border/40 bg-secondary/10 p-0">
                  <summary className="cursor-pointer list-none px-3 py-2 text-xs font-medium text-foreground">Response payload</summary>
                  <div className="border-t border-border/40 p-3">
                    <pre className="max-h-[260px] overflow-auto whitespace-pre-wrap text-[11px] text-muted-foreground">{responsePayloadText}</pre>
                  </div>
                </details>
              ) : null}
            </div>
          )}
        </GlassCard>
      </div>
    </motion.div>
  );
}
