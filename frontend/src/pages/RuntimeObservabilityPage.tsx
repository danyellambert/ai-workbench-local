import { motion } from 'framer-motion';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  Cpu,
  Database,
  FileSearch,
  Activity,
  Gauge,
  HardDrive,
  GitBranch,
  Timer,
  Radar,
  Coins,
  ArrowRightLeft,
  ShieldAlert,
} from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabRuntimePage } from '@/lib/ai-lab-data';
import { Progress } from '@/components/ui/progress';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, AreaChart, Area } from 'recharts';

const latencyChartConfig = {
  seconds: { label: 'Seconds' },
};

const timelineChartConfig = {
  latencyS: { label: 'Latency (s)' },
  contextPressurePct: { label: 'Context pressure %' },
};

function asPercent(value?: number | null) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  return `${Math.round(value * 100)}%`;
}

function asNumber(value?: number | null, digits = 1) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  return value.toFixed(digits);
}

export default function RuntimeObservabilityPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: aiLabQueryKeys.runtime,
    queryFn: getLabRuntimePage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const runtime = data?.runtime;
  const generationRows = data?.generation_rows ?? [];
  const retrievalRows = data?.retrieval_rows ?? [];
  const vectorRows = data?.vector_rows ?? [];
  const diagnosticsRows = data?.diagnostics_rows ?? [];
  const opsSummary = data?.ops_summary;
  const retrievalHealth = data?.retrieval_health;
  const costSummary = data?.cost_summary;
  const latencyBreakdown = data?.latency_breakdown ?? [];
  const providerBreakdown = data?.provider_breakdown ?? [];
  const failureModes = data?.failure_modes ?? [];
  const recentTraces = data?.recent_traces ?? [];
  const timeline = data?.timeline ?? [];
  const watchouts = data?.watchouts ?? [];
  const crossSurfaceNotes = data?.cross_surface_notes ?? [];

  const contextPressure = Math.round(runtime?.contextPressurePct ?? Math.min((runtime?.contextPressure ?? 0) * 100, 100));
  const contextUtilization = Math.round(runtime?.contextUtilizationPct ?? 0);

  const strongestProvider = providerBreakdown[0];
  const highlightedTrace = recentTraces.find((trace) => !trace.success) ?? recentTraces.find((trace) => trace.needsReview) ?? recentTraces[0];

  const latencyTotal = useMemo(
    () => latencyBreakdown.reduce((sum, item) => sum + (typeof item.seconds === 'number' ? item.seconds : 0), 0),
    [latencyBreakdown],
  );

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Runtime & Observability"
        description="Operational posture for the AI runtime — configuration applied, throughput, latency, retrieval health, cost signals and recent trace issues."
        operatorQuestion="Is the runtime healthy enough to operate, and where should I escalate next if it is not?"
        badges={[
          runtime
            ? {
                label: runtime.vectorBackendStatus === 'healthy' ? 'Runtime healthy' : 'Runtime degraded',
                variant: runtime.vectorBackendStatus === 'healthy' ? 'success' : 'warning',
              }
            : { label: isLoading ? 'Loading runtime…' : 'Runtime unavailable', variant: isError ? 'warning' : 'default' },
          runtime ? { label: `${runtime.indexedDocumentCount} docs`, variant: 'default' } : { label: 'Document inventory pending', variant: 'default' },
          runtime ? { label: runtime.retrievalStrategy, variant: 'default' } : { label: 'Waiting for retrieval settings', variant: 'default' },
        ]}
        dataSource={data?.meta?.source}
      />

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            Runtime observability now depends on persisted backend state. The API is unavailable, so no mock diagnostics are shown.
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={6}
        metrics={[
          {
            label: 'Success Rate',
            value: asPercent(opsSummary?.successRate),
            status: (opsSummary?.successRate ?? 0) >= 0.8 ? 'healthy' : (opsSummary?.successRate ?? 0) >= 0.65 ? 'warning' : 'error',
            icon: Activity,
          },
          {
            label: 'p95 Latency',
            value: opsSummary?.p95LatencyS ? `${asNumber(opsSummary.p95LatencyS)}s` : '—',
            status: (opsSummary?.p95LatencyS ?? 0) >= 12 ? 'warning' : 'healthy',
            icon: Timer,
          },
          {
            label: 'Needs Review',
            value: asPercent(opsSummary?.needsReviewRate),
            status: (opsSummary?.needsReviewRate ?? 0) >= 0.2 ? 'warning' : 'healthy',
            icon: ShieldAlert,
          },
          {
            label: 'Avg Tokens / Run',
            value: typeof costSummary?.avgTotalTokens === 'number' ? Math.round(costSummary.avgTotalTokens).toLocaleString() : '—',
            status: 'neutral',
            icon: Coins,
          },
          {
            label: 'Empty Retrievals',
            value: asPercent(retrievalHealth?.emptyRetrievalRate),
            status: (retrievalHealth?.emptyRetrievalRate ?? 0) >= 0.1 ? 'warning' : 'healthy',
            icon: FileSearch,
          },
          {
            label: '24h Throughput',
            value: opsSummary?.throughput24h ?? '—',
            status: 'neutral',
            icon: Radar,
          },
        ]}
      />

      <div className="grid md:grid-cols-4 gap-3 mb-6">
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Dominant provider</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{strongestProvider ? `${strongestProvider.provider} · ${strongestProvider.model}` : 'No persisted provider slice yet'}</p>
          <p className="mt-1 text-xs text-muted-foreground">{strongestProvider ? `${strongestProvider.runs} traces · ${Math.round(strongestProvider.errorRate * 100)}% error rate` : 'Provider/model mix appears once runtime traces exist.'}</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Context utilization</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{runtime ? `${contextUtilization}%` : '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Real observed context usage from the latest trace with a recorded budget.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Context pressure</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{runtime ? `${contextPressure}%` : '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Derived pressure signal from the runtime log. Useful for triage, not a substitute for evals.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Cost visibility</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{typeof costSummary?.pricedRunRate === 'number' ? `${Math.round(costSummary.pricedRunRate * 100)}% priced` : '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">How much of runtime traffic has usable cost accounting attached.</p>
        </GlassCard>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Generation Configuration</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2.5 text-xs">
            {generationRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 border-b border-border/20 last:border-0 gap-4">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground font-mono text-[11px] text-right">{row.value}</span>
              </div>
            ))}
            {isLoading && generationRows.length === 0 ? <p className="text-xs text-muted-foreground">Loading generation configuration…</p> : null}
          </div>
        </GlassCard>

        <GlassCard delay={0.15}>
          <div className="flex items-center gap-2 mb-4">
            <FileSearch className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Retrieval Configuration</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2.5 text-xs">
            {retrievalRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 border-b border-border/20 last:border-0 gap-4">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground font-mono text-[11px] text-right">{row.value}</span>
              </div>
            ))}
            {isLoading && retrievalRows.length === 0 ? <p className="text-xs text-muted-foreground">Loading retrieval configuration…</p> : null}
          </div>
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-[0.95fr,1.05fr] gap-4 mb-6">
        <GlassCard delay={0.2}>
          <div className="flex items-center gap-2 mb-4">
            <Gauge className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Context Envelope</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-4 text-xs">
            <div>
              <div className="flex items-center justify-between gap-3 mb-2">
                <span className="text-muted-foreground">Latest measured utilization</span>
                <span className={`font-medium ${contextUtilization > 85 ? 'text-glow-warning' : 'text-glow-success'}`}>{runtime ? `${contextUtilization}%` : '—'}</span>
              </div>
              <Progress value={runtime ? contextUtilization : 0} className="h-2 bg-secondary" />
              <p className="mt-2 text-[10px] text-muted-foreground">
                Used {runtime?.contextBudgetUsed?.toLocaleString() ?? '—'} of {runtime?.contextBudgetTotal?.toLocaleString() ?? '—'} context units in the latest trace that reported a budget.
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between gap-3 mb-2">
                <span className="text-muted-foreground">Derived pressure signal</span>
                <span className={`font-medium ${contextPressure > 80 ? 'text-glow-warning' : 'text-glow-success'}`}>{runtime ? `${contextPressure}%` : '—'}</span>
              </div>
              <Progress value={runtime ? contextPressure : 0} className="h-2 bg-secondary" />
              <p className="mt-2 text-[10px] text-muted-foreground">
                Pressure is inferred from the runtime log. It is useful for operator triage, but not a replacement for regression evidence.
              </p>
            </div>
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3 text-[10px] text-muted-foreground">
              A senior AI engineer would expect both numbers: utilization tells you what the latest trace actually consumed, while pressure tells you whether the runtime is trending toward context risk.
            </div>
          </div>
        </GlassCard>

        <GlassCard delay={0.25}>
          <div className="flex items-center gap-2 mb-4">
            <Timer className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Latency Breakdown</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {latencyBreakdown.length === 0 ? (
            <p className="text-xs text-muted-foreground">Latency stage breakdown appears once persisted runtime traces include stage timings.</p>
          ) : (
            <>
              <div className="h-[220px]">
                <ChartContainer config={latencyChartConfig} className="w-full h-full">
                  <BarChart data={latencyBreakdown} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                    <XAxis dataKey="stage" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                    <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="seconds" fill="hsl(217, 91%, 60%)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ChartContainer>
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Average observed latency across stages totals {latencyTotal ? `${latencyTotal.toFixed(1)}s` : '—'}. Large generation share usually belongs here; routing logic belongs in Workflow Inspector.
              </p>
            </>
          )}
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-[1.05fr,0.95fr] gap-4 mb-6">
        <GlassCard delay={0.3}>
          <div className="flex items-center gap-2 mb-4">
            <ArrowRightLeft className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Recent Trace Trend</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {timeline.length === 0 ? (
            <p className="text-xs text-muted-foreground">Recent trace trend appears when runtime history is available.</p>
          ) : (
            <div className="h-[240px]">
              <ChartContainer config={timelineChartConfig} className="w-full h-full">
                <AreaChart data={timeline} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                  <XAxis dataKey="label" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Area type="monotone" dataKey="latencyS" stroke="hsl(217, 91%, 60%)" fill="hsl(217, 91%, 60%)" fillOpacity={0.18} />
                  <Area type="monotone" dataKey="contextPressurePct" stroke="hsl(38, 92%, 50%)" fill="hsl(38, 92%, 50%)" fillOpacity={0.12} />
                </AreaChart>
              </ChartContainer>
            </div>
          )}
          <p className="mt-2 text-[11px] text-muted-foreground">
            This trend is for operational drift only. Use Benchmarks for model comparisons and Evals & Diagnosis for real quality regressions.
          </p>
        </GlassCard>

        <GlassCard delay={0.32}>
          <div className="flex items-center gap-2 mb-4">
            <Radar className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Retrieval & Cost Signals</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-3 text-xs">
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Avg retrieved chunks</span>
                <span className="text-foreground font-medium">{typeof retrievalHealth?.avgRetrievedChunks === 'number' ? retrievalHealth.avgRetrievedChunks.toFixed(1) : '—'}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Empty retrieval rate</span>
                <span className={`font-medium ${(retrievalHealth?.emptyRetrievalRate ?? 0) >= 0.1 ? 'text-glow-warning' : 'text-glow-success'}`}>{asPercent(retrievalHealth?.emptyRetrievalRate)}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Prompt truncation rate</span>
                <span className="text-foreground font-medium">{asPercent(retrievalHealth?.truncatedPromptRate)}</span>
              </div>
            </div>
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Total tokens</span>
                <span className="text-foreground font-medium">{typeof costSummary?.totalTokens === 'number' ? Math.round(costSummary.totalTokens).toLocaleString() : '—'}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Avg cost / run</span>
                <span className="text-foreground font-medium">{typeof costSummary?.avgCostUsd === 'number' ? `$${costSummary.avgCostUsd.toFixed(4)}` : '—'}</span>
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <span className="text-muted-foreground">Priced run coverage</span>
                <span className="text-foreground font-medium">{asPercent(costSummary?.pricedRunRate)}</span>
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-[0.9fr,1.1fr] gap-4 mb-6">
        <GlassCard delay={0.34}>
          <div className="flex items-center gap-2 mb-4">
            <HardDrive className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Vector Backend & Diagnostics</h3>
            <StatusPill status={runtime?.vectorBackendStatus === 'healthy' ? 'active' : runtime ? 'degraded' : 'inactive'} />
          </div>
          <div className="space-y-2 text-xs mb-4">
            {vectorRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 gap-4 border-b border-border/20 last:border-0">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground text-right">{row.value}</span>
              </div>
            ))}
          </div>
          <div className="space-y-2 text-xs">
            {diagnosticsRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 gap-4 border-b border-border/20 last:border-0">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground text-right">{row.value}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.36}>
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Recent Trace Watchlist</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {highlightedTrace ? (
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3 mb-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-foreground">{highlightedTrace.task}</p>
                  <p className="text-[10px] text-muted-foreground">{highlightedTrace.provider} · {highlightedTrace.model}</p>
                </div>
                <StatusPill status={!highlightedTrace.success ? 'error' : highlightedTrace.needsReview ? 'warning' : 'completed'} />
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
                <span>Latency: {highlightedTrace.latencyS.toFixed(2)}s</span>
                <span>Tokens: {highlightedTrace.totalTokens.toLocaleString()}</span>
                <span>Context pressure: {highlightedTrace.contextPressurePct.toFixed(0)}%</span>
                <span>Sources: {highlightedTrace.sourceCount}</span>
              </div>
              {highlightedTrace.errorMessage ? <p className="mt-2 text-[10px] text-glow-warning">{highlightedTrace.errorMessage}</p> : null}
            </div>
          ) : null}
          <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
            {recentTraces.map((trace) => (
              <div key={trace.id} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium text-foreground">{trace.task}</p>
                    <p className="text-[10px] text-muted-foreground">{new Date(trace.timestamp).toLocaleString()} · {trace.provider}</p>
                  </div>
                  <StatusPill status={!trace.success ? 'error' : trace.needsReview ? 'warning' : 'completed'} />
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
                  <span>{trace.latencyS.toFixed(2)}s latency</span>
                  <span>{trace.totalTokens.toLocaleString()} tokens</span>
                  <span>{trace.contextPressurePct.toFixed(0)}% pressure</span>
                  <span>{trace.sourceCount} source(s)</span>
                </div>
              </div>
            ))}
            {isLoading && recentTraces.length === 0 ? <p className="text-xs text-muted-foreground">Loading recent traces…</p> : null}
          </div>
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-[0.95fr,1.05fr] gap-4">
        <GlassCard delay={0.38}>
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Failure Modes & Watchouts</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2 mb-4">
            {failureModes.length === 0 ? (
              <p className="text-xs text-muted-foreground">No recurring failure mode was derived from the persisted runtime traces.</p>
            ) : (
              failureModes.map((item) => (
                <div key={item.id} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-foreground">{item.label}</span>
                    <span className={`text-[10px] font-medium ${item.severity === 'error' ? 'text-glow-error' : 'text-glow-warning'}`}>{item.count} trace(s)</span>
                  </div>
                  {item.detail ? <p className="mt-1 text-[10px] text-muted-foreground">{item.detail}</p> : null}
                </div>
              ))
            )}
          </div>
          <div className="space-y-2">
            {watchouts.length === 0 ? (
              <p className="text-xs text-muted-foreground">No runtime watchout is currently elevated.</p>
            ) : (
              watchouts.map((note, index) => (
                <div key={`${note}-${index}`} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5 text-[11px] text-muted-foreground">
                  {note}
                </div>
              ))
            )}
          </div>
        </GlassCard>

        <GlassCard delay={0.4}>
          <div className="flex items-center gap-2 mb-4">
            <Database className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">What belongs somewhere else</h3>
            {data?.meta?.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2">
            {crossSurfaceNotes.map((note, index) => (
              <div key={`${note}-${index}`} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5 text-[11px] text-muted-foreground">
                {note}
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg border border-primary/15 bg-primary/5 px-3 py-2.5 text-[11px] text-muted-foreground">
            This is intentionally a runtime operations page, not an everything page. It should help a senior AI engineer decide whether the runtime is healthy and which specialized surface to open next.
          </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}
