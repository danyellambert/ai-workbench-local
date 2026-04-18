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
            {data.meta.notes.join(' ')}
          </div>
        ) : null}
      </GlassCard>

      <GlassCard delay={0.2}>
        <ArtifactExplorerPanel artifacts={artifacts} dataSource={data?.meta.source ?? 'derived'} />
      </GlassCard>
    </motion.div>
  );
}
