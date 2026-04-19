import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Archive, Eye, FlaskConical, Cpu, AlertTriangle } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { ArtifactExplorerPanel } from '@/components/ai-lab/ArtifactExplorerPanel';
import { GlassCard } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabArtifactsPage } from '@/lib/ai-lab-data';

export default function AdvancedExperimentsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: aiLabQueryKeys.artifacts,
    queryFn: getLabArtifactsPage,
    retry: false,
    refetchOnWindowFocus: false,
  });

  const artifacts = data?.artifacts ?? [];
  const diagnostics = data?.diagnostics ?? [];
  const summary = data?.summary;
  const runRegistry = data?.runRegistry;
  const recentCaptures = data?.recentCaptures ?? [];
  const statusLabel = data?.status === 'empty' ? 'Waiting for captures' : data?.status === 'live' ? 'Live' : 'Derived live';

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <AiLabSectionIntro
        title="Experiments & Artifacts"
        description="Technical evidence archive, experimentation results and diagnostic reports for the AI pipeline."
        operatorQuestion="Where is the technical evidence that explains current behavior?"
        badges={[
          { label: `${summary?.totalArtifacts ?? 0} artifacts`, variant: 'default' },
          { label: `${summary?.readyArtifacts ?? 0} ready`, variant: 'success' },
          { label: `${summary ? summary.totalArtifacts - summary.readyArtifacts : 0} pending/error`, variant: summary && summary.errorArtifacts > 0 ? 'warning' : 'default' },
        ]}
        dataSource={data?.meta.source}
      />

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            This page now reflects the actual artifact directory and runtime diagnostics only. The Product API is unavailable, so no mock artifact catalog is shown.
          </div>
        </GlassCard>
      )}

      <AiLabMetricGrid
        columns={4}
        metrics={[
          { label: 'Total Artifacts', value: summary?.totalArtifacts ?? '—', icon: Archive, status: 'neutral' },
          { label: 'Benchmarks', value: artifacts.filter((item) => item.type === 'benchmark').length, icon: FlaskConical, status: 'neutral' },
          { label: 'Eval Reports', value: artifacts.filter((item) => item.type === 'eval').length, icon: Eye, status: 'neutral' },
          { label: 'Diagnostics', value: diagnostics.length, icon: Cpu, status: 'neutral' },
        ]}
      />

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Chat registry</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{runRegistry?.chatSessions ?? summary?.chatSessions ?? '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Persisted AI LAB chat sessions linked into the artifact surface.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Workflow runs</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{runRegistry?.workflowRuns ?? summary?.workflowRuns ?? '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Persisted inspector runs available for artifact drill-down.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Latest workflow artifact</p>
          <p className="mt-2 text-sm font-semibold text-foreground break-all">{runRegistry?.latestWorkflowArtifact ?? 'No linked artifact yet'}</p>
          <p className="mt-1 text-xs text-muted-foreground">The most recent persisted artifact path connected to Workflow Inspector.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Capture posture</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{statusLabel}</p>
          <p className="mt-1 text-xs text-muted-foreground">{data?.degraded_reason ?? `${recentCaptures.length} recent capture(s) surfaced from the live artifact inventory.`}</p>
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-[1.15fr,0.85fr] gap-4 mb-6">
        <GlassCard delay={0.08}>
          <div className="flex items-center gap-2 mb-4">
            <Archive className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Run Registry</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          <div className="grid sm:grid-cols-2 gap-3 text-[10px]">
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3">
              <p className="text-muted-foreground uppercase tracking-wider">Latest chat session</p>
              <p className="mt-2 text-xs text-foreground font-medium break-all">{runRegistry?.latestChatSession ?? 'No session yet'}</p>
            </div>
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3">
              <p className="text-muted-foreground uppercase tracking-wider">Latest workflow run</p>
              <p className="mt-2 text-xs text-foreground font-medium break-all">{runRegistry?.latestWorkflowRun ?? 'No run yet'}</p>
            </div>
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3 sm:col-span-2">
              <p className="text-muted-foreground uppercase tracking-wider">Latest linked workflow artifact</p>
              <p className="mt-2 text-xs text-foreground font-medium break-all">{runRegistry?.latestWorkflowArtifact ?? 'No workflow artifact linked yet'}</p>
            </div>
          </div>
        </GlassCard>

        <GlassCard delay={0.1}>
          <div className="flex items-center gap-2 mb-4">
            <Eye className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Recent Captures</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {recentCaptures.length === 0 ? (
            <p className="text-xs text-muted-foreground">No capture registry has been derived yet from the current artifact inventory.</p>
          ) : (
            <div className="space-y-2">
              {recentCaptures.slice(0, 6).map((capture) => (
                <div key={capture.id} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-xs font-medium text-foreground truncate">{capture.label}</span>
                    <span className="text-[10px] text-muted-foreground">{capture.status ?? 'unknown'}</span>
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground">{capture.category ?? 'uncategorized'}{capture.createdAt ? ` · ${new Date(capture.createdAt).toLocaleString()}` : ''}</p>
                  {capture.artifactPath ? <p className="mt-1 text-[10px] text-muted-foreground/80 break-all">{capture.artifactPath}</p> : null}
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      <GlassCard className="mb-6" delay={0.1}>
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Processing Diagnostics</h3>
          {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
        </div>
        {isLoading && !diagnostics.length ? (
          <p className="text-xs text-muted-foreground">Loading diagnostics from runtime state and artifact inventory…</p>
        ) : diagnostics.length === 0 ? (
          <p className="text-xs text-muted-foreground">No diagnostics were derived from the current workspace yet.</p>
        ) : (
          <div className="space-y-2">
            {diagnostics.map((diagnostic, index) => (
              <motion.div
                key={diagnostic.label}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + index * 0.03 }}
                className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-secondary/20 transition-colors gap-4"
              >
                <div>
                  <p className="text-xs font-medium text-foreground">{diagnostic.label}</p>
                  <p className="text-[10px] text-muted-foreground">{diagnostic.detail}</p>
                </div>
                <span className={`text-[10px] font-medium ${
                  diagnostic.health === 'healthy' ? 'text-glow-success' : diagnostic.health === 'warning' ? 'text-glow-warning' : 'text-muted-foreground'
                }`}>{diagnostic.status}</span>
              </motion.div>
            ))}
          </div>
        )}
        {data?.meta.notes?.length ? (
          <div className="mt-4 rounded-lg bg-secondary/20 p-3 text-[10px] text-muted-foreground">
            {data?.meta?.notes?.join(' ')}
          </div>
        ) : null}
      </GlassCard>

      <GlassCard delay={0.2}>
        <ArtifactExplorerPanel artifacts={artifacts} dataSource={data?.meta.source ?? 'derived'} />
      </GlassCard>
    </motion.div>
  );
}
