import { motion } from 'framer-motion';
import { ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Eye, Clock, TrendingDown, BarChart3 } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard } from '@/components/shared/ui-components';
import { getEvalSuites, getEvalCases } from '@/lib/ai-lab-data';
import type { EvalVerdict } from '@/types/ai-lab';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';

const suites = getEvalSuites();
const cases = getEvalCases();

const totals = suites.data.reduce((acc, s) => ({ pass: acc.pass + s.pass, warn: acc.warn + s.warn, fail: acc.fail + s.fail, review: acc.review + s.needsReview, total: acc.total + s.total }), { pass: 0, warn: 0, fail: 0, review: 0, total: 0 });
const passRate = Math.round((totals.pass / totals.total) * 100);

const verdictStyle: Record<EvalVerdict, string> = {
  PASS: 'bg-glow-success/10 text-glow-success border-glow-success/20',
  WARN: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
  FAIL: 'bg-glow-error/10 text-glow-error border-glow-error/20',
};

const failCases = cases.data.filter(c => c.verdict === 'FAIL');
const warnCases = cases.data.filter(c => c.verdict === 'WARN');

// Stacked bar chart data
const suiteChartData = suites.data.map(s => ({
  name: s.name,
  Pass: s.pass,
  Warn: s.warn,
  Fail: s.fail,
}));

const suiteChartConfig = {
  Pass: { label: 'Pass', color: 'hsl(142, 71%, 45%)' },
  Warn: { label: 'Warn', color: 'hsl(38, 92%, 50%)' },
  Fail: { label: 'Fail', color: 'hsl(0, 84%, 60%)' },
};

export default function EvalsDiagnosisPage() {
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
        dataSource={suites.meta.source}
      />

      <AiLabMetricGrid columns={5} metrics={[
        { label: 'Pass Rate', value: `${passRate}%`, icon: ShieldCheck, status: passRate >= 85 ? 'healthy' : 'warning' },
        { label: 'Total Cases', value: totals.total, icon: CheckCircle2, status: 'neutral' },
        { label: 'Failures', value: totals.fail, icon: XCircle, status: totals.fail > 0 ? 'error' : 'healthy' },
        { label: 'Warnings', value: totals.warn, icon: AlertTriangle, status: totals.warn > 0 ? 'warning' : 'healthy' },
        { label: 'Needs Review', value: totals.review, icon: Eye, status: totals.review > 0 ? 'warning' : 'healthy' },
      ]} />

      {/* Suite Quality Chart */}
      <GlassCard className="mb-6" delay={0.08}>
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Suite Pass/Warn/Fail Distribution</h3>
          <DataSourceBadge source="mock" />
        </div>
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
      </GlassCard>

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        {/* Suite Leaderboard */}
        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2 mb-4">
            <ShieldCheck className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Suite Leaderboard</h3>
            <DataSourceBadge source="mock" />
          </div>
          <div className="space-y-2">
            {[...suites.data].sort((a, b) => (b.pass / b.total) - (a.pass / a.total)).map((s, i) => {
              const rate = Math.round((s.pass / s.total) * 100);
              return (
                <motion.div key={s.name} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 + i * 0.04 }}
                  className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-medium text-foreground font-mono">{s.name}</span>
                    {s.needsReview > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded bg-glow-warning/10 text-glow-warning">{s.needsReview} review</span>}
                  </div>
                  <div className="flex items-center gap-3 text-[10px]">
                    <span className="text-glow-success">{s.pass}P</span>
                    <span className="text-glow-warning">{s.warn}W</span>
                    <span className="text-glow-error">{s.fail}F</span>
                    <span className={`font-medium ${rate >= 85 ? 'text-glow-success' : 'text-glow-warning'}`}>{rate}%</span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </GlassCard>

        {/* Investigate First */}
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
              {failCases.map((c, i) => (
                <motion.div key={c.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.04 }}
                  className="p-3 rounded-lg border border-glow-error/20 bg-glow-error/5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-foreground">{c.task}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle.FAIL}`}>FAIL</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground">{c.errorDetail}</p>
                  <div className="flex items-center gap-3 mt-1.5 text-[9px] text-muted-foreground/60">
                    <span>{c.suite}</span><span>{c.model}</span><span>{c.latency}s</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      {/* Warnings */}
      {warnCases.length > 0 && (
        <GlassCard className="mb-6" delay={0.2}>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-glow-warning" />
            <h3 className="text-sm font-medium text-foreground">Adaptation Candidates</h3>
            <span className="text-[10px] text-muted-foreground">Tasks with warnings that may benefit from prompt or strategy adjustments</span>
          </div>
          <div className="space-y-2">
            {warnCases.map(c => (
              <div key={c.id} className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors">
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle.WARN}`}>WARN</span>
                  <span className="text-xs text-foreground">{c.task}</span>
                  <span className="text-[10px] text-muted-foreground">{c.suite}</span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span>Score: {(c.score * 100).toFixed(0)}%</span>
                  <span>{c.latency}s</span>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* All Cases */}
      <GlassCard delay={0.25}>
        <div className="flex items-center gap-2 mb-4">
          <Clock className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Recent Eval Cases</h3>
          <DataSourceBadge source="mock" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50">
                {['Task', 'Suite', 'Verdict', 'Score', 'Model', 'Latency', 'Review'].map(h => (
                  <th key={h} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cases.data.map(c => (
                <tr key={c.id} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                  <td className="px-3 py-2.5 text-xs text-foreground">{c.task}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{c.suite}</td>
                  <td className="px-3 py-2.5"><span className={`text-[10px] px-2 py-0.5 rounded border font-medium ${verdictStyle[c.verdict]}`}>{c.verdict}</span></td>
                  <td className="px-3 py-2.5 text-xs text-foreground">{(c.score * 100).toFixed(0)}%</td>
                  <td className="px-3 py-2.5 text-[10px] text-muted-foreground font-mono">{c.model}</td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">{c.latency}s</td>
                  <td className="px-3 py-2.5">{c.needsReview && <span className="text-[10px] px-2 py-0.5 rounded bg-glow-warning/10 text-glow-warning border border-glow-warning/20">Yes</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </motion.div>
  );
}
