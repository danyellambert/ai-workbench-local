import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, AlertCircle, Info, ArrowRight, Activity, FileText, Database, Cpu, ShieldCheck, BarChart3, PieChartIcon } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { AiLabSectionIntro } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { AI_LAB_ROUTES } from '@/lib/ai-lab-navigation';
import { aiLabQueryKeys, getLabOverviewPage } from '@/lib/ai-lab-data';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { PieChart, Pie, Cell } from 'recharts';

const routeColors = ['hsl(217, 91%, 60%)', 'hsl(142, 71%, 45%)', 'hsl(38, 92%, 50%)', 'hsl(0, 84%, 60%)'];

const severityIcon: Record<string, React.ElementType> = {
  critical: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const severityStyle: Record<string, string> = {
  critical: 'border-glow-error/30 bg-glow-error/5',
  warning: 'border-glow-warning/30 bg-glow-warning/5',
  info: 'border-border/50 bg-secondary/20',
};

function getMetricIcon(label: string) {
  if (label.includes('Document')) return FileText;
  if (label.includes('Chunk')) return Database;
  if (label.includes('Run')) return Activity;
  if (label.includes('Action')) return ShieldCheck;
  if (label.includes('Model')) return Cpu;
  return BarChart3;
}

type MetricStatus = 'healthy' | 'warning' | 'error' | 'neutral';

function normalizeMetricStatus(status: string): MetricStatus {
  if (status === 'healthy' || status === 'warning' || status === 'error') return status;
  return 'neutral';
}

export default function LabOverviewPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: aiLabQueryKeys.overview,
    queryFn: getLabOverviewPage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const runtime = data?.runtime;
  const workflowMix = data?.workflow_mix ?? [];
  const alerts = data?.alerts ?? [];
  const reviewRate = data?.review_rate ?? 0;

  const chartConfig = workflowMix.reduce<Record<string, { label: string; color: string }>>((acc, item, index) => {
    acc[item.name] = { label: item.name, color: routeColors[index % routeColors.length] };
    return acc;
  }, {});

  const metrics: Array<{ label: string; value: string | number; status: MetricStatus; trend?: string; icon: LucideIcon }> = (data?.kpis ?? []).map((metric) => ({
    label: metric.label,
    value: metric.value,
    status: normalizeMetricStatus(metric.status),
    trend: metric.trend,
    icon: getMetricIcon(metric.label),
  }));

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="AI Engineering Operating Console"
        description="Unified view of runtime health, quality signals, active alerts and operational readiness."
        operatorQuestion="What needs attention right now?"
        badges={[
          { label: 'AI Lab', variant: 'default' },
          runtime
            ? {
                label: runtime.vectorBackendStatus === 'healthy' ? 'Runtime Healthy' : 'Runtime Degraded',
                variant: runtime.vectorBackendStatus === 'healthy' ? 'success' : 'warning',
              }
            : { label: isLoading ? 'Loading runtime…' : 'Runtime unavailable', variant: isError ? 'warning' : 'default' },
          runtime
            ? { label: `${runtime.indexedDocumentCount} docs indexed`, variant: 'default' }
            : { label: 'Waiting for document inventory', variant: 'default' },
        ]}
        dataSource={data?.meta.source}
      />

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            AI Lab overview could not reach the Product API. The page now avoids mock data and only renders persisted backend signals.
          </div>
        </GlassCard>
      )}

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="glass rounded-xl p-3 px-5 mb-6 flex items-center gap-6 text-[11px] overflow-x-auto"
      >
        <div className="flex items-center gap-2 shrink-0">
          <span className={`w-2 h-2 rounded-full ${runtime?.vectorBackendStatus === 'healthy' ? 'bg-glow-success animate-pulse' : 'bg-glow-warning'}`} />
          <span className="text-muted-foreground">Runtime</span>
          <span className="text-foreground font-medium">
            {runtime ? `${runtime.generationProvider} · ${runtime.generationModel.split(':')[0]}` : isLoading ? 'Loading…' : 'Unavailable'}
          </span>
        </div>
        <div className="w-px h-4 bg-border/50" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-muted-foreground">Vector</span>
          <StatusPill status={runtime?.vectorBackendStatus === 'healthy' ? 'active' : runtime ? 'degraded' : 'inactive'} />
        </div>
        <div className="w-px h-4 bg-border/50" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-muted-foreground">Context</span>
          <span className="text-foreground font-medium">
            {runtime ? `${Math.round(Math.min(runtime.contextPressure, 1) * 100)}%` : '—'}
          </span>
        </div>
        <div className="w-px h-4 bg-border/50" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-muted-foreground">Ingestion</span>
          <StatusPill status={runtime?.ingestionHealth === 'healthy' ? 'active' : runtime ? 'warning' : 'inactive'} />
        </div>
      </motion.div>

      <AiLabMetricGrid
        columns={6}
        metrics={
          metrics.length
            ? metrics
            : [
                { label: 'Indexed Documents', value: '—', status: 'neutral', icon: FileText },
                { label: 'Total Chunks', value: '—', status: 'neutral', icon: Database },
                { label: 'Runtime Runs', value: '—', status: 'neutral', icon: Activity },
                { label: 'Open Actions', value: '—', status: 'neutral', icon: ShieldCheck },
                { label: 'Evaluated Cases', value: '—', status: 'neutral', icon: Cpu },
                { label: 'Models Compared', value: '—', status: 'neutral', icon: BarChart3 },
              ]
        }
      />

      <div className="grid lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2">
          <GlassCard delay={0.15}>
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-4 h-4 text-glow-warning" />
              <h3 className="text-sm font-medium text-foreground">Active Alerts</h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-warning/10 text-glow-warning border border-glow-warning/20">
                {alerts.length}
              </span>
            </div>
            {isLoading && !alerts.length ? (
              <p className="text-xs text-muted-foreground">Loading alerts from runtime, evals and EvidenceOps…</p>
            ) : alerts.length === 0 ? (
              <p className="text-xs text-muted-foreground">No persisted alerts are active right now.</p>
            ) : (
              <div className="space-y-2">
                {alerts.map((alert, index) => {
                  const Icon = severityIcon[alert.severity] || Info;
                  return (
                    <motion.div
                      key={alert.id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.2 + index * 0.04 }}
                      className={`flex items-start gap-3 p-3 rounded-lg border ${severityStyle[alert.severity]}`}
                    >
                      <Icon
                        className={`w-4 h-4 shrink-0 mt-0.5 ${
                          alert.severity === 'critical'
                            ? 'text-glow-error'
                            : alert.severity === 'warning'
                              ? 'text-glow-warning'
                              : 'text-muted-foreground'
                        }`}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-foreground">{alert.title}</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5">{alert.detail}</p>
                      </div>
                      <span className="text-[9px] text-muted-foreground/50 shrink-0">{alert.source}</span>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </GlassCard>
        </div>

        <GlassCard delay={0.18}>
          <div className="flex items-center gap-2 mb-3">
            <PieChartIcon className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">{data?.workflow_mix_label ?? 'Workflow Mix'}</h3>
          </div>
          {workflowMix.length > 0 ? (
            <>
              <div className="h-[140px]">
                <ChartContainer config={chartConfig} className="w-full h-full">
                  <PieChart>
                    <Pie data={workflowMix} cx="50%" cy="50%" innerRadius={35} outerRadius={55} paddingAngle={3} dataKey="value">
                      {workflowMix.map((_, idx) => (
                        <Cell key={idx} fill={routeColors[idx % routeColors.length]} />
                      ))}
                    </Pie>
                    <ChartTooltip content={<ChartTooltipContent />} />
                  </PieChart>
                </ChartContainer>
              </div>
              <div className="space-y-1.5 mt-2">
                {workflowMix.map((item, index) => (
                  <div key={item.name} className="flex items-center justify-between text-[10px]">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: routeColors[index % routeColors.length] }} />
                      <span className="text-muted-foreground">{item.name}</span>
                    </div>
                    <span className="text-foreground font-medium">{item.value}</span>
                  </div>
                ))}
                <div className="pt-1.5 border-t border-border/30 flex justify-between text-[10px]">
                  <span className="text-muted-foreground">Review rate</span>
                  <span className={`font-medium ${reviewRate > 40 ? 'text-glow-warning' : 'text-glow-success'}`}>{reviewRate}%</span>
                </div>
              </div>
            </>
          ) : (
            <p className="text-xs text-muted-foreground">Workflow mix will populate once persisted workflow history is available.</p>
          )}
        </GlassCard>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
        {AI_LAB_ROUTES.filter((route) => route.key !== 'overview').map((route, index) => {
          const Icon = route.icon;
          return (
            <motion.div key={route.key} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 + index * 0.04 }}>
              <Link to={route.path} className="glass rounded-xl p-4 block hover:border-primary/30 transition-all duration-300 group h-full">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Icon className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <h4 className="text-xs font-medium text-foreground">{route.label}</h4>
                </div>
                <p className="text-[10px] text-muted-foreground leading-relaxed">{route.description}</p>
                <div className="flex items-center gap-1 mt-3 text-[10px] text-primary/60 group-hover:text-primary transition-colors">
                  <span>Open</span>
                  <ArrowRight className="w-3 h-3" />
                </div>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
