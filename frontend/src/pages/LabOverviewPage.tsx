import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Gauge, Activity, ShieldCheck, PieChart as PieChartIcon, ArrowRightLeft } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabOverviewPage } from '@/lib/ai-lab-data';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

const workflowChartConfig = {
  volume: { label: 'Workflow share' },
};

const reviewChartConfig = {
  rate: { label: 'Review rate' },
};

const alertStyles: Record<string, string> = {
  critical: 'border-glow-error/20 bg-glow-error/5 text-glow-error',
  warning: 'border-glow-warning/20 bg-glow-warning/5 text-glow-warning',
  info: 'border-primary/20 bg-primary/5 text-primary',
};

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

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="AI Engineering Operating Console"
        description="Unified view of runtime health, quality posture, active alerts and operational readiness across the AI Lab surfaces."
        operatorQuestion="What needs attention right now, and which surface should I open next?"
        badges={[
          {
            label: runtime?.vectorBackendStatus === 'healthy' ? 'Runtime healthy' : 'Runtime degraded',
            variant: runtime?.vectorBackendStatus === 'healthy' ? 'success' : 'warning',
          },
          { label: `${runtime?.indexedDocumentCount ?? 0} docs indexed`, variant: 'default' },
          { label: `${workflowMix.length} workflow slices`, variant: 'default' },
        ]}
        dataSource={data?.meta?.source}
      />

      {isError ? (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            AI Lab overview depends on persisted backend state. The Product API is unavailable, so no synthetic overview is shown.
          </div>
        </GlassCard>
      ) : null}

      <AiLabMetricGrid
        columns={6}
        metrics={[
          { label: 'Indexed Docs', value: runtime?.indexedDocumentCount ?? '—', icon: Activity, status: 'healthy' },
          { label: 'Total Chunks', value: runtime?.totalChunks ?? '—', icon: ArrowRightLeft, status: 'healthy' },
          { label: 'Context Pressure', value: typeof runtime?.contextPressurePct === 'number' ? `${Math.round(runtime.contextPressurePct)}%` : '—', icon: Gauge, status: (runtime?.contextPressure ?? 0) >= 0.8 ? 'warning' : 'healthy' },
          { label: 'Ingestion Health', value: runtime?.ingestionHealth ?? '—', icon: ShieldCheck, status: runtime?.ingestionHealth === 'healthy' ? 'healthy' : 'warning' },
          { label: 'Review Rate', value: `${Math.round(reviewRate)}%`, icon: AlertTriangle, status: reviewRate >= 25 ? 'warning' : 'healthy' },
          { label: 'Workflow Mix', value: workflowMix.length || '—', icon: PieChartIcon, status: 'neutral' },
        ]}
      />

      <div className="grid xl:grid-cols-[1.1fr,0.9fr] gap-4 mb-6">
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Active Alerts</h3>
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
                    <span>{new Date(alert.timestamp).toLocaleString()}</span>
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
                    <Pie data={workflowMix} dataKey="value" nameKey="name" innerRadius={42} outerRadius={72} paddingAngle={3}>
                      {workflowMix.map((item, index) => (
                        <Cell key={`${item.name}-${index}`} fill={`hsl(${210 + index * 34} 88% ${60 - index * 4}%)`} />
                      ))}
                    </Pie>
                    <ChartTooltip content={<ChartTooltipContent />} />
                  </PieChart>
                </ChartContainer>
              </div>
              <div className="space-y-2">
                {workflowMix.map((item) => (
                  <div key={item.name} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-medium text-foreground">{item.name}</span>
                      <span className="text-[10px] text-muted-foreground">{item.value} run(s)</span>
                    </div>
                  </div>
                ))}
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
                <Bar dataKey="rate" fill="hsl(217, 91%, 60%)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Review rate is a triage signal only. Use Workflow Inspector for trace-level decisions and Evals & Diagnosis for quality regressions.
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

      {kpis.length ? (
        <GlassCard>
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Consolidated KPI Strip</h3>
            {data?.meta?.source ? <DataSourceBadge source={data.meta.source} /> : null}
          </div>
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
            {kpis.map((kpi) => (
              <div key={kpi.label} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs font-medium text-foreground">{kpi.label}</span>
                  <span className={`text-[10px] font-medium ${kpi.status === 'healthy' ? 'text-glow-success' : kpi.status === 'warning' ? 'text-glow-warning' : kpi.status === 'error' ? 'text-glow-error' : 'text-muted-foreground'}`}>
                    {kpi.value}
                  </span>
                </div>
                {kpi.trend ? <p className="mt-1 text-[10px] text-muted-foreground">{kpi.trend}</p> : null}
              </div>
            ))}
          </div>
        </GlassCard>
      ) : null}
    </motion.div>
  );
}
