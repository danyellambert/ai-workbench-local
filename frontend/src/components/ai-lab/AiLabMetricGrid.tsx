import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

interface MetricItem {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  status?: 'healthy' | 'warning' | 'error' | 'neutral';
  trend?: string;
  subtitle?: string;
}

interface AiLabMetricGridProps {
  metrics: MetricItem[];
  columns?: 2 | 3 | 4 | 5 | 6;
}

export function AiLabMetricGrid({ metrics, columns = 4 }: AiLabMetricGridProps) {
  const colClass: Record<number, string> = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 md:grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-4',
    5: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-5',
    6: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-6',
  };
  const statusColor: Record<string, string> = {
    healthy: 'text-glow-success',
    warning: 'text-glow-warning',
    error: 'text-glow-error',
    neutral: 'text-foreground',
  };

  return (
    <div className={cn('grid gap-3 mb-6', colClass[columns])}>
      {metrics.map((m, i) => {
        const Icon = m.icon;
        return (
          <motion.div key={m.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 + i * 0.03, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="glass rounded-xl p-4 group hover:border-primary/20 transition-all duration-300">
            <div className="flex items-start justify-between mb-2">
              {Icon && (
                <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center bg-secondary/50',
                  m.status === 'healthy' && 'text-glow-success',
                  m.status === 'warning' && 'text-glow-warning',
                  m.status === 'error' && 'text-glow-error',
                  (!m.status || m.status === 'neutral') && 'text-muted-foreground',
                )}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
              )}
              {m.trend && <span className="text-[10px] text-glow-success font-medium">{m.trend}</span>}
            </div>
            <p className={cn('text-xl font-semibold tracking-tight', statusColor[m.status || 'neutral'])}>{m.value}</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">{m.label}</p>
            {m.subtitle && <p className="text-[9px] text-muted-foreground/60 mt-0.5">{m.subtitle}</p>}
          </motion.div>
        );
      })}
    </div>
  );
}
