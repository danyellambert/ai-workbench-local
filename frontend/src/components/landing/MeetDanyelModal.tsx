import { motion } from 'framer-motion';
import { ExternalLink, Github, Linkedin, Sparkles, X } from 'lucide-react';

const LINKEDIN_URL = 'https://www.linkedin.com/in/danyel-';
const GITHUB_URL = 'https://github.com/danyellambert/ai-workbench-local';

interface MeetDanyelModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MeetDanyelModal({ isOpen, onClose }: MeetDanyelModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center px-6 py-10 bg-background/70 backdrop-blur-xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="builder-modal-title"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 18, scale: 0.98 }}
        transition={{ duration: 0.22 }}
        className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-border/70 bg-card/80 p-6 md:p-7 text-left shadow-2xl shadow-primary/10 backdrop-blur-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="absolute -top-24 -right-20 h-56 w-56 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute -bottom-28 -left-24 h-56 w-56 rounded-full bg-sky-400/10 blur-3xl" />

        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 z-20 inline-flex h-10 w-10 items-center justify-center rounded-full border border-border/60 bg-background/50 text-muted-foreground hover:text-foreground hover:bg-background/75 focus:outline-none focus:ring-2 focus:ring-primary/60 focus:ring-offset-2 focus:ring-offset-background transition-colors"
          aria-label="Close builder profile"
        >
          <X className="h-4 w-4 pointer-events-none" />
        </button>

        <div className="relative">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            Built end-to-end
          </div>

          <h2 id="builder-modal-title" className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground">
            Built by Danyel Lambert
          </h2>

          <p className="mt-4 text-sm md:text-base leading-relaxed text-muted-foreground">
            I build practical AI and automation systems that help teams transform complex information into clearer decisions.
          </p>

          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            Axiovance is a full-stack AI product demo designed to show end-to-end execution: document intelligence, workflow automation, evidence-backed decision support, evaluation, observability, and deployment.
          </p>

          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            It reflects how I like to work: understand the business problem, design the system, build the product, measure quality, and make it usable.
          </p>

          <div className="mt-7 flex flex-col sm:flex-row gap-3">
            <a
              href={LINKEDIN_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Linkedin className="h-4 w-4" />
              LinkedIn
              <ExternalLink className="h-3.5 w-3.5 opacity-70" />
            </a>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-border/60 bg-background/35 px-4 py-3 text-sm font-medium text-foreground hover:bg-background/60 transition-colors"
            >
              <Github className="h-4 w-4" />
              GitHub
              <ExternalLink className="h-3.5 w-3.5 opacity-70" />
            </a>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
