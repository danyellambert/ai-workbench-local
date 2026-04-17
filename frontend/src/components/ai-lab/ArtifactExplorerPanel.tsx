import { motion } from 'framer-motion';
import { Archive, FileText, BarChart3, ShieldCheck, Eye, Download } from 'lucide-react';
import { StatusPill } from '@/components/shared/ui-components';
import { DataSourceBadge } from './AiLabSectionIntro';
import type { LabArtifact } from '@/types/ai-lab';
import type { DataSource } from '@/types/ai-lab';

const typeIcons: Record<string, React.ElementType> = {
  report: FileText, benchmark: BarChart3, eval: ShieldCheck,
  extraction: Eye, ocr_diagnostic: Eye, embedding_experiment: Eye,
};

interface ArtifactExplorerPanelProps {
  artifacts: LabArtifact[];
  dataSource: DataSource;
}

export function ArtifactExplorerPanel({ artifacts, dataSource }: ArtifactExplorerPanelProps) {
  const grouped = artifacts.reduce<Record<string, LabArtifact[]>>((acc, a) => {
    (acc[a.category] = acc[a.category] || []).push(a);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Archive className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-medium text-foreground">Artifact Explorer</h3>
        <DataSourceBadge source={dataSource} />
      </div>
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-medium mb-2">{category}</p>
          <div className="space-y-2">
            {items.map((a, i) => {
              const Icon = typeIcons[a.type] || FileText;
              return (
                <motion.div key={a.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + i * 0.03 }}
                  className="glass rounded-lg p-4 hover:border-primary/20 transition-all duration-300 group">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-secondary/50 flex items-center justify-center shrink-0">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-medium text-foreground truncate">{a.name}</p>
                          <span className="text-[9px] text-muted-foreground/50 font-mono">{a.version}</span>
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-0.5">{a.description}</p>
                        <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground/60">
                          <span>{a.size}</span>
                          <span>{new Date(a.createdAt).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                    <StatusPill status={a.status} />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
