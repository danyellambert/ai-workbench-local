import { motion } from 'framer-motion';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BarChart3, CalendarClock, CheckCircle2, Gauge, Target, Timer, Trophy } from 'lucide-react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Cell, BarChart, Bar, Legend } from 'recharts';

import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { GlassCard } from '@/components/shared/ui-components';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { aiLabQueryKeys, getLabBenchmarksPage } from '@/lib/ai-lab-data';
import { useAppStore } from '@/lib/store';

import { formatUserDateTime } from '@/lib/user-time';
const profileColors: Record<string, string> = {
  'Recommended production': 'hsl(142, 71%, 45%)',
  'External reference': 'hsl(217, 91%, 60%)',
  'Fastest observed': 'hsl(38, 92%, 50%)',
  'Benchmark candidate': 'hsl(199, 89%, 48%)',
  'Phase 8.5 winner': 'hsl(280, 67%, 55%)',
};

const scatterChartConfig = {
  fit: { label: 'Use-case fit %' },
  latency: { label: 'Latency (s)' },
};

const retrievalChartConfig = {
  OutputDiscipline: { label: 'Output discipline', color: 'hsl(217, 91%, 60%)' },
  ContextRetention: { label: 'Context retention', color: 'hsl(142, 71%, 45%)' },
  Composite: { label: 'Composite', color: 'hsl(280, 67%, 55%)' },
};

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function formatPercent(value?: number | null) {
  return isNumber(value) ? `${Math.round(value * 100)}%` : '—';
}

function formatPercentWithLabel(value?: number | null, fallback = 'Not scored') {
  return isNumber(value) ? `${Math.round(value * 100)}%` : fallback;
}

function formatSeconds(value?: number | null) {
  if (!isNumber(value)) {
    return '—';
  }
  if (value >= 10) {
    return `${value.toFixed(3)}s`;
  }
  return `${value.toFixed(3)}s`;
}

function formatCount(value?: number | null) {
  return isNumber(value) ? `${Math.round(value)}` : '—';
}

function formatBenchmarkTimestamp(value?: string | number | null): string {
  return formatUserDateTime(value);
}

