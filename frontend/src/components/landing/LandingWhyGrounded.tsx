import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { CheckCircle2, FileSearch, Layers, BarChart3, FileOutput, FlaskConical } from 'lucide-react';

const capabilities = [
  { icon: CheckCircle2, title: 'Grounded Outputs', desc: 'Every finding, recommendation and claim is directly linked to source material from your documents.' },
  { icon: FileSearch, title: 'Evidence Traceability', desc: 'Full provenance chain from conclusion back to the exact chunk, page and paragraph in the original document.' },
  { icon: Layers, title: 'Structured Results', desc: 'Not free-form text. Typed, categorized outputs with severity, confidence scores and actionable metadata.' },
  { icon: BarChart3, title: 'Document-Backed Recommendations', desc: 'AI recommendations are derived from retrieved evidence, not fabricated from training data.' },
  { icon: FileOutput, title: 'Executive Artifacts', desc: 'Generate presentation decks, structured JSON exports and decision-ready materials from any workflow run.' },
  { icon: FlaskConical, title: 'Product + AI Lab', desc: 'A product layer that solves business problems, backed by an engineering lab for observability and control.' },
];

export default function LandingWhyGrounded() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section className="relative py-32 px-6" ref={ref}>
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <p className="text-xs uppercase tracking-[0.2em] text-primary font-medium mb-4">Why This Is Different</p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight max-w-2xl mx-auto">
            Every output is grounded. Every claim is traceable.
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto">
            This isn't another chatbot. It's a decision engine built on evidence architecture.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {capabilities.map((cap, i) => (
            <motion.div
              key={cap.title}
              initial={{ opacity: 0, y: 25 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: 0.1 * i }}
              className="group rounded-2xl border border-border/40 bg-card/30 backdrop-blur-sm p-6 hover:border-primary/30 transition-all duration-500 hover:shadow-[0_0_25px_-8px_hsl(var(--primary)/0.15)]"
            >
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/15 transition-colors">
                <cap.icon className="w-5 h-5 text-primary" />
              </div>
              <h3 className="text-sm font-semibold text-foreground mb-2">{cap.title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{cap.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
