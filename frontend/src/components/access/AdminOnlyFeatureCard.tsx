import { Linkedin, LockKeyhole, Sparkles } from 'lucide-react';

type AdminOnlyFeatureCardProps = {
  eyebrow?: string;
  title: string;
  description: string;
  valuePoints?: string[];
  ctaLabel?: string;
  ctaHref?: string;
  secondaryLabel?: string;
  secondaryText?: string;
  compact?: boolean;
};

export default function AdminOnlyFeatureCard({
  eyebrow = 'Curated demo workspace',
  title,
  description,
  valuePoints = [],
  ctaLabel = 'Connect with Danyel on LinkedIn',
  ctaHref = 'https://www.linkedin.com/in/danyel-/',
  secondaryLabel = 'Want to test this with your own workspace?',
  secondaryText = 'Connect with Danyel for a guided demo using private documents, real workflows, and the integrations you care about.',
  compact = false,
}: AdminOnlyFeatureCardProps) {
  return (
    <div className={`glass rounded-2xl border border-border/50 bg-card/80 ${compact ? 'p-4' : 'p-5'}`}>
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-primary">
          <LockKeyhole className="h-4.5 w-4.5" />
        </div>

        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary/70">
            {eyebrow}
          </p>

          <h3 className="mt-1 text-lg font-semibold tracking-tight text-foreground">
            {title}
          </h3>

          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>

          {valuePoints.length > 0 && (
            <div className="mt-4 grid gap-2">
              {valuePoints.slice(0, 3).map((point) => (
                <div key={point} className="flex items-start gap-2 text-xs leading-5 text-muted-foreground">
                  <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary/70" />
                  <span>{point}</span>
                </div>
              ))}
            </div>
          )}

          <div className="mt-5 flex flex-col gap-3 rounded-xl border border-border/40 bg-secondary/20 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-medium text-foreground">{secondaryLabel}</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{secondaryText}</p>
            </div>

            <a
              href={ctaHref}
              target="_blank"
              rel="noreferrer"
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <Linkedin className="h-3.5 w-3.5" />
              {ctaLabel}
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
