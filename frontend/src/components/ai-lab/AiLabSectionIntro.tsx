import { motion } from 'framer-motion';
import type { DataSource } from '@/types/ai-lab';
import { DATA_SOURCE_LABELS } from '@/types/ai-lab';
import { cn } from '@/lib/utils';

interface DataSourceBadgeProps {
  source: DataSource;
  className?: string;
}

export function DataSourceBadge({ source, className }: DataSourceBadgeProps) {
  const colors: Record<DataSource, string> = {
    live: 'bg-glow-success/10 text-glow-success border-glow-success/20',
    derived: 'bg-primary/10 text-primary border-primary/20',
    snapshot: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
    mock: 'bg-muted text-muted-foreground border-border',
  };
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9px] font-medium border tracking-wide', colors[source], className)}>
      <span className={cn('w-1 h-1 rounded-full',
        source === 'live' && 'bg-glow-success',
        source === 'derived' && 'bg-primary',
        source === 'snapshot' && 'bg-glow-warning',
        source === 'mock' && 'bg-muted-foreground',
      )} />
      {DATA_SOURCE_LABELS[source]}
    </span>
  );
}

interface AiLabSectionIntroProps {
  title: string;
  description: string;
  operatorQuestion: string;
  badges?: Array<{ label: string; variant?: 'default' | 'success' | 'warning' | 'error' }>;
  dataSource?: DataSource;
  surfaceStatus?: string;
  degradedReason?: string | null;
  children?: React.ReactNode;
}

export function AiLabSectionIntro({ title, description, operatorQuestion, badges, dataSource, surfaceStatus, degradedReason, children }: AiLabSectionIntroProps) {
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
      <div className="flex items-start justify-between">
        <div className="max-w-2xl">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
            {dataSource && <DataSourceBadge source={dataSource} />}
          </div>
          <p className="text-sm text-muted-foreground mt-1">{description}</p>
          <p className="text-xs text-primary/70 mt-2 italic">↳ {operatorQuestion}</p>
          {(surfaceStatus || degradedReason) && (
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              {surfaceStatus ? (
                <span className={cn('px-2 py-0.5 rounded text-[10px] font-medium border',
                  surfaceStatus === 'live' && 'bg-glow-success/10 text-glow-success border-glow-success/20',
                  surfaceStatus === 'derived-live' && 'bg-primary/10 text-primary border-primary/20',
                  surfaceStatus === 'historical' && 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
                  surfaceStatus === 'degraded' && 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
                  surfaceStatus === 'empty' && 'bg-secondary text-secondary-foreground border-border',
                )}>
                  {surfaceStatus}
                </span>
              ) : null}
              {degradedReason ? (
                <span className="text-[10px] text-muted-foreground">{degradedReason}</span>
              ) : null}
            </div>
          )}
          {badges && badges.length > 0 && (
            <div className="flex items-center gap-2 mt-3">
              {badges.map(b => {
                const variants: Record<string, string> = {
                  default: 'bg-secondary text-secondary-foreground border-border',
                  success: 'bg-glow-success/10 text-glow-success border-glow-success/20',
                  warning: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
                  error: 'bg-glow-error/10 text-glow-error border-glow-error/20',
                };
                return (
                  <span key={b.label} className={cn('px-2 py-0.5 rounded text-[10px] font-medium border', variants[b.variant || 'default'])}>
                    {b.label}
                  </span>
                );
              })}
            </div>
          )}
        </div>
        {children && <div className="flex items-center gap-2 shrink-0">{children}</div>}
      </div>
    </motion.div>
  );
}
