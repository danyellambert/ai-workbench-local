import { cn } from '@/lib/utils';
import type { CSSProperties, MouseEventHandler, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  label: string; value: string | number; icon: LucideIcon; trend?: string;
  glowColor?: string; delay?: number;
}

export function MetricCard({ label, value, icon: Icon, trend, glowColor = 'primary', delay = 0 }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="glass rounded-xl p-4 group hover:border-primary/30 transition-all duration-300"
    >
      <div className="flex items-start justify-between mb-3">
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center",
          glowColor === 'primary' && "bg-primary/10 text-primary",
          glowColor === 'accent' && "bg-accent/10 text-accent",
          glowColor === 'success' && "bg-glow-success/10 text-glow-success",
          glowColor === 'warning' && "bg-glow-warning/10 text-glow-warning",
        )}>
          <Icon className="w-4 h-4" />
        </div>
        {trend && <span className="text-[10px] text-glow-success font-medium">{trend}</span>}
      </div>
      <p className="text-2xl font-semibold text-foreground tracking-tight">{value}</p>
      <p className="text-xs text-muted-foreground mt-1">{label}</p>
    </motion.div>
  );
}

interface StatusPillProps { status: string; className?: string; }

export function StatusPill({ status, className }: StatusPillProps) {
  const config: Record<string, string> = {
    completed: 'bg-glow-success/10 text-glow-success border-glow-success/20',
    running: 'bg-primary/10 text-primary border-primary/20',
    indexed: 'bg-glow-success/10 text-glow-success border-glow-success/20',
    indexing: 'bg-primary/10 text-primary border-primary/20',
    warning: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
    error: 'bg-glow-error/10 text-glow-error border-glow-error/20',
    pending: 'bg-muted text-muted-foreground border-border',
    active: 'bg-glow-success/10 text-glow-success border-glow-success/20',
    connected: 'bg-glow-success/10 text-glow-success border-glow-success/20',
    degraded: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
    live: 'bg-glow-success/10 text-glow-success border-glow-success/20',
    'derived-live': 'bg-primary/10 text-primary border-primary/20',
    historical: 'bg-secondary/60 text-secondary-foreground border-border',
    empty: 'bg-muted text-muted-foreground border-border',
    disconnected: 'bg-glow-error/10 text-glow-error border-glow-error/20',
    not_configured: 'bg-muted text-muted-foreground border-border',
    inactive: 'bg-muted text-muted-foreground border-border',
    ready: 'bg-glow-success/10 text-glow-success border-glow-success/20',
    generating: 'bg-primary/10 text-primary border-primary/20',
    open: 'bg-primary/10 text-primary border-primary/20',
    in_progress: 'bg-glow-warning/10 text-glow-warning border-glow-warning/20',
    blocked: 'bg-glow-error/10 text-glow-error border-glow-error/20',
    done: 'bg-glow-success/10 text-glow-success border-glow-success/20',
  };

  return (
    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border capitalize", config[status] || config.pending, className)}>
      <span className={cn("w-1.5 h-1.5 rounded-full",
        status === 'running' || status === 'indexing' || status === 'generating' ? 'animate-pulse' : '',
        status === 'completed' || status === 'indexed' || status === 'active' || status === 'connected' || status === 'ready' || status === 'done' || status === 'live' ? 'bg-glow-success' : '',
        status === 'running' || status === 'indexing' || status === 'generating' || status === 'open' || status === 'derived-live' ? 'bg-primary' : '',
        status === 'warning' || status === 'degraded' || status === 'in_progress' ? 'bg-glow-warning' : '',
        status === 'error' || status === 'blocked' || status === 'disconnected' ? 'bg-glow-error' : '',
        status === 'pending' || status === 'inactive' || status === 'not_configured' || status === 'historical' || status === 'empty' ? 'bg-muted-foreground' : '',
      )} />
      {({ in_progress: 'Approved / WIP' } as Record<string, string>)[status] || status.split('_').join(' ').split('-').join(' ')}
    </span>
  );
}

interface SeverityBadgeProps { severity: 'critical' | 'high' | 'medium' | 'low'; }

export function SeverityBadge({ severity }: SeverityBadgeProps) {
  const config = {
    critical: 'bg-glow-error/15 text-glow-error border-glow-error/25',
    high: 'bg-glow-warning/15 text-glow-warning border-glow-warning/25',
    medium: 'bg-primary/15 text-primary border-primary/25',
    low: 'bg-muted text-muted-foreground border-border',
  };
  return (
    <span className={cn("px-2 py-0.5 rounded text-[10px] font-medium border uppercase tracking-wide", config[severity])}>
      {severity}
    </span>
  );
}

type WorkflowProgressStep = { key: string; label: string; status: string };

export function WorkflowProgressHeader({
  steps,
  title = 'Workflow progress',
  description = 'Track how the live run is moving across the workflow.',
  className,
}: {
  steps: WorkflowProgressStep[];
  title?: string;
  description?: string;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('glass rounded-xl p-4 mb-6', className)}
    >
      <div className="flex flex-col gap-1.5 mb-4">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <div className="flex items-center gap-1">
        {steps.map((step, index) => (
          <div key={step.key} className="flex items-center gap-1 flex-1 min-w-0">
            <div className="flex min-w-0 items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors text-muted-foreground">
              <StatusPill status={step.status} />
              <span className="hidden sm:inline truncate">{step.label}</span>
            </div>
            {index < steps.length - 1 && (
              <div className={cn('flex-1 h-px', step.status === 'completed' ? 'bg-glow-success/40' : 'bg-border')} />
            )}
          </div>
        ))}
      </div>
    </motion.div>
  );
}

export function PageHeader({ title, description, children }: { title: string; description?: string; children?: React.ReactNode }) {
  return (
    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="flex items-start justify-between mb-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description && <p className="text-sm text-muted-foreground mt-1 max-w-xl">{description}</p>}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </motion.div>
  );
}

export function EmptyState({ icon: Icon, title, description }: { icon: LucideIcon; title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-xl bg-secondary/50 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-medium text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground max-w-sm">{description}</p>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("shimmer rounded-lg", className)} />;
}

type GlassCardProps = {
  children: ReactNode;
  className?: string;
  delay?: number;
  id?: string;
  style?: CSSProperties;
  onClick?: MouseEventHandler<HTMLDivElement>;
  ['data-testid']?: string;
  ['data-tour']?: string;
};

export function GlassCard({ children, className, delay = 0, ...props }: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn("glass rounded-xl p-5", className)}
      {...props}
    >
      {children}
    </motion.div>
  );
}
