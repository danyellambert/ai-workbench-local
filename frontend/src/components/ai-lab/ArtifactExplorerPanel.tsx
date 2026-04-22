import { motion } from 'framer-motion';
import type { ElementType } from 'react';
import { Archive, FileStack, BarChart3, ShieldCheck } from 'lucide-react';
import { StatusPill } from '@/components/shared/ui-components';
import { DataSourceBadge } from './AiLabSectionIntro';
import type { LabArtifact } from '@/types/ai-lab';
import type { DataSource } from '@/types/ai-lab';

const typeIcons: Record<string, ElementType> = {
  deck_bundle: FileStack,
  benchmark_bundle: BarChart3,
  evidence_bundle: ShieldCheck,
};

interface ArtifactExplorerPanelProps {
  artifacts: LabArtifact[];
  dataSource: DataSource;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

export function ArtifactExplorerPanel({ artifacts, dataSource }: ArtifactExplorerPanelProps) {
  const grouped = artifacts.reduce<Record<string, LabArtifact[]>>((acc, artifact) => {
    const key = artifact.workflowLabel || artifact.category || 'Unlabeled workflow';
    (acc[key] = acc[key] || []).push(artifact);
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
            {items.map((artifact, index) => {
              const Icon = typeIcons[artifact.type] || FileStack;
              const detailBits = [
                artifact.exportKind ? artifact.exportKind.split('_').join(' ') : null,
                artifact.slideCount ? `${artifact.slideCount} slides` : null,
                artifact.previewCount ? `${artifact.previewCount} previews` : null,
                artifact.issueCount ? `${artifact.issueCount} issues` : null,
                !artifact.issueCount && artifact.warningCount ? `${artifact.warningCount} warnings` : null,
                artifact.assetCount ? `${artifact.assetCount} assets` : null,
              ].filter(Boolean);
              return (
                <motion.div
                  key={artifact.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + index * 0.03 }}
                  className="glass rounded-lg p-4 hover:border-primary/20 transition-all duration-300 group"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-secondary/50 flex items-center justify-center shrink-0">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-medium text-foreground truncate">{artifact.name}</p>
                          <span className="text-[9px] text-muted-foreground/50 font-mono">{artifact.version}</span>
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-0.5">{artifact.description}</p>
                        {detailBits.length > 0 ? <p className="text-[10px] text-muted-foreground/70 mt-1">{detailBits.join(' · ')}</p> : null}
                        <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground/60">
                          <span>{artifact.size}</span>
                          <span>{formatDate(artifact.createdAt)}</span>
                        </div>
                      </div>
                    </div>
                    <StatusPill status={artifact.status} />
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
