import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Archive, Eye, FlaskConical, Cpu, AlertTriangle, Link2 } from 'lucide-react';
import { AiLabSectionIntro, DataSourceBadge } from '@/components/ai-lab/AiLabSectionIntro';
import { AiLabMetricGrid } from '@/components/ai-lab/AiLabMetricGrid';
import { ArtifactExplorerPanel } from '@/components/ai-lab/ArtifactExplorerPanel';
import { GlassCard } from '@/components/shared/ui-components';
import { aiLabQueryKeys, getLabArtifactsPage } from '@/lib/ai-lab-data';

function formatDateTime(value?: string | null): string {
  if (!value) return 'n/a';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

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
  const attentionCount = (summary?.warningArtifacts ?? 0) + (summary?.errorArtifacts ?? 0);
  const statusLabel = data?.status === 'empty' ? 'Waiting for bundles' : data?.status === 'live' ? 'Live' : 'Derived live';

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div data-tour="lab-artifacts-header">
        <AiLabSectionIntro
        title="Experiments & Artifacts"
        description="Product-visible export bundles, workflow-linked evidence and capture posture for the AI Lab surfaces."
        operatorQuestion="Which persisted artifact bundles explain the latest workflow behavior?"
        dataSource={data?.meta.source}
        surfaceStatus={data?.status}
        degradedReason={data?.degraded_reason}
        />
      </div>

      {isError && (
        <GlassCard className="mb-6 border border-glow-warning/20 bg-glow-warning/5">
          <div className="flex items-center gap-2 text-xs text-glow-warning">
            <AlertTriangle className="w-4 h-4" />
            The bundle registry could not be derived from persisted metadata. This surface suppresses raw sidecars and only shows product-visible export bundles.
          </div>
        </GlassCard>
      )}

      <div data-tour="lab-artifacts-metrics">
        <AiLabMetricGrid
        columns={4}
        metrics={[
          { label: 'Export Bundles', value: summary?.totalArtifacts ?? '—', subtitle: 'top-level presentation_exports registry', icon: Archive, status: 'neutral' },
          { label: 'Ready Bundles', value: summary?.readyArtifacts ?? '—', subtitle: `${summary?.warningArtifacts ?? 0} warning · ${summary?.errorArtifacts ?? 0} error`, icon: FlaskConical, status: attentionCount > 0 ? 'warning' : 'healthy' },
          { label: 'Needs Attention', value: attentionCount, subtitle: 'failed or degraded bundles', icon: Eye, status: attentionCount > 0 ? 'warning' : 'healthy' },
          { label: 'Artifact-linked Runs', value: summary?.linkedWorkflowRuns ?? '—', subtitle: 'product workflow history', icon: Link2, status: (summary?.linkedWorkflowRuns ?? 0) > 0 ? 'healthy' : 'warning' },
        ]}
        />
      </div>

      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6" data-tour="lab-artifacts-registry-summary">
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Chat registry</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{runRegistry?.chatSessions ?? summary?.chatSessions ?? '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Persisted AI Lab chat sessions visible from the artifact surface.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Product workflow runs</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{runRegistry?.workflowRuns ?? summary?.workflowRuns ?? '—'}</p>
          <p className="mt-1 text-xs text-muted-foreground">Persisted product workflow history entries, not just inspector samples.</p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Latest linked artifact</p>
          <p className="mt-2 text-sm font-semibold text-foreground break-all">{runRegistry?.latestWorkflowArtifact?.label ?? 'No linked artifact yet'}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {runRegistry?.latestWorkflowArtifact?.updatedAt ? `Updated ${formatDateTime(runRegistry.latestWorkflowArtifact.updatedAt)}` : 'The latest workflow run with a captured artifact bundle will surface here.'}
          </p>
        </GlassCard>
        <GlassCard className="p-4">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Capture posture</p>
          <p className="mt-2 text-sm font-semibold text-foreground">{statusLabel}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {data?.degraded_reason ?? `${summary?.linkedWorkflowRuns ?? 0} artifact-linked product run(s), ${summary?.unlinkedWorkflowRuns ?? 0} still without artifact capture, across ${summary?.workflowCount ?? 0} workflow surface(s).`}
          </p>
        </GlassCard>
      </div>

      <div className="grid xl:grid-cols-[1.15fr,0.85fr] gap-4 mb-6">
        <GlassCard delay={0.08} data-tour="lab-artifacts-run-registry">
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
              <p className="text-muted-foreground uppercase tracking-wider">Latest product workflow run</p>
              <p className="mt-2 text-xs text-foreground font-medium break-all">{runRegistry?.latestWorkflowRun ?? 'No run yet'}</p>
            </div>
            <div className="rounded-lg border border-border/30 bg-secondary/20 p-3 sm:col-span-2">
              <p className="text-muted-foreground uppercase tracking-wider">Latest linked workflow artifact</p>
              <p className="mt-2 text-xs text-foreground font-medium break-all">{runRegistry?.latestWorkflowArtifact?.label ?? 'No workflow artifact linked yet'}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">{runRegistry?.latestWorkflowArtifact?.runId ? `Run ${runRegistry.latestWorkflowArtifact.runId}` : 'The latest product workflow run with a persisted artifact capture will surface here.'}</p>
            </div>
          </div>
        </GlassCard>

        <GlassCard delay={0.1} data-tour="lab-artifacts-recent-bundles">
          <div className="flex items-center gap-2 mb-4">
            <Eye className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-medium text-foreground">Recent Bundles</h3>
            {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
          </div>
          {recentCaptures.length === 0 ? (
            <p className="text-xs text-muted-foreground">No product-visible bundle registry has been derived yet from the current workspace.</p>
          ) : (
            <div className="space-y-2">
              {recentCaptures.slice(0, 6).map((capture) => {
                const details = [
                  capture.slideCount ? `${capture.slideCount} slides` : null,
                  capture.previewCount ? `${capture.previewCount} previews` : null,
                  capture.issueCount ? `${capture.issueCount} issues` : null,
                  !capture.issueCount && capture.warningCount ? `${capture.warningCount} warnings` : null,
                  capture.assetCount ? `${capture.assetCount} assets` : null,
                ].filter(Boolean);
                return (
                  <div key={capture.id} className="rounded-lg border border-border/30 bg-secondary/20 px-3 py-2.5">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-xs font-medium text-foreground truncate">{capture.label}</span>
                      <span className="text-[10px] text-muted-foreground">{capture.status ?? 'unknown'}</span>
                    </div>
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      {capture.workflowLabel ?? 'Unlabeled workflow'}
                      {capture.exportKind ? ` · ${capture.exportKind.split('_').join(' ')}` : ''}
                      {capture.createdAt ? ` · ${formatDateTime(capture.createdAt)}` : ''}
                    </p>
                    {details.length > 0 ? <p className="mt-1 text-[10px] text-muted-foreground/80">{details.join(' · ')}</p> : null}
                  </div>
                );
              })}
            </div>
          )}
        </GlassCard>
      </div>

      <GlassCard className="mb-6" delay={0.1} data-tour="lab-artifacts-diagnostics">
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-medium text-foreground">Processing Diagnostics</h3>
          {data?.meta.source && <DataSourceBadge source={data.meta.source} />}
        </div>
        {isLoading && !diagnostics.length ? (
          <p className="text-xs text-muted-foreground">Loading diagnostics from runtime state and artifact metadata…</p>
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

      <GlassCard delay={0.2} data-tour="lab-artifacts-explorer">
        <ArtifactExplorerPanel artifacts={artifacts} dataSource={data?.meta.source ?? 'derived'} />
      </GlassCard>
    </motion.div>
  );
}
