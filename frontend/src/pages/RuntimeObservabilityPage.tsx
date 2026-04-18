import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Cpu, Database, FileSearch, Activity, Gauge, HardDrive, GitBranch } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { GlassCard, StatusPill } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabRuntimePage } from '@/lib/ai-lab-data';
import { Progress } from '@/components/ui/progress';

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
  const contextPressure = Math.round(Math.min(runtime?.contextPressure ?? 0, 1) * 100);

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Runtime & Observability"
        description="Full runtime configuration, resource health and diagnostic summary for the AI pipeline."
        operatorQuestion="Is the runtime healthy and cost-controlled?"
        badges={[
          runtime
            ? {
                label: runtime.vectorBackendStatus === 'healthy' ? 'All Systems Operational' : 'Degraded',
                variant: runtime.vectorBackendStatus === 'healthy' ? 'success' : 'warning',
              }
            : { label: isLoading ? 'Loading runtime…' : 'Runtime unavailable', variant: isError ? 'warning' : 'default' },
          runtime ? { label: `${runtime.indexedDocumentCount} docs`, variant: 'default' } : { label: 'Document inventory pending', variant: 'default' },
          runtime ? { label: runtime.retrievalStrategy, variant: 'default' } : { label: 'Waiting for retrieval settings', variant: 'default' },
        ]}
        dataSource={data?.meta.source}
      />

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            Runtime observability now depends on persisted backend state. The API is unavailable, so mock diagnostics are no longer shown.
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={4}
        metrics={[
          { label: 'Context Pressure', value: runtime ? `${contextPressure}%` : '—', status: contextPressure > 80 ? 'warning' : 'healthy', icon: Gauge },
          { label: 'Indexed Documents', value: runtime?.indexedDocumentCount ?? '—', status: runtime ? 'healthy' : 'neutral', icon: FileSearch },
          { label: 'Vector Backend', value: runtime?.vectorBackend ?? '—', status: runtime?.vectorBackendStatus === 'healthy' ? 'healthy' : runtime ? 'warning' : 'neutral', icon: Database },
          { label: 'Ingestion Health', value: runtime ? (runtime.ingestionHealth === 'healthy' ? 'Healthy' : runtime.ingestionHealth) : '—', status: runtime?.ingestionHealth === 'healthy' ? 'healthy' : runtime ? 'warning' : 'neutral', icon: Activity },
        ]}
      />

      <div className="grid lg:grid-cols-2 gap-4 mb-6">
        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Generation Configuration</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2.5 text-xs">
            {generationRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 border-b border-border/20 last:border-0 gap-4">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground font-mono text-[11px] text-right">{row.value}</span>
              </div>
            ))}
            {isLoading && generationRows.length === 0 && <p className="text-xs text-muted-foreground">Loading generation configuration…</p>}
          </div>
        </GlassCard>

        <GlassCard delay={0.15}>
          <div className="flex items-center gap-2 mb-4">
            <FileSearch className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Retrieval Configuration</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2.5 text-xs">
            {retrievalRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 border-b border-border/20 last:border-0 gap-4">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground font-mono text-[11px] text-right">{row.value}</span>
              </div>
            ))}
            {isLoading && retrievalRows.length === 0 && <p className="text-xs text-muted-foreground">Loading retrieval configuration…</p>}
          </div>
        </GlassCard>
      </div>

      <GlassCard className="mb-6" delay={0.2}>
        <div className="flex items-center gap-2 mb-4">
          <Gauge className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Context Budget</h3>
          {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
        </div>
        <div className="flex items-center gap-4 mb-2 flex-wrap">
          <span className="text-xs text-muted-foreground">Used: {runtime?.contextBudgetUsed?.toLocaleString() ?? '—'}</span>
          <span className="text-xs text-muted-foreground">Total: {runtime?.contextBudgetTotal?.toLocaleString() ?? '—'}</span>
          <span className={`text-xs font-medium ${contextPressure > 80 ? 'text-glow-warning' : 'text-glow-success'}`}>{runtime ? `${contextPressure}%` : '—'}</span>
        </div>
        <Progress value={runtime ? contextPressure : 0} className="h-2 bg-secondary" />
        <p className="text-[10px] text-muted-foreground mt-2">
          {!runtime
            ? 'Context usage will render when persisted runtime traces are available.'
            : contextPressure > 80
              ? 'Context budget is under pressure. Consider reducing top-k or chunk size.'
              : 'Context budget is within healthy limits for the latest persisted runtime state.'}
        </p>
      </GlassCard>

      <div className="grid lg:grid-cols-2 gap-4">
        <GlassCard delay={0.25}>
          <div className="flex items-center gap-2 mb-4">
            <HardDrive className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Vector Backend</h3>
            <StatusPill status={runtime?.vectorBackendStatus === 'healthy' ? 'active' : runtime ? 'degraded' : 'inactive'} />
          </div>
          <div className="space-y-2 text-xs">
            {vectorRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 gap-4">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground text-right">{row.value}</span>
              </div>
            ))}
            {isLoading && vectorRows.length === 0 && <p className="text-xs text-muted-foreground">Loading vector backend status…</p>}
          </div>
        </GlassCard>

        <GlassCard delay={0.3}>
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Diagnostics Summary</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="space-y-2 text-xs">
            {diagnosticsRows.map((row) => (
              <div key={row.label} className="flex justify-between py-1.5 gap-4">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="text-foreground text-right">{row.value}</span>
              </div>
            ))}
            {isLoading && diagnosticsRows.length === 0 && <p className="text-xs text-muted-foreground">Loading diagnostics summary…</p>}
          </div>
          {data?.meta.notes?.length ? (
            <div className="mt-4 rounded-lg bg-secondary/20 p-3 text-[10px] text-muted-foreground">
              {data.meta.notes.join(' ')}
            </div>
          ) : null}
        </GlassCard>
      </div>
    </motion.div>
  );
}
