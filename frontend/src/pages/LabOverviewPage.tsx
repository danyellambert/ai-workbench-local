import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  Gauge,
  Activity,
  ShieldCheck,
  PieChart as PieChartIcon,
  ArrowRightLeft,
  Database,
  Clock3,
  FolderKanban,
  Workflow,
  Terminal,
  type LucideIcon,
} from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabOverviewPage, type LabOverviewKpi } from '@/lib/ai-lab-data';
import { AI_LAB_ROUTES } from '@/lib/ai-lab-navigation';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { formatUserDateTime } from '@/lib/user-time';

const workflowChartConfig = {
  volume: { label: 'Workflow share' },
};

const reviewChartConfig = {
  rate: { label: 'Review rate' },
};

const WORKFLOW_MIX_COLOR_BY_NAME: Record<string, string> = {
  'Document Review': 'hsl(217 91% 60%)',
  'Action Plan / Evidence Review': 'hsl(142 71% 45%)',
  'Candidate Review': 'hsl(43 96% 56%)',
  'Policy / Contract Comparison': 'hsl(0 84% 60%)',
};

const WORKFLOW_MIX_FALLBACK_COLORS = [
  'hsl(217 91% 60%)',
  'hsl(142 71% 45%)',
  'hsl(43 96% 56%)',
  'hsl(0 84% 60%)',
  'hsl(231 82% 66%)',
  'hsl(278 72% 64%)',
];

const alertStyles: Record<string, string> = {
  critical: 'border-glow-error/20 bg-glow-error/5 text-glow-error',
  warning: 'border-glow-warning/20 bg-glow-warning/5 text-glow-warning',
  info: 'border-primary/20 bg-primary/5 text-primary',
};


type MetricStatus = 'healthy' | 'warning' | 'error' | 'neutral';

type MetricGridItem = {
  label: string;
  value: string | number;
  status?: MetricStatus;
  trend?: string;
  icon?: LucideIcon;
};

function getWorkflowMixColor(name: string, index: number) {
  return WORKFLOW_MIX_COLOR_BY_NAME[name] || WORKFLOW_MIX_FALLBACK_COLORS[index % WORKFLOW_MIX_FALLBACK_COLORS.length];
}

function normalizeStatus(status?: string | null): string {
  const value = String(status || '').trim().toLowerCase();
  if (!value) return 'pending';
  if (value === 'healthy' || value === 'connected' || value === 'indexed' || value === 'ready') return 'active';
  if (value === 'critical' || value === 'failed' || value === 'error') return 'error';
  if (value === 'warning' || value === 'degraded') return 'warning';
  return value;
}

function formatRuntimeLabel(runtime: Record<string, unknown>) {
  const provider = String(runtime?.generationProvider || '').trim();
  const model = String(runtime?.generationModel || '').trim();
  if (provider && model) return `${provider} · ${model}`;
  return provider || model || 'Not configured';
}

function getAlertSummaryStatus(alerts: Array<{ severity?: string }>) {
  if (alerts.some((alert) => alert.severity === 'critical')) return 'error';
  if (alerts.some((alert) => alert.severity === 'warning')) return 'warning';
  return alerts.length ? 'active' : 'pending';
}

function getMetricIcon(label: string) {
  const value = label.toLowerCase();
  if (value.includes('chunk')) return Database;
  if (value.includes('latency')) return Clock3;
  if (value.includes('mcp')) return Terminal;
  if (value.includes('workflow') || value.includes('run')) return Workflow;
  if (value.includes('eval') || value.includes('pass')) return ShieldCheck;
  if (value.includes('action')) return FolderKanban;
  if (value.includes('review')) return AlertTriangle;
  return Activity;
}

function formatMetricValue(value: unknown): string | number {
  if (typeof value === 'string' || typeof value === 'number') return value;
  if (value == null) return '—';
  return String(value);
}

function formatLatencyDelta(delta: unknown): string | undefined {
  if (typeof delta !== 'number' || !Number.isFinite(delta) || Math.abs(delta) < 0.05) return undefined;
  const rounded = Math.round(delta * 10) / 10;
  const prefix = rounded > 0 ? '+' : '';
  return `${prefix}${rounded.toFixed(1)}s`;
}

function getLatencyTrendFromRuntime(runtime: Record<string, unknown>): string | undefined {
  return formatLatencyDelta(
    runtime.avgLatencyDeltaS ??
      runtime.avg_latency_delta_s ??
      runtime.latencyDeltaS ??
      runtime.latency_delta_s ??
      runtime.avgLatencyDelta ??
      runtime.avg_latency_delta
  );
}

