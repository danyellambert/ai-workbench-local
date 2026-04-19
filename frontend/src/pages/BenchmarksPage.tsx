import { motion } from 'framer-motion';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BarChart3, Trophy, Timer, Target, CheckCircle2, ArrowUpDown } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabBenchmarksPage } from '@/lib/ai-lab-data';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Cell, BarChart, Bar, Legend } from 'recharts';
import { useAppStore } from '@/lib/store';

const profileColors: Record<string, string> = {
  'Recommended production': 'hsl(142, 71%, 45%)',
  'External reference': 'hsl(217, 91%, 60%)',
  'Fastest observed': 'hsl(38, 92%, 50%)',
  'Hosted candidate': 'hsl(280, 67%, 55%)',
  'Benchmark candidate': 'hsl(199, 89%, 48%)',
};

const scatterChartConfig = {
  fit: { label: 'Use-Case Fit %' },
  latency: { label: 'Latency (s)' },
};

const retrievalChartConfig = {
  OutputDiscipline: { label: 'Output discipline', color: 'hsl(217, 91%, 60%)' },
  ContextRetention: { label: 'Context retention', color: 'hsl(142, 71%, 45%)' },
  Composite: { label: 'Composite', color: 'hsl(280, 67%, 55%)' },
};

export default function BenchmarksPage() {
  const benchmarkBaselineLabel = useAppStore((state) => state.benchmarkBaselineLabel);
  const { data, isLoading, isError } = useQuery({
    queryKey: aiLabQueryKeys.benchmarks,
    queryFn: getLabBenchmarksPage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const models = data?.models ?? [];
  const retrievalObservations = data?.retrievalObservations ?? [];
  const presets = data?.presets ?? [];
  const providerSummary = data?.providerSummary ?? [];
  const leaderboardHighlights = data?.leaderboardHighlights ?? [];
  const recommended = models[0];
  const statusLabel = data?.status === 'empty' ? 'Waiting for runs' : data?.status === 'derived' ? 'Derived live' : 'Live';

  const sorted = useMemo(() => [...models].sort((a, b) => b.useCaseFit - a.useCaseFit), [models]);
  const scatterData = useMemo(
    () => models.map((model) => ({
      name: model.family,
      latency: model.latency,
      fit: Math.round(model.useCaseFit * 100),
      groundedness: Math.round(model.groundedness * 100),
      profile: model.profileTag || 'Benchmark candidate',
      model: model.model,
      runs: model.runs,
    })),
    [models],
  );

  const retrievalChartData = useMemo(
    () => retrievalObservations.map((item) => ({
      name: item.strategy.replace(/_/g, ' '),
      OutputDiscipline: Math.round(item.outputDiscipline * 100),
      ContextRetention: Math.round(item.contextRetention * 100),
      Composite: Math.round(item.composite * 100),
    })),
    [retrievalObservations],
  );

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Benchmarks"
        description="Model and strategy comparison hub — latency, quality, groundedness and adherence across configurations."
        operatorQuestion="Which model/provider setup is strongest for which use case?"
        badges={[
          { label: `${data?.summary.modelCount ?? 0} models`, variant: 'default' },
          { label: `${retrievalObservations.length} retrieval observations`, variant: 'default' },
          { label: recommended ? `Production: ${recommended.family}` : 'Waiting for phase7 logs', variant: recommended ? 'success' : 'default' },
          ...(benchmarkBaselineLabel ? [{ label: `Baseline: ${benchmarkBaselineLabel}`, variant: 'default' as const }] : []),
        ]}
        dataSource={data?.meta.source}
      />

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            Benchmarks now read recorded phase7 comparison logs only. The Product API is unavailable, so no synthetic leaderboard is shown.
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={4}
        metrics={[
          { label: 'Production Fit', value: recommended ? `${Math.round(recommended.useCaseFit * 100)}%` : '—', icon: Trophy, status: recommended ? 'healthy' : 'neutral' },
          { label: 'Best Groundedness', value: data ? `${Math.round(data.summary.bestGroundedness * 100)}%` : '—', icon: Target, status: data ? 'healthy' : 'neutral' },
          { label: 'Fastest Latency', value: data ? `${data.summary.fastestLatency}s` : '—', icon: Timer, status: data ? 'healthy' : 'neutral' },
          { label: 'Models Tested', value: data?.summary.modelCount ?? '—', icon: BarChart3, status: 'neutral' },
        ]}
      />

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Provider coverage</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{providerSummary.length || '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Active providers with recorded model comparisons.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Top provider</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{providerSummary[0]?.provider ?? 'No provider yet'}</p>
          <p className="mt-1 text-xs text-muted-foreground">{providerSummary[0]?.bestModel ? `${providerSummary[0].bestModel} · ${providerSummary[0].bestFit}% best fit` : 'Benchmark registry is still empty.'}</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Leaderboard posture</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{statusLabel}</p>
          <p className="mt-1 text-xs text-muted-foreground">{data?.degraded_reason ?? `${leaderboardHighlights.length} highlight(s) derived from recorded runs.`}</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Preset coverage</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{presets.length || '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Reusable benchmark presets aggregated from the comparison log.</p>
        </GlassCard>
      </div>

      {leaderboardHighlights.length ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
          {leaderboardHighlights.map((highlight, index) => (
            <GlassCard key={`${highlight.label}-${index}`} className="p-4" delay={0.05 + index * 0.03}>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{highlight.label}</p>
              <p className="mt-2 text-sm font-semibold text-foreground">{highlight.model ?? '—'}</p>
              <p className="mt-1 text-xs text-muted-foreground">{highlight.detail ?? 'Recorded from the persisted benchmark leaderboard.'}</p>
            </GlassCard>
          ))}
        </div>
      ) : null}

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
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            {isLoading && !sorted.length ? (
              <p className="text-xs text-muted-foreground">Loading recorded benchmark runs…</p>
            ) : sorted.length === 0 ? (
              <p className="text-xs text-muted-foreground">No phase7 benchmark comparison log has been recorded in this workspace yet.</p>
            ) : (
              <div className="space-y-2">
                {sorted.map((model, index) => {
                  const profile = model.profileTag || 'Benchmark candidate';
                  const isRecommended = profile === 'Recommended production';
                  const isExternal = profile === 'External reference';
                  return (
                    <motion.div
                      key={model.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 + index * 0.04 }}
                      className={`flex items-center gap-4 py-3 px-4 rounded-lg transition-colors ${
                        isRecommended ? 'bg-glow-success/5 border border-glow-success/20' : index === 0 ? 'bg-secondary/20' : 'hover:bg-secondary/20'
                      }`}
                    >
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                        isRecommended ? 'bg-glow-success/20 text-glow-success' : 'bg-secondary text-muted-foreground'
                      }`}>{index + 1}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-xs font-medium text-foreground">{model.model}</p>
                          {isRecommended ? (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-glow-success/10 text-glow-success border border-glow-success/20 font-medium">Production</span>
                          ) : null}
                          {isExternal ? (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border/50 font-medium">External ref.</span>
                          ) : null}
                        </div>
                        <p className="text-[10px] text-muted-foreground">{model.provider} · {model.family} · {model.quantization}</p>
                      </div>
                      <div className="flex items-center gap-6 text-[10px] text-muted-foreground shrink-0">
                        <div className="text-center"><p className="text-foreground font-medium">{model.latency}s</p><p>Latency</p></div>
                        <div className="text-center"><p className="text-foreground font-medium">{Math.round(model.adherence * 100)}%</p><p>Adherence</p></div>
                        <div className="text-center"><p className="text-foreground font-medium">{Math.round(model.groundedness * 100)}%</p><p>Ground.</p></div>
                        <div className="text-center"><p className="text-primary font-semibold text-xs">{Math.round(model.useCaseFit * 100)}%</p><p>Fit</p></div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </GlassCard>
        </TabsContent>

        <TabsContent value="tradeoffs" className="mt-0">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Latency vs Use-Case Fit</h3>
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            {scatterData.length === 0 ? (
              <p className="text-xs text-muted-foreground">A tradeoff map appears once model comparison runs are recorded.</p>
            ) : (
              <>
                <div className="h-[340px]">
                  <ChartContainer config={scatterChartConfig} className="w-full h-full">
                    <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                      <XAxis type="number" dataKey="latency" name="Latency" unit="s" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} label={{ value: 'Latency (seconds)', position: 'bottom', fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                      <YAxis type="number" dataKey="fit" name="Fit" unit="%" domain={[60, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} label={{ value: 'Use-Case Fit %', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                      <ChartTooltip
                        content={({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; profile: string; latency: number; fit: number; groundedness: number; runs: number } }> }) => {
                          if (!active || !payload?.length) return null;
                          const entry = payload[0].payload;
                          return (
                            <div className="glass rounded-lg p-3 border border-border/50 text-xs">
                              <p className="font-medium text-foreground mb-1">{entry.name}</p>
                              <p className="text-muted-foreground text-[10px] mb-2">{entry.profile}</p>
                              <div className="space-y-0.5 text-[10px]">
                                <p>Latency: <span className="text-foreground">{entry.latency}s</span></p>
                                <p>Fit: <span className="text-foreground">{entry.fit}%</span></p>
                                <p>Groundedness: <span className="text-foreground">{entry.groundedness}%</span></p>
                                <p>Recorded runs: <span className="text-foreground">{entry.runs}</span></p>
                              </div>
                            </div>
                          );
                        }}
                      />
                      <Scatter data={scatterData} fill="hsl(var(--primary))">
                        {scatterData.map((entry, index) => (
                          <Cell key={index} fill={profileColors[entry.profile] || 'hsl(var(--primary))'} r={8} />
                        ))}
                      </Scatter>
                    </ScatterChart>
                  </ChartContainer>
                </div>
                <div className="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-border/30">
                  {Object.entries(profileColors).map(([label, color]) => (
                    <div key={label} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                      {label}
                    </div>
                  ))}
                </div>
              </>
            )}
          </GlassCard>
        </TabsContent>

        <TabsContent value="cards" className="mt-0">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {models.map((model, index) => {
              const profile = model.profileTag || 'Benchmark candidate';
              const isRecommended = profile === 'Recommended production';
              const isExternal = profile === 'External reference';
              return (
                <motion.div
                  key={model.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + index * 0.05 }}
                  className={`glass rounded-xl p-5 ${isRecommended ? 'border-glow-success/30' : ''}`}
                >
                  <div className="flex items-start justify-between mb-3 gap-3">
                    <div>
                      <h4 className="text-sm font-medium text-foreground">{model.family}</h4>
                      <p className="text-[10px] text-muted-foreground font-mono break-all">{model.model}</p>
                    </div>
                    {isRecommended ? (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-success/10 text-glow-success border border-glow-success/20 font-medium">Production</span>
                    ) : null}
                    {isExternal ? (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border/50 font-medium">External ref.</span>
                    ) : null}
                  </div>
                  <p className="text-[10px] text-muted-foreground mb-3">{profile}</p>
                  <div className="space-y-3 mt-2">
                    {[
                      { label: 'Use Case Fit', value: model.useCaseFit },
                      { label: 'Groundedness', value: model.groundedness },
                      { label: 'Adherence', value: model.adherence },
                    ].map((metric) => (
                      <div key={metric.label}>
                        <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
                          <span>{metric.label}</span>
                          <span className="text-foreground font-medium">{Math.round(metric.value * 100)}%</span>
                        </div>
                        <Progress value={metric.value * 100} className="h-1.5 bg-secondary" />
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 pt-3 border-t border-border/30 grid grid-cols-2 gap-2 text-[10px] text-muted-foreground">
                    <div><span className="block text-muted-foreground/60">Latency</span>{model.latency}s</div>
                    <div><span className="block text-muted-foreground/60">Output</span>{model.outputChars} chars</div>
                    <div><span className="block text-muted-foreground/60">Runtime</span>{model.runtimeBucket.replace(/_/g, ' ')}</div>
                    <div><span className="block text-muted-foreground/60">Runs</span>{model.runs}</div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="presets" className="mt-0 space-y-3">
          {presets.length === 0 ? (
            <GlassCard>
              <p className="text-xs text-muted-foreground">No observed benchmark presets were found in the phase7 comparison log.</p>
            </GlassCard>
          ) : (
            presets.map((preset, index) => (
              <GlassCard key={preset.id} delay={0.1 + index * 0.05}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-medium text-foreground">{preset.name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">{preset.description}</p>
                  </div>
                  {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
                </div>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {preset.metrics.map((metric) => (
                    <span key={metric} className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">{metric}</span>
                  ))}
                </div>
                <p className="text-[10px] text-muted-foreground mt-2">Models: {preset.models.join(', ')}</p>
              </GlassCard>
            ))
          )}
          {providerSummary.length ? (
            <GlassCard delay={0.2}>
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-medium text-foreground">Provider Summary</h3>
              </div>
              <div className="space-y-2">
                {providerSummary.map((provider) => (
                  <div key={provider.provider} className="flex items-center justify-between gap-4 rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                    <div>
                      <p className="text-xs font-medium text-foreground">{provider.provider}</p>
                      <p className="text-[10px] text-muted-foreground">{provider.models} model(s) · best {provider.bestFit}% fit</p>
                    </div>
                    <div className="text-right text-[10px] text-muted-foreground">
                      <p className="text-foreground font-medium">{provider.avgLatency}s</p>
                      <p>{provider.bestModel ?? 'No leader yet'}</p>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
          ) : null}
        </TabsContent>

        <TabsContent value="retrieval" className="mt-0 space-y-4">
          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Retrieval Quality Comparison</h3>
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            {retrievalChartData.length === 0 ? (
              <p className="text-xs text-muted-foreground">Retrieval observations will populate when benchmark comparison runs include recorded retrieval context.</p>
            ) : (
              <div className="h-[260px]">
                <ChartContainer config={retrievalChartConfig} className="w-full h-full">
                  <BarChart data={retrievalChartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                    <YAxis domain={[60, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Legend wrapperStyle={{ fontSize: '10px' }} />
                    <Bar dataKey="OutputDiscipline" fill="hsl(217, 91%, 60%)" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="ContextRetention" fill="hsl(142, 71%, 45%)" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="Composite" fill="hsl(280, 67%, 55%)" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ChartContainer>
              </div>
            )}
          </GlassCard>

          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <ArrowUpDown className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Retrieval Observation Detail</h3>
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border/50">
                    {['Strategy', 'Output', 'Retention', 'Composite', 'Latency', 'Coverage', 'Description'].map((heading) => (
                      <th key={heading} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {retrievalObservations.map((item) => (
                    <tr key={item.strategy} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                      <td className="px-3 py-2.5 text-xs text-foreground font-mono">{item.strategy}</td>
                      <td className="px-3 py-2.5 text-xs text-foreground">{Math.round(item.outputDiscipline * 100)}%</td>
                      <td className="px-3 py-2.5 text-xs text-foreground">{Math.round(item.contextRetention * 100)}%</td>
                      <td className="px-3 py-2.5 text-xs text-primary font-medium">{Math.round(item.composite * 100)}%</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{item.latency}s</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{item.coverage}</td>
                      <td className="px-3 py-2.5 text-[10px] text-muted-foreground">{item.description}</td>
                    </tr>
                  ))}
                  {isLoading && !retrievalObservations.length ? (
                    <tr>
                      <td colSpan={7} className="px-3 py-6 text-xs text-muted-foreground">Loading retrieval observations…</td>
                    </tr>
                  ) : null}
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
              {retrievalObservations[0]
                ? (
                  <>
                    <span className="text-foreground font-medium">{retrievalObservations[0].strategy}</span> is the best observed retrieval posture in recorded benchmark runs, with{' '}
                    <span className="text-foreground font-medium">{Math.round(retrievalObservations[0].composite * 100)}%</span> composite quality across{' '}
                    <span className="text-foreground font-medium">{retrievalObservations[0].coverage}</span> captured candidate result(s).
                  </>
                )
                : 'No retrieval summary is available until the benchmark log captures retrieval-aware comparison runs.'}
            </p>
          </GlassCard>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
