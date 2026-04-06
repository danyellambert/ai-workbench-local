import { motion } from 'framer-motion';
import { History, FileText, Clock, ArrowRight } from 'lucide-react';
import { PageHeader, StatusPill, GlassCard } from '@/components/shared/ui-components';
import { workflowRuns } from '@/lib/mock-data';

export default function RunHistoryPage() {
  return (
    <motion.div className="p-6 lg:p-8 max-w-[1400px] mx-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <PageHeader title="Run History" description="Complete history of workflow executions and generated artifacts." />

      <div className="space-y-3">
        {workflowRuns.map((run, i) => (
          <motion.div key={run.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.04 }}
            className="glass rounded-xl p-4 hover:border-primary/20 transition-all duration-300 cursor-pointer group">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 min-w-0">
                <StatusPill status={run.status} />
                <div className="min-w-0">
                  <h4 className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{run.workflow}</h4>
                  <p className="text-xs text-muted-foreground truncate">{run.documents.join(', ')}</p>
                </div>
              </div>
              <div className="flex items-center gap-6 shrink-0 ml-4">
                <div className="text-right hidden sm:block">
                  <p className="text-xs text-muted-foreground flex items-center gap-1"><Clock className="w-3 h-3" />{run.duration}</p>
                  <p className="text-[10px] text-muted-foreground">{new Date(run.startedAt).toLocaleString()}</p>
                </div>
                {run.findings && <span className="text-xs text-muted-foreground">{run.findings} findings</span>}
                {run.artifacts && (
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
