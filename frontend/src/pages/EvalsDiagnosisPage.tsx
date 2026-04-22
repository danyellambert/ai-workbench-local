import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Eye, Clock, TrendingDown, BarChart3, Activity } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabEvalsPage } from '@/lib/ai-lab-data';
import type { LabEvalVerdict, LabEvalsCase } from '@/lib/ai-lab-data';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';

const verdictStyle: Record<LabEvalVerdict, string> = {
  PASS: 'bg-glow-success/10 text-glow-success border-glow-success/20',
  WARN: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
  FAIL: 'bg-glow-error/10 text-glow-error border-glow-error/20',
};

const verdictChartConfig = {
  Pass: { label: 'Pass', color: 'hsl(142, 71%, 45%)' },
  Warn: { label: 'Warn', color: 'hsl(38, 92%, 50%)' },
  Fail: { label: 'Fail', color: 'hsl(0, 84%, 60%)' },
};

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function statusLabel(status?: string) {
  if (status === 'live') return 'Live + historical';
  if (status === 'derived-live') return 'Historical baseline only';
  if (status === 'empty') return 'Waiting for product usage';
  return 'Product scoped';
}

export default function EvalsDiagnosisPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: aiLabQueryKeys.evals,
    queryFn: getLabEvalsPage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const suites = data?.suites ?? [];
  const cases = data?.cases ?? [];
  const historicalCases = data?.historicalCases ?? [];
  const liveCases = data?.liveCases ?? [];
  const totals = data?.totals ?? { total: 0, pass: 0, warn: 0, fail: 0, review: 0 };
  const liveTotals = data?.liveTotals ?? { total: 0, pass: 0, warn: 0, fail: 0, review: 0 };
  const passRate = data?.passRate ?? 0;
  const livePassRate = data?.livePassRate ?? 0;
  const providerBreakdown = data?.providerBreakdown ?? [];
  const taskBreakdown = data?.taskBreakdown ?? [];
  const liveProviderBreakdown = data?.liveProviderBreakdown ?? [];
  const liveTaskBreakdown = data?.liveTaskBreakdown ?? [];
  const liveWorkflowBreakdown = data?.liveWorkflowBreakdown ?? [];
  const watchlist = data?.watchlist ?? [];
  const investigateFirst = data?.investigateFirst ?? cases.filter((item) => item.verdict === 'FAIL');
  const activeWorkflowLabels = data?.scope?.observedWorkflowLabels ?? [];
  const activeTaskTypes = data?.scope?.observedTaskTypes ?? [];

  const suiteChartData = suites.map((suite) => ({
    name: suite.name,
    Pass: suite.pass,
    Warn: suite.warn,
    Fail: suite.fail,
  }));

  const liveWorkflowChartData = liveWorkflowBreakdown.map((workflow) => ({
    name: workflow.label,
    Pass: workflow.pass,
    Warn: workflow.warn,
    Fail: workflow.fail,
  }));

  const suiteLeaderboard = [...suites].sort((a, b) => (b.pass / Math.max(b.total, 1)) - (a.pass / Math.max(a.total, 1)));
  const liveWorkflowLeaderboard = [...liveWorkflowBreakdown].sort((a, b) => ((b.pass / Math.max(b.total, 1)) - (a.pass / Math.max(a.total, 1))) || (b.total - a.total));
  const recentCases = cases.slice(0, 80);

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Evals & Diagnosis"
        description="Product-scoped quality measurement, regression detection and diagnostic investigation for workflows actually used by the current product."
        operatorQuestion="Which active product workflows are healthy live, and where is the historical baseline regressing?"
        badges={[
          { label: `${formatPercent(passRate)} historical pass`, variant: passRate >= 85 ? 'success' : passRate >= 70 ? 'warning' : 'error' },
          { label: `${liveTotals.total} live evals`, variant: liveTotals.total > 0 ? 'success' : 'warning' },
          { label: `${activeTaskTypes.length} active tasks`, variant: activeTaskTypes.length > 0 ? 'success' : 'warning' },
        ]}
        dataSource={data?.meta.source}
        surfaceStatus={data?.status}
        degradedReason={data?.degraded_reason}
      />

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            This page now scopes to product-observed workflows only. The Product API is unavailable, so live product evals could not be refreshed.
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={5}
        metrics={[
          { label: 'Historical Pass', value: `${passRate}%`, icon: ShieldCheck, status: passRate >= 85 ? 'healthy' : passRate >= 70 ? 'warning' : 'error' },
          { label: 'Historical Cases', value: totals.total, icon: CheckCircle2, status: totals.total > 0 ? 'neutral' : 'warning' },
          { label: 'Live Pass', value: `${livePassRate}%`, icon: Activity, status: liveTotals.total > 0 ? (livePassRate >= 85 ? 'healthy' : livePassRate >= 70 ? 'warning' : 'error') : 'neutral' },
          { label: 'Live Runs', value: liveTotals.total, icon: Clock, status: liveTotals.total > 0 ? 'healthy' : 'warning' },
          { label: 'Active Tasks', value: activeTaskTypes.length, icon: Eye, status: activeTaskTypes.length > 0 ? 'healthy' : 'warning' },
        ]}
      />

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Observed workflows</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{activeWorkflowLabels.length || '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Only workflows actually observed in product runs contribute to this page.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Historical baseline</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{statusLabel(data?.status)}</p>
          <p className="mt-1 text-xs text-muted-foreground">{historicalCases.length ? `${historicalCases.length} product-scoped historical eval cases retained.` : 'No retained historical baseline yet.'}</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Live product posture</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{liveTotals.total ? `${liveTotals.pass} pass · ${liveTotals.warn} warn · ${liveTotals.fail} fail` : 'No live evals yet'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Derived from current product workflow telemetry, not external benchmarks.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Scope filter</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{activeTaskTypes.length ? activeTaskTypes.join(', ') : 'Waiting for product usage'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Anything outside the currently used product task types is excluded from this page.</p>
        </GlassCard>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        <GlassCard delay={0.08}>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Historical Product Distribution</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {suiteChartData.length === 0 ? (
            <p className="text-xs text-muted-foreground">No product-scoped historical eval suites are recorded yet.</p>
          ) : (
            <div className="h-[220px]">
              <ChartContainer config={verdictChartConfig} className="w-full h-full">
                <BarChart data={suiteChartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                  <Bar dataKey="Pass" stackId="a" fill="hsl(142, 71%, 45%)" />
                  <Bar dataKey="Warn" stackId="a" fill="hsl(38, 92%, 50%)" />
                  <Bar dataKey="Fail" stackId="a" fill="hsl(0, 84%, 60%)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ChartContainer>
            </div>
          )}
        </GlassCard>

        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Live Workflow Verdicts</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {liveWorkflowChartData.length === 0 ? (
            <p className="text-xs text-muted-foreground">Run product workflows to populate live eval verdicts here.</p>
          ) : (
            <div className="h-[220px]">
              <ChartContainer config={verdictChartConfig} className="w-full h-full">
                <BarChart data={liveWorkflowChartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                  <Bar dataKey="Pass" stackId="a" fill="hsl(142, 71%, 45%)" />
                  <Bar dataKey="Warn" stackId="a" fill="hsl(38, 92%, 50%)" />
                  <Bar dataKey="Fail" stackId="a" fill="hsl(0, 84%, 60%)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ChartContainer>
            </div>
          )}
        </GlassCard>
      </div>

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        <GlassCard delay={0.12}>
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Historical Suite Leaderboard</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2">
            {suiteLeaderboard.length === 0 ? <p className="text-xs text-muted-foreground">No historical product suites yet.</p> : suiteLeaderboard.map((suite, index) => {
              const rate = Math.round((suite.pass / Math.max(suite.total, 1)) * 100);
              return (
                <motion.div
                  key={suite.name}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 + index * 0.04 }}
                  className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-medium text-foreground font-mono">{suite.name}</span>
                    {suite.needsReview > 0 ? <span className="text-[9px] px-1.5 py-0.5 rounded bg-glow-warning/10 text-glow-warning">{suite.needsReview} review</span> : null}
                  </div>
                  <div className="flex items-center gap-3 text-[10px]">
                    <span className="text-glow-success">{suite.pass}P</span>
                    <span className="text-glow-warning">{suite.warn}W</span>
                    <span className="text-glow-error">{suite.fail}F</span>
                    <span className={`font-medium ${rate >= 85 ? 'text-glow-success' : rate >= 70 ? 'text-glow-warning' : 'text-glow-error'}`}>{rate}%</span>
                  </div>
                </motion.div>
              );
            })}
            {isLoading && !suiteLeaderboard.length ? <p className="text-xs text-muted-foreground">Loading suite history…</p> : null}
          </div>
        </GlassCard>

        <GlassCard delay={0.15}>
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-4 h-4 text-glow-error" />
            <h3 className="text-sm font-medium text-foreground">Investigate First</h3>
          </div>
          {investigateFirst.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-8 h-8 text-glow-success/30 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">No live or historical failures are currently scoped to the active product workflows.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {investigateFirst.slice(0, 6).map((item: LabEvalsCase, index) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + index * 0.04 }}
                  className="p-3 rounded-lg border border-glow-error/20 bg-glow-error/5"
                >
                  <div className="flex items-center justify-between mb-1 gap-3">
                    <span className="text-xs font-medium text-foreground">{item.task}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground border border-border/50">{item.sourceKind === 'live' ? 'live' : 'historical'}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle.FAIL}`}>FAIL</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-muted-foreground">{item.errorDetail || item.reason || 'Failure details were not persisted for this case.'}</p>
                  <div className="flex items-center gap-3 mt-1.5 text-[9px] text-muted-foreground/60 flex-wrap">
                    <span>{item.suite}</span>
                    <span>{item.model}</span>
                    <span>{item.latency}s</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-3 gap-4 mb-6">
        <GlassCard delay={0.18}>
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Historical Provider Breakdown</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {providerBreakdown.length === 0 ? (
            <p className="text-xs text-muted-foreground">No product-scoped provider slices exist in the historical baseline yet.</p>
          ) : (
            <div className="space-y-2">
              {providerBreakdown.map((provider) => (
                <div key={provider.provider} className="flex items-center justify-between gap-4 rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                  <div>
                    <p className="text-xs font-medium text-foreground">{provider.provider}</p>
                    <p className="text-[10px] text-muted-foreground">{provider.total} cases · {provider.failures} failures</p>
                  </div>
                  <span className={`text-xs font-medium ${provider.passRate >= 85 ? 'text-glow-success' : provider.passRate >= 70 ? 'text-glow-warning' : 'text-glow-error'}`}>{provider.passRate}%</span>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard delay={0.2}>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Historical Task Breakdown</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {taskBreakdown.length === 0 ? (
            <p className="text-xs text-muted-foreground">Task slices appear only for tasks used by currently observed product workflows.</p>
          ) : (
            <div className="space-y-2">
              {taskBreakdown.slice(0, 6).map((task) => (
                <div key={task.task} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-foreground">{task.task}</span>
                    <span className={`text-[10px] font-medium ${task.passRate >= 85 ? 'text-glow-success' : task.passRate >= 70 ? 'text-glow-warning' : 'text-glow-error'}`}>{task.passRate}%</span>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground">{task.total} cases · avg score {Math.round(task.avgScore * 100)}%</p>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard delay={0.22}>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Product Watchlist</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {watchlist.length === 0 ? (
            <p className="text-xs text-muted-foreground">No live or historical watchlist items are present for currently active product workflows.</p>
          ) : (
            <div className="space-y-2">
              {watchlist.slice(0, 6).map((item) => (
                <div key={item.id} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-foreground truncate">{item.task}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground border border-border/50">{item.sourceKind === 'live' ? 'live' : 'historical'}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle[item.verdict]}`}>{item.verdict}</span>
                    </div>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground">{item.reason || item.errorDetail || 'Escalated product-scoped eval case.'}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground/70">{item.suite}{item.timestamp ? ` · ${new Date(item.timestamp).toLocaleString()}` : ''}</p>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      {(data?.diagnosis?.adaptationCandidates ?? []).length ? (
        <GlassCard className="mb-6" delay={0.2}>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Historical Adaptation Candidates</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2">
            {(data?.diagnosis?.adaptationCandidates ?? []).slice(0, 5).map((candidate) => (
              <div key={candidate.task_type} className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-foreground font-medium">{candidate.task_type}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-secondary text-muted-foreground border border-border/50">{candidate.health_label}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">{candidate.adaptation_priority}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">{candidate.recommended_action}</p>
                </div>
                <div className="text-[10px] text-right text-muted-foreground shrink-0">
                  <p>Fail rate: <span className="text-foreground">{Math.round(candidate.fail_rate * 100)}%</span></p>
                  <p>Recent: <span className="text-foreground">{Math.round(candidate.recent_fail_rate * 100)}%</span></p>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      ) : null}

      <GlassCard delay={0.25}>
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Recent Product Eval Cases</h3>
          {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50">
                {['Source', 'Task', 'Suite', 'Verdict', 'Score', 'Model', 'Latency', 'Review'].map((heading) => (
                  <th key={heading} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recentCases.map((item) => (
                <tr key={item.id} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                  <td className="px-3 py-2.5"><span className="text-[10px] px-2 py-0.5 rounded bg-secondary text-muted-foreground border border-border/50">{item.sourceKind === 'live' ? 'live' : 'historical'}</span></td>
                  <td className="px-3 py-2.5 text-xs text-foreground">{item.task}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{item.suite}</td>
                  <td className="px-3 py-2.5"><span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle[item.verdict]}`}>{item.verdict}</span></td>
                  <td className="px-3 py-2.5 text-xs text-foreground">{Math.round(item.score * 100)}%</td>
                  <td className="px-3 py-2.5 text-[10px] text-muted-foreground font-mono">{item.model}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{item.latency}s</td>
                  <td className="px-3 py-2.5">
                    {item.needsReview ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-glow-warning/10 text-glow-warning border border-glow-warning/20">Yes</span>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">No</span>
                    )}
                  </td>
                </tr>
              ))}
              {isLoading && !recentCases.length ? (
                <tr>
                  <td colSpan={8} className="px-3 py-6 text-xs text-muted-foreground">Loading product eval cases…</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </motion.div>
  );
}
