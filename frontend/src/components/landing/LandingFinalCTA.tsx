import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function LandingFinalCTA() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="relative py-32 px-6" ref={ref}>
      <div className="max-w-3xl mx-auto text-center">
        {/* Glow */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[500px] h-[500px] rounded-full opacity-[0.06]"
            style={{ background: 'radial-gradient(circle, hsl(217 91% 60%), transparent 60%)' }} />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="relative z-10"
        >
          <h2 className="text-3xl md:text-5xl font-bold tracking-tight mb-6">
            Ready to make{' '}
            <span className="text-gradient-hero">grounded decisions</span>?
          </h2>
          <p className="text-muted-foreground max-w-lg mx-auto mb-10 leading-relaxed">
            Stop relying on hallucinated summaries. Start building decisions on evidence 
            extracted directly from your documents.
          </p>
          <Link
            to="/app"
            className="group inline-flex items-center gap-2.5 px-8 py-4 rounded-xl bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-all duration-300 shadow-[0_0_40px_-8px_hsl(var(--primary)/0.5)]"
          >
            Enter Workbench
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </motion.div>
      </div>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={isInView ? { opacity: 1 } : {}}
        transition={{ delay: 0.5, duration: 0.5 }}
        className="relative z-10 mt-24 text-center"
      >
        <p className="text-[11px] text-muted-foreground/50">
          AI Decision Studio · Document intelligence for decision workflows
        </p>
      </motion.div>
    </section>
  );
}