function MetricRow({
  label,
  value,
  coverage,
}: {
  label: string;
  value?: number | null;
  coverage?: number;
}) {
  return (
    <div>
      <div className="flex justify-between text-[10px] text-muted-foreground mb-1 gap-3">
        <span>{label}</span>
        <span className="text-right text-foreground font-medium">
          {isNumber(value) ? `${Math.round(value * 100)}%` : 'Not scored'}
          {coverage ? <span className="ml-1 text-muted-foreground font-normal">· {coverage} run(s)</span> : null}
        </span>
      </div>
      {isNumber(value) ? (
        <Progress value={value * 100} className="h-1.5 bg-secondary" />
      ) : (
        <div className="h-1.5 rounded bg-secondary/60" />
      )}
    </div>
  );
}

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
  const promptProfiles = data?.presets ?? [];
  const providerSummary = data?.providerSummary ?? [];
  const leaderboardHighlights = data?.leaderboardHighlights ?? [];
  const recommended = models.find((model) => model.profileTag === 'Recommended production') ?? models.find((model) => isNumber(model.useCaseFit));
  const benchmarkStatus = data?.status === 'historical' ? 'Historical' : data?.status === 'derived-live' ? 'Derived live' : data?.status === 'empty' ? 'Waiting for runs' : 'Derived';
  const partialModelCount = data?.summary.partialModelCount ?? 0;

  const orderedModels = useMemo(() => models, [models]);

  const scatterData = useMemo(
    () => models
      .filter((model) => isNumber(model.useCaseFit) && isNumber(model.latency))
      .map((model) => ({
        name: model.family,
        latency: model.latency as number,
        fit: Math.round((model.useCaseFit as number) * 100),
        groundedness: isNumber(model.groundedness) ? Math.round((model.groundedness as number) * 100) : null,
        profile: model.profileTag || 'Benchmark candidate',
        model: model.model,
        runs: model.runs,
        caseCount: model.caseCount,
      })),
    [models],
  );

  const sourceBreakdown = data?.sourceBreakdown ?? [];

  const presentScatterProfiles = useMemo(
    () => Array.from(new Set(scatterData.map((item) => item.profile))).filter((label) => Boolean(profileColors[label])),
    [scatterData],
  );

  const retrievalChartData = useMemo(() => {
    const scoredObservations = retrievalObservations
      .filter((item) => isNumber(item.composite) || isNumber(item.outputDiscipline) || isNumber(item.contextRetention))
      .sort((left, right) => {
        const compositeDelta = (right.composite ?? -1) - (left.composite ?? -1);
        if (compositeDelta !== 0) {
          return compositeDelta;
        }
        const outputDelta = (right.outputDiscipline ?? -1) - (left.outputDiscipline ?? -1);
        if (outputDelta !== 0) {
          return outputDelta;
        }
        const retentionDelta = (right.contextRetention ?? -1) - (left.contextRetention ?? -1);
        if (retentionDelta !== 0) {
          return retentionDelta;
        }
        return (left.latency ?? Number.POSITIVE_INFINITY) - (right.latency ?? Number.POSITIVE_INFINITY);
      });

    const representativeByScore = new Map<string, typeof scoredObservations[number]>();
    scoredObservations.forEach((item) => {
      const scoreKey = [
        isNumber(item.outputDiscipline) ? Math.round(item.outputDiscipline * 100) : 'na',
        isNumber(item.contextRetention) ? Math.round(item.contextRetention * 100) : 'na',
        isNumber(item.composite) ? Math.round(item.composite * 100) : 'na',
      ].join(':');
      const existing = representativeByScore.get(scoreKey);
      if (!existing || (item.latency ?? Number.POSITIVE_INFINITY) < (existing.latency ?? Number.POSITIVE_INFINITY)) {
        representativeByScore.set(scoreKey, item);
      }
    });

    const representativeRows = Array.from(representativeByScore.values());
    const desiredCount = Math.min(12, representativeRows.length);
    if (desiredCount === 0) {
      return [];
    }

    const chosenIndices = new Set<number>();
    for (let position = 0; position < desiredCount; position += 1) {
      const index = Math.round((position * (representativeRows.length - 1)) / Math.max(desiredCount - 1, 1));
      chosenIndices.add(index);
    }

    return Array.from(chosenIndices)
      .sort((left, right) => left - right)
      .map((index) => representativeRows[index])
      .map((item) => ({
        name: item.strategy.replace(/_/g, ' '),
        category: item.category ?? 'Retrieval benchmark',
        OutputDiscipline: isNumber(item.outputDiscipline) ? Math.round(item.outputDiscipline * 100) : null,
        ContextRetention: isNumber(item.contextRetention) ? Math.round(item.contextRetention * 100) : null,
        Composite: isNumber(item.composite) ? Math.round(item.composite * 100) : null,
      }));
  }, [retrievalObservations]);

  const freshnessLabel = formatBenchmarkTimestamp(data?.summary.lastRecordedAt);

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="lab-benchmarks-header">
        <AiLabSectionIntro
        title="Benchmarks"
        description="Recorded product benchmark comparison hub — measured fit, groundedness, adherence and latency from persisted comparison runs in this workspace."
        operatorQuestion="Which model setup is actually strongest for the benchmark scenarios this product has already executed here?"
        badges={[
          { label: benchmarkStatus, variant: data?.status === 'historical' ? 'warning' : 'default' },
          ...(benchmarkBaselineLabel ? [{ label: `Baseline: ${benchmarkBaselineLabel}`, variant: 'default' as const }] : []),
          ...(data?.summary.lastRecordedAt ? [{ label: `Last run: ${freshnessLabel}`, variant: data?.status === 'historical' ? 'warning' as const : 'default' as const }] : []),
        ]}
        dataSource={data?.meta.source}
        degradedReason={data?.degraded_reason}
        />
      </div>

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            Benchmarks read only the persisted phase7 comparison log for this workspace. The Product API response could not be refreshed just now.
          </div>
        </GlassCard>
      )}

      {(data?.status === 'historical' || partialModelCount > 0) && (
        <GlassCard className="mb-6 border border-primary/20 bg-primary/5">
          <div className="flex items-start gap-2 text-xs text-muted-foreground leading-relaxed">
            <CalendarClock className="w-4 h-4 text-primary mt-0.5 shrink-0" />
            <div>
              {data?.status === 'historical' ? (
                <p>
                  The latest recorded benchmark is <span className="text-foreground font-medium">historical</span> ({freshnessLabel}). This surface is useful for comparison evidence, but it is not showing live product traffic. Local Phase 8.5 runtime winners are merged in when that decision bundle exists.
                </p>
              ) : null}
              {partialModelCount > 0 ? (
                <p className={data?.status === 'historical' ? 'mt-2' : ''}>
                  {partialModelCount} model row(s) come from older comparison runs that do not include measured groundedness or use-case-fit telemetry. Those metrics are shown as <span className="text-foreground font-medium">Not scored</span> instead of being inferred. Groundedness measures how well the answer stays supported by the captured evidence; use-case fit measures how well the output matches the benchmark task goal.
                </p>
              ) : null}
            </div>
          </div>
        </GlassCard>
      )}

      <div data-tour="lab-benchmarks-metrics">
        <AiLabMetricGrid
        columns={6}
        metrics={[
          { label: 'Recorded Runs', value: data?.summary.totalRuns ?? '—', icon: BarChart3, status: 'neutral' },
          { label: 'Models Tested', value: data?.summary.modelCount ?? '—', icon: Gauge, status: 'neutral' },
          { label: 'Scored Models', value: data?.summary.scoredModelCount ?? '—', icon: CheckCircle2, status: isNumber(data?.summary.scoredModelCount) && (data?.summary.scoredModelCount ?? 0) > 0 ? 'healthy' : 'neutral' },
          { label: 'Benchmark Scenarios', value: data?.summary.useCaseCount ?? '—', icon: Target, status: 'neutral' },
          { label: 'Best Scored Fit', value: formatPercentWithLabel(recommended?.useCaseFit), icon: Trophy, status: recommended ? 'healthy' : 'neutral' },
          { label: 'Fastest Latency', value: formatSeconds(data?.summary.fastestLatency), icon: Timer, status: isNumber(data?.summary.fastestLatency) ? 'healthy' : 'neutral' },
        ]}
        />
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6" data-tour="lab-benchmarks-coverage">
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Provider coverage</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{providerSummary.length || '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Providers that actually appear in recorded comparison runs.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Top scored provider</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{providerSummary[0]?.provider ?? 'No provider yet'}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {providerSummary[0]?.bestModel
              ? `${providerSummary[0].bestModel} · ${providerSummary[0].bestFit}% best fit`
              : 'No provider has measured use-case-fit telemetry yet.'}
          </p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Benchmark posture</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{benchmarkStatus}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {data?.status === 'historical'
              ? `Latest recorded comparison: ${freshnessLabel}.`
              : data?.degraded_reason ?? `${leaderboardHighlights.length} highlight(s) derived from recorded runs.`}
          </p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Benchmark bundles</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{data?.summary.sourceBundleCount ?? '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Merged phase7 comparisons plus benchmark_runs bundles such as Phase 4.5 retrieval sweeps, Phase 8.5 matrices, and findings experiments.</p>
        </GlassCard>
      </div>

      {leaderboardHighlights.length ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6" data-tour="lab-benchmarks-highlights">
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
        <div className="inline-flex">
        <TabsList data-tour="lab-benchmarks-tabs" className="bg-secondary/30 border border-border/50 mb-4">
          <TabsTrigger value="leaderboard" className="text-xs data-[state=active]:bg-secondary">Leaderboard</TabsTrigger>
          <TabsTrigger value="tradeoffs" className="text-xs data-[state=active]:bg-secondary">Tradeoff Map</TabsTrigger>
          <TabsTrigger value="cards" className="text-xs data-[state=active]:bg-secondary">Model Cards</TabsTrigger>
          <TabsTrigger value="profiles" className="text-xs data-[state=active]:bg-secondary">Prompt Profiles</TabsTrigger>
          <TabsTrigger value="retrieval" className="text-xs data-[state=active]:bg-secondary">Retrieval Strategies</TabsTrigger>
        </TabsList>
        </div>

        <TabsContent value="leaderboard" className="mt-0">
          <GlassCard data-tour="lab-benchmarks-leaderboard">
            <div className="flex items-center gap-2 mb-4">
              <Trophy className="w-4 h-4 text-glow-warning" />
              <h3 className="text-sm font-medium text-foreground">Model Leaderboard</h3>
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            {isLoading && !orderedModels.length ? (
              <p className="text-xs text-muted-foreground">Loading recorded benchmark runs…</p>
            ) : orderedModels.length === 0 ? (
              <p className="text-xs text-muted-foreground">No phase7 benchmark comparison log has been recorded in this workspace yet.</p>
            ) : (
              <div className="space-y-2">
                {orderedModels.map((model, index) => {
                  const profile = model.profileTag || (model.scoreStatus === 'partial' ? 'Historical comparison' : 'Benchmark candidate');
                  const isRecommended = model.profileTag === 'Recommended production';
                  const isExternal = model.profileTag === 'External reference';
                  const isPartial = model.scoreStatus === 'partial';
                  return (
                    <motion.div
                      key={model.id}
                      data-tour={index < 3 ? 'lab-benchmarks-leaderboard-row' : undefined}
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
                          {isPartial ? (
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-medium">Partial scoring</span>
                          ) : null}
                        </div>
                        <p className="text-[10px] text-muted-foreground">
                          {model.provider} · {model.family} · {model.quantization}
                          {isNumber(model.caseCount) && (model.caseCount ?? 0) > model.runs ? ` · ${model.caseCount} eval cases` : ''}
                        </p>
                        <p className="text-[10px] text-muted-foreground mt-1">{profile}</p>
                      </div>
                      <div className="flex items-center gap-6 text-[10px] text-muted-foreground shrink-0">
                        <div className="text-center"><p className="text-foreground font-medium">{formatSeconds(model.latency)}</p><p>Latency</p></div>
                        <div className="text-center"><p className="text-foreground font-medium">{formatPercent(model.adherence)}</p><p>Adherence</p></div>
                        <div className="text-center"><p className="text-foreground font-medium">{formatPercent(model.groundedness)}</p><p>Ground.</p></div>
                        <div className="text-center"><p className="text-primary font-semibold text-xs">{formatPercent(model.useCaseFit)}</p><p>Fit</p></div>
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
              <h3 className="text-sm font-medium text-foreground">Latency vs Scored Use-Case Fit</h3>
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            {scatterData.length === 0 ? (
              <p className="text-xs text-muted-foreground">A tradeoff map appears after comparison runs record measured use-case-fit telemetry.</p>
            ) : (
              <>
                <div className="h-[340px]">
                  <ChartContainer config={scatterChartConfig} className="w-full h-full">
                    <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                      <XAxis type="number" dataKey="latency" name="Latency" unit="s" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} label={{ value: 'Latency (seconds)', position: 'bottom', fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                      <YAxis type="number" dataKey="fit" name="Fit" unit="%" domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} label={{ value: 'Scored use-case fit %', angle: -90, position: 'insideLeft', fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                      <ChartTooltip
                        content={({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; profile: string; latency: number; fit: number; groundedness: number | null; runs: number; caseCount?: number } }> }) => {
                          if (!active || !payload?.length) return null;
                          const entry = payload[0].payload;
                          return (
                            <div className="glass rounded-lg p-3 border border-border/50 text-xs">
                              <p className="font-medium text-foreground mb-1">{entry.name}</p>
                              <p className="text-muted-foreground text-[10px] mb-2">{entry.profile}</p>
                              <div className="space-y-0.5 text-[10px]">
                                <p>Latency: <span className="text-foreground">{entry.latency}s</span></p>
                                <p>Fit: <span className="text-foreground">{entry.fit}%</span></p>
                                <p>Groundedness: <span className="text-foreground">{entry.groundedness == null ? 'Not scored' : `${entry.groundedness}%`}</span></p>
                                <p>Recorded bundles: <span className="text-foreground">{entry.runs}</span></p>
                                {isNumber(entry.caseCount) && (entry.caseCount ?? 0) > entry.runs ? (
                                  <p>Evaluated cases: <span className="text-foreground">{entry.caseCount}</span></p>
                                ) : null}
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
                  {presentScatterProfiles.map((label) => (
                    <div key={label} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: profileColors[label] }} />
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
            {orderedModels.map((model, index) => {
              const profile = model.profileTag || (model.scoreStatus === 'partial' ? 'Historical comparison without full scoring' : 'Benchmark candidate');
              const isRecommended = model.profileTag === 'Recommended production';
              const isExternal = model.profileTag === 'External reference';
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
                    <div className="flex items-center gap-2 flex-wrap justify-end">
                      {isRecommended ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-glow-success/10 text-glow-success border border-glow-success/20 font-medium">Production</span>
                      ) : null}
                      {isExternal ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border/50 font-medium">External ref.</span>
                      ) : null}
                      {model.scoreStatus === 'partial' ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20 font-medium">Partial scoring</span>
                      ) : null}
                    </div>
                  </div>
                  <p className="text-[10px] text-muted-foreground mb-3">{profile}</p>
                  <div className="space-y-3 mt-2">
                    <MetricRow label="Use Case Fit" value={model.useCaseFit} coverage={model.metricCoverage?.useCaseFit} />
                    <MetricRow label="Groundedness" value={model.groundedness} coverage={model.metricCoverage?.groundedness} />
                    <MetricRow label="Adherence" value={model.adherence} coverage={model.metricCoverage?.adherence} />
                  </div>
                  <div className="mt-4 pt-3 border-t border-border/30 grid grid-cols-2 sm:grid-cols-3 gap-2 text-[10px] text-muted-foreground">
                    <div><span className="block text-muted-foreground/60">Latency</span>{formatSeconds(model.latency)}</div>
                    <div><span className="block text-muted-foreground/60">Output</span>{isNumber(model.outputChars) ? `${Math.round(model.outputChars)} chars` : '—'}</div>
                    <div><span className="block text-muted-foreground/60">Runtime</span>{model.runtimeBucket?.replace(/_/g, ' ') || '—'}</div>
                    <div><span className="block text-muted-foreground/60">Bundles</span>{model.runs}</div>
                    {isNumber(model.caseCount) && (model.caseCount ?? 0) > model.runs ? (
                      <div><span className="block text-muted-foreground/60">Eval cases</span>{model.caseCount}</div>
                    ) : null}
                  </div>
                  {model.scoreStatus === 'partial' ? (
                    <p className="mt-3 text-[10px] leading-relaxed text-muted-foreground">
                      Groundedness and use-case fit are blank here because this source bundle only recorded partial benchmark telemetry. The page keeps those fields unfilled instead of backfilling guessed values.
                    </p>
                  ) : null}
                </motion.div>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="profiles" className="mt-0 space-y-3">
          {promptProfiles.length === 0 ? (
            <GlassCard>
              <p className="text-xs text-muted-foreground">No recorded prompt profiles were found in the phase7 comparison log.</p>
            </GlassCard>
          ) : (
            promptProfiles.map((profile, index) => (
              <GlassCard key={profile.id} delay={0.1 + index * 0.05}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-medium text-foreground">{profile.name}</h4>
                    <p className="text-xs text-muted-foreground mt-0.5">{profile.description}</p>
                  </div>
                  {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
                </div>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {profile.metrics.map((metric) => (
                    <span key={metric} className="text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">{metric}</span>
                  ))}
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[10px]">
                  {isNumber(profile.metricSummary?.useCaseFit) ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Fit {formatPercent(profile.metricSummary?.useCaseFit)}</span> : null}
                  {isNumber(profile.metricSummary?.groundedness) ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Grounding {formatPercent(profile.metricSummary?.groundedness)}</span> : null}
                  {isNumber(profile.metricSummary?.adherence) ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Adherence {formatPercent(profile.metricSummary?.adherence)}</span> : null}
                  {isNumber(profile.metricSummary?.decisionScore) ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Decision {formatPercent(profile.metricSummary?.decisionScore)}</span> : null}
                  {isNumber(profile.metricSummary?.groundingRatio) ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Grounding ratio {formatPercent(profile.metricSummary?.groundingRatio)}</span> : null}
                  {isNumber(profile.metricSummary?.structuredSuccess) ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Structured {formatPercent(profile.metricSummary?.structuredSuccess)}</span> : null}
                  {isNumber(profile.metricSummary?.latency) ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Latency {formatSeconds(profile.metricSummary?.latency)}</span> : null}
                  {isNumber(profile.runCount) && profile.runCount > 0 ? <span className="px-2 py-0.5 rounded border border-border/50 bg-secondary/30 text-foreground">Bundles {profile.runCount}</span> : null}
                </div>
                <p className="text-[10px] text-muted-foreground mt-2">Models: {profile.models.join(', ')}</p>
              </GlassCard>
            ))
          )}
          {providerSummary.length ? (
            <GlassCard delay={0.2}>
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-medium text-foreground">Provider Summary</h3>
              </div>
              <div className="space-y-2">
                {providerSummary.map((provider) => (
                  <div key={provider.provider} className="flex items-center justify-between gap-4 rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                    <div>
                      <p className="text-xs font-medium text-foreground">{provider.provider}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {provider.models} model(s)
                        {isNumber(provider.scoredModels) ? ` · ${provider.scoredModels} scored` : ''}
                        {provider.bestFit != null ? ` · best ${provider.bestFit}% fit` : ' · no scored fit yet'}
                      </p>
                    </div>
                    <div className="text-right text-[10px] text-muted-foreground">
                      <p className="text-foreground font-medium">{formatSeconds(provider.avgLatency ?? null)}</p>
                      <p>{provider.bestModel ?? 'No scored leader yet'}</p>
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
              <>
                <div className="h-[260px]">
                  <ChartContainer config={retrievalChartConfig} className="w-full h-full">
                    <BarChart data={retrievalChartData} margin={{ top: 10, right: 20, bottom: 5, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.3} />
                      <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <Legend wrapperStyle={{ fontSize: '10px' }} />
                      <Bar dataKey="OutputDiscipline" fill="hsl(217, 91%, 60%)" radius={[2, 2, 0, 0]} />
                      <Bar dataKey="ContextRetention" fill="hsl(142, 71%, 45%)" radius={[2, 2, 0, 0]} />
                      <Bar dataKey="Composite" fill="hsl(280, 67%, 55%)" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ChartContainer>
                </div>
                <p className="mt-3 text-[10px] leading-relaxed text-muted-foreground">
                  This chart shows representative score bands across the retrieval observations, instead of only the top few ties. The full observation table stays expanded below.
                </p>
              </>
            )}
          </GlassCard>

          <GlassCard>
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-medium text-foreground">Retrieval Observation Detail</h3>
              {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border/50">
                    {['Strategy', 'Category', 'Output', 'Retention', 'Composite', 'Latency', 'Candidates', 'Avg ctx chars', 'Description'].map((heading) => (
                      <th key={heading} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{heading}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {retrievalObservations.map((item) => (
                    <tr key={`${item.category ?? 'retrieval'}:${item.strategy}`} className="border-b border-border/20 hover:bg-secondary/10 transition-colors">
                      <td className="px-3 py-2.5 text-xs text-foreground font-mono">{item.strategy}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{item.category ?? '—'}</td>
                      <td className="px-3 py-2.5 text-xs text-foreground">{formatPercent(item.outputDiscipline)}</td>
                      <td className="px-3 py-2.5 text-xs text-foreground">{formatPercent(item.contextRetention)}</td>
                      <td className="px-3 py-2.5 text-xs text-primary font-medium">{formatPercent(item.composite)}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{formatSeconds(item.latency)}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{item.candidateCount ?? '—'}{isNumber(item.scoredCandidateCount) ? ` · ${item.scoredCandidateCount} scored` : ''}</td>
                      <td className="px-3 py-2.5 text-xs text-muted-foreground">{formatCount(item.avgContextChars)}</td>
                      <td className="px-3 py-2.5 text-[10px] text-muted-foreground">{item.description}</td>
                    </tr>
                  ))}
                  {isLoading && !retrievalObservations.length ? (
                    <tr>
                      <td colSpan={9} className="px-3 py-6 text-xs text-muted-foreground">Loading retrieval observations…</td>
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
                    <span className="text-foreground font-medium">{retrievalObservations[0].strategy}</span> is the best scored retrieval posture observed in this workspace, with{' '}
                    <span className="text-foreground font-medium">{formatPercent(retrievalObservations[0].composite)}</span> composite quality across{' '}
                    <span className="text-foreground font-medium">{retrievalObservations[0].scoredCandidateCount ?? 0}</span> scored candidate(s) and{' '}
                    <span className="text-foreground font-medium">{retrievalObservations[0].candidateCount ?? 0}</span> total captured candidate result(s).
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
