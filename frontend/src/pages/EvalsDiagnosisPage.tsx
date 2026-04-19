import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Eye, Clock, TrendingDown, BarChart3 } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabEvalsPage } from '@/lib/ai-lab-data';
import type { LabEvalVerdict } from '@/lib/ai-lab-data';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';

const verdictStyle: Record<LabEvalVerdict, string> = {
  PASS: 'bg-glow-success/10 text-glow-success border-glow-success/20',
  WARN: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
  FAIL: 'bg-glow-error/10 text-glow-error border-glow-error/20',
};

const suiteChartConfig = {
  Pass: { label: 'Pass', color: 'hsl(142, 71%, 45%)' },
  Warn: { label: 'Warn', color: 'hsl(38, 92%, 50%)' },
  Fail: { label: 'Fail', color: 'hsl(0, 84%, 60%)' },
};

export default function EvalsDiagnosisPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: aiLabQueryKeys.evals,
    queryFn: getLabEvalsPage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const suites = data?.suites ?? [];
  const cases = data?.cases ?? [];
  const totals = data?.totals ?? { total: 0, pass: 0, warn: 0, fail: 0, review: 0 };
  const passRate = data?.passRate ?? 0;
  const providerBreakdown = data?.providerBreakdown ?? [];
  const taskBreakdown = data?.taskBreakdown ?? [];
  const watchlist = data?.watchlist ?? [];
  const failCases = cases.filter((item) => item.verdict === 'FAIL');
  const warnCases = cases.filter((item) => item.verdict === 'WARN');
  const statusLabel = data?.status === 'empty' ? 'Waiting for evals' : data?.status === 'live' ? 'Live' : 'Derived live';

  const suiteChartData = suites.map((suite) => ({
    name: suite.name,
    Pass: suite.pass,
    Warn: suite.warn,
    Fail: suite.fail,
  }));

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Evals & Diagnosis"
        description="Quality measurement, regression detection and diagnostic investigation for all structured tasks."
        operatorQuestion="Where has quality regressed?"
        badges={[
          { label: `${passRate}% pass rate`, variant: passRate >= 85 ? 'success' : 'warning' },
          { label: `${totals.fail} failures`, variant: totals.fail > 0 ? 'error' : 'success' },
          { label: `${totals.review} needs review`, variant: totals.review > 0 ? 'warning' : 'success' },
        ]}
        dataSource={data?.meta.source}
      />

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            This page now uses persisted eval history from the backend. The Product API is unavailable, so mock quality dashboards are no longer displayed.
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={5}
        metrics={[
          { label: 'Pass Rate', value: `${passRate}%`, icon: ShieldCheck, status: passRate >= 85 ? 'healthy' : 'warning' },
          { label: 'Total Cases', value: totals.total, icon: CheckCircle2, status: 'neutral' },
          { label: 'Failures', value: totals.fail, icon: XCircle, status: totals.fail > 0 ? 'error' : 'healthy' },
          { label: 'Warnings', value: totals.warn, icon: AlertTriangle, status: totals.warn > 0 ? 'warning' : 'healthy' },
          { label: 'Needs Review', value: totals.review, icon: Eye, status: totals.review > 0 ? 'warning' : 'healthy' },
        ]}
      />

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Provider spread</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{providerBreakdown.length || '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Providers or models represented in persisted eval history.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Most tested provider</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{providerBreakdown[0]?.provider ?? 'No provider yet'}</p>
          <p className="mt-1 text-xs text-muted-foreground">{providerBreakdown[0] ? `${providerBreakdown[0].passRate}% pass rate across ${providerBreakdown[0].total} cases.` : 'Eval registry is empty.'}</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Task watchlist</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{watchlist.length || '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Persisted fails or review cases elevated for operator follow-up.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Eval posture</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{statusLabel}</p>
          <p className="mt-1 text-xs text-muted-foreground">{data?.degraded_reason ?? (data?.diagnosis.globalRecommendation || 'Diagnosis is computed from the persisted phase8 SQLite store.')}</p>
        </GlassCard>
      </div>

      <GlassCard className="mb-6" delay={0.08}>
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Suite Pass/Warn/Fail Distribution</h3>
          {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
        </div>
        {suiteChartData.length === 0 ? (
          <p className="text-xs text-muted-foreground">No eval suites are recorded yet.</p>
        ) : (
          <div className="h-[220px]">
            <ChartContainer config={suiteChartConfig} className="w-full h-full">
              <BarChart data={suiteChartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Legend wrapperStyle={{ fontSize: '10px' }} />
                <Bar dataKey="Pass" stackId="a" fill="hsl(142, 71%, 45%)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Warn" stackId="a" fill="hsl(38, 92%, 50%)" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Fail" stackId="a" fill="hsl(0, 84%, 60%)" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </div>
        )}
      </GlassCard>

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Suite Leaderboard</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2">
            {[...suites].sort((a, b) => (b.pass / Math.max(b.total, 1)) - (a.pass / Math.max(a.total, 1))).map((suite, index) => {
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
                    {suite.needsReview > 0 ? (
                      <span className="text-[9px] px-1.5 py-0.5 rounded bg-glow-warning/10 text-glow-warning">{suite.needsReview} review</span>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-3 text-[10px]">
                    <span className="text-glow-success">{suite.pass}P</span>
                    <span className="text-glow-warning">{suite.warn}W</span>
                    <span className="text-glow-error">{suite.fail}F</span>
                    <span className={`font-medium ${rate >= 85 ? 'text-glow-success' : 'text-glow-warning'}`}>{rate}%</span>
                  </div>
                </motion.div>
              );
            })}
            {isLoading && !suites.length ? <p className="text-xs text-muted-foreground">Loading suite history…</p> : null}
          </div>
        </GlassCard>

        <GlassCard delay={0.15}>
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className="w-4 h-4 text-glow-error" />
            <h3 className="text-sm font-medium text-foreground">Investigate First</h3>
          </div>
          {failCases.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-8 h-8 text-glow-success/30 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">No failures detected</p>
            </div>
          ) : (
            <div className="space-y-2">
              {failCases.slice(0, 6).map((item, index) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + index * 0.04 }}
                  className="p-3 rounded-lg border border-glow-error/20 bg-glow-error/5"
                >
                  <div className="flex items-center justify-between mb-1 gap-3">
                    <span className="text-xs font-medium text-foreground">{item.task}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle.FAIL}`}>FAIL</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground">{item.errorDetail || 'Failure details were not persisted for this case.'}</p>
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
            <h3 className="text-sm font-medium text-foreground">Provider Breakdown</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {providerBreakdown.length === 0 ? (
            <p className="text-xs text-muted-foreground">Provider slices appear once eval runs are persisted.</p>
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
            <h3 className="text-sm font-medium text-foreground">Task Breakdown</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {taskBreakdown.length === 0 ? (
            <p className="text-xs text-muted-foreground">Task slices appear when phase8 history contains repeated task types.</p>
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
            <h3 className="text-sm font-medium text-foreground">Watchlist</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {watchlist.length === 0 ? (
            <p className="text-xs text-muted-foreground">No escalated watchlist items are present in the current eval history.</p>
          ) : (
            <div className="space-y-2">
              {watchlist.slice(0, 6).map((item) => (
                <div key={item.id} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-foreground truncate">{item.task}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle[item.verdict]}`}>{item.verdict}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground">{item.reason}</p>
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
            <h3 className="text-sm font-medium text-foreground">Adaptation Candidates</h3>
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

      {warnCases.length > 0 ? (
        <GlassCard className="mb-6" delay={0.22}>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Warnings to Watch</h3>
          </div>
          <div className="space-y-2">
            {warnCases.slice(0, 8).map((item) => (
              <div key={item.id} className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle.WARN}`}>WARN</span>
                  <span className="text-xs text-foreground truncate">{item.task}</span>
                  <span className="text-[10px] text-muted-foreground">{item.suite}</span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground shrink-0">
                  <span>Score: {Math.round(item.score * 100)}%</span>
                  <span>{item.latency}s</span>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      ) : null}

      <GlassCard delay={0.25}>
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Recent Eval Cases</h3>
          {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50">
                {['Task', 'Suite', 'Verdict', 'Score', 'Model', 'Latency', 'Review'].map((heading) => (
                  <th key={heading} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{heading}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
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
              {isLoading && !cases.length ? (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-xs text-muted-foreground">Loading eval cases…</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </motion.div>
  );
}
