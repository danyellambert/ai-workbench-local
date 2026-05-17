import { motion } from 'framer-motion';
import type { ElementType } from 'react';
import { Archive, FileStack, BarChart3, ShieldCheck, ChevronDown } from 'lucide-react';
import { StatusPill } from '@/components/shared/ui-components';
import { DataSourceBadge } from './AiLabSectionIntro';
import type { LabArtifact } from '@/types/ai-lab';
import type { DataSource } from '@/types/ai-lab';
import { formatUserDate } from '@/lib/user-time';

const typeIcons: Record<string, ElementType> = {
  deck_bundle: FileStack,
  benchmark_bundle: BarChart3,
  evidence_bundle: ShieldCheck,
};

interface ArtifactExplorerPanelProps {
  artifacts: LabArtifact[];
  dataSource: DataSource;
}

function formatDate(value?: string | number | null): string {
  return formatUserDate(value);
}

export function ArtifactExplorerPanel({ artifacts, dataSource }: ArtifactExplorerPanelProps) {
  const grouped = artifacts.reduce<Record<string, LabArtifact[]>>((acc, artifact) => {
    const key = artifact.workflowLabel || artifact.category || 'Unlabeled workflow';
    (acc[key] = acc[key] || []).push(artifact);
    return acc;
  }, {});
  const groupedEntries = Object.entries(grouped).map(([category, items]) => ({
    category,
    items,
    ready: items.filter((item) => item.status === 'ready').length,
    attention: items.filter((item) => item.status === 'warning' || item.status === 'error').length,
    latestCreatedAt: items.map((item) => item.createdAt).filter(Boolean).sort().slice(-1)[0] ?? null,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2" data-tour="lab-artifacts-explorer-start">
        <Archive className="w-4 h-4 text-primary" />
        <h3 className="text-sm font-medium text-foreground">Artifact Explorer</h3>
        <DataSourceBadge source={dataSource} />
      </div>
      {groupedEntries.map(({ category, items, ready, attention, latestCreatedAt }, groupIndex) => (
        <details key={category} className="rounded-xl border border-border/30 bg-secondary/10 open:bg-secondary/15" open>
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3" data-tour={groupIndex === 0 ? 'lab-artifacts-explorer-start' : undefined}>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground/60 font-medium">{category}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">{items.length} bundle(s) · {ready} ready · {attention} attention · {latestCreatedAt ? formatDate(latestCreatedAt) : 'no timestamp'}</p>
            </div>
            <ChevronDown className="w-4 h-4 text-muted-foreground transition-transform details-open:rotate-180" />
          </summary>
          <div className="grid gap-2 border-t border-border/30 px-4 py-3 md:grid-cols-2">
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
                  data-tour={groupIndex === 0 && index < 2 ? 'lab-artifacts-explorer-start' : undefined}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.08 + index * 0.02 }}
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
        </details>
      ))}
    </div>
  );
}
