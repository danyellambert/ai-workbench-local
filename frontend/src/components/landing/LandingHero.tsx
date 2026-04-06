import { motion } from 'framer-motion';
import { ArrowRight, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Props {
  onExploreWorkflows: () => void;
}

export default function LandingHero({ onExploreWorkflows }: Props) {
  return (
    <section className="relative flex flex-col items-center justify-center min-h-screen px-6 pt-16 text-center">
      {/* Badge */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border/60 bg-card/40 backdrop-blur-md mb-8"
      >
        <Shield className="w-3.5 h-3.5 text-primary" />
        <span className="text-xs text-muted-foreground">Grounded in evidence. No hallucination by design.</span>
      </motion.div>

      {/* Headline */}
      <motion.h1
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.45 }}
        className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.08] max-w-4xl"
      >
        AI-powered decisions,{' '}
        <span className="text-gradient-hero">
          grounded in your documents.
        </span>
      </motion.h1>

      {/* Subtitle */}
      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.65 }}
        className="mt-6 text-base md:text-lg text-muted-foreground max-w-2xl leading-relaxed"
      >
        Upload contracts, reports, policies or CVs. Run structured, evidence-backed workflows
        for review, comparison, action planning and candidate assessment — with every claim
        linked to its source.
      </motion.p>

      {/* CTAs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.85 }}
        className="flex flex-col sm:flex-row items-center gap-4 mt-10"
      >
        <Link
          to="/app"
          className="group inline-flex items-center gap-2 px-7 py-3.5 rounded-xl bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-all duration-300 shadow-[0_0_30px_-5px_hsl(var(--primary)/0.4)]"
        >
          Enter Workbench
          <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
        </Link>
        <button
          onClick={onExploreWorkflows}
          className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl border border-border/60 bg-card/30 backdrop-blur-md text-sm text-muted-foreground hover:text-foreground hover:border-border transition-all duration-300"
        >
          Explore Workflows
        </button>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="absolute bottom-10"
      >
        <div className="w-5 h-8 rounded-full border-2 border-muted-foreground/30 flex justify-center pt-1.5">
          <motion.div
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-1 h-1 rounded-full bg-muted-foreground/50"
          />
        </div>
      </motion.div>
    </section>
  );
}
