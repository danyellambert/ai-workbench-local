import { motion } from 'framer-motion';
import { History, FileText, Clock, ArrowRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader, StatusPill, GlassCard } from '@/components/shared/ui-components';
import { getProductRunHistory } from '@/lib/product-api';

function formatDateTime(value?: string | null): string {
  if (!value) return 'n/a';
  const normalized = value.includes('T') ? value : value.replace(' ', 'T');
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function RunHistoryPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['product-run-history'],
    queryFn: getProductRunHistory,
  });

  const runs = data?.runs ?? [];

  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Run History" description="Complete history of workflow executions and generated artifacts." />

      <div className="space-y-3">
        {!runs.length && (
          <GlassCard>
            <div className="text-xs text-muted-foreground">{isLoading ? 'Loading run history...' : 'No product workflow history is available yet.'}</div>
          </GlassCard>
        )}
        {runs.map((run, i) => (
          <motion.div key={run.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.04 }}
            className="glass rounded-xl p-4 hover:border-primary/20 transition-all duration-300 cursor-pointer group">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 min-w-0">
                <StatusPill status={run.status} />
                <div className="min-w-0">
                  <h4 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{run.workflow_label}</h4>
                  <p className="text-xs text-muted-foreground truncate">{(run.documents || []).join(', ')}</p>
                </div>
              </div>
              <div className="flex items-center gap-6 shrink-0 ml-4">
                <div className="text-right hidden sm:block">
                  <p className="text-xs text-muted-foreground flex items-center gap-1"><Clock className="w-3 h-3" />{run.duration_label || '—'}</p>
                  <p className="text-[10px] text-muted-foreground">{formatDateTime(run.timestamp)}</p>
                </div>
                {typeof run.findings_count === 'number' && run.findings_count > 0 && <span className="text-xs text-muted-foreground">{run.findings_count} findings</span>}
                {run.artifacts && run.artifacts.length > 0 && (
                  <div className="flex items-center gap-1">
                    {run.artifacts.map(a => (
                      <span key={a} className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-muted-foreground">{a.split('.').pop()}</span>
                    ))}
                  </div>
                )}
                <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
