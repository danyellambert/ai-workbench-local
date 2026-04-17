import { motion } from 'framer-motion';
import { BarChart3, Trophy, Timer, Target, Zap, CheckCircle2, ArrowUpDown } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard } from '@/components/shared/ui-components';
import { models } from '@/lib/mock-data';
import { getBenchmarkPresets, getStrategyBenchmarks } from '@/lib/ai-lab-data';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell, BarChart, Bar, Legend } from 'recharts';
import { useAppStore } from '@/lib/store';

const presets = getBenchmarkPresets();
const strategies = getStrategyBenchmarks();
const recommended = models.find(m => m.profileTag === 'Recommended production')!;
const sorted = [...models].sort((a, b) => b.useCaseFit - a.useCaseFit);

// Scatter chart data
const scatterData = models.map(m => ({
  name: m.family,
  latency: m.latency,
  fit: Math.round(m.useCaseFit * 100),
  groundedness: Math.round(m.groundedness * 100),
  profile: m.profileTag || '',
  model: m.model,
}));

const profileColors: Record<string, string> = {
  'Recommended production': 'hsl(142, 71%, 45%)',
  'External reference': 'hsl(217, 91%, 60%)',
  'Fast triage (local)': 'hsl(38, 92%, 50%)',
  'Deep analysis (local)': 'hsl(280, 67%, 55%)',
  'Long-context local': 'hsl(199, 89%, 48%)',
};

const scatterChartConfig = {
  fit: { label: 'Use-Case Fit %' },
  latency: { label: 'Latency (s)' },
};

// Retrieval strategy chart data
const strategyChartData = strategies.data.map(s => ({
  name: s.strategy.replace('_', ' '),
  Precision: Math.round(s.precision * 100),
  Recall: Math.round(s.recall * 100),
  F1: Math.round(s.f1 * 100),
}));

const strategyChartConfig = {
  Precision: { label: 'Precision', color: 'hsl(217, 91%, 60%)' },
  Recall: { label: 'Recall', color: 'hsl(142, 71%, 45%)' },
  F1: { label: 'F1 Score', color: 'hsl(280, 67%, 55%)' },
};