function pickTopMetrics(
  kpis: LabOverviewKpi[],
  reviewRate: number,
  runtime: Record<string, unknown>,
  workflowMix: Array<{ name: string; value: number }>
): MetricGridItem[] {
  const preferredMatchers = [
    /indexed/i,
    /chunk/i,
    /(workflow runs|completed runs|total runs|runs)/i,
    /(open actions|active mcp tools|mcp)/i,
    /(eval pass rate|pass rate)/i,
    /(avg latency|average latency|latency)/i,
  ];

  const chosen: LabOverviewKpi[] = [];
  const usedLabels = new Set<string>();
  const runtimeLatencyTrend = getLatencyTrendFromRuntime(runtime);

  preferredMatchers.forEach((matcher) => {
    const found = kpis.find((kpi) => !usedLabels.has(kpi.label) && matcher.test(kpi.label));
    if (found) {
      chosen.push(found);
      usedLabels.add(found.label);
    }
  });

  kpis.forEach((kpi) => {
    if (!usedLabels.has(kpi.label) && chosen.length < 6) {
      chosen.push(kpi);
      usedLabels.add(kpi.label);
    }
  });

  if (!chosen.length) {
    return [
      { label: 'Indexed Documents', value: formatMetricValue(runtime.indexedDocumentCount), status: 'healthy', icon: Activity },
      { label: 'Total Chunks', value: formatMetricValue(runtime.totalChunks), status: 'healthy', icon: Database },
      { label: 'Review Rate', value: `${Math.round(reviewRate)}%`, status: reviewRate >= 25 ? 'warning' : 'healthy', icon: AlertTriangle },
      { label: 'Workflow Mix', value: workflowMix.length || '—', status: 'neutral', icon: PieChartIcon },
    ];
  }

  return chosen.slice(0, 6).map((metric) => {
    const isLatencyMetric = /(avg latency|average latency|latency)/i.test(metric.label);

    return {
      label: metric.label,
      value: formatMetricValue(metric.value),
      status: metric.status,
      trend: metric.trend || (isLatencyMetric ? runtimeLatencyTrend : undefined),
      icon: getMetricIcon(metric.label),
    };
  });
}

export default function LabOverviewPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: aiLabQueryKeys.overview,
    queryFn: getLabOverviewPage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const runtime = data?.runtime ?? {};
  const kpis = data?.kpis ?? [];
  const alerts = data?.alerts ?? [];
  const workflowMix = data?.workflow_mix ?? [];
  const reviewRate = typeof data?.review_rate === 'number' ? data.review_rate : 0;
  const reviewData = [
    { name: 'Needs review', rate: reviewRate },
    { name: 'No review', rate: Math.max(100 - reviewRate, 0) },
  ];

  const topMetrics = pickTopMetrics(kpis, reviewRate, runtime, workflowMix);
  const runtimeStatus = normalizeStatus(typeof runtime?.vectorBackendStatus === 'string' ? runtime.vectorBackendStatus : undefined);
  const alertSummaryStatus = getAlertSummaryStatus(alerts);
  const surfaceLinks = AI_LAB_ROUTES.filter((route) => route.key !== 'overview');

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="lab-overview-header">
        <AiLabSectionIntro
          title="AI Engineering Operating Console"
        description="Unified view of runtime health, quality signals, active alerts and operational readiness."
        operatorQuestion="What needs attention right now?"
        badges={[
          { label: 'AI Lab', variant: 'default' },
          {
            label: runtime?.vectorBackendStatus === 'healthy' ? 'Runtime Healthy' : 'Runtime Degraded',
            variant: runtime?.vectorBackendStatus === 'healthy' ? 'success' : 'warning',
          },
        ]}
        dataSource={data?.meta?.source}
        surfaceStatus={data?.status}
        degradedReason={data?.degraded_reason}
        />
      </div>

      {isError ? (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            AI Lab overview depends on persisted backend state. The Product API is unavailable, so no synthetic overview is shown.
          </div>
        </GlassCard>
      ) : null}

      <GlassCard className="mb-6 py-4" data-tour="lab-overview-status-strip">
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-muted-foreground">
          <div className="flex items-center gap-2 min-w-0">
            <span className="h-2.5 w-2.5 rounded-full bg-glow-success shrink-0" aria-hidden="true" />
            <span className="uppercase tracking-wide text-[10px] text-muted-foreground/80">Runtime</span>
            <span className="text-foreground truncate">{formatRuntimeLabel(runtime)}</span>
          </div>

          <div className="hidden h-4 w-px bg-border/60 lg:block" />

          <div className="flex items-center gap-2 min-w-0">
            <span className="uppercase tracking-wide text-[10px] text-muted-foreground/80">Vector</span>
            <StatusPill status={runtimeStatus} />
          </div>

          <div className="hidden h-4 w-px bg-border/60 lg:block" />

          <div className="flex items-center gap-2 min-w-0">
            <span className="uppercase tracking-wide text-[10px] text-muted-foreground/80">Alerts</span>
            <span className="text-foreground">{alerts.length}</span>
            <StatusPill status={alertSummaryStatus} />
          </div>

          {data?.meta?.updated_at ? (
            <>
              <div className="hidden h-4 w-px bg-border/60 lg:block" />
              <div className="flex items-center gap-2 min-w-0">
                <span className="uppercase tracking-wide text-[10px] text-muted-foreground/80">Updated</span>
                <span className="text-foreground">{formatUserDateTime(data.meta.updated_at)}</span>
              </div>
            </>
          ) : null}
        </div>
      </GlassCard>

      <div data-tour="lab-overview-metrics">
        <AiLabMetricGrid columns={6} metrics={topMetrics} />
      </div>

      <div className="grid xl:grid-cols-[1.1fr,0.9fr] gap-4 mb-6" data-tour="lab-overview-signals">
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Active Alerts</h3>
            <span className="inline-flex items-center justify-center rounded-full border border-glow-warning/20 bg-glow-warning/10 px-2 py-0.5 text-[10px] font-medium text-glow-warning">
              {alerts.length}
            </span>
            {data?.meta?.source ? <DataSourceBadge source={data.meta.source} /> : null}
          </div>
          {isLoading && !alerts.length ? (
            <p className="text-xs text-muted-foreground">Loading consolidated alert stream…</p>
          ) : alerts.length === 0 ? (
            <p className="text-xs text-muted-foreground">No alerts are currently elevated in the persisted AI Lab state.</p>
          ) : (
            <div className="space-y-2">
              {alerts.map((alert) => (
                <div key={alert.id} className={`rounded-lg border px-3 py-2.5 ${alertStyles[alert.severity] || alertStyles.info}`}>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-medium">{alert.title}</p>
                    <StatusPill status={alert.severity === 'critical' ? 'error' : alert.severity === 'warning' ? 'warning' : 'active'} />
                  </div>
                  <p className="mt-1 text-[11px] text-foreground/80">{alert.detail}</p>
                  <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span>{alert.source}</span>
                    <span>{formatUserDateTime(alert.timestamp)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <PieChartIcon className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Workflow Mix</h3>
            {data?.meta?.source ? <DataSourceBadge source={data.meta.source} /> : null}
          </div>
          {workflowMix.length === 0 ? (
            <p className="text-xs text-muted-foreground">Workflow distribution appears once the product runtime has persisted workflow history.</p>
          ) : (
            <div className="grid lg:grid-cols-[0.9fr,1.1fr] gap-4 items-center">
              <div className="h-[200px]">
                <ChartContainer config={workflowChartConfig} className="w-full h-full">
                  <PieChart>
                    <Pie
                      data={workflowMix}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={42}
                      outerRadius={72}
                      paddingAngle={3}
                      stroke="hsl(var(--background))"
                      strokeWidth={2}
                    >
                      {workflowMix.map((item, index) => (
                        <Cell key={`${item.name}-${index}`} fill={getWorkflowMixColor(item.name, index)} />
                      ))}
                    </Pie>
                    <ChartTooltip content={<ChartTooltipContent />} />
                  </PieChart>
                </ChartContainer>
              </div>
              <div className="space-y-2">
                {workflowMix.map((item, index) => {
                  const color = getWorkflowMixColor(item.name, index);
                  return (
                    <div key={item.name} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 min-w-0">
                          <span
                            className="h-2.5 w-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: color, boxShadow: '0 0 0 1px hsl(var(--border))' }}
                            aria-hidden="true"
                          />
                          <span className="text-xs font-medium text-foreground">{item.name}</span>
                        </div>
                        <span className="text-[10px] text-muted-foreground whitespace-nowrap">{item.value} run(s)</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-[1.05fr,0.95fr] gap-4 mb-6">
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <Gauge className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Review Pressure Snapshot</h3>
            {data?.meta?.source ? <DataSourceBadge source={data.meta.source} /> : null}
          </div>
          <div className="h-[220px]">
            <ChartContainer config={reviewChartConfig} className="w-full h-full">
              <BarChart data={reviewData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="rate" fill="hsl(217 91% 60%)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Review rate is a triage signal only. Use Workflow Inspector for trace-level decisions and Evals &amp; Diagnosis for quality regressions.
          </p>
        </GlassCard>

        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <ArrowRightLeft className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Surface Boundaries</h3>
            {data?.meta?.source ? <DataSourceBadge source={data.meta.source} /> : null}
          </div>
          <div className="space-y-2">
            {(data?.cross_surface_notes ?? []).map((note, index) => (
              <div key={`${note}-${index}`} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5 text-[11px] text-muted-foreground">
                {note}
              </div>
            ))}
            {!data?.cross_surface_notes?.length ? (
              <p className="text-xs text-muted-foreground">Cross-surface guidance will appear once the overview payload is connected.</p>
            ) : null}
          </div>
        </GlassCard>
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3" data-tour="lab-overview-surface-map">
        {surfaceLinks.map((route) => {
          const Icon = route.icon;
          return (
            <Link key={route.key} to={route.path} className="block group">
              <div className="rounded-xl border border-border/30 bg-secondary/20 p-4 h-full transition-all duration-200 hover:border-primary/35 hover:bg-secondary/30 hover:-translate-y-0.5">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-xs text-primary font-medium whitespace-nowrap">Open →</span>
                </div>
                <h4 className="text-sm font-medium text-foreground">{route.label}</h4>
                <p className="mt-2 text-[11px] text-muted-foreground">{route.description}</p>
              </div>
            </Link>
          );
        })}
      </div>
    </motion.div>
  );
}