export default function BenchmarksPage() {
  const benchmarkBaselineLabel = useAppStore((state) => state.benchmarkBaselineLabel);
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Benchmarks"
        description="Model and strategy comparison hub — latency, quality, groundedness and adherence across configurations."
        operatorQuestion="Which model/provider setup is strongest for which use case?"
        badges={[
          { label: `${models.length} models`, variant: 'default' },
          { label: `${strategies.data.length} retrieval strategies`, variant: 'default' },
          { label: `Production: ${recommended.family}`, variant: 'success' },
          ...(benchmarkBaselineLabel ? [{ label: `Baseline: ${benchmarkBaselineLabel}`, variant: 'default' as const }] : []),
        ]}
        dataSource="mock"
      />

      <AiLabMetricGrid columns={4} metrics={[
        { label: 'Production Fit', value: `${(recommended.useCaseFit * 100).toFixed(0)}%`, icon: Trophy, status: 'healthy' },
        { label: 'Best Groundedness', value: `${(Math.max(...models.map(m => m.groundedness)) * 100).toFixed(0)}%`, icon: Target, status: 'healthy' },
        { label: 'Fastest Latency', value: `${Math.min(...models.map(m => m.latency))}s`, icon: Timer, status: 'healthy' },
        { label: 'Models Tested', value: models.length, icon: BarChart3, status: 'neutral' },
      ]} />

      <Tabs defaultValue="leaderboard">
        <TabsList className="bg-secondary/30 border border-border/50 mb-4">
          <TabsTrigger value="leaderboard" className="text-xs data-[state=active]:bg-secondary">Leaderboard</TabsTrigger>
          <TabsTrigger value="tradeoffs" className="text-xs data-[state=active]:bg-secondary">Tradeoff Map</TabsTrigger>
          <TabsTrigger value="cards" className="text-xs data-[state=active]:bg-secondary">Model Cards</TabsTrigger>
          <TabsTrigger value="presets" className="text-xs data-[state=active]:bg-secondary">Presets</TabsTrigger>
          <TabsTrigger value="retrieval" className="text-xs data-[state=active]:bg-secondary">Retrieval Strategies</TabsTrigger>
        </TabsList>

        <TabsContent value="leaderboard" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Trophy className="w-4 h-4 text-glow-warning" />
              <h3 className="text-sm font-medium text-foreground">Model Leaderboard</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="space-y-2">
              {sorted.map((model, i) => {
                const isRecommended = model.profileTag === 'Recommended production';
                const isExternal = model.runtimeBucket === 'cloud_api';
                return (
                  <motion.div key={model.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 + i * 0.04 }}
                    className={`flex items-center gap-4 py-3 px-4 rounded-lg transition-colors ${
                      isRecommended ? 'bg-glow-success/5 border border-glow-success/20' : i === 0 && !isRecommended ? 'bg-secondary/20' : 'hover:bg-secondary/20'
                    }`}>
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      isRecommended ? 'bg-glow-success/20 text-glow-success' : 'bg-secondary text-muted-foreground'
                    }`}>{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-medium text-foreground">{model.model}</p>
                        {isRecommended && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-glow-success/10 text-glow-success border border-glow-success/20 font-medium">Production</span>}
                        {isExternal && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border/50 font-medium">External ref.</span>}
                      </div>
                      <p className="text-[10px] text-muted-foreground">{model.provider} · {model.family} · {model.quantization}</p>
                    </div>
                    <div className="flex items-center gap-6 text-[10px] text-muted-foreground shrink-0">
                      <div className="text-center"><p className="text-foreground font-medium">{model.latency}s</p><p>Latency</p></div>
                      <div className="text-center"><p className="text-foreground font-medium">{(model.adherence * 100).toFixed(0)}%</p><p>Adherence</p></div>
                      <div className="text-center"><p className="text-foreground font-medium">{(model.groundedness * 100).toFixed(0)}%</p><p>Ground.</p></div>
                      <div className="text-center"><p className="text-primary font-semibold text-xs">{(model.useCaseFit * 100).toFixed(0)}%</p><p>Fit</p></div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </GlassCard>
        </TabsContent>

        {/* Tradeoff Scatter Plot */}
        <TabsContent value="tradeoffs" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Latency vs Use-Case Fit</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="h-[340px]">
              <ChartContainer config={scatterChartConfig} className="w-full h-full">
                <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                  <XAxis type="number" dataKey="latency" name="Latency" unit="s" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} label={{ value: 'Latency (seconds)', position: 'bottom', fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis type="number" dataKey="fit" name="Fit" unit="%" domain={[60, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} label={{ value: 'Use-Case Fit %', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <ChartTooltip content={({ active, payload }: any) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    return (
                      <div className="glass rounded-lg p-3 border border-border/50 text-xs">
                        <p className="font-medium text-foreground mb-1">{d.name}</p>
                        <p className="text-muted-foreground text-[10px] mb-2">{d.profile}</p>
                        <div className="space-y-0.5 text-[10px]">
                          <p>Latency: <span className="text-foreground">{d.latency}s</span></p>
                          <p>Fit: <span className="text-foreground">{d.fit}%</span></p>
                          <p>Groundedness: <span className="text-foreground">{d.groundedness}%</span></p>
                        </div>
                      </div>
                    );
                  }} />
                  <Scatter data={scatterData} fill="hsl(var(--primary))">
                    {scatterData.map((entry, idx) => (
                      <Cell key={idx} fill={profileColors[entry.profile] || 'hsl(var(--primary))'} r={8} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ChartContainer>
            </div>
            {/* Legend */}
            <div className="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-border/30">
              {Object.entries(profileColors).map(([label, color]) => (
                <div key={label} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                  {label}
                </div>
              ))}
            </div>
          </GlassCard>
        </TabsContent>

        <TabsContent value="cards" className="mt-0">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {models.map((model, i) => {
              const isRecommended = model.profileTag === 'Recommended production';
              const isExternal = model.runtimeBucket === 'cloud_api';
              return (
                <motion.div key={model.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                  className={`glass rounded-xl p-5 ${isRecommended ? 'border-glow-success/30' : ''}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className="text-sm font-medium text-foreground">{model.family}</h4>
                      <p className="text-[10px] text-muted-foreground font-mono">{model.model}</p>
                    </div>
                    {isRecommended && <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-success/10 text-glow-success border border-glow-success/20 font-medium">Production</span>}
                    {isExternal && <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border/50 font-medium">External ref.</span>}
                  </div>
                  {model.profileTag && <p className="text-[10px] text-muted-foreground mb-3">{model.profileTag}</p>}
                  <div className="space-y-3 mt-2">
                    {[{ label: 'Use Case Fit', value: model.useCaseFit }, { label: 'Groundedness', value: model.groundedness }, { label: 'Adherence', value: model.adherence }].map(metric => (
                      <div key={metric.label}>
                        <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
                          <span>{metric.label}</span>
                          <span className="text-foreground font-medium">{(metric.value * 100).toFixed(0)}%</span>
                        </div>
                        <Progress value={metric.value * 100} className="h-1.5 bg-secondary" />
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 pt-3 border-t border-border/30 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
                    <div><span className="block text-muted-foreground/60">Latency</span>{model.latency}s</div>
                    <div><span className="block text-muted-foreground/60">Output</span>{model.outputChars} chars</div>
                    <div><span className="block text-muted-foreground/60">Runtime</span>{model.runtimeBucket.replace('_', ' ')}</div>
                    <div><span className="block text-muted-foreground/60">Quantization</span>{model.quantization}</div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="presets" className="mt-0 space-y-3">
          {presets.data.map((p, i) => (
            <GlassCard key={p.id} delay={0.1 + i * 0.05}>
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-medium text-foreground">{p.name}</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">{p.description}</p>
                </div>
                <DataSourceBadge source="mock" />
              </div>
              <div className="flex items-center gap-2 mt-3 flex-wrap">
                {p.metrics.map(m => (
                  <span key={m} className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">{m}</span>
                ))}
              </div>
              <p className="text-[10px] text-muted-foreground mt-2">
                Models: {p.models.map(mid => models.find(m => m.id === mid)?.family || mid).join(', ')}
              </p>
            </GlassCard>
          ))}
        </TabsContent>

        <TabsContent value="retrieval" className="mt-0 space-y-4">
          {/* Retrieval Strategy Chart */}
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Retrieval Quality Comparison</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="h-[260px]">
              <ChartContainer config={strategyChartConfig} className="w-full h-full">
                <BarChart data={strategyChartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis domain={[60, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Legend wrapperStyle={{ fontSize: '10px' }} />
                  <Bar dataKey="Precision" fill="hsl(217, 91%, 60%)" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Recall" fill="hsl(142, 71%, 45%)" radius={[2, 2, 0, 0]} />
                  <Bar dataKey="F1" fill="hsl(280, 67%, 55%)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ChartContainer>
            </div>
          </GlassCard>

          {/* Retrieval Table */}
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <ArrowUpDown className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Retrieval Strategy Detail</h3>
              <DataSourceBadge source="mock" />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border/50">
                    {['Strategy', 'Precision', 'Recall', 'F1', 'Latency', 'Description'].map(h => (
                      <th key={h} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {strategies.data.map(s => (
                    <tr key={s.strategy} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                      <td className="px-3 py-2.5 text-xs text-foreground font-mono">{s.strategy}</td>
                      <td className="px-3 py-2.5 text-xs text-foreground">{(s.precision * 100).toFixed(0)}%</td>
                      <td className="px-3 py-2.5 text-xs text-foreground">{(s.recall * 100).toFixed(0)}%</td>
                      <td className="px-3 py-2.5 text-xs text-primary font-medium">{(s.f1 * 100).toFixed(0)}%</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{s.latency}s</td>
                      <td className="px-3 py-2.5 text-[10px] text-muted-foreground">{s.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>

          <GlassCard delay={0.15}>
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Strategy Summary</h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              <span className="text-foreground font-medium">hybrid_rerank</span> is the recommended production strategy (90% F1, 1.8s). <span className="text-foreground font-medium">ensemble_weighted</span> matches F1 at 90% but adds 33% latency.
              For latency-critical triage, <span className="text-foreground font-medium">bm25_only</span> at 0.3s provides acceptable precision (78%) with minimal compute cost.
            </p>
          </GlassCard>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
